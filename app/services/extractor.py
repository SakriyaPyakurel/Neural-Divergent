import spacy
from typing import List 
from models.memory import SemanticRepresentation,CandidateRelationship 

class LocalExtractionEngine:
    def __init__(self):
        # loading spacy's lightweight, , fast English dependency parser locally
        self.nlp = spacy.load('en_core_web_sm') 
    
    def extract_sirs(self,raw_message:str) -> List[SemanticRepresentation]:
        # The main orchestation method
        doc,reason_text,exclude_ids = self.parse_message(raw_message) 
        candidates : List[CandidateRelationship] = []

        # Merging the splitted extractions 
        candidates.extend(self.detect_attribute_relationships(doc,reason_text,exclude_ids)) 
        candidates.extend(self.detect_action_relationships(doc,reason_text,exclude_ids))

   
        final_sirs = self.build_candidate_sirs(candidates)
        return self.assign_confidence(final_sirs) 
         
    def parse_message(self, raw_message: str):
        # Extracting the clause dynamically
        doc = self.nlp(raw_message)
        reason_text = None
        exclude_ids = set()
        for token in doc:
            if token.dep_ == "mark" and token.text.lower() in ["because", "since", "as", "given"]:
                reason_verb = token.head
                reason_text = " ".join([t.text for t in reason_verb.subtree]).strip()
                exclude_ids = {t.i for t in reason_verb.subtree}
                break
            elif token.text.lower() == "due":
                reason_text = " ".join([t.text for t in token.subtree]).strip()
                exclude_ids = {t.i for t in token.subtree}
                break
                
        return doc, reason_text, exclude_ids
    
    def detect_attribute_relationships(self,doc,reason_text:str,exclude_ids:set)->List[CandidateRelationship]:
        # handles identity and knowledge both
        relationships = [] 
        for token in doc:
            # Ignoring tokens living inside the reason clause
            if token.i in exclude_ids:
                continue

            if token.lemma_ == "be":
                # Detecting negation 
                is_negated = any(child.dep_ == "neg" for child in token.children)

                # Extracting the full subject branch 
                subject = ""
                for child in token.children:
                    if child.dep_ in ["nsubj","nsubjpass"]:
                        raw_subject = " ".join([t.text for t in child.subtree if t.i not in exclude_ids])
                        subject = raw_subject.replace(" - ", "-")
                        break
               
                # Extracting the full attribute branch
                obj = ""
                for child in token.children:
                    if child.dep_ in ["attr","acomp"]:
                        raw_obj = " ".join([t.text for t in child.subtree if t.i not in exclude_ids])
                        obj = raw_obj.replace(" - ", "-")
                        break
                
                if subject and obj:
                    relationships.append(CandidateRelationship(
                        subject=subject,
                        verb="is",
                        object=obj,
                        reason=reason_text,
                        is_negated=is_negated
                    ))
        return relationships
    
    def detect_action_relationships(self,doc,reason_text:str,exclude_ids:set)->List[CandidateRelationship]:
        # handles actions, preferences and compound statements 
        relationships = [] 
        for token in doc:
            # masking out reason clause elements
            if token.i in exclude_ids:
               continue

            # looking for action verbs
            if token.pos_ == "VERB" and token.lemma_ != "be":
                # Skip infinitive modifier verbs
                if any(c.text.lower() == "to" and c.dep_ == "aux" for c in token.children):
                    continue
                # Detecting negation 
                is_negated = any(child.dep_ == "neg" for child in token.children)

                # Finding the subject 
                subject_tokens = [c.text for c in token.children if c.dep_ in ["nsubj","nsubjpass"]] 
                subject = " ".join(subject_tokens)

                # handling compound statements 
                if not subject:
                    if token.dep_ == "conj":
                        head_subj = [c.text for c in token.head.children if c.dep_ in ["nsubj","nsubjpass"]]
                        subject = " ".join(head_subj) if head_subj else "user" 
                    else:
                        subject = "user" 

                # Collecting all predicate components
                obj_components = []
                # Sorting children by their position in the sentence to maintain correct English order
                sorted_children = sorted(token.children, key=lambda x:x.i)
                for child in sorted_children:
                    if child.i in exclude_ids:
                        continue
                    # Capturing direct objects, prepositional phases along with clausal complements
                    if child.dep_ in ["dobj", "pobj", "prep", "oprd", "ccomp"]:
                        component_text = " ".join([t.text for t in child.subtree if t.i not in exclude_ids])
                        if component_text:
                            obj_components.append(component_text)
                if obj_components:
                    # Cleaning up spaces around punctuation
                    obj = " ".join(obj_components).replace(" - ","-")
                    relationships.append(CandidateRelationship(
                        subject=subject,
                        verb=token.lemma_,
                        object=obj,
                        reason=reason_text,
                        is_negated=is_negated
                    ))

        return relationships

    def build_candidate_sirs(self,candidates:List[CandidateRelationship])->List[SemanticRepresentation]:
        # Converting structured intermediate models into final SIRs
        sirs = [] 
        for candidate in candidates:
            # Apply negation to the metadata and adjust the relationship mapping
            meta = {"negated":candidate.is_negated}
            final_relationship = f"not_{candidate.verb}" if candidate.is_negated else candidate.verb
            
            sirs.append(SemanticRepresentation(
                subject = candidate.subject,
                relationship=final_relationship,
                object=candidate.object,
                event_type=None, # will be decided later on by the classifier
                reason=candidate.reason,
                confidence = 0.0, # Placeholder, will be handled in the assign_confidence stage
                metadata=meta
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


