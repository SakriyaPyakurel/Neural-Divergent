import uuid
from datetime import datetime,timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.models.auth_schemas import (
    DeveloperRegisterRequest,
    CreateNDKeyRequest,
    NDKeyIssuedResponse,
    NDKeyMetadata
)
from typing import List
from app.core.key_manager import generate_nd_api_key
from app.core.security import verify_nd_api_key

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Developer ND Key Management"])

def get_db(request: Request):
    """Utility helper to safely fetch graph manager instance."""
    graph_manager = getattr(request.app.state, "graph_manager", None)
    if not graph_manager:
        raise HTTPException(status_code=500, detail="Database driver unavailable.")
    return graph_manager

@auth_router.post("/register", response_model=NDKeyIssuedResponse, status_code=status.HTTP_201_CREATED)
async def register_developer(payload: DeveloperRegisterRequest, request: Request):
    graph_manager = get_db(request)
    
    # Check if developer already exists
    check_cypher = "MATCH (d:Developer {email: $email}) RETURN d.id AS id"
    existing = graph_manager.execute_read(check_cypher, {"email": payload.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Developer with this email is already registered."
        )

    user_id = f"dev_{uuid.uuid4().hex[:12]}"
    key_id = f"key_{uuid.uuid4().hex[:10]}"
    raw_key, key_hash, key_prefix = generate_nd_api_key(environment="live")
    now = datetime.now(timezone.utc).isoformat()

    cypher = """
    CREATE (d:Developer {
        id: $user_id, 
        email: $email, 
        name: $name, 
        created_at: $now
    })
    CREATE (k:NDKey {
        id: $key_id,
        key_hash: $key_hash,
        prefix: $key_prefix,
        label: 'Default Initial Key',
        is_active: true,
        created_at: $now
    })
    CREATE (d)-[:HAS_KEY]->(k)
    RETURN d.id AS user_id
    """
    try:
        graph_manager.execute_write(cypher, {
            "email": payload.email, 
            "user_id": user_id, 
            "name": payload.developer_name, 
            "key_id": key_id,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "now": now
        })
        return NDKeyIssuedResponse(
            status="success",
            message="Developer registered successfully. Save your initial ND API Key now; it will not be shown again.",
            raw_nd_api_key=raw_key,
            key_label="Default Initial Key",
            key_prefix=key_prefix,
            created_at=now
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@auth_router.post("/keys/generate", response_model=NDKeyIssuedResponse)
async def issue_new_nd_key(
    payload: CreateNDKeyRequest, 
    request: Request,
    user_id: str = Depends(verify_nd_api_key)
):
    graph_manager = get_db(request)
    raw_key, key_hash, key_prefix = generate_nd_api_key(environment=payload.environment)
    key_id = f"key_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc).isoformat()

    cypher = """
    MATCH (d:Developer {id: $user_id})
    CREATE (k:NDKey {
        id: $key_id,
        key_hash: $key_hash,
        prefix: $key_prefix,
        label: $label,
        is_active: true,
        created_at: $now
    })
    CREATE (d)-[:HAS_KEY]->(k)
    RETURN k.id AS key_id
    """
    try:
        graph_manager.execute_write(cypher, {
            "user_id": user_id,
            "key_id": key_id,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "label": payload.key_label,
            "now": now
        })
        return NDKeyIssuedResponse(
            status="success",
            message="Copy your new ND API Key. It will never be shown again.",
            raw_nd_api_key=raw_key,
            key_label=payload.key_label,
            key_prefix=key_prefix,
            created_at=now
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Key generation failed: {str(e)}")

@auth_router.get("/keys", response_model=List[NDKeyMetadata])
async def list_nd_keys(
    request: Request,
    user_id: str = Depends(verify_nd_api_key)
):
    graph_manager = get_db(request)
    cypher = """
    MATCH (d:Developer {id: $user_id})-[:HAS_KEY]->(k:NDKey)
    RETURN k.id AS key_id, 
           k.label AS key_label, 
           k.prefix AS key_prefix, 
           k.is_active AS is_active, 
           k.created_at AS created_at,
           k.last_used_at AS last_used_at
    ORDER BY k.created_at DESC
    """
    results = graph_manager.execute_read(cypher, {"user_id": user_id})
    formatted_keys = []
    for record in results:
        data = dict(record)
        
        # Converting Neo4j/datetime objects to strings if present
        if data.get("last_used_at") is not None:
            data["last_used_at"] = str(data["last_used_at"])
        if data.get("created_at") is not None:
            data["created_at"] = str(data["created_at"])
            
        formatted_keys.append(NDKeyMetadata(**data))

    return formatted_keys

@auth_router.delete("/keys/{key_id}")
async def revoke_nd_key(
    key_id: str, 
    request: Request, 
    user_id: str = Depends(verify_nd_api_key)
):
    graph_manager = get_db(request)
    cypher = """
    MATCH (d:Developer {id: $user_id})-[:HAS_KEY]->(k:NDKey {id: $key_id})
    SET k.is_active = false
    RETURN k.id AS revoked_key_id
    """
    res = graph_manager.execute_write(cypher, {"user_id": user_id, "key_id": key_id})
    if not res:
        raise HTTPException(status_code=404, detail="Key not found or unauthorized.")
    return {"status": "success", "message": f"ND API key '{key_id}' successfully revoked."}