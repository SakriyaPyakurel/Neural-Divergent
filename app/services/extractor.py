import spacy
from typing import List 
from app.models.memory import SemanticRepresentation 

class LocalExtractionEngine:
    def __init__(self):
        # loading spacy's lightweight, , fast English dependency parser locally
        self.nlp = spacy.load('en_core_web_sm') 
    
    def extract_sirs(self,raw_message:str) -> List[SemanticRepresentation]:
        # The main orchestation method
        doc,reason_text = self.parse_message(raw_message) 
        raw_relationships = self.detect_relationships(doc,reason_text) 
        candidate_sirs = self.build_candidate_sirs(raw_relationships)  
        final_sirs = self.assign_confidence(candidate_sirs) 

        return final_sirs 
         
    def parse_message(self,raw_message:str):
        # Stage 1: cleaning text and building a gramatical tree
        doc = self.nlp(raw_message) 
        reason_text = None 
        for token in doc:
            if token.dep_ == "mark" and token.text.lower() in ["because","since","as"]:
                reason_root = token.head 
                # Extracting entire grammatical tree for the subclause 
                reason_text = " ".join([t.text for t in reason_root.subtree]).strip() 
                break 
        return doc,reason_text 
    
    def detect_relationships(self,doc,reason_text:str)->List[dict]:
        # Stage 2: Dynamically extracting Subject-Verb-Object
        relationships = [] 
        for token in doc:
            if token.pos_ in ["VERB","AUX"]:
                # Finding the subject (example: 'I','User','The system')
                subject_tokens = [c.text for c in token.children if c.dep_ in ["nsubj","nsubjpass"]]
                subject = " ".join(subject_tokens) if subject_tokens else "user" 
                # Finding the object 
                object_tokens = [c.text for c in token.children if c.dep_ in ["dobj","pobj","attr","acomp"]] 
                obj = " ".join(object_tokens) 
                # Handling prepositions attached to the verb 
                prep = " ".join([c.text for c in token.children if c.dep_ == "prep"]) 
                full_verb = f"{token.lemma_} {prep}".strip() if prep else token.lemma_ 

                # if successfully found a relationship then capturing it
                if obj:
                    relationships.append({
                        "type":"dynamic", #later on classifier figures out the category
                         "subject":subject,
                         "verb":full_verb,
                         "object":obj,
                         "reason":reason_text
                    })
        return relationships

    def build_candidate_sirs(self,raw_relationships:List[dict])->List[SemanticRepresentation]:
        # Step 3: Normalizing raw data into pydantic semantic relationships
        sirs = [] 
        for rel in raw_relationships:
            if not rel["object"]:# Skipping malformed relationships
                continue 

            # Mapping the raw data into structured schema
            sirs.append(SemanticRepresentation(
                subject = rel["subject"],
                relationship=rel["verb"],
                object=rel["object"],
                event_type=None, # will be decided later on by the classifier
                reason=rel["reason"],
                confidence = 0.0, # Placeholder, will be handled in the assign_confidence stage
                metadata={}
            ))
        return sirs 
    
    def assign_confidence(self,sirs:List[SemanticRepresentation]) -> List[SemanticRepresentation]:
        # Step 4: calculating probabilistic certainity 
        for sir in sirs:
            # Simple rule based calculation
            base_score = 0.85 
            if sir.reason:
                base_score+= 0.10 # Higher confidence if reason is provided 
            sir.confidence = min(base_score,0.99) # Should Never be 1.0 
        return sirs


