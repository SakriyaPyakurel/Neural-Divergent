import tiktoken 
import logging 
from typing import List,Dict,Any 

logger = logging.getLogger("NeuralDivergent.ContextCompressor")

class ContextCompressor:
    def __init__(self,graph_manager,encoder_model:str="cl100k_base"):
        """
        Initializes the Context Compressor.
        :param graph_manager: The Neo4j graph manager instance.
        :param encoder_model: The tiktoken model to use for token counting. 
                              'cl100k_base' is standard for GPT-3.5/GPT-4.
        """
        self.graph_manager = graph_manager 

        try:
            self.tokenizer = tiktoken.get_encoding(encoder_model) 
        except Exception as e:
            logger.error(f"Failed to load tiktoken encoder: {e}") 
            self.tokenizer = None

    def extract_active_subgraph(self,entities:List[str],max_hops:int=2,limit:int=50) -> List[Dict[str,Any]]:
        """
        Traverses Neo4j starting from extracted entities up to max_hops,
        retrieving only ACTIVE relationships, sorted by importance.
        """
        if not entities:
            logger.debug("No entities provided for subgraph extraction.")
            return [] 
        # Cypher breakdown:
        # 1. Matching starting nodes by name.
        # 2. Traversing paths 1 to max_hops deep.
        # 3. Ensuring ALL relationships in the path are active (prunes historical noise).
        # 4. UNWIND the path to get distinct individual relationships (prevents duplication).
        cypher = """
        MATCH (s) WHERE s.name IN $entities
        MATCH path = (s)-[r*1..2]-(o)
        WHERE ALL(rel IN r WHERE rel.is_active = true)
        
        UNWIND r AS rel
        WITH DISTINCT rel
        
        RETURN 
            startNode(rel).name AS subject,
            type(rel) AS predicate,
            endNode(rel).name AS object,
            coalesce(rel.importance_score, 0.5) AS importance,
            coalesce(rel.reinforcement_count, 1) AS reinforcement
        ORDER BY importance DESC, reinforcement DESC
        LIMIT $limit
        """
        try: 
            #execute_read expecting a dictionary of parameters
            params = {
                "entities":entities,
                "limit":limit
            }
            records = self.graph_manager.execute_read(cypher,params) 
            return records if records else [] 
        except Exception as e:
            logger.error(f"Failed to extract subgraph context: {e}") 
            return [] 

    def serialize_to_dense_dsl(self, records: List[Dict[str, Any]]) -> str:
        """
        Converts graph paths into a hyper-compact Domain Specific Language (DSL)
        to minimize the token footprint sent to the LLM.
        """
        if not records:
            return "[KNOWLEDGE_GRAPH]\nNo specific prior context found."

        # Using a very dense syntax : Subject | Predicate -> Object 
        # This strips out conversational fluff while maintaining absolute semantic clarity.
        lines = ["[KNOWLEDGE_GRAPH]"]
        for r in records:
            # Safely grabbing values, defaulting to string to prevent serialization errors
            sub = str(r.get('subject', 'Unknown'))
            pred = str(r.get('predicate', 'RELATES_TO'))
            obj = str(r.get('object', 'Unknown'))
            
            lines.append(f"{sub} | {pred} -> {obj}")

        return "\n".join(lines)

    def compute_compression(self, raw_history: str, compressed_context: str) -> Dict[str, Any]:
        """
        Measures the exact token savings produced by Neural Divergent.
        """
        if not self.tokenizer:
            return {"error": "Tokenizer not initialized"} 

        # Count tokens
        raw_tokens = len(self.tokenizer.encode(raw_history))
        compressed_tokens = len(self.tokenizer.encode(compressed_context))

        # Avoid division by zero
        reduction_pct = 0.0
        if raw_tokens > 0:
            reduction_pct = round(((raw_tokens - compressed_tokens) / raw_tokens) * 100, 2)

            # If the raw context is smaller than our injected context, capping at 0% 
            if reduction_pct < 0:
                reduction_pct = 0.0

        return {
            "raw_token_count": raw_tokens,
            "compressed_token_count": compressed_tokens,
            "reduction_percentage": reduction_pct,
            "saved_tokens": max(0, raw_tokens - compressed_tokens)
        }
        