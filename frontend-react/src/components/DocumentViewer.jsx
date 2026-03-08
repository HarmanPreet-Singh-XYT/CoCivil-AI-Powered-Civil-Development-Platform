import { useCallback } from 'react';
import ReactMarkdown from 'react-markdown';

const SAFETY_PREFIX = 'DRAFT — FOR PROFESSIONAL REVIEW ONLY';

export default function DocumentViewer({ document, planId, onRegenerate, onStatusChange }) {
    if (!document) {
        return (
            <div className="doc-viewer-empty">
                <p>Select a document to view</p>
            </div>
        );
    }

    const content = document.content_text || '';
    const hasSafetyPreamble = content.includes(SAFETY_PREFIX);

    const handleDownload = useCallback(async (format) => {
        try {
            const { downloadPlanDocument } = await import('../api.js');
            const res = await downloadPlanDocument(planId, document.id, format);
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = window.document.createElement('a');
            a.href = url;
            const ext = format === 'markdown' ? 'md' : format;
            a.download = `${document.doc_type}.${ext}`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Download failed:', err);
        }
    }, [planId, document]);

    return (
        <div className="doc-viewer">
            <div className="doc-viewer-header">
                <h3>{document.title}</h3>
                <div className="doc-viewer-actions">
                    <button
                        className="doc-action-btn"
                        onClick={() => onRegenerate?.(document.doc_type)}
                        title="Regenerate this document"
                    >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
                            <polyline points="23 4 23 10 17 10" />
                            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                        </svg>
                        Regenerate
                    </button>
                    <select
                        className="doc-download-select"
                        defaultValue=""
                        onChange={(e) => { if (e.target.value) { handleDownload(e.target.value); e.target.value = ''; } }}
                    >
                        <option value="" disabled>Download</option>
                        <option value="markdown">Markdown (.md)</option>
                        <option value="html">HTML</option>
                        <option value="docx">Word (.docx)</option>
                    </select>
                </div>
            </div>

            {hasSafetyPreamble && (
                <div className="doc-safety-banner">
                    {SAFETY_PREFIX}. This document must be reviewed by a qualified Ontario Land Use Planner (RPP) before submission.
                </div>
            )}

            <div className="doc-viewer-content">
                <ReactMarkdown>{content}</ReactMarkdown>
            </div>

            <div className="doc-viewer-status">
                <span className={`doc-status-badge ${document.review_status}`}>
                    {document.review_status}
                </span>
                {document.review_status === 'draft' && (
                    <button className="doc-review-btn" onClick={() => onStatusChange?.(document.id, 'submit')}>
                        Submit for Review
                    </button>
                )}
                {document.review_status === 'under_review' && (
                    <>
                        <button className="doc-review-btn approve" onClick={() => onStatusChange?.(document.id, 'approve')}>
                            Approve
                        </button>
                        <button className="doc-review-btn reject" onClick={() => onStatusChange?.(document.id, 'reject')}>
                            Reject
                        </button>
                    </>
                )}
            </div>
        </div>
    );
}
