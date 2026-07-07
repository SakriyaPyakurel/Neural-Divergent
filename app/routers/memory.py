from fastapi import APIRouter,Request,HTTPException,Query
from typing import List,Dict,Any
from app.models.schemas import IngestRequest,CognitiveIngestResponse

import logging

logger = logging.getLogger(__name__)

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