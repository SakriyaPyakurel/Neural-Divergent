from pydantic import BaseModel,Field
from typing import List,Optional

# Request and Response Schemas
class IngestRequest(BaseModel):
    text: str = Field(...,description="The raw conversational utterance from the user.")
    active_contexts: Optional[List[str]] = Field(
        default=None,
        description="Dynamic contextual keywords to prioritize during evaluation.",
        examples=["neural divergent","startup"] 
    )

class ProcessedTripleResponse(BaseModel):
    triple: List[str] = Field(...,description="The parsed [Subject,Predicate,Object] triple.")
    action: str = Field(...,description="Action taken by the MDE: DUPLICATE, SUPERSEDED, NOVEL(NEW), or IGNORED.")
    memory_id: Optional[int] = Field(None,description="The assigned table database row ID.")
    importance_prior: float = Field(...,description="Calculated initial mathematical prior.")
    retention_policy: str = Field(...,description="Assigned RetentionPolicy (EPHEREMAL, SHORT_TERM, LONG_TERM).")

class CognitiveIngestResponse(BaseModel):
    utterance:str
    processed_count:int 
    results: List[ProcessedTripleResponse]
