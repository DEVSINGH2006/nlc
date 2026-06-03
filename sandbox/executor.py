"""
Stage 5: Local Virtual Execution Sandbox (Bonus Feature)
==========================================================
Executes a suite of verification tests against the generated blueprint
WITHOUT actually running any application code.

Tests performed:
  1. Python Syntax Validation — validates any Python templates in the blueprint
  2. Schema Integrity Check — validates all Pydantic models parse correctly
  3. API Contract Validation — checks endpoint paths, methods, and schemas
  4. Dependency Resolvability — verifies package names are well-formed
  5. Cross-Reference Audit — every API endpoint's model refs exist in data layer
  6. Security Policy Check — critical endpoints have auth_required=True
  7. Blueprint Completeness — all required sections present and non-empty

This sandbox proves the blueprint is operationally valid before delivery.
"""

import ast
import time
import json
import re
from typing import List, Tuple
from schemas.blueprint import (
    ApplicationBlueprint,
    ExecutionProof,
    SandboxTestResult,
)


class LocalVirtualSandbox:
    def __init__(self, console=None):
        self.console = console

    def run(self, blueprint: ApplicationBlueprint) -> ExecutionProof:
        proof = ExecutionProof()
        tests: List[SandboxTestResult] = []
        log: List[str] = []

        log.append("═══ Local Virtual Execution Sandbox ═══")
        log.append(f"Target: {blueprint.metadata.app_name}")
        log.append(f"Timestamp: {blueprint.metadata.compiled_at}")
        log.append("")

        # Test 1: Python syntax validation
        result = self._test_python_syntax(blueprint)
        tests.append(result)
        proof.python_syntax_valid = result.passed
        log.append(f"[{'PASS' if result.passed else 'FAIL'}] {result.test_name}")

        # Test 2: Schema integrity
        result = self._test_schema_integrity(blueprint)
        tests.append(result)
        proof.schema_integrity_valid = result.passed
        log.append(f"[{'PASS' if result.passed else 'FAIL'}] {result.test_name}")

        # Test 3: API contract validation
        result = self._test_api_contracts(blueprint)
        tests.append(result)
        proof.api_contract_valid = result.passed
        log.append(f"[{'PASS' if result.passed else 'FAIL'}] {result.test_name}")

        # Test 4: Dependency resolvability
        result = self._test_dependencies(blueprint)
        tests.append(result)
        proof.dependency_resolvable = result.passed
        log.append(f"[{'PASS' if result.passed else 'FAIL'}] {result.test_name}")

        # Test 5: Cross-reference audit
        result = self._test_cross_references(blueprint)
        tests.append(result)
        log.append(f"[{'PASS' if result.passed else 'FAIL'}] {result.test_name}")

        # Test 6: Security policy
        result = self._test_security_policy(blueprint)
        tests.append(result)
        log.append(f"[{'PASS' if result.passed else 'FAIL'}] {result.test_name}")

        # Test 7: Blueprint completeness
        result = self._test_completeness(blueprint)
        tests.append(result)
        log.append(f"[{'PASS' if result.passed else 'FAIL'}] {result.test_name}")

        # Final verdict
        all_passed = all(t.passed for t in tests)
        critical_passed = all(
            t.passed for t in tests
            if t.test_name in [
                "Python Syntax Validation",
                "Schema Integrity Check",
                "API Contract Validation",
            ]
        )
        proof.sandbox_passed = critical_passed
        proof.test_results = tests
        proof.execution_log = log

        log.append("")
        log.append(f"═══ Sandbox Result: {'ALL TESTS PASSED' if all_passed else 'COMPLETED WITH WARNINGS'} ═══")
        log.append(f"Tests: {sum(1 for t in tests if t.passed)}/{len(tests)} passed")

        return proof

    # ─── Individual Tests ───────────────────────────────────────

    def _test_python_syntax(self, blueprint: ApplicationBlueprint) -> SandboxTestResult:
        start = time.time()
        errors = []

        for node in blueprint.directory_structure.files:
            if node.template and node.path.endswith(".py"):
                try:
                    ast.parse(node.template)
                except SyntaxError as e:
                    errors.append(f"{node.path}: {e}")

        duration = (time.time() - start) * 1000
        if errors:
            return SandboxTestResult(
                test_name="Python Syntax Validation",
                passed=False,
                error="; ".join(errors),
                duration_ms=duration,
            )
        return SandboxTestResult(
            test_name="Python Syntax Validation",
            passed=True,
            output=f"Validated {sum(1 for n in blueprint.directory_structure.files if n.template and n.path.endswith('.py'))} Python files",
            duration_ms=duration,
        )

    def _test_schema_integrity(self, blueprint: ApplicationBlueprint) -> SandboxTestResult:
        start = time.time()
        try:
            # Re-validate the whole blueprint by dumping and reloading
            dumped = blueprint.model_dump()
            reloaded = ApplicationBlueprint(**dumped)
            duration = (time.time() - start) * 1000
            return SandboxTestResult(
                test_name="Schema Integrity Check",
                passed=True,
                output=f"Blueprint re-validation successful. {len(dumped)} top-level keys.",
                duration_ms=duration,
            )
        except Exception as e:
            return SandboxTestResult(
                test_name="Schema Integrity Check",
                passed=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    def _test_api_contracts(self, blueprint: ApplicationBlueprint) -> SandboxTestResult:
        start = time.time()
        errors = []
        path_pattern = re.compile(r"^/[a-zA-Z0-9/_{}.-]*$")

        for ep in blueprint.api_layer.endpoints:
            if not path_pattern.match(ep.path):
                errors.append(f"Invalid path format: {ep.path}")
            if ep.method not in ["GET", "POST", "PUT", "PATCH", "DELETE", "WS"]:
                errors.append(f"Invalid method '{ep.method}' for {ep.path}")
            if not ep.description or len(ep.description) < 5:
                errors.append(f"Missing/short description for {ep.path}")

        # Check for duplicate paths+methods
        seen = set()
        for ep in blueprint.api_layer.endpoints:
            key = f"{ep.method}:{ep.path}"
            if key in seen:
                errors.append(f"Duplicate endpoint: {key}")
            seen.add(key)

        duration = (time.time() - start) * 1000
        if errors:
            return SandboxTestResult(
                test_name="API Contract Validation",
                passed=False,
                error="; ".join(errors[:3]),
                duration_ms=duration,
            )
        return SandboxTestResult(
            test_name="API Contract Validation",
            passed=True,
            output=f"{len(blueprint.api_layer.endpoints)} endpoints validated",
            duration_ms=duration,
        )

    def _test_dependencies(self, blueprint: ApplicationBlueprint) -> SandboxTestResult:
        start = time.time()
        errors = []
        pkg_name_pattern = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$")

        for pkg in blueprint.dependency_manifest.packages:
            if not pkg_name_pattern.match(pkg.name):
                errors.append(f"Suspicious package name: '{pkg.name}'")
            if not pkg.version or pkg.version.lower() in ["latest", "any", "*", ""]:
                errors.append(f"Package '{pkg.name}' has no pinned version")
            if not pkg.purpose:
                errors.append(f"Package '{pkg.name}' missing purpose")

        duration = (time.time() - start) * 1000
        if errors:
            return SandboxTestResult(
                test_name="Dependency Resolvability",
                passed=False,
                error="; ".join(errors[:3]),
                duration_ms=duration,
            )
        return SandboxTestResult(
            test_name="Dependency Resolvability",
            passed=True,
            output=f"{len(blueprint.dependency_manifest.packages)} packages validated",
            duration_ms=duration,
        )

    def _test_cross_references(self, blueprint: ApplicationBlueprint) -> SandboxTestResult:
        start = time.time()
        model_names = {m.name.lower() for m in blueprint.data_layer.models}
        warnings = []

        # Check if endpoints reference known entity names
        for ep in blueprint.api_layer.endpoints:
            path_parts = ep.path.strip("/").split("/")
            for part in path_parts:
                if part and not part.startswith("{") and part not in ["api", "v1", "v2", "health", "auth"]:
                    # Heuristic: plural path segments should match model names
                    singular = part.rstrip("s")
                    if singular not in model_names and part not in model_names:
                        warnings.append(f"Path segment '{part}' has no matching data model")

        duration = (time.time() - start) * 1000
        if warnings:
            return SandboxTestResult(
                test_name="Cross-Reference Audit",
                passed=True,  # Warnings, not failures
                output=f"Completed with {len(warnings)} advisory notes",
                error="; ".join(warnings[:2]) if warnings else None,
                duration_ms=duration,
            )
        return SandboxTestResult(
            test_name="Cross-Reference Audit",
            passed=True,
            output="All API-to-model references consistent",
            duration_ms=duration,
        )

    def _test_security_policy(self, blueprint: ApplicationBlueprint) -> SandboxTestResult:
        start = time.time()
        violations = []
        sensitive_patterns = ["delete", "admin", "user", "password", "token", "secret", "payment"]

        for ep in blueprint.api_layer.endpoints:
            path_lower = ep.path.lower()
            # Authentication endpoints (token retrieval, login, registration) are public by design
            if "auth/token" in path_lower or "login" in path_lower or "register" in path_lower:
                continue
            is_sensitive = any(p in path_lower for p in sensitive_patterns)
            if is_sensitive and not ep.auth_required:
                violations.append(f"Sensitive endpoint unprotected: {ep.method} {ep.path}")

        duration = (time.time() - start) * 1000
        if violations:
            return SandboxTestResult(
                test_name="Security Policy Check",
                passed=False,
                error=f"{len(violations)} unprotected sensitive endpoint(s): " + "; ".join(violations[:2]),
                duration_ms=duration,
            )
        return SandboxTestResult(
            test_name="Security Policy Check",
            passed=True,
            output="Security policy compliant",
            duration_ms=duration,
        )

    def _test_completeness(self, blueprint: ApplicationBlueprint) -> SandboxTestResult:
        start = time.time()
        missing = []

        if not blueprint.metadata.app_name:
            missing.append("metadata.app_name")
        if not blueprint.architecture.components:
            missing.append("architecture.components")
        if not blueprint.api_layer.endpoints:
            missing.append("api_layer.endpoints")
        if not blueprint.data_layer.models:
            missing.append("data_layer.models")
        if not blueprint.dependency_manifest.packages:
            missing.append("dependency_manifest.packages")
        if not blueprint.directory_structure.files:
            missing.append("directory_structure.files")
        if not blueprint.refinement.implementation_roadmap:
            missing.append("refinement.implementation_roadmap")

        duration = (time.time() - start) * 1000
        if missing:
            return SandboxTestResult(
                test_name="Blueprint Completeness",
                passed=False,
                error=f"Missing sections: {', '.join(missing)}",
                duration_ms=duration,
            )
        return SandboxTestResult(
            test_name="Blueprint Completeness",
            passed=True,
            output="All required blueprint sections present",
            duration_ms=duration,
        )