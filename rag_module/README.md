# RAG Module (FAISS + HF)

Purpose: small retrieval layer the MCP servers can call to pull relevant filing snippets.

## Layout
- `pipeline.py` — core `RAGPipeline` class (index, query, quick context).
- `cli.py` — `python -m rag_module.cli build-index` and `query`.
- `mcp_tool.py` — helper to expose a `rag_search` tool to MCP.
- `config.py` — defaults (model name, chunk size, paths, cache folder).

## Quickstart
1) Build the index (targets `documents/*.txt` by default):
```
python -m rag_module.cli build-index
```
2) Query:
```
python -m rag_module.cli query "latest revenue guidance"
```

## MCP usage
- Add `rag_module.mcp_tool.rag_tool_definition()` to your MCP `list_tools`.
- Add `rag_module.mcp_tool.execute_rag_tool` to your dispatch table.
- The tool returns plain text chunks annotated with score, source path, and chunk id.

## Notes
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` cached under `rag_module/cache/`.
- Index + metadata live under `rag_module/index/` and are intentionally kept in git. Caches are ignored.
- The HTML filings live in `documents/` (see `documents/fetch_filings.py` to refresh).
