import re 
from typing import Dict,Any,Tuple,Optional
import os
import json

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
        return mapping.get(level_str.upper(), cls.MEDIUM)

class SemanticRepresentation:
    """Standardized semantic payload extracted from the linguistic parsing layer."""
    def __init__(self,subject:str,relationship:str,obj:str,
                 source_text:str,confidence:float,reason:Optional[str]=None,
                 metadata:Optional[Dict[str,Any]]=None):
        self.subject = subject.strip() 
        self.relationship = relationship.strip().lower() 
        self.object = obj.strip()
        self.source_text = source_text.strip()
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
        self.ontology_path = ontology_path
        self.registry = self._load_ontology()

        self.importance_evaluator = ImportanceEvaluator(self.registry)
        self.retention_evaluator = RetentionEvaluator(self.registry)

    def _load_ontology(self) -> Dict[str,Dict[str,Any]]:
        """Loads and parses the json ontology file with an in-memory hard fallback.""" 
        if os.path.exists(self.ontology_path):
            try:
                with open(self.ontology_path,'r',encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load ontology file at {self.ontology_path} : {e}")
        
        # Hard fallback to prevent crash if the dependency tree is decoupled
        return {
            "name":{"importance":"CRITICAL","retention":"LONG_TERM"},
            "favorite_language":{"importance":"HIGH","retention":"LONG_TERM"},
            "working_on":{"importance":"MEDIUM","retention":"SHORT_TERM"}
        }  
    
    def evaluate_representation(self,sir:SemanticRepresentation) -> Tuple[float,str]:
        """
        Processes the semantic representation throughly a highly optimized sequence.

        Returns:
            A tuple of (initial_importance_score: float , retention_policy: str)
        """
        # Fail Fast : Empty Object Parsing Noise
        if not sir.object or len(sir.object.strip()) == 0:
            return ImportanceLevel.NOISE, RetentionPolicy.EPHEMERAL
        
        # Fail Fast : Parsing Integrity Gate (Severe Parse Failures) 
        if sir.confidence < 0.40:
            return ImportanceLevel.NOISE, RetentionPolicy.EPHEMERAL
        
        # Calculating Initial Decoupled Prior and Retention
        importance_score = self.importance_evaluator.calculate(sir) 
        retention_policy = self.retention_evaluator.determine_policy(sir) 

        return importance_score, retention_policy