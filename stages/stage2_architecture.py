"""
Stage 2: Architecture Design
==============================
Uses the structured intent from Stage 1 to design a complete
system architecture — components, patterns, communication, deployment.

Key behaviors:
  - Selects architecture pattern based on scale + complexity
  - Defines every major component with its responsibilities
  - Considers scalability, fault tolerance, security from the start
  - Returns strict JSON matching ArchitectureDesignResult schema
"""

import json
from core.llm_client import LLMClient
from core.config import CompilerConfig
from schemas.blueprint import IntentExtractionResult, ArchitectureDesignResult


SYSTEM_PROMPT = """You are the Architecture Design Engine of a Natural Language Compiler (NLC).

You receive a structured intent object and return a complete system architecture as JSON.

ARCHITECTURE RULES:
1. Select the MOST appropriate pattern (MVC, microservices, monolith, event-driven, serverless, CQRS, hexagonal)
2. Define every component with: name, type, responsibility, technology, interfaces_with
3. Choose communication style that fits the scale (REST, GraphQL, gRPC, message_queue, websocket)
4. Specify deployment target realistically
5. Include security model appropriate to the app type
6. Add caching strategy if performance is a concern
7. Explain your architectural reasoning

Component types: service | database | frontend | worker | gateway | cache | queue | scheduler | ml_model | cdn

RULES:
- Return ONLY valid JSON. No markdown, no explanation.
- Technology choices must be specific (e.g. "FastAPI" not "Python framework")
- Every component must have at least one interface_with entry (or "standalone" if truly isolated)
- Minimum 2 components, maximum 12 for this tool

Output schema:
{
  "pattern": "string",
  "components": [
    {
      "name": "string",
      "type": "string",
      "responsibility": "string",
      "technology": "string",
      "interfaces_with": ["string"],
      "scalability_notes": "string or null"
    }
  ],
  "communication_style": "string",
  "deployment_target": "string",
  "security_model": "string",
  "caching_strategy": "string or null",
  "reasoning": "string"
}"""


USER_TEMPLATE = """Design the system architecture for this application.

EXTRACTED INTENT:
{intent_json}

Return the architecture JSON object now."""


class ArchitectureDesigner:
    def __init__(self, llm: LLMClient, config: CompilerConfig, console=None):
        self.llm = llm
        self.config = config
        self.console = console

    def run(self, intent: IntentExtractionResult) -> ArchitectureDesignResult:
        raw = self.llm.call_with_retry(
            system_prompt=SYSTEM_PROMPT,
            user_message=USER_TEMPLATE.format(
                intent_json=json.dumps(intent.model_dump(), indent=2)
            ),
            validator_fn=self._validate,
            stage_name="ArchitectureDesign",
            console=self.console,
        )
        return ArchitectureDesignResult(**raw)

    def _validate(self, data: dict):
        required = ["pattern", "components", "communication_style", "deployment_target", "security_model", "reasoning"]
        for key in required:
            if key not in data:
                raise ValueError(f"Missing required field: '{key}'")
        components = data.get("components", [])
        if not isinstance(components, list) or len(components) < 2:
            raise ValueError("Must have at least 2 components")
        for i, comp in enumerate(components):
            for field in ["name", "type", "responsibility", "technology"]:
                if field not in comp:
                    raise ValueError(f"Component {i} missing field: '{field}'")