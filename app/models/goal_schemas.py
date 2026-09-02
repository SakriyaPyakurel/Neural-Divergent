from pydantic import BaseModel, Field
from typing import List, Optional

# --- Requests ---
class GoalCreateRequest(BaseModel):
    user_id: str = Field(..., description="The ID of the user creating the goal.")
    goal_name: str = Field(..., description="The high-level name or title of the goal.")
    subtasks: List[str] = Field(..., min_items=1, description="List of actionable subtasks.")

class TaskUpdateRequest(BaseModel):
    status: str = Field(..., description="New status for the task (e.g., 'COMPLETED', 'IN_PROGRESS')")

# --- Responses ---
class TaskItem(BaseModel):
    name: str
    status: str

class GoalResponse(BaseModel):
    goal_name: str
    status: str
    tasks: List[TaskItem]

class GoalListResponse(BaseModel):
    user_id: str
    goals: List[GoalResponse]

class StandardActionResponse(BaseModel):
    status: str
    message: str