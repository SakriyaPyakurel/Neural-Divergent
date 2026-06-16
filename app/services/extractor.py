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

        # Passing candidates through the Semantic Transformer
        normalized_candidates = self.normalize_semantics(candidates) 

        # Passing normalized candidates to the builder
        final_sirs = self.build_candidate_sirs(normalized_candidates)

        # Enriching metadata
        for sir in final_sirs:
            sir.metadata["extraction_method"] = "dependency_parse_with_semantic_normalization" 
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

                subject = ""
                for child in token.children:
                    if child.dep_ in ["nsubj", "nsubjpass"]:
                        raw_subject = " ".join([t.text for t in child.subtree if t.i not in exclude_ids])
                        subject = raw_subject.replace(" - ", "-")
                        break
                
                #Using Fallback for compound subjects (conjunctions)
                if not subject:
                    if token.dep_ == "conj":
                        for child in token.head.children:
                            if child.dep_ in ["nsubj", "nsubjpass"]:
                                raw_subject = " ".join([t.text for t in child.subtree if t.i not in exclude_ids])
                                subject = raw_subject.replace(" - ", "-")
                                break
                    if not subject:
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
    
    def normalize_semantics(self, candidates: List[CandidateRelationship]) -> List[CandidateRelationship]:
        """Dynamically transforms raw grammatical relationships into generalized semantic truths."""
        normalized = []
        
        # Expanded user identity matrix
        USER_PRONOUNS = {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "ourselves"}

        for candidate in candidates:
            # Tokenize the subject phrase to scan for user-centric ownership
            subj_words = set(candidate.subject.lower().split())
            is_user_centric = bool(subj_words.intersection(USER_PRONOUNS))

            # State-of-Being Verbs (is/am/are/be)
            if candidate.verb in ["is", "am", "are", "be"]:
                
                if is_user_centric:
                    # ONLY runs if the phrase belongs to the user profile
                    subj_doc = self.nlp(candidate.subject)
                    core_trait_parts = []
                    
                    for token in subj_doc:
                        if token.dep_ == "ROOT" and token.pos_ in ["NOUN", "PROPN"]:
                            # Capturing critical adjectival descriptors (e.g., "favorite", "primary")
                            modifiers = [child.lemma_ for child in token.children if child.dep_ in ["amod", "compound"]]
                            core_trait_parts.extend(modifiers)
                            core_trait_parts.append(token.lemma_)
                            break
                    
                    if core_trait_parts:
                        candidate.subject = "user"
                        candidate.verb = "_".join(core_trait_parts)
                    else:
                        candidate.subject = "user"  # Safe fallback if no root noun is extracted
                        
                else:
                    # PATH B: Knowledge Fact Protection Firewall
                    pass
            else:
                # Standardize core operational actors down to the system user
                if candidate.subject.lower() in ["i", "we"]:
                    candidate.subject = "user"
            
            # Appending the clean, normalized candidate to our processing stream
            normalized.append(candidate)
            
        return normalized
                  

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
        # Calculating probabilistic certainity 
        for sir in sirs:
            # Simple rule based calculation
            base_score = 0.85 
            if sir.reason:
                base_score+= 0.10 # Higher confidence if reason is provided 
            sir.confidence = min(base_score,0.99) # Should Never be 1.0 
        return sirs


