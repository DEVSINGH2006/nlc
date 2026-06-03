"""
Stage 4: Refinement & Cross-Layer Synthesis
============================================
The final intelligent pass over the entire blueprint.
Detects inconsistencies, missing links, and security gaps
across all layers and synthesizes a hardened, production-ready result.

Cross-layer checks performed:
  - API endpoints reference valid data models
  - Auth strategy is consistent across API + architecture
  - Dependencies cover all technologies mentioned in architecture
  - File structure contains all necessary files for the tech stack
  - No orphaned components (every component is used)
  - Security gaps (missing rate limits, unprotected endpoints, etc.)
  - Performance anti-patterns (N+1 queries, missing indexes)
"""

import json
from core.llm_client import LLMClient
from core.config import CompilerConfig
from schemas.blueprint import (
    IntentExtractionResult,
    ArchitectureDesignResult,
    SchemaGenerationResult,
    RefinementResult,
)


SYSTEM_PROMPT = """You are the Cross-Layer Synthesis Engine of a Natural Language Compiler (NLC).

You receive the COMPLETE blueprint (intent + architecture + all schemas) and perform a final
intelligent pass to detect issues, apply optimizations, and harden the output.

Your job:
1. CROSS-LAYER VALIDATION — find inconsistencies between layers:
   - API endpoints that reference models which don't exist in data_layer
   - Auth method in api_layer that doesn't match security_model in architecture
   - Technologies in architecture not covered by dependencies
   - Missing files in directory_structure for the chosen tech stack

2. SECURITY HARDENING — identify and list security improvements:
   - Unprotected endpoints that should require auth
   - Missing input validation notes
   - Missing rate limiting on sensitive endpoints
   - Secrets management gaps

3. OPTIMIZATIONS — practical improvements:
   - Missing database indexes for commonly queried fields
   - Caching opportunities
   - Missing error handling patterns

4. IMPLEMENTATION ROADMAP — ordered list of build steps (most critical first)

5. RISK ASSESSMENT — overall complexity: "low" | "medium" | "high" | "enterprise"

6. ESTIMATED BUILD TIME — in hours (float)

STRICT RULES:
- Return ONLY valid JSON.
- issues_found must list REAL issues, not invented ones
- If no issues found in a category, return empty array
- Be precise and actionable in all resolutions

Output schema:
{
  "issues_found": [
    {
      "severity": "critical|warning|info",
      "layer": "string",
      "description": "string",
      "resolution": "string"
    }
  ],
  "optimizations_applied": ["string"],
  "security_hardening": ["string"],
  "implementation_roadmap": ["string"],
  "estimated_build_time_hours": 0.0,
  "risk_assessment": "low|medium|high|enterprise"
}"""


USER_TEMPLATE = """Perform cross-layer synthesis and refinement on this complete blueprint.

INTENT:
{intent_json}

ARCHITECTURE:
{architecture_json}

SCHEMAS:
{schema_json}

Return the refinement JSON object now."""


class RefinementEngine:
    def __init__(self, llm: LLMClient, config: CompilerConfig, console=None):
        self.llm = llm
        self.config = config
        self.console = console

    def run(
        self,
        intent: IntentExtractionResult,
        architecture: ArchitectureDesignResult,
        schemas: SchemaGenerationResult,
    ) -> RefinementResult:
        raw = self.llm.call_with_retry(
            system_prompt=SYSTEM_PROMPT,
            user_message=USER_TEMPLATE.format(
                intent_json=json.dumps(intent.model_dump(), indent=2),
                architecture_json=json.dumps(architecture.model_dump(), indent=2),
                schema_json=json.dumps(schemas.model_dump(), indent=2),
            ),
            validator_fn=self._validate,
            stage_name="Refinement",
            console=self.console,
        )
        return RefinementResult(**raw)

    def _validate(self, data: dict):
        required = ["issues_found", "optimizations_applied", "security_hardening", "implementation_roadmap", "risk_assessment"]
        for key in required:
            if key not in data:
                raise ValueError(f"Missing required field: '{key}'")
        valid_risks = ["low", "medium", "high", "enterprise"]
        if data.get("risk_assessment") not in valid_risks:
            raise ValueError(f"risk_assessment must be one of: {valid_risks}")
        for issue in data.get("issues_found", []):
            for field in ["severity", "layer", "description", "resolution"]:
                if field not in issue:
                    raise ValueError(f"Issue missing field: '{field}'")