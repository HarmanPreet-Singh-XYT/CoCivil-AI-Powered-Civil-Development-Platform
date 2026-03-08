import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { getPolicyStack, getParcelOverlays } from '../api.js';
import { isResolvedParcel, isUnresolvedParcel } from '../lib/parcelState.js';

// ──────────────────── STATIC ZONING BYLAW DATA ────────────────────
const ZONING_DATA = {
    R: { maxUnits: 2, maxHeight: 10, maxFsi: 0.6, frontSetback: 6, sideSetback: 1.2, rearSetback: 7.5, lotCoverage: 33, angularPlane: 'N/A', typology: 'Detached', uses: ['Dwelling Unit', 'Home Occupation'] },
    RD: { maxUnits: 2, maxHeight: 10, maxFsi: 0.6, frontSetback: 6, sideSetback: 1.2, rearSetback: 7.5, lotCoverage: 33, angularPlane: 'N/A', typology: 'Semi-Detached', uses: ['Dwelling Unit', 'Home Occupation'] },
    RS: { maxUnits: 4, maxHeight: 10, maxFsi: 1.0, frontSetback: 6, sideSetback: 1.5, rearSetback: 7.5, lotCoverage: 40, angularPlane: 'N/A', typology: 'Fourplex', uses: ['Dwelling Unit', 'Home Occupation'] },
    RT: { maxUnits: 6, maxHeight: 12, maxFsi: 1.5, frontSetback: 4.5, sideSetback: 1.5, rearSetback: 7.5, lotCoverage: 45, angularPlane: '45° @ 10.5m', typology: 'Townhouse', uses: ['Dwelling Unit', 'Home Occupation', 'Live-Work'] },
    RM: { maxUnits: 60, maxHeight: 20, maxFsi: 2.5, frontSetback: 3, sideSetback: 5.5, rearSetback: 7.5, lotCoverage: 55, angularPlane: '45° @ 10.5m', typology: 'Mid-Rise', uses: ['Dwelling Unit', 'Home Occupation', 'Retail'] },
    RA: { maxUnits: 120, maxHeight: 36, maxFsi: 3.5, frontSetback: 3, sideSetback: 5.5, rearSetback: 7.5, lotCoverage: 45, angularPlane: '45° @ 10.5m', typology: 'Apartment', uses: ['Dwelling Unit', 'Retail', 'Office'] },
    CR: { maxUnits: 80, maxHeight: 30, maxFsi: 3.0, frontSetback: 0, sideSetback: 0, rearSetback: 7.5, lotCoverage: 80, angularPlane: '45° @ 24m', typology: 'Mixed-Use', uses: ['Dwelling Unit', 'Retail', 'Office', 'Restaurant'] },
    CRE: { maxUnits: 100, maxHeight: 45, maxFsi: 4.0, frontSetback: 0, sideSetback: 0, rearSetback: 7.5, lotCoverage: 80, angularPlane: '45° @ 24m', typology: 'Mixed-Use', uses: ['Dwelling Unit', 'Retail', 'Office'] },
    I: { maxUnits: 0, maxHeight: 15, maxFsi: 1.0, frontSetback: 6, sideSetback: 3, rearSetback: 3, lotCoverage: 60, angularPlane: 'N/A', typology: 'Industrial', uses: ['Manufacturing', 'Warehouse', 'Office'] },
};

const DEFAULT_PANEL_WIDTH = 380;
const MIN_PANEL_WIDTH = 280;
const MAX_PANEL_WIDTH = 640;

