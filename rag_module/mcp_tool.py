from __future__ import annotations

from typing import List, Optional

from mcp.types import TextContent, Tool

from .config import DEFAULT_TOP_K
from .pipeline import RAGPipeline

_PIPELINE: RAGPipeline | None = None


def _get_pipeline() -> RAGPipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = RAGPipeline()
    return _PIPELINE


def rag_tool_definition() -> Tool:
    """Tool definition for MCP registration."""
    return Tool(
        name="rag_search",
        description="Search the FAISS index of filings and return the most relevant chunks for a query.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look for in the filings."},
                "top_k": {
                    "type": "integer",
                    "default": DEFAULT_TOP_K,
                    "minimum": 1,
                    "maximum": 20,
                    "description": "How many chunks to return.",
                },
            },
            "required": ["query"],
        },
    )


async def execute_rag_tool(arguments: dict, pipeline: Optional[RAGPipeline] = None) -> List[TextContent]:
    """Async wrapper so it can plug into MCP dispatch tables."""
    query = arguments.get("query", "")
    top_k = int(arguments.get("top_k", DEFAULT_TOP_K))
    pipe = pipeline or _get_pipeline()
    try:
        results = pipe.query(query, top_k=top_k)
        if not results:
            text = "No results found."
        else:
            text = "\n\n".join(
                f"[{res['score']:.3f}] {res['source']}#chunk-{res['chunk_id']} :: {res['text']}"
                for res in results
            )
    except FileNotFoundError:
        text = "RAG index missing. Run `python -m rag_module.cli build-index` first."
    except Exception as exc:  # pragma: no cover - operational path
        text = f"RAG error: {exc}"
    return [TextContent(type="text", text=text)]
