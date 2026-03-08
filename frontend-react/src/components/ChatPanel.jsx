import { useState, useRef, useCallback, useEffect } from 'react';
import {
    chatWithAssistant,
    generatePlan,
    generatePlanFromUpload,
    generateResponseFromUpload,
    getContractorRecommendations,
    getPlan,
    getPlanDocuments,
    regeneratePlanDocument,
    uploadDocument,
    getUpload,
    parseModel,
    parseInfraModel,
} from '../api.js';
import ContractorCards from './ContractorCards.jsx';
import { parseChatCommand } from '../lib/chatCommands.js';
import { formatParcelContext } from '../lib/parcelState.js';
import useResizable from '../hooks/useResizable.js';

const POLL_INTERVAL_MS = 3000;

function sleep(ms, signal) {
    if (signal?.aborted) {
        throw new DOMException('Request aborted', 'AbortError');
    }

    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
            signal?.removeEventListener('abort', onAbort);
            resolve();
        }, ms);

        function onAbort() {
            clearTimeout(timer);
            reject(new DOMException('Request aborted', 'AbortError'));
        }

        signal?.addEventListener('abort', onAbort, { once: true });
    });
}

function isAbortError(error) {
    return error?.name === 'AbortError';
}

function planStartErrorMessage(error, filename = null) {
    if (error?.status === 401 || error?.status === 403) {
        return filename
            ? `Please sign in before generating a plan from ${filename}.`
            : 'Please sign in before generating a plan.';
    }
    return filename
        ? `Failed to start plan generation from ${filename}: ${error.message}`
        : `Failed to start generation: ${error.message}`;
}

