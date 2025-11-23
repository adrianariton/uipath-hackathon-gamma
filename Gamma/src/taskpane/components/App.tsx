import * as React from "react";
import { useState, useRef, useEffect } from "react";
import { TextField, DefaultButton, Spinner, SpinnerSize } from "@fluentui/react";
import { ExcelTools } from "../../utils/excelTools";

export interface AppProps {
    isOfficeInitialized?: boolean;
}

interface ChatMessage {
    sender: 'user' | 'bot';
    text: string;
    tools_used?: any[];
}

const App: React.FC<AppProps> = ({ isOfficeInitialized }) => {
    /* --- 1. HOOKS (Trebuie să fie mereu la început) --- */
    const [prompt, setPrompt] = useState("");
    const [messages, setMessages] = useState<ChatMessage[]>([
        { sender: 'bot', text: 'Hello! Ready to control Excel via MCP.' }
    ]);
    const [loading, setLoading] = useState(false);
    const [isConnected, setIsConnected] = useState(false);

    const ws = useRef<WebSocket | null>(null);
    const chatEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll
    const scrollToBottom = () => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };
    useEffect(scrollToBottom, [messages]);

    /* --- 2. WEBSOCKET SETUP (Mutat ÎNAINTE de return) --- */
    useEffect(() => {
        // Ne conectăm la socket chiar dacă Office se încarcă în fundal
        const socket = new WebSocket("wss://localhost:8000/ws");

        socket.onopen = () => {
            console.log("✅ Connected to WebSocket");
            setIsConnected(true);
        };

        socket.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            console.log("Received:", msg);
            handleServerMessage(msg);
        };

        socket.onclose = () => {
            console.log("❌ Disconnected");
            setIsConnected(false);
            setLoading(false);
            setMessages(prev => [...prev, { sender: 'bot', text: "⚠️ Connection lost." }]);
        };

        ws.current = socket;

        return () => {
            socket.close();
        };
    }, []); // Empty dependency array = run once on mount

    /* --- 3. MESSAGE HANDLER --- */
    const handleServerMessage = async (msg: any) => {
        // Dacă Office nu e gata încă, ignorăm sau punem în coadă comenzile de Excel
        // Deși e rar să primești comenzi în prima secundă.
        if (!isOfficeInitialized && msg.event === "tool_request") {
            console.warn("Received tool request before Office was ready.");
            return;
        }

        setLoading(false);

        // A. Chat Response
        if (msg.event === "chat_response") {
            // toolsused e optional, cum fac
            var { reply, tools_used = [] } = msg.payload;
            setMessages(prev => [...prev, { sender: 'bot', text: reply, tools_used: tools_used }]);
        }
        // B. Status updates
        else if (msg.event === "status") {
            setMessages(prev => [...prev, { sender: 'bot', text: `⚙️ ${msg.payload.text}` }]);
        }
        // C. TOOL REQUEST
        else if (msg.event === "tool_request") {
            const { tool_name, request_id, args } = msg.payload;
            let result = null;

            console.log(`🔧 Tool Request: ${tool_name}`, args);

            try {
                switch (tool_name) {
                    case "modify_cells":
                        result = await ExcelTools.modify_cells(args.cells);
                        break;
                    case "read_subtable":
                        result = await ExcelTools.read_subtable(args.col1, args.col2, args.row1, args.row2);
                        break;
                    case "read_cells_text":
                        result = await ExcelTools.read_cells_text(args.cells);
                        break;
                    case "read_cells_values":
                        result = await ExcelTools.read_cells_values(args.cells);
                        break;
                    case "extend":
                        result = await ExcelTools.extend(args.source, args.target);
                        break;
                    case "create_chart":
                        // args is expected to be the options object matching ExcelTools.create_chart
                        result = await ExcelTools.create_chart(args);
                        break;
                    case "delete_all_charts":
                        result = await ExcelTools.delete_all_charts();
                        break;
                    default:
                        console.warn("Unknown tool:", tool_name);
                        result = "Error: Unknown tool name";
                }

                if (ws.current && ws.current.readyState === WebSocket.OPEN) {
                    ws.current.send(JSON.stringify({
                        event: "tool_result",
                        request_id: request_id,
                        payload: { result: result }
                    }));
                    console.log(`✅ Tool ${tool_name} executed. Result sent.`);
                }

            } catch (error: any) {
                console.error(`❌ Tool failed: ${tool_name}`, error);
                if (ws.current && ws.current.readyState === WebSocket.OPEN) {
                    ws.current.send(JSON.stringify({
                        event: "tool_result",
                        request_id: request_id,
                        payload: { result: `Error: ${error.message}` }
                    }));
                }
            }
        }
    };

    /* --- 4. SEND FUNCTION --- */
    const handleSend = () => {
        if (!prompt.trim() || !ws.current) return;

        const userMsg = prompt;
        setMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
        setPrompt("");
        setLoading(true);

        ws.current.send(JSON.stringify({
            event: "chat",
            payload: { text: userMsg }
        }));
    };

    /* --- 5. CONDITIONAL RENDER (LOADING SCREEN) --- */
    // Acum e safe să facem return, după ce toate hook-urile au fost declarate
    if (!isOfficeInitialized) {
        return (
            <div style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "100vh",
                backgroundColor: "#fff"
            }}>
                <Spinner size={SpinnerSize.large} label="Se conectează la Excel..." />
            </div>
        );
    }

    /* --- 6. UI RENDER (MAIN) --- */
    const bubbleStyle = (sender: string) => ({
        alignSelf: sender === 'user' ? 'flex-end' : 'flex-start',
        background: sender === 'user' ? '#702b9a' : '#F3F2F1',
        color: sender === 'user' ? 'white' : 'black',
        padding: '10px',
        borderRadius: '12px',
        maxWidth: '85%',
        marginBottom: '8px',
        fontSize: '13px'
    });

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', padding: '15px', boxSizing: 'border-box', backgroundColor: '#fff' }}>

            {/* HEADER */}
            <div style={{ marginBottom: '10px', borderBottom: '2px solid #702b9a', paddingBottom: '15px', display: 'flex', alignItems: 'center', gap: '15px' }}>
                {/* Asigura-te ca imaginea exista in folderul public/assets */}
                <img
                    src="/assets/gamma-64.png"
                    alt="Gamma Logo"
                    style={{ width: '36px', height: '36px', objectFit: 'contain', border: isConnected ? '2px solid #4CAF50' : '2px solid #ccc', borderRadius: '50%', padding: '2px' }}
                />
                <div>
                    <h2 style={{ margin: 0, fontSize: '24px', color: '#323130', fontWeight: '800' }}>Gamma</h2>
                    <span style={{ fontSize: '10px', color: isConnected ? 'green' : 'red', letterSpacing: '1px' }}>
                        {isConnected ? '● LIVE' : '○ DISCONNECTED'}
                    </span>
                </div>
            </div>

            {/* CHAT */}
            <div
                style={{
                    flex: 1,
                    overflowY: 'auto',
                    display: 'flex',
                    flexDirection: 'column',
                    marginBottom: '15px',
                }}
            >
                {messages.map((msg, idx) => (
                    msg.text.includes("sorry") ? null :
                        <div key={idx} style={bubbleStyle(msg.sender)}>
                            {msg.text}

                            {/* Afișăm tools_used dacă există */}
                            {msg.tools_used && msg.tools_used.length > 0 && msg.tools_used.map((tool, tIdx) => (
                                <div
                                    key={tIdx}
                                    style={{ marginTop: '5px', fontSize: '10px', color: '#555' }}
                                >
                                    {tool.function?.name ?? "null"}
                                </div>
                            ))}
                        </div>
                ))}

                {loading && (
                    <div style={{ alignSelf: 'center', padding: '10px' }}>
                        <Spinner size={SpinnerSize.small} label="Thinking..." />
                    </div>
                )}

                <div ref={chatEndRef} />
            </div>

            {/* INPUT */}
            < div style={{ display: 'flex', gap: '8px', marginBottom: '15px' }}>
                <TextField
                    placeholder="Ask Gamma..."
                    value={prompt}
                    onChange={(_, v) => setPrompt(v || "")}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    disabled={!isConnected}
                    styles={{ root: { flex: 1 } }}
                />
                <DefaultButton text="Send" onClick={handleSend} primary disabled={!isConnected} styles={{ root: { minWidth: '60px', backgroundColor: '#702b9a', borderColor: '#702b9a' } }} />
            </div>
        </div>
    );
};

export default App;
