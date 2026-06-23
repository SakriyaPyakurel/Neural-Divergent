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
            event_type TEXT NOT NULL,
            reason TEXT,
            confidence REAL,
            metadata TEXT,  -- Stored as a JSON string
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1 -- 1 for active, 0 for historically overwritten
        );
        """
        # Creating an index to lookups graph-like lightening fast
        index_query = """
        CREATE INDEX IF NOT EXISTS idx_triple ON semantic_memories(subject, predicate, object);
        """

        with self._get_connection() as conn:
            cursor = conn.cursor() 
            cursor.execute(query) 
            cursor.execute(index_query) 
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
    
    def insert_triple(self,subject:str,predicate:str,object_val:str,
                      event_type:str,reason:str=None,
                      confidence:float=1.0,metadata:Dict=None)->int:
        """Inserts a new semantic node/edge into the ledger."""

        query = """
        INSERT INTO semantic_memories 
        (subject, predicate, object, event_type, reason, confidence, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        meta_str = json.dumps(metadata) if metadata else "{}" 

        with self._get_connection() as conn:
            cursor= conn.cursor() 
            cursor.execute(query,(subject,predicate,object_val,event_type,reason,confidence,meta_str))
            conn.commit() 
            return cursor.lastrowid
    
    def deprecate_memory(self,memory_id:int):
        """Soft deletes a memory(sets is_active to 0)""" 

        query = "UPDATE semantic_memories SET is_active = 0 WHERE id = ?"
        with self._get_connection() as conn:
            cursor=conn.cursor() 
            cursor.execute(query,(memory_id,)) 
            conn.commit()
