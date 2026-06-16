from services.extractor import LocalExtractionEngine
test_cases = [
    # Test 1: Compound statement with a shared subject
    "I manage All In One Store and expanded the catalog to include Home Essentials.",
    
    # Test 2: Negation combined with a causal clause
    "I do not sell groceries because the profit margins are too low.",
    
    # Test 3: Identity statement with a complex attribute
    "My primary business is a single owner e-commerce platform.",
    
    # Test 4: Action with a prepositional reason
    "We migrated the server to AWS due to frequent downtime.",

    "Capital of Nepal is Kathmandu",

    "My name is Sakriya Pyakurel"
]
engine = LocalExtractionEngine() 
for i, text in enumerate(test_cases, 1):
    print(f"\n--- Test Case {i} ---")
    print(f"Input: {text}")
    results = engine.extract_sirs(text)
    for res in results:
        print(f"Extracted: {res}")