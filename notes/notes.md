# Task Manager API - Full Project Notes

## Project Purpose

A production-structured REST API where users register, log in, and manage only their own tasks. Consolidates: PostgreSQL, SQLAlchemy ORM, JWT authentication, Pydantic v2 validation, ownership-based access control, pagination, filtering, tags with many-to-many relationships, and global error handling.

---

## Project Structure

```
task_manager_api/
├── main.py
├── config.py
├── .env
├── .gitignore
├── requirements.txt
└── app/
    ├── database.py
    ├── utils.py
    ├── models/
    │   ├── __init__.py
    │   ├── users.py
    │   ├── tasks.py
    │   └── tags.py
    ├── schemas/
    │   ├── __init__.py
    │   ├── users.py
    │   └── tasks.py
    ├── crud/
    │   ├── __init__.py
    │   ├── users.py
    │   └── tasks.py
    └── routers/
        ├── __init__.py
        ├── users.py
        └── tasks.py
```

---

## Endpoints

| Method | Route | Auth Required | Description |
|--------|-------|---------------|-------------|
| POST | `/users/register` | No | Register a new user |
| POST | `/users/login` | No | Login, returns JWT |
| GET | `/users/me` | Yes | Get current user info |
| GET | `/tasks/` | Yes | List own tasks (paginated, filterable) |
| POST | `/tasks/` | Yes | Create a new task |
| GET | `/tasks/{task_id}` | Yes | Fetch a single task (ownership check) |
| PUT | `/tasks/{task_id}` | Yes | Update a task (ownership check) |
| DELETE | `/tasks/{task_id}` | Yes | Delete a task (ownership check) |

---

## Task Fields

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | integer | primary key, auto |
| `title` | string | required, 2-100 chars |
| `description` | string | optional |
| `status` | enum | `todo`, `in_progress`, `done` (default: `todo`) |
| `due_date` | date | optional |
| `user_id` | integer | FK to users, set from JWT (never from client) |
| `tags` | list[str] | optional, many-to-many via `task_tags` table |

---

## Configuration

**`.env`**
```
DATABASE_URL=postgresql://mac@localhost/task_manager_db
SECRET_KEY=your_super_secret_key_min_32_characters
```

**`config.py`**
```python
from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    model_config = {"env_file": str(BASE_DIR / ".env")}

setting = Settings()
```

`BASE_DIR` anchors the `.env` path to the project root regardless of where you run the server from. `pydantic-settings` reads `.env` automatically and validates types on startup - if a required variable is missing, it crashes immediately with a clear error rather than silently failing later.

---

## Database Setup

**`app/database.py`**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import setting

