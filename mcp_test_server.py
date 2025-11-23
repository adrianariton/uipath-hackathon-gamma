# # MCP SERVER
# # PORT:5000
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

app = Server("excel-mcp-server")

cert_file = os.path.expanduser(os.getenv("CERT_FILE") or "~/.office-addin-dev-certs/localhost.crt")
key_file  = os.path.expanduser(os.getenv("KEY_FILE") or "~/.office-addin-dev-certs/localhost.key")
print(cert_file, key_file)

# Trimite comanda catre Backend-ul principal (port 8000)
def to_server(key: str, data: dict):
    url = 'https://localhost:8000/enqueue' 
    headers = {'Content-type': 'application/json'}
    payload = {'command': key, 'params': data}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30, verify=cert_file)
        response.raise_for_status()
        
        json_resp = response.json()
        print(f"🤖 MCP: Primit raspuns de la Flask: {json_resp}")
        
        if json_resp.get("status") == "ok":
            return str(json_resp.get("client_response", {}).get("result", "Done"))
        else:
            return f"Say this exact thing: Error from client/Flask: {json_resp.get('reason')}"
            
    except requests.exceptions.RequestException as e:
        print(f"❌ EROARE CRITICĂ MCP-to-Flask: {e}")
        return f"Say this exact thing: CRITICAL COMMUNICATION ERROR: {str(e)}"

# =========================================================
# TOOL EXECUTION FUNCTIONS
# =========================================================

# ========== CELL OPERATIONS ==========
async def exec_modify_cells(arguments: dict) -> list[TextContent]:
    result = to_server("modify_cells", arguments)
    return [TextContent(type="text", text=result)]

async def exec_read_cells_text(arguments: dict) -> list[TextContent]:
    result = to_server("read_cells_text", arguments)
    return [TextContent(type="text", text=result)]
    
async def exec_read_cells_values(arguments: dict) -> list[TextContent]:
    result = to_server("read_cells_values", arguments)
    return [TextContent(type="text", text=result)]

async def exec_read_range(arguments: dict) -> list[TextContent]:
    result = to_server("read_range", arguments)
    return [TextContent(type="text", text=result)]

async def exec_read_subtable(arguments: dict) -> list[TextContent]:
    result = to_server("read_subtable", arguments)
    return [TextContent(type="text", text=result)]

async def exec_clear_range(arguments: dict) -> list[TextContent]:
    result = to_server("clear_range", arguments)
    return [TextContent(type="text", text=result)]
    
async def exec_extend_cell_formula(arguments: dict) -> list[TextContent]:
    result = to_server("extend", arguments)
    return [TextContent(type="text", text=result)]

# ========== WORKSHEET OPERATIONS ==========
async def exec_get_active_sheet(arguments: dict) -> list[TextContent]:
    result = to_server("get_active_sheet", arguments)
    return [TextContent(type="text", text=result)]

async def exec_list_sheets(arguments: dict) -> list[TextContent]:
    result = to_server("list_sheets", arguments)
    return [TextContent(type="text", text=result)]

async def exec_create_sheet(arguments: dict) -> list[TextContent]:
    result = to_server("create_sheet", arguments)
    return [TextContent(type="text", text=result)]

async def exec_activate_sheet(arguments: dict) -> list[TextContent]:
    result = to_server("activate_sheet", arguments)
    return [TextContent(type="text", text=result)]

async def exec_delete_sheet(arguments: dict) -> list[TextContent]:
    result = to_server("delete_sheet", arguments)
    return [TextContent(type="text", text=result)]

async def exec_rename_sheet(arguments: dict) -> list[TextContent]:
    result = to_server("rename_sheet", arguments)
    return [TextContent(type="text", text=result)]

# ========== FORMATTING ==========
async def exec_format_cells(arguments: dict) -> list[TextContent]:
    result = to_server("format_cells", arguments)
    return [TextContent(type="text", text=result)]

