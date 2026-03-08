import { useState, useRef, useCallback, useEffect } from 'react';
import {
    chatWithAssistant, generatePlan, generatePlanFromUpload,
    generateResponseFromUpload, getPlan, getPlanDocuments,
    uploadDocument, getUpload, parseModel,
} from '../api.js';
import { parseChatCommand } from '../lib/chatCommands.js';
import { formatParcelContext } from '../lib/parcelState.js';

const DEFAULT_CHAT_HEIGHT = 280;
const MIN_CHAT_HEIGHT = 160;
const MAX_CHAT_HEIGHT = 600;

export default function ChatPanel({ parcelContext, onPlanComplete, onToggleExpand, modelParams, onModelUpdate }) {
    const [isExpanded, setIsExpanded] = useState(false);
    const [chatHeight, setChatHeight] = useState(DEFAULT_CHAT_HEIGHT);
    const [isResizing, setIsResizing] = useState(false);
    const [messages, setMessages] = useState([
        { role: 'assistant', text: "Hello! I'm your development due-diligence assistant. Search for a property above or ask me anything about zoning, policies, or development potential." },
    ]);
    const [inputValue, setInputValue] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const [confirmReset, setConfirmReset] = useState(false);
    const [isDragOver, setIsDragOver] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(null);
    const [latestAnalyzedUpload, setLatestAnalyzedUpload] = useState(null);

    const conversationHistoryRef = useRef([]);
    const messagesEndRef = useRef(null);
    const fileInputRef = useRef(null);
    const startYRef = useRef(null);
    const startHeightRef = useRef(null);

    const parcelContextStr = formatParcelContext(parcelContext);

    // ── Keep CSS variable in sync so #chat-body height: var(--chat-height) works ──
    useEffect(() => {
        document.documentElement.style.setProperty('--chat-height', `${chatHeight}px`);
    }, [chatHeight]);

    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    useEffect(() => { scrollToBottom(); }, [messages, isTyping, scrollToBottom]);

    // ── Kill transitions during drag ──────────────────────────────────────────
    useEffect(() => {
        const style = document.createElement('style');
        style.id = 'no-layout-transition';
        if (isResizing) {
            style.textContent = `#sidebar, #search-container, #chat-panel, #policy-panel, .panel-reopen-tab { transition: none !important; }`;
            document.head.appendChild(style);
        }
        return () => { document.getElementById('no-layout-transition')?.remove(); };
    }, [isResizing]);

    // ── Drag-to-resize from top edge ──────────────────────────────────────────
    const handleResizeStart = useCallback((e) => {
        if (!isExpanded) return;
        e.preventDefault();
        setIsResizing(true);
        startYRef.current = e.clientY;
        startHeightRef.current = chatHeight;
    }, [isExpanded, chatHeight]);

    useEffect(() => {
        if (!isResizing) return;
        const onMove = (e) => {
            const delta = startYRef.current - e.clientY; // drag up = taller
            const newHeight = Math.min(MAX_CHAT_HEIGHT, Math.max(MIN_CHAT_HEIGHT, startHeightRef.current + delta));
            setChatHeight(newHeight);
        };
        const onUp = () => setIsResizing(false);
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        return () => {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        };
    }, [isResizing]);

    // ── Toggle ────────────────────────────────────────────────────────────────
    const handleToggle = useCallback(() => {
        setIsExpanded((prev) => {
            const next = !prev;
            onToggleExpand?.(next);
            return next;
        });
    }, [onToggleExpand]);

    // ── Reset chat ────────────────────────────────────────────────────────────
    const INITIAL_MESSAGE = { role: 'assistant', text: "Hello! I'm your development due-diligence assistant. Search for a property above or ask me anything about zoning, policies, or development potential." };
    const handleResetClick = useCallback((e) => {
        e.stopPropagation();
        setConfirmReset(true);
    }, []);
    const handleResetConfirm = useCallback((e) => {
        e.stopPropagation();
        setMessages([INITIAL_MESSAGE]);
        conversationHistoryRef.current = [];
        setLatestAnalyzedUpload(null);
        setUploadProgress(null);
        setInputValue('');
        setIsTyping(false);
        setConfirmReset(false);
    }, []);
    const handleResetCancel = useCallback((e) => {
        e.stopPropagation();
        setConfirmReset(false);
    }, []);

    // ── Plan polling ──────────────────────────────────────────────────────────
    const pollPlan = useCallback(async (planId) => {
        const maxAttempts = 30;
        for (let i = 0; i < maxAttempts; i++) {
            await new Promise((r) => setTimeout(r, 3000));
            try {
                const plan = await getPlan(planId);
                if (plan.status === 'completed' || plan.status === 'done') {
                    const docs = await getPlanDocuments(planId);
                    const docList = docs.length > 0 ? docs.map((d) => `- ${d.title || d.document_type}`).join('\n') : 'No documents generated yet.';
                    setMessages((prev) => [...prev, { role: 'assistant', text: `Plan generation complete! Generated documents:\n\n${docList}` }]);
                    if (onPlanComplete && plan.summary?.massing) onPlanComplete(plan.summary.massing);
                    return;
                }
                if (plan.status === 'failed' || plan.status === 'error') {
                    setMessages((prev) => [...prev, { role: 'assistant', text: `Plan generation failed. ${plan.error_message || 'Please try again.'}` }]);
                    return;
                }
                if (plan.status === 'needs_clarification') {
                    const questions = plan.clarification_questions || [];
                    setMessages((prev) => [...prev, { role: 'assistant', text: `I need some clarification:\n\n${questions.map((q, i) => `${i + 1}. ${q}`).join('\n')}` }]);
                    return;
                }
            } catch { /* keep polling */ }
        }
        setMessages((prev) => [...prev, { role: 'assistant', text: 'Plan generation is still in progress. Check back shortly.' }]);
    }, [onPlanComplete]);

    const handleGenerateAction = useCallback(async (action, msgIdx) => {
        setMessages((prev) => prev.map((m, i) => i === msgIdx ? { ...m, actionFired: true } : m));
        setMessages((prev) => [...prev, { role: 'assistant', text: `Starting: ${action.label}...` }]);
        try {
            const result = await generatePlan(action.query);
            pollPlan(result.job_id);
        } catch (err) {
            setMessages((prev) => [...prev, { role: 'assistant', text: `Failed to start generation: ${err.message}` }]);
        }
    }, [pollPlan]);

    // ── Send message ──────────────────────────────────────────────────────────
    const sendMessage = useCallback(async () => {
        const text = inputValue.trim();
        if (!text) return;
        const nextHistory = [...conversationHistoryRef.current, { role: 'user', text }];
        setInputValue('');
        setMessages((prev) => [...prev, { role: 'user', text }]);
        conversationHistoryRef.current = nextHistory;
        setIsTyping(true);

        const command = parseChatCommand(text);

        if (command.type === 'model') {
            try {
                const params = await parseModel(text, modelParams);
                onModelUpdate?.(params);
                setMessages((prev) => [...prev, { role: 'assistant', text: `Building updated: ${params.storeys} storeys, ${params.height_m}m tall (${(params.typology || '').replace(/_/g, ' ')}).` }]);
            } catch (err) {
                setMessages((prev) => [...prev, { role: 'assistant', text: `Couldn't parse building description: ${err.message}` }]);
            } finally { setIsTyping(false); }
            return;
        }

        if (command.type === 'plan_from_upload') {
            if (!latestAnalyzedUpload?.id) {
                setMessages((prev) => [...prev, { role: 'assistant', text: 'There is no analyzed upload ready yet.' }]);
                setIsTyping(false); return;
            }
            try {
                const result = await generatePlanFromUpload(latestAnalyzedUpload.id);
                setMessages((prev) => [...prev, { role: 'assistant', text: `Plan generation started from ${latestAnalyzedUpload.filename}. I'll let you know when it's ready...` }]);
                setIsTyping(false);
                pollPlan(result.job_id); return;
            } catch (err) {
                setMessages((prev) => [...prev, { role: 'assistant', text: `Failed to start plan generation: ${err.message}` }]);
                setIsTyping(false); return;
            }
        }

        if (command.type === 'response_from_upload') {
            if (!latestAnalyzedUpload?.id) {
                setMessages((prev) => [...prev, { role: 'assistant', text: 'There is no analyzed upload ready yet.' }]);
                setIsTyping(false); return;
            }
            try {
                const result = await generateResponseFromUpload(latestAnalyzedUpload.id);
                const label = (result.response_type || 'response').replace(/_/g, ' ');
                setMessages((prev) => [...prev, { role: 'assistant', text: `Generated ${label} from ${latestAnalyzedUpload.filename}:\n\n${result.content}` }]);
            } catch (err) {
                setMessages((prev) => [...prev, { role: 'assistant', text: `Failed: ${err.message}` }]);
            } finally { setIsTyping(false); }
            return;
        }

        try {
            const { message, proposedAction } = await chatWithAssistant({ messages: nextHistory.slice(-20), parcelContext: parcelContextStr });
            setMessages((prev) => [...prev, { role: 'assistant', text: message, action: proposedAction || null, actionFired: false }]);
            conversationHistoryRef.current = [...nextHistory, { role: 'assistant', text: message }];
        } catch (err) {
            setMessages((prev) => [...prev, { role: 'assistant', text: `Sorry, I couldn't get a response right now. ${err.message}` }]);
        } finally { setIsTyping(false); }
    }, [inputValue, latestAnalyzedUpload, parcelContextStr, pollPlan]);

    // ── Upload ────────────────────────────────────────────────────────────────
    const pollUpload = useCallback(async (uploadId, filename) => {
        for (let i = 0; i < 40; i++) {
            await new Promise((r) => setTimeout(r, 3000));
            try {
                const upload = await getUpload(uploadId);
                if (upload.status === 'analyzed') {
                    setUploadProgress(null);
                    const parts = [`Document analyzed: ${filename}`];
                    if (upload.doc_category) parts.push(`Category: ${upload.doc_category.replace(/_/g, ' ')}`);
                    if (upload.page_count) parts.push(`Pages: ${upload.page_count}`);
                    parts.push(`\nSay "generate plan from upload" or "generate response from upload" to proceed.`);
                    setMessages((prev) => [...prev, { role: 'assistant', text: parts.join('\n') }]);
                    setLatestAnalyzedUpload({ id: uploadId, filename });
                    return;
                }
                if (upload.status === 'failed') {
                    setUploadProgress(null);
                    setMessages((prev) => [...prev, { role: 'assistant', text: `Document analysis failed for ${filename}.` }]);
                    return;
                }
                setUploadProgress({ filename, status: upload.status });
            } catch { /* keep polling */ }
        }
        setUploadProgress(null);
        setMessages((prev) => [...prev, { role: 'assistant', text: `Document analysis still in progress for ${filename}.` }]);
    }, []);

    const handleFileUpload = useCallback(async (file) => {
        if (!file) return;
        if (file.size > 50 * 1024 * 1024) { setMessages((prev) => [...prev, { role: 'assistant', text: 'File exceeds 50 MB limit.' }]); return; }
        setMessages((prev) => [...prev, { role: 'user', text: `Uploading: ${file.name}` }]);
        setUploadProgress({ filename: file.name, status: 'uploading' });
        try {
            const result = await uploadDocument(file);
            setUploadProgress({ filename: file.name, status: 'processing' });
            setMessages((prev) => [...prev, { role: 'assistant', text: `Uploaded ${file.name} — analyzing document...` }]);
            pollUpload(result.id, file.name);
        } catch (err) {
            setUploadProgress(null);
            setMessages((prev) => [...prev, { role: 'assistant', text: `Upload failed: ${err.message}` }]);
        }
    }, [pollUpload]);

    const handleDrop = useCallback((e) => { e.preventDefault(); setIsDragOver(false); const f = e.dataTransfer?.files?.[0]; if (f) handleFileUpload(f); }, [handleFileUpload]);
    const handleDragOver = useCallback((e) => { e.preventDefault(); setIsDragOver(true); }, []);
    const handleDragLeave = useCallback(() => setIsDragOver(false), []);
    const handleKeyDown = useCallback((e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }, [sendMessage]);

    return (
        <div
            id="chat-panel"
            className={isExpanded ? 'expanded' : ''}
            style={{ userSelect: isResizing ? 'none' : undefined }}
        >
            {/* Top drag handle — sits on the border, not over the toggle content */}
            {isExpanded && (
                <div
                    onMouseDown={handleResizeStart}
                    style={{
                        position: 'absolute',
                        top: -3,
                        left: 0,
                        right: 0,
                        height: 6,
                        cursor: 'row-resize',
                        zIndex: 25,
                        background: isResizing ? 'rgba(200,165,92,0.3)' : 'transparent',
                        transition: 'background 0.15s',
                    }}
                />
            )}

            <div id="chat-toggle" role="button" tabIndex="0" aria-label="Toggle chat" onClick={handleToggle}>
                <div id="chat-toggle-left">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    </svg>
                    <span>Ask the AI Agent</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    {isExpanded && messages.length > 1 && (
                        confirmReset ? (
                            <div
                                onClick={e => e.stopPropagation()}
                                style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.72rem' }}
                            >
                                <span style={{ color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>Clear chat?</span>
                                <button
                                    onClick={handleResetConfirm}
                                    style={{
                                        padding: '2px 8px', borderRadius: 4, fontSize: '0.72rem', fontWeight: 600,
                                        background: 'rgba(248,113,113,0.12)', color: 'var(--error)',
                                        border: '1px solid rgba(248,113,113,0.25)', cursor: 'pointer',
                                    }}
                                >Yes</button>
                                <button
                                    onClick={handleResetCancel}
                                    style={{
                                        padding: '2px 8px', borderRadius: 4, fontSize: '0.72rem', fontWeight: 600,
                                        background: 'rgba(255,255,255,0.05)', color: 'var(--text-secondary)',
                                        border: '1px solid var(--border)', cursor: 'pointer',
                                    }}
                                >No</button>
                            </div>
                        ) : (
                            <button
                                onClick={handleResetClick}
                                title="Reset conversation"
                                style={{
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    width: 26, height: 26, borderRadius: 6,
                                    color: 'var(--text-muted)', transition: 'color 0.15s, background 0.15s',
                                    background: 'transparent',
                                }}
                                onMouseEnter={e => { e.currentTarget.style.color = 'var(--error)'; e.currentTarget.style.background = 'rgba(248,113,113,0.08)'; }}
                                onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.background = 'transparent'; }}
                            >
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
                                    <polyline points="1 4 1 10 7 10" />
                                    <path d="M3.51 15a9 9 0 1 0 .49-4.95" />
                                </svg>
                            </button>
                        )
                    )}
                    <svg id="chat-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="18 15 12 9 6 15" />
                    </svg>
                </div>
            </div>

            <div id="chat-body" onDrop={handleDrop} onDragOver={handleDragOver} onDragLeave={handleDragLeave}>
                {isDragOver && (
                    <div className="chat-drop-overlay">
                        <div className="chat-drop-content">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="32" height="32">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                <polyline points="17 8 12 3 7 8" />
                                <line x1="12" y1="3" x2="12" y2="15" />
                            </svg>
                            <span>Drop file to upload</span>
                        </div>
                    </div>
                )}
                <div id="chat-messages">
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`chat-message ${msg.role}`}>
                            <div className="message-avatar">{msg.role === 'assistant' ? 'AI' : 'You'}</div>
                            <div className="message-content">
                                <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{msg.text}</p>
                                {msg.role === 'assistant' && msg.action && !msg.actionFired && (
                                    <button className="generate-action-btn" onClick={() => handleGenerateAction(msg.action, idx)}>
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="13" height="13">
                                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                            <polyline points="14 2 14 8 20 8" />
                                            <line x1="12" y1="18" x2="12" y2="12" />
                                            <line x1="9" y1="15" x2="15" y2="15" />
                                        </svg>
                                        {msg.action.label}
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                    {uploadProgress && (
                        <div className="chat-message assistant">
                            <div className="message-avatar">AI</div>
                            <div className="message-content">
                                <div className="upload-status">
                                    <div className="upload-spinner"></div>
                                    <span>{uploadProgress.status === 'uploading' ? 'Uploading' : 'Analyzing'} {uploadProgress.filename}...</span>
                                </div>
                            </div>
                        </div>
                    )}
                    {isTyping && (
                        <div className="chat-message assistant">
                            <div className="message-avatar">AI</div>
                            <div className="message-content">
                                <div className="typing-indicator"><span></span><span></span><span></span></div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
                <div id="chat-input-container">
                    <input type="file" ref={fileInputRef} style={{ display: 'none' }}
                        accept=".pdf,.png,.jpg,.jpeg,.xlsx,.xls,.csv"
                        onChange={(e) => { handleFileUpload(e.target.files?.[0]); e.target.value = ''; }}
                    />
                    <button className="chat-upload-btn" aria-label="Upload file" title="Upload a document for AI analysis" onClick={() => fileInputRef.current?.click()}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
                            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                        </svg>
                    </button>
                    <input type="text" id="chat-input"
                        placeholder="Ask about zoning, setbacks, variance requirements..."
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