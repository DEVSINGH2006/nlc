"""
Blueprint Schemas — Pydantic V2
================================
Type-safe, validated output schemas for every layer of the
compiled application blueprint.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


# ─────────────────────────────────────────
# Stage 1: Intent Extraction
# ─────────────────────────────────────────

class IntentExtractionResult(BaseModel):
    """Structured output from Stage 1."""
    primary_goal: str = Field(..., description="Core purpose of the application in one sentence")
    app_category: str = Field(..., description="e.g. web_app, cli_tool, api_service, data_pipeline, ml_system")
    target_users: List[str] = Field(..., description="Who will use this application")
    core_features: List[str] = Field(..., min_length=1, description="Top-level features required")
    implicit_requirements: List[str] = Field(default_factory=list, description="Inferred but unstated requirements")
    anti_goals: List[str] = Field(default_factory=list, description="What this app should NOT do")
    ambiguities: List[str] = Field(default_factory=list, description="Unclear parts of the prompt")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in intent extraction")


# ─────────────────────────────────────────
# Stage 2: Architecture Design
# ─────────────────────────────────────────

class ComponentSpec(BaseModel):
    name: str
    type: str = Field(..., description="e.g. service, database, frontend, worker, gateway")
    responsibility: str
    technology: str
    interfaces_with: List[str] = Field(default_factory=list)
    scalability_notes: Optional[str] = None


class ArchitectureDesignResult(BaseModel):
    """Structured output from Stage 2."""
    pattern: str = Field(..., description="e.g. MVC, microservices, monolith, event-driven, serverless")
    components: List[ComponentSpec]
    communication_style: str = Field(..., description="e.g. REST, GraphQL, gRPC, message_queue, websocket")
    deployment_target: str = Field(..., description="e.g. docker, kubernetes, lambda, vps, bare_metal")
    security_model: str = Field(..., description="e.g. JWT, OAuth2, API_key, session_based")
    caching_strategy: Optional[str] = None
    reasoning: str = Field(..., description="Why this architecture was chosen")


# ─────────────────────────────────────────
# Stage 3: Schema Block Generation
# ─────────────────────────────────────────

class APIEndpoint(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "WS"]
    path: str
    description: str
    request_body: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    auth_required: bool = True
    rate_limited: bool = False


class APILayer(BaseModel):
    base_url: str = Field(default="/api/v1")
    endpoints: List[APIEndpoint]
    versioning_strategy: str = Field(default="url_prefix")
    authentication: str


class DataField(BaseModel):
    name: str
    type: str
    required: bool = True
    unique: bool = False
    indexed: bool = False
    description: Optional[str] = None
    default: Optional[Any] = None


class DataModel(BaseModel):
    name: str
    table_name: str
    fields: List[DataField]
    relationships: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)


class DataLayer(BaseModel):
    database_type: str = Field(..., description="e.g. postgresql, mongodb, sqlite, redis")
    orm: Optional[str] = Field(None, description="e.g. SQLAlchemy, Prisma, Mongoose")
    models: List[DataModel]
    migration_strategy: str = Field(default="alembic")


class Package(BaseModel):
    name: str
    version: str
    purpose: str
    dev_only: bool = False


class DependencyManifest(BaseModel):
    primary_language: str
    runtime_version: str
    packages: List[Package]
    environment_variables: List[str] = Field(default_factory=list)


class FileNode(BaseModel):
    path: str
    type: Literal["file", "directory"]
    description: str
    template: Optional[str] = None  # Starter code snippet


class DirectoryStructure(BaseModel):
    root: str
    files: List[FileNode]


class SchemaGenerationResult(BaseModel):
    """Structured output from Stage 3."""
    api_layer: APILayer
    data_layer: DataLayer
    dependency_manifest: DependencyManifest
    directory_structure: DirectoryStructure


# ─────────────────────────────────────────
# Stage 4: Refinement & Cross-Layer Synthesis
# ─────────────────────────────────────────

class CrossLayerIssue(BaseModel):
    severity: Literal["critical", "warning", "info"]
    layer: str
    description: str
    resolution: str


class RefinementResult(BaseModel):
    """Structured output from Stage 4."""
    issues_found: List[CrossLayerIssue] = Field(default_factory=list)
    optimizations_applied: List[str] = Field(default_factory=list)
    security_hardening: List[str] = Field(default_factory=list)
    implementation_roadmap: List[str] = Field(default_factory=list)
    estimated_build_time_hours: Optional[float] = None
    risk_assessment: str = Field(default="low")


# ─────────────────────────────────────────
# Stage 5: Execution Proof (Sandbox)
# ─────────────────────────────────────────

class SandboxTestResult(BaseModel):
    test_name: str
    passed: bool
    output: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float


class ExecutionProof(BaseModel):
    sandbox_passed: bool = False
    python_syntax_valid: bool = False
    schema_integrity_valid: bool = False
    api_contract_valid: bool = False
    dependency_resolvable: bool = False
    test_results: List[SandboxTestResult] = Field(default_factory=list)
    execution_log: List[str] = Field(default_factory=list)


# ─────────────────────────────────────────
# Final Blueprint — Root Schema
# ─────────────────────────────────────────

class BlueprintMetadata(BaseModel):
    app_name: str
    app_type: str
    primary_language: str
    complexity_score: str = Field(..., description="low / medium / high / enterprise")
    compiled_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    nlc_version: str = "1.0.0"
    original_prompt: str


class ApplicationBlueprint(BaseModel):
    """
    The complete compiled application blueprint.
    Root output schema — every field validated by Pydantic V2.
    """
    metadata: BlueprintMetadata
    intent: IntentExtractionResult
    architecture: ArchitectureDesignResult
    api_layer: APILayer
    data_layer: DataLayer
    dependency_manifest: DependencyManifest
    directory_structure: DirectoryStructure
    refinement: RefinementResult
    execution_proof: ExecutionProof

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v):
        if not v.app_name or len(v.app_name) < 2:
            raise ValueError("app_name must be at least 2 characters")
        return v