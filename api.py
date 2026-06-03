import asyncio
from functools import partial

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()  # Load GEMINI_API_KEY from .env before pipeline starts

from core.pipeline import CompilerPipeline
from core.config import CompilerConfig

app = FastAPI(
    title="Natural Language Compiler",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CompileRequest(BaseModel):
    prompt: str


@app.get("/", response_class=FileResponse)
async def serve_ui():
    """Serve the frontend."""
    return FileResponse("index.html")


@app.get("/health")
async def health():
    return {"status": "online", "service": "NLC Compiler"}


@app.post("/compile")
async def compile_app(data: CompileRequest):
    console = Console()
    config = CompilerConfig(run_sandbox=True, verbose=False)
    pipeline = CompilerPipeline(config=config, console=console)

    loop = asyncio.get_event_loop()
    try:
        # Run the blocking pipeline in a thread so the async event loop stays responsive
        blueprint = await asyncio.wait_for(
            loop.run_in_executor(None, partial(pipeline.run, data.prompt)),
            timeout=300  # 5 minute hard cap per compile request
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Compilation timed out after 5 minutes.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return blueprint.model_dump()
