from fastapi import APIRouter,Request,HTTPException,Query
from typing import List,Dict,Any
from models.schemas import IngestRequest,ProcessedTripleResponse,CognitiveIngestResponse

memory_router = APIRouter(
    prefix="/api/v1/memory",
    tags = ["Cognitive Memory Engine"] 
)

@memory_router.post("/ingest",response_model=CognitiveIngestResponse)
async def ingest_conversation(request: Request,payload: IngestRequest):
    """
    Ingest a raw conversational utterance
    """
    orchestrator = request.app.state.orchestrator
    try:
        results = orchestrator.process_utterance(
            text=payload.text,
            active_contexts = payload.active_contexts
        )
        return CognitiveIngestResponse(
            utterance=payload.text,
            processed_count=len(results),
            results=[
                ProcessedTripleResponse(
                    triple=list(r["triple"]),
                    action=r["action"],
                    memory_id=r.get("memory_id"),
                    importance_prior=r["importance_prior"],
                    retention_policy=r["retention_policy"] 
                    ) for r in results  
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Error in pipeline: {str(e)}")

@memory_router.get("/active",response_model=List[Dict[str,Any]])
async def get_active_truth(request:Request, subject: str = Query(...,example="user"),predicate: str= Query(...,example="favorite_language")):
    """
    Queries the current state of truth (active memories) for a subject-predicate relation.
    Example: Find what the user's active programming language is.
    """
    db = request.state.db 
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
    db = request.state.db 
    try:
        records = db.find_related_memories(subject.strip())
        return records 
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))