from __future__ import annotations

from pathlib import Path

import typer

from .config import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_SOURCE_DIR,
    DEFAULT_TOP_K,
)
from .pipeline import RAGPipeline

app = typer.Typer(help="RAG helper CLI (build index, query)")


@app.command("build-index")
def build_index(
    source: Path = typer.Option(
        DEFAULT_SOURCE_DIR,
        "--source",
        "-s",
        help="Directory containing text files to index.",
    ),
    glob: str = typer.Option("*.txt", "--glob", help="Glob for files to include."),
    chunk_size: int = typer.Option(DEFAULT_CHUNK_SIZE, "--chunk-size", help="Words per chunk."),
    overlap: int = typer.Option(DEFAULT_CHUNK_OVERLAP, "--overlap", help="Word overlap between chunks."),
    reset: bool = typer.Option(True, "--reset/--append", help="Rebuild from scratch or append to existing index."),
) -> None:
    rag = RAGPipeline()
    added = rag.index_directory(
        source_dir=source, glob_pattern=glob, chunk_size=chunk_size, overlap=overlap, reset=reset
    )
    if added == 0:
        typer.echo("No text files found to index.")
        return
    rag.save()
    typer.echo(f"Indexed {added} chunks from {source}")
    typer.echo(f"FAISS index: {rag.index_path}")
    typer.echo(f"Metadata: {rag.metadata_path}")


@app.command("query")
def query_index(
    query: str = typer.Argument(..., help="Natural language query to search for."),
    top_k: int = typer.Option(DEFAULT_TOP_K, "--top-k", "-k", help="Number of chunks to return."),
) -> None:
    rag = RAGPipeline()
    results = rag.query(query, top_k=top_k)
    if not results:
        typer.echo("No results found.")
        return
    for res in results:
        typer.echo(f"{res['score']:.3f} | {res['source']} #chunk-{res['chunk_id']}")
        typer.echo(res["text"])
        typer.echo("-" * 40)


if __name__ == "__main__":
    app()