engine = create_engine(setting.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`get_db` is a FastAPI dependency that yields one DB session per request and closes it in the `finally` block regardless of whether the request succeeds or raises an exception. `autocommit=False` means you must call `db.commit()` explicitly - nothing is written to the DB until you do.

---

## Models

### `app/models/users.py`
```python
from __future__ import annotations
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    tasks = relationship("Task", back_populates="owner")
```

### `app/models/tasks.py`
```python
from __future__ import annotations
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Enum
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.todo, nullable=False)
    due_date = Column(Date, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    owner = relationship("User", back_populates="tasks")
    tags = relationship("Tag", secondary="task_tags", back_populates="tasks")
```

### `app/models/tags.py`
```python
from __future__ import annotations
from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE")),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"))
)

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    tasks = relationship("Task", secondary=task_tags, back_populates="tags")
```

### Why `TaskStatus(str, enum.Enum)`?

Inheriting from `str` makes enum values behave as plain strings everywhere - JSON serialization, SQLAlchemy comparisons, and Pydantic validation all work without extra configuration. Without `str`, you'd need custom serializers.

### Why `from __future__ import annotations`?

Allows forward references in type hints. SQLAlchemy relationships reference model names as strings (`"Task"`, `"Tag"`) which resolves circular import issues between model files.

### Many-to-Many: How It Works

A task can have many tags. A tag can belong to many tasks. A direct FK on either table can't represent this - you need a third table (`task_tags`) that holds pairs of `(task_id, tag_id)`.

```
tasks          task_tags         tags
-----          ---------         ----
id   <----     task_id           id
title          tag_id    ---->   name
...
```

SQLAlchemy handles this with the `secondary` argument on `relationship`. You never interact with `task_tags` directly - SQLAlchemy inserts and deletes rows in it automatically when you assign `task.tags = [tag1, tag2]`.

`ondelete="CASCADE"` on both FKs means if a task or tag is deleted, the corresponding rows in `task_tags` are cleaned up automatically at the DB level.

---

## Schemas

### `app/schemas/users.py`
```python
from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    class Config:
        from_attributes = True
```

### `app/schemas/tasks.py`
```python
from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from app.models.tasks import TaskStatus

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.todo
    due_date: Optional[date] = None
    tags: list[str] = []

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[date] = None
    tags: Optional[list[str]] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    due_date: Optional[date]
    user_id: int
    tags: list[str] = []

    @classmethod
    def model_validate(cls, obj, **kwargs):
        return cls(
            id=obj.id,
            title=obj.title,
            description=obj.description,
            status=obj.status,
            due_date=obj.due_date,
            user_id=obj.user_id,
            tags=[tag.name for tag in obj.tags]
        )

    class Config:
        from_attributes = True
```

### Why all fields are `Optional` in `TaskUpdate`?

Partial update pattern. The client only sends fields they want to change. The CRUD layer checks `if field is not None` and skips unchanged fields. If you made all fields required, every PUT request would need to resend the entire object even to change one field.

### Why `tags: list[str]` in `TaskResponse` needs a custom `model_validate`?

The ORM returns `Task.tags` as a list of `Tag` objects, not strings. Pydantic can't automatically convert `[Tag(id=1, name="work")]` to `["work"]`. The override extracts `.name` from each `Tag` object before constructing the response. Without this, `model_validate` either fails or returns wrong data.

### `from_attributes = True`

Tells Pydantic to read data from ORM object attributes (e.g. `task.title`) instead of expecting a dictionary. Required whenever you pass a SQLAlchemy model instance directly to a Pydantic schema.

---

## Auth Utilities

**`app/utils.py`**
```python
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.crud.users import get_user_by_email
from app.database import get_db
from config import setting

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, setting.SECRET_KEY, algorithm="HS256")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, setting.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    email = payload.get("sub")
    if email is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return get_user_by_email(email, db)
```

### JWT Flow

```
Register/Login
    -> password hashed with bcrypt
    -> JWT created: {"sub": email, "exp": now + 30min}
    -> signed with SECRET_KEY using HS256
    -> returned to client as {"access_token": "...", "token_type": "bearer"}

Protected Request
    -> client sends: Authorization: Bearer <token>
    -> OAuth2PasswordBearer extracts the token
    -> jwt.decode() verifies signature and expiry
    -> email extracted from "sub" claim
    -> user fetched from DB and injected into the route
```

### `datetime.now(timezone.utc)` vs `datetime.utcnow()`

`datetime.utcnow()` is deprecated in Python 3.12+. It returns a naive datetime (no timezone info) which causes warnings with newer `jose` versions. `datetime.now(timezone.utc)` returns a timezone-aware datetime and is the correct modern approach.

### `OAuth2PasswordBearer(tokenUrl="/users/login")`

Tells FastAPI's Swagger docs where the login endpoint is so it can auto-populate the Authorize button. The `tokenUrl` doesn't affect actual token validation - that happens in `jwt.decode()`.

---

## CRUD Layer

### `app/crud/users.py`
```python
from sqlalchemy.orm import Session
from app.models.users import User
from app.schemas.users import UserCreate

def get_user_by_email(email: str, db: Session):
    return db.query(User).filter(User.email == email).first()

def create_user(user: UserCreate, db: Session):
    new_user = User(email=user.email, password=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
```

### `app/crud/tasks.py`
```python
from sqlalchemy.orm import Session
from app.models.tasks import Task
from app.models.tags import Tag
from app.schemas.tasks import TaskCreate, TaskUpdate

def get_all_tasks(db: Session, user_id: int, page: int = 1, size: int = 10, search: str = "", status: str = None):
    query = db.query(Task).filter(Task.user_id == user_id)
    if search:
        query = query.filter(Task.title.ilike(f"%{search}%"))
    if status:
        query = query.filter(Task.status == status)
    total = query.count()
    results = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "results": results}

def get_task_by_id(task_id: int, db: Session):
    return db.query(Task).filter(Task.id == task_id).first()

def _get_or_create_tags(db: Session, tag_names: list[str]) -> list[Tag]:
    tags = []
    for name in set(tag_names):
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags

def create_task(task: TaskCreate, db: Session, user_id: int):
    new_task = Task(
        title=task.title,
        description=task.description,
        status=task.status,
        due_date=task.due_date,
        user_id=user_id
    )
    db.add(new_task)
    db.flush()  # assigns new_task.id without committing
    if task.tags:
        tags = _get_or_create_tags(db, task.tags)
        new_task.tags = tags
    db.commit()
    db.refresh(new_task)
    return new_task

def update_task(task_id: int, task: TaskUpdate, db: Session):
    existing = get_task_by_id(task_id, db)
    if existing is None:
        return None
    if task.title is not None:
        existing.title = task.title
    if task.description is not None:
        existing.description = task.description
    if task.status is not None:
        existing.status = task.status
    if task.due_date is not None:
        existing.due_date = task.due_date
    if task.tags is not None:
        tags = _get_or_create_tags(db, task.tags)
        existing.tags = tags
    db.commit()
    db.refresh(existing)
    return existing

def delete_task(task_id: int, db: Session):
    existing = get_task_by_id(task_id, db)
    db.delete(existing)
    db.commit()
```

### `db.flush()` vs `db.commit()`

`db.flush()` sends the SQL to the database within the current transaction but does NOT commit. The row gets an auto-generated `id` (because PostgreSQL assigns it on insert) but the change is not permanent yet. This is why `flush()` is used before assigning tags - the task needs an `id` so SQLAlchemy can populate the `task_tags` join table correctly. `db.commit()` then makes everything permanent in one atomic operation.

### `_get_or_create_tags` Pattern

Tags are shared across tasks and must be unique by name. This function:
1. Uses `set(tag_names)` to deduplicate the incoming list
2. For each name, checks if a tag with that name already exists
3. Creates it if not, then flushes so it gets an `id`
4. Returns the full list of `Tag` objects

When you then do `new_task.tags = tags`, SQLAlchemy automatically inserts the correct rows into `task_tags`. You never write to `task_tags` directly.

### Pagination

```
page=1, size=10  ->  offset(0).limit(10)   ->  rows 1-10
page=2, size=10  ->  offset(10).limit(10)  ->  rows 11-20
page=3, size=10  ->  offset(20).limit(10)  ->  rows 21-30

Formula: offset = (page - 1) * size
```

`total = query.count()` runs before `.offset().limit()` so it counts all matching rows, not just the current page. This lets the client calculate total pages.

### `ilike` for Search

`ilike(f"%{search}%")` is a case-insensitive SQL LIKE query. `%` is a wildcard matching any sequence of characters. So `ilike("%auth%")` matches "auth", "Authentication", "OAuth2", etc.

---

## Routers

### `app/routers/users.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.crud.users import create_user, get_user_by_email
from app.database import get_db
from app.schemas.users import UserCreate, UserResponse
from app.utils import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/register", response_model=UserResponse)
def registration(user: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(user.email, db):
        raise HTTPException(status_code=400, detail="Email already registered")
    user.password = hash_password(user.password)
    return create_user(user, db)

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_by_email(form_data.username, db)
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_user)):
    return current_user
