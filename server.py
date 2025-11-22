# BACKEND
# PORT:8000
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sock import Sock 
import json
import requests
import asyncio
import uuid
import threading
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv
app = Flask(__name__)
CORS(app)
sock = Sock(app) # Folosim flask-sock, nu SocketIO!
load_dotenv()
# Configurare API Key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") # PUNE CHEIA TA AICI!!!
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-4o"
cert_file = "/Users/alexandruariton/.office-addin-dev-certs/localhost.crt"
key_file  = "/Users/alexandruariton/.office-addin-dev-certs/localhost.key"

# Globale
AVAILABLE_TOOLS = []
active_ws = None # Tinem minte conexiunea activa cu Excelul
pending_requests = {} # id -> {event: Event, response: val}

# --- 1. TOOL FETCHING (La fel ca inainte) ---
async def fetch_tools_from_mcp():
    try:
        # Nota: Asigura-te ca mcp_test_server.py e in acelasi folder
        server_params = StdioServerParameters(command="python", args=["mcp_test_server.py"], env={})
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                
                tools_openai = []
                for tool in result.tools:
                    tools_openai.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema,
                        }
                    })
                return tools_openai
    except Exception as e:
        print(f"❌ MCP Error: {e}")
        return []

def execute_tool_locally(tool_name, arguments):
    """Executam tool-ul prin MCP (care va chema /enqueue daca e nevoie de Excel)"""
    async def run():
        server_params = StdioServerParameters(command="python", args=["mcp_test_server.py"], env={})
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if result.content:
                    return result.content[0].text
                return "No result"
    print("Incepem!")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        print("Reusim....")
        return loop.run_until_complete(run())
    finally:
        loop.close()

# --- 2. WEBSOCKET ROUTE (Pentru Excel) ---
# Asta inlocuieste ruta veche de socketio
@sock.route('/ws')
def websocket_route(ws):
    global active_ws
    print("🔌 Excel conectat la WebSocket (/ws)!")
    active_ws = ws
    
    try:
        while True:
            data = ws.receive() # Blocant pana vine mesaj de la Excel
            if not data: break
            
            message = json.loads(data)
            print(f"📩 Mesaj de la Excel: {message}")
            
            # Verificam daca e raspunsul la un tool (tool_result)
            if message.get("event") == "tool_result":
                req_id = message.get("request_id")
                payload = message.get("payload")
                
                if req_id in pending_requests:
                    pending_requests[req_id]["response"] = payload
                    pending_requests[req_id]["event"].set() # Deblocam /enqueue
            
            # Verificam daca e chat simplu
            elif message.get("event") == "chat":
                user_text = message["payload"]["text"]
                # Aici declansam logica de LLM
                threading.Thread(target=handle_chat_async, args=(user_text, ws)).start()

    except Exception as e:
        print(f"❌ WS Error: {e}")
    finally:
        print("🔌 Excel deconectat.")
        active_ws = None

# --- 3. BRIDGE ENDPOINT (MCP -> Flask -> Excel) ---
@app.route("/enqueue", methods=["POST"])
def enqueue():
    """Aceasta ruta este apelata de mcp_test_server.py cand vrea sa faca ceva in Excel"""
    if not active_ws:
        return jsonify({"status": "error", "reason": "No Excel connected"}), 503
        
    data = request.json
    command = data.get("command") # ex: modify_cells
    params = data.get("params")
    
    req_id = str(uuid.uuid4())
    ev = threading.Event()
    pending_requests[req_id] = {"event": ev, "response": None}
    
    print(f"⏳ Trimit comanda '{command}' catre Excel (ID: {req_id})...")
    
    # 1. Trimitem comanda catre Excel prin WebSocket
    try:
        msg = {
            "event": "tool_request",
            "payload": {
                "tool_name": command,
                "request_id": req_id,
                "args": params
            }
        }
        active_ws.send(json.dumps(msg))
    except Exception as e:
        return jsonify({"status": "error", "reason": f"WS Send fail: {e}"}), 500
        
    # 2. Asteptam raspunsul (Blocam requestul HTTP pana raspunde WebSocketul)
    ok = ev.wait(timeout=30)
    
    response_data = pending_requests.pop(req_id, None)
    
    if not ok:
        print("❌ Timeout asteptand Excel.")
        return jsonify({"status": "timeout"}), 504
        
    print(f"✅ Primit raspuns de la Excel: {response_data['response']}")
    return jsonify({"status": "ok", "client_response": response_data["response"]})


# --- 4. LLM LOGIC ---
def call_openrouter(messages, tools=None):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"model": MODEL, "messages": messages}
    if tools: payload["tools"] = tools
    
    resp = requests.post(OPENROUTER_API_URL, headers=headers, json=payload)
    if resp.status_code != 200:
        raise Exception(resp.text)
    return resp.json()

def handle_chat_async(user_message, ws):
    """Ruleaza LLM-ul pe un thread separat sa nu blocheze WS"""
    try:
        messages = [
            {"role": "system", "content": "You are a helpful Excel assistant."},
            {"role": "user", "content": user_message}
        ]
        
        # 1. Apel LLM
        response = call_openrouter(messages, AVAILABLE_TOOLS)
        choice = response["choices"][0]["message"]
        
        # 2. Verifica Tool Calls
        if choice.get("tool_calls"):
            # Informam userul
            ws.send(json.dumps({
                "event": "status", 
                "payload": {"text": "Executing Excel commands..."}
            }))
            
            tool_calls = choice["tool_calls"]
            messages.append(choice) # Adaugam intentia AI in istoric
            
            for tc in tool_calls:
                t_name = tc["function"]["name"]
                t_args = json.loads(tc["function"]["arguments"])
                
                print(f"🤖 AI vrea sa execute: {t_name} cu {t_args}")
                # Aici se intampla magia: 
                # execute_tool_locally -> mcp_server -> POST /enqueue -> WS -> Excel -> WS -> /enqueue -> mcp -> done
                res_txt = execute_tool_locally(t_name, t_args)
                
                print(f"🤖 AI a executat: {t_name}")
                print(f"Raspuns: {res_txt}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": res_txt
                })
            
            # 3. Final answer dupa tool execution
            final_resp = call_openrouter(messages)
            final_text = final_resp["choices"][0]["message"]["content"]
            
            ws.send(json.dumps({
                "event": "chat_response",
                "payload": {"reply": final_text}
            }))
            
        else:
            # Raspuns simplu text
            ws.send(json.dumps({
                "event": "chat_response",
                "payload": {"reply": choice["content"]}
            }))
            
    except Exception as e:
        print(f"Eroare Chat: {e}")
        ws.send(json.dumps({
            "event": "chat_response",
            "payload": {"reply": f"Error: {str(e)}"}
        }))

if __name__ == "__main__":
    print("🚀 Server pornit pe port 8000 (HTTP + WebSocket)")
    
    # Incarcare tools la start
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    AVAILABLE_TOOLS = loop.run_until_complete(fetch_tools_from_mcp())
    loop.close()
    
    if not AVAILABLE_TOOLS:
        print("⚠️ Nu am incarcat tools. Verifica mcp_test_server.py")
    else:
        print(f"✅ Incarcat {len(AVAILABLE_TOOLS)} unelte.")

    # PORNIM APP
    app.run(host="0.0.0.0", port=8000, debug=True, ssl_context=(cert_file, key_file))
