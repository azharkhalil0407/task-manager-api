# Task Manager API

A production-structured RESTful API built with FastAPI and PostgreSQL for managing personal tasks with JWT authentication, tag support, and ownership-based access control.

## Tech Stack

- **FastAPI** - Web framework
- **PostgreSQL** - Database
- **SQLAlchemy** - ORM with many-to-many relationship support
- **Alembic** - Database migrations
- **JWT (python-jose)** - Authentication
- **Pydantic v2** - Data validation and serialization
- **Passlib + bcrypt** - Password hashing

## Features

- User registration and login with JWT authentication
- Full CRUD on tasks - create, read, update, and delete
- Tag support with many-to-many relationships (tasks can share tags globally)
- Filter tasks by status (`todo`, `in_progress`, `done`)
- Case-insensitive title search
- Pagination on task listing
- Ownership checks - users can only access their own tasks
- Consistent error responses across all endpoints (`{"status": "error", "message": "..."}`)

## Project Structure

```
task-manager-api/
├── main.py
├── config.py
├── .env
├── requirements.txt
└── app/
    ├── database.py
    ├── utils.py
    ├── models/
    │   ├── users.py
    │   ├── tasks.py
    │   └── tags.py
    ├── schemas/
    │   ├── users.py
    │   └── tasks.py
    ├── crud/
    │   ├── users.py
    │   └── tasks.py
    └── routers/
        ├── users.py
        └── tasks.py
```

## Setup

1. Clone the repo:
```bash
git clone https://github.com/azharkhalil0407/task-manager-api.git
cd task-manager-api
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:
```
DATABASE_URL=postgresql://your_user@localhost/task_manager_db
SECRET_KEY=your_secret_key_minimum_32_characters
```

5. Create the database:
```bash
psql postgres -c "CREATE DATABASE task_manager_db;"
```

6. Run the server:
```bash
python3 -m uvicorn main:app --reload
```

7. Visit the interactive docs at `http://127.0.0.1:8000/docs`

## API Endpoints

### Users

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/users/register` | No | Register a new user |
| POST | `/users/login` | No | Login and receive a JWT token |
| GET | `/users/me` | Yes | Get current authenticated user |

### Tasks

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/tasks/` | Yes | List own tasks (paginated, searchable, filterable) |
| POST | `/tasks/` | Yes | Create a new task |
| GET | `/tasks/{id}` | Yes | Get a single task (ownership enforced) |
| PUT | `/tasks/{id}` | Yes | Update a task (ownership enforced) |
| DELETE | `/tasks/{id}` | Yes | Delete a task (ownership enforced) |

## Query Parameters for `GET /tasks/`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (min: 1) |
| `size` | int | 10 | Items per page (min: 1, max: 100) |
| `search` | string | `""` | Case-insensitive search by title |
| `status` | string | `null` | Filter by status value |

## Task Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `title` | string | Yes | 2 to 100 characters |
| `description` | string | No | Optional detail |
| `status` | string | No | Defaults to `todo` |
| `due_date` | date (YYYY-MM-DD) | No | Optional deadline |
| `tags` | list of strings | No | Shared globally across tasks |

## Task Status Values

- `todo`
- `in_progress`
- `done`

## Example Request

**Create a task:**
```json
POST /tasks/
Authorization: Bearer <token>

{
  "title": "Write unit tests",
  "description": "Cover all CRUD endpoints with pytest",
  "status": "in_progress",
  "due_date": "2026-06-30",
  "tags": ["testing", "backend"]
}
```

**Response:**
```json
{
  "id": 1,
  "title": "Write unit tests",
  "description": "Cover all CRUD endpoints with pytest",
  "status": "in_progress",
  "due_date": "2026-06-30",
  "user_id": 3,
  "tags": ["testing", "backend"]
}
```

## Error Format

All errors return a consistent shape:
```json
{
  "status": "error",
  "message": "Task not found"
}
```