// ──────────────────── HELPERS ────────────────────
function complianceStatus(proposed, max) {
    if (proposed === '' || proposed === undefined) return 'neutral';
    const p = parseFloat(proposed), m = parseFloat(max);
    if (isNaN(p)) return 'neutral';
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

// ──────────────────── TAB COMPONENTS ────────────────────
function OverviewTab({ parcel, zoning, proposal, setProposal }) {
    const update = (key, val) => setProposal((p) => ({ ...p, [key]: val }));
    const rows = [
        { label: 'Height (m)', permitted: zoning.maxHeight, key: 'height' },
        { label: 'FSI / FAR', permitted: zoning.maxFsi, key: 'fsi' },
        { label: 'Units', permitted: zoning.maxUnits, key: 'units' },
        { label: 'Lot Coverage (%)', permitted: zoning.lotCoverage, key: 'lotCoverage' },
    ];
    return (
        <>
            <div className="tab-section-header">
                <h3>Project Configurator</h3>
                <p className="tab-section-desc">Compare your proposal against local bylaw guidance for zone {parcel.zoning}.</p>
                <p className="tab-section-desc" style={{ marginTop: 8, opacity: 0.8 }}>This tab uses deterministic in-app zoning tables and should be treated as preliminary guidance.</p>
            </div>
            <div className="dd-address-badge">
                <span className="dd-zone-chip">{parcel.zoning}</span>
                <span>{parcel.address}</span>
            </div>
            <div className="configurator-grid">
                <div className="config-col-header">Zoning Permits</div>
                <div className="config-col-header">Your Proposal</div>
                <div className="config-col-header config-col-status" />
                {rows.map((r) => {
                    const st = complianceStatus(proposal[r.key], r.permitted);
                    return (
                        <div className="config-row" key={r.key}>
                            <div className="config-label">{r.label}</div>
                            <div className="config-permitted">{r.permitted}</div>
                            <div className="config-proposed">
                                <input type="number" className="config-input" value={proposal[r.key]} onChange={(e) => update(r.key, e.target.value)} placeholder="—" />
                            </div>
                            <div className="config-status">{statusIcon(st)}</div>
                        </div>
                    );
                })}
            </div>
            <div className="dd-card"><div className="dd-card-label">Typology</div><div className="dd-card-value">{zoning.typology}</div></div>
            <div className="dd-card">
                <div className="dd-card-label">Permitted Uses</div>
                <div className="tag-list">{zoning.uses.map((u) => <span key={u} className="tag">{u}</span>)}</div>
            </div>
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
        { label: 'Front Setback', value: `${zoning.frontSetback} m` },
        { label: 'Side Setback', value: `${zoning.sideSetback} m` },
        { label: 'Rear Setback', value: `${zoning.rearSetback} m` },
        { label: 'Max Height', value: `${zoning.maxHeight} m` },
        { label: 'Max FSI', value: `${zoning.maxFsi}` },
        { label: 'Lot Coverage', value: `${zoning.lotCoverage}%` },
        { label: 'Angular Plane', value: zoning.angularPlane },
    ];
    return (
        <>
            <div className="tab-section-header">
                <h3>Building Envelope</h3>
                <p className="tab-section-desc">Physical constraints derived from the local zoning table for zone {parcel.zoning}.</p>
                <p className="tab-section-desc" style={{ marginTop: 8, opacity: 0.8 }}>Envelope values shown here are preliminary and should be verified against official bylaw text.</p>
            </div>
            <div className="massing-grid">
                {envelopeRows.map((r) => (
                    <div className="massing-card" key={r.label}>
                        <div className="massing-label">{r.label}</div>
                        <div className="massing-value">{r.value}</div>
                    </div>
                ))}
            </div>
            <div className="dd-card"><div className="dd-card-label">Lot Area</div><div className="dd-card-value">{hasLotArea ? `${parcel.lotArea} m²` : 'Unavailable'}</div></div>
            <div className="dd-card"><div className="dd-card-label">Max GFA (FSI × Lot Area)</div><div className="dd-card-value">{hasLotArea ? `${(parcel.lotArea * zoning.maxFsi).toFixed(0)} m²` : 'Unavailable without parcel lot area'}</div></div>
        </>
    );
}

function PoliciesTab({ policies, loading }) {
    const [expanded, setExpanded] = useState({});
    const toggle = (idx) => setExpanded((prev) => ({ ...prev, [idx]: !prev[idx] }));
    if (loading) return <div className="tab-section-header"><h3>Policy Extracts</h3><p className="tab-section-desc">Loading applicable policies…</p></div>;
    if (!policies || policies.length === 0) return <div className="tab-section-header"><h3>Policy Extracts</h3><p className="tab-section-desc">No policies found for this parcel.</p></div>;
    return (
        <>
            <div className="tab-section-header"><h3>Policy Extracts</h3><p className="tab-section-desc">Relevant legislation and guidelines for this parcel.</p></div>
            <div className="policy-accordion">
                {policies.map((doc, idx) => (
                    <div key={idx} className={`accordion-item ${expanded[idx] ? 'accordion-open' : ''}`}>
                        <button className="accordion-header" onClick={() => toggle(idx)}>
                            <div className="accordion-title">
                                <svg className="accordion-doc-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
                                <span>{doc.name}</span>
                            </div>
                            <div className="accordion-meta">
                                <span className="accordion-count">{doc.extracts} extracts</span>
                                <svg className="accordion-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9" /></svg>
                            </div>
                        </button>
                        {expanded[idx] && (
                            <div className="accordion-body">
                                {doc.sections.length > 0 ? doc.sections.map((s, si) => (
                                    <div key={si} className="extract-block">
                                        <div className="extract-title">{s.title}</div>
                                        <p className="extract-text">{s.text}</p>
                                    </div>
                                )) : <p className="extract-text" style={{ opacity: 0.5 }}>No clause extracts available for this document.</p>}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </>
    );
}

function DatasetsTab({ overlays, loading }) {
    if (loading) return <div className="tab-section-header"><h3>Data Sources</h3><p className="tab-section-desc">Loading overlays…</p></div>;
    if (!overlays || overlays.length === 0) return <div className="tab-section-header"><h3>Data Sources</h3><p className="tab-section-desc">No overlay datasets found for this parcel.</p></div>;
    return (
        <>
            <div className="tab-section-header"><h3>Data Sources</h3><p className="tab-section-desc">Municipally-verified datasets intersecting this parcel.</p></div>
            <div className="datasets-list">
                {overlays.map((d, idx) => (
                    <div key={idx} className="dataset-row">
                        <div className="dataset-row-left">
                            <svg className="dataset-row-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" /></svg>
                            <div>
                                <div className="dataset-row-name">{d.name}</div>
                                <div className="dataset-row-desc">{d.description}</div>
                            </div>
                        </div>
                        {d.values != null && <div className="dataset-row-meta">{d.values} values</div>}
                    </div>
                ))}
            </div>
        </>
    );
}

function PrecedentsTab({ parcel }) {
    return (
        <div className="tab-section-header">
            <h3>Nearby Applications</h3>
            <p className="tab-section-desc">Precedent search is available after running a scenario for {parcel.address}. Use the chat to generate a development plan.</p>
        </div>
    );
}

function UnresolvedParcelTab({ parcel }) {
    return (
        <div className="tab-empty">
            <p>{parcel.message}</p>
            <p style={{ marginTop: 10, opacity: 0.75 }}>The map can still center this address, but parcel-linked zoning, policy, datasets, precedents, and entitlements stay unavailable until a parcel record is matched.</p>
        </div>
    );
}

function MissingZoningGuidanceTab({ parcel }) {
    return (
        <div className="tab-empty">
            <p>This parcel resolved successfully, but the app does not have a local zoning guidance table for zone <strong>{parcel.zoning || 'unknown'}</strong>.</p>
            <p style={{ marginTop: 10, opacity: 0.75 }}>Policy extracts and datasets may still be available in their tabs, but overview, massing, and entitlement guidance are unavailable here.</p>
        </div>
    );
}

function EntitlementsTab({ parcel, zoning, proposal }) {
    const approvals = useMemo(() => {
        const items = [];
        const check = (label, proposed, max) => {
            const st = complianceStatus(proposed, max);
            if (st === 'ok') items.push({ label, status: 'As-of-Right', cls: 'badge-approved' });
            else if (st === 'variance') items.push({ label, status: 'Minor Variance', cls: 'badge-review' });
            else if (st === 'rezone') items.push({ label, status: 'Rezoning Required', cls: 'badge-refused' });
        };
        check('Height', proposal.height, zoning.maxHeight);
        check('FSI', proposal.fsi, zoning.maxFsi);
        check('Units', proposal.units, zoning.maxUnits);
        check('Lot Coverage', proposal.lotCoverage, zoning.lotCoverage);
        if (items.length === 0) items.push({ label: 'Enter proposal values in Overview tab', status: '—', cls: '' });
        return items;
    }, [proposal, zoning]);

    const handleExport = useCallback(() => {
        const win = window.open('', '_blank');
        win.document.write(`<html><head><title>Preliminary Entitlement Snapshot — ${parcel.address}</title></head><body><h1>Entitlement Snapshot: ${parcel.address}</h1></body></html>`);
        win.document.close();
        win.print();
    }, [parcel, zoning, proposal, approvals]);

    return (
        <>
            <div className="tab-section-header">
                <h3>Entitlements & Report</h3>
                <p className="tab-section-desc">Preliminary approval signal based on your proposal values and the local zoning table.</p>
                <p className="tab-section-desc" style={{ marginTop: 8, opacity: 0.8 }}>This is not a backend entitlement workflow and should be treated as an early-stage estimate only.</p>
            </div>
            <div className="approvals-list">
                {approvals.map((a, idx) => (
                    <div key={idx} className="approval-row">
                        <span className="approval-label">{a.label}</span>
                        {a.cls ? <span className={`precedent-badge ${a.cls}`}>{a.status}</span> : <span className="approval-dash">{a.status}</span>}
                    </div>
                ))}
            </div>
            <button className="export-btn" onClick={handleExport}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
                Export Preliminary Entitlement Snapshot
            </button>
        </>
    );
}

function FinancesTab() {
    return (
        <div className="tab-section-header">
            <h3>Financial Feasibility</h3>
            <p className="tab-section-desc">Financial feasibility is not available in this frontend yet.</p>
            <p className="tab-section-desc" style={{ marginTop: 8, opacity: 0.8 }}>Pro forma analysis and cost modeling will appear here once the UI is wired to scenario-backed backend outputs.</p>
        </div>
    );
}

// ──────────────────── DATA MAPPERS ────────────────────
function mapPolicyStack(data) {
    if (!data) return [];
    const entries = data.applicable_policies || [];
    const byDoc = {};
    for (const entry of entries) {
        const key = entry.document_id || entry.document_title;
        if (!byDoc[key]) byDoc[key] = { name: entry.document_title || entry.doc_type || 'Policy Document', sections: [] };
        if (entry.raw_text || entry.section_ref) byDoc[key].sections.push({ title: entry.section_ref || 'Section', text: entry.raw_text || '' });
    }
    return Object.values(byDoc).map((doc) => ({ ...doc, extracts: doc.sections.length }));
}

function mapOverlays(data) {
    if (!data) return [];
    const byLayer = {};
    for (const o of (data.overlays || [])) {
        const key = o.layer_id || o.layer_name || o.layer_type;
        if (!byLayer[key]) byLayer[key] = { name: o.layer_name || o.name || o.layer_type || 'Dataset', description: o.source_url ? `Source: ${o.source_url}` : (o.layer_type || ''), count: 0 };
        byLayer[key].count += 1;
    }
    return Object.values(byLayer).map((l) => ({ name: l.name, description: l.description, values: l.count }));
}

// ──────────────────── MAIN PANEL ────────────────────
const TAB_TITLES = {
    overview: 'Project Overview', massing: 'Building Massing', finances: 'Financial Analysis',
    entitlements: 'Entitlements', policies: 'Policy Extracts', datasets: 'Data Sources', precedents: 'Precedents',
};

export default function PolicyPanel({ parcel, isOpen, onClose, activeNav, savedParcels, onSaveParcel }) {
    const [proposal, setProposal] = useState({ height: '', fsi: '', units: '', lotCoverage: '' });
    const [policies, setPolicies] = useState([]);
    const [overlays, setOverlays] = useState([]);
    const [loadingPolicies, setLoadingPolicies] = useState(false);
    const [loadingOverlays, setLoadingOverlays] = useState(false);
    const [panelWidth, setPanelWidth] = useState(DEFAULT_PANEL_WIDTH);
    const [isResizing, setIsResizing] = useState(false);
    const startXRef = useRef(null);
    const startWidthRef = useRef(null);

    // ── Keep CSS variable in sync so chat panel "right: var(--panel-width)" stays correct ──
    useEffect(() => {
        document.documentElement.style.setProperty('--panel-width', `${panelWidth}px`);
    }, [panelWidth]);

    // ── Kill transitions during drag so chat bar moves in lockstep ────────────
    useEffect(() => {
        const style = document.createElement('style');
        style.id = 'no-layout-transition';
        if (isResizing) {
            style.textContent = `#sidebar, #search-container, #chat-panel, #policy-panel, .panel-reopen-tab { transition: none !important; }`;
            document.head.appendChild(style);
        }
        return () => { document.getElementById('no-layout-transition')?.remove(); };
    }, [isResizing]);

    // ── Drag-to-resize from left edge ─────────────────────────────────────────
    const handleResizeStart = useCallback((e) => {
        e.preventDefault();
        setIsResizing(true);
        startXRef.current = e.clientX;
        startWidthRef.current = panelWidth;
    }, [panelWidth]);

    useEffect(() => {
        if (!isResizing) return;
        const onMove = (e) => {
            const delta = startXRef.current - e.clientX; // drag left = wider
            const newWidth = Math.min(MAX_PANEL_WIDTH, Math.max(MIN_PANEL_WIDTH, startWidthRef.current + delta));
            setPanelWidth(newWidth);
        };
        const onUp = () => setIsResizing(false);
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        return () => {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        };
    }, [isResizing]);

    // ── Live data ─────────────────────────────────────────────────────────────
    useEffect(() => {
        if (!isResolvedParcel(parcel)) return undefined;
        let cancelled = false;
        queueMicrotask(() => { if (!cancelled) { setLoadingPolicies(true); setLoadingOverlays(true); } });
        getPolicyStack(parcel.id)
            .then((d) => { if (!cancelled) setPolicies(mapPolicyStack(d)); })
            .catch(() => { if (!cancelled) setPolicies([]); })
            .finally(() => { if (!cancelled) setLoadingPolicies(false); });
        getParcelOverlays(parcel.id)
            .then((d) => { if (!cancelled) setOverlays(mapOverlays(d)); })
            .catch(() => { if (!cancelled) setOverlays([]); })
            .finally(() => { if (!cancelled) setLoadingOverlays(false); });
        return () => { cancelled = true; };
    }, [parcel]);

    const zoning = useMemo(() => {
        if (!isResolvedParcel(parcel) || !parcel?.zoning) return null;
        return ZONING_DATA[parcel.zoning] || null;
    }, [parcel]);

    const visiblePolicies = isResolvedParcel(parcel) ? policies : [];
    const visibleOverlays = isResolvedParcel(parcel) ? overlays : [];
    const visiblePoliciesLoading = isResolvedParcel(parcel) ? loadingPolicies : false;
    const visibleOverlaysLoading = isResolvedParcel(parcel) ? loadingOverlays : false;

    const renderTab = () => {
        if (!parcel) return <div className="tab-empty"><p>Search for a property to view due diligence information.</p></div>;
        if (isUnresolvedParcel(parcel)) return <UnresolvedParcelTab parcel={parcel} />;
        if (!zoning && ['overview', 'massing', 'entitlements'].includes(activeNav)) return <MissingZoningGuidanceTab parcel={parcel} />;
        switch (activeNav) {
            case 'overview': return <OverviewTab parcel={parcel} zoning={zoning} proposal={proposal} setProposal={setProposal} />;
            case 'massing': return <MassingTab zoning={zoning} parcel={parcel} />;
            case 'policies': return <PoliciesTab policies={visiblePolicies} loading={visiblePoliciesLoading} />;
            case 'datasets': return <DatasetsTab overlays={visibleOverlays} loading={visibleOverlaysLoading} />;
            case 'precedents': return <PrecedentsTab parcel={parcel} />;
            case 'entitlements': return <EntitlementsTab parcel={parcel} zoning={zoning} proposal={proposal} />;
            case 'finances': return <FinancesTab />;
            default: return <OverviewTab parcel={parcel} zoning={zoning} proposal={proposal} setProposal={setProposal} />;
        }
    };

    return (
        <aside
            id="policy-panel"
            className={isOpen ? '' : 'panel-hidden'}
            style={{ userSelect: isResizing ? 'none' : undefined }}
        >
            {/* Left drag handle — offset onto the border so no visible line inside panel */}
            <div
                onMouseDown={handleResizeStart}
                onMouseEnter={e => { if (!isResizing) e.currentTarget.style.background = 'rgba(200,165,92,0.15)'; }}
                onMouseLeave={e => { if (!isResizing) e.currentTarget.style.background = 'transparent'; }}
                style={{
                    position: 'absolute',
                    left: -2,
                    top: 0,
                    bottom: 0,
                    width: 4,
                    cursor: 'col-resize',
                    zIndex: 20,
                    background: isResizing ? 'rgba(200,165,92,0.3)' : 'transparent',
                    transition: 'background 0.15s',
                }}
            />

            <div id="policy-panel-header">
                <h2 id="policy-panel-title">{TAB_TITLES[activeNav] || 'Project Information'}</h2>
                <div className="panel-header-actions">
                    {isResolvedParcel(parcel) && onSaveParcel && (
                        <button className="panel-save-btn" onClick={() => onSaveParcel(parcel)} title="Save parcel for comparison">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" /></svg>
                        </button>
                    )}
                    <button id="policy-panel-close" aria-label="Close panel" onClick={onClose}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                    </button>
                </div>
            </div>

            <div id="policy-panel-content">
                {savedParcels && savedParcels.length > 0 && (
                    <div className="saved-parcels-strip">
                        <div className="saved-parcels-label">Saved Parcels</div>
                        <div className="saved-parcels-list">
                            {savedParcels.map((sp, idx) => (
                                <div key={idx} className="saved-parcel-chip">
                                    <span className="saved-parcel-zone">{sp.zoning || '—'}</span>
                                    <span className="saved-parcel-addr">{sp.address?.split(',')[0]}</span>
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