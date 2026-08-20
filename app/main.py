from fastapi import FastAPI,Request
from contextlib import asynccontextmanager 
import logging 
from pathlib import Path
from dotenv import load_dotenv
import os
import uuid

# Importing the LLM SDK
from openai import AsyncOpenAI

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
from app.services.retrieval_planner import RetrievalPlanner

#importing required schemas 
from app.models.schemas import ChatRequest
# importing routers
from app.routers.memory import memory_router
from app.routers.graph import graph_router
from app.routers.cognitive import cognitive_router

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) 
load_dotenv()

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
       NEO4J_URL = os.getenv("NEO4J_URL", "bolt://127.0.0.1:7687")
       NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
       NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

       graph_manager = GraphManager(url=NEO4J_URL, user=NEO4J_USER, password=NEO4J_PASSWORD)
       graph_manager.connect()
       graph_manager.setup_schema()
       graph_ingester = GraphIngester(graph_manager=graph_manager, ontology_path=ONTOLOGY_PATH)

       # Initializing the Retrieval Planner and attaching it to app state
       retrieval_planner = RetrievalPlanner(graph_manager=graph_manager)

       app.state.graph_manager = graph_manager 
       app.state.graph_ingester = graph_ingester
       app.state.retrieval_planner = retrieval_planner

       # Initializing the Async LLM Client
       app.state.llm_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
              description="The Cognitive orchestrator and memory decision engine with context compression engine.",
              version="0.7.0",
              lifespan=lifespan)

# including the routers
app.include_router(memory_router)
app.include_router(graph_router)
app.include_router(cognitive_router)

@app.get("/",tags=["System"]) 
async def root():
    """Health check endpoint to verify the system is online.""" 
    return {
        "status":"online",
        "system":"Neural Divergent Engine",
        "ready":True
    }

@app.post("/api/v1/chat") 
async def chat_endpoint(request:ChatRequest,fastapi_req:Request):
   """
   Main entry point for conversational interaction. 
   Routes queries, pulls graph context, and constructs the LLM payload.
   """
   # Retrieving the planner,llm_client and graph Manager from the app state
   planner: RetrievalPlanner = fastapi_req.app.state.retrieval_planner
   llm_client: AsyncOpenAI = fastapi_req.app.state.llm_client
   graph_manager: GraphManager = fastapi_req.app.state.graph_manager

   # Logging incoming user turn to Neo4j sequential chain
   user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
   graph_manager.add_message_turn(
        user_id=request.user_id,
        message_id=user_msg_id,
        speaker="user",
        text=request.message
    )

   # Routing Intent & Extract Graph Context 
   route_type, memory_context = planner.prepare_context(
        user_id=request.user_id, 
        query=request.message,
        max_hops=2
   )

   # Constructing the System Prompt
   system_prompt = f"""
    You are Neural Divergent, an advanced cognitive AI.
    Your memory is backed by a deterministic Graph Database.
    
    === USER CONTEXT (GRAPH RETRIEVAL) ===
    {memory_context}
    ======================================
    
    Instructions:
    1. Answer the user's message naturally.
    2. Do NOT mention the graph database, Cypher, or nodes directly. 
    3. Treat the context above as organic facts you remember about the user.
    """

   try:
      # Executing the Async LLM call 
      response = await llm_client.chat.completions.create(
            model="gpt-4o-mini", # Using a fast/cheap model for standard chat
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message}
            ],
            temperature=0.7,
            max_tokens=500
        )
      final_answer = response.choices[0].message.content

      # Logging AI response turn to Neo4j sequential chain
      ai_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
      graph_manager.add_message_turn(
            user_id=request.user_id,
            message_id=ai_msg_id,
            speaker="assistant",
            text=final_answer
        )

      return {
            "status": "success",
            "route_taken": route_type,
            "response": final_answer,
            "messages_recorded": [user_msg_id, ai_msg_id]
        }
   except Exception as e:
        logger.error(f"LLM Generation Failed: {e}")
        return {"status": "error", "message": "Failed to generate cognitive response."}

   
   