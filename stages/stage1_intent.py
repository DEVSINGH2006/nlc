"""
Stage 1: Intent Extraction
===========================
Transforms messy, human-written natural language into a clean,
structured understanding of what the user actually wants to build.

Key behaviors:
  - Handles vague, incomplete, or contradictory prompts
  - Infers implicit requirements from domain knowledge
  - Surfaces ambiguities rather than guessing
  - Returns strict JSON matching IntentExtractionResult schema
"""

from core.llm_client import LLMClient
from core.config import CompilerConfig
from schemas.blueprint import IntentExtractionResult


SYSTEM_PROMPT = """You are the Intent Extraction Engine of a Natural Language Compiler (NLC).

Your ONLY job is to analyze a user's application description and return a SINGLE valid JSON object.

You must extract:
1. The primary goal (one clear sentence)
2. App category (web_app | cli_tool | api_service | data_pipeline | ml_system | mobile_app | desktop_app | other)
3. Target users (list of user personas)
4. Core features (concrete, actionable feature list — minimum 3)
5. Implicit requirements (things they DIDN'T say but obviously need — auth, error handling, logging, etc.)
6. Anti-goals (what this app should NOT do based on context)
7. Ambiguities (genuinely unclear parts — list them, don't guess)
8. Confidence score (0.0 to 1.0 — how well you understood the prompt)

RULES:
- Return ONLY valid JSON. No markdown, no explanation, no preamble.
- Never hallucinate features that weren't implied.
- Be ruthlessly specific. Vague features like "good UX" are not acceptable.
- If the prompt is very short, infer intelligently from the domain.

Output schema:
{
  "primary_goal": "string",
  "app_category": "string",
  "target_users": ["string"],
  "core_features": ["string"],
  "implicit_requirements": ["string"],
  "anti_goals": ["string"],
  "ambiguities": ["string"],
  "confidence_score": 0.0
}"""


USER_TEMPLATE = """Analyze this application description and extract structured intent:

USER PROMPT:
\"\"\"{prompt}\"\"\"

Return the JSON object now."""


class IntentExtractor:
    def __init__(self, llm: LLMClient, config: CompilerConfig, console=None):
        self.llm = llm
        self.config = config
        self.console = console

    def run(self, prompt: str) -> IntentExtractionResult:
        raw = self.llm.call_with_retry(
            system_prompt=SYSTEM_PROMPT,
            user_message=USER_TEMPLATE.format(prompt=prompt),
            validator_fn=self._validate,
            stage_name="IntentExtraction",
            console=self.console,
        )
        return IntentExtractionResult(**raw)

    def _validate(self, data: dict):
        required = ["primary_goal", "app_category", "core_features", "confidence_score"]
        for key in required:
            if key not in data:
                raise ValueError(f"Missing required field: '{key}'")
        if not isinstance(data["core_features"], list) or len(data["core_features"]) == 0:
            raise ValueError("core_features must be a non-empty list")
        score = data.get("confidence_score", -1)
        if not (0.0 <= float(score) <= 1.0):
            raise ValueError("confidence_score must be between 0.0 and 1.0")