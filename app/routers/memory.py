from fastapi import APIRouter,Request,HTTPException,Query
from typing import List,Dict,Any
from app.models.schemas import IngestRequest,CognitiveIngestResponse

import logging

logger = logging.getLogger('NeuralDivergent.memory_router')

memory_router = APIRouter(
    prefix="/api/v1/memory",
    tags = ["Cognitive Memory Engine"] 
)

@memory_router.post("/ingest", response_model=CognitiveIngestResponse)
async def ingest_information(
    payload: IngestRequest,
    request: Request  # Injecting the raw request to access app.state
):
    """
    Ingests natural language, extracts semantic triples, evaluates importance, 
    and commits valuable data to the memory graph.
    """
    # Retrieving the pre-loaded orchestrator from the application state
    orchestrator = request.app.state.orchestrator
    
    try:
        # Running the pipeline
        raw_ledger = orchestrator.process_utterance(
            text=payload.text,
            active_contexts=payload.active_contexts
        )
        
        # Calculating high-level metrics for the API response
        stored = sum(1 for item in raw_ledger if item["action"] in ["NEW", "REINFORCED", "SUPERSEDED"])
        ignored = sum(1 for item in raw_ledger if item["action"] == "IGNORED")

        # Packagaging the raw dictionary results into the Pydantic schema
        return CognitiveIngestResponse(
            source_text=payload.text,
            processed_count=len(raw_ledger),
            stored_count=stored,
            ignored_count=ignored,
            results=raw_ledger 
        )

    except Exception as e:
        logger.error(f"Pipeline crashed during ingestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="The cognitive pipeline encountered an internal error.")
        

@memory_router.get("/active",response_model=List[Dict[str,Any]])
async def get_active_truth(request:Request, subject: str = Query(...,example="user"),predicate: str= Query(...,example="primary_category")):
    """
    Queries the current state of truth (active memories) for a subject-predicate relation.
    Example: Find what the user's active programming language is.
    """
    db = request.app.state.db 
    try:
        records = db.find_by_subject_and_predicate(subject.strip(),predicate.strip().lower()) 
        return records 
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    
@memory_router.get("/related/{subject}",response_model=List[Dict[str,Any]])
async def get_related_memories(request:Request, subject:str):
    """
    Graph Traversal equivalent. Retrieves all active properties and relationships
    originating from a target subject node.
    """
    db = request.app.state.db 
    try:
        records = db.find_related_memories(subject.strip())
        return records 
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    
@memory_router.get("/search")
async def search_cognitive_memory(
    request:Request,
    q:str=Query(...,description="The concept,entity or keyword to search."),
    limit:int = Query(10,description="Maximum number of memories to retrieve.")
):
    """
    Query the cognitive memory graph. Returns a ranked list of relevant
    memories balancing importance,confidence,reinforcement strength and recency.
    """
    if not q.strip():
        raise HTTPException(status_code=400,detail="Search query cannot be empty.") 
    
    # Grabbing the database connection from application state 
    db = request.app.state.db 

    try:
        # Executing the ranked memory search
        results = db.search_ranked_memories(search_term=q,limit=limit) 

        return {
            "query":q,
            "total_found":len(results),
            "results":results
        }
    except Exception as e:
        logger.error(f"Failed to search memories: {str(e)}",exc_info=True)
        raise HTTPException(status_code=500,detail="Internal Search error.")
    
@memory_router.get("/traverse") 
async def traverse_graph(
    request:Request,
    entity:str = Query(...,description="The root entity to start the traversal from (e.g. 'User' or 'Python')"),
    limit:int = Query(15,description="Maximum number of nodes to return in the web.") 
):
    """
    Performs an associative cognitive graph traversal.
    Returns direct matches (Depth 0) and related associative memories (Depth 1) 
    ranked by human-like cognitive priority
    """
    if not entity.strip():
        raise HTTPException(status_code=400,detail="Root entity cannot be empty.") 
    
    db = request.app.state.db 

    try:
        results = db.traverse_memory_graph(root_entity=entity,limit=limit) 

        return {
            "root_entity":entity,
            "total_nodes":len(results),
            "graph":results
        }
    except Exception as e:
        logger.error(f"Failed to traverse graph: {str(e)}",exc_info=True) 
        raise HTTPException(status_code=500,detail="Memory Traversal Error.")