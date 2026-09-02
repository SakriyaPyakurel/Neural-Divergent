import logging 
from typing import List,Dict,Any 

logger = logging.getLogger("NeuralDivergent.GoalPlanner") 

class GoalPlanner:
    def __init__(self,graph_manager):
        self.graph_manager = graph_manager 

    def register_goal(self, user_id: str, goal_name: str, subtasks: List[str]) -> Dict[str, Any]:
        cypher = """
        MERGE (u:User {id: $user_id})
        MERGE (g:Goal {name: $goal_name})
        ON CREATE SET g.status = 'IN_PROGRESS'
        MERGE (u)-[:HAS_ACTIVE_GOAL]->(g)
        
        WITH g
        UNWIND $subtasks AS task_name
        MERGE (t:Task {name: task_name})
        ON CREATE SET t.status = 'PENDING'
        MERGE (g)-[:REQUIRES_ACTION]->(t)
        
        RETURN g.name AS goal_name, g.status AS status, collect({name: t.name, status: t.status}) AS tasks
        """
        try:
            records = self.graph_manager.execute_write(cypher, {"user_id": user_id, "goal_name": goal_name, "subtasks": subtasks})
            return records[0] if records else {}
        except Exception as e:
            logger.error(f"Failed to register goal: {e}")
            return {}

    def get_user_goals(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves all goals and their nested tasks for a specific user."""
        cypher = """
        MATCH (u:User {id: $user_id})-[:HAS_ACTIVE_GOAL]->(g:Goal)
        OPTIONAL MATCH (g)-[:REQUIRES_ACTION]->(t:Task)
        RETURN g.name AS goal_name, g.status AS status, collect({name: t.name, status: coalesce(t.status, 'UNKNOWN')}) AS tasks
        """
        try:
            records = self.graph_manager.execute_read(cypher, {"user_id": user_id})
            return records if records else []
        except Exception as e:
            logger.error(f"Failed to fetch goals: {e}")
            return []

    def mark_task_complete(self, task_name: str) -> bool:
        """Updates a task's status and evaluates if the parent goal is complete."""
        cypher = """
        MATCH (t:Task {name: $task_name})
        SET t.status = 'COMPLETED'
        WITH t
        MATCH (g:Goal)-[:REQUIRES_ACTION]->(t)
        
        // Checking if all sibling tasks are completed
        OPTIONAL MATCH (g)-[:REQUIRES_ACTION]->(pending:Task) WHERE pending.status = 'PENDING'
        WITH g, count(pending) as pending_count
        
        CALL apoc.do.when(
            pending_count = 0,
            "SET g.status = 'COMPLETED' RETURN g",
            "RETURN g",
            {g: g}
        ) YIELD value
        
        RETURN true AS success
        """
        try:
            self.graph_manager.execute_write(cypher, {"task_name": task_name})
            return True
        except Exception as e:
            logger.error(f"Failed to update task state: {e}")
            return False