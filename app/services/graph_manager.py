import logging 
from neo4j import GraphDatabase 
from neo4j.exceptions import ServiceUnavailable 

logger = logging.getLogger('NeuralDivergent.GraphManager') 

class GraphManager:
    """
    Handles the connection and schema constraints for the Neo4j Graph Database.
    """
    def __init__(self,url="bolt://localhost:7687",user="neo4j",password="password"):
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
            self._initialize_constraints()
        except ServiceUnavailable as su:
            logger.error(f"Failed to connect to Graph Database: {su}") 
            raise 
    def close(self):
        """Closes connection pool."""
        if self.driver:
            self.driver.close() 
            logger.info("Graph Database connection closed.") 

    def _initialize_constraints(self):
        """
        Sets up the database constraints to ensure data integrity.
        Prevents duplicate entries (like multiple 'user' or 'Python' nodes).
        """
        cypher_queries = [
            # Ensuring the Subject (e.g., 'user') is unique
            "CREATE CONSTRAINT unique_subject IF NOT EXISTS FOR (s:Subject) REQUIRE s.name IS UNIQUE",
            
            # Ensuring the Object/Concept (e.g., 'Python', 'Kathmandu') is unique
            "CREATE CONSTRAINT unique_concept IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE"
        ]

        with self.driver.session() as session:
            for query in cypher_queries:
                try:
                    session.run(query) 
                except Exception as e:
                    logger.warning(f"Constraint issue: {e}") 
            logger.info("Graph constraints verified.")

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
            return self.execute_read(lambda tx: tx.run(query,parameters).data())



