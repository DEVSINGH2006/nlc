"""
LLM Client
==========
Wraps the Gemini API with:
  - Absolute JSON enforcement (system-level instruction)
  - Auto-retry with exponential backoff
  - Token-aware truncation
  - Response validation hooks
"""

import json
import time
import re
from typing import Any, Optional, Dict, List
import google.generativeai as genai
from core.config import CompilerConfig
import os


class LLMClient:
    def __init__(self, config: CompilerConfig):
        self.config = config
        self.api_key = os.environ.get("GEMINI_API_KEY")

        if not self.api_key:
            self.mock_mode = True
            self.client = None
        else:
            self.mock_mode = False
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(
                model_name="gemini-2.5-flash"
            )

    def call(
        self,
        system_prompt: str,
        user_message: str,
        response_prefix: str = "{",   # kept for API compatibility, not prepended
        attempt: int = 0,
    ) -> Dict[str, Any]:
        """
        Single LLM call with JSON enforcement via prompt instruction.
        response_prefix parameter is accepted for compatibility but NOT
        prepended to the response (Gemini doesn't support assistant turn injection,
        and prepending caused double-brace JSON parse errors).
        """
        if self.mock_mode:
            raise RuntimeError("Cannot invoke LLM call in mock/offline mode.")

        response = self.client.generate_content(
            f"""{system_prompt}

IMPORTANT:
Return ONLY valid JSON.
Do not use markdown.
Do not explain anything.
Do not wrap in ```json``` fences.

USER REQUEST:
{user_message}
"""
        )

        raw_text = response.text.strip()
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
        """
        Retry loop with self-healing: on parse/validation failure,
        the error is fed back to the model as context for correction.
        """
        if getattr(self, "mock_mode", False):
            if console:
                console.print(f"    [yellow]⚠ GEMINI_API_KEY not set. Falling back to Mock Engine for '{stage_name}'...[/yellow]")
            result = self._generate_mock_response(stage_name, user_message)
            if validator_fn:
                validator_fn(result)
            return result

        last_error = None
        last_raw = None

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
                last_error = str(e)
                last_raw = str(result) if "result" in dir() else "N/A"
                if console:
                    console.print(f"    [yellow]⚠ Attempt {attempt + 1} failed: {e} — retrying...[/yellow]")
                time.sleep(2 ** attempt)

        raise RuntimeError(
            f"Stage '{stage_name}' failed after {self.config.max_retries} attempts. "
            f"Last error: {last_error}"
        )

    def _parse_json(self, raw: str) -> Dict[str, Any]:
        """
        Multi-strategy JSON parser:
        1. Direct parse
        2. Strip markdown fences
        3. Extract first {...} or [...] block
        4. Raise informative error
        """
        # Strategy 1: direct
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

        # Strategy 3: extract first JSON object
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        raise json.JSONDecodeError(
            f"Could not parse JSON from response. Raw preview: {raw[:300]}",
            raw, 0
        )

    def _generate_mock_response(self, stage_name: str, user_message: str) -> Dict[str, Any]:
        # Extract prompt
        prompt_match = re.search(r'USER PROMPT:\s*"""(.*?)"""', user_message, re.DOTALL)
        prompt = prompt_match.group(1).strip() if prompt_match else "SaaS App"
        prompt_clean = prompt.replace('"', '').strip()

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
                    "Responsive interface / API endpoints with schema validation"
                ],
                "implicit_requirements": [
                    "Security hardening and input validation",
                    "Structured logging and comprehensive error handling",
                    "Robust database migration support"
                ],
                "anti_goals": [
                    "Scale to millions of users on day one",
                    "Support offline-first storage"
                ],
                "ambiguities": [
                    "Specific third-party integrations required",
                    "Production cloud environment deployment details"
                ],
                "confidence_score": 0.95
            }

        elif stage_name == "ArchitectureDesign":
            pattern = "MVC" if app_category in ["web_app", "api_service"] else "monolith"
            return {
                "pattern": pattern,
                "components": [
                    {
                        "name": "Gateway / Presentation Layer",
                        "type": "gateway",
                        "responsibility": "Handles incoming HTTP requests, CORS, and JWT authentication validation",
                        "technology": "FastAPI" if app_category == "api_service" else "Express / Node.js",
                        "interfaces_with": ["Application Service Layer"]
                    },
                    {
                        "name": "Application Service Layer",
                        "type": "service",
                        "responsibility": "Executes core business logic rules and orchestrates data access",
                        "technology": "Python" if app_category == "api_service" else "JavaScript",
                        "interfaces_with": ["Database Persistence Layer"]
                    },
                    {
                        "name": "Database Persistence Layer",
                        "type": "database",
                        "responsibility": "Stores persistent data entities securely",
                        "technology": "PostgreSQL",
                        "interfaces_with": []
                    }
                ],
                "communication_style": "REST",
                "deployment_target": "docker",
                "security_model": "JWT",
                "caching_strategy": "Redis",
                "reasoning": f"A modular 3-tier {pattern} architecture isolates interface details, business logic, and storage for sustainable maintenance."
            }

        elif stage_name == "SchemaGeneration":
            lang = "python"
            version = "3.11"
            packages = [
                {"name": "fastapi", "version": "0.100.0", "purpose": "Asynchronous Web framework for API endpoints"},
                {"name": "uvicorn", "version": "0.22.0", "purpose": "High-performance ASGI server for Python production"},
                {"name": "sqlalchemy", "version": "2.0.0", "purpose": "Object-Relational Mapping (ORM) library for SQL operations"},
                {"name": "pydantic", "version": "2.4.0", "purpose": "Data validation and settings management using Python type hints"},
                {"name": "alembic", "version": "1.11.0", "purpose": "Lightweight database migration tool for SQLAlchemy"}
            ]
            env_vars = ["DATABASE_URL", "SECRET_KEY", "ENVIRONMENT"]

            return {
                "api_layer": {
                    "base_url": "/api/v1",
                    "endpoints": [
                        {
                            "method": "POST",
                            "path": "/auth/register",
                            "description": "Register a new user account with credentials",
                            "request_body": {"username": "string", "email": "string", "password": "string"},
                            "response_schema": {"id": "integer", "username": "string", "email": "string"},
                            "auth_required": False,
                            "rate_limited": True
                        },
                        {
                            "method": "POST",
                            "path": "/auth/token",
                            "description": "Authenticate user credentials and retrieve a JWT bearer token",
                            "request_body": {"username": "string", "password": "string"},
                            "response_schema": {"access_token": "string", "token_type": "string"},
                            "auth_required": False,
                            "rate_limited": True
                        },
                        {
                            "method": "GET",
                            "path": "/items",
                            "description": "Retrieve list of domain resources for the authenticated user",
                            "request_body": None,
                            "response_schema": {"items": "array"},
                            "auth_required": True,
                            "rate_limited": False
                        }
                    ],
                    "versioning_strategy": "url_prefix",
                    "authentication": "JWT"
                },
                "data_layer": {
                    "database_type": "postgresql",
                    "orm": "SQLAlchemy",
                    "models": [
                        {
                            "name": "User",
                            "table_name": "users",
                            "fields": [
                                {"name": "id", "type": "Integer", "required": True, "unique": True, "indexed": True},
                                {"name": "username", "type": "String", "required": True, "unique": True, "indexed": True},
                                {"name": "email", "type": "String", "required": True, "unique": True},
                                {"name": "hashed_password", "type": "String", "required": True}
                            ],
                            "relationships": ["items"],
                            "constraints": []
                        },
                        {
                            "name": "Item",
                            "table_name": "items",
                            "fields": [
                                {"name": "id", "type": "Integer", "required": True, "unique": True, "indexed": True},
                                {"name": "title", "type": "String", "required": True},
                                {"name": "description", "type": "String", "required": False},
                                {"name": "owner_id", "type": "Integer", "required": True}
                            ],
                            "relationships": ["owner"],
                            "constraints": []
                        }
                    ],
                    "migration_strategy": "alembic"
                },
                "dependency_manifest": {
                    "primary_language": lang,
                    "runtime_version": version,
                    "packages": packages,
                    "environment_variables": env_vars
                },
                "directory_structure": {
                    "root": "app",
                    "files": [
                        {
                            "path": "main.py",
                            "type": "file",
                            "description": "Application entrypoint initiating the ASGI server and API routing",
                            "template": "import uvicorn\nfrom fastapi import FastAPI\n\napp = FastAPI(title='Mock App')\n\n@app.get('/')\ndef read_root():\n    return {'status': 'healthy'}\n"
                        },
                        {
                            "path": "config.py",
                            "type": "file",
                            "description": "Application settings and environment configuration loader",
                            "template": "from pydantic_settings import BaseSettings\n\nclass Settings(BaseSettings):\n    DATABASE_URL: str = 'sqlite:///./test.db'\n    SECRET_KEY: str = 'supersecret'\n\nsettings = Settings()\n"
                        }
                    ]
                }
            }

        elif stage_name == "Refinement":
            return {
                "issues_found": [
                    {
                        "severity": "warning",
                        "layer": "API Layer",
                        "description": "Missing rate limit on the /items list endpoint",
                        "resolution": "Apply standard rate limiting wrapper middleware on the list route to prevent denial of service queries."
                    }
                ],
                "optimizations_applied": [
                    "Configured explicit indexes on indexable search query keys in SQLAlchemy models",
                    "Added connection pooling configuration to database loader block"
                ],
                "security_hardening": [
                    "Required CORS middleware initialization within the main.py router file",
                    "Enforced JWT signature hashing algorithm validation parameters"
                ],
                "implementation_roadmap": [
                    "Initialize Python environment requirements",
                    "Setup SQLAlchemy schema entities and initialize Alembic database migration scripts",
                    "Implement secure credential hashing, login, token retrieval endpoints",
                    "Implement the basic resource items CRUD views and middleware validation constraints"
                ],
                "estimated_build_time_hours": 8.0,
                "risk_assessment": "low"
            }

        return {}
