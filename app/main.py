from services.extractor import LocalExtractionEngine
from services.database import MemoryDatabase
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
    print("Initializing Proto-Graph Database...")
    # Using a test db file so we don't clutter the main one
    db = MemoryDatabase("neural_divergent_test.db") 

    print("\n1. Inserting a new memory: 'User loves Python'")
    mem_id_1 = db.insert_triple(
        subject="user",
        predicate="favorite_language",
        object_val="Python",
        event_type="Preference",
        confidence=0.95,
        metadata={"source": "test_script"}
    )
    print(f"Inserted successfully! Assigned ID: {mem_id_1}")

    print("\n2. Retrieving the exact memory from disk...")
    exact_match = db.find_exact_triple("user", "favorite_language", "Python")
    if exact_match:
        print(f"Found: [{exact_match['subject']} -> {exact_match['predicate']} -> {exact_match['object']}]")
        print(f"Event Type: {exact_match['event_type']} | Metadata: {exact_match['metadata']}")

    print("\n3. Simulating a contradiction: 'User now loves Rust'")
    print("Deprecating the old memory (Setting is_active = 0)...")
    db.deprecate_memory(mem_id_1)
    
    print("Inserting the new truth...")
    mem_id_2 = db.insert_triple(
        subject="user",
        predicate="favorite_language",
        object_val="Rust",
        event_type="Preference",
        confidence=0.99
    )

    print("\n4. Querying the current active truth for 'favorite_language'...")
    active_memories = db.find_by_subject_and_predicate("user", "favorite_language")
    
    if len(active_memories) == 1:
        mem = active_memories[0]
        print(f"Current Active Memory: [{mem['subject']} -> {mem['predicate']} -> {mem['object']}]")
    else:
        print("Warning: Found multiple or zero active memories.")

if __name__ == "__main__":
    run_database_test()