export default function ChatPanel({ parcelContext, onPlanComplete, onToggleExpand, modelParams, onModelUpdate, analyzedUploads, activePlanId, assetType }) {
    const { isResizing: isChatResizing, handleProps: chatResizeProps } = useResizable({
        defaultSize: 280,
        minSize: 150,
        maxSize: 600,
        axis: 'vertical',
        reverse: true,
        cssVar: '--chat-height',
    });

    const [isExpanded, setIsExpanded] = useState(false);
    const [messages, setMessages] = useState([
        {
            role: 'assistant',
            text: "Hello! I'm your development due-diligence assistant. Search for a property above or ask me anything about zoning, policies, or development potential.",
        },
    ]);
    const [inputValue, setInputValue] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const [isDragOver, setIsDragOver] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(null);
    const [latestAnalyzedUpload, setLatestAnalyzedUpload] = useState(null);

    const conversationHistoryRef = useRef([]);
    const messagesEndRef = useRef(null);
    const fileInputRef = useRef(null);
    const planPollControllerRef = useRef(null);
    const uploadPollControllerRef = useRef(null);

    const parcelContextStr = formatParcelContext(parcelContext);

    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping, scrollToBottom]);

    const handleToggle = useCallback(() => {
        setIsExpanded((prev) => {
            const next = !prev;
            onToggleExpand?.(next);
            return next;
        });
    }, [onToggleExpand]);

    const cancelPlanPoll = useCallback(() => {
        planPollControllerRef.current?.abort();
        planPollControllerRef.current = null;
    }, []);

    const cancelUploadPoll = useCallback(() => {
        uploadPollControllerRef.current?.abort();
        uploadPollControllerRef.current = null;
    }, []);

    useEffect(() => () => {
        cancelPlanPoll();
        cancelUploadPoll();
    }, [cancelPlanPoll, cancelUploadPoll]);

    const pollPlan = useCallback(async (planId) => {
        cancelPlanPoll();
        const controller = new AbortController();
        const { signal } = controller;
        planPollControllerRef.current = controller;
        const maxAttempts = 30;

        try {
            for (let i = 0; i < maxAttempts; i++) {
                await sleep(POLL_INTERVAL_MS, signal);
                const plan = await getPlan(planId, { signal });
                if (signal.aborted) return;

                if (plan.status === 'completed' || plan.status === 'done') {
                    const docs = await getPlanDocuments(planId, { signal });
                    if (signal.aborted) return;
                    const docList = docs.length > 0
                        ? docs.map((d) => `- ${d.title || d.document_type}`).join('\n')
                        : 'No documents generated yet.';

                    // Fetch contractor recommendations
                    const lat = parcelContext?.latitude ?? parcelContext?.lat ?? 43.6532;
                    const lng = parcelContext?.longitude ?? parcelContext?.lng ?? -79.3832;
                    const contractorData = await getContractorRecommendations(planId, lat, lng);

                    setMessages((prev) => [...prev, {
                        role: 'assistant',
                        text: `Plan generation complete! Generated documents:\n\n${docList}`,
                        contractors: contractorData.contractors || [],
                    }]);
                    if (onPlanComplete && plan.summary?.massing) {
                        onPlanComplete(plan.summary.massing, planId);
                    }
                    return;
                }
                if (plan.status === 'failed' || plan.status === 'error') {
                    setMessages((prev) => [...prev, {
                        role: 'assistant',
                        text: `Plan generation failed. ${plan.error_message || 'Please try again.'}`,
                    }]);
                    return;
                }
                if (plan.status === 'needs_clarification') {
                    const questions = plan.clarification_questions || [];
                    setMessages((prev) => [...prev, {
                        role: 'assistant',
                        text: `I need some clarification before proceeding:\n\n${questions.map((q, i) => `${i + 1}. ${q}`).join('\n')}`,
                    }]);
                    return;
                }
            }
        } catch (error) {
            if (!isAbortError(error)) {
                console.error('Plan polling error:', error);
            }
            return;
        } finally {
            if (planPollControllerRef.current === controller) {
                planPollControllerRef.current = null;
            }
        }

        if (!signal.aborted) {
            setMessages((prev) => [...prev, {
                role: 'assistant',
                text: 'Plan generation is still in progress. Check back shortly.',
            }]);
        }
    }, [cancelPlanPoll, onPlanComplete]);

    const handleGenerateAction = useCallback(async (action, msgIdx) => {
        // Disable the button on the message that proposed it
        setMessages((prev) => prev.map((m, i) =>
            i === msgIdx ? { ...m, actionFired: true } : m
        ));
        setMessages((prev) => [...prev, {
            role: 'assistant',
            text: `Starting: ${action.label}...`,
        }]);

        const docTypes = action.doc_types;
        const isSmallSubset = Array.isArray(docTypes) && docTypes.length <= 3;

        try {
            // Smart routing: if an active plan exists and we're generating ≤3 docs,
            // regenerate from existing plan data (no pipeline re-run)
            if (activePlanId && isSmallSubset) {
                const results = [];
                for (const dt of docTypes) {
                    const doc = await regeneratePlanDocument(activePlanId, dt, {});
                    results.push(doc);
                }
                const docList = results.map((d) => `- ${d.title || d.doc_type}`).join('\n');
                setMessages((prev) => [...prev, {
                    role: 'assistant',
                    text: `Documents generated from existing plan:\n\n${docList}`,
                }]);
            } else {
                // No existing plan or large batch — run full pipeline
                const result = await generatePlan(action.query, docTypes);
                pollPlan(result.job_id);
            }
        } catch (err) {
            setMessages((prev) => [...prev, {
                role: 'assistant',
                text: planStartErrorMessage(err),
            }]);
        }
    }, [pollPlan, activePlanId]);

    const sendMessage = useCallback(async () => {
        const text = inputValue.trim();
        if (!text) return;

        const nextHistory = [...conversationHistoryRef.current, { role: 'user', text }];
        setInputValue('');
        setMessages((prev) => [...prev, { role: 'user', text }]);
        conversationHistoryRef.current = nextHistory;
        setIsTyping(true);

        // Keep upload-specific commands as direct shortcuts
        const command = parseChatCommand(text);

        if (command.type === 'infra_model' || command.type === 'bridge_model') {
            try {
                const infraAssetType = command.type === 'bridge_model' ? 'bridge' : 'pipeline';
                const params = await parseInfraModel(text, modelParams, infraAssetType);
                onModelUpdate?.(params);
                let infraMsg = command.type === 'bridge_model'
                    ? `Bridge design updated: ${params.span_m || 0}m span, ${params.deck_width_m || 0}m deck width (${(params.structure_type || '').replace(/_/g, ' ')}).`
                    : `Pipeline design updated: ${params.diameter_mm || 0}mm ${params.material || ''} ${params.infra_type || ''} pipe, ${params.length_m || 0}m length.`;
                if (params.warnings?.length) {
                    infraMsg += '\n-- ' + params.warnings.join('\n-- ');
                }
                setMessages((prev) => [...prev, {
                    role: 'assistant',
                    text: infraMsg,
                }]);
            } catch (err) {
                setMessages((prev) => [...prev, {
                    role: 'assistant',
                    text: `Couldn't parse infrastructure description: ${err.message}`,
                }]);
            } finally {
                setIsTyping(false);
            }
            return;
        }

        if (command.type === 'model') {
            try {
                const zoneCode = parcelContext?.zoneCode || parcelContext?.zone_code || parcelContext?.zoning || null;
                const lotAreaM2 = parcelContext?.lotArea ?? parcelContext?.lot_area_m2 ?? null;
                const params = await parseModel(text, modelParams, zoneCode, lotAreaM2);
                onModelUpdate?.(params);
                let modelMsg = `Building updated: ${params.storeys} storeys, ${params.height_m}m tall (${(params.typology || '').replace(/_/g, ' ')}).`;
                if (params.warnings?.length) {
                    modelMsg += '\n-- ' + params.warnings.join('\n-- ');
                }
                setMessages((prev) => [...prev, {
                    role: 'assistant',
                    text: modelMsg,
                }]);
            } catch (err) {
                setMessages((prev) => [...prev, {
                    role: 'assistant',
                    text: `Couldn't parse building description: ${err.message}`,
                }]);
            } finally {
                setIsTyping(false);
            }
            return;
        }

        if (command.type === 'plan_from_upload') {
            if (!latestAnalyzedUpload?.id) {
                setMessages((prev) => [...prev, {
                    role: 'assistant',
                    text: 'There is no analyzed upload ready yet. Upload a document and wait for analysis to finish before generating a plan from it.',
                }]);
                setIsTyping(false);
                return;
            }
            try {
                const result = await generatePlanFromUpload(latestAnalyzedUpload.id);
                setMessages((prev) => [...prev, {
                    role: 'assistant',
                    text: `Plan generation started from ${latestAnalyzedUpload.filename}. I'll let you know when it's ready...`,
                }]);
                setIsTyping(false);
                pollPlan(result.job_id);
                return;
            } catch (err) {
                setMessages((prev) => [...prev, {
                    role: 'assistant',
                    text: planStartErrorMessage(err, latestAnalyzedUpload.filename),
                }]);
                setIsTyping(false);
                return;
            }
        }

        if (command.type === 'response_from_upload') {
            if (!latestAnalyzedUpload?.id) {
                setMessages((prev) => [...prev, {
                    role: 'assistant',
                    text: 'There is no analyzed upload ready yet. Upload a document and wait for analysis to finish before generating a response from it.',
                }]);
                setIsTyping(false);
                return;
            }
            try {
                const result = await generateResponseFromUpload(latestAnalyzedUpload.id);
                const responseLabel = (result.response_type || 'response').replace(/_/g, ' ');
                setMessages((prev) => [...prev, {
                    role: 'assistant',
                    text: `Generated ${responseLabel} from ${latestAnalyzedUpload.filename}:\n\n${result.content}`,
                }]);
            } catch (err) {
                setMessages((prev) => [...prev, {
                    role: 'assistant',
                    text: `Failed to generate a response from ${latestAnalyzedUpload.filename}: ${err.message}`,
                }]);
            } finally {
                setIsTyping(false);
            }
            return;
        }

        // All other messages go to the AI — it decides whether to answer, propose generation, or update the model
        try {
            const zoneCode = parcelContext?.zoneCode || parcelContext?.zone_code || parcelContext?.zoning || null;
            const uploadContext = (analyzedUploads || []).map((u) => ({
                filename: u.filename,
                extracted_data: u.extractedData || null,
            }));
            const { message, proposedAction, modelUpdate, contractors } = await chatWithAssistant({
                messages: nextHistory.slice(-20),
                parcelContext: parcelContextStr,
                modelParams: modelParams || null,
                zoneCode,
                uploadContext: uploadContext.length ? uploadContext : null,
            });

            // If the AI decided to update the 3D model, apply it
            if (modelUpdate) {
                onModelUpdate?.(modelUpdate);
            }

            let displayMsg = message;
            if (modelUpdate?.warnings?.length) {
                displayMsg += '\n⚠ ' + modelUpdate.warnings.join('\n⚠ ');
            }

            const assistantMessage = {
                role: 'assistant',
                text: displayMsg,
                action: proposedAction || null,
                actionFired: false,
                contractors: contractors || [],
            };
            setMessages((prev) => [...prev, assistantMessage]);
            conversationHistoryRef.current = [...nextHistory, { role: 'assistant', text: message }];
        } catch (err) {
            console.error('Assistant chat error:', err);
            setMessages((prev) => [...prev, {
                role: 'assistant',
                text: `Sorry, I couldn't get a response right now. ${err.message}`,
            }]);
        } finally {
            setIsTyping(false);
        }
    }, [inputValue, latestAnalyzedUpload, modelParams, onModelUpdate, parcelContext, parcelContextStr, pollPlan]);

    const pollUpload = useCallback(async (uploadId, filename) => {
        cancelUploadPoll();
        const controller = new AbortController();
        const { signal } = controller;
        uploadPollControllerRef.current = controller;
        const maxAttempts = 40;

        try {
            for (let i = 0; i < maxAttempts; i++) {
                await sleep(POLL_INTERVAL_MS, signal);
                const upload = await getUpload(uploadId, { signal });
                if (signal.aborted) return;

                if (upload.status === 'analyzed') {
                    setUploadProgress(null);
                    const ed = upload.extracted_data || {};

                    // Pipeline DXF path
                    if (ed.pipeline_network) {
                        const net = ed.pipeline_network;
                        const s = net.summary || {};
                        const parts = [
                            `Pipeline DXF analyzed: ${filename}`,
                            `Network: ${s.pipe_count ?? 0} pipe segments · ${s.total_length_m ?? 0}m total length`,
                        ];
                        if (s.manhole_count) parts.push(`Manholes: ${s.manhole_count}`);
                        if (s.valve_count)   parts.push(`Valves: ${s.valve_count}`);
                        if (s.hydrant_count) parts.push(`Hydrants: ${s.hydrant_count}`);
                        parts.push('\nThe 3D pipeline viewer has opened. Click any pipe or manhole to edit its properties.');
                        setMessages((prev) => [...prev, { role: 'assistant', text: parts.join('\n') }]);
                        setLatestAnalyzedUpload({ id: uploadId, filename });
                        return;
                    }

                    // Standard document path
                    const parts = [`Document analyzed: ${filename}`];
                    if (upload.doc_category) parts.push(`Category: ${upload.doc_category.replace(/_/g, ' ')}`);
                    if (upload.page_count) parts.push(`Pages: ${upload.page_count}`);
                    if (ed && !ed.error && !ed.note) {
                        const b = ed.building || {};
                        const items = [];
                        if (b.storeys) items.push(`${b.storeys} storeys`);
                        if (b.unit_count) items.push(`${b.unit_count} units`);
                        if (b.height_m) items.push(`${b.height_m}m height`);
                        if (items.length) parts.push(`Extracted: ${items.join(', ')}`);
                    }
                    if (upload.compliance_findings?.issues?.length) {
                        parts.push(`Compliance issues found: ${upload.compliance_findings.issues.length}`);
                    }
                    parts.push(`\nSay "generate plan from upload" or "generate response from upload" to proceed.`);
                    setMessages((prev) => [...prev, { role: 'assistant', text: parts.join('\n') }]);
                    setLatestAnalyzedUpload({ id: uploadId, filename });
                    return;
                }
                if (upload.status === 'failed') {
                    setUploadProgress(null);
                    setMessages((prev) => [...prev, {
                        role: 'assistant',
                        text: `Document analysis failed for ${filename}. ${upload.error_message || 'Please try again.'}`,
                    }]);
                    return;
                }
                setUploadProgress({ filename, status: upload.status });
            }
        } catch (error) {
            if (!isAbortError(error)) {
                console.error('Upload polling error:', error);
            }
            return;
        } finally {
            if (uploadPollControllerRef.current === controller) {
                uploadPollControllerRef.current = null;
            }
        }

        if (!signal.aborted) {
            setUploadProgress(null);
            setMessages((prev) => [...prev, {
                role: 'assistant',
                text: `Document analysis is still in progress for ${filename}. Check back shortly.`,
            }]);
        }
    }, [cancelUploadPoll]);

    const handleFileUpload = useCallback(async (file) => {
        if (!file) return;
        const maxSize = 50 * 1024 * 1024;
        if (file.size > maxSize) {
            setMessages((prev) => [...prev, { role: 'assistant', text: 'File exceeds 50 MB limit.' }]);
            return;
        }
        setMessages((prev) => [...prev, { role: 'user', text: `Uploading: ${file.name}` }]);
        setUploadProgress({ filename: file.name, status: 'uploading' });
        try {
            const result = await uploadDocument(file);
            setUploadProgress({ filename: file.name, status: 'processing' });
            setMessages((prev) => [...prev, {
                role: 'assistant',
                text: `Uploaded ${file.name} — analyzing document...`,
            }]);
            pollUpload(result.id, file.name);
        } catch (err) {
            setUploadProgress(null);
            setMessages((prev) => [...prev, {
                role: 'assistant',
                text: `Upload failed: ${err.message}`,
            }]);
        }
    }, [pollUpload]);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        setIsDragOver(false);
        const file = e.dataTransfer?.files?.[0];
        if (file) handleFileUpload(file);
    }, [handleFileUpload]);

    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        setIsDragOver(true);
    }, []);

    const handleDragLeave = useCallback(() => {
        setIsDragOver(false);
    }, []);

    const handleKeyDown = useCallback((e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    }, [sendMessage]);

    return (
        <div id="chat-panel" className={isExpanded ? 'expanded' : ''} style={{ userSelect: isChatResizing ? 'none' : undefined }}>
            {isExpanded && <div {...chatResizeProps} style={{ ...chatResizeProps.style, top: -2 }} />}
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
                                {msg.contractors?.length > 0 && (
                                    <ContractorCards contractors={msg.contractors} />
                                )}
                                {msg.role === 'assistant' && msg.action && !msg.actionFired && (
                                    <button
                                        className="generate-action-btn"
                                        onClick={() => handleGenerateAction(msg.action, idx)}
                                    >
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="13" height="13">
                                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                                            <polyline points="14 2 14 8 20 8"/>
                                            <line x1="12" y1="18" x2="12" y2="12"/>
                                            <line x1="9" y1="15" x2="15" y2="15"/>
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
                                <div className="typing-indicator">
                                    <span></span><span></span><span></span>
                                </div>
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
                    <button className="chat-upload-btn" aria-label="Upload file" title="Upload a document for AI analysis"
                        onClick={() => fileInputRef.current?.click()}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
                            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                        </svg>
                    </button>
                    <input
                        type="text"
                        id="chat-input"
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
