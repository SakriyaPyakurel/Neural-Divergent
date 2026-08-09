from fastapi import FastAPI
from contextlib import asynccontextmanager 
import logging 
from pathlib import Path
import os

# Importing services 
from app.services.database import MemoryDatabase 
from app.services.importance_engine import OntologyLoader,ImportanceEstimator 
from app.services.decision_engine import MemoryDecisionEngine
from app.services.extractor import LocalExtractionEngine 
from app.services.semantic_classifier import SemanticClassifier
from app.services.orchestrator import NeuralDivergentOrchestrator 
from app.services.decay_engine import CognitiveDecayEngine
from app.services.embedding_engine import EmbeddingEngine
from app.services.semantic_normalizer import SemanticNormalizer
from app.services.graph_manager import GraphManager 
from app.services.graph_ingester import GraphIngester

# importing routers
from app.routers.memory import memory_router
from app.routers.graph import graph_router

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) 

@asynccontextmanager
async def lifespan(app:FastAPI):
    """Application lifecycle manager of Neural Divergent.""" 
    logging.info("Booting up Neural Divergent Cognitive Engine...") 
    graph_manager = None 
    decay_engine = None
    try:
       # Initializing the database from the file 
       db_file = Path("db.txt")
       db_path = None
       if db_file.exists():
         db_path = db_file.read_text().strip() or None
       db = MemoryDatabase(db_path=db_path) if db_path is not None else MemoryDatabase()
       app.state.db = db 
       logger.info(f"Using cognitive database: {db_path}")

       ONTOLOGY_PATH = "app/ontology/predicate_ontology.json"
       SEMANTIC_PATH = "app/ontology/semantic_normalization.json"

       # Initializing Graph Database Service(Neo4j)
       NEO4J_URL = os.getenv("NEO4J_URL", "bolt://localhost:7687")
       NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
       NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

       graph_manager = GraphManager(url=NEO4J_URL, user=NEO4J_USER, password=NEO4J_PASSWORD)
       graph_manager.connect()
       graph_ingester = GraphIngester(graph_manager=graph_manager, ontology_path=ONTOLOGY_PATH)

       app.state.graph_manager = graph_manager 
       app.state.graph_ingester = graph_ingester

       # loading dependencies(Ontology,Estimator,Decision Engine,Extractor,semantic classifier)
       registry = OntologyLoader.get_registry(ONTOLOGY_PATH) 
       importance_estimator = ImportanceEstimator(ontology_path=ONTOLOGY_PATH)
       decision_engine = MemoryDecisionEngine(db=db,registry=registry) 
       extractor = LocalExtractionEngine()
       classifier = SemanticClassifier()
       embedder = EmbeddingEngine()
       normalizer = SemanticNormalizer(rules_path=SEMANTIC_PATH)

      # Initializing the orchestrator and attach to state (needed for ingestion) 
       orchestrator = NeuralDivergentOrchestrator(
        extractor=extractor,
        classifier=classifier,
        importance_estimator=importance_estimator,
        decision_engine=decision_engine,
        embedder=embedder,
        normalizer=normalizer,
        graph_ingester=graph_ingester
        )
       app.state.embedder = embedder
       app.state.orchestrator = orchestrator

       # Spawning the Cognitive Decay Engine
       # Checking every hour(3600s), archiving if rank drops below 0.12
       decay_engine = CognitiveDecayEngine(db=db,check_interval_seconds=3600,decay_threshold=0.12)
       await decay_engine.start()
       app.state.decay_engine = decay_engine
       logger.info("Neural Divergent initialized successfully with Graph layer.")
       yield 
    except Exception as e:
       logger.exception(f"Failed to initialize Neural Divergent: {e}")
       raise
    finally:
       logger.info("Shutting down Neural Divergent.") 
       if decay_engine is not None:
          await decay_engine.stop()
       if graph_manager is not None:
          graph_manager.close()

app = FastAPI(title="Neural-Divergent API",
              description="The Cognitive orchestrator and memory decision engine.",
              version="0.6.0",
              lifespan=lifespan)

# including the routers
app.include_router(memory_router)
app.include_router(graph_router)

@app.get("/",tags=["System"]) 
async def root():
    """Health check endpoint to verify the system is online.""" 
    return {
        "status":"online",
        "system":"Neural Divergent Engine",
        "ready":True
    }