```

### `app/routers/tasks.py`
```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.crud.tasks import create_task, delete_task, get_all_tasks, get_task_by_id, update_task
from app.database import get_db
from app.schemas.tasks import TaskCreate, TaskResponse, TaskUpdate
from app.utils import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/", response_model=dict)
def list_tasks(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    search: str = Query(default=""),
    status: str = Query(default=None)
):
    data = get_all_tasks(db, current_user.id, page, size, search, status)
    return {
        "total": data["total"],
        "page": data["page"],
        "size": data["size"],
        "results": [TaskResponse.model_validate(t) for t in data["results"]]
    }

@router.get("/{task_id}", response_model=TaskResponse)
def fetch_task(task_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    task = get_task_by_id(task_id, db)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return task

@router.post("/", status_code=201, response_model=TaskResponse)
def add_task(task: TaskCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return create_task(task, db, current_user.id)

@router.put("/{task_id}", response_model=TaskResponse)
def edit_task(task_id: int, task: TaskUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    existing = get_task_by_id(task_id, db)
    if existing is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if existing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return update_task(task_id, task, db)

@router.delete("/{task_id}")
def remove_task(task_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    existing = get_task_by_id(task_id, db)
    if existing is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if existing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    delete_task(task_id, db)
    return {"message": "Task deleted"}
```

### Ownership Check Pattern

Every single-task endpoint follows the same two-step pattern:

```
1. Check existence  ->  404 if not found
2. Check ownership  ->  403 if wrong user
```

Order matters. If you check ownership on `None`, you get `AttributeError: 'NoneType' object has no attribute 'user_id'` instead of a clean HTTP error. Always 404 before 403.

---

## Main Entry Point

**`main.py`**
```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.database import Base, engine
from app.models.users import User
from app.models.tasks import Task
from app.models.tags import Tag, task_tags
from app.routers.users import router as users_router
from app.routers.tasks import router as tasks_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(users_router)
app.include_router(tasks_router)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"status": "error", "message": "Invalid input"})

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"status": "error", "message": exc.detail})
```

### Why models are imported explicitly in `main.py`

`Base.metadata.create_all(bind=engine)` only creates tables for models that Python has already imported. If `User`, `Task`, `Tag`, and `task_tags` haven't been imported before `create_all` runs, their tables won't exist. The explicit imports guarantee all models are registered in `Base.metadata` before table creation runs.

### Global Error Handlers

Instead of FastAPI's default error format, both handlers return:
```json
{"status": "error", "message": "..."}
```

This gives every error response - validation failures and HTTP exceptions alike - a consistent shape that clients can rely on.

---

## Requirements

```
fastapi==0.115.0
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
psycopg2-binary==2.9.10
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pydantic==2.9.2
pydantic-settings==2.5.2
python-multipart==0.0.12
alembic==1.13.3
bcrypt==4.0.1
```

Note: `psycopg2-binary` is fine for local development. In production, use `psycopg2` (compiled from source, more stable).

---

## Running the App

```bash
# Create the database
psql postgres -c "CREATE DATABASE task_manager_db;"

