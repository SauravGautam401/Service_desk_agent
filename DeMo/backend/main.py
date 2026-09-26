import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.rag.service import ask_rag


app = FastAPI()


# --------------------------------
# FRONTEND PATH
# --------------------------------
# backend/main.py -> DeMo/backend -> DeMo -> DeMo/Frontend
FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "Frontend"
)


# --------------------------------
# CORS
# --------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------
# REQUEST MODEL
# --------------------------------

class ChatRequest(BaseModel):
    message: str


# --------------------------------
# HOME (serves the frontend UI)
# --------------------------------

@app.get("/")
def home():

    return FileResponse(
        os.path.join(FRONTEND_DIR, "index1.html")
    )


# --------------------------------
# CHAT
# --------------------------------

@app.post("/chat")
def chat(request: ChatRequest):

    answer = ask_rag(
        request.message
    )

    return {
        "response": answer
    }


# --------------------------------
# STATIC FILES (style.css, script.js, etc.)
# --------------------------------
# Mounted last so it does not shadow the "/" and "/chat" routes above.
# This lets index1.html load style.css / script.js from the same origin,
# so running only the backend server is enough to use the UI.

app.mount(
    "/",
    StaticFiles(directory=FRONTEND_DIR),
    name="frontend"
)