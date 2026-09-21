import logging 
from neo4j import GraphDatabase 
from neo4j.exceptions import ServiceUnavailable 

logger = logging.getLogger('NeuralDivergent.GraphManager') 

class GraphManager:
    """
    Handles the connection and schema constraints for the Neo4j Graph Database.
    """
    def __init__(self,url="bolt://127.0.0.1:7687",user="neo4j",password="password123"):
        self.url = url 
        self.user = user 
        self.password = password
        self.driver = None 

    def connect(self):
        """Establishes connection pool to the database.""" 
        try:
            self.driver = GraphDatabase.driver(self.url,auth=(self.user,self.password))
            self.driver.verify_connectivity() 
            logger.info("Successfully connected to Graph Database.")
            self._initialize_schema()
        except ServiceUnavailable as su:
            logger.error(f"Failed to connect to Graph Database: {su}") 
            raise 
    def close(self):
        """Closes connection pool."""
        if self.driver:
            self.driver.close() 
            logger.info("Graph Database connection closed.") 

    def _initialize_schema(self):
        """
        Initializes constraints and indexes for the Cognitive Memory Graph.
        Uses IF NOT EXISTS so it is completely safe to run on every startup.
        """
        queries = [
            # Uniqueness Constraints (Prevents duplicates)
            "CREATE CONSTRAINT unique_subject IF NOT EXISTS FOR (s:Subject) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT unique_concept IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
            "CREATE CONSTRAINT msg_id_unique IF NOT EXISTS FOR (m:Message) REQUIRE m.message_id IS UNIQUE",
            "CREATE CONSTRAINT ded_id_unique IF NOT EXISTS FOR (d:Deduction) REQUIRE d.deduction_id IS UNIQUE",
            
            # Performance Indexes (Speeds up filtering and lookups)
            "CREATE INDEX deduction_active_idx IF NOT EXISTS FOR (d:Deduction) ON (d.is_active)",
            "CREATE INDEX concept_name_idx IF NOT EXISTS FOR (c:Concept) ON (c.name)",
            "CREATE INDEX user_active_idx IF NOT EXISTS FOR (u:User) ON (u.is_active)"
        ]
        
        with self.driver.session() as session:
            for query in queries:
                try:
                    session.run(query)
                except Exception as e:
                    # Logs a warning but doesn't crash the app if one index fails
                    logger.warning(f"Schema setup warning for query [{query}]: {e}") 
                    
            logger.info("Graph constraints and indexes verified.")

    def execute_write(self,query,parameters=None):
        """
        Helper method to execute cypher write transactions.
        """
        with self.driver.session() as session:
            return session.execute_write(lambda tx: tx.run(query, parameters).data())

    def execute_read(self,query,parameters=None):
        """
        Helper method to execute cypher read transactions.
        """
        with self.driver.session() as session:
            return session.execute_read(lambda tx: tx.run(query, parameters).data())

    def add_message_turn(self, user_id: str, message_id: str, speaker: str, text: str):
        """Appends a new message to the user's sequential conversation chain."""
        query = """
        // Ensuring the user exists
        MERGE (u:User {user_id: $user_id})
        
        // Finding the end of the current conversation chain
        WITH u
        OPTIONAL MATCH (u)-[:SPOKE]->(last_m:Message)
        WHERE NOT (last_m)-[:NEXT_MESSAGE]->()
        
        // Creating the new message node
        CREATE (new_m:Message {
            message_id: $message_id, 
            speaker: $speaker, 
            text: $text, 
            timestamp: datetime()
        })
        MERGE (u)-[:SPOKE]->(new_m)
        
        // Linking the previous message to the new one (if it exists)
        WITH last_m, new_m
        WHERE last_m IS NOT NULL
        CREATE (last_m)-[:NEXT_MESSAGE]->(new_m)
        """
        
        with self.driver.session() as session:
            session.run(query, user_id=user_id, message_id=message_id, speaker=speaker, text=text)

    def add_deduction(self, deduction_id: str, statement: str, confidence: float, linked_concepts: list, old_deduction_id: str = None):
        """Stores a new logical deduction and optionally supersedes an outdated one."""
        query = """
        // Creating the new active deduction
        MERGE (d:Deduction {deduction_id: $deduction_id})
        SET d.statement = $statement, 
            d.confidence = $confidence, 
            d.is_active = true, 
            d.created_at = datetime()
            
        // Linking it to the concepts it was inferred from
        WITH d
        UNWIND $linked_concepts AS concept_name
        MATCH (c:Concept {name: concept_name})
        MERGE (c)-[:INFERRED_FROM]->(d)
        """
        
        supersede_query = """
        // Deactivating old logic and mapping the evolution
        MATCH (old_d:Deduction {deduction_id: $old_deduction_id})
        MATCH (new_d:Deduction {deduction_id: $new_deduction_id})
        SET old_d.is_active = false
        CREATE (new_d)-[:SUPERSEDES]->(old_d)
        """
        
        with self.driver.session() as session:
            session.run(query, deduction_id=deduction_id, statement=statement, confidence=confidence, linked_concepts=linked_concepts)
            
            if old_deduction_id:
                session.run(supersede_query, old_deduction_id=old_deduction_id, new_deduction_id=deduction_id)



