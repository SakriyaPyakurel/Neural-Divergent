from fastapi import APIRouter,HTTPException,Request
import logging

logger = logging.getLogger("NeuralDivergent.GraphRouter")

# Initialize the router for the cognitive graph
graph_router = APIRouter(
    prefix="/api/v1/graph",
    tags=["Cognitive Memory Graph"]
)

@graph_router.get("/stats")
async def get_graph_stats(request: Request):
    """
    Returns the total number of nodes and cognitive relationships in Neo4j.
    """
    graph_manager = getattr(request.app.state, "graph_manager", None)
    if not graph_manager:
        raise HTTPException(status_code=500, detail="Graph Database is not initialized.")

    query = """
    MATCH (n) WITH count(n) as node_count
    MATCH ()-[r]->() RETURN node_count, count(r) as edge_count
    """
    
    try:
        results = graph_manager.execute_read(query)
        if results:
            return {
                "nodes": results[0]["node_count"],
                "edges": results[0]["edge_count"]
            }
        return {"nodes": 0, "edges": 0}
    except Exception as e:
        logger.error(f"Failed to fetch graph stats: {e}")
        raise HTTPException(status_code=500, detail="Error querying Graph DB.")