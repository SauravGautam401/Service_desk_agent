import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.rag.service import ask_rag, stream_rag

log = logging.getLogger("service_desk")
app = FastAPI(title="Service Desk Agent API")
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = (BASE_DIR / ".." / "Frontend").resolve()
DB_PATH = BASE_DIR / "service_desk.db"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@contextmanager
def db_session():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db():
    with db_session() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            employee_name TEXT NOT NULL,
            employee_email TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS ticket_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            author_role TEXT NOT NULL,
            author_name TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_name TEXT,
            user_email TEXT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            sources TEXT NOT NULL DEFAULT '[]',
            response_ms INTEGER,
            created_at TEXT NOT NULL
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_logs_email ON chat_logs(user_email, id)")


init_db()


def log_chat(req, answer, sources, started):
    """Persist one Q&A turn. Never lets a logging error break the chat."""
    try:
        with db_session() as conn:
            conn.execute(
                "INSERT INTO chat_logs (session_id, user_name, user_email, question, answer, sources, response_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (req.session_id, req.user_name, (req.user_email or "").lower() or None, req.message.strip(),
                 answer, json.dumps(sources), int((time.monotonic() - started) * 1000), now()),
            )
    except Exception:
        log.exception("Could not write chat log")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    session_id: Optional[str] = Field(default=None, max_length=64)
    user_name: Optional[str] = Field(default=None, max_length=120)
    user_email: Optional[str] = Field(default=None, max_length=254)


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=10000)
    employee_name: str = Field(min_length=1, max_length=120)
    employee_email: str = Field(min_length=3, max_length=254)


class TicketReply(BaseModel):
    author_name: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=5000)
    status: Optional[str] = "In Progress"


def ticket_dict(conn, row):
    messages = conn.execute(
        "SELECT id, author_role, author_name, body, created_at FROM ticket_messages WHERE ticket_id=? ORDER BY id",
        (row["id"],),
    ).fetchall()
    return {
        "id": row["id"], "title": row["title"], "description": row["description"],
        "employee_name": row["employee_name"], "employee_email": row["employee_email"],
        "status": row["status"], "created_at": row["created_at"], "updated_at": row["updated_at"],
        "messages": [dict(m) for m in messages],
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(request: ChatRequest):
    started = time.monotonic()
    try:
        result = ask_rag(request.message)
    except Exception as exc:
        # Keep the ticketing portal usable even if the local RAG model is unavailable.
        raise HTTPException(status_code=500, detail=f"The AI assistant could not answer right now: {exc}")
    log_chat(request, result["response"], result["sources"], started)
    return result


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
    """Server-Sent Events: {"type":"token","text":...} ... {"type":"done","sources":[...]}"""
    def events():
        started = time.monotonic()
        parts, sources = [], []
        try:
            for kind, data in stream_rag(request.message):
                if kind == "token":
                    parts.append(data)
                    yield _sse({"type": "token", "text": data})
                else:
                    sources = data["sources"]
                    yield _sse({"type": "done", "sources": sources})
        except Exception as exc:
            log.exception("Streaming chat failed")
            yield _sse({"type": "error", "detail": f"The AI assistant could not answer right now: {exc}"})
        finally:
            answer = "".join(parts).strip()
            if answer:
                log_chat(request, answer, sources, started)

    return StreamingResponse(
        events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/chat/logs")
def chat_logs(email: Optional[str] = None, limit: int = Query(50, ge=1, le=500)):
    """Recent logged conversations (optionally for one employee). Demo endpoint: add auth before deploying."""
    with db_session() as conn:
        if email:
            rows = conn.execute("SELECT * FROM chat_logs WHERE user_email=? ORDER BY id DESC LIMIT ?", (email.strip().lower(), limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM chat_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{**dict(r), "sources": json.loads(r["sources"])} for r in rows]


@app.post("/tickets", status_code=201)
def create_ticket(ticket: TicketCreate):
    timestamp = now()
    with db_session() as conn:
        cur = conn.execute(
            "INSERT INTO tickets (title, description, employee_name, employee_email, status, created_at, updated_at) VALUES (?, ?, ?, ?, 'Open', ?, ?)",
            (ticket.title.strip(), ticket.description.strip(), ticket.employee_name.strip(), ticket.employee_email.strip().lower(), timestamp, timestamp),
        )
        ticket_id = cur.lastrowid
        conn.execute(
            "INSERT INTO ticket_messages (ticket_id, author_role, author_name, body, created_at) VALUES (?, 'employee', ?, ?, ?)",
            (ticket_id, ticket.employee_name.strip(), "Ticket created", timestamp),
        )
        row = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        return ticket_dict(conn, row)


@app.get("/tickets")
def list_tickets(role: str = Query(..., pattern="^(employee|it)$"), email: Optional[str] = None):
    with db_session() as conn:
        if role == "employee":
            if not email:
                raise HTTPException(status_code=400, detail="Employee email is required")
            rows = conn.execute("SELECT * FROM tickets WHERE employee_email=? ORDER BY updated_at DESC", (email.strip().lower(),)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tickets ORDER BY CASE status WHEN 'Open' THEN 0 WHEN 'In Progress' THEN 1 ELSE 2 END, updated_at DESC").fetchall()
        return [ticket_dict(conn, row) for row in rows]


@app.post("/tickets/{ticket_id}/reply")
def reply_to_ticket(ticket_id: int, reply: TicketReply):
    status = reply.status or "In Progress"
    if status not in {"Open", "In Progress", "Resolved"}:
        raise HTTPException(status_code=400, detail="Invalid ticket status")
    timestamp = now()
    with db_session() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        conn.execute(
            "INSERT INTO ticket_messages (ticket_id, author_role, author_name, body, created_at) VALUES (?, 'it', ?, ?, ?)",
            (ticket_id, reply.author_name.strip(), reply.body.strip(), timestamp),
        )
        conn.execute("UPDATE tickets SET status=?, updated_at=? WHERE id=?", (status, timestamp, ticket_id))
        row = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        return ticket_dict(conn, row)


@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index1.html")


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
