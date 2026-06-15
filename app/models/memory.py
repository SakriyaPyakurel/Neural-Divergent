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

class MemoryContext(BaseModel):
    reason:Optional[str] =None 
    time:Optional[str] = None 
    domain:Optional[str] = None

class Memory(BaseModel):
    id : str = Field(default_factory=lambda:str(uuid4())) 
    fact:str 
    context:MemoryContext 
    primary_category:MemoryCategory
    secondary_categories:List[MemoryCategory] = [] 
    importance_score: float = Field(
        ge=0.0,
        le=1.0
    )
    timestamp: datetime = Field(default_factory= lambda: datetime.now(UTC)) 
    related_memories: List[str] = []

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
    event_type: Optional[str]
    reason: Optional[str]
    confidence: float
    metadata: dict