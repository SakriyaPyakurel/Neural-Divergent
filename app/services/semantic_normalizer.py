import re
import json
from typing import List, Dict, Any
import logging

logger = logging.getLogger('NeuralDivergent.SemanticNormalizer')

class SemanticNormalizer:
    """
    The Cognitive Language Layer of Neural Divergent.
    Transforms raw syntax dependencies into stable, canonical cognitive concepts.
    Driven by external JSON configurations for easy expansion without code changes.
    """
    def __init__(self, rules_path: str = "app/ontology/semantic_normalization.json"):
        self.rules_path = rules_path
        
        # In-memory stores for the cognitive rules
        self.subjects = {}
        self.predicates = {}
        self.objects = {}
        self.phrase_patterns = []
        self.canonical_objects = {}
        
        self._load_rules()

    def _load_rules(self):
        """Loads the multi-tiered cognitive rules from the JSON configuration."""
        try:
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                self.subjects = data.get("subjects", {})
                self.predicates = data.get("predicates", {})
                self.objects = data.get("objects", {})
                self.phrase_patterns = data.get("phrase_patterns", [])
                self.canonical_objects = data.get("canonical_objects", {})
                
                # Pre-sorting object reduction rules by length descending 
                # so replacing larger phrases before smaller ones
                self._sorted_object_rules = sorted(
                    self.objects.items(), 
                    key=lambda item: len(item[0]), 
                    reverse=True
                )
                
        except FileNotFoundError:
            logger.warning(f"Cognitive normalization rules not found at {self.rules_path}.")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse cognitive rules: {e}")

    def normalize(self, candidate_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the 4-pass cognitive normalization pipeline.
        """
        normalized = candidate_dict.copy()

        normalized = self._normalize_subject(normalized)
        normalized = self._apply_semantic_rules(normalized) # Handling Predicates & Phrase Patterns
        normalized = self._clean_object_noise(normalized)

        return normalized

    def _normalize_subject(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Pass 1: Canonicalize pronouns and subjects."""
        subject = candidate.get("subject", "").lower().strip()
        candidate["subject"] = self.subjects.get(subject, subject)
        return candidate

    def _apply_semantic_rules(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Pass 2 & 4: Apply high-level phrase patterns and predicate rules."""
        verb = candidate.get("predicate", "").lower().strip()
        obj = candidate.get("object", "").lower().strip()
        
        # 1. Check Phrase Patterns first (Highest context specificity)
        for pattern in self.phrase_patterns:
            target = pattern.get("contains", "").lower()
            if target in obj or target in verb:
                candidate["predicate"] = pattern.get("predicate", candidate["predicate"])
                if "object" in pattern:
                    candidate["object"] = pattern["object"]
                return candidate
                
        # Checking specific Predicate rules
        if verb in self.predicates:
            rules = self.predicates[verb]
            for rule in rules:
                contains_list = rule.get("contains", [])
                
                # If contains_list is empty, it's a catch-all (like "live"). 
                # Otherwise, check if ANY of the keywords are in the object.
                if not contains_list or any(c in obj for c in contains_list):
                    candidate["predicate"] = rule.get("predicate", candidate["predicate"])
                    if "object" in rule:
                        candidate["object"] = rule["object"]
                    break 
                    
        return candidate

    def _clean_object_noise(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Pass 3: Clean up object noise and enforce canonical casing."""
        obj = candidate.get("object", "").strip()
        lower_obj = obj.lower()
        
        # Direct object phrase replacement 
        for noise_phrase, clean_phrase in self._sorted_object_rules:
            if noise_phrase in lower_obj:
                # Replacing the noisy phrase with the clean concept
                lower_obj = lower_obj.replace(noise_phrase, clean_phrase).strip()
                break

        obj = lower_obj
        
        # 2. Canonical mapping via word-boundary Regex (e.g., "lego" -> "Lego")
        for lower_canonical, proper_canonical in self.canonical_objects.items():
            if lower_canonical in obj:
                # Using regex to only replace whole words
                pattern = re.compile(rf"\b{re.escape(lower_canonical)}\b", re.IGNORECASE)
                obj = pattern.sub(proper_canonical, obj)
                
        candidate["object"] = obj
        return candidate