import { useState, useRef, useCallback, useEffect } from 'react';

const GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent';

const SYSTEM_PROMPT = `You are an expert land-development due-diligence assistant for the City of Toronto. You help development analysts, planners, and architects understand zoning regulations, building policies, setback requirements, height limits, floor space index (FSI), permitted uses, and development potential.

Your knowledge covers:
- Toronto Zoning Bylaw 569-2013
- Ontario Building Code
- Toronto Official Plan policies
- Development application processes
- Entitlements and variance procedures
- Building envelope constraints (setbacks, angular planes, stepbacks)
- Unit mix and density requirements
- Parking and loading requirements

When answering:
- Be precise and cite bylaw sections when possible
- Provide specific numeric values (heights in metres, setbacks in metres, FSI ratios)
- Distinguish between as-of-right permissions and what requires a variance
- Note when information may have changed due to amendments
- Keep responses concise but thorough

If a parcel address is provided in the conversation context, tailor your answers to that specific location and its zoning.`;

function formatMessageHtml(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.06);padding:1px 4px;border-radius:3px;font-size:0.85em;">$1</code>')
        .replace(/\n/g, '<br>');
}

export default function ChatPanel({ parcelContext }) {
    const [isExpanded, setIsExpanded] = useState(false);
    const [messages, setMessages] = useState([
        {
            role: 'assistant',
            text: "Hello! I'm your development due-diligence assistant. Search for a property above or ask me anything about zoning, policies, or development potential.",
        },
    ]);
    const [inputValue, setInputValue] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const [apiKey, setApiKey] = useState(() => localStorage.getItem('gemini_api_key') || '');

    const conversationHistoryRef = useRef([]);
    const messagesEndRef = useRef(null);
    const hasPromptedRef = useRef(false);

    // Build parcel context string
    const parcelContextStr = parcelContext
        ? `Current parcel: ${parcelContext.address}, Zoning: ${parcelContext.zoning}, Lot Area: ${parcelContext.lotArea}m²`
        : '';

    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping, scrollToBottom]);

    const promptForApiKey = useCallback(() => {
        if (hasPromptedRef.current) return;
        hasPromptedRef.current = true;
        const key = prompt('Enter your Gemini API key for AI responses.\nGet one free at: https://aistudio.google.com/apikey');
        if (key && key.trim()) {
            const trimmed = key.trim();
            setApiKey(trimmed);
            localStorage.setItem('gemini_api_key', trimmed);
            setMessages((prev) => [
                ...prev,
                { role: 'assistant', text: "API key saved! I'm ready to answer your questions about zoning, development potential, and land-use policies." },
            ]);
        }
    }, []);

    const handleToggle = useCallback(() => {
        setIsExpanded((prev) => {
            const next = !prev;
            if (next && !apiKey && !hasPromptedRef.current) {
                setTimeout(() => promptForApiKey(), 300);
            }
            return next;
        });
    }, [apiKey, promptForApiKey]);

    const callGemini = useCallback(async (userMessage) => {
        const contextMessage = parcelContextStr
            ? `[Context: ${parcelContextStr}]\n\n${userMessage}`
            : userMessage;

        const history = conversationHistoryRef.current.slice(-10).map((msg) => ({
            role: msg.role,
            parts: msg.parts,
        }));

        // Override last user message with context
        if (history.length > 0) {
            history[history.length - 1] = {
                role: 'user',
                parts: [{ text: contextMessage }],
            };
        }

        const body = {
            system_instruction: {
                parts: [{ text: SYSTEM_PROMPT }],
            },
            contents: history,
            generationConfig: {
                temperature: 0.7,
                maxOutputTokens: 1024,
                topP: 0.9,
            },
        };

        const res = await fetch(`${GEMINI_API_URL}?key=${apiKey}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.error?.message || `API returned ${res.status}`);
        }

        const data = await res.json();
        return data.candidates?.[0]?.content?.parts?.[0]?.text || 'No response generated.';
    }, [apiKey, parcelContextStr]);

    const sendMessage = useCallback(async () => {
        const text = inputValue.trim();
        if (!text) return;

        setInputValue('');
        setMessages((prev) => [...prev, { role: 'user', text }]);
        conversationHistoryRef.current.push({ role: 'user', parts: [{ text }] });

        if (!apiKey) {
            setMessages((prev) => [
                ...prev,
                { role: 'assistant', text: 'Please provide a Gemini API key to enable AI responses. Click the chat header to set it up.' },
            ]);
            promptForApiKey();
            return;
        }

        setIsTyping(true);

        try {
            const response = await callGemini(text);
            setIsTyping(false);
            setMessages((prev) => [...prev, { role: 'assistant', text: response }]);
            conversationHistoryRef.current.push({ role: 'model', parts: [{ text: response }] });
        } catch (err) {
            setIsTyping(false);
            console.error('Gemini API error:', err);
            setMessages((prev) => [
                ...prev,
                { role: 'assistant', text: `I encountered an error: ${err.message}. Please check your API key and try again.` },
            ]);
        }
    }, [inputValue, apiKey, callGemini, promptForApiKey]);

    const handleKeyDown = useCallback((e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    }, [sendMessage]);

    return (
        <div id="chat-panel" className={isExpanded ? 'expanded' : ''}>
            <div id="chat-toggle" role="button" tabIndex="0" aria-label="Toggle chat" onClick={handleToggle}>
                <div id="chat-toggle-left">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    </svg>
                    <span>Ask the AI Agent</span>
                </div>
                <svg id="chat-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="18 15 12 9 6 15" />
                </svg>
            </div>
            <div id="chat-body">
                <div id="chat-messages">
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`chat-message ${msg.role}`}>
                            <div className="message-avatar">{msg.role === 'assistant' ? 'AI' : 'You'}</div>
                            <div
                                className="message-content"
                                dangerouslySetInnerHTML={{ __html: `<p>${formatMessageHtml(msg.text)}</p>` }}
                            />
                        </div>
                    ))}
                    {isTyping && (
                        <div className="chat-message assistant">
                            <div className="message-avatar">AI</div>
                            <div className="message-content">
                                <div className="typing-indicator">
                                    <span></span><span></span><span></span>
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
                <div id="chat-input-container">
                    <input
                        type="text"
                        id="chat-input"
                        placeholder="Ask about zoning, setbacks, height limits, development potential..."
                        autoComplete="off"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                    />
                    <button id="chat-send" aria-label="Send message" onClick={sendMessage}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <line x1="22" y1="2" x2="11" y2="13" />
                            <polygon points="22 2 15 22 11 13 2 9 22 2" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}
