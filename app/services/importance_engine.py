import re 
from typing import Dict,Any,Tuple,Optional,List
import os
import json
import logging 
from models.memory import SemanticRepresentation

logger = logging.getLogger(__name__)

class RetentionPolicy:
    """Decoupled Retention Policies representing how long a memory should be kept."""
    EPHEMERAL = "EPHEMERAL" # Session-only / Conversational noise -> Expire instantly(0 days)
    SHORT_TERM = "SHORT_TERM" # Contextual task / Conversation state -> Auto-expire(1-7 days)  
    LONG_TERM = "LONG_TERM" # Core identity,user traits, semantic facts -> Permanent(Infinite)  

class ImportancePrior:
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
            "MEDIUM":cls.MEDIUM,
            "LOW":cls.LOW,
            "NOISE":cls.NOISE
        }
        return mapping.get(level_str.upper(), cls.MEDIUM)

class OntologyLoader:
    """Loads the declerative semantic ontology once and shares it across the application."""
    _registry = None 

    @classmethod
    def get_registry(cls,path:str="app/ontology/predicate_ontology.json")->Dict[str,Dict[str,Any]]:
        if cls._registry is None:
            if os.path.exists(path):
                try:
                    with open(path,'r', encoding='utf-8') as f:
                        cls._registry = json.load(f) 
                    logger.info(f"Successfully loaded cognitive ontology from {path}") 
                except Exception as e:
                    logger.error(f"Failed to load ontology from file at {path} : {e}") 
                    cls._registry = cls._get_default_ontology()
            else:
                logger.warning(f"Ontology file not found at {path}. Falling back to default ontology.")
                cls._registry = cls._get_default_ontology() 
        return cls._registry

    @staticmethod
    def _get_default_ontology() -> Dict[str,Dict[str,Any]]:
        """Safe fallback to ensure the cognitive engine never crashes on boot."""
        return {
            "name": {"category": "identity", "importance": "CRITICAL", "retention": "LONG_TERM"},
            "favorite_language": {"category": "preference", "importance": "HIGH", "retention": "LONG_TERM"},
            "working_on": {"category": "project", "importance": "MEDIUM", "retention": "SHORT_TERM"}
        }        



class ImportanceEvaluator:
    """Computes initial mathemathical importance score [0.0 to 1.0] using ontological priors."""
    def __init__(self,registry:Dict[str,Dict[str,Any]]):
        self.registry = registry 

    def calculate(self,sir:SemanticRepresentation,active_contexts:List[str] = None)->float:
        """Calculates importance prior.
           Accepts dynamic active_contexts so the engine doesn't hardcode domain knowledge
        """
        entry = self.registry.get(sir.relationship) 

        # Determine the dynamic base importance from the ontology registry
        if entry:
            base_prior = ImportancePrior.from_string(entry.get("importance","MEDIUM")) 
        else:
            base_prior = ImportancePrior.MEDIUM

        # Applying structural reasoning boosts defined by ontology permissions
        if sir.reason is not None and (not entry or entry.get("supports_reason",True)):
            base_prior+=0.05

        if sir.metadata.get("negated",False) and (not entry or entry.get("supports_negation",True)):
            base_prior-=0.05 

        # Semantic context expansion (Dynamically passed by the Larger System)
        if active_contexts:
            if any(ctx.lower() in sir.source_text.lower() for ctx in active_contexts):
                base_prior+=0.15

        # Mutiplying by extraction confidence to verify parse integrity
        final_importance = base_prior * sir.confidence
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
        if default_policy == RetentionPolicy.LONG_TERM:
            return RetentionPolicy.LONG_TERM
        
        if default_policy == RetentionPolicy.EPHEMERAL:
            return RetentionPolicy.EPHEMERAL
        
        return RetentionPolicy.SHORT_TERM
    
class ImportanceEstimator:
    """
    The orchestation cognitive filter sitting directly before the Memory Decision Engine.
    Dynamically loads and evaluates semamtic triples against Neural divergent's structural ontology
    """ 
    def __init__(self,ontology_path:str="app/ontology/predicate_ontology.json"):
        self.registry = OntologyLoader.get_registry(ontology_path)

        self.importance_evaluator = ImportanceEvaluator(self.registry)
        self.retention_evaluator = RetentionEvaluator(self.registry)

    def evaluate_representation(self,sir:SemanticRepresentation,active_contexts:List[str]=None) -> Tuple[float,str]:
        """
        Processes the semantic representation throughly a highly optimized sequence.

        Returns:
            A tuple of (initial_importance_score: float , retention_policy: str)
        """
        # Fail Fast : Empty Object Parsing Noise
        if not sir.object or len(sir.object.strip()) == 0:
            return ImportancePrior.NOISE, RetentionPolicy.EPHEMERAL
        
        # Fail Fast : Parsing Integrity Gate (Severe Parse Failures) 
        if sir.confidence < 0.40:
            return ImportancePrior.NOISE, RetentionPolicy.EPHEMERAL
        
        # Calculating Initial Decoupled Prior and Retention
        importance_score = self.importance_evaluator.calculate(sir,active_contexts) 
        retention_policy = self.retention_evaluator.determine_policy(sir) 

        # Noise catcher : Downgrade absolute conversational filler to EPHEMERAL
        if importance_score <= ImportancePrior.NOISE:
            retention_policy = RetentionPolicy.EPHEMERAL

        return importance_score, retention_policy