async def exec_add_border(arguments: dict) -> list[TextContent]:
    result = to_server("add_border", arguments)
    return [TextContent(type="text", text=result)]

async def exec_set_number_format(arguments: dict) -> list[TextContent]:
    result = to_server("set_number_format", arguments)
    return [TextContent(type="text", text=result)]

# ========== ROWS & COLUMNS ==========
async def exec_insert_rows(arguments: dict) -> list[TextContent]:
    result = to_server("insert_rows", arguments)
    return [TextContent(type="text", text=result)]

async def exec_delete_rows(arguments: dict) -> list[TextContent]:
    result = to_server("delete_rows", arguments)
    return [TextContent(type="text", text=result)]

async def exec_insert_columns(arguments: dict) -> list[TextContent]:
    result = to_server("insert_columns", arguments)
    return [TextContent(type="text", text=result)]

async def exec_delete_columns(arguments: dict) -> list[TextContent]:
    result = to_server("delete_columns", arguments)
    return [TextContent(type="text", text=result)]

async def exec_auto_fit_columns(arguments: dict) -> list[TextContent]:
    result = to_server("auto_fit_columns", arguments)
    return [TextContent(type="text", text=result)]

async def exec_auto_fit_rows(arguments: dict) -> list[TextContent]:
    result = to_server("auto_fit_rows", arguments)
    return [TextContent(type="text", text=result)]

# ========== CHARTS ==========
async def exec_create_chart(arguments: dict) -> list[TextContent]:
    result = to_server("create_chart", arguments)
    return [TextContent(type="text", text=result)]

async def exec_delete_all_charts(arguments: dict) -> list[TextContent]:
    result = to_server("delete_all_charts", arguments)
    return [TextContent(type="text", text=result)]

# ========== TABLES ==========
async def exec_create_table(arguments: dict) -> list[TextContent]:
    result = to_server("create_table", arguments)
    return [TextContent(type="text", text=result)]

async def exec_list_tables(arguments: dict) -> list[TextContent]:
    result = to_server("list_tables", arguments)
    return [TextContent(type="text", text=result)]

async def exec_delete_table(arguments: dict) -> list[TextContent]:
    result = to_server("delete_table", arguments)
    return [TextContent(type="text", text=result)]

# ========== FORMULAS ==========
async def exec_get_formula(arguments: dict) -> list[TextContent]:
    result = to_server("get_formula", arguments)
    return [TextContent(type="text", text=result)]

async def exec_set_formula(arguments: dict) -> list[TextContent]:
    result = to_server("set_formula", arguments)
    return [TextContent(type="text", text=result)]

# ========== SORTING & FILTERING ==========
async def exec_sort_range(arguments: dict) -> list[TextContent]:
    result = to_server("sort_range", arguments)
    return [TextContent(type="text", text=result)]

# ========== FIND & REPLACE ==========
async def exec_find_in_range(arguments: dict) -> list[TextContent]:
    result = to_server("find_in_range", arguments)
    return [TextContent(type="text", text=result)]

async def exec_replace_in_range(arguments: dict) -> list[TextContent]:
    result = to_server("replace_in_range", arguments)
    return [TextContent(type="text", text=result)]

# ========== NAMED RANGES ==========
async def exec_create_named_range(arguments: dict) -> list[TextContent]:
    result = to_server("create_named_range", arguments)
    return [TextContent(type="text", text=result)]

async def exec_get_named_range(arguments: dict) -> list[TextContent]:
    result = to_server("get_named_range", arguments)
    return [TextContent(type="text", text=result)]

async def exec_list_named_ranges(arguments: dict) -> list[TextContent]:
    result = to_server("list_named_ranges", arguments)
    return [TextContent(type="text", text=result)]

# ========== PROTECTION ==========
async def exec_protect_sheet(arguments: dict) -> list[TextContent]:
    result = to_server("protect_sheet", arguments)
    return [TextContent(type="text", text=result)]

async def exec_unprotect_sheet(arguments: dict) -> list[TextContent]:
    result = to_server("unprotect_sheet", arguments)
    return [TextContent(type="text", text=result)]

