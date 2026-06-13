import spacy
from typing import List 
from app.models.memory import SemanticRepresentation 

class LocalExtractionEngine:
    def __init__(self):
        # loading spacy's lightweight, , fast English dependency parser locally
        self.nlp = spacy.load('en_core_web_sm') 
    def extract_sirs(self,raw_message:str) -> List[SemanticRepresentation]:
        # processing the text for forming the dependency tree
        doc = self.nlp(raw_message) 
        sirs = [] 

        #Isolator Logic: If "because" is encountered, splitting the sentence 
        reason_text = None 
        if "because" in raw_message.lower():
            parts = raw_message.lower().split("because",1) 
            reason_text = parts[1].strip() 
        # Step 1: Scanning for the main neural divergent architectural action 
        for token in doc:
            #Checking if the token is a verb and matches our target actions
            if token.pos_ == "VERB" and token.lemma_ in ["switch","move","change","migrate"]:
                subject = "user" # it's default assumption for 1st-person chat
                obj = None 
                source = None 
                
                #Navigating the grammatical tree branching off the verb 
                for child in token.children:
                    if child.dep_ == "nsubj":
                        subject = child.text 
                    if child.text.lower() == "to":
                        obj = "".join([c.text for c in child.children]) 
                    if child.text.lower() == "from":
                        source = "".join([c.text for c in child.children]) 
                    # if found a destination successfully, building the first SIR 
                    if obj:
                      sirs.append(SemanticRepresentation(
                        subject=subject,
                        relationship="migrated_framework",
                        object=obj,
                        event_type="technology_migration",
                        reason=reason_text,
                        confidence=1.0, # High confidence based on explicit verb matching
                        metadata={"source": source} if source else {}
                    ))
        # Step 2: Scanning the isolator reason text 
        if reason_text:
            reason_doc = self.nlp(reason_text) 
            for token in reason_doc:
                if token.dep_ == "nsubj" and token.head.pos_ in ["ADJ", "VERB"]:
                    
                    # Building the secondary SIR representing the experience
                    sirs.append(SemanticRepresentation(
                        subject=token.text,
                        relationship="has_limitation",
                        object=token.head.text if token.head.pos_ == "ADJ" else "issue",
                        event_type="experience_evaluation",
                        reason=reason_text,
                        confidence=0.85, # Slightly lower confidence for inferred limitations
                        metadata={}
                    ))
                    
        return sirs