import hashlib 
import secrets 
from typing import Tuple 

def generate_nd_api_key(environment: str = "live") -> Tuple[str, str, str]:
    """
    Generates a cryptographically secure Neural Divergent API key.
    
    Returns:
        tuple: (raw_key, key_hash, key_prefix)
        - raw_key: Displayed ONCE to developer (e.g., 'nd_live_8f3a9a12...')
        - key_hash: Saved to database for lookup (SHA-256)
        - key_prefix: First 8 chars saved to display in dashboard (e.g., 'nd_live_8f3a...')
    """
    prefix = f"nd_{environment}_"
    random_bytes = secrets.token_urlsafe(32)
    raw_key = f"{prefix}{random_bytes}"
    
    # Generating SHA-256 hash for secure storage
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:12] + "..."
    
    return raw_key, key_hash, key_prefix

def hash_api_key(raw_key: str) -> str:
    """Hashes an incoming X-API-Key header value for database lookup."""
    return hashlib.sha256(raw_key.encode()).hexdigest()