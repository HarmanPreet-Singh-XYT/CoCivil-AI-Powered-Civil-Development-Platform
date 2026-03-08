import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { getParcelOverlays, getParcelZoningAnalysis, getPolicyStack, getNearbyApplications, getParcelFinancialSummary, uploadDocument, getUpload, getPlanDocuments, regeneratePlanDocument } from '../api.js';
import { isResolvedParcel, isUnresolvedParcel } from '../lib/parcelState.js';

const UPLOAD_POLL_MS = 3000;
const UPLOAD_MAX_ATTEMPTS = 40;
const MAX_FILE_SIZE = 50 * 1024 * 1024;
const ACCEPTED_TYPES = '.pdf,.png,.jpg,.jpeg,.xlsx,.xls,.csv,.dwg,.dxf,.doc,.docx';

function FileUploadZone({ onUploadComplete }) {
    const [isDragOver, setIsDragOver] = useState(false);
    const [uploads, setUploads] = useState([]);
    const fileInputRef = useRef(null);
    const pollControllersRef = useRef({});

    useEffect(() => {
        return () => {
            Object.values(pollControllersRef.current).forEach((c) => c.abort());
        };
    }, []);

    const pollUpload = useCallback(async (uploadId, filename) => {
        const controller = new AbortController();
        pollControllersRef.current[uploadId] = controller;
        const { signal } = controller;

        try {
            for (let i = 0; i < UPLOAD_MAX_ATTEMPTS; i++) {
                await new Promise((resolve, reject) => {
                    const timer = setTimeout(resolve, UPLOAD_POLL_MS);
                    signal.addEventListener('abort', () => { clearTimeout(timer); reject(new DOMException('Aborted', 'AbortError')); }, { once: true });
                });
                const upload = await getUpload(uploadId, { signal });
                if (signal.aborted) return;

                if (upload.status === 'analyzed') {
                    const summary = [];
                    if (upload.doc_category) summary.push(upload.doc_category.replace(/_/g, ' '));
                    if (upload.page_count) summary.push(`${upload.page_count} pages`);
                    const extracted = upload.extracted_data?.building || {};
                    const items = [];
                    if (extracted.storeys) items.push(`${extracted.storeys} storeys`);
                    if (extracted.unit_count) items.push(`${extracted.unit_count} units`);
                    if (extracted.height_m) items.push(`${extracted.height_m}m`);
                    if (items.length) summary.push(items.join(', '));
                    const issueCount = upload.compliance_findings?.issues?.length || 0;

                    setUploads((prev) => prev.map((u) =>
                        u.id === uploadId ? { ...u, status: 'analyzed', summary: summary.join(' · '), issueCount, extractedData: upload.extracted_data } : u
                    ));
                    onUploadComplete?.({ id: uploadId, filename, extractedData: upload.extracted_data });
                    return;
                }
                if (upload.status === 'failed') {
                    setUploads((prev) => prev.map((u) =>
                        u.id === uploadId ? { ...u, status: 'failed', error: upload.error_message || 'Analysis failed' } : u
                    ));
                    return;
                }
            }
            setUploads((prev) => prev.map((u) =>
                u.id === uploadId ? { ...u, status: 'timeout' } : u
            ));
        } catch (error) {
            if (error?.name !== 'AbortError') {
                setUploads((prev) => prev.map((u) =>
                    u.id === uploadId ? { ...u, status: 'failed', error: error.message } : u
                ));
            }
        } finally {
            delete pollControllersRef.current[uploadId];
        }
    }, [onUploadComplete]);

    const handleFile = useCallback(async (file) => {
        if (!file) return;
        if (file.size > MAX_FILE_SIZE) {
            setUploads((prev) => [...prev, { id: `err-${Date.now()}`, filename: file.name, status: 'failed', error: 'File exceeds 50 MB limit' }]);
            return;
        }
        const tempId = `temp-${Date.now()}`;
        setUploads((prev) => [...prev, { id: tempId, filename: file.name, status: 'uploading' }]);

        try {
            const result = await uploadDocument(file);
            if (result.status === 'analyzed' && result.extracted_data) {
                // Immediate result (e.g. DXF parsed inline)
                setUploads((prev) => prev.map((u) =>
                    u.id === tempId ? { ...u, id: result.id, status: 'analyzed', summary: 'Parsed', extractedData: result.extracted_data } : u
                ));
                onUploadComplete?.({ id: result.id, filename: file.name, extractedData: result.extracted_data });
            } else {
                setUploads((prev) => prev.map((u) =>
                    u.id === tempId ? { ...u, id: result.id, status: 'processing' } : u
                ));
                pollUpload(result.id, file.name);
            }
        } catch (err) {
            setUploads((prev) => prev.map((u) =>
                u.id === tempId ? { ...u, status: 'failed', error: err.message } : u
            ));
        }
    }, [pollUpload]);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragOver(false);
        const files = Array.from(e.dataTransfer?.files || []);
        files.forEach(handleFile);
    }, [handleFile]);

    const handleRemove = useCallback((id) => {
        pollControllersRef.current[id]?.abort();
        setUploads((prev) => prev.filter((u) => u.id !== id));
    }, []);

    const statusLabel = (upload) => {
        if (upload.status === 'uploading') return 'Uploading...';
        if (upload.status === 'processing') return 'Analyzing...';
        if (upload.status === 'analyzed') return 'Analyzed';
        if (upload.status === 'failed') return upload.error || 'Failed';
        if (upload.status === 'timeout') return 'Still processing...';
        return upload.status;
    };

    const statusClass = (upload) => {
        if (upload.status === 'analyzed') return 'upload-status-ok';
        if (upload.status === 'failed') return 'upload-status-error';
        return 'upload-status-pending';
    };

    return (
        <div className="upload-zone-wrapper">
            <div className="dd-card-label" style={{ marginBottom: 8 }}>Project Files</div>
            <div
                className={`upload-dropzone ${isDragOver ? 'upload-dropzone-active' : ''}`}
                onDrop={handleDrop}
                onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                onDragLeave={() => setIsDragOver(false)}
                onClick={() => fileInputRef.current?.click()}
                role="button"
                tabIndex={0}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept={ACCEPTED_TYPES}
                    style={{ display: 'none' }}
                    onChange={(e) => { Array.from(e.target.files).forEach(handleFile); e.target.value = ''; }}
                />
                <svg className="upload-dropzone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
                <span className="upload-dropzone-text">Drop files here or click to browse</span>
                <span className="upload-dropzone-hint">Blueprints, site plans, reports, drawings, spreadsheets</span>
            </div>

            {uploads.length > 0 && (
                <div className="upload-file-list">
                    {uploads.map((upload) => (
                        <div key={upload.id} className={`upload-file-row ${statusClass(upload)}`}>
                            <div className="upload-file-info">
                                <div className="upload-file-name">
                                    {(upload.status === 'uploading' || upload.status === 'processing') && (
                                        <span className="upload-file-spinner" />
                                    )}
                                    {upload.status === 'analyzed' && (
                                        <svg className="upload-file-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
                                            <polyline points="20 6 9 17 4 12" />
                                        </svg>
                                    )}
                                    {upload.status === 'failed' && (
                                        <svg className="upload-file-x" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
                                            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                                        </svg>
                                    )}
                                    <span>{upload.filename}</span>
                                </div>
                                <div className="upload-file-status">{statusLabel(upload)}</div>
                                {upload.summary && <div className="upload-file-summary">{upload.summary}</div>}
                                {upload.issueCount > 0 && (
                                    <div className="upload-file-issues">{upload.issueCount} compliance issue{upload.issueCount > 1 ? 's' : ''} found</div>
                                )}
                            </div>
                            <button className="upload-file-remove" onClick={(e) => { e.stopPropagation(); handleRemove(upload.id); }} title="Remove">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
                                    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                                </svg>
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function complianceStatus(proposed, max) {
    if (proposed === '' || proposed === undefined || proposed === null) return 'neutral';
    const p = parseFloat(proposed);
    const m = parseFloat(max);
    if (Number.isNaN(p) || Number.isNaN(m)) return 'neutral';
    if (p <= m) return 'ok';
    if (p <= m * 1.15) return 'variance';
    return 'rezone';
}

function statusIcon(status) {
    if (status === 'ok') return <span className="compliance-dot compliance-ok" title="Compliant">●</span>;
    if (status === 'variance') return <span className="compliance-dot compliance-variance" title="Minor variance likely">●</span>;
    if (status === 'rezone') return <span className="compliance-dot compliance-rezone" title="Rezoning required">●</span>;
    return <span className="compliance-dot compliance-neutral">○</span>;
}

function formatMetric(value, suffix = '', fallback = 'Unavailable') {
    if (value === null || value === undefined || value === '') return fallback;
    return `${value}${suffix}`;
}

function isAbortError(error) {
    return error?.name === 'AbortError';
}

function zoneDisplay(parcel, zoning) {
    return zoning?.zoneString || parcel?.zoneCode || parcel?.zoning || 'Unknown';
}

function zoningNotes(zoning) {
    if (!zoning) return [];
    const overlayNotes = (zoning.overlayConstraints || [])
        .map((constraint) => constraint.impact)
        .filter(Boolean);
    return [...new Set([...(zoning.warnings || []), ...overlayNotes])];
}

function ReviewNotesCard({ zoning }) {
    const notes = zoningNotes(zoning);
    if (notes.length === 0) return null;

    return (
        <div className="dd-card">
            <div className="dd-card-label">Review Notes</div>
            <ul style={{ margin: '10px 0 0 18px', padding: 0 }}>
                {notes.map((note) => (
                    <li key={note} style={{ marginBottom: 8 }}>
                        {note}
                    </li>
                ))}
            </ul>
        </div>
    );
}

function LoadingZoningTab({ parcel }) {
    return (
        <div className="tab-section-header">
            <h3>Loading Zoning Analysis</h3>
            <p className="tab-section-desc">Fetching backend zoning analysis for {parcel.address}…</p>
        </div>
    );
}

function OverviewTab({ parcel, zoning, proposal, setProposal, onUploadComplete }) {
    const update = (key, val) => setProposal((prev) => ({ ...prev, [key]: val }));
    const rows = [
        { label: 'Height (m)', permitted: zoning.maxHeight, key: 'height' },
        { label: 'FSI / FAR', permitted: zoning.maxFsi, key: 'fsi' },
        { label: 'Storeys', permitted: zoning.maxStoreys, key: 'storeys' },
        { label: 'Lot Coverage (%)', permitted: zoning.lotCoverage, key: 'lotCoverage' },
    ];
    const zoneName = zoneDisplay(parcel, zoning);

    return (
        <>
            <FileUploadZone onUploadComplete={onUploadComplete} />

            <div className="tab-section-header" style={{ marginTop: 16 }}>
                <h3>Project Configurator</h3>
                <p className="tab-section-desc">Compare your proposal against backend zoning analysis for {zoneName}.</p>
                <p className="tab-section-desc" style={{ marginTop: 8, opacity: 0.8 }}>
                    This tab uses the backend bylaw parser and reference tables instead of a frontend zoning lookup.
                </p>
            </div>

            <div className="dd-address-badge">
                <span className="dd-zone-chip">{zoning.zoneCategory || parcel.zoning || '—'}</span>
                <span>{parcel.address}</span>
            </div>

            <div className="configurator-grid">
                <div className="config-col-header">Zoning Permits</div>
                <div className="config-col-header">Your Proposal</div>
                <div className="config-col-header config-col-status" />

                {rows.map((row) => {
                    const status = complianceStatus(proposal[row.key], row.permitted);
                    return (
                        <div className="config-row" key={row.key}>
                            <div className="config-label">{row.label}</div>
                            <div className="config-permitted">{formatMetric(row.permitted)}</div>
                            <div className="config-proposed">
                                <input
                                    type="number"
                                    className="config-input"
                                    value={proposal[row.key]}
                                    onChange={(event) => update(row.key, event.target.value)}
                                    placeholder="—"
                                />
                            </div>
                            <div className="config-status">{statusIcon(status)}</div>
                        </div>
                    );
                })}
            </div>

            <div className="dd-card">
                <div className="dd-card-label">Zone Classification</div>
                <div className="dd-card-value">{zoning.label}</div>
            </div>
            <div className="dd-card">
                <div className="dd-card-label">By-law Reference</div>
                <div className="dd-card-value">{formatMetric(zoning.bylawSection, '', 'Unavailable')}</div>
            </div>
            <div className="dd-card">
                <div className="dd-card-label">Permitted Uses</div>
                <div className="tag-list">
                    {(zoning.uses || []).length > 0
                        ? zoning.uses.map((use) => <span key={use} className="tag">{use}</span>)
                        : <span className="tag">No uses surfaced</span>
                    }
                </div>
            </div>
            <ReviewNotesCard zoning={zoning} />

            <div className="compliance-legend">
                <span><span className="compliance-dot compliance-ok">●</span> As-of-right</span>
                <span><span className="compliance-dot compliance-variance">●</span> Minor variance</span>
                <span><span className="compliance-dot compliance-rezone">●</span> Rezoning</span>
            </div>
        </>
    );
}

function MassingTab({ zoning, parcel }) {
    const hasLotArea = Number.isFinite(parcel.lotArea);
    const envelopeRows = [
        { label: 'Front Setback', value: formatMetric(zoning.frontSetback, ' m') },
        { label: 'Interior Side Setback', value: formatMetric(zoning.sideSetback, ' m') },
        { label: 'Exterior Side Setback', value: formatMetric(zoning.exteriorSideSetback, ' m') },
        { label: 'Rear Setback', value: formatMetric(zoning.rearSetback, ' m') },
        { label: 'Max Height', value: formatMetric(zoning.maxHeight, ' m') },
        { label: 'Max Storeys', value: formatMetric(zoning.maxStoreys) },
        { label: 'Max FSI', value: formatMetric(zoning.maxFsi) },
        { label: 'Lot Coverage', value: formatMetric(zoning.lotCoverage, '%') },
        { label: 'Min Landscaping', value: formatMetric(zoning.landscaping, '%') },
    ];

    return (
        <>
            <div className="tab-section-header">
                <h3>Building Envelope</h3>
                <p className="tab-section-desc">Physical constraints derived from backend zoning analysis for {zoneDisplay(parcel, zoning)}.</p>
                <p className="tab-section-desc" style={{ marginTop: 8, opacity: 0.8 }}>
                    If the parcel carries exceptions or overlays, the review notes below should be checked before treating these values as final.
                </p>
            </div>

            <div className="massing-grid">
                {envelopeRows.map((row) => (
                    <div className="massing-card" key={row.label}>
                        <div className="massing-label">{row.label}</div>
                        <div className="massing-value">{row.value}</div>
                    </div>
                ))}
            </div>

            <div className="dd-card">
                <div className="dd-card-label">Lot Area</div>
                <div className="dd-card-value">{hasLotArea ? `${parcel.lotArea} m²` : 'Unavailable'}</div>
            </div>
            <div className="dd-card">
                <div className="dd-card-label">Max GFA (FSI × Lot Area)</div>
                <div className="dd-card-value">
                    {hasLotArea && zoning.maxFsi != null
                        ? `${(parcel.lotArea * zoning.maxFsi).toFixed(0)} m²`
                        : 'Unavailable without parcel lot area and FSI'
                    }
                </div>
            </div>
            <ReviewNotesCard zoning={zoning} />
        </>
    );
}

function PoliciesTab({ policies, loading }) {
    const [expanded, setExpanded] = useState({});
    const toggle = (idx) => setExpanded((prev) => ({ ...prev, [idx]: !prev[idx] }));

    if (loading) {
        return (
            <div className="tab-section-header">
                <h3>Policy Extracts</h3>
                <p className="tab-section-desc">Loading applicable policies…</p>
            </div>
        );
    }

    if (!policies || policies.length === 0) {
        return (
            <div className="tab-section-header">
                <h3>Policy Extracts</h3>
                <p className="tab-section-desc">No policies found for this parcel.</p>
            </div>
        );
    }

    return (
        <>
            <div className="tab-section-header">
                <h3>Policy Extracts</h3>
                <p className="tab-section-desc">Relevant legislation and guidelines for this parcel.</p>
            </div>

            <div className="policy-accordion">
                {policies.map((doc, idx) => (
                    <div key={idx} className={`accordion-item ${expanded[idx] ? 'accordion-open' : ''}`}>
                        <button className="accordion-header" onClick={() => toggle(idx)}>
                            <div className="accordion-title">
                                <svg className="accordion-doc-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                    <polyline points="14 2 14 8 20 8" />
                                </svg>
                                <span>{doc.name}</span>
                            </div>
                            <div className="accordion-meta">
                                <span className="accordion-count">{doc.extracts} extracts</span>
                                <svg className="accordion-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <polyline points="6 9 12 15 18 9" />
                                </svg>
                            </div>
                        </button>
                        {expanded[idx] && (
                            <div className="accordion-body">
                                {doc.sections.length > 0 ? doc.sections.map((section, sectionIndex) => (
                                    <div key={sectionIndex} className="extract-block">
                                        <div className="extract-title">{section.title}</div>
                                        <p className="extract-text">{section.text}</p>
                                    </div>
                                )) : (
                                    <p className="extract-text" style={{ opacity: 0.5 }}>No clause extracts available for this document.</p>
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </>
    );
}

function DatasetsTab({ overlays, loading }) {
    if (loading) {
        return (
            <div className="tab-section-header">
                <h3>Data Sources</h3>
                <p className="tab-section-desc">Loading overlays…</p>
            </div>
        );
    }

    if (!overlays || overlays.length === 0) {
        return (
            <div className="tab-section-header">
                <h3>Data Sources</h3>
                <p className="tab-section-desc">No overlay datasets found for this parcel.</p>
            </div>
        );
    }

    return (
        <>
            <div className="tab-section-header">
                <h3>Data Sources</h3>
                <p className="tab-section-desc">Municipally-verified datasets intersecting this parcel.</p>
            </div>
            <div className="datasets-list">
                {overlays.map((overlay, idx) => (
                    <div key={idx} className="dataset-row">
                        <div className="dataset-row-left">
                            <svg className="dataset-row-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <ellipse cx="12" cy="5" rx="9" ry="3" />
                                <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                                <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                            </svg>
                            <div>
                                <div className="dataset-row-name">{overlay.name}</div>
                                <div className="dataset-row-desc">{overlay.description}</div>
                            </div>
                        </div>
                        {overlay.values != null && (
                            <div className="dataset-row-meta">{overlay.values} values</div>
                        )}
                    </div>
                ))}
            </div>
        </>
    );
}

function PrecedentsTab({ parcel }) {
    const [applications, setApplications] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!parcel?.id) return;
        const controller = new AbortController();
        setLoading(true);
        setError(null);
        getNearbyApplications(parcel.id, { signal: controller.signal })
            .then((data) => {
                setApplications(data.applications || []);
            })
            .catch((err) => {
                if (err?.name !== 'AbortError') setError('Failed to load nearby applications');
            })
            .finally(() => setLoading(false));
        return () => controller.abort();
    }, [parcel?.id]);

    const APP_TYPE_LABELS = { SA: 'Site Alteration', OZ: 'Official Plan / Zoning', CD: 'Condo Approval', SB: 'Site Plan / Boulevard', PL: 'Plan of Subdivision' };
    const DECISION_COLORS = { approved: '#2d8a4e', refused: '#c0392b', appealed: '#e67e22', pending: '#7f8c8d' };

    if (loading) {
        return (
            <div className="tab-section-header">
                <h3>Nearby Applications</h3>
                <p className="tab-section-desc">Loading nearby development applications...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="tab-section-header">
                <h3>Nearby Applications</h3>
                <p className="tab-section-desc" style={{ color: '#c0392b' }}>{error}</p>
            </div>
        );
    }

    if (!applications.length) {
        return (
            <div className="tab-section-header">
                <h3>Nearby Applications</h3>
                <p className="tab-section-desc">No development applications found within 2km of {parcel.address}.</p>
            </div>
        );
    }

    return (
        <>
            <div className="tab-section-header">
                <h3>Nearby Applications</h3>
                <p className="tab-section-desc">{applications.length} development application{applications.length !== 1 ? 's' : ''} within 2km</p>
            </div>
            <div className="dataset-list">
                {applications.map((app) => (
                    <div key={app.id} className="dataset-row">
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, flex: 1 }}>
                            <div style={{
                                width: 8, height: 8, borderRadius: '50%', marginTop: 6, flexShrink: 0,
                                backgroundColor: DECISION_COLORS[app.decision] || '#999',
                            }} />
                            <div style={{ flex: 1 }}>
                                <div className="dataset-row-name">{app.address || app.app_number}</div>
                                <div className="dataset-row-desc">
                                    {APP_TYPE_LABELS[app.app_type] || app.app_type}
                                    {app.proposed_height_m ? ` · ${app.proposed_height_m}m` : ''}
                                    {app.proposed_units ? ` · ${app.proposed_units} units` : ''}
                                </div>
                            </div>
                        </div>
                        <div style={{ textAlign: 'right', flexShrink: 0 }}>
                            <div style={{ fontSize: 12, color: DECISION_COLORS[app.decision] || '#999', fontWeight: 500 }}>
                                {app.decision || app.status || 'unknown'}
                            </div>
                            {app.distance_m != null && (
                                <div style={{ fontSize: 11, opacity: 0.6 }}>{app.distance_m < 1000 ? `${Math.round(app.distance_m)}m` : `${(app.distance_m / 1000).toFixed(1)}km`}</div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </>
    );
}

function UnresolvedParcelTab({ parcel }) {
    return (
        <div className="tab-empty">
            <p>{parcel.message}</p>
            <p style={{ marginTop: 10, opacity: 0.75 }}>
                The map can still center this address, but parcel-linked zoning, policy, datasets, precedents, and entitlements stay unavailable until a parcel record is matched.
            </p>
        </div>
    );
}

function MissingZoningGuidanceTab({ parcel }) {
    return (
        <div className="tab-empty">
            <p>
                This parcel resolved successfully, but the backend could not derive zoning standards for
                {' '}
                <strong>{parcel.zoneCode || parcel.zoning || 'unknown'}</strong>.
            </p>
            <p style={{ marginTop: 10, opacity: 0.75 }}>
                Policy extracts and datasets may still be available in their tabs, but overview, massing, and entitlement guidance are unavailable here.
            </p>
        </div>
    );
}

function EntitlementsTab({ parcel, zoning, proposal }) {
    const approvals = useMemo(() => {
        const items = [];

        const check = (label, proposed, max) => {
            const status = complianceStatus(proposed, max);
            if (status === 'ok') items.push({ label, status: 'As-of-Right', cls: 'badge-approved' });
            else if (status === 'variance') items.push({ label, status: 'Minor Variance', cls: 'badge-review' });
            else if (status === 'rezone') items.push({ label, status: 'Rezoning Required', cls: 'badge-refused' });
        };

        check('Height', proposal.height, zoning.maxHeight);
        check('FSI', proposal.fsi, zoning.maxFsi);
        check('Storeys', proposal.storeys, zoning.maxStoreys);
        check('Lot Coverage', proposal.lotCoverage, zoning.lotCoverage);

        if (items.length === 0) {
            items.push({ label: 'Enter proposal values in Overview tab', status: '—', cls: '' });
        }
        return items;
    }, [proposal, zoning]);

    const handleExport = useCallback(() => {
        const zoneName = zoneDisplay(parcel, zoning);
        const win = window.open('', '_blank');
        win.document.write(`
<html><head><title>Preliminary Entitlement Snapshot — ${parcel.address}</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 40px; color: #1a1a1a; max-width: 800px; margin: 0 auto; }
  h1 { font-size: 1.5rem; border-bottom: 2px solid #c8a55c; padding-bottom: 8px; }
  h2 { font-size: 1.1rem; margin-top: 24px; color: #555; }
  table { width: 100%; border-collapse: collapse; margin: 12px 0; }
  th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #e0e0e0; font-size: 0.9rem; }
  th { background: #f5f5f5; font-weight: 600; }
  .badge { padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
  .badge-green { background: #dcfce7; color: #166534; }
  .badge-amber { background: #fef3c7; color: #92400e; }
  .badge-red   { background: #fee2e2; color: #991b1b; }
  .footer { margin-top: 40px; font-size: 0.8rem; color: #999; border-top: 1px solid #e0e0e0; padding-top: 12px; }
</style></head><body>
<h1>Preliminary Entitlement Snapshot</h1>
<p><strong>Note:</strong> This export is generated from backend zoning analysis and proposal values entered in the UI. It is an early-stage estimate, not a legal opinion.</p>
<p><strong>Address:</strong> ${parcel.address} &nbsp; <strong>Zone:</strong> ${zoneName} &nbsp; <strong>By-law Section:</strong> ${zoning.bylawSection || 'Unavailable'}</p>
<h2>Zoning Constraints</h2>
<table><tr><th>Parameter</th><th>Permitted</th><th>Proposed</th><th>Status</th></tr>
${[
    ['Height', zoning.maxHeight, proposal.height, 'm'],
    ['FSI', zoning.maxFsi, proposal.fsi, ''],
    ['Storeys', zoning.maxStoreys, proposal.storeys, ''],
    ['Lot Coverage', zoning.lotCoverage, proposal.lotCoverage, '%'],
].map(([label, max, val, unit]) => {
    const status = complianceStatus(val, max);
    const badge = !val
        ? '—'
        : status === 'ok'
            ? '<span class="badge badge-green">Compliant</span>'
            : status === 'variance'
                ? '<span class="badge badge-amber">Variance</span>'
                : '<span class="badge badge-red">Rezone</span>';
    const permitted = max === null || max === undefined ? 'Unavailable' : `${max}${unit}`;
    return `<tr><td>${label}</td><td>${permitted}</td><td>${val || '—'}${val ? unit : ''}</td><td>${badge}</td></tr>`;
}).join('')}
</table>
<h2>Building Envelope</h2>
<table><tr><th>Constraint</th><th>Value</th></tr>
<tr><td>Front Setback</td><td>${formatMetric(zoning.frontSetback, ' m')}</td></tr>
<tr><td>Interior Side Setback</td><td>${formatMetric(zoning.sideSetback, ' m')}</td></tr>
<tr><td>Exterior Side Setback</td><td>${formatMetric(zoning.exteriorSideSetback, ' m')}</td></tr>
<tr><td>Rear Setback</td><td>${formatMetric(zoning.rearSetback, ' m')}</td></tr>
</table>
<h2>Required Approvals</h2>
<table><tr><th>Parameter</th><th>Approval Type</th></tr>
${approvals.map((approval) => `<tr><td>${approval.label}</td><td>${approval.status}</td></tr>`).join('')}
</table>
<div class="footer">Generated by applicationAI · Backend zoning estimate · ${new Date().toLocaleString()}</div>
</body></html>`);
        win.document.close();
        win.print();
    }, [approvals, parcel, proposal, zoning]);

    return (
        <>
            <div className="tab-section-header">
                <h3>Entitlements & Report</h3>
                <p className="tab-section-desc">Preliminary approval signal based on your proposal values and backend zoning analysis.</p>
                <p className="tab-section-desc" style={{ marginTop: 8, opacity: 0.8 }}>
                    Review notes should be checked before treating any non-compliant item as a simple variance.
                </p>
            </div>

            <div className="approvals-list">
                {approvals.map((approval, idx) => (
                    <div key={idx} className="approval-row">
                        <span className="approval-label">{approval.label}</span>
                        {approval.cls
                            ? <span className={`precedent-badge ${approval.cls}`}>{approval.status}</span>
                            : <span className="approval-dash">{approval.status}</span>
                        }
                    </div>
                ))}
            </div>

            <ReviewNotesCard zoning={zoning} />

            <button className="export-btn" onClick={handleExport}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Export Preliminary Entitlement Snapshot
            </button>
        </>
    );
}

function formatCurrency(val) {
    if (val == null) return '—';
    if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
    if (Math.abs(val) >= 1e3) return `$${(val / 1e3).toFixed(0)}K`;
    return `$${val.toLocaleString()}`;
}

function FinancesTab({ parcel }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [activeEstimate, setActiveEstimate] = useState('rental');

    useEffect(() => {
        if (!parcel?.id) return;
        const controller = new AbortController();
        setLoading(true);
        getParcelFinancialSummary(parcel.id, { signal: controller.signal })
            .then((d) => { if (d) setData(d); })
            .catch(() => {})
            .finally(() => setLoading(false));
        return () => controller.abort();
    }, [parcel?.id]);

    if (loading) return <div className="tab-section-header"><h3>Financial Feasibility</h3><p className="tab-section-desc">Loading financial data...</p></div>;
    if (!data) return <div className="tab-section-header"><h3>Financial Feasibility</h3><p className="tab-section-desc">No financial data available for this parcel.</p></div>;

    const estimate = data.estimates?.[activeEstimate];
    const COMP_TYPE_LABELS = { rental: 'Rental', sale: 'Condo Sale', land_sale: 'Land Sale', construction_cost: 'Construction' };

    return (
        <>
            <div className="tab-section-header">
                <h3>Financial Feasibility</h3>
                <p className="tab-section-desc">Quick pro forma estimate for {data.address}</p>
            </div>

            {/* Parcel metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, padding: '0 16px 12px' }}>
                <div className="kpi-card">
                    <div className="kpi-label">Assessed Value</div>
                    <div className="kpi-value">{formatCurrency(data.assessed_value)}</div>
                </div>
                <div className="kpi-card">
                    <div className="kpi-label">Max GFA</div>
                    <div className="kpi-value">{data.estimated_gfa_m2 ? `${data.estimated_gfa_m2.toLocaleString()} m²` : '—'}</div>
                </div>
                <div className="kpi-card">
                    <div className="kpi-label">Lot Area</div>
                    <div className="kpi-value">{data.lot_area_m2 ? `${Math.round(data.lot_area_m2).toLocaleString()} m²` : '—'}</div>
                </div>
                <div className="kpi-card">
                    <div className="kpi-label">Max FSI / Height</div>
                    <div className="kpi-value">{data.max_fsi ?? '—'} / {data.max_height_m ? `${data.max_height_m}m` : '—'}</div>
                </div>
            </div>

            {/* Tenure toggle */}
            {Object.keys(data.estimates || {}).length > 0 && (
                <div style={{ padding: '0 16px 8px', display: 'flex', gap: 6 }}>
                    {Object.keys(data.estimates).map((key) => (
                        <button
                            key={key}
                            onClick={() => setActiveEstimate(key)}
                            className={`tenure-toggle ${activeEstimate === key ? 'active' : ''}`}
                        >
                            {key === 'rental' ? 'Rental' : 'Condo'}
                        </button>
                    ))}
                </div>
            )}

            {/* Pro forma estimate */}
            {estimate && (
                <div style={{ padding: '0 16px 12px' }}>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, opacity: 0.7 }}>Pro Forma Estimate</div>
                    <div className="proforma-table">
                        <div className="proforma-row"><span>Revenue</span><span style={{ color: '#2d8a4e' }}>{formatCurrency(estimate.revenue)}</span></div>
                        {estimate.noi != null && <div className="proforma-row"><span>NOI</span><span>{formatCurrency(estimate.noi)}</span></div>}
                        <div className="proforma-row"><span>Hard Cost</span><span style={{ color: '#c0392b' }}>{formatCurrency(estimate.hard_cost)}</span></div>
                        <div className="proforma-row"><span>Soft Cost</span><span style={{ color: '#c0392b' }}>{formatCurrency(estimate.soft_cost)}</span></div>
                        <div className="proforma-row total"><span>Total Cost</span><span style={{ color: '#c0392b' }}>{formatCurrency(estimate.total_cost)}</span></div>
                        <div className="proforma-row"><span>Valuation</span><span>{formatCurrency(estimate.valuation)}</span></div>
                        <div className="proforma-row total" style={{ borderTop: '2px solid var(--border-color)' }}>
                            <span>Residual Land Value</span>
                            <span style={{ color: estimate.residual_land_value >= 0 ? '#2d8a4e' : '#c0392b', fontWeight: 700 }}>
                                {formatCurrency(estimate.residual_land_value)}
                            </span>
                        </div>
                    </div>
                </div>
            )}

            {/* Market comps */}
            {data.nearby_comps?.length > 0 && (
                <div style={{ padding: '0 16px 12px' }}>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, opacity: 0.7 }}>
                        Nearby Market Comps ({data.nearby_comps.length})
                    </div>
                    <div className="dataset-list">
                        {data.nearby_comps.map((comp, i) => (
                            <div key={i} className="dataset-row" style={{ padding: '8px 0' }}>
                                <div style={{ flex: 1 }}>
                                    <div className="dataset-row-name">{comp.address}</div>
                                    <div className="dataset-row-desc">
                                        {COMP_TYPE_LABELS[comp.comp_type] || comp.comp_type}
                                        {comp.attributes?.rent_psf_monthly ? ` · $${comp.attributes.rent_psf_monthly}/psf/mo` : ''}
                                        {comp.attributes?.sale_psf ? ` · $${comp.attributes.sale_psf}/psf` : ''}
                                        {comp.attributes?.price_per_buildable_sqft ? ` · $${comp.attributes.price_per_buildable_sqft}/bsf` : ''}
                                        {comp.attributes?.hard_cost_psf ? ` · $${comp.attributes.hard_cost_psf}/psf` : ''}
                                        {comp.attributes?.units ? ` · ${comp.attributes.units} units` : ''}
                                    </div>
                                </div>
                                {comp.distance_m != null && (
                                    <div style={{ fontSize: 11, opacity: 0.6, flexShrink: 0 }}>
                                        {comp.distance_m < 1000 ? `${Math.round(comp.distance_m)}m` : `${(comp.distance_m / 1000).toFixed(1)}km`}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </>
    );
}

function mapPolicyStack(data) {
    if (!data) return [];
    const entries = data.applicable_policies || [];
    const byDoc = {};

    for (const entry of entries) {
        const key = entry.document_id || entry.document_title;
        if (!byDoc[key]) {
            byDoc[key] = {
                name: entry.document_title || entry.doc_type || 'Policy Document',
                sections: [],
            };
        }
        if (entry.raw_text || entry.section_ref) {
            byDoc[key].sections.push({
                title: entry.section_ref || 'Section',
                text: entry.raw_text || '',
            });
        }
    }

    return Object.values(byDoc).map((doc) => ({
        ...doc,
        extracts: doc.sections.length,
    }));
}

function mapOverlays(data) {
    if (!data) return [];
    const overlays = data.overlays || [];
    const byLayer = {};

    for (const overlay of overlays) {
        const key = overlay.layer_id || overlay.layer_name || overlay.layer_type;
        if (!byLayer[key]) {
            byLayer[key] = {
                name: overlay.layer_name || overlay.name || overlay.layer_type || 'Dataset',
                description: overlay.source_url ? `Source: ${overlay.source_url}` : (overlay.layer_type || ''),
                count: 0,
            };
        }
        byLayer[key].count += 1;
    }

    return Object.values(byLayer).map((layer) => ({
        name: layer.name,
        description: layer.description,
        values: layer.count,
    }));
}

function mapZoningAnalysis(data) {
    if (!data?.standards) return null;
    const standards = data.standards;
    return {
        zoneString: data.zone_string || null,
        zoneCategory: data.components?.category || standards.category || null,
        label: standards.label || standards.category || 'Unknown Zone',
        maxHeight: standards.max_height_m,
        maxStoreys: standards.max_storeys,
        maxFsi: standards.max_fsi,
        frontSetback: standards.min_front_setback_m,
        rearSetback: standards.min_rear_setback_m,
        sideSetback: standards.min_interior_side_setback_m,
        exteriorSideSetback: standards.min_exterior_side_setback_m,
        lotCoverage: standards.max_lot_coverage_pct,
        landscaping: standards.min_landscaping_pct,
        uses: standards.permitted_uses || [],
        bylawSection: standards.bylaw_section,
        warnings: data.warnings || [],
        overlayConstraints: data.overlay_constraints || [],
    };
}

function DocumentsTab({ planId }) {
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedDoc, setSelectedDoc] = useState(null);

    useEffect(() => {
        if (!planId) return;
        let cancelled = false;
        setLoading(true);
        getPlanDocuments(planId).then((docs) => {
            if (!cancelled) {
                setDocuments(docs);
                setLoading(false);
            }
        }).catch(() => { if (!cancelled) setLoading(false); });
        return () => { cancelled = true; };
    }, [planId]);

    const handleRegenerate = useCallback(async (docType) => {
        try {
            const doc = await regeneratePlanDocument(planId, docType, {});
            setDocuments((prev) => {
                const exists = prev.find((d) => d.doc_type === docType);
                if (exists) return prev.map((d) => d.doc_type === docType ? doc : d);
                return [...prev, doc];
            });
            setSelectedDoc(doc);
        } catch (err) {
            console.error('Regenerate failed:', err);
        }
    }, [planId]);

    if (!planId) {
        return (
            <div style={{ padding: 20, textAlign: 'center', opacity: 0.7 }}>
                <p>Generate a plan to view documents.</p>
                <p style={{ fontSize: 12, marginTop: 8 }}>Use the chat panel to generate a development plan, then view and manage documents here.</p>
            </div>
        );
    }

    if (loading) {
        return <div style={{ padding: 20, textAlign: 'center' }}>Loading documents...</div>;
    }

    const selected = selectedDoc || (documents.length > 0 ? documents[0] : null);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
            <div style={{ padding: '8px 12px', borderBottom: '1px solid #eee', fontSize: 12, color: '#666' }}>
                {documents.length} document{documents.length !== 1 ? 's' : ''} generated
            </div>
            <div style={{ flex: 1, overflow: 'auto', padding: '8px 0' }}>
                {documents.map((doc) => (
                    <button
                        key={doc.id}
                        onClick={() => setSelectedDoc(doc)}
                        style={{
                            display: 'flex', alignItems: 'center', gap: 8,
                            width: '100%', padding: '8px 12px', border: 'none', cursor: 'pointer',
                            background: selected?.id === doc.id ? '#f0f4ff' : 'transparent',
                            borderLeft: selected?.id === doc.id ? '3px solid #3b82f6' : '3px solid transparent',
                            textAlign: 'left', fontSize: 13,
                        }}
                    >
                        <span style={{
                            width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                            background: doc.review_status === 'approved' ? '#4caf50' : doc.review_status === 'under_review' ? '#ff9800' : '#9e9e9e',
                        }} />
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.title}</span>
                    </button>
                ))}
            </div>
            {selected && (
                <div style={{ borderTop: '1px solid #eee', padding: 12, maxHeight: '50%', overflow: 'auto' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                        <strong style={{ fontSize: 13 }}>{selected.title}</strong>
                        <button
                            onClick={() => handleRegenerate(selected.doc_type)}
                            style={{ fontSize: 11, padding: '2px 8px', border: '1px solid #ccc', borderRadius: 4, cursor: 'pointer', background: '#fff' }}
                        >
                            Regenerate
                        </button>
                    </div>
                    <div style={{ fontSize: 12, lineHeight: 1.5, maxHeight: 300, overflow: 'auto', whiteSpace: 'pre-wrap', color: '#333' }}>
                        {(selected.content_text || '').slice(0, 2000)}
                        {(selected.content_text || '').length > 2000 && '...'}
                    </div>
                    <div style={{ marginTop: 8, fontSize: 11, color: '#888' }}>
                        Status: {selected.review_status} | Format: {selected.format}
                    </div>
                </div>
            )}
        </div>
    );
}

const TAB_TITLES = {
    overview: 'Project Overview',
    massing: 'Building Massing',
    finances: 'Financial Analysis',
    entitlements: 'Entitlements',
    policies: 'Policy Extracts',
    datasets: 'Data Sources',
    precedents: 'Precedents',
    documents: 'Documents',
};

const ZONING_TABS = new Set(['overview', 'massing', 'entitlements']);

export default function PolicyPanel({ parcel, isOpen, onClose, activeNav, savedParcels, onSaveParcel, onUploadAnalyzed, activePlanId }) {
    const [proposal, setProposal] = useState({ height: '', fsi: '', storeys: '', lotCoverage: '' });
    const [policies, setPolicies] = useState([]);
    const [overlays, setOverlays] = useState([]);
    const [zoningAnalysis, setZoningAnalysis] = useState(null);
    const [loadingPolicies, setLoadingPolicies] = useState(false);
    const [loadingOverlays, setLoadingOverlays] = useState(false);
    const [loadingZoning, setLoadingZoning] = useState(false);

    useEffect(() => {
        if (!isResolvedParcel(parcel)) {
            setPolicies([]);
            setOverlays([]);
            setZoningAnalysis(null);
            setLoadingPolicies(false);
            setLoadingOverlays(false);
            setLoadingZoning(false);
            return undefined;
        }

        const controller = new AbortController();
        const requestOptions = { signal: controller.signal };

        setLoadingPolicies(true);
        setLoadingOverlays(true);
        setLoadingZoning(true);

        getPolicyStack(parcel.id, requestOptions)
            .then((data) => {
                setPolicies(mapPolicyStack(data));
            })
            .catch((error) => {
                if (!isAbortError(error)) setPolicies([]);
            })
            .finally(() => {
                if (!controller.signal.aborted) setLoadingPolicies(false);
            });

        getParcelOverlays(parcel.id, requestOptions)
            .then((data) => {
                setOverlays(mapOverlays(data));
            })
            .catch((error) => {
                if (!isAbortError(error)) setOverlays([]);
            })
            .finally(() => {
                if (!controller.signal.aborted) setLoadingOverlays(false);
            });

        getParcelZoningAnalysis(parcel.id, requestOptions)
            .then((data) => {
                setZoningAnalysis(data);
            })
            .catch((error) => {
                if (!isAbortError(error)) setZoningAnalysis(null);
            })
            .finally(() => {
                if (!controller.signal.aborted) setLoadingZoning(false);
            });

        return () => {
            controller.abort();
        };
    }, [parcel]);

    const zoning = useMemo(() => mapZoningAnalysis(zoningAnalysis), [zoningAnalysis]);
    const visiblePolicies = isResolvedParcel(parcel) ? policies : [];
    const visibleOverlays = isResolvedParcel(parcel) ? overlays : [];
    const visiblePoliciesLoading = isResolvedParcel(parcel) ? loadingPolicies : false;
    const visibleOverlaysLoading = isResolvedParcel(parcel) ? loadingOverlays : false;
    const visibleZoningLoading = isResolvedParcel(parcel) ? loadingZoning : false;

    const renderTab = () => {
        if (!parcel) {
            return (
                <div className="tab-empty">
                    {activeNav === 'overview' && <FileUploadZone onUploadComplete={onUploadAnalyzed} />}
                    <p>Search for a property to view due diligence information.</p>
                </div>
            );
        }
        if (isUnresolvedParcel(parcel)) {
            return <UnresolvedParcelTab parcel={parcel} />;
        }
        if (visibleZoningLoading && ZONING_TABS.has(activeNav)) {
            return <LoadingZoningTab parcel={parcel} />;
        }
        if (!zoning && ZONING_TABS.has(activeNav)) {
            return <MissingZoningGuidanceTab parcel={parcel} />;
        }

        switch (activeNav) {
            case 'overview':
                return <OverviewTab parcel={parcel} zoning={zoning} proposal={proposal} setProposal={setProposal} onUploadComplete={onUploadAnalyzed} />;
            case 'massing':
                return <MassingTab zoning={zoning} parcel={parcel} />;
            case 'policies':
                return <PoliciesTab policies={visiblePolicies} loading={visiblePoliciesLoading} />;
            case 'datasets':
                return <DatasetsTab overlays={visibleOverlays} loading={visibleOverlaysLoading} />;
            case 'precedents':
                return <PrecedentsTab parcel={parcel} />;
            case 'entitlements':
                return <EntitlementsTab parcel={parcel} zoning={zoning} proposal={proposal} />;
            case 'finances':
                return <FinancesTab parcel={parcel} />;
            case 'documents':
                return <DocumentsTab planId={activePlanId} />;
            default:
                return <OverviewTab parcel={parcel} zoning={zoning} proposal={proposal} setProposal={setProposal} onUploadComplete={onUploadAnalyzed} />;
        }
    };

    return (
        <aside id="policy-panel" className={isOpen ? '' : 'panel-hidden'}>
            <div id="policy-panel-header">
                <h2 id="policy-panel-title">{TAB_TITLES[activeNav] || 'Project Information'}</h2>
                <div className="panel-header-actions">
                    {isResolvedParcel(parcel) && onSaveParcel && (
                        <button className="panel-save-btn" onClick={() => onSaveParcel(parcel)} title="Save parcel for comparison">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                            </svg>
                        </button>
                    )}
                    <button id="policy-panel-close" aria-label="Close panel" onClick={onClose}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <line x1="18" y1="6" x2="6" y2="18" />
                            <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                    </button>
                </div>
            </div>

            <div id="policy-panel-content">
                {savedParcels && savedParcels.length > 0 && (
                    <div className="saved-parcels-strip">
                        <div className="saved-parcels-label">Saved Parcels</div>
                        <div className="saved-parcels-list">
                            {savedParcels.map((savedParcel, idx) => (
                                <div key={idx} className="saved-parcel-chip">
                                    <span className="saved-parcel-zone">{savedParcel.zoning || '—'}</span>
                                    <span className="saved-parcel-addr">{savedParcel.address?.split(',')[0]}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {renderTab()}
            </div>
        </aside>
    );
}
