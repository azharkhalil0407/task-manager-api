# task-manager-api

A RESTful Task Manager API built with FastAPI, PostgreSQL, and SQLAlchemy. Supports JWT-based authentication, task ownership, tag management, pagination, filtering, and a complete test suite. Fully containerized with Docker Compose.

---

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL (production), SQLite (testing)
- **ORM:** SQLAlchemy
- **Auth:** JWT via `python-jose`, password hashing via `passlib[bcrypt]`
- **Validation:** Pydantic v2
- **Testing:** Pytest + FastAPI TestClient
- **Containerization:** Docker + Docker Compose

---

## Project Structure

```
task-manager-api/
├── app/
│   ├── crud/
│   │   ├── tasks.py          # Task CRUD operations
│   │   └── users.py          # User CRUD operations
│   ├── models/
│   │   ├── tags.py           # Tag model + task_tags association table
│   │   ├── tasks.py          # Task model with status enum
│   │   └── users.py          # User model
│   ├── routers/
│   │   ├── tasks.py          # Task endpoints
│   │   └── users.py          # Auth endpoints (register, login, me)
│   ├── schemas/
│   │   ├── tasks.py          # TaskCreate, TaskUpdate, TaskResponse
│   │   └── users.py          # UserCreate, UserResponse
│   ├── database.py           # Engine, session, Base
│   ├── dependencies.py       # get_db dependency
│   └── utils.py              # JWT helpers, password hashing, get_current_user
├── tests/
│   ├── conftest.py           # Fixtures: client, db_session, auth_headers
│   ├── test_auth.py          # Auth endpoint tests
│   └── test_tasks.py         # Task endpoint tests
├── config.py                 # Settings via pydantic-settings
├── main.py                   # App entry point, routers, exception handlers
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Features

- User registration and login with bcrypt-hashed passwords
- JWT access token authentication (30-minute expiry)
- Full task CRUD with per-user ownership enforcement (403 on unauthorized access)
- Task status: `todo`, `in_progress`, `done`
- Many-to-many tag system via `task_tags` association table (tags shared globally, auto-created on use)
- Pagination, case-insensitive title search, and status filtering
- Global exception handlers returning consistent JSON error shapes
- Isolated test suite using SQLite — no external database required to run tests

---

## Getting Started

### Prerequisites

- Docker and Docker Compose, **or** Python 3.9+ with PostgreSQL running locally

### Run with Docker (recommended)

```bash
git clone https://github.com/azharkhalil0407/task-manager-api.git
cd task-manager-api
docker-compose up --build
```

The API will be available at `http://localhost:8000`.

`DATABASE_URL` is pre-configured to point to the PostgreSQL container defined in `docker-compose.yml`. You only need to set `SECRET_KEY` (see environment variables below).

### Run Locally

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create a .env file in the project root
echo "DATABASE_URL=postgresql://user:password@localhost:5432/taskmanager" > .env
echo "SECRET_KEY=your-secret-key-minimum-32-characters" >> .env

# Create the database
createdb taskmanager

# Start the server
uvicorn main:app --reload
```

---

## Environment Variables

| Variable       | Description                          | Required              |
|----------------|--------------------------------------|-----------------------|
| `DATABASE_URL` | PostgreSQL connection string         | Local dev only        |
| `SECRET_KEY`   | JWT signing key (min 32 characters)  | Always                |

Docker users: `DATABASE_URL` is pre-configured in `docker-compose.yml`. Only `SECRET_KEY` needs to be set.

---

## API Reference

### Auth

| Method | Endpoint          | Description             | Auth Required |
|--------|-------------------|-------------------------|---------------|
| POST   | `/users/register` | Register a new user     | No            |
| POST   | `/users/login`    | Login and get JWT token | No            |
| GET    | `/users/me`       | Get current user info   | Yes           |

### Tasks

| Method | Endpoint       | Description                        | Auth Required |
|--------|----------------|------------------------------------|---------------|
| GET    | `/tasks/`      | List tasks with pagination/filters | Yes           |
| GET    | `/tasks/{id}`  | Get a single task by ID            | Yes           |
| POST   | `/tasks/`      | Create a new task                  | Yes           |
| PUT    | `/tasks/{id}`  | Update a task (owner only)         | Yes           |
| DELETE | `/tasks/{id}`  | Delete a task (owner only)         | Yes           |

### Query Parameters for `GET /tasks/`

| Parameter | Type    | Default | Description                                      |
|-----------|---------|---------|--------------------------------------------------|
| `page`    | integer | 1       | Page number                                      |
| `size`    | integer | 10      | Results per page (max 100)                       |
| `search`  | string  | `""`    | Filter by title (case-insensitive)               |
| `status`  | string  | null    | `todo`, `in_progress`, or `done`                 |

### Task Payload (POST / PUT)

```json
{
  "title": "Buy groceries",
  "description": "Milk, eggs, bread",
  "status": "todo",
  "due_date": "2026-06-30",
  "tags": ["personal", "errands"]
}
```

### Paginated Response

```json
{
  "page": 1,
  "size": 10,
  "total": 2,
  "results": [
    {
      "id": 1,
      "title": "Buy groceries",
      "description": "Milk, eggs, bread",
      "status": "todo",
      "due_date": "2026-06-30",
      "user_id": 1,
      "tags": ["personal", "errands"]
    }
  ]
}
```

---

## Error Handling

All errors return a consistent JSON shape:

```json
{
  "status": "error",
  "message": "Task not found"
}
```

Global exception handlers catch `RequestValidationError` (422) and `HTTPException` to ensure uniform error responses across all endpoints.

---

## Running Tests

```bash
python3 -m pytest tests/ -v
```

Tests use an isolated SQLite database that is created and dropped per test function. No PostgreSQL instance is required. The suite covers user registration, login, authentication edge cases, task CRUD, and ownership enforcement.

---

## Data Models

### User

| Field     | Type    | Notes            |
|-----------|---------|------------------|
| id        | integer | Primary key      |
| email     | string  | Unique, required |
| password  | string  | Bcrypt hashed    |
| is_active | boolean | Default: true    |

### Task

| Field       | Type    | Notes                         |
|-------------|---------|-------------------------------|
| id          | integer | Primary key                   |
| title       | string  | Required, 2-100 characters    |
| description | string  | Optional                      |
| status      | enum    | `todo`, `in_progress`, `done` |
| due_date    | date    | Optional                      |
| user_id     | integer | Foreign key to users (owner)  |
| tags        | list    | Many-to-many via `task_tags`  |

### Tag

| Field | Type    | Notes        |
|-------|---------|--------------|
| id    | integer | Primary key  |
| name  | string  | Unique       |

Tags are shared across all users. When creating or updating a task, tags are automatically created if they do not already exist.

---

## Interactive Docs

FastAPI provides auto-generated interactive documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
