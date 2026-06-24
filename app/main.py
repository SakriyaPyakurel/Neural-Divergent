from services.extractor import LocalExtractionEngine
from services.database import MemoryDatabase
import time
if __name__ == "__main__":
    extractor = LocalExtractionEngine()
    
    test_suite = [
        # --- IDENTITY ---
        "My name is Sakriya.",
        "I am a single owner of an e-commerce platform.",
        "I'm the lead developer for All In One Store.",
        
        # --- PREFERENCES ---
        "My favorite programming language is Python.",
        "Our primary category is Home Essentials.",
        "I prefer wireframe designs over full mockups.",
        
        # --- KNOWLEDGE (The Firewall) ---
        "The capital of Nepal is Kathmandu.",
        "Python is a high-level programming language.",
        "Data Flow Diagrams show system architecture.",
        
        # --- ACTIONS ---
        "I built a custom NLP extraction engine.",
        "We expanded the catalog to include electronics and fashion.",
        "I extracted 5000 active IATA airline codes from the PDF.",
        
        # --- NEGATIONS ---
        "I do not use Java for backend development.",
        "We didn't launch the new server yesterday.",
        "I never test the database in production.",
        
        # --- REASONS & CAUSALITY ---
        "I switched to Django because FastAPI was difficult to scale.",
        "We delayed the launch due to a major database crash.",
        "I built a deterministic engine since LLM APIs are too expensive.",
        
        # --- THE EDGE CASES (The Breakers) ---
        "Python is my favorite language.", # The Inverse Semantic (Expected to act like Knowledge)
        "I love Python and use it for machine learning.", # Compound Action
        "My team's primary language is Python." # Complex possession
    ]

    print("Output Validation of NEURAL DIVERGENT V1 VALIDATION SUITE...\n")
    
    for i, sentence in enumerate(test_suite, 1):
        print(f"--- Test {i} ---")
        print(f"Input: {sentence}")
        sirs = extractor.extract_sirs(sentence)
        if not sirs:
            print("Extracted: [NO RELATIONSHIPS DETECTED]")
        for sir in sirs:
            print(f"Extracted: subject='{sir.subject}' relationship='{sir.relationship}' object='{sir.object}' reason='{sir.reason}' event_type='{sir.event_type}' confidence={sir.metadata['classification_confidence']} negated={sir.metadata['negated']}")
        print("-" * 50 + "\n")

def run_database_test():
    print("Initializing Upgraded Proto-Graph Database...")
    # Using a test db file so we don't clutter the main one
    db = MemoryDatabase("neural_divergent_test.db") 

    print("\nInserting a new memory: 'User loves Python'")
    source_sentence_1 = "My favorite programming language is Python."
    mem_id_1 = db.insert_triple(
        subject="user",
        predicate="favorite_language",
        object_val="Python",
        event_type="Preference",
        memory_category="PREFERENCE",
        source_text=source_sentence_1,
        confidence=0.95,
        metadata={"source": "test_script"}
    )
    print(f"Inserted successfully! Assigned ID: {mem_id_1}")

    print("\nRetrieving the exact memory from disk...")
    exact_match = db.find_exact_triple("user", "favorite_language", "Python")
    if exact_match:
        print(f"Found Node Action: [{exact_match['subject']} -> {exact_match['predicate']} -> {exact_match['object']}]")
        print(f"  - Category: {exact_match['memory_category']}")
        print(f"  - Source Text: '{exact_match['source_text']}'")
        print(f"  - Metadata: {exact_match['metadata']}")
        print(f"  - Last Accessed Initially: {exact_match['last_accessed']}")

    print("\n3. Simulating memory retrieval (Touching the heartbeat)...")
    # Wait briefly to show a timestamp difference
    time.sleep(1)
    db.touch_memory(mem_id_1)
    updated_match = db.find_exact_triple("user", "favorite_language", "Python")
    print(f"  - Last Accessed Updated: {updated_match['last_accessed']}")

    print("\n4. Simulating a contradiction: 'User now loves Rust'")
    print("Deactivating the old memory (Setting is_active = 0)...")
    db.deprecate_memory(mem_id_1)
    
    print("Inserting the new truth and linking it to supersede the old one...")
    source_sentence_2 = "My favorite programming language is Rust."
    mem_id_2 = db.insert_triple(
        subject="user",
        predicate="favorite_language",
        object_val="Rust",
        event_type="Preference",
        memory_category="PREFERENCE",
        source_text=source_sentence_2,
        confidence=0.99,
        supersedes_id=mem_id_1  #Linking the version chain!
    )
    print(f"Inserted successfully! Assigned ID: {mem_id_2} (Supersedes ID: {mem_id_1})")

    print("\nQuerying the current active truth for 'favorite_language'...")
    active_memories = db.find_by_subject_and_predicate("user", "favorite_language")
    
    if len(active_memories) == 1:
        mem = active_memories[0]
        print(f"Current Active Memory: [{mem['subject']} -> {mem['predicate']} -> {mem['object']}]")
        print(f"  - Linked Supersedes ID: {mem['supersedes_id']}")
    else:
        print(f"Warning: Found {len(active_memories)} active memories.")

    print("\nSimulating Graph Node Search (Retrieving related subject memories)...")
    # inserting another active identity trait to see if it groups together
    db.insert_triple(
        subject="user",
        predicate="name",
        object_val="Sakriya",
        event_type="Identity",
        memory_category="IDENTITY",
        source_text="My name is Sakriya."
    )
    
    all_user_memories = db.find_related_memories("user")
    print(f"Found {len(all_user_memories)} active relationships originating from subject 'user':")
    for r in all_user_memories:
        print(f"  - (user) -[{r['predicate']}]-> ({r['object']}) | Category: {r['memory_category']}")

if __name__ == "__main__":
    run_database_test()