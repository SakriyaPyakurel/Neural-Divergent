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

@graph_router.get("/visualize")
async def get_graph_visualization_data(request: Request, limit: int = 150):
    """
    Pulls a snapshot of the graph formatted specifically for frontend 
    graph visualization libraries (like React Force Graph or D3.js).
    """
    graph_manager = getattr(request.app.state, "graph_manager", None)
    if not graph_manager:
        raise HTTPException(status_code=500, detail="Graph Database is not initialized.")

    # Query pulls active edges and their connected nodes
    query = """
    MATCH (s)-[r]->(o)
    WHERE r.is_active = true
    RETURN 
        s.name AS source, labels(s)[0] AS source_label,
        type(r) AS relationship, properties(r) AS rel_props,
        o.name AS target, labels(o)[0] AS target_label
    LIMIT $limit
    """
    
    try:
        records = graph_manager.execute_read(query, {"limit": limit})
        
        nodes_dict = {}
        links = []
        
        for record in records:
            # Building unique nodes
            source_id = record["source"]
            target_id = record["target"]
            
            if source_id not in nodes_dict:
                nodes_dict[source_id] = {"id": source_id, "label": record["source_label"]}
            if target_id not in nodes_dict:
                nodes_dict[target_id] = {"id": target_id, "label": record["target_label"]}
                
            # Building the links (edges)
            links.append({
                "source": source_id,
                "target": target_id,
                "label": record["relationship"],
                "reinforcement_count": record["rel_props"].get("reinforcement_count", 1),
                "importance": record["rel_props"].get("importance_score", 0.0),
                "memory_id": record["rel_props"].get("sqlite_id")
            })
            
        return {
            "nodes": list(nodes_dict.values()),
            "links": links
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch visualization data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@graph_router.get("/subject/{name}")
async def get_subject_network(name: str, request: Request):
    """
    Looks up a specific subject (e.g., 'user') and gets all of their immediate connections.
    """
    graph_manager = getattr(request.app.state, "graph_manager", None)
    if not graph_manager:
        raise HTTPException(status_code=500, detail="Graph Database is not initialized.")

    query = """
    MATCH (s:Subject {name: $name})-[r]->(o)
    WHERE r.is_active = true
    RETURN type(r) AS predicate, o.name AS object, properties(r) AS properties
    ORDER BY properties.importance_score DESC
    """
    
    try:
        records = graph_manager.execute_read(query, {"name": name.strip()})
        return {"subject": name, "connections": records}
    except Exception as e:
        logger.error(f"Failed to fetch subject network for {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))