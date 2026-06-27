import spacy
from typing import List,Dict,Any
from transformers import pipeline
from models.memory import SemanticRepresentation,CandidateRelationship 

class LocalExtractionEngine:
    def __init__(self):
        # loading spacy's lightweight, , fast English dependency parser locally
        self.nlp = spacy.load('en_core_web_sm') 
        print("Loading AI cognitive classifier. Can take a minute on first try.")
        self.classifier = pipeline("zero-shot-classification",model="facebook/bart-large-mnli") 
        # Available Memory categories(Kept small for now) 
        self.memory_categories = ["Identity", "Preference", "Project", "Knowledge", "Action"]
    
    def extract_sirs(self,raw_message:str) -> List[SemanticRepresentation]:
        """Main orchestation method"""
        doc,reason_text,exclude_ids = self.parse_message(raw_message) 

        candidates : List[CandidateRelationship] = []
        # Merging the splitted extractions 
        candidates.extend(self.detect_attribute_relationships(doc,reason_text,exclude_ids)) 
        candidates.extend(self.detect_action_relationships(doc,reason_text,exclude_ids))

        # Passing candidates through the Semantic Transformer
        normalized_candidates = self.normalize_semantics(candidates) 

        # Passing normalized candidates to the builder
        final_sirs = self.build_candidate_sirs(normalized_candidates)

        # Routing the clean data to the event_classifier 
        final_sirs = self.classify_event_type(final_sirs,raw_message)

        # Enriching metadata
        for sir in final_sirs:
            sir.metadata["extraction_method"] = "dependency_parse_with_semantic_normalization" 
        return self.assign_confidence(final_sirs) 
         
    def parse_message(self, raw_message: str):
        """Extracting the clause dynamically"""
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
        "Handles identity and knowledge both"""
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
        """Handles actions, preferences and compound statements""" 
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
            subj_words = set(candidate.subject.lower().replace("'", " ").replace("’", " ").split())
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
        """Converting structured intermediate models into final SIRs"""
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
    
    def classify_event_type(self,sirs:List[SemanticRepresentation],original_text:str)->List[SemanticRepresentation]:
        """Utilizes a Zero-Shot LLM to categorize the extracted memory into a database bucket"""

        # Determining user-centricity once using existing matrix
        USER_PRONOUNS = {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "ourselves"}
        words = set(original_text.lower().replace("'"," ").split())   
        is_user_centric = bool(words.intersection(USER_PRONOUNS))     
        
        # Utilizing core high-signal keywords 
        PREFERENCE_SIGNALS = {
            "favorite", "prefer", "love", "like", "dislike", "hate", "enjoy", "despise"
        }
        IDENTITY_SIGNALS = {
            # Core identity
            "name", "age", "birthday", "gender", "pronoun",
            # Professional identity
            "profession", "occupation", "role", "title", "owner", "developer",
            # Geographic/Background identity
            "hometown", "nationality", "citizen"
        }
        for sir in sirs:
            # Firewall check for 'Knowledge/Facts'
            if sir.relationship == 'is' and not is_user_centric:
                sir.event_type = "Knowledge" 
                sir.metadata['classification_confidence'] = 1.0000
                continue
            # Instantly catching obvious preferences or core identity markers
            if words.intersection(PREFERENCE_SIGNALS):
                sir.event_type = "Preference"
                sir.metadata['classification_confidence'] = 1.0000
                continue
            elif words.intersection(IDENTITY_SIGNALS) and "store" not in original_text.lower():
                sir.event_type = "Identity"
                sir.metadata['classification_confidence'] = 1.0000
                continue
            # For complex, dynamic action and project classifications
            label_map = {
                "working on a specific project, company, website, or business task": "Project",
                "performing a general action, event, or change": "Action"
            }
            # Passing the pristine original text so the model has maximum grammatical signal
            result = self.classifier(
                original_text,
                candidate_labels=list(label_map.keys()),
                hypothesis_template="This text describes someone {}.",
                multi_label=False
            )
            
            best_desc_label = result['labels'][0] 
            confidence = result['scores'][0]

            #updating the SIR
            sir.event_type = label_map[best_desc_label]
            sir.metadata['classification_confidence'] = round(confidence,4) 
        return sirs

    def assign_confidence(self,sirs:List[SemanticRepresentation]) -> List[SemanticRepresentation]:
        """
        Computes mathemathical confidence score for each extracted Semantic Information Representation(SIR)

        Evaluates:
        -> Syntatic Directness: Direct active clauses score higher than passive or compound classes
        -> Pronomial Ambiguity: Explicit names or direct 'user' mappings score higher than ambiguous nouns.
        -> Polarity Risk: Negated statements carry a slight penalty due to polarity risks in parsing.
        -> Explanatory  Context: Semantic reasons('because','since') increases confidence.
        """
        for sir in sirs:
            # Starting with a strong baseline confidence
            base_score = 0.80

            # Subject Quality and Ambiguity
            subj_lower = sir.subject.lower() 
            if subj_lower == "user":
                # Direct first person pronouns mapped to "user" are highly reliable
                base_score+=0.10
            elif len(subj_lower.split()) > 3:
                # Excessive long subjects indicate messy dependency subtree parsing
                base_score-=0.15

            # Relationship/Predicate complexity
            pred_words = sir.relationship.split("_")
            if any(w in ["is","am","was","are","were"] for w in pred_words):
                # Copular identity claims are gramatically stable and easy to extract
                base_score+=0.05
            if len(pred_words)>3:
                # Multi-word verbs combined with helper prepositions are noisier to parse
                base_score-=0.10

            # Polarity and negation risks
            if sir.metadata.get("negated",False):
                # Negated states(like not,never) are slightly prone to edge-case parsing errors
                base_score-=0.05

            # Casuality and reasoning Boost
            if sir.reason is not None:
                # Statements containing structured explanations (because,since,due to) are highly delibrate and carry rich cognitive intent
                base_score+=0.05

            # Short-circuit deterministic Knowledge Firewall
            if sir.subject != "user" and sir.relationship == "is" and sir.reason is None:
                base_score=1.00
               
            # Bounding confidence strictly between 0.10 and 1.00
            sir.confidence = round(max(0.10,min(1.00,base_score)),4)
        return sirs


