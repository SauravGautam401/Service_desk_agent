Service Desk Agent

An AI-powered Service Desk application with an employee support portal,
an IT ticket-management portal, and a RAG-based chatbot.

Features

Employee Portal

Ask IT-related questions using the AI assistant.

Create support tickets with a title, description, name, and email.

View submitted tickets, their status, and IT replies.

IT Support Portal

View the ticket queue.

Read ticket details.

Reply to employees.

Update ticket status.

AI Assistant

Uses Retrieval-Augmented Generation (RAG) to retrieve relevant
information from the project's knowledge base.

Uses a language model to generate answers based on retrieved
content.

Tech Stack

Backend: Python, FastAPI

Frontend: HTML, CSS, JavaScript

Database: SQLite

AI: Embeddings, document retrieval, and a language model

Server: Uvicorn

Project Structure

Service_desk_agent/
└── DeMo/
    ├── Frontend/
    │   ├── index1.html
    │   ├── style.css
    │   └── script.js
    └── backend/
        ├── main.py
        ├── app/
        │   └── rag/
        │       └── service.py
        └── service_desk.db

This is an illustrative structure. Your repository may contain
additional files or slightly different folder names.

Requirements

Python and pip

A web browser

The Python packages required by the backend and RAG pipeline

Installation and Setup

1. Clone the repository

git clone <YOUR_GITHUB_REPOSITORY_URL>
cd <YOUR_REPOSITORY_FOLDER>

2. Open the backend directory

cd DeMo/backend

Run the commands from the directory containing main.py.

3. Install dependencies

If the repository contains requirements.txt, run:

python -m pip install -r requirements.txt

If it does not, install the packages required by the project. The
backend uses FastAPI and Uvicorn; the RAG pipeline may require
additional packages.

4. Start the server

python -m uvicorn main:app --reload

Open these addresses in your browser:

Application: http://127.0.0.1:8000/

API documentation: http://127.0.0.1:8000/docs

Health check: http://127.0.0.1:8000/api/health

Keep the terminal running while using the application.

To stop the server, press Ctrl + C in the terminal.

API Endpoints

Method   Endpoint                       Description

GET      /api/health                  Checks whether the backend is running
POST     /chat                        Sends a message to the AI assistant
POST     /tickets                     Creates a support ticket
GET      /tickets                     Retrieves tickets
POST     /tickets/{ticket_id}/reply   Adds a reply to a ticket
GET      /docs                        Opens interactive API documentation

The ticket retrieval endpoint supports role-based query parameters for
employee and IT views. See /docs for the request and response schemas.

Database

The application uses SQLite. The backend initializes the ticket tables
and stores ticket details, employee information, ticket status,
timestamps, and ticket messages in service_desk.db.

Review the database before publishing the repository. Do not upload real
employee information or private ticket conversations.

Troubleshooting

Could not import module main

Make sure the terminal is inside the backend directory containing
main.py, then run:

python -m uvicorn main:app --reload

ModuleNotFoundError

Install the missing package in the same Python environment used to run
the server. If available, install dependencies with:

python -m pip install -r requirements.txt

ERR_CONNECTION_REFUSED

The backend server is probably not running. Start Uvicorn and check its
terminal output, then open http://127.0.0.1:8000/.

Frontend API requests fail

Open the frontend through the FastAPI server at
http://127.0.0.1:8000/, rather than opening the HTML file directly.
The frontend uses the same host for API requests.

Security Notes

Do not commit API keys, passwords, tokens, private configuration
files, or virtual environments.

Use test data rather than real employee information.

Add proper authentication and authorization before deploying this
application for real users.

Future Improvements

Improve the chatbot's conversational responses.

Preserve unsent IT reply drafts during ticket-list refreshes.

Add stronger authentication and role-based access control.

Add ticket search, filtering, and automated tests.

Add deployment instructions.

Contributing

Suggestions and improvements are welcome. Open an issue or submit a pull
request.

License

Add a license file before allowing others to reuse or distribute this
project. Without a license, standard copyright restrictions apply.