"""
LLM Client
==========
Wraps the Google Gemini API (free tier) using the new `google-genai` SDK
with HTTP/REST transport — avoids the gRPC SSL issues of the old SDK.

Free tier: https://aistudio.google.com/apikey
Model: gemini-2.0-flash  (fast, free, 15 RPM / 1M TPD)

Features:
  - Absolute JSON enforcement via system instruction
  - Thinking-block stripping
  - Auto-retry with exponential backoff + self-healing prompts
  - Catches ALL exception types (API errors, network errors, JSON errors)
  - Graceful mock fallback when GEMINI_API_KEY is not set
"""

import json
import time
import re
import os
from typing import Any, Dict
from core.config import CompilerConfig


def _build_client(api_key: str):
    """Build a Gemini REST client (no gRPC, no SSL issues)."""
    from google import genai
    return genai.Client(api_key=api_key)


class LLMClient:
    MODEL = "gemini-2.0-flash"

    def __init__(self, config: CompilerConfig):
        self.config = config
        self.api_key = os.environ.get("GEMINI_API_KEY")

        if not self.api_key:
            self.mock_mode = True
            self.client = None
        else:
            self.mock_mode = False
            self.client = _build_client(self.api_key)

    def call(
        self,
        system_prompt: str,
        user_message: str,
        response_prefix: str = "{",
        attempt: int = 0,
    ) -> Dict[str, Any]:
        if self.mock_mode:
            raise RuntimeError("Cannot invoke LLM call in mock/offline mode.")

        full_prompt = (
            system_prompt
            + "\n\nCRITICAL OUTPUT RULES:\n"
            "- Return ONLY valid JSON. No markdown. No explanation.\n"
            "- Do NOT wrap in ```json``` fences.\n"
            "- Start your response directly with { and nothing else.\n"
            "\nUSER REQUEST:\n"
            + user_message
        )

        response = self.client.models.generate_content(
            model=self.MODEL,
            contents=full_prompt,
        )

        raw_text = response.text.strip()

        # Strip any thinking blocks the model may emit
        raw_text = re.sub(r"<think>[\s\S]*?</think>", "", raw_text, flags=re.IGNORECASE).strip()

        return self._parse_json(raw_text)

    def call_with_retry(
        self,
        system_prompt: str,
        user_message: str,
        validator_fn=None,
        response_prefix: str = "{",
        stage_name: str = "unknown",
        console=None,
    ) -> Dict[str, Any]:
        if getattr(self, "mock_mode", False):
            if console:
                console.print(
                    f"    [yellow]⚠ GEMINI_API_KEY not set. "
                    f"Falling back to Mock Engine for '{stage_name}'...[/yellow]"
                )
            result = self._generate_mock_response(stage_name, user_message)
            if validator_fn:
                validator_fn(result)
            return result

        last_error = None
        last_raw = "N/A"
        result = None

        for attempt in range(self.config.max_retries):
            try:
                healing_context = ""
                if attempt > 0 and last_error:
                    healing_context = (
                        f"\n\n[SELF-HEALING ATTEMPT {attempt}]\n"
                        f"Your previous response caused this error:\n{last_error}\n"
                        f"Previous raw output:\n{last_raw}\n"
                        f"Fix all issues and return valid JSON only."
                    )

                result = self.call(
                    system_prompt=system_prompt,
                    user_message=user_message + healing_context,
                    response_prefix=response_prefix,
                    attempt=attempt,
                )

                if validator_fn:
                    validator_fn(result)

                if console and attempt > 0:
                    console.print(f"    [green]✓ Self-healed on attempt {attempt + 1}[/green]")

                return result

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                # JSON / validation errors — retry with self-healing
                last_error = str(e)
                last_raw = str(result) if result is not None else "N/A"
                if console:
                    console.print(
                        f"    [yellow]⚠ Attempt {attempt + 1} failed (parse/validation): {e} — retrying...[/yellow]"
                    )
                time.sleep(2 ** attempt)

            except Exception as e:
                # Network errors, API errors (403, 429, 500 etc.)
                last_error = str(e)
                last_raw = "N/A"
                error_str = str(e)

                # Unrecoverable: bad API key
                if "API_KEY_INVALID" in error_str or "API key not valid" in error_str:
                    raise RuntimeError(
                        "Invalid GEMINI_API_KEY. Get a free key at https://aistudio.google.com/apikey"
                    ) from e

                # Unrecoverable: firewall/network block
                if "403" in error_str and "allowlist" in error_str.lower():
                    raise RuntimeError(
                        "Gemini API blocked by network/firewall. Check your internet connection."
                    ) from e

                # Unrecoverable: daily quota fully exhausted (limit: 0)
                if "429" in error_str and "limit: 0" in error_str:
                    raise RuntimeError(
                        "Your Gemini API free-tier daily quota is exhausted (limit: 0).\n"
                        "Fix: Get a fresh free key at https://aistudio.google.com/apikey\n"
                        "     (use a different Google account, or wait until tomorrow for reset)"
                    ) from e

                # Rate limited (429) but quota not fully gone — wait the suggested delay
                if "429" in error_str:
                    import re as _re
                    delay_match = _re.search(r"retryDelay.*?(\d+)s", error_str)
                    wait = int(delay_match.group(1)) + 2 if delay_match else 60
                    if console:
                        console.print(
                            f"    [yellow]⚠ Rate limited — waiting {wait}s before retry {attempt + 1}/{self.config.max_retries}...[/yellow]"
                        )
                    time.sleep(wait)
                    continue

                if console:
                    console.print(
                        f"    [yellow]⚠ Attempt {attempt + 1} failed (API/network): {type(e).__name__}: {e} — retrying...[/yellow]"
                    )
                time.sleep(2 ** attempt)

        raise RuntimeError(
            f"Stage '{stage_name}' failed after {self.config.max_retries} attempts. "
            f"Last error: {last_error}"
        )

    def _parse_json(self, raw: str) -> Dict[str, Any]:
        # Strategy 1: direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Strategy 2: strip markdown fences
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Strategy 3: extract first JSON object/array
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        raise json.JSONDecodeError(
            f"Could not parse JSON from response. Raw preview: {raw[:300]}",
            raw, 0,
        )

    # ── Mock Engine (no API key needed) ─────────────────────────

    def _generate_mock_response(self, stage_name: str, user_message: str) -> Dict[str, Any]:
        prompt_match = re.search(r'USER PROMPT:\s*"""(.*?)"""', user_message, re.DOTALL)
        prompt = prompt_match.group(1).strip() if prompt_match else "SaaS App"
        prompt_clean = prompt.replace('"', "").strip()

        app_category = "web_app"
        if any(w in prompt.lower() for w in ["api", "backend", "service", "rest"]):
            app_category = "api_service"
        elif any(w in prompt.lower() for w in ["cli", "tool", "script", "terminal"]):
            app_category = "cli_tool"
        elif any(w in prompt.lower() for w in ["ml", "ai", "model", "predict"]):
            app_category = "ml_system"
        elif any(w in prompt.lower() for w in ["pipeline", "etl", "data"]):
            app_category = "data_pipeline"

        if stage_name == "IntentExtraction":
            return {
                "primary_goal": f"Create {prompt_clean}",
                "app_category": app_category,
                "target_users": ["End Users", "System Administrators"],
                "core_features": [
                    "User authentication and profile management",
                    "Core database CRUD operations matching application requirements",
                    "Responsive interface / API endpoints with schema validation",
                ],
                "implicit_requirements": [
                    "Security hardening and input validation",
                    "Structured logging and comprehensive error handling",
                    "Robust database migration support",
                ],
                "anti_goals": ["Scale to millions of users on day one"],
                "ambiguities": ["Specific third-party integrations required"],
                "confidence_score": 0.95,
            }

        elif stage_name == "ArchitectureDesign":
            pattern = "MVC" if app_category in ["web_app", "api_service"] else "monolith"
            return {
                "pattern": pattern,
                "components": [
                    {"name": "API Gateway", "type": "gateway", "responsibility": "HTTP requests and JWT auth", "technology": "FastAPI", "interfaces_with": ["Application Service"]},
                    {"name": "Application Service", "type": "service", "responsibility": "Core business logic", "technology": "Python", "interfaces_with": ["Database"]},
                    {"name": "Database", "type": "database", "responsibility": "Persistent storage", "technology": "PostgreSQL", "interfaces_with": []},
                ],
                "communication_style": "REST",
                "deployment_target": "docker",
                "security_model": "JWT",
                "caching_strategy": "Redis",
                "reasoning": f"3-tier {pattern} architecture for maintainability.",
            }

        elif stage_name == "SchemaGeneration":
            return {
                "api_layer": {
                    "base_url": "/api/v1",
                    "endpoints": [
                        {"method": "POST", "path": "/api/v1/auth/register", "description": "Register new user", "request_body": {"username": "string", "email": "string", "password": "string"}, "response_schema": {"id": "integer"}, "auth_required": False, "rate_limited": True},
                        {"method": "POST", "path": "/api/v1/auth/token", "description": "Login and get JWT", "request_body": {"username": "string", "password": "string"}, "response_schema": {"access_token": "string"}, "auth_required": False, "rate_limited": True},
                        {"method": "GET", "path": "/api/v1/tasks", "description": "List user tasks", "request_body": None, "response_schema": {"tasks": "array"}, "auth_required": True, "rate_limited": False},
                        {"method": "POST", "path": "/api/v1/tasks", "description": "Create a task", "request_body": {"title": "string"}, "response_schema": {"id": "integer"}, "auth_required": True, "rate_limited": False},
                        {"method": "PUT", "path": "/api/v1/tasks/{id}", "description": "Update a task", "request_body": {"title": "string"}, "response_schema": {"id": "integer"}, "auth_required": True, "rate_limited": False},
                    ],
                    "versioning_strategy": "url_prefix",
                    "authentication": "JWT",
                },
                "data_layer": {
                    "database_type": "postgresql",
                    "orm": "SQLAlchemy",
                    "models": [
                        {"name": "User", "table_name": "users", "fields": [
                            {"name": "id", "type": "Integer", "required": True, "unique": True, "indexed": True},
                            {"name": "username", "type": "String", "required": True, "unique": True, "indexed": True},
                            {"name": "email", "type": "String", "required": True, "unique": True, "indexed": False},
                            {"name": "hashed_password", "type": "String", "required": True, "unique": False, "indexed": False},
                        ], "relationships": ["tasks"], "constraints": []},
                        {"name": "Task", "table_name": "tasks", "fields": [
                            {"name": "id", "type": "Integer", "required": True, "unique": True, "indexed": True},
                            {"name": "title", "type": "String", "required": True, "unique": False, "indexed": False},
                            {"name": "completed", "type": "Boolean", "required": True, "unique": False, "indexed": False},
                            {"name": "owner_id", "type": "Integer", "required": True, "unique": False, "indexed": True},
                        ], "relationships": ["owner"], "constraints": []},
                    ],
                    "migration_strategy": "alembic",
                },
                "dependency_manifest": {
                    "primary_language": "python",
                    "runtime_version": "3.11",
                    "packages": [
                        {"name": "fastapi", "version": "0.100.0", "purpose": "Web framework", "dev_only": False},
                        {"name": "uvicorn", "version": "0.22.0", "purpose": "ASGI server", "dev_only": False},
                        {"name": "sqlalchemy", "version": "2.0.0", "purpose": "ORM", "dev_only": False},
                        {"name": "pydantic", "version": "2.4.0", "purpose": "Data validation", "dev_only": False},
                        {"name": "alembic", "version": "1.11.0", "purpose": "Migrations", "dev_only": False},
                        {"name": "python-jose", "version": "3.3.0", "purpose": "JWT tokens", "dev_only": False},
                        {"name": "passlib", "version": "1.7.4", "purpose": "Password hashing", "dev_only": False},
                    ],
                    "environment_variables": ["DATABASE_URL", "SECRET_KEY"],
                },
                "directory_structure": {
                    "root": "app",
                    "files": [
                        {"path": "main.py", "type": "file", "description": "App entrypoint", "template": "from fastapi import FastAPI\napp = FastAPI()\n"},
                        {"path": "config.py", "type": "file", "description": "Settings", "template": "import os\nDATABASE_URL = os.getenv('DATABASE_URL')\n"},
                        {"path": "database.py", "type": "file", "description": "DB session", "template": "from sqlalchemy import create_engine\n"},
                        {"path": "models.py", "type": "file", "description": "ORM models", "template": "from sqlalchemy import Column, Integer, String\n"},
                        {"path": "schemas.py", "type": "file", "description": "Pydantic schemas", "template": "from pydantic import BaseModel\n"},
                        {"path": "auth.py", "type": "file", "description": "Auth helpers", "template": "def create_token(data): return 'token'\n"},
                        {"path": "routers/__init__.py", "type": "file", "description": "Router package", "template": ""},
                        {"path": "routers/tasks.py", "type": "file", "description": "Task routes", "template": "from fastapi import APIRouter\nrouter = APIRouter()\n"},
                    ],
                },
            }

        elif stage_name == "Refinement":
            return {
                "issues_found": [{"severity": "warning", "layer": "API Layer", "description": "Missing rate limit on list endpoint", "resolution": "Add rate limiting middleware."}],
                "optimizations_applied": ["Added indexes on foreign keys"],
                "security_hardening": ["CORS middleware required", "JWT expiry enforced"],
                "implementation_roadmap": ["Setup environment", "Initialize database", "Implement auth", "Implement task CRUD", "Write tests", "Deploy"],
                "estimated_build_time_hours": 8.0,
                "risk_assessment": "low",
            }

        return {}