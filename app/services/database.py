import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any, Union
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)
# Dynamically locating app/.env (one level up from app/services/database.py)
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Loading the environment variables from app/.env
load_dotenv(dotenv_path=ENV_PATH)

class MemoryDatabase:
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        # Default to environment variables, crucial for Neo4j AuraDB
        self.uri = uri or os.getenv("NEO4J_URL")
        self.user = user or os.getenv("NEO4J_USER")
        self.password = password or os.getenv("NEO4J_PASSWORD")

        # Explicit validation check to catch missing env vars early
        if not self.uri or not self.user or not self.password:
            raise ValueError(
                f"Missing Neo4j credentials. Looked in environment and at '{ENV_PATH}'. "
                "Ensure NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD are defined in your app/.env file."
            )
        
        # Initializing the Neo4j Driver
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self.setup_tables()

    def close(self):
        """Always close the driver when the app shuts down."""
        self.driver.close()

    def setup_tables(self):
        """Initializes the Graph constraints and Vector Indexes for AuraDB."""
        # Indices for faster exact-match and LIKE searches
        indices = [
            "CREATE INDEX memory_subject IF NOT EXISTS FOR (m:Memory) ON (m.subject)",
            "CREATE INDEX memory_predicate IF NOT EXISTS FOR (m:Memory) ON (m.predicate)",
            "CREATE INDEX memory_object IF NOT EXISTS FOR (m:Memory) ON (m.object)"
        ]
        
        # Native Neo4j Vector Index (384 dimensions for standard embedding models)
        vector_index_query = """
        CREATE VECTOR INDEX memory_vectors IF NOT EXISTS
        FOR (m:Memory) ON (m.embedding)
        OPTIONS {indexConfig: {
            `vector.dimensions`: 384,
            `vector.similarity_function`: 'cosine'
        }}
        """
        
        with self.driver.session() as session:
            for query in indices:
                session.run(query)
            session.run(vector_index_query)
            logger.info("Neo4j indexes and vector schemas initialized.")

    def _format_record(self, record, node_alias: str = "m", extra_fields: List[str] = None) -> Dict:
        """Helper to convert a Neo4j Node Record into a Python dictionary matching the old SQLite format."""
        node = record[node_alias]
        result = dict(node.items())
        
        # Neo4j uses string elementIds in v5+ instead of auto-incrementing integers
        result['id'] = node.element_id 
        
        # Format Neo4j DateTime objects back to strings
        if 'created_at' in result:
            result['created_at'] = str(result['created_at'])
        if 'last_accessed' in result:
            result['last_accessed'] = str(result['last_accessed'])
            
        if 'metadata' in result and isinstance(result['metadata'], str):
            try:
                result['metadata'] = json.loads(result['metadata'])
            except json.JSONDecodeError:
                pass
                
        # Injecting dynamic calculated fields (like distance, cognitive_rank)
        if extra_fields:
            for field in extra_fields:
                if field in record:
                    result[field] = record[field]
                    
        return result

    def find_exact_triple(self, subject: str, predicate: str, object_val: str) -> Optional[Dict]:
        query = """
        MATCH (m:Memory {subject: $subject, predicate: $predicate, object:$object, is_active: 1})
        RETURN m LIMIT 1
        """
        with self.driver.session() as session:
            result = session.run(query, subject=subject, predicate=predicate, object=object_val).single()
            return self._format_record(result) if result else None

    def find_by_subject_and_predicate(self, subject: str, predicate: str) -> List[Dict]:
        query = """
        MATCH (m:Memory {subject: $subject, predicate:$predicate, is_active: 1})
        RETURN m
        """
        with self.driver.session() as session:
            records = session.run(query, subject=subject, predicate=predicate)
            return [self._format_record(record) for record in records]

    def find_related_memories(self, subject: str) -> List[Dict]:
        query = """
        MATCH (m:Memory)
        WHERE m.subject CONTAINS $subject AND m.is_active = 1
        RETURN m ORDER BY m.last_accessed DESC
        """
        with self.driver.session() as session:
            records = session.run(query, subject=subject)
            return [self._format_record(record) for record in records]

    def insert_triple(self, subject: str, predicate: str, object_val: str,
                      importance_score: float, event_type: Optional[str] = None, memory_category: Optional[str] = None,
                      source_text: Optional[str] = None, reason: Optional[str] = None,
                      confidence: float = 1.0, metadata: Dict = None,
                      supersedes_id: Optional[str] = None,
                      vector_embedding: Optional[List[float]] = None) -> str:
        """Inserts memory node. Note: Returns a string UUID (elementId) instead of an int."""
        query = """
        CREATE (m:Memory {
            subject: $subject, predicate: $predicate, object:$object,
            importance_score: $importance_score, event_type:$event_type,
            memory_category: $memory_category, source_text:$source_text,
            reason: $reason, confidence:$confidence,
            metadata: $metadata, supersedes_id:$supersedes_id,
            strength: 1, is_active: 1,
            created_at: datetime(), last_accessed: datetime()
        })
        """
        if vector_embedding:
            query += " SET m.embedding = $embedding"
            
        query += " RETURN elementId(m) AS new_id"
        
        meta_str = json.dumps(metadata) if metadata else "{}" 

        with self.driver.session() as session:
            result = session.run(query, 
                subject=subject, predicate=predicate, object=object_val,
                importance_score=importance_score, event_type=event_type,
                memory_category=memory_category, source_text=source_text,
                reason=reason, confidence=confidence, metadata=meta_str,
                supersedes_id=supersedes_id, embedding=vector_embedding
            )
            return result.single()["new_id"]

    def reinforce_memory(self, memory_id: Union[str, int], new_source_text: str, vector_embedding: Optional[List[float]] = None):
        query = """
        MATCH (m:Memory) WHERE elementId(m) = $id
        SET m.source_text = $source_text,
            m.last_accessed = datetime()
        """
        if vector_embedding:
            query += " SET m.embedding = $embedding"
            
        with self.driver.session() as session:
            session.run(query, id=str(memory_id), source_text=new_source_text, embedding=vector_embedding)

    def deprecate_memory(self, memory_id: Union[str, int]):
        query = "MATCH (m:Memory) WHERE elementId(m) = $id SET m.is_active = 0"
        with self.driver.session() as session:
            session.run(query, id=str(memory_id))

    def touch_memory(self, memory_id: Union[str, int], new_source_text: str, vector_embedding: Optional[List[float]] = None):
        """Updates the access heartbeat with Neo4j CASE WHEN logic replacing SQLite MIN/MAX"""
        query = """
        MATCH (m:Memory) WHERE elementId(m) = $id
        SET m.source_text = $source_text,
            m.last_accessed = datetime(),
            m.strength = m.strength + 1,
            m.importance_score = CASE WHEN m.importance_score + 0.05 < 1.0 THEN m.importance_score + 0.05 ELSE 1.0 END,
            m.confidence = CASE WHEN m.confidence + (1.0 - m.confidence) * 0.2 < 1.0 THEN m.confidence + (1.0 - m.confidence) * 0.2 ELSE 1.0 END
        """
        if vector_embedding:
            query += " SET m.embedding = $embedding"

        with self.driver.session() as session:
            session.run(query, id=str(memory_id), source_text=new_source_text, embedding=vector_embedding)

    def search_normal_memories(self, search_term: str) -> List[Dict]:
        query = """
        MATCH (m:Memory)
        WHERE m.is_active = 1
          AND (toLower(m.subject) CONTAINS toLower($term) 
               OR toLower(m.predicate) CONTAINS toLower($term) 
               OR toLower(m.object) CONTAINS toLower($term))
        RETURN m
        ORDER BY m.importance_score DESC, m.strength DESC, m.confidence DESC
        """
        with self.driver.session() as session:
            records = session.run(query, term=search_term.strip())
            return [self._format_record(rec) for rec in records]

    def search_hybrid_memories(self, query_embedding: List[float], limit: int = 10) -> List[Dict]:
        """Hybrid Search utilizing Neo4j's db.index.vector.queryNodes and duration math for decay."""
        query = """
        CALL db.index.vector.queryNodes('memory_vectors', 50, $embedding) YIELD node AS m, score AS similarity
        WHERE m.is_active = 1
        WITH m, similarity,
            (
                (CASE WHEN similarity > 0.01 THEN similarity ELSE 0.01 END)
                * m.importance_score
                * m.confidence
                * (CASE WHEN 1.0 + (m.strength - 1.0) * 0.2 < 3.0 THEN 1.0 + (m.strength - 1.0) * 0.2 ELSE 3.0 END)
            )
            /
            (
                1.0 + (duration.between(m.last_accessed, datetime()).seconds / 86400.0) * 0.05
            ) AS cognitive_rank
        RETURN m, similarity AS distance, cognitive_rank
        ORDER BY cognitive_rank DESC, distance DESC
        LIMIT $limit
        """
        with self.driver.session() as session:
            records = session.run(query, embedding=query_embedding, limit=limit)
            results = []
            for rec in records:
                formatted = self._format_record(rec, extra_fields=['distance', 'cognitive_rank'])
                formatted['cognitive_rank'] = round(formatted['cognitive_rank'], 4)
                results.append(formatted)
            return results

    def get_subject_history(self, subject: str, include_inactive: bool = True, limit: int = 50) -> List[Dict]:
        query = "MATCH (m:Memory {subject: $subject}) "
        if not include_inactive:
            query += "WHERE m.is_active = 1 "
        query += "RETURN m ORDER BY m.created_at DESC LIMIT $limit"
        
        with self.driver.session() as session:
            records = session.run(query, subject=subject, limit=limit)
            return [self._format_record(rec) for rec in records]

    def get_predicate_history(self, subject: str, predicate: str, include_inactive: bool = True, limit: int = 50) -> List[Dict]:
        query = "MATCH (m:Memory {subject: $subject, predicate:$predicate}) "
        if not include_inactive:
            query += "WHERE m.is_active = 1 "
        query += "RETURN m ORDER BY m.created_at ASC LIMIT $limit"

        with self.driver.session() as session:
            records = session.run(query, subject=subject, predicate=predicate, limit=limit)
            return [self._format_record(rec) for rec in records]

    def get_recent_history(self, include_inactive: bool = True, limit: int = 50) -> List[Dict]:
        query = "MATCH (m:Memory) "
        if not include_inactive:
            query += "WHERE m.is_active = 1 "
        query += "RETURN m ORDER BY m.created_at DESC LIMIT $limit"

        with self.driver.session() as session:
            records = session.run(query, limit=limit)
            return [self._format_record(rec) for rec in records]

    def traverse_memory_graph(self, root_entity: str, limit: int = 15) -> List[Dict]:
        """Translated the complex multi-step CTE directly into a Neo4j CALL {} UNION structure."""
        query = """
        CALL {
            WITH $root AS root_term
            MATCH (m:Memory)
            WHERE m.is_active = 1 AND (m.subject CONTAINS root_term OR m.object CONTAINS root_term)
            RETURN m, 0 AS traversal_depth
            ORDER BY m.importance_score DESC
            LIMIT 5
        }
        UNION
        CALL {
            WITH $root AS root_term
            MATCH (m0:Memory)
            WHERE m0.is_active = 1 AND (m0.subject CONTAINS root_term OR m0.object CONTAINS root_term)
            WITH m0 ORDER BY m0.importance_score DESC LIMIT 5
            
            MATCH (m1:Memory)
            WHERE m1.is_active = 1 
              AND elementId(m1) <> elementId(m0)
              AND (m1.subject IN [m0.subject, m0.object] OR m1.object IN [m0.subject, m0.object])
            RETURN m1 AS m, 1 AS traversal_depth
        }
        WITH m, min(traversal_depth) AS depth 
        WITH m, depth,
             (m.importance_score * m.confidence * CASE WHEN 1.0 + (m.strength - 1.0) * 0.2 < 3.0 THEN 1.0 + (m.strength - 1.0) * 0.2 ELSE 3.0 END) / 
             (1.0 + (duration.between(m.last_accessed, datetime()).seconds / 86400.0) * 0.05) AS cognitive_rank
        RETURN m, depth AS traversal_depth, cognitive_rank
        ORDER BY depth ASC, cognitive_rank DESC
        LIMIT $limit
        """
        with self.driver.session() as session:
            records = session.run(query, root=root_entity.strip(), limit=limit)
            results = []
            for rec in records:
                formatted = self._format_record(rec, extra_fields=['traversal_depth', 'cognitive_rank'])
                formatted['cognitive_rank'] = round(formatted['cognitive_rank'], 4)
                results.append(formatted)
            return results

    def get_decayable_memories(self) -> List[Dict]:
        query = """
        MATCH (m:Memory)
        WHERE m.is_active = 1 AND m.metadata CONTAINS 'EPHEMERAL' OR m.metadata CONTAINS 'SHORT_TERM'
        WITH m,
             (m.importance_score * m.confidence * CASE WHEN 1.0 + (m.strength - 1.0) * 0.2 < 3.0 THEN 1.0 + (m.strength - 1.0) * 0.2 ELSE 3.0 END) / 
             (1.0 + (duration.between(m.last_accessed, datetime()).seconds / 86400.0) * 0.05) AS current_rank
        RETURN m, current_rank
        """
        with self.driver.session() as session:
            records = session.run(query)
            return [self._format_record(rec, extra_fields=['current_rank']) for rec in records]

    def archive_faded_memories(self, ids_to_archive: List[Union[str, int]]):
        if not ids_to_archive:
            return
        
        string_ids = [str(i) for i in ids_to_archive]
        query = "MATCH (m:Memory) WHERE elementId(m) IN $ids SET m.is_active = 0"
        
        with self.driver.session() as session:
            session.run(query, ids=string_ids)
            logger.info(f"Archived {len(ids_to_archive)} decayed memories.")