from transformers import pipeline
from typing import Dict,Tuple
from models.memory import SemanticRepresentation,MemoryCategory

class SemanticClassifier:
    def __init__(self):
        self.classifier = pipeline("zero-shot-classification",model="facebook/bart-large-mnli")

        # High-Signal descriptive hypotheses mapped directly to MemoryCategory enums
        self.CATEGORY_MAP: Dict[str, MemoryCategory] = {
            "personal identity information, traits, roles, or background": MemoryCategory.IDENTITY,
            "personal preferences, likes, dislikes, or interests": MemoryCategory.PREFERENCE,
            "an ongoing engineering project, code repository, company, or business task": MemoryCategory.PROJECT,
            "a specific technical decision, architectural choice, or conclusion": MemoryCategory.DECISION,
            "general factual knowledge, scientific truths, or external data points": MemoryCategory.KNOWLEDGE,
            "a past event, action, historical incident, or lived experience": MemoryCategory.EXPERIENCE
        }
        self.EVENT_MAP: Dict[str, str] = {
            "a factual assertion or permanent state of truth": "Fact",
            "a specific action, operational change, or completed event": "Action",
            "an ongoing process, multi-step roadmap, or active state": "Process",
            "a future goal, intention, roadmap objective, or plan": "Goal"
        }

    def resolve_ambiguity(self,raw_message:str) -> Tuple[MemoryCategory,str,float]:
        """
        Runs deep semantic evaluation only when deterministic ontology lookups return unknown.
        Executes exactly twice per ambiguous sentence, optimizing token processing.
        """
        # Resolving Memory Category
        cat_labels = list(self.CATEGORY_MAP.keys())
        cat_result = self.classifier(
            raw_message,
            candidate_labels=cat_labels,
            hypothesis_template="This text explicitly documents {}.",
            multi_label=False
        )
        best_cat_phrase = cat_result['labels'][0] 
        cat_score = cat_result['scores'][0] 
        resolved_category = self.CATEGORY_MAP[best_cat_phrase] 

        # Resolving Event Type
        event_labels = list(self.EVENT_MAP.keys()) 
        event_result = self.classifier(
            raw_message,
            candidate_labels=event_labels,
            hypothesis_template = "This statement represents {}.",
            multi_label = False
        )
        best_event_phrase = event_result['labels'][0] 
        event_score = event_result['scores'][0] 
        resolved_event_type = self.EVENT_MAP[best_event_phrase] 

        # Blended processing of scores for evaluation in down stream
        blended_confidence = round((cat_score+event_score)/2,4)

        return resolved_category,resolved_event_type,blended_confidence

        
        
