from fastapi import Security,HTTPException,status 
from fastapi.security.api_key import APIKeyHeader 
import os 

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

VALID_API_KEYS = {os.getenv("NEURAL_DIVERGENT_API_KEY", "nd-secure-dev-key-2026")}

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key in VALID_API_KEYS:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid or missing API Key. Access denied to Neural Divergent cognitive layer."
    )