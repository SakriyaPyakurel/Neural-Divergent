from fastapi import APIRouter, Depends, HTTPException, Request, status
import urllib.parse

from app.core.security import verify_nd_api_key
from app.models.goal_schemas import (
    GoalCreateRequest, 
    GoalResponse, 
    GoalListResponse, 
    StandardActionResponse,
    TaskUpdateRequest
)
from app.services.goal_planner import GoalPlanner

goals_router = APIRouter(
    prefix="/api/v1/goals",
    tags=["Cognitive Goals"],
    dependencies=[Depends(verify_nd_api_key)]
)

def get_planner(request: Request) -> GoalPlanner:
    """Dependency to inject the GoalPlanner service."""
    graph_manager = getattr(request.app.state, "graph_manager", None)
    if not graph_manager:
        raise HTTPException(status_code=500, detail="Database not initialized.")
    return GoalPlanner(graph_manager)

@goals_router.post("/", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(payload: GoalCreateRequest, planner: GoalPlanner = Depends(get_planner)):
    result = planner.register_goal(payload.user_id, payload.goal_name, payload.subtasks)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create goal in graph.")
    return result

@goals_router.get("/user/{user_id}", response_model=GoalListResponse)
async def get_goals(user_id: str, planner: GoalPlanner = Depends(get_planner)):
    # URL decode in case spaces or special characters exist in user_id
    decoded_user_id = urllib.parse.unquote(user_id)
    goals = planner.get_user_goals(decoded_user_id)
    return GoalListResponse(user_id=decoded_user_id, goals=goals)

@goals_router.patch("/tasks/{task_name}", response_model=StandardActionResponse)
async def update_task_status(
    task_name: str, 
    payload: TaskUpdateRequest, 
    planner: GoalPlanner = Depends(get_planner)
):
    # Decoding task_name for graph injection
    decoded_task_name = urllib.parse.unquote(task_name)

    if payload.status.upper() != "COMPLETED":
        raise HTTPException(status_code=400, detail="Currently only 'COMPLETED' status updates are supported.")
        
    success = planner.mark_task_complete(decoded_task_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Task '{decoded_task_name}' not found or failed to update.")
        
    return StandardActionResponse(
        status="success", 
        message=f"Task '{decoded_task_name}' marked as complete. Parent goal evaluated."
    )
