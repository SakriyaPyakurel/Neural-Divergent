Neural Divergent

A Deterministic Cognitive Memory Architecture for AI Systems

Version: 0.5.x (Current Development)

Overview

Neural Divergent is a deterministic cognitive memory architecture designed to improve how AI assistants understand, store, organize, retrieve and reason over conversational information.

Unlike traditional LLM memory systems that rely heavily on embeddings or repeated prompt injection, Neural Divergent attempts to perform as much reasoning as possible locally before an LLM is ever involved.

The philosophy is simple:

Convert natural language into structured semantic knowledge first.

Think before retrieving.

Retrieve before generating.

The project is not intended to replace Large Language Models.

Instead, it functions as a cognitive layer sitting between human conversation and the LLM.

This architecture allows:

significantly lower token consumption

deterministic memory formation

explainable reasoning

contradiction management

semantic graph growth

future knowledge graph migration

Project Vision

Current AI assistants largely depend on context windows. Once the conversation becomes large, they begin forgetting previous information, hallucinating relationships, or repeatedly consuming tokens to rediscover already known facts.

Neural Divergent aims to solve this by introducing an explicit cognitive memory architecture. Instead of repeatedly asking an LLM to understand everything again, the system builds a structured memory graph that continuously evolves.

Long-term goal:

Human Conversation

↓

Deterministic Cognitive Pipeline

↓

Persistent Semantic Memory

↓

Targeted Retrieval

↓

LLM Reasoning

Instead of:

Conversation

↓

Entire Prompt

↓

LLM

↓

Repeat Forever

Design Philosophy

The architecture follows several core principles:

Deterministic First

Whenever deterministic algorithms can solve a problem, they should always execute before expensive probabilistic AI.

Examples:

dependency parsing

relationship extraction

contradiction detection

duplicate detection

semantic normalization

cognitive pruning

These operations should never require an LLM.

Minimize Token Consumption

Every unnecessary token sent to an LLM costs money. Neural Divergent attempts to reduce conversational redundancy before retrieval.

The objective is:

Conversation

↓

Structural Information Representation

↓

Relevant Memory Retrieval

↓

Minimal Prompt

↓

LLM

Explainability

Every stored memory should answer:

Why was it stored?

Where did it come from?

How important is it?

Why does it still exist?

Why did it replace another memory?

Modular Architecture

Each component performs exactly one responsibility. No module performs another module's job. This keeps the pipeline maintainable and independently testable.

Current Cognitive Pipeline

User Message

↓

Local Extraction Engine (Grammar to Syntax)

↓

Semantic Normalizer (Syntax to Cognitive Concepts)

↓

Memory Refiner (Batch Pruning & Deduplication)

↓

Importance Estimator (Cognitive Valuation)

↓

Memory Decision Engine (Graph Consistency)

↓

Proto-Graph Memory Database

↓

Retrieval APIs

↓

(Future) Embedding Retrieval / LLM

Component Overview

1. Local Extraction Engine

Purpose

Transform raw natural language into deterministic syntactic representations.

Responsibilities

dependency parsing

linguistic normalization

SIR (Subject-Intent-Relationship) construction

reason extraction

negation detection

Output

Raw Semantic Representation containing subject, relationship, object, confidence, metadata, reason, and source text.

2. Semantic Normalizer (Cognitive Language Layer)

Purpose

Transforms raw syntax dependencies into stable, canonical cognitive concepts. Driven by external JSON configurations (semantic_normalization.json) for zero-code expandability.

Responsibilities (4-Pass Pipeline)

Pass 1: Subject Canonicalization (e.g., standardizing pronouns)

Pass 2: Phrase Pattern Matching (High-context mapping)

Pass 3: Object Noise Reduction & Canonical Casing (e.g., "interested in science" -> "science")

Pass 4: Predicate Rule Application

3. Memory Refiner (Cognitive Pruner)

Purpose

Evaluates batches of normalized triples from a single source text to filter out noise before valuation.

Responsibilities

Deduplication: Prevents identical semantic meanings from flooding the pipeline.

Ontology Enforcement: Promotes "Strong" (ontology-backed) triples over "Weak" grammatical constructs.

