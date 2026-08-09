import logging 
import re 
import json 
from typing import Dict,Any,Optional

logger = logging.getLogger("NeuralDivergent.GraphIngester")

class GraphIngester:
    """
    Translates normalized candidate dictionaries into persistent Neo4j Graph elements.
    Handles memory supersession and reinforcement automatically.
    """
    def __init__(self,graph_manager,ontology_path="app/ontology/predicate_ontology.json"):
        self.db = graph_manager 
        self.ontology = self._load_ontology(ontology_path) 

    def _load_ontology(self,path:str) -> dict:
        try:
            with open(path,'r',encoding='utf-8') as f:
                return json.load(f) 
        except Exception as e:
            logger.error(f"Could not load ontology for graph ingestion: {e}")
            return {}

    def ingest_memory(self, 
                      subject: str, 
                      predicate: str, 
                      object_val: str, 
                      memory_category: str, 
                      importance_score: float, 
                      memory_id: int, 
                      metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generates and executes the Cypher query to ingest a single memory,
        linking it back to the primary SQLite database via memory_id.
        """
        if not subject or not object_val or not predicate:
            logger.warning("Incomplete candidate. Skipping graph ingestion.")
            return None

        # Sanitizing relationship type for Cypher (Strictly Uppercase & Underscores)
        rel_type = re.sub(r'[^A-Z0-9_]', '', predicate.upper())
        
        # Checking ontology for exclusive vs accumulative traits
        ontology_rule = self.ontology.get(predicate.lower(), {})
        is_exclusive = not ontology_rule.get("allow_multiple", True)

        supersession_cypher = ""
        if is_exclusive:
            supersession_cypher = f"""
            // Finding existing active relationships of this type pointing to a DIFFERENT concept
            WITH s, o
            OPTIONAL MATCH (s)-[old_r:{rel_type} {{is_active: true}}]->(old_o:Concept)
            WHERE id(old_o) <> id(o)
            
            // Mark the old relationship as inactive
            SET old_r.is_active = false, old_r.superseded_at = datetime()
            """

        # Serializing metadata to a JSON string for safe graph storage
        metadata_str = json.dumps(metadata) if metadata else "{}"

        query = f"""
        // Finding or creating the Nodes
        MERGE (s:Subject {{name: $subject}})
        MERGE (o:Concept {{name: $object}})
        
        {supersession_cypher}
        
        // Finding or Creating the active Relationship Edge
        WITH s, o
        MERGE (s)-[r:{rel_type} {{is_active: true}}]->(o)
        
        // Setting Properties (TETHERING TO SQLITE HERE)
        ON CREATE SET 
            r.sqlite_id = $memory_id,
            r.category = $category,
            r.importance_score = $importance,
            r.metadata = $metadata_str,
            r.created_at = datetime(),
            r.last_seen_at = datetime(),
            r.reinforcement_count = 1
            
        ON MATCH SET
            r.sqlite_id = $memory_id, // Ensuring canonical ID is updated if superseding/merging
            r.last_seen_at = datetime(),
            r.importance_score = CASE WHEN $importance > r.importance_score THEN $importance ELSE r.importance_score END,
            r.metadata = $metadata_str,
            r.reinforcement_count = coalesce(r.reinforcement_count, 1) + 1
            
        RETURN properties(r) AS rel_data
        """

        params = {
            "subject": subject.strip(),
            "object": object_val.strip(),
            "memory_id": memory_id,
            "category": memory_category,
            "importance": importance_score,
            "metadata_str":metadata_str
        }

        # Executing transaction
        records = self.db.execute_write(query, params)
        
        if records:
            return records[0]
        return None