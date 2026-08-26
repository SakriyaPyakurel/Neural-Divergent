from enum import Enum
from pydantic import BaseModel,Field
from datetime import datetime,UTC
from typing import List,Optional
from uuid import uuid4
class MemoryCategory(str, Enum):
    IDENTITY = "identity"
    PREFERENCE = "preference"
    PROJECT = "project"
    DECISION = "decision"
    KNOWLEDGE = "knowledge"
    EXPERIENCE = "experience"


class CandidateRelationship(BaseModel):
    # An intermediate and pure structural representation of a sentence before being categorized 
    subject:str 
    verb:str 
    object:str 
    reason: Optional[str] = None 
    is_negated: bool = False

class SemanticRepresentation(BaseModel):
    subject: str
    relationship: str
    object: str
    source_text:str
    event_type: Optional[str]
    reason: Optional[str]
    confidence: float
    metadata: dict