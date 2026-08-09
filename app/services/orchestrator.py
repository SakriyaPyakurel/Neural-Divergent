from typing import List,Dict,Any,Optional
from dataclasses import dataclass
import logging
from sentence_transformers import SentenceTransformer
#Importing finalized cognitive modules
from app.services.extractor import LocalExtractionEngine
from app.services.semantic_classifier import SemanticClassifier
from app.services.importance_engine import ImportanceEstimator,RetentionPolicy,OntologyLoader
from app.services.decision_engine import MemoryDecisionEngine
from app.services.embedding_engine import EmbeddingEngine
from app.services.semantic_normalizer import SemanticNormalizer
from app.services.graph_ingester import GraphIngester
from app.services.memory_refiner import  MemoryRefiner
from app.models.memory import MemoryCategory
from app.models.schemas import MemoryAction

logger = logging.getLogger('NeuralDivergent.Orchestrator')

@dataclass
class MemoryProcessingResult:
   """Standardized ledger entry for any memory processed by the pipeline."""
   subject:str
   predicate:str 
   object_val:str 
   action:str 
   memory_id:Optional[int] = None
   importance_prior: float = 0.0 
   retention_policy: str = "EPHEMERAL"
   reason:Optional[str] = None
   confidence: float = 1.0
   graph_synced: bool = False 
   graph_metadata:Optional[Dict[str,Any]] = None

   def to_dict(self) -> Dict[str, Any]:
        """Converts the dataclass to the exact dictionary format the FastAPI router expects."""
        return {
            "triple": {
                "subject": self.subject,
                "predicate": self.predicate,
                "object": self.object_val
            },
            "action": self.action,
            "memory_id": self.memory_id,
            "importance_prior": self.importance_prior,
            "retention_policy": self.retention_policy,
            "reason":self.reason,
            "confidence":self.confidence,
            "graph_synced":self.graph_synced,
            "graph_metadata":self.graph_metadata
        }

