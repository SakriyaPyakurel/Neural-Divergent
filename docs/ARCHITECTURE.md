# Neural Divergent
## A Deterministic Cognitive Memory Architecture for AI Systems

Version: 0.4.x (Current Development)

---

# Overview

Neural Divergent is a deterministic cognitive memory architecture designed to improve how AI assistants understand, store, organize, retrieve and reason over conversational information.

Unlike traditional LLM memory systems that rely heavily on embeddings or repeated prompt injection, Neural Divergent attempts to perform as much reasoning as possible locally before an LLM is ever involved.

The philosophy is simple:

> Convert natural language into structured semantic knowledge first.
> Think before retrieving.
> Retrieve before generating.

The project is not intended to replace Large Language Models.

Instead, it functions as a cognitive layer sitting between human conversation and the LLM.

This architecture allows:

- significantly lower token consumption
- deterministic memory formation
- explainable reasoning
- contradiction management
- semantic graph growth
- future knowledge graph migration

---

# Project Vision

Current AI assistants largely depend on context windows.

Once the conversation becomes large, they begin forgetting previous information, hallucinating relationships, or repeatedly consuming tokens to rediscover already known facts.

Neural Divergent aims to solve this by introducing an explicit cognitive memory architecture.

Instead of repeatedly asking an LLM to understand everything again, the system builds a structured memory graph that continuously evolves.

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

Instead of

Conversation

↓

Entire Prompt

↓

LLM

↓

Repeat Forever

---

# Design Philosophy

The architecture follows several principles.

## Deterministic First

Whenever deterministic algorithms can solve a problem,
they should always execute before expensive probabilistic AI.

Examples:

- dependency parsing
- relationship extraction
- contradiction detection
- duplicate detection
- semantic normalization

These operations should never require an LLM.

---

## Minimize Token Consumption

Every unnecessary token sent to an LLM costs money.

Neural Divergent attempts to reduce conversational redundancy before retrieval.

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

---

## Explainability

Every stored memory should answer:

Why was it stored?

Where did it come from?

How important is it?

Why does it still exist?

Why did it replace another memory?

---

## Modular Architecture

Each component performs exactly one responsibility.

No module performs another module's job.

This keeps the pipeline maintainable and independently testable.

---

# Current Cognitive Pipeline

User Message

↓

Local Extraction Engine

↓

Semantic Normalization

↓

Importance Estimator

↓

Memory Decision Engine

↓

Proto-Graph Memory Database

↓

Retrieval APIs

↓

(Future)

Embedding Retrieval

↓

LLM

---

# Component Overview

## 1. Local Extraction Engine

Purpose

Transform raw natural language into deterministic semantic representations.

Responsibilities

- dependency parsing
- linguistic normalization
- SIR construction
- reason extraction
- negation detection
- relationship normalization
- metadata generation

Output

SemanticRepresentation

containing

- subject
- relationship
- object
- confidence
- metadata
- reason
- source text

---

## 2. Importance Estimator

Purpose

Estimate whether information deserves memory.

This stage performs cognitive valuation.

Inputs

SemanticRepresentation

Outputs

- importance prior
- retention policy

Current capabilities

- ontology-driven predicate evaluation
- configurable ontology JSON
- confidence weighting
- contextual boosting
- reasoning bonus
- negation penalty
- noise filtering

Retention Policies

EPHEMERAL

SHORT_TERM

LONG_TERM

Importance Prior

0.0 → 1.0

---

## Predicate Ontology

The system now uses a declarative ontology rather than hardcoded logic.

Example

```
name

importance: CRITICAL

retention: LONG_TERM

category: IDENTITY
```

Benefits

- zero-code ontology updates
- scalable
- easily extendable
- future knowledge graph compatible

---

## 3. Memory Decision Engine

Purpose

Maintain consistency inside memory.

Responsibilities

Duplicate Detection

Existing fact?

↓

REINFORCED