Stop-Verb Pruning: Aggressively discards weak syntactic helpers (e.g., "is", "was", "make", "do") if better cognitive concepts exist in the same sentence.

4. Importance Estimator & Declarative Ontology

Purpose

Estimate whether information deserves memory based on a declarative ontology (predicate_ontology.json).

Ontology Schema Example

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


Benefits

Zero-code ontology updates

Richer categorization (identity, experience, project, preference)

Explicit Node types for future Knowledge Graphs

Confidence weighting, reasoning bonuses, and negation penalties

5. Memory Decision Engine

Purpose

Maintain strict logical consistency inside the memory graph, now assisted by Vector Embeddings for fuzzy-duplicate detection.

Current Actions:

NEW: Novel information stored.

REINFORCED: Existing fact observed again (increases weight).

SUPERSEDED: Existing truth contradicted and overwritten.

IGNORED: Trivial or duplicate data dropped.

REJECTED_LOW_CONFIDENCE: Data fell below the cognitive threshold.

6. Proto-Graph Memory Database

Current implementation: SQLite
Schema: semantic_memories

Stores:

subject, predicate, object, importance, retention, confidence, metadata, reason, event type, memory category, reinforcement count, timestamps, active state, superseded links.

The database behaves like a lightweight semantic graph (Subject -> Relationship -> Object) preparing for an eventual migration to Neo4j or Memgraph.

7. Orchestrator

The central pipeline coordinator. It contains no business logic. Instead, it delegates work strictly to injected cognitive engines (Extractor -> Normalizer -> Refiner -> Estimator -> Decision -> Storage) and returns the processing ledger.

Current API

Base Route: /api/v1/memory

POST /ingest

Processes natural language into cognitive memory via the full extraction, normalization, pruning, and decision pipeline. Returns a ledger of actions taken (NEW, REINFORCED, PRUNED, etc.).

GET /active

Returns active truth for Subject + Predicate.

GET /related/{subject}

Returns connected active memories for a given subject.

GET /search

Ranked semantic memory retrieval considering importance, confidence, reinforcement, and recency.

GET /traverse

Associative graph traversal (Depth 0 matches -> Depth 1 connected memories).

Features Implemented

✓ Local deterministic NLP extraction

✓ 4-Pass Semantic Normalization (JSON-Driven)

✓ Cognitive Memory Refinement & Stop-Verb Pruning

✓ Subject–Predicate–Object representation

✓ Confidence estimation & Negation handling

✓ Reason extraction

✓ Rich Declarative Predicate Ontology (Categories & Node Types)

✓ Retention policies (EPHEMERAL, SHORT_TERM, LONG_TERM)

✓ Duplicate detection (Embedding Assisted)

✓ Contradiction handling & Soft supersession

✓ Reinforcement learning of existing memories

✓ Proto-graph database

✓ Active truth, Related memory, and Ranked retrieval APIs

✓ Graph traversal

✓ Robust Embedding retrieval layer (Phase 5)

✓ Hybrid graph + vector search orchestration (Phase 5)

✓ Semantic ranking & Memory activation thresholds (Phase 5)

What Makes Neural Divergent Different

Most AI memory systems:

Conversation ↓ Embedding ↓ Vector Search ↓ LLM

Neural Divergent:

Conversation ↓ Grammar ↓ Cognitive Semantics ↓ Pruning ↓ Importance ↓ Memory Decisions ↓ Graph ↓ Retrieval ↓ LLM

The architecture actively filters noise, standardizes concepts, and reasons about data structure before embedding or involving an LLM.

Next up Roadmap

Neural Divergent 6

True Knowledge Graph backend (Neo4j or Memgraph)

Relationship traversal optimizations

Multi-hop deterministic reasoning

Neural Divergent 7

Context builder

Automatic prompt assembly

Token optimization & Memory compression

Neural Divergent 8

Cognitive planner

Goal management

Task decomposition

Self-updating memory and Reasoning chains

Long-Term Vision

The final architecture aims to resemble a simplified cognitive system. Rather than treating memory as raw text blobs, Neural Divergent treats memory as highly-structured, refined, and categorized knowledge.

The project ultimately aims to become a fast, deterministic cognitive layer capable of sitting in front of any modern Large Language Model, granting it long-term, explainable, and evolving memory without context-window exhaustion.