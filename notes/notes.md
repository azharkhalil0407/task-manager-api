# Task Manager Project — Full Implementation Notes

---

## Project Purpose

Users register and log in, then manage only their own tasks. This project consolidates everything covered so far: PostgreSQL, SQLAlchemy relationships, JWT authentication, Pydantic validation, ownership checks, pagination, filtering, and global error handling — all in a single production-structured application.

---

## Task Fields

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | integer | primary key |
| `title` | string | required, 2–100 chars |
| `description` | string | optional |
| `status` | enum | `todo`, `in_progress`, `done` (default: `todo`) |
| `due_date` | date | optional |
| `user_id` | integer | foreign key to users |

---

## Endpoints

**Users**
- `POST /users/register`
- `POST /users/login`
- `GET /users/me`

**Tasks** (all require JWT authentication)
- `GET /tasks/` — list own tasks (pagination, search by title, filter by status)
- `POST /tasks/` — create task
- `GET /tasks/{task_id}` — get one task (ownership check)
- `PUT /tasks/{task_id}` — update task (ownership check)
- `DELETE /tasks/{task_id}` — delete task (ownership check)

**Rules:**
- All task endpoints require authentication via JWT
- Single-task endpoints check ownership — a user cannot access another user's task
- Consistent error format: `{"status": "error", "message": "..."}`
- No Alembic — use `Base.metadata.create_all`

---

## Project Structure

```
projectx/
├── main.py
├── config.py
├── .env
├── .gitignore
├── requirements.txt
└── app/
    ├── database.py
    ├── utils.py
    ├── dependencies.py
    ├── models/
    │   ├── __init__.py
    │   ├── users.py
    │   └── tasks.py
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

## Configuration

**.env**

```
DATABASE_URL=postgresql://mac@localhost/task_manager_db
SECRET_KEY=mysupersecretkey123
```

**config.py**

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

`BASE_DIR` points to the project root so the `.env` file is always found regardless of where you run the app from.

---

## Database Setup

**app/database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import setting

engine = create_engine(setting.DATABASE_URL)
sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

**app/dependencies.py**

```python
from app.database import sessionLocal

def get_db():
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## Utils — Auth Helpers

**app/utils.py**

```python
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.crud.users import get_user_by_email
from app.dependencies import get_db
from config import setting

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
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

---

## Models

**app/models/users.py**

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

**app/models/tasks.py**

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
```

**Why `TaskStatus(str, enum.Enum)`?**
Inheriting from `str` means the enum values are valid JSON strings. Without `str`, SQLAlchemy and Pydantic would struggle to serialize the enum for API responses.

---

## Schemas

**app/schemas/users.py**

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

**app/schemas/tasks.py**

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

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[date] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    due_date: Optional[date]
    user_id: int
    class Config:
        from_attributes = True
```

**Why all fields are `Optional` in `TaskUpdate`?**
A PUT request for partial updates should not require every field. If a field is `None`, the CRUD layer skips it. This pattern is called a partial update.

---

## CRUD

**app/crud/users.py**

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

**app/crud/tasks.py**

```python
from sqlalchemy.orm import Session
from app.models.tasks import Task
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

def create_task(task: TaskCreate, db: Session, user_id: int):
    new_task = Task(
        title=task.title,
        description=task.description,
        status=task.status,
        due_date=task.due_date,
        user_id=user_id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

def update_task(task_id: int, task: TaskUpdate, db: Session):
    existing = get_task_by_id(task_id, db)
    if task.title is not None: existing.title = task.title
    if task.description is not None: existing.description = task.description
    if task.status is not None: existing.status = task.status
    if task.due_date is not None: existing.due_date = task.due_date
    db.commit()
    db.refresh(existing)
    return existing

def delete_task(task_id: int, db: Session):
    existing = get_task_by_id(task_id, db)
    db.delete(existing)
    db.commit()
```

**How pagination works:**
- `page=1, size=10` → `offset(0).limit(10)` → rows 1–10
- `page=2, size=10` → `offset(10).limit(10)` → rows 11–20
- Formula: `offset = (page - 1) * size`

**How `ilike` works:**
`ilike(f"%{search}%")` is a case-insensitive LIKE query. `%` is a wildcard — matches anything before or after the search term.

---

## Routers

**app/routers/users.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.crud.users import create_user, get_user_by_email
from app.dependencies import get_db
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

**app/routers/tasks.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.crud.tasks import create_task, delete_task, get_all_tasks, get_task_by_id, update_task
from app.dependencies import get_db
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

**Ownership check pattern:**
Every single-task endpoint follows the same two-step pattern: check existence first (404), then check ownership (403). Order matters — if you check ownership on a `None` object, you get an `AttributeError`, not a clean HTTP error.

---

## Main Entry Point

**main.py**

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.database import Base, engine
from app.models.users import User
from app.models.tasks import Task
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

**Why models are imported explicitly in main.py:**
`Base.metadata.create_all` only knows about models that have been imported. If `User` and `Task` are not imported before `create_all` runs, their tables will not be created.

---

## Running the Application

```bash
# Create the database
psql postgres -c "CREATE DATABASE task_manager_db;"

# Install dependencies (bcrypt version matters)
pip install bcrypt==4.0.1

# Start the server
python3 -m uvicorn main:app --reload
```

API docs available at `http://127.0.0.1:8000/docs`

---

## Requirements

**requirements.txt**

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
bcrypt==4.0.1
```

**.gitignore**

```
venv/
__pycache__/
*.pyc
.env
```

---

## Core Mental Models

```
TaskStatus(str, enum.Enum)   = enum values are JSON-serializable strings.
TaskUpdate all Optional      = partial update pattern. Skip fields that are None.
Pagination offset formula    = (page - 1) * size.
ilike("%search%")            = case-insensitive SQL LIKE. Wildcards on both sides.
404 before 403               = always check existence before checking ownership.
user_id from token           = never from the client. Always from get_current_user.
models imported in main.py   = required for create_all to know about the tables.
```