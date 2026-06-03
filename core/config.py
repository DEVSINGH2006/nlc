from dataclasses import dataclass

@dataclass
class CompilerConfig:
    max_retries: int = 3
    run_sandbox: bool = False
    verbose: bool = False
    output_path: str = "output/blueprint.json"
    model: str = "gemini-2.5-flash"
    max_tokens: int = 2048
    temperature: float = 0.0
    stage_timeout_seconds: int = 60
    sandbox_timeout_seconds: int = 30
