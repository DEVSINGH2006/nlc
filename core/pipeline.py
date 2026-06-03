"""
Compiler Pipeline
==================
Orchestrates all 5 stages in sequence with rich progress output.
Each stage feeds its output into the next — zero global state.
"""

import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text

from core.config import CompilerConfig
from core.llm_client import LLMClient
from stages.stage1_intent import IntentExtractor
from stages.stage2_architecture import ArchitectureDesigner
from stages.stage3_schema import SchemaGenerator
from stages.stage4_refinement import RefinementEngine
from sandbox.executor import LocalVirtualSandbox
from schemas.blueprint import ApplicationBlueprint, BlueprintMetadata, ExecutionProof


STAGES = [
    ("Stage 1", "Intent Extraction",              "cyan"),
    ("Stage 2", "Architecture Design",            "blue"),
    ("Stage 3", "Schema Block Generation",        "magenta"),
    ("Stage 4", "Refinement & Cross-Layer Synthesis", "yellow"),
    ("Stage 5", "Local Virtual Execution Sandbox","green"),
]


class CompilerPipeline:
    def __init__(self, config: CompilerConfig, console: Console):
        self.config = config
        self.console = console
        self.llm = LLMClient(config=config)

    def run(self, prompt: str) -> ApplicationBlueprint:
        self.console.print(Panel(
            f"[bold white]Compiling:[/bold white] [italic cyan]{prompt}[/italic cyan]",
            title="[bold cyan]NLC Compiler[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        ))

        timings = {}

        # ── Stage 1: Intent Extraction ──────────────────────────
        self._print_stage_header("Stage 1", "Intent Extraction", "cyan")
        t = time.time()
        extractor = IntentExtractor(llm=self.llm, config=self.config, console=self.console)
        intent = extractor.run(prompt)
        timings["Stage 1"] = time.time() - t
        self._print_stage_result(intent.model_dump(), timings["Stage 1"], [
            ("Primary Goal",    intent.primary_goal),
            ("App Category",    intent.app_category),
            ("Core Features",   f"{len(intent.core_features)} identified"),
            ("Implicit Reqs",   f"{len(intent.implicit_requirements)} inferred"),
            ("Confidence",      f"{intent.confidence_score:.0%}"),
        ])

        # ── Stage 2: Architecture Design ────────────────────────
        self._print_stage_header("Stage 2", "Architecture Design", "blue")
        t = time.time()
        designer = ArchitectureDesigner(llm=self.llm, config=self.config, console=self.console)
        architecture = designer.run(intent)
        timings["Stage 2"] = time.time() - t
        self._print_stage_result(architecture.model_dump(), timings["Stage 2"], [
            ("Pattern",         architecture.pattern),
            ("Components",      f"{len(architecture.components)} defined"),
            ("Communication",   architecture.communication_style),
            ("Deployment",      architecture.deployment_target),
            ("Security Model",  architecture.security_model),
        ])

        # ── Stage 3: Schema Block Generation ────────────────────
        self._print_stage_header("Stage 3", "Schema Block Generation", "magenta")
        t = time.time()
        generator = SchemaGenerator(llm=self.llm, config=self.config, console=self.console)
        schemas = generator.run(intent, architecture)
        timings["Stage 3"] = time.time() - t
        self._print_stage_result(schemas.model_dump(), timings["Stage 3"], [
            ("API Endpoints",   f"{len(schemas.api_layer.endpoints)} endpoints"),
            ("Data Models",     f"{len(schemas.data_layer.models)} models"),
            ("Dependencies",    f"{len(schemas.dependency_manifest.packages)} packages"),
            ("File Nodes",      f"{len(schemas.directory_structure.files)} files/dirs"),
            ("Database",        schemas.data_layer.database_type),
        ])

        # ── Stage 4: Refinement & Synthesis ─────────────────────
        self._print_stage_header("Stage 4", "Refinement & Cross-Layer Synthesis", "yellow")
        t = time.time()
        refiner = RefinementEngine(llm=self.llm, config=self.config, console=self.console)
        refinement = refiner.run(intent, architecture, schemas)
        timings["Stage 4"] = time.time() - t
        critical = [i for i in refinement.issues_found if i.severity == "critical"]
        warnings  = [i for i in refinement.issues_found if i.severity == "warning"]
        self._print_stage_result(refinement.model_dump(), timings["Stage 4"], [
            ("Issues Found",    f"{len(refinement.issues_found)} total ({len(critical)} critical, {len(warnings)} warnings)"),
            ("Optimizations",   f"{len(refinement.optimizations_applied)} applied"),
            ("Security Fixes",  f"{len(refinement.security_hardening)} applied"),
            ("Roadmap Steps",   f"{len(refinement.implementation_roadmap)} steps"),
            ("Risk Level",      refinement.risk_assessment.upper()),
            ("Est. Build Time", f"{refinement.estimated_build_time_hours}h" if refinement.estimated_build_time_hours else "N/A"),
        ])

        # ── Assemble partial blueprint for sandbox ───────────────
        metadata = BlueprintMetadata(
            app_name=self._derive_app_name(intent),
            app_type=intent.app_category,
            primary_language=schemas.dependency_manifest.primary_language,
            complexity_score=refinement.risk_assessment,
            original_prompt=prompt,
        )

        execution_proof = ExecutionProof()  # default: skipped

        # ── Stage 5: Local Virtual Execution Sandbox ─────────────
        self._print_stage_header("Stage 5", "Local Virtual Execution Sandbox", "green")
        t = time.time()
        partial_blueprint = ApplicationBlueprint(
            metadata=metadata,
            intent=intent,
            architecture=architecture,
            api_layer=schemas.api_layer,
            data_layer=schemas.data_layer,
            dependency_manifest=schemas.dependency_manifest,
            directory_structure=schemas.directory_structure,
            refinement=refinement,
            execution_proof=execution_proof,
        )
        sandbox = LocalVirtualSandbox(console=self.console)
        execution_proof = sandbox.run(partial_blueprint)
        timings["Stage 5"] = time.time() - t

        passed = sum(1 for t_ in execution_proof.test_results if t_.passed)
        total  = len(execution_proof.test_results)
        self._print_stage_result({}, timings["Stage 5"], [
            ("Tests Passed",   f"{passed}/{total}"),
            ("Python Syntax",  "✓ Valid"   if execution_proof.python_syntax_valid   else "✗ Issues found"),
            ("Schema Integrity","✓ Valid"  if execution_proof.schema_integrity_valid else "✗ Issues found"),
            ("API Contracts",  "✓ Valid"   if execution_proof.api_contract_valid     else "✗ Issues found"),
            ("Dependencies",   "✓ Valid"   if execution_proof.dependency_resolvable  else "✗ Issues found"),
            ("Sandbox Status", "[bold green]PASSED[/bold green]" if execution_proof.sandbox_passed else "[bold yellow]COMPLETED WITH WARNINGS[/bold yellow]"),
        ])

        # ── Final Assembly ───────────────────────────────────────
        blueprint = ApplicationBlueprint(
            metadata=metadata,
            intent=intent,
            architecture=architecture,
            api_layer=schemas.api_layer,
            data_layer=schemas.data_layer,
            dependency_manifest=schemas.dependency_manifest,
            directory_structure=schemas.directory_structure,
            refinement=refinement,
            execution_proof=execution_proof,
        )

        total_time = sum(timings.values())
        self.console.print(f"\n[bold cyan]✓ Compilation complete[/bold cyan] in [white]{total_time:.1f}s[/white]\n")

        return blueprint

    # ── Helpers ──────────────────────────────────────────────────

    def _print_stage_header(self, stage_id: str, name: str, color: str):
        self.console.print(f"\n[bold {color}]▶ {stage_id}[/bold {color}] [white]{name}[/white]")
        self.console.print(f"  [dim]{'─' * 50}[/dim]")

    def _print_stage_result(self, data: dict, elapsed: float, fields: list):
        for label, value in fields:
            self.console.print(f"  [dim]{label:<20}[/dim] {value}")
        self.console.print(f"  [dim]{'─' * 50}[/dim]")
        self.console.print(f"  [dim green]✓ Done in {elapsed:.1f}s[/dim green]")

    def _derive_app_name(self, intent) -> str:
        """Extract a clean app name from the primary goal."""
        goal = intent.primary_goal
        words = goal.replace("Build", "").replace("Create", "").replace("A ", "").split()
        name_words = [w.capitalize() for w in words[:3] if len(w) > 2]
        return "".join(name_words) or "GeneratedApp"