import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.rag.service import ask_rag

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


init_db()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


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
    try:
        return {"response": ask_rag(request.message)}
    except Exception as exc:
        # Keep the ticketing portal usable even if the local RAG model is unavailable.
        raise HTTPException(status_code=500, detail=f"The AI assistant could not answer right now: {exc}")


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