Contradiction Detection

Existing truth?

↓

SUPERSEDED

Novel Information

↓

NEW

Current actions

NEW

REINFORCED

SUPERSEDED

IGNORED

---

## 4. Proto-Graph Memory Database

Current implementation

SQLite

Schema

semantic_memories

Stores

subject

predicate

object

importance

retention

confidence

metadata

reason

event type

memory category

reinforcement count

timestamps

active state

superseded links

The database behaves like a lightweight semantic graph.

---

## Graph Principles

Each row represents

Subject

↓

Relationship

↓

Object

instead of traditional relational rows.

Example

User

↓

favorite_language

↓

Python

Future migration

SQLite

↓

Neo4j

or

↓

Memgraph

without changing higher-level logic.

---

## 5. Orchestrator

The orchestrator coordinates the entire pipeline.

Responsibilities

Receive user input

↓

Extraction

↓

Importance Estimation

↓

Decision Engine

↓

Persistence

↓

Return processing ledger

The orchestrator contains no business logic.

It delegates work.

---

# Current API

Base Route

/api/v1/memory

Implemented endpoints

POST

/ingest

Processes natural language into cognitive memory.

Pipeline

Text

↓

Extraction

↓

Importance

↓

Decision

↓

Storage

↓

Response

Returns

- processed memories
- ignored memories
- importance
- retention
- action
- confidence

---

GET

/active

Returns active truth for

Subject

+

Predicate

Example

User

favorite_language

↓

Python

---

GET

/related/{subject}

Returns connected active memories.

Example

User

↓

works_on

↓

Neural Divergent

↓

uses

↓

FastAPI

---

GET

/search

Ranked semantic memory retrieval.

Ranking considers

- importance
- confidence
- reinforcement
- recency

---

GET

/traverse

Associative graph traversal.

Returns

Depth 0

↓

Direct matches

↓

Depth 1

↓

Connected memories

Foundation for future reasoning.

---

# Features Implemented

✓ Local deterministic NLP extraction

✓ Semantic normalization

✓ Subject–Predicate–Object representation

✓ Confidence estimation

✓ Negation handling

✓ Reason extraction

✓ Ontology-driven importance estimation

✓ Configurable predicate ontology

✓ Retention policies

✓ Duplicate detection

✓ Contradiction handling

✓ Reinforcement learning of existing memories

✓ Soft memory supersession

✓ Proto-graph database

✓ Active truth queries

✓ Related memory retrieval

✓ Ranked memory search

✓ Graph traversal

✓ FastAPI cognitive API

✓ Modular architecture

---

# What Makes Neural Divergent Different

Most memory systems

Conversation

↓

Embedding

↓

Vector Search

↓

LLM

Neural Divergent

Conversation

↓

Grammar

↓

Semantics

↓

Importance

↓

Memory Decisions

↓

Graph

↓

Retrieval

↓

LLM

The architecture attempts to reason before embedding.

---

# Next up Roadmap

## Neural Divergent 5

Embedding retrieval layer

Hybrid graph + vector search

Semantic ranking

Memory activation

---

## Neural Divergent 6

Knowledge graph backend

Neo4j

or

Memgraph

Relationship traversal

Multi-hop reasoning

---

## Neural Divergent 7

Context builder

Automatic prompt assembly

Token optimization

Memory compression

---

## Neural Divergent 8

Cognitive planner

Goal management

Task decomposition

Self-updating memory

Reasoning chains

---

# Long-Term Vision

The final architecture aims to resemble a simplified cognitive system.

Conversation

↓

Understanding

↓

Semantic Memory

↓

Importance

↓

Memory Formation

↓

Knowledge Graph

↓

Retrieval

↓

Reasoning

↓

Response Generation

Rather than treating memory as text, Neural Divergent treats memory as structured knowledge.

The project ultimately aims to become a deterministic cognitive layer capable of sitting in front of any modern Large Language Model.