# Install dependencies
pip install -r requirements.txt

# Start the server
python3 -m uvicorn main:app --reload
```

API docs: `http://127.0.0.1:8000/docs`

---

## Core Mental Models

| Concept | Rule |
|---------|------|
| `TaskStatus(str, enum.Enum)` | Inheriting from `str` makes enum values JSON-serializable strings. Without it, serialization breaks. |
| `TaskUpdate` all Optional | Partial update pattern. Skip fields that are `None` in the CRUD layer. |
| Pagination offset formula | `offset = (page - 1) * size` |
| `ilike("%search%")` | Case-insensitive SQL LIKE. `%` wildcards on both sides match anywhere in the string. |
| 404 before 403 | Always check existence before checking ownership. Ownership check on `None` crashes. |
| `user_id` from token | Never trust `user_id` from the request body. Always pull it from `get_current_user`. |
| Models imported in `main.py` | Required for `create_all` to know about the tables. |
| `db.flush()` before tags | Assigns the task an `id` without committing, so `task_tags` rows can reference it. |
| `_get_or_create_tags` | Tags are global and reusable. Check first, create only if missing. Use `set()` to deduplicate input. |
| Many-to-many via `secondary` | SQLAlchemy manages `task_tags` rows automatically when you assign `task.tags = [...]`. |
| `from_attributes = True` | Lets Pydantic read from ORM object attributes instead of requiring a dict. |
| `model_validate` override on `TaskResponse` | Needed because `task.tags` returns `Tag` objects, not strings. Manual extraction via `[tag.name for tag in obj.tags]`. |
| `datetime.now(timezone.utc)` | Use this instead of deprecated `datetime.utcnow()` for JWT expiry. |