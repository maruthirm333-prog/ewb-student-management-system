# Project Walkthrough — Student Management System

This guide explains the project in simple English for an internship review or viva.

## 1. What did we build?

We built a backend API that stores and manages student records. A user sends a request, FastAPI receives it, Python decides what should happen, and SQLite saves or returns the data.

The required part uses Python, FastAPI and SQLite. The Ollama AI feature is optional.

## 2. What is a backend?

A backend is the part of an application that works behind the scenes. It receives requests, applies rules, reads or changes data, and sends a response. It normally isn't the screen that a user sees.

## 3. What is an API?

An API is a way for two software programs to communicate. In this project, the client sends an HTTP request to FastAPI. FastAPI sends back a response, usually as JSON.

## 4. What are the main technologies?

- **Python:** the programming language used for the application logic.
- **FastAPI:** the Python framework that defines API routes and validates requests.
- **SQLite:** a small database saved in a file on the computer.
- **Pydantic:** checks that incoming information has the right shape and values.
- **Uvicorn:** starts the FastAPI web server.
- **Ollama (optional):** runs a language model locally on the computer.

## 5. What does CRUD mean?

- **Create:** `POST /students` — add a student.
- **Read:** `GET /students` or `GET /students/{student_id}` — view students.
- **Update:** `PUT /students/{student_id}` replaces all editable details; `PATCH /students/{student_id}` changes only the fields sent.
- **Delete:** `DELETE /students/{student_id}` removes a student.

The database generates a unique numeric ID for each new student.

## 6. How does adding a student work?

1. A client sends a `POST /students` request with JSON fields.
2. FastAPI checks the request against the Pydantic model.
3. The endpoint inserts the values into SQLite using SQL parameters.
4. SQLite stores the record and gives the new ID.
5. The API returns the created student as JSON, with status `201 Created`.

The other operations follow the same general pattern: validate input, do a safe database operation, then return a result.

## 7. How do we handle errors?

- A missing student ID returns `404 Not Found`.
- Invalid fields, an invalid date, a malformed email, or missing contact information return `422 Unprocessable Entity`.
- If Ollama is unavailable, the optional AI route returns `503 Service Unavailable`; the CRUD routes still work.
- SQL values are passed as parameters rather than inserted into SQL strings, which helps prevent SQL injection.

## 8. What does the optional AI feature do?

It accepts a question such as “How many students are there?” The backend first runs a known, limited database query in Python and prepares the result as context. It then sends the question and the context to a local Ollama model. The model writes a simple answer from the supplied information.

Important safety point: the model does **not** receive a database connection and does **not** execute SQL. The question parser supports simple question patterns; it is not a general-purpose database agent.

## 9. Why is SQLite suitable here?

SQLite stores information in a local file, so this small learning project does not need a separate database server. Data remains after the API is stopped and started again.

## 10. How to run and test

1. Open a terminal in the project folder.
2. Create and activate a virtual environment as shown in `README.md`.
3. Install `requirements.txt`.
4. Run `python -m uvicorn main:app --reload`.
5. Open `http://127.0.0.1:8000/docs`.
6. Use the interactive page to test `POST`, `GET`, `PUT`, `PATCH` and `DELETE`.
7. To run automated tests, install `requirements-dev.txt`, then run `python -m pytest -q`.

## 11. Likely viva questions and simple answers

**Q: What is the purpose of this project?**  
A: It manages student records through an API. It can add, display, edit and delete students.

**Q: Why did you use FastAPI?**  
A: It lets us define API endpoints in Python, validate incoming data, and automatically provide interactive API documentation.

**Q: Why SQLite?**  
A: It is a simple file-based database that keeps the records between application restarts.

**Q: What is CRUD?**  
A: Create, Read, Update and Delete—the four main record-management operations.

**Q: What is an endpoint?**  
A: A URL path and HTTP method that performs a particular task, for example `POST /students` adds a student.

**Q: What is the difference between PUT and PATCH?**  
A: PUT replaces the student's editable details. PATCH changes only the fields included in the request.

**Q: What happens when a user asks for a student ID that does not exist?**  
A: The API returns `404 Not Found` with a clear message.

**Q: How is input validated?**  
A: Pydantic checks fields such as the student's name, birth date, email and contact method before the endpoint saves the data.

**Q: Where is the data stored?**  
A: In `data/students.db`, an SQLite database file created automatically when the application starts.

**Q: What is the optional AI extension?**  
A: It retrieves student information in backend code, then gives that information to a local Ollama model to produce a natural-language answer.

**Q: Does the AI model execute database SQL?**  
A: No. The backend executes fixed, parameterized queries. The model receives only the resulting context.

**Q: Is this production-ready?**  
A: It is a learning assignment. Before real public use, it would need authentication, access controls, stronger operational monitoring, backups, and deployment hardening.

## 12. Honest demonstration tip

Before showing the project, run it on your own computer and test the endpoints at `/docs`. Make sure you can explain each file and operation in your own words. The source code and this guide are provided to help you learn the project; do not claim to have manually typed every line if asked.
