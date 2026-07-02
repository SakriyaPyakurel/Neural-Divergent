import logging
from typing import List,Dict,Any,Tuple,Optional
from dataclasses import dataclass

#Importing finalized cognitive modules
from database import MemoryDatabase 
from extractor import LocalExtractionEngine
from importance_engine import ImportanceEstimator,RetentionPolicy,OntologyLoader
from decision_engine import MemoryDecisionEngine

logger = logging.getLogger("NeuralDivergent.Orchestrator") 

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

class NeuralDivergentOrchestrator:
   """
    The central cognitive pipeline coordinator.
    Delegates work strictly to injected cognitive engines.
   """
   def __init__(self,extractor:LocalExtractionEngine,
                importance_estimator:ImportanceEstimator,
                decision_engine: MemoryDecisionEngine,
                ontology_path:str = "app/ontology/predicate_ontology.json"):
      """Utilizes the tools handed to it rather than creating them."""
      logger.info("Initializing Neural Divergent Cognitive Pipeline...")
      self.extractor = extractor
      self.importance_estimator = importance_estimator 
      self.decision_engine = decision_engine 

      # Loading the shared declerative ontology to map categories on the fly 
      self.ontology_path = ontology_path
      self.ontology = OntologyLoader.get_registry(ontology_path)

   def ingest(self,text:str,active_contexts:List[str] = None) -> List[MemoryProcessingResult]:
      """
      Master entry point.
      Ingests raw input, evaluates cognitive worth, routes to long term storage if appropriate.
      """
      logger.info(f"Ingesting '{text}'") 
      results_ledger = [] 

      # Extracting SIRs
      sirs = self._extract(text) 
      if not sirs:
          logger.info("No actionable semantic triples extracted.")
          return results_ledger
       
       # Processing each extracted structural triple 
      for sir in sirs:
         # Evaluating Importance Prior and Retention Policy
         importance_score, retention_policy = self._evaluate(sir,active_contexts)

         # The Ephemeral Gate 
         if retention_policy == RetentionPolicy.EPHEMERAL:
            logger.info(f"Discarded as EPHEMERAL (Score: {importance_score}): [{sir.subject} -> {sir.relationship} -> {sir.object}]")
            results_ledger.append({
               "triple": (sir.subject,sir.relationship,sir.object),
               "action":"IGNORED",
               "reason":"Classified as Conversational Noise.",
               "importance_prior":importance_score,
               "retention_policy":retention_policy
            })
            continue 
          
         # Storing
         result = self._store(sir,importance_score,retention_policy)
         results_ledger.append(result) 

      return results_ledger
   
   def _extract(self,text:str)->List[Any]:
      """Delegates linguistic Parsing to the Extraction Engine."""
      return self.extractor.extract_sirs(text) 

   def _evaluate(self,sir:Any,active_contexts:List[str])->Tuple[float,str]:
      """Delegates cognitive valuation to the Importance Estimator.""" 
      return self.importance_estimator.evaluate_representation(sir,active_contexts) 

   def _store(self,sir:Any,importance_score:float,retention_policy:str) -> MemoryProcessingResult:
      """Packages metadata and delegates conflict resolution to the Decision Engine."""
      # Appending evaluation metrics to the metadata envelope
      metadata_payload = sir.metadata.copy() if sir.metadata else {} 
      metadata_payload["importance_prior"] = importance_score 
      metadata_payload["retention_policy"] = retention_policy

      # Looking up configured properties of the predicate from ontology registry
      predicate_config = self.ontology.get(sir.relationship.lower(),{})

      # Looks up the configurations from predicate_ontology.json, defaulting if not found
      event_type = (metadata_payload.get("event_type") or predicate_config.get("graph_node_type") or "SENSORY_NODE")
      memory_category = (metadata_payload.get("memory_category") or predicate_config.get("category","GENERAL") or "GENERAL").upper()

      # updating the metadata payload
      metadata_payload["event_type"] = event_type
      metadata_payload["memory_category"] = memory_category

      action,memory_id = self.decision_engine.process_extracted_memory(
         subject=sir.subject,
         predicate=sir.relationship,
         object_val=sir.object,
         event_type=event_type,
         memory_category=memory_category,
         source_text=sir.source_text,
         reason = sir.reason,
         confidence=sir.confidence,
         metadata=metadata_payload
      )

      logger.info(f"Storage Action: {action} (ID: {memory_id}) | Prior: {importance_score}")
      
      return MemoryProcessingResult(
         subject=sir.subject,
         predicate=sir.relationship,
         object_val=sir.object,
         action=action,
         memory_id=memory_id,
         importance_prior=importance_score,
         retention_policy=retention_policy
      )