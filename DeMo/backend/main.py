from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.rag.service import ask_rag


app = FastAPI()


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
# HOME
# --------------------------------

@app.get("/")
def home():

    return {
        "message": "Service Desk Agent API is running"
    }


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