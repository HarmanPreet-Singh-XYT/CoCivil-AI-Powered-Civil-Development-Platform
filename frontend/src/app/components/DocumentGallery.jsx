import { useState, useCallback } from 'react';
import DocumentViewer from './DocumentViewer.jsx';

const DOC_GROUPS = [
    {
        label: 'Core Submission',
        types: ['cover_letter', 'planning_rationale', 'compliance_matrix', 'site_plan_data',
                'massing_summary', 'unit_mix_summary', 'financial_feasibility', 'precedent_report',
                'public_benefit_statement', 'shadow_study'],
    },
    {
        label: 'Variance & Compliance',
        types: ['four_statutory_tests', 'variance_justification', 'as_of_right_check', 'compliance_review_report'],
    },
    {
        label: 'Pathway & Process',
        types: ['approval_pathway_document', 'timeline_cost_estimate', 'required_studies_checklist',
                'professional_referral_checklist', 'building_permit_readiness_checklist', 'pac_prep_package'],
    },
    {
        label: 'Appeals & Responses',
        types: ['olt_appeal_brief', 'revised_rationale', 'mediation_strategy', 'correction_response'],
    },
    {
        label: 'Community & Readiness',
        types: ['neighbour_support_letter', 'submission_readiness_report', 'due_diligence_report'],
    },
];

function statusColor(status) {
    if (status === 'approved') return '#4caf50';
    if (status === 'under_review') return '#ff9800';
    if (status === 'draft') return '#9e9e9e';
    return '#9e9e9e';
}

export default function DocumentGallery({ planId, documents, onRegenerate, onDocStatusChange }) {
    const [selectedDocId, setSelectedDocId] = useState(null);

    const selectedDoc = documents.find((d) => d.id === selectedDocId);
    const docsByType = Object.fromEntries(documents.map((d) => [d.doc_type, d]));

    const handleExportAll = useCallback(async () => {
        try {
            const { exportPlan } = await import('../api.js');
            await exportPlan(planId);
        } catch (err) {
            console.error('Export failed:', err);
        }
    }, [planId]);

    return (
        <div className="doc-gallery">
            <div className="doc-gallery-sidebar">
                <div className="doc-gallery-header">
                    <h3>Documents ({documents.length})</h3>
                    <button className="doc-export-btn" onClick={handleExportAll} title="Export all documents">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                            <polyline points="7 10 12 15 17 10" />
                            <line x1="12" y1="15" x2="12" y2="3" />
                        </svg>
                        Export All
                    </button>
                </div>
                <div className="doc-gallery-list">
                    {DOC_GROUPS.map((group) => {
                        const groupDocs = group.types.filter((t) => docsByType[t]);
                        if (groupDocs.length === 0) return null;
                        return (
                            <div key={group.label} className="doc-group">
                                <div className="doc-group-label">{group.label}</div>
                                {groupDocs.map((docType) => {
                                    const doc = docsByType[docType];
                                    return (
                                        <button
                                            key={doc.id}
                                            className={`doc-list-item ${selectedDocId === doc.id ? 'selected' : ''}`}
                                            onClick={() => setSelectedDocId(doc.id)}
                                        >
                                            <span
                                                className="doc-status-dot"
                                                style={{ background: statusColor(doc.review_status) }}
                                            />
                                            <span className="doc-list-title">{doc.title}</span>
                                        </button>
                                    );
                                })}
                            </div>
                        );
                    })}
                </div>
            </div>
            <div className="doc-gallery-viewer">
                <DocumentViewer
                    document={selectedDoc}
                    planId={planId}
                    onRegenerate={onRegenerate}
                    onStatusChange={onDocStatusChange}
                />
            </div>
        </div>
    );
}
