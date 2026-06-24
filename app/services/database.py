import sqlite3 
import json 
from datetime import datetime 
from typing import List,Dict,Optional,Any

class MemoryDatabase:
    def __init__(self,db_path:str="neural_divergent.db"):
        self.db_path = db_path 
        self.setup_tables() 
    
    def _get_connection(self):
        """Creates and returns a database connection for Neural Divergent."""
        conn = sqlite3.connect(self.db_path) 
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
            source_text TEXT,               -- The raw sentence that triggered this extraction (Problem 3)
            reason TEXT,
            confidence REAL,
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
                      event_type:str,memory_category:str=None,
                      source_text:str=None,reason:str=None,
                      confidence:float=1.0,metadata:Dict=None,
                      supersedes_id: int = None)->int:
        """Inserts a new semantic node/edge into the ledger with full metadata."""

        query = """
         INSERT INTO semantic_memories 
        (subject, predicate, object, event_type, memory_category, source_text, reason, confidence, metadata, supersedes_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        meta_str = json.dumps(metadata) if metadata else "{}" 

        with self._get_connection() as conn:
            cursor= conn.cursor() 
            cursor.execute(query,(
                subject, predicate, object_val, event_type, 
                memory_category, source_text, reason, confidence, meta_str, supersedes_id
            ))
            conn.commit() 
            return cursor.lastrowid
    
    def deprecate_memory(self,memory_id:int):
        """Soft deletes a memory(sets is_active to 0)""" 

        query = "UPDATE semantic_memories SET is_active = 0 WHERE id = ?"
        with self._get_connection() as conn:
            cursor=conn.cursor() 
            cursor.execute(query,(memory_id,)) 
            conn.commit()
    
    def touch_memory(self,memory_id:int):
        """Updates the access heartbeat when a memory is accessed or confirmed."""
        query = "UPDATE semantic_memories SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?"
        with self._get_connection() as conn:
            cursor = conn.cursor() 
            cursor.execute(query,(memory_id,)) 
            conn.commit()
