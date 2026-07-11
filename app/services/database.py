import sqlite3 
import json 
from typing import List,Dict,Optional,Any
import logging

class MemoryDatabase:
    def __init__(self,db_path:str="neural_divergent.db"):
        self.db_path = db_path 
        self.setup_tables() 
    
    def _get_connection(self):
        """Creates and returns a database connection for Neural Divergent."""
        conn = sqlite3.connect(self.db_path,check_same_thread=False) 
        conn.row_factory = sqlite3.Row # Returning rows as dictionaries instead of just raw tuples
        return conn
    
    def setup_tables(self):
        """Initializes the Proto-Graph schema if it is not existent."""

        query = """
        CREATE TABLE IF NOT EXISTS semantic_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            event_type TEXT,                -- Made NULLABLE to prevent extraction integrity issues
            memory_category TEXT,           -- IDENTITY, PREFERENCE, KNOWLEDGE, etc.
            source_text TEXT,               -- The raw sentence that triggered this extraction 
            reason TEXT,
            confidence REAL DEFAULT 1.0,
            importance_score REAL DEFAULT 1.0,
            strength INTEGER DEFAULT 1,    -- DEFAULTS to 1
            metadata TEXT,                  -- Stored as a JSON string
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,    -- 1 for active, 0 for historically overwritten
            supersedes_id INTEGER,          -- References the memory ID this fact replaces
            FOREIGN KEY(supersedes_id) REFERENCES semantic_memories(id)
        );
        """
        # Creating indices for quick relational and subject lookups
        index_triples = """
        CREATE INDEX IF NOT EXISTS idx_triple ON semantic_memories(subject, predicate, object);
        """
        index_subject = """
        CREATE INDEX IF NOT EXISTS idx_subject ON semantic_memories(subject);
        """

        with self._get_connection() as conn:
            cursor = conn.cursor() 
            cursor.execute(query) 
            cursor.execute(index_triples) 
            cursor.execute(index_subject)
            conn.commit()

    def find_exact_triple(self,subject:str,predicate:str,object_val:str) -> Optional[Dict]:
        """Checks if a specific, exact memory already is in existence to prevent duplicate entries."""

        query = """
        SELECT * FROM semantic_memories 
        WHERE subject = ? AND predicate = ? AND object = ? AND is_active = 1
        """
        with self._get_connection() as conn:
            cursor = conn.cursor() 
            cursor.execute(query,(subject,predicate,object_val)) 
            row = cursor.fetchone() 
            return dict(row) if row else None 
    
    def find_by_subject_and_predicate(self,subject:str,predicate:str)->List[Dict]:
        """Finds active memories based on subject and relationship."""

        query = """
        SELECT * FROM semantic_memories 
        WHERE subject = ? AND predicate = ? AND is_active = 1
        """
        with self._get_connection() as conn:
            cursor = conn.cursor() 
            cursor.execute(query,(subject,predicate)) 
            return [dict(row) for row in cursor.fetchall()]
    
    def find_related_memories(self, subject: str) -> List[Dict]:
        """Retrieves all active facts related to a specific subject node."""
        query = """
        SELECT * FROM semantic_memories 
        WHERE subject LIKE ? AND is_active = 1
        ORDER BY last_accessed DESC
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (f"%{subject}%",))
            return [dict(row) for row in cursor.fetchall()]
        
    def insert_triple(self,subject:str,predicate:str,object_val:str,
                      importance_score:float,event_type:Optional[str]=None,memory_category:Optional[str]=None,
                      source_text:Optional[str]=None,reason:Optional[str]=None,
                      confidence:float=1.0,metadata:Dict=None,
                      supersedes_id: Optional[int] = None)->int:
        """Inserts a new semantic node/edge into the ledger with full metadata."""

        query = """
         INSERT INTO semantic_memories 
        (subject, predicate, object, importance_score, event_type, memory_category, source_text, reason, confidence, metadata, supersedes_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        meta_str = json.dumps(metadata) if metadata else "{}" 

        with self._get_connection() as conn:
            cursor= conn.cursor() 
            cursor.execute(query,(
                subject, predicate, object_val, importance_score, event_type, 
                memory_category, source_text, reason, confidence, meta_str, supersedes_id
            ))
            conn.commit() 
            return cursor.lastrowid
    
    def reinforce_memory(self,memory_id:int,new_source_text:str):
        """Updates the source text and bumps the last_accessed timestamp for an existing memory."""

        query = """
        UPDATE memories 
        SET source_text = ?, 
            last_accessed = CURRENT_TIMESTAMP
        WHERE id = ?
        """

        # Executing and committing the transaction
        with self._get_connection() as conn:
            cursor = conn.cursor() 
            cursor.execute(query,(new_source_text,memory_id)) 
            conn.commit()          
    
    def deprecate_memory(self,memory_id:int):
        """Soft deletes a memory(sets is_active to 0)""" 

        query = "UPDATE semantic_memories SET is_active = 0 WHERE id = ?"
        with self._get_connection() as conn:
            cursor=conn.cursor() 
            cursor.execute(query,(memory_id,)) 
            conn.commit()
    
    def touch_memory(self,memory_id:int,new_source_text:str):
        """Updates the access heartbeat when a memory is accessed or confirmed."""
        query = """UPDATE semantic_memories SET source_text=?,
                last_accessed = CURRENT_TIMESTAMP,
                strength = strength+1,
                importance_score = MIN(1.0, importance_score+0.05),
                -- Confidence Evolution: Closing 20 percent of the remaining gap to 1.0 (Asympotic Growth)--
                confidence = MIN(1.0, confidence + (1.0 - confidence) * 0.2)
                WHERE id = ?"""
        with self._get_connection() as conn:
            cursor = conn.cursor() 
            cursor.execute(query,(new_source_text,memory_id)) 
            conn.commit()

    def search_ranked_memories(self,search_term:str,limit:int=10)->list[dict]:
        """
        Search active memories using full text keyword match across subject,
        predicate, and object, ranking the results via unified cognitive scoring formula.
        """
        query = """
            SELECT *,
            -- The cognitive ranking formula --
            (importance_score * confidence * MIN(3.0,1.0+(strength-1.0)*0.2))/
            (1.0+(julianday('now')-julianday(last_accessed))*0.05) AS cognitive_rank
            FROM semantic_memories
            WHERE is_active = 1
            AND (subject LIKE ? OR predicate LIKE ? OR object LIKE ?)
            ORDER BY cognitive_rank DESC
            LIMIT ?
        """
        like_term = f"%{search_term.strip()}%"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query,(like_term,like_term,like_term,limit))
                columns = [column[0] for column in cursor.description]
                results = [dict(zip(columns,row)) for row in cursor.fetchall()]
            for res in results:
                res['cognitive_rank'] = round(res['cognitive_rank'],4)
            return results
        except Exception as e:
            logging.getLogger(__name__).error(f"Search failed: {e}") 
            return []
    
    def traverse_memory_graph(self,root_entity:str,limit:int=15) -> List[Dict[str,Any]]:
        """
        Performs a 1-degree graph traversal from a root entity.
        Returns direct matches(depth 0) and related cognitive memories(depth 1),
        ranked by cognitive strength
        """
        query = """
              WITH direct_matches AS (
                -- Depth 0: Exact or partial matches to the root entity
                SELECT id, subject, object
                FROM semantic_memories
                WHERE is_active = 1 
                  AND (subject LIKE ? OR object LIKE ?)
                ORDER BY importance_score DESC
                LIMIT 5 -- Bounding the start nodes so the graph doesn't explode
            ),
            connected_memories AS (
                -- Fetch the full rows for Depth 0 Nodes
                SELECT m.*, 0 AS traversal_depth
                FROM semantic_memories m
                JOIN direct_matches d ON m.id = d.id
                
                UNION
                
                -- Depth 1: Associative Nodes connected to Depth 0
                -- (e.g., sharing the same subject or object)
                SELECT m.*, 1 AS traversal_depth
                FROM semantic_memories m
                JOIN direct_matches d 
                  ON (m.subject = d.subject OR m.object = d.subject OR m.subject = d.object OR m.object = d.object)
                WHERE m.is_active = 1 AND m.id != d.id
            )
            SELECT *,
                -- Calculate Cognitive Rank for the entire associative web
                (importance_score * confidence * MIN(3.0, 1.0 + (strength - 1.0) * 0.2)) / 
                (1.0 + (julianday('now') - julianday(last_accessed)) * 0.05) AS cognitive_rank
            FROM connected_memories
            GROUP BY id  -- Deduplicate if a memory was reached via multiple associative paths
            ORDER BY traversal_depth ASC, cognitive_rank DESC
            LIMIT ?
            """
        like_term = f"%{root_entity.strip()}%"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor() 
                cursor.execute(query,(like_term,like_term,limit)) 
                columns = [column[0] for column in cursor.description] 
                results = [dict(zip(columns,row)) for row in cursor.fetchall()] 

                for res in results:
                    res['cognitive_rank'] = round(res['cognitive_rank'],4) 
                
                return results 
        except Exception as e:
            logging.getLogger(__name__).error(f"Graph traversal failed: {e}")
            return []

    def get_decayable_memories(self)->List[Dict[str,Any]]:
        """
        Returns active EPHEMERAL or SHORT_TERM memories with their
        dynamically calculated cognitive rank to evaluate for archival.
        """
        query="""
               SELECT *,
               (importance_score * confidence * MIN(3.0,1.0 + (strength - 1.0) * 0.2)) /
               (1.0 + (julianday('now') - julianday(last_accessed)) * 0.05) AS current_rank
               FROM semantic_memories
               WHERE is_active=1
               AND json_extract(metadata,'$.retention_policy') IN ('EPHEMERAL','SHORT_TERM')
        """
        with self._get_connection() as conn:
            cursor = conn.cursor() 
            cursor.execute(query) 
            columns = [column[0] for column in cursor.description] 
            results = [dict(zip(columns,row)) for row in cursor.fetchall()] 
        return results
    
    def archive_faded_memories(self,ids_to_archive:List[int]):
        """Bulk archives memories by turning off their respective active flag""" 
        if not ids_to_archive:
            return 
        placeholders = ','.join('?' for _ in ids_to_archive) 
        query = f"UPDATE semantic_memories SET is_active = 0 WHERE id IN ({placeholders})" 
        with self._get_connection() as conn:
            cursor = conn.cursor() 
            cursor.execute(query,ids_to_archive) 
            conn.commit() 
        logging.getLogger(__name__).info(f"Archived {len(ids_to_archive)} decayed memories from active state.")