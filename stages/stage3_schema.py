"""
Stage 3: Schema Block Generation
==================================
Generates three concrete blueprint layers simultaneously:
  1. API Layer  — all endpoints with request/response schemas
  2. Data Layer — database models with fields and relationships
  3. Dependency Manifest — packages, versions, env vars
  4. Directory Structure — full file tree with descriptions

Key behaviors:
  - All schemas are specific, not generic placeholders
  - API endpoints include HTTP method, path, auth, rate limits
  - Data models include field types, constraints, indexes
  - Dependencies include exact purpose (no mystery packages)
  - Directory structure includes starter code templates for key files
"""

import json
from core.llm_client import LLMClient
from core.config import CompilerConfig
from schemas.blueprint import (
    IntentExtractionResult,
    ArchitectureDesignResult,
    SchemaGenerationResult,
    APILayer,
    DataLayer,
    DependencyManifest,
    DirectoryStructure,
)


SYSTEM_PROMPT = """You are the Schema Block Generator of a Natural Language Compiler (NLC).

You receive intent + architecture and produce concrete implementation schemas as JSON.

You must generate ALL FOUR sections in one JSON response:

1. API LAYER — every endpoint the app needs:
   - method: GET | POST | PUT | PATCH | DELETE | WS
   - path: e.g. /api/v1/users/{id}
   - description, request_body, response_schema, auth_required, rate_limited

2. DATA LAYER — all database models:
   - Each model has: name, table_name, fields[], relationships[], constraints[]
   - Each field: name, type, required, unique, indexed, description, default

3. DEPENDENCY MANIFEST — all packages needed:
   - primary_language, runtime_version
   - packages: [{name, version, purpose, dev_only}]
   - environment_variables: list of env var names (no values)

4. DIRECTORY STRUCTURE — the full file/folder tree:
   - Each node: path, type (file|directory), description
   - Include a template (starter code) for key files like main.py, models.py, etc.

STRICT RULES:
- Return ONLY valid JSON. No markdown, no explanation.
- Use specific versions (e.g. "2.0.3", not "latest")
- Every API endpoint must have a clear request and response schema
- Template code must be syntactically valid Python/JS/etc.
- At minimum: 3 endpoints, 2 models, 5 packages, 8 file nodes

Output schema:
{
  "api_layer": {
    "base_url": "/api/v1",
    "endpoints": [...],
    "versioning_strategy": "url_prefix",
    "authentication": "string"
  },
  "data_layer": {
    "database_type": "string",
    "orm": "string",
    "models": [...],
    "migration_strategy": "string"
  },
  "dependency_manifest": {
    "primary_language": "string",
    "runtime_version": "string",
    "packages": [...],
    "environment_variables": [...]
  },
  "directory_structure": {
    "root": "string",
    "files": [...]
  }
}"""


USER_TEMPLATE = """Generate all schema blocks for this application.

EXTRACTED INTENT:
{intent_json}

ARCHITECTURE DESIGN:
{architecture_json}

Return the complete schema JSON object now."""


class SchemaGenerator:
    def __init__(self, llm: LLMClient, config: CompilerConfig, console=None):
        self.llm = llm
        self.config = config
        self.console = console

    def run(
        self,
        intent: IntentExtractionResult,
        architecture: ArchitectureDesignResult,
    ) -> SchemaGenerationResult:
        raw = self.llm.call_with_retry(
            system_prompt=SYSTEM_PROMPT,
            user_message=USER_TEMPLATE.format(
                intent_json=json.dumps(intent.model_dump(), indent=2),
                architecture_json=json.dumps(architecture.model_dump(), indent=2),
            ),
            validator_fn=self._validate,
            stage_name="SchemaGeneration",
            console=self.console,
        )
        return SchemaGenerationResult(
            api_layer=APILayer(**raw["api_layer"]),
            data_layer=DataLayer(**raw["data_layer"]),
            dependency_manifest=DependencyManifest(**raw["dependency_manifest"]),
            directory_structure=DirectoryStructure(**raw["directory_structure"]),
        )

    def _validate(self, data: dict):
        required = ["api_layer", "data_layer", "dependency_manifest", "directory_structure"]
        for key in required:
            if key not in data:
                raise ValueError(f"Missing top-level section: '{key}'")

        endpoints = data.get("api_layer", {}).get("endpoints", [])
        if len(endpoints) < 3:
            raise ValueError(f"Need at least 3 API endpoints, got {len(endpoints)}")

        models = data.get("data_layer", {}).get("models", [])
        if len(models) < 2:
            raise ValueError(f"Need at least 2 data models, got {len(models)}")

        packages = data.get("dependency_manifest", {}).get("packages", [])
        if len(packages) < 5:
            raise ValueError(f"Need at least 5 packages, got {len(packages)}")

        files = data.get("directory_structure", {}).get("files", [])
        if len(files) < 8:
            raise ValueError(f"Need at least 8 file nodes, got {len(files)}")