# ========== UTILITIES ==========
async def exec_get_used_range(arguments: dict) -> list[TextContent]:
    result = to_server("get_used_range", arguments)
    return [TextContent(type="text", text=result)]

async def exec_get_selection(arguments: dict) -> list[TextContent]:
    result = to_server("get_selection", arguments)
    return [TextContent(type="text", text=result)]

async def exec_calculate(arguments: dict) -> list[TextContent]:
    result = to_server("calculate", arguments)
    return [TextContent(type="text", text=result)]

# ========== UTILITY TOOLS ==========
async def exec_get_current_time(arguments: dict) -> list[TextContent]:
    now = datetime.now()
    result = f"Current time: {now}"
    return [TextContent(type="text", text=result)]

async def exec_get_random_number(arguments: dict) -> list[TextContent]:
    interval = arguments.get("interval", [1, 100])
    rand_num = random.randint(interval[0], interval[1])
    return [TextContent(type="text", text=str(rand_num))]

# =========================================================
# DISPATCH TABLE
# =========================================================
TOOL_DISPATCH = {
    # Cell Operations
    "modify_cells": exec_modify_cells,
    "read_cells_text": exec_read_cells_text,
    "read_cells_values": exec_read_cells_values,
    "read_range": exec_read_range,
    "read_subtable": exec_read_subtable,
    "clear_range": exec_clear_range,
    "extend_cell_formula": exec_extend_cell_formula,
    
    # Worksheet Operations
    "get_active_sheet": exec_get_active_sheet,
    "list_sheets": exec_list_sheets,
    "create_sheet": exec_create_sheet,
    "activate_sheet": exec_activate_sheet,
    "delete_sheet": exec_delete_sheet,
    "rename_sheet": exec_rename_sheet,
    
    # Formatting
    "format_cells": exec_format_cells,
    "add_border": exec_add_border,
    "set_number_format": exec_set_number_format,
    
    # Rows & Columns
    "insert_rows": exec_insert_rows,
    "delete_rows": exec_delete_rows,
    "insert_columns": exec_insert_columns,
    "delete_columns": exec_delete_columns,
    "auto_fit_columns": exec_auto_fit_columns,
    "auto_fit_rows": exec_auto_fit_rows,
    
    # Charts
    "create_chart": exec_create_chart,
    "delete_all_charts": exec_delete_all_charts,
    
    # Tables
    "create_table": exec_create_table,
    "list_tables": exec_list_tables,
    "delete_table": exec_delete_table,
    
    # Formulas
    "get_formula": exec_get_formula,
    "set_formula": exec_set_formula,
    
    # Sorting & Filtering
    "sort_range": exec_sort_range,
    
    # Find & Replace
    "find_in_range": exec_find_in_range,
    "replace_in_range": exec_replace_in_range,
    
    # Named Ranges
    "create_named_range": exec_create_named_range,
    "get_named_range": exec_get_named_range,
    "list_named_ranges": exec_list_named_ranges,
    
    # Protection
    "protect_sheet": exec_protect_sheet,
    "unprotect_sheet": exec_unprotect_sheet,
    
    # Utilities
    "get_used_range": exec_get_used_range,
    "get_selection": exec_get_selection,
    "calculate": exec_calculate,
    
    # Utility Tools
    "get_current_time": exec_get_current_time,
    "get_random_number": exec_get_random_number,
    "start_crawl": start_crawl,
    "get_crawl_status": get_crawl_status
}