class NeuralDivergentOrchestrator:
   """
    The central cognitive pipeline coordinator.
    Delegates work strictly to injected cognitive engines.
   """
   def __init__(self,extractor:LocalExtractionEngine,
                classifier:SemanticClassifier,
                importance_estimator:ImportanceEstimator,
                decision_engine: MemoryDecisionEngine,
                embedder:EmbeddingEngine,
                normalizer:SemanticNormalizer,
                graph_ingester:GraphIngester,
                ontology_path:str = "app/ontology/predicate_ontology.json"
                ):
      """Utilizes the tools handed to it rather than creating them."""
      logger.info("Initializing Neural Divergent Cognitive Pipeline...")
      self.extractor = extractor
      self.classifier = classifier
      self.importance_estimator = importance_estimator 
      self.decision_engine = decision_engine 
      self.embedding_engine = embedder
      self.normalizer = normalizer
      self.graph_ingester = graph_ingester
      self.refiner = MemoryRefiner()

      # Loading the shared declerative ontology to map categories on the fly 
      self.ontology_path = ontology_path
      self.ontology = OntologyLoader.get_registry(ontology_path)

   def process_utterance(self,text:str,active_contexts:List[str] = None) -> List[MemoryProcessingResult]:
      """
      Master entry point.
      Ingests raw input, evaluates cognitive worth, routes to long term storage if appropriate.
      """
      logger.info('Orchestrator is well and running.')
      results_ledger = [] 

      # Extracting SIRs
      sirs = self.extractor.extract_sirs(text) 
      if not sirs:
          logger.info("No actionable semantic triples extracted.")
          return results_ledger
      
      # Caching classification results per message context to avoid repeating work
      cached_category: MemoryCategory = None 
      cached_event_type: str = None 
      cached_confidence: float = None
       
      # Processing each extracted structural triple 
      normalized_candidates = []
      for sir in sirs:
         # Converting raw syntax into cannonical cognitive concepts
         raw_candidate = {
             "subject": sir.subject,
             "predicate": sir.relationship,
             "object": sir.object,
             "original_sir":sir
         }
         normalized = self.normalizer.normalize(raw_candidate)
         normalized_candidates.append(normalized)

         # Memory refinement(pruning pass) - discarding noisy/weak triples if strong ontology matches exist in the batch
         ontology_keys = set(self.ontology.keys()) 
         refined_candidates = self.refiner.refine(normalized_candidates,ontology_keys)

         # Cognitive processing pass - Processing only the refined high value candidates 
         for r_candidate in refined_candidates:
           sir = r_candidate["original_sir"]
           # Overwriting grammatical extraction with refined cognitive concepts
           sir.subject = r_candidate.get("subject") or ""
           sir.relationship = r_candidate.get("predicate") or ""
           sir.object = r_candidate.get("object") or ""
         # looking up the configured properties of the predicate from the declerative ontology
         predicate_config = self.ontology.get(sir.relationship.lower(),{})

         #Extracting category from ontology if it exists
         ontology_category = predicate_config.get("category") 
         ontology_event_type = predicate_config.get("graph_node_type") 

         # Deterministic Firewall Gate 
         if ontology_category and ontology_category.upper() in MemoryCategory.__members__:
            # High-confidence match. Bypassing the zero-shot classifier completely
            memory_category = MemoryCategory[ontology_category.upper()]
            event_type = ontology_event_type or "Fact" 
            classification_confidence = 1.0000
            logger.info(f"Deterministic category hit via ontology for predicate '{sir.relationship}' : {memory_category}")
         else:
            if cached_category is None:
               cached_category,cached_event_type,cached_confidence = self.classifier.resolve_ambiguity(text)

            memory_category = cached_category 
            event_type = cached_event_type 
            classification_confidence = cached_confidence 
            logger.info(f"Fallback invoked for predicate '{sir.relationship} : {memory_category}'") 
         
         # Injecting evaluated categorical types directly into SIRs
         sir.event_type = event_type
         metadata_payload = sir.metadata.copy() if sir.metadata else {} 
         metadata_payload["classification_confidence"] = classification_confidence

         # Computing mathemathically unified pipeline confidence 
         sir.confidence = round((sir.confidence*0.6) + (classification_confidence * 0.4),4) 

         # Evaluating cognitive importance and retention 
         importance_score,retention_policy=self.importance_estimator.evaluate_representation(sir,active_contexts) 
         metadata_payload["importance_prior"] = importance_score 
         metadata_payload["retention_policy"] = retention_policy 

         if retention_policy == RetentionPolicy.EPHEMERAL:
            result = MemoryProcessingResult(
               subject=sir.subject,predicate=sir.relationship,object_val=sir.object,
               action="IGNORED",importance_prior=importance_score,retention_policy="EPHEMERAL"
            )
            results_ledger.append(result.to_dict())
            continue
         semantic_sentence = f"{sir.subject.strip()} {sir.relationship.strip().lower()} {sir.object.strip()} REASON: {sir.reason}"
         vector_embeddings = self.embedding_engine.generate_embeddings(semantic_sentence)
         # Context Resolution and Storage via Decision Engine
         action,memory_id = self.decision_engine.process_extracted_memory(
            subject=sir.subject,
            predicate=sir.relationship,
            object_val=sir.object,
            importance_score=importance_score,
            event_type=event_type,
            memory_category=memory_category.value,
            source_text=sir.source_text,
            reason=sir.reason,
            confidence=sir.confidence,
            metadata=metadata_payload,
            vector_embedding=vector_embeddings
         )
         # GRAPH INGESTION LAYER
         # Pushing to Neo4j only if the Decision Engine created or altered the memory
         valid_graph_actions = [
                MemoryAction.NEW.value, 
                MemoryAction.REINFORCED.value, 
                MemoryAction.SUPERSEDED.value
            ]

         graph_synced = False 
         graph_metadata = None 

         if action in valid_graph_actions:
            try:
               graph_result = self.graph_ingester.ingest_memory(
                        subject=sir.subject,
                        predicate=sir.relationship,
                        object_val=sir.object,
                        memory_category=memory_category.value,
                        importance_score=importance_score,
                        memory_id=memory_id,
                        metadata=metadata_payload
                    )
               if graph_result:
                  graph_synced = True 
                  graph_metadata = graph_result.get("rel_data", {})
                  logger.info(f"Graph synchronized for memory_id {memory_id}. Edge Count: {graph_metadata.get('reinforcement_count', 1)}")
            except Exception as e:
               logger.error(f"Failed to ingest memory {memory_id} into Graph: {e}")
         else:
            logger.debug(f"Skipping graph ingestion for memory_id {memory_id} (Action: {action}).")

         result = MemoryProcessingResult(sir.subject,predicate=sir.relationship,object_val=sir.object,
                                                      action=action,memory_id=memory_id,importance_prior=importance_score,retention_policy=retention_policy,
                                                      reason=sir.reason,confidence=sir.confidence,
                                                      graph_synced=graph_synced,
                                                      graph_metadata=graph_metadata)
         results_ledger.append(result.to_dict())
         
      return results_ledger
         