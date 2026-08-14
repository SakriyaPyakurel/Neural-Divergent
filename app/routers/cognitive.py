from fastapi import APIRouter,Request,HTTPException 
import logging
from app.models.schemas import CompressionRequest,CompressionResponse
from app.services.context_compressor import ContextCompressor 

logger = logging.getLogger("NeuralDivergent.CognitiveRouter") 

cognitive_router = APIRouter(
    prefix="/cognitive",
    tags=["Cognitive Context"]
)

@cognitive_router.post('/compress',response_model=CompressionResponse) 
async def compress_context_for_llm(payload:CompressionRequest,request:Request):
    """
    Receives raw conversation history & query entities, pulls active graph memory,
    and returns a compressed context package along with token reduction metrics.
    """
    graph_manager = getattr(request.app.state, "graph_manager", None)
    if not graph_manager:
        logger.error("Graph Manager is not initialized on app.state.")
        raise HTTPException(status_code=500, detail="Graph Database is not initialized.")

    try:
        # Initializing the compressor 
        compressor = ContextCompressor(graph_manager=graph_manager)

        # Fetching relevant graph neighborhood deterministically
        subgraph_records = compressor.extract_active_subgraph(
            entities=payload.target_entities,
            max_hops=payload.max_hops,
            limit=payload.limit
        )

        # Serializing graph into hyper-compact context
        dense_context = compressor.serialize_to_dense_dsl(subgraph_records)

        # Calculating Token Savings
        metrics = compressor.compute_compression(
            raw_history=payload.raw_history, 
            compressed_context=dense_context
        )

        return CompressionResponse(
            compressed_context=dense_context,
            metrics=metrics
        )
    
    except Exception as e:
        logger.error(f"Compression failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))