# =========================================================
# TOOL DEFINITIONS
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
        # ========== CELL OPERATIONS ==========
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
            name="read_cells_text",
            description="Read text content from specific cells.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addresses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of cell addresses, e.g. ['A1', 'B2']"
                    }
                },
                "required": ["addresses"]
            },
        ),
        Tool(
            name="read_cells_values",
            description="Read numeric values from specific cells.",
            inputSchema={
                "type": "object",
                "properties": {
                    "addresses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of cell addresses"
                    }
                },
                "required": ["addresses"]
            },
        ),
        Tool(
            name="read_range",
            description="Read all values from a range as a 2D array.",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "Range address, e.g. 'A1:C10'"}
                },
                "required": ["address"]
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
            name="clear_range",
            description="Clear contents of a range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "Range to clear"}
                },
                "required": ["address"]
            },
        ),
        Tool(
            name="extend_cell_formula",
            description="Auto-fill/drag a cell formula to a target range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source cell"},
                    "target": {"type": "string", "description": "Target cell"}
                },
                "required": ["source", "target"]
            },
        ),
        
        # ========== WORKSHEET OPERATIONS ==========
        Tool(
            name="get_active_sheet",
            description="Get the name of the currently active worksheet.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_sheets",
            description="List all worksheet names in the workbook.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="create_sheet",
            description="Create a new worksheet.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name for the new sheet"}
                },
                "required": ["name"]
            },
        ),
        Tool(
            name="activate_sheet",
            description="Switch to a specific worksheet.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Sheet name to activate"}
                },
                "required": ["name"]
            },
        ),
        Tool(
            name="delete_sheet",
            description="Delete a worksheet.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Sheet name to delete"}
                },
                "required": ["name"]
            },
        ),
        Tool(
            name="rename_sheet",
            description="Rename a worksheet.",
            inputSchema={
                "type": "object",
                "properties": {
                    "oldName": {"type": "string"},
                    "newName": {"type": "string"}
                },
                "required": ["oldName", "newName"]
            },
        ),
        
        # ========== FORMATTING ==========
        Tool(
            name="format_cells",
            description="Apply formatting to cells (colors, fonts, alignment).",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "Range to format"},
                    "format": {
                        "type": "object",
                        "properties": {
                            "backgroundColor": {"type": "string"},
                            "fontColor": {"type": "string"},
                            "fontSize": {"type": "number"},
                            "bold": {"type": "boolean"},
                            "italic": {"type": "boolean"},
                            "horizontalAlignment": {"type": "string", "enum": ["Left", "Center", "Right"]},
                            "verticalAlignment": {"type": "string", "enum": ["Top", "Center", "Bottom"]}
                        }
                    }
                },
                "required": ["address", "format"]
            },
        ),
        Tool(
            name="add_border",
            description="Add borders to cells.",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string"},
                    "style": {"type": "string", "enum": ["Thin", "Medium", "Thick"], "default": "Thin"}
                },
                "required": ["address"]
            },
        ),
        Tool(
            name="set_number_format",
            description="Set number format for cells (e.g., '0.00', '$#,##0.00', '0%').",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string"},
                    "format": {"type": "string", "description": "Number format string"}
                },
                "required": ["address", "format"]
            },
        ),
        
        # ========== ROWS & COLUMNS ==========
        Tool(
            name="insert_rows",
            description="Insert rows at a specific position.",
            inputSchema={
                "type": "object",
                "properties": {
                    "startRow": {"type": "number", "description": "Row number to insert at"},
                    "count": {"type": "number", "description": "Number of rows to insert"}
                },
                "required": ["startRow", "count"]
            },
        ),
        Tool(
            name="delete_rows",
            description="Delete rows starting at a specific position.",
            inputSchema={
                "type": "object",
                "properties": {
                    "startRow": {"type": "number"},
                    "count": {"type": "number"}
                },
                "required": ["startRow", "count"]
            },
        ),
        Tool(
            name="insert_columns",
            description="Insert columns at a specific position.",
            inputSchema={
                "type": "object",
                "properties": {
                    "column": {"type": "string", "description": "Column letter"},
                    "count": {"type": "number"}
                },
                "required": ["column", "count"]
            },
        ),
        Tool(
            name="delete_columns",
            description="Delete columns starting at a specific position.",
            inputSchema={
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                    "count": {"type": "number"}
                },
                "required": ["column", "count"]
            },
        ),
        Tool(
            name="auto_fit_columns",
            description="Auto-fit column widths for a range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string"}
                },
                "required": ["address"]
            },
        ),
        Tool(
            name="auto_fit_rows",
            description="Auto-fit row heights for a range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string"}
                },
                "required": ["address"]
            },
        ),
        
        # ========== CHARTS ==========
        Tool(
            name="create_chart",
            description="Create a chart from data range. Supported types: Line, Column, Bar, Pie, Scatter, Area.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataRange": {"type": "string", "description": "Data range, e.g. 'A1:B10'"},
                    "chartType": {"type": "string", "default": "Column"},
                    "title": {"type": "string", "default": "Chart"},
                    "hasHeaders": {"type": "boolean", "default": True},
                    "position": {"type": "string", "default": "D2"},
                    "width": {"type": "number", "default": 400},
                    "height": {"type": "number", "default": 300}
                },
                "required": ["dataRange"]
            },
        ),
        Tool(
            name="delete_all_charts",
            description="Delete all charts from the active worksheet.",
            inputSchema={"type": "object", "properties": {}},
        ),
        
        # ========== TABLES ==========
        Tool(
            name="create_table",
            description="Create an Excel table from a range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string"},
                    "tableName": {"type": "string"},
                    "hasHeaders": {"type": "boolean", "default": True}
                },
                "required": ["address", "tableName"]
            },
        ),
        Tool(
            name="list_tables",
            description="List all table names in the active worksheet.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="delete_table",
            description="Delete a table by name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tableName": {"type": "string"}
                },
                "required": ["tableName"]
            },
        ),
        
        # ========== FORMULAS ==========
        Tool(
            name="get_formula",
            description="Get the formula from a cell.",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string"}
                },
                "required": ["address"]
            },
        ),
        Tool(
            name="set_formula",
            description="Set a formula in a cell.",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string"},
                    "formula": {"type": "string", "description": "Excel formula, e.g. '=SUM(A1:A10)'"}
                },
                "required": ["address", "formula"]
            },
        ),
        
        # ========== SORTING & FILTERING ==========
        Tool(
            name="sort_range",
            description="Sort a range by a specific column.",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string"},
                    "columnIndex": {"type": "number", "description": "Column index to sort by (0-based)"},
                    "ascending": {"type": "boolean", "default": True}
                },
                "required": ["address", "columnIndex"]
            },
        ),
        
        # ========== FIND & REPLACE ==========
        Tool(
            name="find_in_range",
            description="Find text in a range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string"},
                    "searchText": {"type": "string"}
                },
                "required": ["address", "searchText"]
            },
        ),
        Tool(
            name="replace_in_range",
            description="Replace text in a range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string"},
                    "searchText": {"type": "string"},
                    "replaceText": {"type": "string"}
                },
                "required": ["address", "searchText", "replaceText"]
            },
        ),
        
        # ========== NAMED RANGES ==========
        Tool(
            name="create_named_range",
            description="Create a named range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "address": {"type": "string"}
                },
                "required": ["name", "address"]
            },
        ),
        Tool(
            name="get_named_range",
            description="Read values from a named range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                },
                "required": ["name"]
            },
        ),
        Tool(
            name="list_named_ranges",
            description="List all named ranges in the workbook.",
            inputSchema={"type": "object", "properties": {}},
        ),
        
        # ========== PROTECTION ==========
        Tool(
            name="protect_sheet",
            description="Protect the active worksheet with optional password.",
            inputSchema={
                "type": "object",
                "properties": {
                    "password": {"type": "string"}
                }
            },
        ),
        Tool(
            name="unprotect_sheet",
            description="Unprotect the active worksheet.",
            inputSchema={
                "type": "object",
                "properties": {
                    "password": {"type": "string"}
                }
            },
        ),
        
        # ========== UTILITIES ==========
        Tool(
            name="get_used_range",
            description="Get the address of the used range in the active sheet.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_selection",
            description="Get the currently selected range and its values.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="calculate",
            description="Force recalculation of the entire workbook.",
            inputSchema={"type": "object", "properties": {}},
        ),
        
        # ========== UTILITY TOOLS ==========
        Tool(
            name="get_current_time",
            description="Get current date and time.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_random_number",
            description="Generate a random number in a specified interval.",
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
    print("🚀 Running Complete Excel MCP Server with 42 tools!")
    asyncio.run(main())
# import asyncio
# import requests
# import os
# import random 
# from datetime import datetime
# from mcp.server import Server
# from mcp.server.stdio import stdio_server
# from mcp.types import Tool, TextContent
# from browser_use_client import start_crawl, get_crawl_status
# app = Server("test-mcp-server")
#
# cert_file = os.path.expanduser(os.getenv("CERT_FILE") or "~/.office-addin-dev-certs/localhost.crt")
# key_file  = os.path.expanduser(os.getenv("KEY_FILE") or "~/.office-addin-dev-certs/localhost.key")
# print(cert_file, key_file)
# # Trimite comanda catre Backend-ul principal (port 8000)
# # Backend-ul o va da mai departe la Excel prin WebSocket
# # MCP SERVER: Modifică to_server
# def to_server(key : str, data: dict):
#     url = 'https://localhost:8000/enqueue' 
#     headers = {'Content-type': 'application/json'}
#     payload = {'command': key, 'params' : data}
#
#     try: # Adaugă un try/except AICI
#         response = requests.post(url, json=payload, headers=headers, timeout=30, verify=cert_file)
#         response.raise_for_status() # Aruncă excepție pentru 4xx/5xx HTTP
#
#         json_resp = response.json()
#         print(f"🤖 MCP: Primit raspuns de la Flask: {json_resp}") # Log util!
#
#         if json_resp.get("status") == "ok":
#             return str(json_resp.get("client_response", {}).get("result", "Done"))
#         else:
#             return f"Say this exact thing: Error from client/Flask: {json_resp.get('reason')}"
#
#     except requests.exceptions.RequestException as e:
#         print(f"❌ EROARE CRITICĂ MCP-to-Flask: {e}")
#         # Aici apare eroarea dacă Flask nu e accesibil sau returnează 503/500 rapid
#         return f"Say this exact thing: CRITICAL COMMUNICATION ERROR: {str(e)}"
#
# # =========================================================
# # 1. TOOL EXECUTION FUNCTIONS
# # =========================================================
# async def exec_modify_cells(arguments: dict) -> list[TextContent]:
#     result = to_server("modify_cells", arguments)
#     return [TextContent(type="text", text=result)]
#
# async def exec_read_subtable(arguments: dict) -> list[TextContent]:
#     result = to_server("read_subtable", arguments)
#     return [TextContent(type="text", text=result)]
#
# async def exec_read_cells_text(arguments: dict) -> list[TextContent]:
#     result = to_server("read_cells_text", arguments)
#     return [TextContent(type="text", text=result)]
#
# async def exec_read_cells_values(arguments: dict) -> list[TextContent]:
#     result = to_server("read_cells_values", arguments)
#     return [TextContent(type="text", text=result)]
#
# async def exec_extend_cell_formula(arguments: dict) -> list[TextContent]:
#     result = to_server("extend", arguments) # am corectat cheia in 'extend' sa bata cu App.tsx
#     return [TextContent(type="text", text=result)]
#
# async def exec_get_current_time(arguments: dict) -> list[TextContent]:
#     now = datetime.now()
#     result = f"Current time: {now}"
#     return [TextContent(type="text", text=result)]
#
# async def exec_get_random_number(arguments: dict) -> list[TextContent]:
#     interval = arguments.get("interval", [1, 100])
#     rand_num = random.randint(interval[0], interval[1])
#     return [TextContent(type="text", text=str(rand_num))]
#
#
# # =========================================================
# # 2. DISPATCH TABLE
# # =========================================================
#
# # AICI ERA EROAREA: Am scos 'calculate' care nu exista
# TOOL_DISPATCH = {
#     "get_current_time": exec_get_current_time,
#     "get_random_number": exec_get_random_number,
#     "modify_cells": exec_modify_cells,
#     "read_subtable": exec_read_subtable,
#     "read_cells_text": exec_read_cells_text,
#     "read_cells_values": exec_read_cells_values,
#     "extend_cell_formula": exec_extend_cell_formula,
#     "start_crawl": start_crawl,
#     "get_crawl_status": get_crawl_status
# }
#
# # =========================================================
# # 3. CORE MCP SERVER LOGIC
# # =========================================================
#
# @app.list_tools()
# async def list_tools() -> list[Tool]:
#     return [
#         Tool(name="start_crawl",
#              description="Start a browser-based crawl for a given prompt and company name.",
#              inputSchema={
#                  "type": "object",
#                  "properties": {
#                      "prompt": {"type": "string"},
#                      "company_name": {"type": "string"},
#                  },
#                  "required": ["prompt"]
#              }),
#         Tool(name="get_crawl_status",
#              description="Get the status/result of a previously started crawl by query id.",
#              inputSchema={
#                  "type": "object",
#                  "properties": {
#                      "query_id": {"type": "number"} 
#                  }
#              }),
#         Tool(
#             name="modify_cells",
#             description="Write values or formulas into Excel cells. The argument MUST be a dictionary called 'cells' where keys are cell addresses (e.g., 'A1') and values are the content.",
#             inputSchema={
#                 "type": "object",
#                 "properties": {
#                     "cells": {
#                         "type": "object",
#                         "description": "Dictionary of cell_name:value, e.g. {'A1': 100, 'B2': '=A1+10'}"
#                     }
#                 },
#                 "required": ["cells"]
#             },
#         ),
#         Tool(
#             name="read_subtable",
#             description="Read a range of cells as a matrix of strings.",
#             inputSchema={
#                 "type": "object",
#                 "properties": {
#                     "col1": {"type": "string"},
#                     "col2": {"type": "string"},
#                     "row1": {"type": "number"},
#                     "row2": {"type": "number"}
#                 },
#                 "required": ["col1", "col2", "row1", "row2"]
#             },
#         ),
#         Tool(
#             name="read_cells_values",
#             description="Read specific individual cells.",
#             inputSchema={
#                 "type": "object",
#                 "properties": {
#                     "cells": {"type": "array", "items": {"type": "string"}}
#                 },
#                 "required": ["cells"]
#             },
#         ),
#          Tool(
#             name="extend_cell_formula",
#             description="Drag/Autofill a cell to a target range.",
#             inputSchema={
#                 "type": "object",
#                 "properties": {
#                     "source": {"type": "string"},
#                     "target": {"type": "string"}
#                 },
#                 "required": ["source", "target"]
#             },
#         ),
#         Tool(
#             name="get_current_time",
#             description="Get current time",
#             inputSchema={"type": "object", "properties": {}},
#         ),
#         Tool(
#             name="get_random_number",
#             description="Get random number",
#             inputSchema={
#                 "type": "object",
#                 "properties": {
#                     "interval": {
#                         "type": "array",
#                         "items": {"type": "number"},
#                         "minItems": 2,
#                         "maxItems": 2,
#                         "description": "[min, max]"
#                     }
#                 },
#                 "required": ["interval"]
#             },
#         )
#     ]
#
# @app.call_tool()
# async def call_tool(name: str, arguments: dict) -> list[TextContent]:
#     executor = TOOL_DISPATCH.get(name)
#     if executor:
#         try:
#             return await executor(arguments)
#         except Exception as e:
#             return [TextContent(type="text", text=f"Error: {str(e)}")]
#     return [TextContent(type="text", text=f"Unknown tool: {name}")]
#
# async def main():
#     async with stdio_server() as (read_stream, write_stream):
#         await app.run(read_stream, write_stream, app.create_initialization_options())
#
# if __name__ == "__main__":
#     print("Running MCP!")
#     asyncio.run(main())
