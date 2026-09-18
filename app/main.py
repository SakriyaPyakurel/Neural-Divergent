from fastapi import FastAPI,Request,BackgroundTasks,Depends,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager 
import logging 
from pathlib import Path
from dotenv import load_dotenv
import os
import uuid

# Importing the LLM SDK
from openai import AsyncOpenAI

# importing config settings
from app.config import settings

import truststore
truststore.inject_into_ssl()

# Importing services 
from app.services.database import MemoryDatabase 
from app.core.security import verify_nd_api_key
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
from app.routers.goals import goals_router
from app.routers.auth import auth_router

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
       ONTOLOGY_PATH = "app/ontology/predicate_ontology.json"
       SEMANTIC_PATH = "app/ontology/semantic_normalization.json"

       db = MemoryDatabase() 
       app.state.db = db

       graph_manager = GraphManager(url=settings.NEO4J_URL, user=settings.NEO4J_USER, password=settings.NEO4J_PASSWORD.get_secret_value())
       graph_manager.connect()
       graph_manager.setup_schema()
       graph_ingester = GraphIngester(graph_manager=graph_manager, ontology_path=ONTOLOGY_PATH)

       # Initializing the Retrieval Planner and attaching it to app state
       retrieval_planner = RetrievalPlanner(graph_manager=graph_manager)

       app.state.graph_manager = graph_manager 
       app.state.graph_ingester = graph_ingester
       app.state.retrieval_planner = retrieval_planner

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
       decay_engine = CognitiveDecayEngine(
            db=db,
            check_interval_seconds=3600,
            decay_threshold=0.12
        )
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

# Accessibility Layer: CORS Setup
app.add_middleware(
   CORSMiddleware,
   allow_origins=["*"],
   allow_credentials=True,
   allow_methods=["*"],
   allow_headers=["*"])

async def process_deductions_background(user_id: str, message_text: str, orchestrator):
    try:
        logger.info(f"[Background Task] Extracting knowledge triples for {user_id}...")
        results = orchestrator.process_utterance(
            text=message_text,
            active_contexts=[user_id]
        )
        logger.info(f"[Background Task] Processed {len(results)} memory entries into Graph Memory.")
    except Exception as e:
        logger.error(f"[Background Task Failed] Error processing deductions: {e}")


@app.get("/",tags=["System"]) 
async def root():
    """Health check endpoint to verify the system is online.""" 
    return {
        "status":"online",
        "system":"Neural Divergent Engine",
        "ready":True
    }

# Include all application routers (Auth included first)
app.include_router(auth_router)
app.include_router(memory_router)
app.include_router(graph_router)
app.include_router(cognitive_router)
app.include_router(goals_router)


@app.post("/api/v1/chat", dependencies=[Depends(verify_nd_api_key)], tags=["Chat Interface"]) 
async def chat_endpoint(request: ChatRequest, fastapi_req: Request, background_tasks: BackgroundTasks):
    """
    Main entry point for conversational interaction. 
    Routes queries, pulls graph context, and constructs the LLM payload.
    """
    # Extracting secure user_id set by verify_nd_api_key on request.state
    authenticated_user_id = fastapi_req.state.user_id

    planner: RetrievalPlanner = fastapi_req.app.state.retrieval_planner
    graph_manager: GraphManager = fastapi_req.app.state.graph_manager
    orchestrator: NeuralDivergentOrchestrator = fastapi_req.app.state.orchestrator
    # Instantiating dynamic LLM client from incoming payload
    try:
       user_llm_client = AsyncOpenAI(
                api_key=request.llm_api_key,
                base_url=request.llm_url,
                timeout=30.0)
    except:
        logger.error(f"Failed to initialize dynamic LLM client: {e}")
        raise HTTPException(status_code=400, detail="Invalid LLM client configuration.")

    # Logging incoming user turn to Neo4j using authenticated user ID
    user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    graph_manager.add_message_turn(
        user_id=authenticated_user_id,
        message_id=user_msg_id,
        speaker="user",
        text=request.message
    )

    # Routing Intent & Extracting Graph Context 
    route_type, memory_context = planner.prepare_context(
        user_id=authenticated_user_id, 
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
    """

    try:
        response = await user_llm_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        final_answer = response.choices[0].message.content

        # Logging AI response turn to Neo4j
        ai_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        graph_manager.add_message_turn(
            user_id=authenticated_user_id,
            message_id=ai_msg_id,
            speaker="assistant",
            text=final_answer
        )

        # Queue background extraction & graph learning
        background_tasks.add_task(
            process_deductions_background,
            user_id=authenticated_user_id,
            message_text=request.message,
            orchestrator=orchestrator
        )

        return {
            "status": "success",
            "route_taken": route_type,
            "response": final_answer,
            "messages_recorded": [user_msg_id, ai_msg_id],
            "background_learning_queued": True
        }
    except Exception as e:
        logger.error(f"Dynamic LLM Call Failed for user {authenticated_user_id}: {e}")
        raise HTTPException(
            status_code=502, 
            detail="Failed to receive a response from the configured LLM endpoint. Check your API Key, URL, and Model Name."
        )