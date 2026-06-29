from typing import Dict,Any,Tuple,Optional 
from services.database import MemoryDatabase

class MemoryDecisionEngine:
    """
    The cognitive orchestrator of Neural Divergent.
    Evaluates incoming semantic extractions against existing active memories.
    """
    def __init__(self,db:MemoryDatabase):
        self.db = db 
        # Traits that represent exclusive characteristics (only one can be active at a time)
        self.single_value_predicates = {
            "name", 
            "age",
            "favorite_language", 
            "favorite_programming_language",
            "primary_business",
            "primary_category",
            "birthday",
            "nationality"
        }
    
    def _handle_duplicate(self,subject:str,predicate:str,object_val:str) -> Optional[int]:
        """The Duplicate Check.
        Checks if the exact fact [Subject -> Predicate -> Object] is already actively known.
        
        Returns:
        The memory ID if it's a duplicate (after updating its heartbeat)
        or None if the fact is new or different""" 
        # Search the database for an exact active match.
        duplicate_record = self.db.find_exact_triple(subject,predicate,object_val) 

        if duplicate_record:
            # "touch" it to update the last_accessed timestamp, proving it is still relevant
            self.db.touch_memory(duplicate_record['id']) 
            return duplicate_record['id']
        return None

    def _handle_contradiction(self,subject:str,predicate:str,object_val:str,
                              event_type:str=None,memory_category:str=None,
                              source_text:str=None,reason:str=None,
                              confidence:float=1.0,metadata:Dict = None) -> Optional[int]:
        """Contradiction Check
        Handles updates to single-value traits(e.g. Changing favorite language from Python to Rust)
        
        Returns:
        The NEW memory id if a contradiction was found and superseded
        or None if the predicate allows multiple values or is entirely new.
        """ 
        # Proceeding only if this is a trait that can only one active value
        if predicate not in self.single_value_predicates:
            return None 
        
        # Looking for any existing active memory with the same subject and predicate
        existing_records = self.db.find_by_subject_and_predicate(subject,predicate) 

        if existing_records:
            # Targeting the current active truth(there should be only one) 
            old_memory = existing_records[0] 

            # The system knows the object_val is different because it already passed the duplication check
            # Deactivating the old memory
            self.db.deprecate_memory(old_memory['id']) 

            # Inserting the new memory, linking it to the old one for reference
            new_id = self.db.insert_triple(
                subject=subject,
                predicate=predicate,
                object_val=object_val,
                event_type=event_type,
                memory_category=memory_category,
                source_text=source_text,
                reason=reason,
                confidence=confidence,
                metadata=metadata,
                supersedes_id=old_memory['id'] # The chronological link
            )
            return new_id
        
        # Returning None if no active record was found meaning this is a new knowledge
        return None
    
    def _handle_novel(self,subject:str,predicate:str,object_val:str,
                      event_type:str=None,memory_category:str = None,
                      source_text:str=None,reason:str=None,
                      confidence:float=1.0,metadata:dict=None) -> int:
        """Novel entry
        Inserts an entirely new relationship node into the Proto-Graph database
        
        Returns:
        The newly assigned memory ID.
        """
        return self.db.insert_triple(
            subject=subject,
            predicate=predicate,
            object_val=object_val,
            event_type=event_type,
            memory_category=memory_category,
            source_text=source_text,
            reason=reason,
            confidence=confidence,
            metadata=metadata
        )
    
    def process_extracted_memory(self,subject:str,predicate:str,object_val:str,
                                 event_type:str=None,memory_category:str=None,
                                 source_text:str=None,reason:str=None,
                                 confidence:float=1.0,metadata:Dict=None) -> Tuple[str,int]:
        """
        Central cognitive router of the Memory Decision Engine

        Returns:
            A tuple of (action_taken,memory_id)
        """
        # Confidence Gate(Rejecting hallucinations before they enter storage) 
        if confidence<0.60:
            return "REJECTED_LOW_CONFIDENCE",None
        # Cleaning and normalizing strings to prevent whitespace-mismatched duplicates
        subj_clean = subject.strip() 
        pred_clean = predicate.strip().lower() 
        obj_clean = object_val.strip() 

        # Duplicate Check
        dup_id = self._handle_duplicate(subj_clean,pred_clean,obj_clean) 
        if dup_id is not None:
            return "DUPLICATE",dup_id 
        
        # Contradiction/Overwrite Check
        superseded_id = self._handle_contradiction(
            subject=subj_clean,
            predicate=pred_clean,
            object_val=obj_clean,
            event_type=event_type,
            memory_category=memory_category,
            source_text=source_text,
            reason=reason,
            confidence=confidence,
            metadata=metadata
        )
        if superseded_id is not None:
            return "SUPERSEDED",superseded_id
        
        # Novel Entry 
        new_id = self._handle_novel(
            subject=subj_clean,
            predicate=pred_clean,
            object_val=obj_clean,
            event_type=event_type,
            memory_category=memory_category,
            source_text=source_text,
            reason=reason,
            confidence=confidence,
            metadata=metadata
        )
        return "NEW",new_id
