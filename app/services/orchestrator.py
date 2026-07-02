import logging
from typing import List,Dict,Any

#Importing finalized cognitive modules
from database import MemoryDatabase 
from extractor import LocalExtractionEngine
from importance_engine import ImportanceEstimator,RetentionPolicy 
from decision_engine import MemoryDecisionEngine

logger = logging.getLogger("NeuralDivergent.Orchestrator") 

class NeuralDivergentOrchestrator:
    """
    The central cognitive pipeline coordinating:
    Extractor -> ImportanceEstimator -> MemoryDecisionEngine -> Database.

    This class handles thread-safe pipeline of text-to-memory operations.
    """
    def __init__(self,db:MemoryDatabase):
      logger.info("Initializing Neural Divergent Cognitive Pipeline...")
      self.db = db 
      self.extractor = LocalExtractionEngine()
      self.importance_estimator = ImportanceEstimator() 
      self.decision_engine = MemoryDecisionEngine(self.db) 

      # Any memory with a calculated importance prior below this threshold is immediately discarded as conversational noise.
      self.EPHEMERAL_THRESHOLD = 0.25
    
    def process_utterance(self,text:str,active_contexts:List[str] = None) -> List[Dict[str,Any]]:
       """
       Ingests a raw user utterance, extracts structural semantic representations,
       evaluates cognitive value, and routes them safely to the database.
       """
       logger.info(f"Ingesting Utterance: {text}") 
       results_ledger = [] 

       # Extraction(Linguistic Parsing) 
       sirs = self.extractor.extract_sirs(text) 

       if not sirs:
          logger.info("No actionable semantic triples have been extracted.") 
          return results_ledger
       
       # Processing each extracted structural triple 
       for sir in sirs:
          # Evaluating Importance Prior and Retention Policy
          importance_score, retention_policy = self.importance_estimator.evaluate(sir,active_contexts)

          # The Ephemeral Gate 
          if retention_policy == RetentionPolicy.EPHEMERAL or importance_score < self.EPHEMERAL_THRESHOLD:
            logger.info(f"Discarded as EPHEMERAL (Score: {importance_score}): [{sir.subject} -> {sir.relationship} -> {sir.object}]")
            results_ledger.append({
               "triple": (sir.subject,sir.relationship,sir.object),
               "action":"IGNORED",
               "reason":"Below ephemeral retention threshold",
               "importance_prior":importance_score,
               "retention_policy":retention_policy
            })
            continue 
          
          # Constructing metadata and going through Memory Decision Engine(MDE) 
          metadata_payload = sir.metadata.copy() if sir.metadata else {} 
          metadata_payload["importance_score"] = importance_score 
          metadata_payload["retention_policy"] = retention_policy 

          action,memory_id = self.decision_engine.process_extracted_memory(
             subject=sir.subject,
             predicate=sir.relationship,
             object_val = sir.object,
             event_type = metadata_payload.get("event_type","Observation"),
             memory_category=metadata_payload.get("memory_category","GENERAL"),
             source_text=sir.source_text,
             reason=sir.reason,
             confidence=sir.confidence,
             metadata=metadata_payload
          )

          logger.info(f"Storage Action: {action} (ID: {memory_id}) | [{sir.subject} -> {sir.relationship} -> {sir.object}] | Prior: {importance_score}")

          results_ledger.append({
            "triple":(sir.subject,sir.relationship,sir.object),
            "action":action,
            "memory_id":memory_id,
            "importance_score":importance_score,
            "retention_policy":retention_policy
            })
       return results_ledger

