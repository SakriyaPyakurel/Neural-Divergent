Neural Divergent

A Deterministic Cognitive Memory Architecture for AI Systems

Version: 0.7.x (Current Development)

1. Overview

Neural Divergent is a deterministic cognitive memory architecture engineered to improve how AI systems extract, structure, store, retrieve, and reason over conversational information.

Unlike traditional LLM memory solutions that rely heavily on raw vector embeddings or repeated prompt injection, Neural Divergent executes deterministic semantic reasoning locally before an LLM is ever queried.

Core Philosophy

Convert natural language to structured semantic knowledge ──► Think before retrieving ──► Retrieve before generating

Not an LLM Replacement: Neural Divergent operates as an intelligent cognitive layer positioned between human input and Large Language Models.

Key Benefits:

Reduced Token Consumption: Eliminates redundant contextual fluff before sending prompts.

Deterministic Memory: Builds consistent, rule-backed factual representations.

Explainable Reasoning: Every memory operation produces a traceable audit ledger.

Contradiction Management: Detects and resolves conflicting knowledge statefully.

Graph Evolution: Native graph storage using dynamic user-tethered relationship models.

2. Project Vision

Current AI assistants suffer from context window degradation: as conversations grow, models hallucinate relationships, drop early context, or waste tokens reprocessing static facts.

Neural Divergent addresses this by maintaining an explicit, evolving memory graph.

┌────────────────────────────────────────────────────────────────────────┐
│                        TRADITIONAL ARCHITECTURE                        │
│                                                                        │
│ Human Conversation ──► Entire Context ──► LLM Call ──► Repeat Forever  │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│                      NEURAL DIVERGENT APPROACH                         │
│                                                                        │
│ Human Conversation                                                     │
│        │                                                               │
│        ▼                                                               │
│ Deterministic Cognitive Pipeline                                       │
│        │                                                               │
│        ▼                                                               │
│ Persistent Semantic Memory Graph (Neo4j)                               │
│        │                                                               │
│        ▼                                                               │
│ Targeted Hybrid Retrieval ──► Minimal Prompt ──► LLM Execution         │
└────────────────────────────────────────────────────────────────────────┘

3. Design Philosophy

Principle

Description

Deterministic First

High-cost LLMs are never used for tasks that deterministic algorithms (dependency parsing, rule-based pruning, canonicalization) can perform faster and without variance.

Token Optimization

Minimize prompt payload sizes by extracting core semantics and filtering conversational noise before retrieval.

Explainable Auditing

Every stored memory item tracks its origin, valuation weight, active state, and replacement history.

Modular Isolation

Each cognitive engine performs exactly one task along the execution pipeline.

4. Cognitive Pipeline Flow

[User Message Input]
        │
        ▼
[1. Local Extraction Engine] ──────► (Grammar to Raw Syntax / Skips Nested Verb Fragments)
        │
        ▼
[2. Semantic Normalizer] ─────────► (Syntax to Canonical Concepts via JSON Rules)
        │
        ▼
[3. Memory Refiner] ──────────────► (Batch Deduplication & Stop-Verb Pruning)
        │
        ▼
[4. Importance Estimator] ────────► (Declarative Valuation & Ontology Mapping)
        │
        ▼
[5. Memory Decision Engine] ──────► (Graph Consistency & Embedding Deduplication)
        │
        ▼
[6. Graph Ingester Engine] ───────► (User Node Tethering & Dynamic Edge Routing)
        │
        ▼
[7. Native Knowledge Graph] ──────► (Neo4j Persistent Graph Database)
        │
        ▼
[8. Retrieval & Activation] ──────► (Hybrid Graph Traversal & Context Synthesis)

5. Component Breakdown

1. Local Extraction Engine

Purpose: Transforms unformatted natural language into deterministic syntactic structures.

Responsibilities: Dependency parsing, linguistic normalization, Subject-Intent-Relationship (SIR) construction, nested verb complement pruning (xcomp, ccomp, advcl filtering to prevent fragment double-dipping), reason extraction, and negation detection.

Output: Raw semantic triples containing subject, relationship, object, confidence, negation_flag, reason, and source_text.

2. Semantic Normalizer (Cognitive Language Layer)

Purpose: Maps raw syntactic dependencies to canonical concepts via external JSON configuration (semantic_normalization.json).

Execution Pipeline (4-Pass Engine):

Pass 1: Subject Canonicalization (e.g., standardizing variations of personal pronouns to canonical system users).

Pass 2: Phrase Pattern Matching (high-context multi-word maps).

Pass 3: Object Noise Reduction & Case Standardization.

Pass 4: Predicate Rule Application.

3. Memory Refiner (Cognitive Pruner)

