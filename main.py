"""
NLC — Natural Language Compiler
=================================
Pre-Interview Demo Task | AI Engineer Internship @ The AI Signal
Author: Candidate Submission

Pipeline:
  Stage 1 → Intent Extraction
  Stage 2 → Architecture Design
  Stage 3 → Schema Block Generation
  Stage 4 → Refinement & Cross-Layer Synthesis
  Stage 5 → Local Virtual Execution Sandbox (Bonus)
"""

import sys
import json
import time
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich import box

from core.pipeline import CompilerPipeline
from core.config import CompilerConfig

console = Console()


def print_banner():
    banner = Text()
    banner.append("\n  ███╗   ██╗██╗      ██████╗\n", style="bold cyan")
    banner.append("  ████╗  ██║██║     ██╔════╝\n", style="bold cyan")
    banner.append("  ██╔██╗ ██║██║     ██║\n", style="bold cyan")
    banner.append("  ██║╚██╗██║██║     ██║\n", style="bold cyan")
    banner.append("  ██║ ╚████║███████╗╚██████╗\n", style="bold cyan")
    banner.append("  ╚═╝  ╚═══╝╚══════╝ ╚═════╝\n", style="bold cyan")
    banner.append("\n  Natural Language Compiler  ", style="bold white")
    banner.append("v1.0.0\n", style="dim white")
    banner.append("  AI Engineer Internship Demo  ", style="dim cyan")
    banner.append("@ The AI Signal\n\n", style="dim white")
    console.print(banner)


def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description="NLC — Natural Language to Application Blueprint Compiler"
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Natural language description of the application to build",
    )
    parser.add_argument(
        "--output", "-o",
        default="output/blueprint.json",
        help="Output path for the generated JSON blueprint",
    )
    parser.add_argument(
        "--sandbox", "-s",
        action="store_true",
        help="Run Local Virtual Execution Sandbox after compilation",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Max self-healing retry attempts per stage",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose stage-by-stage output",
    )
    args = parser.parse_args()

    # Get prompt
    if args.prompt:
        user_prompt = args.prompt
    else:
        console.print("[bold cyan]Enter your application description:[/bold cyan]")
        console.print("[dim](Describe what you want to build in plain English)[/dim]\n")
        user_prompt = input("  > ").strip()
        if not user_prompt:
            console.print("[bold red]✗ No input provided. Exiting.[/bold red]")
            sys.exit(1)

    console.print(f"\n[dim]Input captured:[/dim] [italic white]{user_prompt}[/italic white]\n")

    # Build config
    config = CompilerConfig(
        max_retries=args.max_retries,
        run_sandbox=args.sandbox,
        verbose=args.verbose,
        output_path=args.output,
    )

    # Run pipeline
    pipeline = CompilerPipeline(config=config, console=console)

    try:
        blueprint = pipeline.run(user_prompt)

        # Write output
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(blueprint.model_dump(), f, indent=2, default=str)

        console.print(f"\n[bold green]✓ Blueprint saved →[/bold green] [cyan]{output_path}[/cyan]")

        # Final summary table
        _print_summary(blueprint, console)

    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠ Compilation interrupted by user.[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]✗ Fatal compiler error:[/bold red] {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _print_summary(blueprint, console):
    from schemas.blueprint import ApplicationBlueprint
    table = Table(
        title="[bold cyan]Compilation Summary[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
        show_header=True,
        header_style="bold white",
    )
    table.add_column("Property", style="dim cyan", width=24)
    table.add_column("Value", style="white")

    table.add_row("App Name", blueprint.metadata.app_name)
    table.add_row("App Type", blueprint.metadata.app_type)
    table.add_row("Primary Language", blueprint.metadata.primary_language)
    table.add_row("Complexity", blueprint.metadata.complexity_score)
    table.add_row("Components", str(len(blueprint.architecture.components)))
    table.add_row("API Endpoints", str(len(blueprint.api_layer.endpoints)))
    table.add_row("Data Models", str(len(blueprint.data_layer.models)))
    table.add_row("Dependencies", str(len(blueprint.dependency_manifest.packages)))
    table.add_row("Sandbox Status", "[green]PASSED[/green]" if blueprint.execution_proof.sandbox_passed else "[yellow]SKIPPED[/yellow]")

    console.print()
    console.print(table)
    console.print()


if __name__ == "__main__":
    main()