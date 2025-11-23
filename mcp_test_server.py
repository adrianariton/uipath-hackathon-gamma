# MCP SERVER
# PORT:5000
import asyncio
import requests
import os
import random 
from datetime import datetime
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from browser_use_client import start_crawl, get_crawl_status
app = Server("test-mcp-server")

cert_file = os.path.expanduser(os.getenv("CERT_FILE") or "~/.office-addin-dev-certs/localhost.crt")
key_file  = os.path.expanduser(os.getenv("KEY_FILE") or "~/.office-addin-dev-certs/localhost.key")
print(cert_file, key_file)
# Trimite comanda catre Backend-ul principal (port 8000)
# Backend-ul o va da mai departe la Excel prin WebSocket
# MCP SERVER: Modifică to_server
def to_server(key : str, data: dict):
    url = 'https://localhost:8000/enqueue' 
    headers = {'Content-type': 'application/json'}
    payload = {'command': key, 'params' : data}
    
    try: # Adaugă un try/except AICI
        response = requests.post(url, json=payload, headers=headers, timeout=30, verify=cert_file)
        response.raise_for_status() # Aruncă excepție pentru 4xx/5xx HTTP
        
        json_resp = response.json()
        print(f"🤖 MCP: Primit raspuns de la Flask: {json_resp}") # Log util!
        
        if json_resp.get("status") == "ok":
            return str(json_resp.get("client_response", {}).get("result", "Done"))
        else:
            return f"Say this exact thing: Error from client/Flask: {json_resp.get('reason')}"
            
    except requests.exceptions.RequestException as e:
        print(f"❌ EROARE CRITICĂ MCP-to-Flask: {e}")
        # Aici apare eroarea dacă Flask nu e accesibil sau returnează 503/500 rapid
        return f"Say this exact thing: CRITICAL COMMUNICATION ERROR: {str(e)}"

# =========================================================
# 1. TOOL EXECUTION FUNCTIONS
# =========================================================
async def exec_modify_cells(arguments: dict) -> list[TextContent]:
    result = to_server("modify_cells", arguments)
    return [TextContent(type="text", text=result)]

async def exec_read_subtable(arguments: dict) -> list[TextContent]:
    result = to_server("read_subtable", arguments)
    return [TextContent(type="text", text=result)]

async def exec_read_cells_text(arguments: dict) -> list[TextContent]:
    result = to_server("read_cells_text", arguments)
    return [TextContent(type="text", text=result)]
    
async def exec_read_cells_values(arguments: dict) -> list[TextContent]:
    result = to_server("read_cells_values", arguments)
    return [TextContent(type="text", text=result)]
    
async def exec_extend_cell_formula(arguments: dict) -> list[TextContent]:
    result = to_server("extend", arguments) # am corectat cheia in 'extend' sa bata cu App.tsx
    return [TextContent(type="text", text=result)]

async def exec_get_current_time(arguments: dict) -> list[TextContent]:
    now = datetime.now()
    result = f"Current time: {now}"
    return [TextContent(type="text", text=result)]

async def exec_get_random_number(arguments: dict) -> list[TextContent]:
    interval = arguments.get("interval", [1, 100])
    rand_num = random.randint(interval[0], interval[1])
    return [TextContent(type="text", text=str(rand_num))]


# =========================================================
# 2. DISPATCH TABLE
# =========================================================

# AICI ERA EROAREA: Am scos 'calculate' care nu exista
TOOL_DISPATCH = {
    "get_current_time": exec_get_current_time,
    "get_random_number": exec_get_random_number,
    "modify_cells": exec_modify_cells,
    "read_subtable": exec_read_subtable,
    "read_cells_text": exec_read_cells_text,
    "read_cells_values": exec_read_cells_values,
    "extend_cell_formula": exec_extend_cell_formula,
    "start_crawl": start_crawl,
    "get_crawl_status": get_crawl_status
}

# =========================================================
# 3. CORE MCP SERVER LOGIC
# =========================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="start_crawl",
             description="Start a browser-based crawl for a given prompt and company name.",
             inputSchema={
                 "type": "object",
                 "properties": {
                     "prompt": {"type": "string"},
                     "company_name": {"type": "string"},
                 },
                 "required": ["prompt"]
             }),
        Tool(name="get_crawl_status",
             description="Get the status/result of a previously started crawl by query id.",
             inputSchema={
                 "type": "object",
                 "properties": {
                     "query_id": {"type": "number"} 
                 }
             }),
        Tool(
            name="modify_cells",
            description="Write values or formulas into Excel cells. The argument MUST be a dictionary called 'cells' where keys are cell addresses (e.g., 'A1') and values are the content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cells": {
                        "type": "object",
                        "description": "Dictionary of cell_name:value, e.g. {'A1': 100, 'B2': '=A1+10'}"
                    }
                },
                "required": ["cells"]
            },
        ),
        Tool(
            name="read_subtable",
            description="Read a range of cells as a matrix of strings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "col1": {"type": "string"},
                    "col2": {"type": "string"},
                    "row1": {"type": "number"},
                    "row2": {"type": "number"}
                },
                "required": ["col1", "col2", "row1", "row2"]
            },
        ),
        Tool(
            name="read_cells_values",
            description="Read specific individual cells.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cells": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["cells"]
            },
        ),
         Tool(
            name="extend_cell_formula",
            description="Drag/Autofill a cell to a target range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"}
                },
                "required": ["source", "target"]
            },
        ),
        Tool(
            name="get_current_time",
            description="Get current time",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_random_number",
            description="Get random number",
            inputSchema={
                "type": "object",
                "properties": {
                    "interval": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2,
                        "description": "[min, max]"
                    }
                },
                "required": ["interval"]
            },
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    executor = TOOL_DISPATCH.get(name)
    if executor:
        try:
            return await executor(arguments)
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    print("Running MCP!")
    asyncio.run(main())
