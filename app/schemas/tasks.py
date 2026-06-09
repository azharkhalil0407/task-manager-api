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