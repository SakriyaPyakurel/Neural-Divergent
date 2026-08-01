import logging 
from typing import List,Dict,Any,Set 

logger = logging.getLogger('NeuralDivergent.MemoryRefiner') 

class MemoryRefiner:
    """
    The Cognitive Pruner of Neural Divergent.
    Evaluates a batch of normalized triples originating from a single source text.
    Discards redundant, weak, or noisy triples in favor of high-confidence canonical triples.
    """
    def __init__(self):
        # Agressively pruning if a better ontology-backed triple exits in the same sentence.
        self.stop_verbs = {
            "is", "was", "am", "are", "be", "have", "has", "had", 
            "do", "does", "did", "take", "make", "try", "start", 
            "begin", "enjoy", "prefer", "want", "need", "seem", 
            "look", "use", "play", "build", "argue", "create"
        }

    def refine(self,candidates:List[Dict[str,Any]],ontology_keys:set[str]) -> List[Dict[str,Any]]:
        """
        Filters a batch of normalized triples.
        """
        if not candidates:
            return 

        refined = [] 
        seen = set() 

        # Deduplication: Sometimes the extractor pulls the same semantic meaning twice.
        unique_candidates = [] 
        for candidate in candidates:
            sig = (candidate.get("subject", "").lower(), 
                   candidate.get("predicate", "").lower(), 
                   candidate.get("object", "").lower())
            if sig not in seen:
                seen.add(sig)
                unique_candidates.append(candidate) 

        if len(candidates) <= 1:
            return unique_candidates 

        # Identifying strong and weak candidates 
        strong_candidates = [] 
        weak_candidates = [] 

        for candidate in unique_candidates:
            pred = candidate.get("predicate","").lower()

           # A candidate is strong if its predicate is formally defined in the ontology.
            if pred in ontology_keys:
                strong_candidates.append(candidate) 
            else:
                weak_candidates.append(candidate) 

        # Pruning decision
        if strong_candidates:
            if weak_candidates:
                logger.info(f"MemoryRefiner pruned {len(weak_candidates)} weak triples in favor of {len(strong_candidates)} strong ontology matches.")
            return strong_candidates

        # Fallback Pruning (No ontology matches found.)
        non_stop_candidates = [cand for cand in weak_candidates if cand.get("predicate","").lower() not in self.stop_verbs]

        if non_stop_candidates and len(non_stop_candidates) < len(weak_candidates):
           logger.info(f"MemoryRefiner fell back to pruning stop-verbs, removed {len(weak_candidates) - len(non_stop_candidates)} triples.")
           return non_stop_candidates 

        # If can't safely prune, returning the unique list and letting the classifier handle it.
        return weak_candidates            

     