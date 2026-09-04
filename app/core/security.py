import logging
from fastapi import Security, HTTPException, Request, status
from fastapi.security.api_key import APIKeyHeader
from app.core.key_manager import hash_api_key

logger = logging.getLogger("NeuralDivergent.Security")

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_nd_api_key(
    request: Request, 
    api_key: str = Security(api_key_header)
) -> str:
    """
    Validates incoming 'X-API-Key' header:
    1. Checks if header exists.
    2. Hashes key and queries graph/database.
    3. Confirms key is active.
    4. Attaches user_id to request state and returns user_id.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing 'X-API-Key' header in request."
        )

    graph_manager = getattr(request.app.state, "graph_manager", None)
    if not graph_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication engine database connection unavailable."
        )

    key_hash = hash_api_key(api_key)

    # Cypher query to locate active developer key node
    cypher = """
    MATCH (u:Developer)-[:HAS_KEY]->(k:NDKey {key_hash: $key_hash})
    WHERE k.is_active = true
    SET k.last_used_at = datetime()
    RETURN u.id AS user_id, u.email AS email, k.label AS key_label
    """
    try:
        results = graph_manager.execute_write(cypher, {"key_hash": key_hash})
        if not results:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or revoked ND API Key."
            )
        
        user_data = results[0]
        # Attaching authenticated context to Request state for downstream routes
        request.state.user_id = user_data["user_id"]
        request.state.developer_email = user_data["email"]
        
        return user_data["user_id"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during ND API key verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal authentication failure."
        )