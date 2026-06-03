# NLC — Natural Language Compiler


> *"Takes messy human language as input. Produces a working application blueprint as output. Like a compiler — but for intent."*

---

## Overview

NLC is a **multi-stage LLM compilation pipeline** that transforms natural language application descriptions into structured, validated, production-ready JSON blueprints. It enforces absolute control over the LLM at every stage through prompt engineering, strict JSON instruction, self-healing retry loops, and a Local Virtual Execution Sandbox.

---

## Pipeline Architecture

```
User Prompt (natural language)
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│  Stage 1 — Intent Extraction                              │
│  Transforms messy input → structured IntentExtractionResult│
│  • Identifies features, anti-goals, ambiguities           │
│  • Infers implicit requirements from domain knowledge     │
│  • Assigns confidence score                               │
└──────────────────────┬────────────────────────────────────┘
                       │ IntentExtractionResult
                       ▼
┌───────────────────────────────────────────────────────────┐
│  Stage 2 — Architecture Design                            │
│  Intent → ArchitectureDesignResult                        │
│  • Selects architecture pattern (MVC, microservices, etc) │
│  • Defines all system components with responsibilities    │
│  • Specifies comms, deployment, security model            │
└──────────────────────┬────────────────────────────────────┘
                       │ ArchitectureDesignResult
                       ▼
┌───────────────────────────────────────────────────────────┐
│  Stage 3 — Schema Block Generation                        │
│  Intent + Architecture → SchemaGenerationResult           │
│  • API Layer: all endpoints with request/response schemas │
│  • Data Layer: database models, fields, relationships     │
│  • Dependency Manifest: packages with pinned versions     │
│  • Directory Structure: full file tree + starter code     │
└──────────────────────┬────────────────────────────────────┘
                       │ SchemaGenerationResult
                       ▼
┌───────────────────────────────────────────────────────────┐
│  Stage 4 — Refinement & Cross-Layer Synthesis             │
│  All previous outputs → RefinementResult                  │
│  • Cross-layer consistency checks                         │
│  • Security hardening pass                                │
│  • Performance optimizations                              │
│  • Ordered implementation roadmap                         │
└──────────────────────┬────────────────────────────────────┘
                       │ Full Blueprint
                       ▼
┌───────────────────────────────────────────────────────────┐
│  Stage 5 — Local Virtual Execution Sandbox (Bonus)        │
│  Blueprint → ExecutionProof                               │
│  • Python syntax validation (AST-based)                   │
│  • Pydantic schema round-trip integrity check             │
│  • API contract validation (paths, methods, duplicates)   │
│  • Dependency name/version validation                     │
│  • Cross-reference audit (endpoints ↔ models)             │
│  • Security policy enforcement check                      │
│  • Blueprint completeness verification                    │
└──────────────────────┬────────────────────────────────────┘
                       │
                       ▼
           ApplicationBlueprint (JSON)
```

---


## Key Design Decisions

### 1. LLM Hallucination Control
Three-layer enforcement:
- **Zero temperature** (`temperature=0.0`) — deterministic, reproducible output
- **JSON instruction** — every prompt explicitly instructs the model to return JSON only, with no markdown or preamble
- **Stage-specific system prompts** — each prompt explicitly names forbidden behaviors and required schema

### 2. Self-Healing Retry Loop
Every stage wraps its LLM call in `call_with_retry()`:
```
Attempt N fails → error fed back as context →
Model sees its own mistake → corrects on next attempt →
Exponential backoff between retries
```

### 3. Multi-Strategy JSON Parser
Three fallback strategies before raising:
1. Direct `json.loads()`
2. Strip markdown fences, try again
3. Regex-extract first `{...}` or `[...]` block

### 4. Pydantic V2 Type Safety
Every stage output is a typed Pydantic model. The final `ApplicationBlueprint` does a full round-trip validation in the sandbox — if it re-serializes successfully, the schema is provably consistent.

### 5. Local Virtual Execution Sandbox
7 automated tests run against the compiled blueprint:

| Test | Method |
|------|--------|
| Python Syntax Validation | `ast.parse()` on all `.py` templates |
| Schema Integrity | Pydantic round-trip dump + reload |
| API Contract Validation | Path regex, method enum, duplicate check |
| Dependency Resolvability | Package name format + version pinning |
| Cross-Reference Audit | Endpoint paths ↔ data model names |
| Security Policy Check | Auth enforcement on sensitive endpoints |
| Blueprint Completeness | All required sections present |

---

## Project Structure

```
nlc/
├── main.py                    # CLI entry point
├── requirements.txt
│
├── core/
│   ├── config.py              # CompilerConfig dataclass
│   ├── llm_client.py          # LLM wrapper: JSON enforcement, retry, healing
│   └── pipeline.py            # Orchestrates all 5 stages
│
├── stages/
│   ├── stage1_intent.py       # Intent Extraction
│   ├── stage2_architecture.py # Architecture Design
│   ├── stage3_schema.py       # Schema Block Generation
│   └── stage4_refinement.py   # Refinement & Cross-Layer Synthesis
│
├── sandbox/
│   └── executor.py            # Local Virtual Execution Sandbox (Stage 5)
│
├── schemas/
│   └── blueprint.py           # All Pydantic V2 schemas
│
└── output/
    └── blueprint.json         # Generated output (git-ignored)
```

---

## Usage

### Install
```bash
pip install -r requirements.txt
```

### Run (interactive)
```bash
python main.py
```

### Run (inline prompt)
```bash
python main.py "Build a SaaS task management tool with teams, projects, and Slack notifications"
```

### Run with sandbox + verbose output
```bash
python main.py "Build a real-time stock price tracker with alerts" --sandbox --verbose
```

### Custom output path
```bash
python main.py "Build a recipe recommendation API" --output ./results/recipe_app.json
```

---

## Output Format

The compiler produces a single `blueprint.json` with this top-level structure:

```json
{
  "metadata": { "app_name": "...", "app_type": "...", "complexity_score": "..." },
  "intent": { "primary_goal": "...", "core_features": [...], "confidence_score": 0.95 },
  "architecture": { "pattern": "...", "components": [...], "security_model": "..." },
  "api_layer": { "endpoints": [...] },
  "data_layer": { "models": [...] },
  "dependency_manifest": { "packages": [...] },
  "directory_structure": { "files": [...] },
  "refinement": { "issues_found": [...], "implementation_roadmap": [...] },
  "execution_proof": { "sandbox_passed": true, "test_results": [...] }
}
```

---

## What Makes This Stand Out

| Requirement | Implementation |
|-------------|----------------|
| Handles messy human input | Stage 1 extracts intent even from vague/contradictory prompts |
| Perfect JSON output | Strict JSON instruction + zero temp + multi-strategy parser |
| No hallucinations | Stage-scoped prompts + validator hooks per stage |
| Self-healing | Error-feedback retry loop with exponential backoff |
| Execution proof | 7-test sandbox with AST parsing, Pydantic round-trip, contract checks |
| Type safety | Full Pydantic V2 schema hierarchy, field validators |
| Modularity | Each stage is independently testable, replaceable |

---

*Built for The AI Signal AI Engineer Internship Demo Task.*