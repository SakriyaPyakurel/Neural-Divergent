import numpy as np
from typing import Dict, Tuple
from fastembed import TextEmbedding
from app.models.memory import MemoryCategory

class SemanticClassifier:
    def __init__(self):
        # Reusing the exact same lightweight model from database setup
        self.embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

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

        # Pre-compute embeddings for hypotheses at startup (only takes ~0.1 seconds)
        self.cat_phrases = list(self.CATEGORY_MAP.keys())
        self.cat_embeddings = list(self.embedding_model.embed(
            [f"This text explicitly documents {cat}." for cat in self.cat_phrases]
        ))

        self.event_phrases = list(self.EVENT_MAP.keys())
        self.event_embeddings = list(self.embedding_model.embed(
            [f"This statement represents {event}." for event in self.event_phrases]
        ))

    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """Calculates mathematical distance between two semantic vectors"""
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

    def resolve_ambiguity(self, raw_message: str) -> Tuple[MemoryCategory, str, float]:
        """
        Runs deep semantic evaluation using vector similarity.
        Executes without PyTorch, keeping RAM under 150MB total.
        """
        # Embedding the user's message
        msg_embedding = list(self.embedding_model.embed([raw_message]))[0]

        # Scoring Categories
        cat_scores = [self._cosine_similarity(msg_embedding, cat_emb) for cat_emb in self.cat_embeddings]
        best_cat_idx = int(np.argmax(cat_scores))
        resolved_category = self.CATEGORY_MAP[self.cat_phrases[best_cat_idx]]
        cat_score = cat_scores[best_cat_idx]

        # Score Events
        event_scores = [self._cosine_similarity(msg_embedding, ev_emb) for ev_emb in self.event_embeddings]
        best_event_idx = int(np.argmax(event_scores))
        resolved_event_type = self.EVENT_MAP[self.event_phrases[best_event_idx]]
        event_score = event_scores[best_event_idx]

        # lended processing of scores for downstream evaluation
        blended_confidence = round((cat_score + event_score) / 2, 4)

        return resolved_category, resolved_event_type, blended_confidence