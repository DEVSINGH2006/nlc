import asyncio
import os
import logging
from functools import partial
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()  # Load GEMINI_API_KEY from .env before pipeline starts

from core.pipeline import CompilerPipeline
from core.config import CompilerConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Natural Language Compiler",
    version="1.0"
)

# Configure CORS with whitelisting
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)


class CompileRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=5000, description="Application description")

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v):
        if not v.strip():
            raise ValueError("Prompt cannot be empty or only whitespace")
        if len(v) < 10:
            raise ValueError("Prompt must be at least 10 characters")
        if len(v) > 5000:
            raise ValueError("Prompt cannot exceed 5000 characters")
        return v.strip()


@app.on_event("startup")
async def validate_startup():
    """Validate configuration on startup."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set! "
            "Get a free key from https://aistudio.google.com/apikey "
            "and set it in .env or Render environment variables."
        )
    if not api_key.startswith("AIza"):
        logger.warning(f"GEMINI_API_KEY doesn't start with 'AIza' - may be invalid format")
    logger.info("Startup validation passed")


@app.get("/", response_class=FileResponse)
async def serve_ui():
    """Serve the frontend."""
    index_path = Path(__file__).parent / "index.html"
    if not index_path.exists():
        logger.error(f"index.html not found at {index_path}")
        raise HTTPException(status_code=404, detail="index.html not found")
    logger.info("Serving index.html")
    return FileResponse(index_path)


@app.get("/health")
async def health():
    return {"status": "online", "service": "NLC Compiler"}


from rich.console import Console

@app.post("/compile")
async def compile_app(data: CompileRequest):
    """Compile a natural language prompt into an application blueprint."""
    logger.info(f"Compilation started for prompt (length={len(data.prompt)})")

    config = CompilerConfig(run_sandbox=True, verbose=False)
    console = Console()  # ✅ Use real console
    pipeline = CompilerPipeline(config=config, console=console)

    loop = asyncio.get_event_loop()
    try:
        blueprint = await asyncio.wait_for(
            loop.run_in_executor(None, partial(pipeline.run, data.prompt)),
            timeout=300
        )
        logger.info(f"Compilation completed successfully")
        return blueprint.model_dump()

    except asyncio.TimeoutError:
        logger.error("Compilation timed out after 5 minutes")
        raise HTTPException(
            status_code=504,
            detail="Compilation timed out after 5 minutes. Try a simpler app description."
        )
    except ValueError as e:
        error_msg = str(e)[:200]
        logger.warning(f"Validation error: {error_msg}")
        raise HTTPException(status_code=422, detail=error_msg)
    except Exception as e:
        error_msg = str(e)

        # Sanitize error messages before returning to client
        if "GEMINI_API_KEY" in error_msg or "API key" in error_msg:
            error_msg = "Invalid or missing GEMINI_API_KEY in server configuration"
        elif "API_KEY_INVALID" in error_msg:
            error_msg = "Invalid GEMINI_API_KEY. Check server configuration."
        elif "daily quota" in error_msg.lower() or "limit: 0" in error_msg:
            error_msg = "Gemini API quota exhausted. Try again tomorrow."
        elif "429" in error_msg and "quota" in error_msg.lower():
            error_msg = "Rate limited on Gemini API. Try again in 60 seconds."
        elif "429" in error_msg:
            error_msg = "Rate limited. Too many requests to Gemini API. Try again in 60 seconds."
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            error_msg = "Gemini API blocked (network/firewall issue)."
        else:
            error_msg = error_msg[:200]

        logger.error(f"Compilation error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)