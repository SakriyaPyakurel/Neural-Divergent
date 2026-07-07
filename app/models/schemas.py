from pydantic import BaseModel,Field
from typing import List,Optional
from datetime import datetime,timezone
from enum import Enum

# ENUMS
class MemoryAction(str,Enum):
    NEW = "NEW"
    DUPLICATE="DUPLICATE" 
    REINFORCED="REINFORCED"
    SUPERSEDED="SUPERSEDED" 
    IGNORED = "IGNORED"

class RetentionPolicy(str,Enum):
    EPHEMERAL = "EPHEMERAL"
    SHORT_TERM = "SHORT_TERM"
    LONG_TERM = "LONG_TERM"

# Request Schemas
class IngestRequest(BaseModel):
    text: str = Field(...,description="The raw natural language input to process.") 
    active_contexts: Optional[List[str]] = Field(
        default_factory=list,
        description="Active conversation tags to boost importance routing."
    )

# Nested Response Models
class SemanticTriple(BaseModel):
    subject: str = Field(..., description="The actor or root entity.")
    predicate: str = Field(..., description="The normalized action, state, or relationship.")
    object: str = Field(..., description="The target entity, attribute, or descriptor.")

class ProcessedTripleResponse(BaseModel):
    triple: SemanticTriple
    action: MemoryAction
    confidence: float = Field(..., description="Extraction confidence score (0.0 to 1.0).")
    importance_prior: float = Field(..., description="Calculated baseline importance.")
    retention_policy: RetentionPolicy
    memory_id: Optional[int] = Field(None, description="The database ID, if stored.")
    reason: Optional[str] = Field(None, description="Extracted causal reasoning, if any.")

# Main Response Schema
class CognitiveIngestResponse(BaseModel):
    source_text: str = Field(..., description="The original sanitized input text.")
    processed_count: int = Field(..., description="Total semantic triples extracted.")
    stored_count: int = Field(..., description="Triples successfully written to memory.")
    ignored_count: int = Field(..., description="Triples ignored due to duplication or low priority.")
    engine_version: str = Field("0.3.0", description="Current version of the Neural Divergent pipeline.")
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        description="ISO 8601 UTC timestamp of processing."
    )
    results: List[ProcessedTripleResponse]
