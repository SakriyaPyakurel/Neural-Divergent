import re 
from typing import Dict,Any,Tuple,Optional

class RetentionPolicy:
    """Decoupled Retention Policies representing how long a memory should be kept."""
    EPHEMERAL = "EPHEMERAL" # Session-only / Conversational noise -> Expire instantly(0 days)
    SHORT_TERM = "SHORT_TERM" # Contextual task / Conversation state -> Auto-expire(1-7 days)  
    LONG_TERM = "LONG_TERM" # Core identity,user traits, semantic facts -> Permanent(Infinite)  

class ImportanceLevel:
    """Includes semantic baseline multipliers for initial memory formation."""
    CRITICAL = 0.95 # Core identity, health and foundational traits
    HIGH = 0.85 # Strong preferences and long term relationships
    MEDIUM = 0.65 #Active projects, current states and general interests
    LOW = 0.45 # Casual Observations and fleeting feelings
    NOISE = 0.10 # Conservational filler 

    @classmethod
    def from_string(cls,level_str:str)->float:
        """Translates declerative string keys from JSON to float priors."""
        mapping = {
            "CRITICAL":cls.CRITICAL, 
            "HIGH":cls.HIGH,
            "MEDUIM":cls.MEDIUM,
            "LOW":cls.LOW,
            "NOISE":cls.NOISE
        }

class SemanticRepresentation:
    """Standardized semantic payload extracted from the linguistic parsing layer."""
    def __init__(self,subject:str,relationship:str,obj:str,
                 source_text:str,confidence:float,reason:Optional[str]=None,
                 metadata:Optional[Dict[str,Any]]=None):
        self.subject = subject.strip() 
        self.relationship = relationship.strip().lower() 
        self.object = obj.strip()
        self.confidence = confidence
        self.reason = reason
        self.metadata = metadata or {}

class ImportanceEvaluator:
    """Computes initial mathemathical importance score [0.0 to 1.0] using ontological priors."""
    def __init__(self,registry:Dict[str,Dict[str,Any]]):
        self.registry = registry 
        # Dynamically scaled system context representing long-term thematic importance.
        self.active_context_keywords = ["neural divergent","startup","thesis"] 

    def calculate(self,sir:SemanticRepresentation)->float:
        entry = self.registry.get(sir.relationship) 

        # Determine the dynamic base importance from the ontology registry
        if entry:
            base_importance = ImportanceLevel.from_string(entry.get("importance","MEDIUM")) 
        else:
            base_importance = ImportanceLevel.MEDIUM

        # Applying structural reasoning boosts defined by ontology permissions
        if sir.reason is not None and (not entry or entry.get("supports_reason",True)):
            base_importance+=0.05

        if sir.metadata.get("negated",False) and (not entry or entry.get("supports_negation",True)):
            base_importance-=0.05 

        # Semantic context expansion
        if any(keyword.lower() in sir.source_text.lower() for keyword in self.active_context_keywords):
            base_importance+=0.15

        # Mutiplying by extraction confidence to verify parse integrity
        final_importance = base_importance * sir.confidence
        return round(max(0.0,min(1.0,final_importance)),4)
    
class RetentionEvaluator:
    """Determines the baseline expiration lifecycle derived from ontological rules."""
    def __init__(self,registry:Dict[str,Dict[str,Any]]):
        self.registry = registry

    def determine_policy(self,sir:SemanticRepresentation)->str:
        entry = self.registry.get(sir.relationship) 

        # Translating string from registry to actual Retention policy
        default_policy = entry.get("retention","SHORT_TERM") if entry else RetentionPolicy.SHORT_TERM

        # Strict rule: identify relationships never degrade to temporary states
        if default_policy == "LONG_TERM":
            return RetentionPolicy.LONG_TERM
        
        return RetentionPolicy.SHORT_TERM
    
class ImportanceEvaluationEngine:
    """
    The orchestation cognitive filter sitting directly before the Memory Decision Engine.
    Dynamically loads and evaluates semamtic triples against Neural divergent's structural ontology
    """ 
    def __init__(self,ontology_path:str="app/ontology/predicate_ontology.json"):
        pass # yet to be written along with ontology loader function

