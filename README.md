# Task Manager API

A RESTful API built with FastAPI and PostgreSQL for managing personal tasks with user authentication.

## Tech Stack

- **FastAPI** - Web framework
- **PostgreSQL** - Database
- **SQLAlchemy** - ORM
- **JWT** - Authentication
- **Pydantic** - Data validation
- **Passlib + bcrypt** - Password hashing

## Features

- User registration and login with JWT authentication
- Create, read, update, and delete tasks
- Filter tasks by status (todo, in_progress, done)
- Search tasks by title
- Pagination on task listing
- Ownership checks - users can only access their own tasks
- Consistent error responses

## Project Structure

```
projectx/
├── main.py
├── config.py
├── .env
├── requirements.txt
└── app/
    ├── database.py
    ├── utils.py
    ├── dependencies.py
    ├── models/
    ├── schemas/
    ├── crud/
    └── routers/
```

## Setup

1. Clone the repo:
```bash
git clone https://github.com/azharkhalil0407/task-manager-api.git
cd task-manager-api
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file:
```
DATABASE_URL=postgresql://your_user@localhost/task_manager_db
SECRET_KEY=your_secret_key
```

5. Create the database:
```bash
psql postgres -c "CREATE DATABASE task_manager_db;"
```

6. Run the server:
```bash
python3 -m uvicorn main:app --reload
```

7. Visit the docs at `http://127.0.0.1:8000/docs`

## API Endpoints

### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /users/register | Register a new user |
| POST | /users/login | Login and get JWT token |
| GET | /users/me | Get current user info |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /tasks/ | List all tasks (paginated) |
| POST | /tasks/ | Create a new task |
| GET | /tasks/{id} | Get a single task |
| PUT | /tasks/{id} | Update a task |
| DELETE | /tasks/{id} | Delete a task |

## Query Parameters for GET /tasks/

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| size | int | 10 | Items per page |
| search | string | "" | Search by title |
| status | string | null | Filter by status |

## Task Status Values

- `todo`
- `in_progress`
- `done`
