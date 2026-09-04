from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# --- Registration & Account Requests ---
class DeveloperRegisterRequest(BaseModel):
    email: EmailStr
    developer_name: str

# --- ND Key Creation & Display ---
class CreateNDKeyRequest(BaseModel):
    key_label: str = Field(..., example="Production Backend Key")
    environment: str = Field("live", example="live or test")

class NDKeyIssuedResponse(BaseModel):
    status: str
    message: str
    raw_nd_api_key: str = Field(..., description="Copy this key now. It will NOT be shown again.")
    key_label: str
    key_prefix: str
    created_at: str

class NDKeyMetadata(BaseModel):
    key_id: str
    key_label: str
    key_prefix: str
    is_active: bool
    created_at: str
    last_used_at: Optional[str] = None