Purpose: Evaluates batches of normalized triples extracted from a single message block to filter noise before valuation.

Responsibilities:

Deduplication: Merges identical semantic meanings within the current turn.

Ontology Enforcement: Elevates ontology-backed relations over raw grammatical constructs.

Stop-Verb Pruning: Discards low-value helper verbs (is, was, make, do) when richer concepts exist in the same context.

4. Importance Estimator & Declarative Ontology

Purpose: Calculates retention viability using predicate_ontology.json.

Ontology Schema Example:

{
  "working_on": {
    "category": "project",
    "importance": "MEDIUM",
    "retention": "SHORT_TERM",
    "exclusive": false,
    "allow_multiple": true,
    "supports_negation": false,
    "supports_reason": true,
    "graph_node_type": "ACTIVITY"
  }
}

Capabilities: Zero-code ontology adjustments, confidence weighting, cognitive valuation scores, reasoning bonuses, and negation penalties.

5. Memory Decision Engine

Purpose: Enforces strict logical consistency across the active memory graph using rule-sets and embedding-assisted fuzzy deduplication.

Decision Types:

NEW: Store novel, verified information.

REINFORCED: Increments the confidence and weight of existing facts.

SUPERSEDED: Soft-deletes or detaches superseded facts when an active contradiction occurs.

IGNORED: Discards redundant or low-value input.

REJECTED_LOW_CONFIDENCE: Drops data beneath cognitive thresholds.

6. Graph Ingester & Native Knowledge Graph (Neo4j)

Purpose: Persists validated cognitive facts as structured graph nodes and edges.

Responsibilities:

Binds atomic concepts directly to specific user entities (User node $\xrightarrow{RELATIONSHIP}$ Concept node).

Executes Cypher queries dynamically based on normalized verbs and predicate ontologies.

Prevents standalone fragmented concept nodes from polluting the graph topology.

7. Orchestrator

Purpose: Pure pipeline coordinator containing zero business logic. Delegates processing sequentially across injected cognitive engines and returns a structured processing ledger.

6. API Specification

Base Route: /api/v1/memory

Method

Endpoint

Description

POST

/ingest

Executes full NLP extraction, normalization, pruning, valuation, decision, and graph ingestion. Returns execution ledger.

GET

/active

Fetches active graph relationships for specific subject + predicate pairs.

GET

/related/{subject}

Returns all connected active graph nodes bound to a given subject node.

GET

/search

Ranked memory search leveraging importance, confidence, recency, and reinforcement.

GET

/traverse

Multilevel Cypher graph traversal (Depth 0 matches $\rightarrow$ Depth N linked entities).

7. Feature Implementation Status

Local deterministic NLP extraction engine

Nested/complement verb fragment suppression (xcomp parsing fix)

4-Pass configuration-driven semantic normalization

Cognitive memory refinement & stop-verb pruning

Structured SPO (Subject-Predicate-Object) memory model

Confidence scoring, negation detection, and reason extraction

Declarative predicate ontology (Categories, Node Types, Policies)

Multi-tier retention policies (EPHEMERAL, SHORT_TERM, LONG_TERM)

Vector embedding-assisted fuzzy duplicate detection

Contradiction handling & soft supersession tracking

Memory reinforcement & frequency tracking

Native Knowledge Graph Backend (Neo4j Integration)

Graph Ingester with dynamic user node tethering

Active truth, related memory, and ranked retrieval endpoints

Associative graph traversal engine

Hybrid Graph + Vector retrieval orchestrator

8. Architectural Comparison

Dimension

Standard RAG / Vector Memory

Neural Divergent Architecture

Ingestion

Raw text chunking $\rightarrow$ Direct embedding

Deterministic NLP parsing $\rightarrow$ Concept Normalization $\rightarrow$ Pruning

Storage

Unstructured vector indices

Native Knowledge Graph (Neo4j $User \xrightarrow{Pred} Concept$)

Determinism

Low (Probabilistic similarity)

High (Rule-backed logic & ontology validation)

Contradictions

Stores conflicting text chunks

Statefully detaches or supersedes outdated facts

Explainability

Black box similarity scores

Fully audited state transitions & extraction ledgers

Token Usage

High (Includes conversational noise)

Extremely Low (Strictly retrieves active canonical graph triples)

9. Development Roadmap

Phase 8: Context & Prompt Synthesis (Next)

Automated context assembly engine.

Dynamic prompt generation based on active cognitive graph state.

Selective memory compression for token budget bounds.

Phase 9: Cognitive Planning & Goal Management

Goal tracking and task decomposition.

Self-updating memory chains and reflective reasoning cycles.

Multi-agent memory synchronization.