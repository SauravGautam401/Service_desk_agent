import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.rag.service import ask_rag


app = FastAPI()

FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "Frontend"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def home():

    return FileResponse(
        os.path.join(FRONTEND_DIR, "index1.html")
    )

@app.post("/chat")
def chat(request: ChatRequest):

    answer = ask_rag(
        request.message
    )

    return {
        "response": answer
    }

app.mount(
    "/",
    StaticFiles(directory=FRONTEND_DIR),
    name="frontend"
)