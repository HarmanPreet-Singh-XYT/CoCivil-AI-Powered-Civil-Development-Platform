import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getParcelOverlays, getParcelZoningAnalysis, getPolicyStack, getNearbyApplications, getParcelFinancialSummary, uploadDocument, getUpload, getPlanDocuments, regeneratePlanDocument } from '../api.js';
import { isResolvedParcel, isUnresolvedParcel } from '../lib/parcelState.js';
import useResizable from '../hooks/useResizable.js';

// ─── Pipeline engineering decision panel ──────────────────────────────────────

const MATERIAL_LABELS = {
    CI: 'Cast Iron', CICL: 'Cast Iron Lined', DIP: 'Ductile Iron', DICL: 'Ductile Iron Lined',
    PVC: 'PVC (Polyvinyl Chloride)', CPP: 'Corrugated Plastic', AC: 'Asbestos Cement',
    COP: 'Copper', UNK: 'Unknown',
};
const MATERIAL_COLORS = {
    CI: '#e67e22', CICL: '#e67e22', DIP: '#2277bb', DICL: '#2277bb',
    PVC: '#27ae60', CPP: '#27ae60', AC: '#e74c3c', COP: '#f1c40f', UNK: '#888',
};

// ── Engineering computations ──────────────────────────────────────────────────

/** Hazen-Williams C-factor adjusted for material age */
function hwCFactor(mat, age) {
    const a = age || 0;
    switch (mat) {
        case 'CI': return Math.max(40, 130 - a * 0.55);
        case 'CICL': return Math.max(80, 130 - a * 0.35);
        case 'DIP': return Math.max(100, 140 - a * 0.20);
        case 'DICL': return Math.max(110, 140 - a * 0.15);
        case 'PVC': return 150;
        case 'CPP': return 140;
        case 'AC': return Math.max(80, 140 - a * 0.30);
        case 'COP': return 130;
        default: return 100;
    }
}

/** Hazen-Williams: flow rate (L/s) for a full pipe at given slope S (m/m) */
function hwFlow(diamMm, C, S = 0.002) {
    const D = diamMm / 1000;
    const R = D / 4;
    const V = 0.8492 * C * Math.pow(R, 0.63) * Math.pow(S, 0.54);
    const A = Math.PI * Math.pow(D / 2, 2);
    return V * A * 1000; // L/s
}

/** Pressure drop kPa per 100 m */
function hwPressureDrop(diamMm, C, flowLs) {
    const D = diamMm / 1000;
    const A = Math.PI * Math.pow(D / 2, 2);
    const V = (flowLs / 1000) / A;
    const R = D / 4;
    const S = Math.pow(V / (0.8492 * C * Math.pow(R, 0.63)), 1 / 0.54);
    return S * 9.81 * 1000 * 100; // kPa/100m
}

/** Break probability breaks/km/year */
function breakProb(mat, age) {
    const a = age || 0;
    if (mat === 'AC') return 0.8;
    if (mat === 'CI' || mat === 'CICL') {
        if (a > 100) return 1.8;
        if (a > 75) return 0.9;
        if (a > 50) return 0.45;
        return 0.18;
    }
    if (mat === 'DIP' || mat === 'DICL') {
        if (a > 60) return 0.22;
        if (a > 30) return 0.10;
        return 0.05;
    }
    if (mat === 'PVC' || mat === 'CPP') {
        if (a > 40) return 0.08;
        return 0.02;
    }
    return 0.3;
}

/** Expected remaining service life (years) */
function remainingLife(mat, age) {
    const a = age || 0;
    const typicalLife = { CI: 100, CICL: 110, DIP: 100, DICL: 120, PVC: 80, CPP: 70, AC: 50, COP: 80, UNK: 70 };
    const life = typicalLife[mat] || 70;
    return Math.max(0, life - a);
}

/** Replacement cost estimate (CAD) */
function replacementCost(diamMm, lengthM) {
    if (!lengthM) return null;
    const d = diamMm || 150;
    // Open-cut cost $/m: scales roughly with diameter
    const costPerM = d <= 150 ? 1200 : d <= 300 ? 1800 : d <= 600 ? 2600 : 3500;
    return costPerM * lengthM;
}

/** Condition severity */
function pipeCondition(mat, installYear) {
    const age = installYear ? (2026 - installYear) : null;
    if (mat === 'AC') return { label: 'Critical — Hazardous Material', color: '#e74c3c', risk: 'critical' };
    if (!age) return { label: 'Unknown', color: '#888', risk: 'unknown' };
    const bp = breakProb(mat, age);
    if (bp >= 1.0) return { label: 'Critical — End of Service Life', color: '#e74c3c', risk: 'critical' };
    if (bp >= 0.45) return { label: 'High Risk', color: '#e67e22', risk: 'high' };
    if (bp >= 0.15) return { label: 'Moderate Risk', color: '#f1c40f', risk: 'moderate' };
    return { label: 'Good Condition', color: '#27ae60', risk: 'good' };
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Section({ title, icon, children, defaultOpen = true, accent }) {
    const [open, setOpen] = React.useState(defaultOpen);
    return (
        <div style={{ marginBottom: 12, border: '1px solid #2a2a2a', borderRadius: 8, overflow: 'hidden' }}>
            <button
                onClick={() => setOpen(o => !o)}
                style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                    padding: '9px 14px', background: '#1e1e1e', border: 'none', cursor: 'pointer',
                    color: '#f0ece4', fontSize: 12, fontWeight: 600, textAlign: 'left',
                    borderBottom: open ? '1px solid #2a2a2a' : 'none',
                }}
            >
                <span style={{ fontSize: 14 }}>{icon}</span>
                <span style={{ flex: 1, letterSpacing: 0.3 }}>{title}</span>
                {accent && <span style={{ fontSize: 11, color: accent.color, fontWeight: 700 }}>{accent.text}</span>}
                <span style={{ color: '#555', fontSize: 10 }}>{open ? '▲' : '▼'}</span>
            </button>
            {open && <div style={{ background: '#161616', padding: '12px 14px' }}>{children}</div>}
        </div>
    );
}

function Row({ label, value, highlight, mono }) {
    return (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '5px 0', borderBottom: '1px solid #222' }}>
            <span style={{ color: '#888', fontSize: 12 }}>{label}</span>
            <span style={{ color: highlight || '#f0ece4', fontSize: 12, fontFamily: mono ? 'monospace' : undefined, textAlign: 'right', maxWidth: '60%' }}>{value}</span>
        </div>
    );
}

function Bar({ value, max, color }) {
    const pct = Math.min(100, Math.round((value / max) * 100));
    return (
        <div style={{ background: '#2a2a2a', borderRadius: 4, height: 6, width: '100%', overflow: 'hidden' }}>
            <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 4, transition: 'width 0.4s' }} />
        </div>
    );
}

function Pill({ text, color }) {
    return (
        <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 5, padding: '2px 8px',
            background: `${color}22`, border: `1px solid ${color}55`, borderRadius: 4,
            fontSize: 11, color, fontWeight: 600,
        }}>{text}</span>
    );
}

function Checklist({ items }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {items.map(({ done, text, sub, urgent }) => (
                <div key={text} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                    <span style={{ fontSize: 13, marginTop: 1, color: urgent ? '#e74c3c' : done ? '#27ae60' : '#888', flexShrink: 0 }}>
                        {urgent ? '⚠' : done ? '✓' : '○'}
                    </span>
                    <div>
                        <div style={{ fontSize: 12, color: urgent ? '#e74c3c' : done ? '#ccc' : '#f0ece4' }}>{text}</div>
                        {sub && <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>{sub}</div>}
                    </div>
                </div>
            ))}
        </div>
    );
}

function PipelineAssetPanel({ asset }) {
    const mat = asset.material || 'UNK';
    const color = MATERIAL_COLORS[mat] || '#888';
    const matLabel = MATERIAL_LABELS[mat] || mat;
    const age = asset.install_year ? (2026 - asset.install_year) : null;
    const diam = asset.diameter_mm || 150;
    const cond = pipeCondition(mat, asset.install_year);

    // Hydraulic
    const C = hwCFactor(mat, age);
    const C_new = hwCFactor(mat, 0);
    const flowNow = hwFlow(diam, C);
    const flowNew = hwFlow(diam, C_new);
    const flowPct = Math.round((flowNow / flowNew) * 100);
    const dpNow = hwPressureDrop(diam, C, flowNow * 0.6);

    // Risk
    const bp = breakProb(mat, age);
    const rl = remainingLife(mat, age);
    const cost = replacementCost(diam, asset.length_m);

    // Material replacement recommendation
    const replaceMat = mat === 'AC' ? 'HDPE (mandatory — asbestos protocol applies)' :
        (mat === 'CI' || mat === 'CICL') ? 'HDPE (trenchless CIPP lining) or DIP (open-cut)' :
            mat === 'PVC' ? 'HDPE or DICL for higher pressure classes' :
                'DIP or HDPE';

    const permitItems = [
        { done: false, text: 'Toronto Water — Watermain Construction Approval', sub: 'Submit CCTV, hydraulic model, and design drawings' },
        { done: false, text: 'ROW Permit — Transportation Services', sub: 'Required for any excavation in road allowance; notify TTC/Metrolinx' },
        { done: false, text: 'Ontario Reg. 170/03 — Drinking Water System Permit to Take Water', sub: 'If service area or demand changes' },
        ...(mat === 'AC' ? [{ done: false, urgent: true, text: 'Ontario Reg. 278/05 — Designated Substance (Asbestos)', sub: 'Asbestos abatement plan required before any disturbance' }] : []),
        { done: false, text: 'Building Permit — City of Toronto', sub: 'For appurtenances, chambers, or connections' },
        { done: false, text: 'TRCA Permit — if within 30 m of watercourse or regulated area', sub: 'Check Toronto Greenspace Map before design' },
        { done: false, text: 'Class Environmental Assessment', sub: 'Required if capital cost > $2M or if new trunk main (Municipal Class EA)' },
    ];

    const geoItems = [
        { done: true, text: `Min burial depth: 1.8 m to top of pipe (Toronto frost line)`, sub: 'OPSD 802.010 — deeper in areas with heavy traffic loading' },
        { done: false, text: 'Bedding Class B required (granular material, compacted to 95% proctor)', sub: 'OPSD 802.030 — haunching to spring line minimum' },
        { done: false, text: 'Ground Penetrating Radar (GPR) survey before excavation', sub: 'Identify fibre, power, gas and sewer conflicts within 3 m corridor' },
        { done: false, text: 'Geotechnical borehole — 1 per 100 m for urban route', sub: 'Assess bearing capacity, groundwater depth, and corrosivity index' },
        { done: false, text: 'Trench stability analysis if depth > 1.2 m', sub: 'Ontario Reg. 213/91 (Construction Projects) — shoring required' },
        ...(mat === 'CI' || mat === 'AC' ? [{ done: false, urgent: true, text: 'Soil corrosivity assessment', sub: 'Resistivity < 2,000 Ω·cm = highly corrosive — cathodic protection required for metal pipe' }] : []),
    ];

    return (
        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#c8c4bc', overflowY: 'auto', height: '100%' }}>

            {/* ── Header ── */}
            <div style={{ padding: '16px 16px 14px', borderBottom: '1px solid #1e1e1e' }}>
                <div style={{ fontSize: 10, color: '#484848', textTransform: 'uppercase', letterSpacing: 1.2, marginBottom: 6 }}>
                    Water Main · {matLabel} · {asset.asset_id || '—'}
                </div>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#e8e4dc', letterSpacing: -0.3, lineHeight: 1.2 }}>
                    {asset.location || 'Unnamed Segment'}
                </div>
                <div style={{ marginTop: 8, fontSize: 11, color: '#484848' }}>{cond.label}</div>
            </div>

            {/* ── Specs strip ── */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', borderBottom: '1px solid #1e1e1e' }}>
                {[
                    { label: 'Diameter', value: diam ? `${diam}mm` : '—', sub: diam ? `${(diam / 25.4).toFixed(0)}"` : '' },
                    { label: 'Material', value: mat, sub: null },
                    { label: 'Installed', value: asset.install_year || '—', sub: age ? `${age} yrs` : null },
                    { label: 'Length', value: asset.length_m ? `${Math.round(asset.length_m)}m` : '—', sub: null },
                ].map(({ label, value, sub }, i) => (
                    <div key={label} style={{
                        padding: '10px 8px', textAlign: 'center',
                        borderRight: i < 3 ? '1px solid #1e1e1e' : 'none',
                    }}>
                        <div style={{ fontSize: 9, color: '#404040', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 4 }}>{label}</div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: '#bab6ae' }}>{value}</div>
                        {sub && <div style={{ fontSize: 9, color: '#404040', marginTop: 2 }}>{sub}</div>}
                    </div>
                ))}
            </div>

            <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: 24 }}>

                {/* ── Hydraulic Performance ── */}
                <div>
                    <div style={{ fontSize: 10, color: '#484848', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
                        Hydraulic Performance
                    </div>

                    <div style={{ marginBottom: 14 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                            <span style={{ fontSize: 11, color: '#555' }}>Carrying capacity vs. new pipe</span>
                            <span style={{ fontSize: 11, color: '#888', fontFamily: 'monospace' }}>{flowPct}% · C={Math.round(C)}/{Math.round(C_new)}</span>
                        </div>
                        <div style={{ background: '#1e1e1e', borderRadius: 3, height: 4, overflow: 'hidden' }}>
                            <div style={{ width: `${flowPct}%`, height: '100%', background: '#484848', borderRadius: 3, transition: 'width 0.4s ease' }} />
                        </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, background: '#1a1a1a' }}>
                        {[
                            { label: 'Flow Capacity', value: `${flowNow.toFixed(1)} L/s`, sub: `${flowPct}% of design` },
                            { label: 'Design Flow (new)', value: `${flowNew.toFixed(1)} L/s`, sub: 'theoretical max' },
                            { label: 'Pressure Drop', value: `${dpNow.toFixed(0)} kPa/100m`, sub: 'at 60% flow' },
                            { label: 'Flow Velocity', value: `${(flowNow / 1000 / (Math.PI * Math.pow(diam / 2000, 2))).toFixed(2)} m/s`, sub: 'at design flow' },
                        ].map(({ label, value, sub }) => (
                            <div key={label} style={{ padding: '10px 12px', background: '#131313' }}>
                                <div style={{ fontSize: 9, color: '#404040', textTransform: 'uppercase', letterSpacing: 0.7, marginBottom: 5 }}>{label}</div>
                                <div style={{ fontSize: 15, fontWeight: 600, color: '#c8c4bc' }}>{value}</div>
                                <div style={{ fontSize: 10, color: '#404040', marginTop: 3 }}>{sub}</div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* ── Structural Risk ── */}
                <div>
                    <div style={{ fontSize: 10, color: '#484848', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
                        Structural Risk
                    </div>

                    <div style={{ marginBottom: 14 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                            <span style={{ fontSize: 11, color: '#555' }}>Break probability (critical ≥ 1.5/km/yr)</span>
                            <span style={{ fontSize: 11, color: '#888', fontFamily: 'monospace' }}>{bp.toFixed(2)}</span>
                        </div>
                        <div style={{ background: '#1e1e1e', borderRadius: 3, height: 4, overflow: 'hidden' }}>
                            <div style={{ width: `${Math.min(100, (bp / 1.5) * 100)}%`, height: '100%', background: '#484848', borderRadius: 3, transition: 'width 0.4s ease' }} />
                        </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, background: '#1a1a1a', marginBottom: (mat === 'AC' || ((mat === 'CI' || mat === 'CICL') && age > 80)) ? 10 : 0 }}>
                        {[
                            { label: 'Condition', value: cond.label },
                            { label: 'Annual Breaks', value: asset.length_m ? `${(bp * asset.length_m / 1000).toFixed(2)}/yr` : `${bp.toFixed(2)}/km`, sub: 'this segment' },
                            { label: 'Remaining Life', value: rl > 0 ? `~${rl} yrs` : 'Expired', sub: rl <= 0 ? 'Past design life' : null },
                            { label: 'Replace Cost', value: cost ? `$${(cost / 1000).toFixed(0)}K–$${(cost * 1.8 / 1000).toFixed(0)}K` : '—', sub: 'CAD estimated' },
                        ].map(({ label, value, sub }) => (
                            <div key={label} style={{ padding: '10px 12px', background: '#131313' }}>
                                <div style={{ fontSize: 9, color: '#404040', textTransform: 'uppercase', letterSpacing: 0.7, marginBottom: 5 }}>{label}</div>
                                <div style={{ fontSize: 13, fontWeight: 600, color: '#c8c4bc', lineHeight: 1.3 }}>{value}</div>
                                {sub && <div style={{ fontSize: 10, color: '#404040', marginTop: 3 }}>{sub}</div>}
                            </div>
                        ))}
                    </div>

                    {(mat === 'AC' || ((mat === 'CI' || mat === 'CICL') && age > 80)) && (
                        <div style={{ padding: '9px 12px', background: '#1a1a1a', borderLeft: '2px solid #555', fontSize: 11, color: '#888', lineHeight: 1.6 }}>
                            {mat === 'AC' && 'Asbestos Cement — Reg. 278/05 applies. Designated Substance Report required before any disturbance.'}
                            {(mat === 'CI' || mat === 'CICL') && age > 80 && `Cast Iron ${age} yrs — CIRC Bulletin recommends replacement assessment.`}
                        </div>
                    )}
                </div>

                {/* ── Geotechnical ── */}
                <div>
                    <div style={{ fontSize: 10, color: '#484848', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
                        Geotechnical Requirements
                    </div>
                    <Checklist items={geoItems} />
                    <div style={{ marginTop: 10, fontSize: 11, color: '#484848', lineHeight: 1.8 }}>
                        <div>Toronto soil: lakebed clays below ~3 m (high corrosivity), glaciofluvial sands near surface, groundwater at 1–2 m in lakefront wards.</div>
                    </div>
                </div>

                {/* ── Permitting ── */}
                <div>
                    <div style={{ fontSize: 10, color: '#484848', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
                        Permitting Pathway
                    </div>
                    <Checklist items={permitItems} />
                    <div style={{ marginTop: 10, fontSize: 11, color: '#484848', lineHeight: 1.8 }}>
                        <div>Toronto Water approval 3–6 mo · ROW permit 4–8 wk · Class EA (if &gt;$2M) 12–18 mo · TRCA 2–4 mo</div>
                    </div>
                </div>

                {/* ── Material Selection ── */}
                <div>
                    <div style={{ fontSize: 10, color: '#484848', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
                        Material Selection
                    </div>
                    <div style={{ fontSize: 11, color: '#555', marginBottom: 12, lineHeight: 1.5 }}>
                        Recommended: <span style={{ color: '#888' }}>{replaceMat}</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 1, background: '#1a1a1a' }}>
                        {[
                            { mat: 'HDPE', c: 150, life: 100, cost: '$900–1,400/m' },
                            { mat: 'DIP', c: 140, life: 100, cost: '$1,100–1,800/m' },
                            { mat: 'DICL', c: 140, life: 120, cost: '$1,200–2,000/m' },
                            { mat: 'PVC', c: 150, life: 80, cost: '$700–1,100/m' },
                        ].map(({ mat: m, c, life, cost: co }) => (
                            <div key={m} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: '#131313' }}>
                                <span style={{ fontSize: 12, fontWeight: 600, color: '#888' }}>{m}</span>
                                <span style={{ fontSize: 11, color: '#484848' }}>C={c} · {life} yr · {co}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* ── Environmental ── */}
                <div style={{ paddingBottom: 16 }}>
                    <div style={{ fontSize: 10, color: '#484848', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
                        Environmental Flags
                    </div>
                    <Checklist items={[
                        { done: false, text: 'TRCA Regulated Area mapping', sub: 'Required if within 30 m of watercourse or valley land' },
                        { done: false, text: 'Stage 1 Archaeological Assessment', sub: 'Ontario Heritage Act — greenspace routes only' },
                        { done: false, text: 'Species at Risk screening (MNRF)', sub: 'Required for any EA project class' },
                        ...(mat === 'AC' ? [{ done: false, urgent: true, text: 'Asbestos Waste Disposal Plan', sub: 'Reg. 347 — designated waste, licensed hauler only' }] : []),
                        { done: false, text: 'Construction dewatering permit', sub: 'TRCA permit to take water if groundwater encountered' },
                        { done: false, text: 'Spill Prevention and Response Plan', sub: 'Required for all fuel/chemical storage on site' },
                    ]} />
                </div>

            </div>
        </div>
    );
}

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

function OverviewTab({ parcel, zoning, onUploadComplete }) {
    const zoneName = zoneDisplay(parcel, zoning);

    return (
        <>
            <FileUploadZone onUploadComplete={onUploadComplete} />

            <div className="dd-address-badge" style={{ marginTop: 16 }}>
                <span className="dd-zone-chip">{zoning.zoneCategory || parcel.zoning || '—'}</span>
                <span>{parcel.address}</span>
            </div>

            <div className="tab-section-header">
                <h3>Zoning Summary</h3>
                <p className="tab-section-desc">Backend zoning analysis for {zoneName}.</p>
            </div>

            <div className="dd-card">
                <div className="dd-card-label">Zone Classification</div>
                <div className="dd-card-value">{zoning.label}</div>
            </div>
            <div className="dd-card">
                <div className="dd-card-label">By-law Reference</div>
                <div className="dd-card-value">{formatMetric(zoning.bylawSection, '', 'Unavailable')}</div>
            </div>

            <div className="zoning-limits-grid">
                {[
                    { label: 'Max Height', value: formatMetric(zoning.maxHeight, ' m') },
                    { label: 'Max FSI', value: formatMetric(zoning.maxFsi) },
                    { label: 'Max Storeys', value: formatMetric(zoning.maxStoreys) },
                    { label: 'Lot Coverage', value: formatMetric(zoning.lotCoverage, '%') },
                ].map((item) => (
                    <div key={item.label} className="zoning-limit-card">
                        <div className="dd-card-label">{item.label}</div>
                        <div className="dd-card-value">{item.value}</div>
                    </div>
                ))}
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
                                        <div className="extract-text extract-markdown">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.text}</ReactMarkdown>
                                        </div>
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
            .catch(() => { })
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
            const rawName = entry.document_title || entry.doc_type || 'Policy Document';
            const fileName = rawName.includes('/') ? rawName.split('/').pop() : rawName;
            byDoc[key] = {
                name: fileName,
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
    finances: 'Financial Analysis',
    policies: 'Policy Extracts',
    datasets: 'Data Sources',
    precedents: 'Precedents',
    documents: 'Documents',
    standards: 'Design Standards',
    network: 'Pipeline Network',
    inspections: 'Inspection Records',
};

const ZONING_TABS = new Set(['overview']);

function InfraStandardsTab({ asset }) {
    const [expanded, setExpanded] = React.useState({ applicable: true, opss: false, awwa: false, csa: false, toronto: false });
    const toggle = (k) => setExpanded(p => ({ ...p, [k]: !p[k] }));
    const Badge = ({ t, c }) => <span className="policy-badge" style={c ? { background: `${c}22`, color: c } : undefined}>{t}</span>;

    const mat = (asset?.material || '').toUpperCase();
    const dia = asset?.diameter_mm;
    const year = asset?.install_year;
    const age = year ? new Date().getFullYear() - year : null;

    // Material-specific applicable standards
    const applicable = [];
    if (mat.includes('CI') || mat.includes('CAST')) {
        applicable.push({ badge: 'RISK', title: 'Cast Iron — Graphitization & Corrosion', desc: `CI pipes lose tensile strength through graphitic corrosion. Age: ${age ?? '?'} years. CI pipes >60 years have 3–5x break rate vs DI. Polyethylene encasement NOT effective retroactively.`, color: '#e74c3c' });
        applicable.push({ badge: 'OPSS', title: 'OPSS.MUNI 491 — Pipe Abandonment', desc: 'When CI replacement is triggered, old main must be grouted per OPSS 491. CLSM fill required.', color: '#2277bb' });
        applicable.push({ badge: 'ECS', title: 'TS 441 — Cathodic Protection', desc: 'CI mains in soils <2,000 Ω·cm require cathodic protection. Sacrificial Mg anodes per Toronto ECS.', color: '#e67e22' });
    }
    if (mat.includes('DI') || mat.includes('DUCTILE')) {
        applicable.push({ badge: 'AWWA', title: 'C151/A21.51 — Ductile-Iron Pipe', desc: `DI pipe ${dia ? dia + ' mm' : ''}. Pressure classes 150–350. Standard lining: cement mortar. External: polyethylene encasement in corrosive soils.`, color: '#27ae60' });
        applicable.push({ badge: 'AWWA', title: 'C600 — DI Pipe Installation', desc: `Leakage formula: L = ND√P / 7,400. For ${dia || '?'} mm pipe at 1,035 kPa: L = ${dia ? Math.round(1 * dia * Math.sqrt(1035) / 7400) : '?'} mL/hr allowable.`, color: '#27ae60' });
        applicable.push({ badge: 'ECS', title: 'TS 441 — Polyethylene Encasement', desc: 'Required for all DI in Toronto where soil resistivity <2,000 Ω·cm.', color: '#e67e22' });
    }
    if (mat.includes('PVC')) {
        applicable.push({ badge: 'AWWA', title: 'C900 — PVC Pressure Pipe', desc: `DR 18 standard (1,620 kPa rating). ${dia || '?'} mm. Typical for distribution 100–300 mm. UV-sensitive — must be stored covered.`, color: '#27ae60' });
        applicable.push({ badge: 'CSA', title: 'CSA B137.3 — PVC Pipe & Fittings', desc: 'Dimensional and material requirements for rigid PVC pressure pipe in cold water service.', color: '#9b59b6' });
    }
    if (mat.includes('AC') || mat.includes('ASBESTOS') || mat.includes('CEMENT')) {
        applicable.push({ badge: 'RISK', title: 'Asbestos Cement — Regulated Material', desc: `AC pipe requires O.Reg 278/05 handling. ${age ?? '?'} years old. Brittle failure mode. No repair — replacement only. Contractor must be licensed.`, color: '#e74c3c' });
        applicable.push({ badge: 'MOL', title: 'O.Reg 278/05 — Asbestos on Construction', desc: 'Type 3 asbestos operation for cutting/breaking AC pipe. Air monitoring, decontamination, disposal at licensed facility.', color: '#e74c3c' });
    }
    if (mat.includes('COP') || mat.includes('COPPER')) {
        applicable.push({ badge: 'CSA', title: 'CSA B137 Series — Copper Service', desc: `Copper service line ${dia || '?'} mm. Typical 19–50 mm for residential. Lead-free solder mandatory (post-1990).`, color: '#9b59b6' });
    }
    if (mat.includes('HDPE') || mat.includes('PE')) {
        applicable.push({ badge: 'AWWA', title: 'C906 — HDPE Pipe for Water', desc: 'Heat-fusion joints only. PE4710. Suitable for trenchless (pipe bursting, HDD).', color: '#27ae60' });
    }
    // Always applicable
    applicable.push({ badge: 'AWWA', title: 'C651 — Disinfection of Water Mains', desc: '25 mg/L chlorine, 24-hour hold, flush to ≤2.0 mg/L free residual before commissioning. Required for all new/repaired mains.', color: '#27ae60' });
    applicable.push({ badge: 'NSF', title: 'NSF/ANSI 61 — Drinking Water Contact', desc: 'Mandatory under O.Reg 170/03 for all pipe, lining, and coating materials in potable water systems.', color: '#9b59b6' });

    if (age && age > 50) {
        applicable.push({ badge: 'ECS', title: 'TS 7.60 — CIPP Lining (Rehab Option)', desc: `At ${age} years, this main may be a CIPP candidate. Min 6.5 mm wall. Pre/post CCTV mandatory. 50-year design life extension.`, color: '#e67e22' });
    }

    const allStandards = {
        opss: {
            label: 'Ontario Provincial Standards (OPSS / OPSD)',
            items: [
                { badge: 'OPSS', title: 'OPSS.MUNI 441 — Watermain Installation in Open Cut', desc: 'Test at 1.5x working pressure or 1,035 kPa min; 2-hour hold. Bedding min 150 mm. 1.5 m min cover. 3.0 m separation from sanitary.' },
                { badge: 'OPSS', title: 'OPSS.MUNI 491 — Pipe Abandonment', desc: 'CLSM/cellular grout fill required. As-built recording and GIS update.' },
                { badge: 'OPSS', title: 'OPSS.MUNI 493 — Watermain CIPP Lining', desc: 'Pre/post CCTV mandatory. NSF/ANSI 61 certified liner. Design per ASTM F1216.' },
                { badge: 'OPSD', title: 'OPSD 806.010 — Bedding and Trench Backfill', desc: 'Granular bedding zones with haunch support to spring line. Class B bedding.' },
            ]
        },
        awwa: {
            label: 'AWWA Standards',
            items: [
                { badge: 'AWWA', title: 'C151/A21.51 — Ductile-Iron Pipe', desc: '80–1,600 mm. Pressure classes 150–350.' },
                { badge: 'AWWA', title: 'C900 — PVC Pressure Pipe', desc: 'DR 18 (1,620 kPa). 100–300 mm distribution.' },
                { badge: 'AWWA', title: 'C906 — HDPE Pipe', desc: 'Heat-fusion joints. Trenchless applications.' },
                { badge: 'AWWA', title: 'C600 — DI Installation', desc: 'Leakage formula: L = ND√P / 7,400.' },
                { badge: 'AWWA', title: 'C651 — Disinfection', desc: '25 mg/L Cl₂, 24-hr hold.' },
            ]
        },
        csa: {
            label: 'CSA & NSF Standards',
            items: [
                { badge: 'CSA', title: 'CSA B137.3 — PVC Pipe', desc: 'Rigid PVC pressure pipe for cold water.' },
                { badge: 'CSA', title: 'CSA B137.1 — HDPE Pipe', desc: 'PE4710 material designation.' },
                { badge: 'NSF', title: 'NSF/ANSI 61 — Drinking Water Contact', desc: 'Mandatory under O.Reg 170/03.' },
            ]
        },
        toronto: {
            label: 'Toronto ECS',
            items: [
                { badge: 'ECS', title: 'TS 441 — Watermain Installation', desc: 'Max 150 m hydrant spacing. Cathodic protection in soils <2,000 Ω·cm.' },
                { badge: 'ECS', title: 'TS 7.60 — CIPP Lining', desc: 'Min 6.5 mm wall. Pre/post CCTV. 50-year design life.' },
                { badge: 'ECS', title: 'Chapter 6 — Approved Materials', desc: 'Only listed products on Toronto Water projects.' },
            ]
        }
    };

    return (
        <div className="tab-section" style={{ padding: '0 4px' }}>
            {asset && applicable.length > 0 && (
                <div style={{ marginBottom: 10, border: '1px solid #2a2a2a', borderRadius: 8, overflow: 'hidden' }}>
                    <button onClick={() => toggle('applicable')} style={{
                        width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        padding: '10px 14px', background: '#1a2a1a', border: 'none', cursor: 'pointer',
                        color: '#f0ece4', fontSize: 12, fontWeight: 600, textAlign: 'left',
                        borderBottom: expanded.applicable ? '1px solid #2a2a2a' : 'none',
                    }}>
                        <span>Applicable to This Asset — {mat || 'Unknown'} {dia ? dia + ' mm' : ''} {year ? `(${year})` : ''}</span>
                        <span style={{ color: '#27ae60', fontSize: 10 }}>{applicable.length} standards</span>
                    </button>
                    {expanded.applicable && (
                        <div style={{ background: '#161616' }}>
                            {applicable.map(({ badge, title, desc, color }) => (
                                <div key={title} style={{ padding: '10px 14px', borderBottom: '1px solid #222' }}>
                                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                                        <Badge t={badge} c={color} />
                                        <div>
                                            <div style={{ fontSize: 12, fontWeight: 600, color: '#f0ece4', marginBottom: 3 }}>{title}</div>
                                            <div style={{ fontSize: 11, color: '#888', lineHeight: 1.5 }}>{desc}</div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
            {!asset && <div style={{ padding: '12px 8px', fontSize: 12, color: '#888' }}>Click a pipe segment on the map to see applicable standards.</div>}
            {Object.entries(allStandards).map(([key, group]) => (
                <div key={key} style={{ marginBottom: 10, border: '1px solid #2a2a2a', borderRadius: 8, overflow: 'hidden' }}>
                    <button onClick={() => toggle(key)} style={{
                        width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        padding: '10px 14px', background: '#1e1e1e', border: 'none', cursor: 'pointer',
                        color: '#f0ece4', fontSize: 12, fontWeight: 600, textAlign: 'left',
                        borderBottom: expanded[key] ? '1px solid #2a2a2a' : 'none',
                    }}>
                        <span>{group.label}</span>
                        <span style={{ color: '#555', fontSize: 10 }}>{expanded[key] ? '▲' : '▼'}</span>
                    </button>
                    {expanded[key] && (
                        <div style={{ background: '#161616' }}>
                            {group.items.map(({ badge, title, desc }) => (
                                <div key={title} style={{ padding: '10px 14px', borderBottom: '1px solid #222' }}>
                                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                                        <Badge t={badge} c={badge === 'OPSD' ? '#c8a55c' : badge === 'OPSS' ? '#2277bb' : badge === 'AWWA' ? '#27ae60' : badge === 'ECS' ? '#e67e22' : '#9b59b6'} />
                                        <div>
                                            <div style={{ fontSize: 12, fontWeight: 600, color: '#f0ece4', marginBottom: 3 }}>{title}</div>
                                            <div style={{ fontSize: 11, color: '#888', lineHeight: 1.5 }}>{desc}</div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

function InfraNetworkTab({ asset }) {
    const dia = asset?.diameter_mm;
    const mat = (asset?.material || '').toUpperCase();
    const len = asset?.length_m;

    // Classify where this pipe sits in the hierarchy
    let pipeClass = 'Unknown';
    let classColor = '#888';
    if (dia) {
        if (dia >= 400) { pipeClass = 'Trunk Main'; classColor = '#e74c3c'; }
        else if (dia >= 200) { pipeClass = 'Primary Distribution'; classColor = '#2277bb'; }
        else if (dia >= 150) { pipeClass = 'Secondary Distribution'; classColor = '#27ae60'; }
        else { pipeClass = 'Service Connection'; classColor = '#f1c40f'; }
    }

    // Hydraulic capacity (Hazen-Williams)
    const cFactor = mat.includes('CI') || mat.includes('CAST') ? 80 : mat.includes('DI') || mat.includes('DUCTILE') ? 120 : mat.includes('PVC') ? 140 : mat.includes('HDPE') || mat.includes('PE') ? 140 : mat.includes('COP') ? 130 : 100;
    const flowCapacity = dia ? (0.2785 * cFactor * Math.pow(dia / 1000, 2.63) * Math.pow(0.003, 0.54) * 1000).toFixed(1) : null;
    const velocity = dia && flowCapacity ? ((parseFloat(flowCapacity) / 1000) / (Math.PI * Math.pow(dia / 2000, 2))).toFixed(2) : null;

    const hierarchy = [
        { label: 'Trunk', dia: '400–1,200 mm', mat: 'DI / PCCP', color: '#e74c3c' },
        { label: 'Primary Distribution', dia: '200–400 mm', mat: 'DI', color: '#2277bb' },
        { label: 'Secondary Distribution', dia: '150–200 mm', mat: 'PVC / DI', color: '#27ae60' },
        { label: 'Service Connection', dia: '19–50 mm', mat: 'Copper / HDPE', color: '#f1c40f' },
    ];

    return (
        <div className="tab-section" style={{ padding: '4px' }}>
            {asset && (
                <div style={{ background: '#1a2a1a', borderRadius: 8, padding: '12px 14px', marginBottom: 12, border: '1px solid #2a4a2a' }}>
                    <div style={{ fontSize: 11, color: '#27ae60', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>This Segment</div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                        <div style={{ background: '#161616', borderRadius: 6, padding: '8px 10px' }}>
                            <div style={{ fontSize: 15, fontWeight: 700, color: classColor }}>{pipeClass}</div>
                            <div style={{ fontSize: 10, color: '#888' }}>Network class</div>
                        </div>
                        <div style={{ background: '#161616', borderRadius: 6, padding: '8px 10px' }}>
                            <div style={{ fontSize: 15, fontWeight: 700, color: '#c8a55c' }}>{dia || '?'} mm</div>
                            <div style={{ fontSize: 10, color: '#888' }}>Diameter</div>
                        </div>
                        <div style={{ background: '#161616', borderRadius: 6, padding: '8px 10px' }}>
                            <div style={{ fontSize: 15, fontWeight: 700, color: '#c8a55c' }}>C = {cFactor}</div>
                            <div style={{ fontSize: 10, color: '#888' }}>Hazen-Williams ({mat || '?'})</div>
                        </div>
                        <div style={{ background: '#161616', borderRadius: 6, padding: '8px 10px' }}>
                            <div style={{ fontSize: 15, fontWeight: 700, color: '#c8a55c' }}>{flowCapacity || '?'} L/s</div>
                            <div style={{ fontSize: 10, color: '#888' }}>Flow capacity @ 3‰</div>
                        </div>
                        {velocity && (
                            <div style={{ background: '#161616', borderRadius: 6, padding: '8px 10px' }}>
                                <div style={{ fontSize: 15, fontWeight: 700, color: parseFloat(velocity) > 2.5 ? '#e74c3c' : '#27ae60' }}>{velocity} m/s</div>
                                <div style={{ fontSize: 10, color: '#888' }}>Velocity {parseFloat(velocity) > 2.5 ? '(HIGH)' : '(OK)'}</div>
                            </div>
                        )}
                        {len && (
                            <div style={{ background: '#161616', borderRadius: 6, padding: '8px 10px' }}>
                                <div style={{ fontSize: 15, fontWeight: 700, color: '#c8a55c' }}>{typeof len === 'number' ? Math.round(len) : len} m</div>
                                <div style={{ fontSize: 10, color: '#888' }}>Segment length</div>
                            </div>
                        )}
                    </div>
                </div>
            )}
            {!asset && <div style={{ padding: '12px 8px', fontSize: 12, color: '#888' }}>Click a pipe segment to see its network classification and hydraulic data.</div>}

            <div style={{ background: '#1e1e1e', borderRadius: 8, padding: '12px 14px', marginBottom: 12, border: '1px solid #2a2a2a' }}>
                <div style={{ fontSize: 11, color: '#888', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Toronto Water System</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    {[['6,100 km', 'Total watermain'], ['550 km', 'Transmission'], ['5,550 km', 'Distribution'], ['18', 'Pumping stations'],
                    ['6', 'Pressure zones'], ['13', 'Pressure districts']].map(([val, lab]) => (
                        <div key={lab} style={{ background: '#161616', borderRadius: 6, padding: '8px 10px' }}>
                            <div style={{ fontSize: 15, fontWeight: 700, color: '#c8a55c' }}>{val}</div>
                            <div style={{ fontSize: 10, color: '#888' }}>{lab}</div>
                        </div>
                    ))}
                </div>
            </div>

            <div style={{ background: '#1e1e1e', borderRadius: 8, padding: '12px 14px', marginBottom: 12, border: '1px solid #2a2a2a' }}>
                <div style={{ fontSize: 11, color: '#888', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Pipe Hierarchy</div>
                {hierarchy.map(({ label, dia: d, mat: m, color }) => {
                    const isThis = label === pipeClass;
                    return (
                        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', borderBottom: '1px solid #222', background: isThis ? '#1a2a1a' : 'transparent', borderRadius: isThis ? 4 : 0, paddingLeft: isThis ? 6 : 0 }}>
                            <span style={{ width: 12, height: 4, background: color, borderRadius: 2, flexShrink: 0 }} />
                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: 12, color: '#f0ece4' }}>{label} {isThis && asset ? '← this pipe' : ''}</div>
                                <div style={{ fontSize: 11, color: '#888' }}>{d} · {m}</div>
                            </div>
                        </div>
                    );
                })}
            </div>

            <div style={{ background: '#1e1e1e', borderRadius: 8, padding: '12px 14px', border: '1px solid #2a2a2a' }}>
                <div style={{ fontSize: 11, color: '#888', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Design Parameters</div>
                <div style={{ fontSize: 12, color: '#aaa', lineHeight: 1.8 }}>
                    <div>Min residual pressure: <strong style={{ color: '#f0ece4' }}>275 kPa (40 psi)</strong></div>
                    <div>Fire flow residual: <strong style={{ color: '#f0ece4' }}>140 kPa (20 psi)</strong></div>
                    <div>Valve spacing: <strong style={{ color: '#f0ece4' }}>max 200 m</strong></div>
                    <div>Hydrant spacing: <strong style={{ color: '#f0ece4' }}>max 150 m</strong> (Toronto ECS)</div>
                </div>
            </div>
        </div>
    );
}

function InfraDatasetsTab() {
    const datasets = [
        { name: 'Watermain Breaks (1990–2016)', source: 'Toronto Open Data', url: 'https://open.toronto.ca/dataset/watermain-breaks/', format: 'SHP / XLSX', fields: 'BREAK_DATE, BREAK_YEAR, XCOORD, YCOORD (MTM NAD 27)', refresh: 'Annual', color: '#e74c3c' },
        { name: 'Watermain Distribution Network', source: 'Toronto CKAN', url: null, format: 'GeoJSON (4326)', fields: 'Asset ID, Type, Diameter, Material, Install Date, Length, Location', refresh: 'Loaded', color: '#2277bb' },
        { name: 'Water Hydrants', source: 'Toronto Open Data', url: null, format: 'GeoJSON', fields: 'Hydrant ID, Location, Status', refresh: 'Loaded', color: '#e67e22' },
        { name: 'Water Valves', source: 'Toronto Open Data', url: null, format: 'GeoJSON', fields: 'Valve ID, Type, Size, Status', refresh: 'Loaded', color: '#9b59b6' },
        { name: 'Water Fittings', source: 'Toronto Open Data', url: null, format: 'GeoJSON', fields: 'Fitting ID, Type, Material', refresh: 'Loaded', color: '#1abc9c' },
        { name: 'Parks Drinking Water Sources', source: 'Toronto Open Data', url: null, format: 'GeoJSON', fields: 'Park Name, Source Type, Status', refresh: 'Loaded', color: '#3498db' },
        { name: 'CUMAP Water Network (Full)', source: 'Toronto Water', url: null, format: 'SHP (on request)', fields: 'PIPE_MATERIAL, DIAMETER_MM, YEAR_INSTALLED, PRESSURE_ZONE', refresh: 'Daily', color: '#888' },
    ];

    return (
        <div className="tab-section" style={{ padding: '4px' }}>
            <div style={{ fontSize: 12, color: '#888', marginBottom: 12, padding: '0 8px' }}>
                Toronto Open Data water infrastructure datasets. Loaded datasets are available on the map.
            </div>
            {datasets.map(d => (
                <div key={d.name} style={{ background: '#1e1e1e', borderRadius: 8, padding: '10px 14px', marginBottom: 8, border: '1px solid #2a2a2a' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span style={{ width: 8, height: 8, borderRadius: '50%', background: d.color, flexShrink: 0 }} />
                            <span style={{ fontSize: 12, fontWeight: 600, color: '#f0ece4' }}>{d.name}</span>
                        </div>
                        <span style={{ fontSize: 10, color: d.refresh === 'Loaded' ? '#27ae60' : '#888', background: d.refresh === 'Loaded' ? '#27ae6022' : '#333', padding: '2px 6px', borderRadius: 3 }}>
                            {d.refresh}
                        </span>
                    </div>
                    <div style={{ fontSize: 11, color: '#888', lineHeight: 1.6 }}>
                        <div>Source: {d.source} · Format: {d.format}</div>
                        <div style={{ color: '#666' }}>Fields: {d.fields}</div>
                    </div>
                    {d.url && <a href={d.url} target="_blank" rel="noreferrer" style={{ fontSize: 11, color: '#c8a55c', textDecoration: 'none', marginTop: 4, display: 'inline-block' }}>Open dataset →</a>}
                </div>
            ))}
            <div style={{ background: '#1e1e1e', borderRadius: 8, padding: '10px 14px', marginTop: 12, border: '1px solid #2a2a2a' }}>
                <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>CKAN API</div>
                <code style={{ fontSize: 10, color: '#c8a55c', wordBreak: 'break-all' }}>https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/</code>
                <div style={{ fontSize: 10, color: '#666', marginTop: 4 }}>No authentication required. GeoJSON / CSV / SHP formats available.</div>
            </div>
        </div>
    );
}

function InfraInspectionsTab({ asset }) {
    const mat = (asset?.material || '').toUpperCase();
    const dia = asset?.diameter_mm;
    const year = asset?.install_year;
    const age = year ? new Date().getFullYear() - year : null;

    const allMethods = [
        { icon: '📹', name: 'CCTV Inspection', standard: 'NASSCO PACP', desc: 'Defect coding per PACP standard. Mandatory post-CIPP per Toronto ECS TS 7.60.', frequency: 'Pre/post-rehab; condition-based', materials: ['all'] },
        { icon: '🔊', name: 'Acoustic Leak Detection', standard: 'Echologics EchoWave', desc: 'Non-invasive. Identifies leaks and wire breaks without service interruption.', frequency: 'Annually on critical mains', materials: ['all'] },
        { icon: '💧', name: 'Hydrostatic Pressure Test', standard: 'AWWA C600 / C605', desc: 'Test at 1,035 kPa or 1.5x working pressure, 2-hour hold.', frequency: 'All new installs and rehab', materials: ['all'] },
        { icon: '⚡', name: 'Cathodic Protection Survey', standard: 'NACE SP0169', desc: '−850 mV CSE criterion. Annual close-interval surveys. Toronto ECS requires Mg anodes in soils <2,000 Ω·cm.', frequency: 'Annually on protected assets', materials: ['CI', 'CAST', 'DI', 'DUCTILE'] },
        { icon: '🎵', name: 'Acoustic Emission (PCCP)', standard: 'Hydrophone', desc: 'Wire break detection in pre-stressed concrete cylinder pipe.', frequency: 'Every 5 years on PCCP mains', materials: ['PCCP', 'CONC'] },
        { icon: '📊', name: 'Flow / Pressure Monitoring', standard: 'AWWA M36', desc: 'District metered areas. Minimum night flow analysis for leakage detection.', frequency: 'Continuous', materials: ['all'] },
    ];

    // Filter methods applicable to this asset's material
    const applicableMethods = asset
        ? allMethods.filter(m => m.materials.includes('all') || m.materials.some(mt => mat.includes(mt)))
        : allMethods;

    // Asset-specific inspection recommendations
    const recommendations = [];
    if (asset) {
        if (age && age > 80) recommendations.push({ level: 'critical', text: `At ${age} years old, this ${mat} main is in the highest-risk cohort. Recommend immediate condition assessment (CCTV + leak survey).` });
        else if (age && age > 50) recommendations.push({ level: 'warning', text: `At ${age} years, this main approaches end-of-design-life. Schedule condition assessment within 2 years.` });
        else if (age && age > 30) recommendations.push({ level: 'info', text: `At ${age} years, this main is mid-life. Standard inspection cycle applies.` });

        if (mat.includes('CI') || mat.includes('CAST')) {
            recommendations.push({ level: 'warning', text: 'Cast iron: check for graphitization, external corrosion pitting, and bell-joint leaks. Soil resistivity test recommended.' });
        }
        if (mat.includes('AC') || mat.includes('ASBESTOS')) {
            recommendations.push({ level: 'critical', text: 'Asbestos cement: O.Reg 278/05 applies for any cutting/breaking. Pipe samples may be required for condition grading.' });
        }
        if (dia && dia >= 400) {
            recommendations.push({ level: 'info', text: `Transmission main (${dia} mm): acoustic leak detection and pressure monitoring are priority methods.` });
        }

        // Allowable leakage calc
        if (dia) {
            const L = Math.round(1 * dia * Math.sqrt(1035) / 7400);
            recommendations.push({ level: 'info', text: `AWWA C600 allowable leakage for ${dia} mm @ 1,035 kPa test: ${L} mL/hr per joint.` });
        }
    }

    const regulations = [
        { reg: 'O.Reg 170/03', title: 'Drinking Water Systems', desc: 'Mandatory operational checks, record retention 2–15 years, annual MECP reports.' },
        { reg: 'O.Reg 453/07', title: 'Drinking Water Works Permit', desc: 'Required for new watermains and alterations to existing systems.' },
        { reg: 'O.Reg 588/17', title: 'Asset Management Planning', desc: 'Condition assessments, lifecycle costing, and level-of-service targets.' },
        { reg: 'OWRA ECA', title: 'Environmental Compliance Approval', desc: 'Required for new installations; routine replacements may qualify for Class EA Schedule A.' },
    ];

    const levelColors = { critical: '#e74c3c', warning: '#e67e22', info: '#2277bb' };

    return (
        <div className="tab-section" style={{ padding: '4px' }}>
            {recommendations.length > 0 && (
                <>
                    <div style={{ fontSize: 11, color: '#888', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8, padding: '0 8px' }}>
                        Recommendations for {mat || 'Unknown'} {dia ? dia + ' mm' : ''} {year ? `(${year})` : ''}
                    </div>
                    {recommendations.map((r, i) => (
                        <div key={i} style={{ background: '#1e1e1e', borderRadius: 8, padding: '10px 14px', marginBottom: 6, border: `1px solid ${levelColors[r.level]}44`, borderLeft: `3px solid ${levelColors[r.level]}` }}>
                            <div style={{ fontSize: 12, color: levelColors[r.level], lineHeight: 1.5 }}>{r.text}</div>
                        </div>
                    ))}
                    <div style={{ height: 12 }} />
                </>
            )}
            {!asset && <div style={{ padding: '12px 8px', fontSize: 12, color: '#888' }}>Click a pipe segment to see asset-specific inspection recommendations.</div>}

            <div style={{ fontSize: 11, color: '#888', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8, padding: '0 8px' }}>
                {asset ? 'Applicable Inspection Methods' : 'All Inspection Methods'}
            </div>
            {applicableMethods.map(m => (
                <div key={m.name} style={{ background: '#1e1e1e', borderRadius: 8, padding: '10px 14px', marginBottom: 8, border: '1px solid #2a2a2a' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                        <span style={{ fontSize: 14 }}>{m.icon}</span>
                        <span style={{ fontSize: 12, fontWeight: 600, color: '#f0ece4' }}>{m.name}</span>
                        <span style={{ marginLeft: 'auto', fontSize: 10, color: '#888', background: '#222', padding: '2px 6px', borderRadius: 3 }}>{m.standard}</span>
                    </div>
                    <div style={{ fontSize: 11, color: '#888', lineHeight: 1.6 }}>{m.desc}</div>
                    <div style={{ fontSize: 10, color: '#c8a55c', marginTop: 4 }}>Frequency: {m.frequency}</div>
                </div>
            ))}

            <div style={{ fontSize: 11, color: '#888', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8, marginTop: 16, padding: '0 8px' }}>Regulatory Framework</div>
            {regulations.map(r => (
                <div key={r.reg} style={{ background: '#1e1e1e', borderRadius: 8, padding: '10px 14px', marginBottom: 8, border: '1px solid #2a2a2a' }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#f0ece4', marginBottom: 3 }}>{r.reg} — {r.title}</div>
                    <div style={{ fontSize: 11, color: '#888', lineHeight: 1.5 }}>{r.desc}</div>
                </div>
            ))}
        </div>
    );
}

function InfraHistoryTab({ asset }) {
    const mat = (asset?.material || '').toUpperCase();
    const year = asset?.install_year;
    const age = year ? new Date().getFullYear() - year : null;
    const dia = asset?.diameter_mm;

    // Material-specific expected service life and break rates
    const materialInfo = {
        CI: { life: 100, breakRate: 25, era: 'Pre-1970', note: 'Bell-and-spigot with lead joints. Graphitic corrosion is primary failure mode. Toronto\'s 1950s CI cohort has highest break density.' },
        CICL: { life: 100, breakRate: 25, era: 'Pre-1970', note: 'Cast iron cement-lined. Lining delays internal tuberculation but external corrosion still occurs.' },
        DI: { life: 100, breakRate: 8, era: '1965–present', note: 'Replaced CI as standard. Cement mortar lining standard since 1970s. Polyethylene encasement in corrosive soils.' },
        DICL: { life: 100, breakRate: 8, era: '1965–present', note: 'Ductile iron cement-lined. Current Toronto Water standard for distribution mains ≥150 mm.' },
        PVC: { life: 75, breakRate: 3, era: '1980–present', note: 'No corrosion. Brittle fracture risk in cold weather (<-7°C). DR 18 standard in Ontario.' },
        AC: { life: 50, breakRate: 30, era: '1950–1980', note: 'Asbestos cement — all targeted for replacement by Toronto Water. No rehabilitation possible. O.Reg 278/05 applies.' },
        COP: { life: 60, breakRate: 5, era: 'Service lines', note: 'Copper service connections 19–50 mm. Lead-free solder mandatory post-1990. Replacement program for lead services.' },
        HDPE: { life: 100, breakRate: 1, era: '2000–present', note: 'Heat-fusion joints. Used for trenchless replacement (pipe bursting). Lowest break rate of all materials.' },
        PCCP: { life: 75, breakRate: 6, era: '1960–1990', note: 'Pre-stressed concrete cylinder pipe for large-diameter transmission. Wire break monitoring required.' },
    };

    const matKey = Object.keys(materialInfo).find(k => mat.includes(k)) || null;
    const info = matKey ? materialInfo[matKey] : null;
    const remainingLife = info && age ? Math.max(0, info.life - age) : null;
    const lifePercent = info && age ? Math.min(100, Math.round((age / info.life) * 100)) : null;

    // Replacement cost estimate (Toronto Water avg $1,200–$2,500/m depending on diameter)
    const costPerM = dia ? (dia < 200 ? 1200 : dia < 400 ? 1800 : 2500) : null;
    const segLen = asset?.length_m ? (typeof asset.length_m === 'number' ? asset.length_m : parseFloat(asset.length_m)) : null;
    const replacementCost = costPerM && segLen ? Math.round(costPerM * segLen) : null;

    const timeline = [
        { year: '1843', event: 'First piped water system (Furniss Works)' },
        { year: '1873', event: 'City takes over water supply' },
        { year: '1950s', event: 'Thin-wall CI installed — now highest break risk' },
        { year: '2007', event: '$87.7 M emergency investment', highlight: true },
        { year: '2020', event: '681 breaks/year — 58% reduction', good: true },
    ];
    if (year) {
        timeline.push({ year: String(year), event: `This ${mat || 'pipe'} segment installed`, thisAsset: true });
        timeline.sort((a, b) => parseInt(a.year) - parseInt(b.year));
    }

    return (
        <div className="tab-section" style={{ padding: '4px' }}>
            {asset && info && (
                <div style={{ background: '#1a2a1a', borderRadius: 8, padding: '12px 14px', marginBottom: 12, border: '1px solid #2a4a2a' }}>
                    <div style={{ fontSize: 11, color: '#27ae60', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
                        This Asset — {mat} {dia ? dia + ' mm' : ''} {year ? `(${year})` : ''}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                        <div style={{ background: '#161616', borderRadius: 6, padding: '8px 10px' }}>
                            <div style={{ fontSize: 16, fontWeight: 700, color: age > 80 ? '#e74c3c' : age > 50 ? '#e67e22' : '#27ae60' }}>{age ?? '?'} yrs</div>
                            <div style={{ fontSize: 10, color: '#888' }}>Current age</div>
                        </div>
                        <div style={{ background: '#161616', borderRadius: 6, padding: '8px 10px' }}>
                            <div style={{ fontSize: 16, fontWeight: 700, color: remainingLife < 10 ? '#e74c3c' : remainingLife < 30 ? '#e67e22' : '#27ae60' }}>{remainingLife ?? '?'} yrs</div>
                            <div style={{ fontSize: 10, color: '#888' }}>Est. remaining life</div>
                        </div>
                        <div style={{ background: '#161616', borderRadius: 6, padding: '8px 10px' }}>
                            <div style={{ fontSize: 16, fontWeight: 700, color: '#c8a55c' }}>{info.breakRate}/100km/yr</div>
                            <div style={{ fontSize: 10, color: '#888' }}>Avg break rate ({matKey})</div>
                        </div>
                        {replacementCost && (
                            <div style={{ background: '#161616', borderRadius: 6, padding: '8px 10px' }}>
                                <div style={{ fontSize: 16, fontWeight: 700, color: '#c8a55c' }}>${(replacementCost / 1000).toFixed(0)}k</div>
                                <div style={{ fontSize: 10, color: '#888' }}>Est. replacement cost</div>
                            </div>
                        )}
                    </div>
                    {lifePercent !== null && (
                        <div style={{ marginBottom: 8 }}>
                            <div style={{ fontSize: 10, color: '#888', marginBottom: 3 }}>Lifecycle: {lifePercent}% consumed</div>
                            <div style={{ height: 6, background: '#333', borderRadius: 3, overflow: 'hidden' }}>
                                <div style={{ height: '100%', width: `${lifePercent}%`, background: lifePercent > 80 ? '#e74c3c' : lifePercent > 50 ? '#e67e22' : '#27ae60', borderRadius: 3 }} />
                            </div>
                        </div>
                    )}
                    <div style={{ fontSize: 11, color: '#888', lineHeight: 1.6 }}>
                        <strong style={{ color: '#aaa' }}>{matKey} era:</strong> {info.era}<br />
                        {info.note}
                    </div>
                </div>
            )}
            {!asset && <div style={{ padding: '12px 8px', fontSize: 12, color: '#888' }}>Click a pipe segment to see its age profile and lifecycle data.</div>}

            <div style={{ background: '#1e1e1e', borderRadius: 8, padding: '12px 14px', marginBottom: 12, border: '1px solid #2a2a2a' }}>
                <div style={{ fontSize: 11, color: '#888', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>System Age Profile</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    {[
                        { label: 'Average pipe age', value: '61 years', color: '#e67e22' },
                        { label: 'Cast iron share', value: '71%', color: '#e67e22' },
                        { label: 'Over 80 years old', value: '24%', color: '#e74c3c' },
                        { label: 'Over 100 years old', value: '13%', color: '#e74c3c' },
                    ].map(s => (
                        <div key={s.label} style={{ background: '#161616', borderRadius: 6, padding: '8px 10px' }}>
                            <div style={{ fontSize: 16, fontWeight: 700, color: s.color }}>{s.value}</div>
                            <div style={{ fontSize: 10, color: '#888' }}>{s.label}</div>
                        </div>
                    ))}
                </div>
            </div>

            <div style={{ background: '#1e1e1e', borderRadius: 8, padding: '12px 14px', marginBottom: 12, border: '1px solid #2a2a2a' }}>
                <div style={{ fontSize: 11, color: '#888', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>Timeline</div>
                {timeline.map((t, i) => (
                    <div key={t.year + i} style={{ display: 'flex', gap: 10, marginBottom: 10, alignItems: 'flex-start', background: t.thisAsset ? '#1a2a1a' : 'transparent', borderRadius: 4, padding: t.thisAsset ? '4px 6px' : 0 }}>
                        <div style={{ width: 46, flexShrink: 0, fontSize: 11, fontWeight: 700, color: t.thisAsset ? '#27ae60' : t.highlight ? '#e74c3c' : t.good ? '#27ae60' : '#c8a55c', textAlign: 'right', paddingTop: 1 }}>{t.year}</div>
                        <div style={{ width: 2, background: t.thisAsset ? '#27ae60' : '#333', flexShrink: 0, minHeight: 16, borderRadius: 1 }} />
                        <div style={{ fontSize: 12, color: t.thisAsset ? '#27ae60' : t.highlight ? '#e74c3c' : t.good ? '#27ae60' : '#ccc', lineHeight: 1.4, fontWeight: t.thisAsset ? 600 : 400 }}>{t.event}</div>
                    </div>
                ))}
            </div>

            <div style={{ background: '#1e1e1e', borderRadius: 8, padding: '12px 14px', border: '1px solid #2a2a2a' }}>
                <div style={{ fontSize: 11, color: '#888', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>2025–2034 Capital Plan</div>
                <div style={{ fontSize: 12, color: '#aaa', lineHeight: 1.8 }}>
                    <div>Total Toronto Water budget: <strong style={{ color: '#c8a55c' }}>$8.924 B</strong></div>
                    <div>Linear watermain & sewer: <strong style={{ color: '#c8a55c' }}>$5.429 B</strong></div>
                    <div>SOGR backlog (2024): <strong style={{ color: '#e74c3c' }}>$2.194 B</strong></div>
                </div>
            </div>
        </div>
    );
}


export default function PolicyPanel({ parcel, isOpen, onClose, activeNav, savedParcels, onSaveParcel, onUploadAnalyzed, activePlanId, assetType, selectedPipelineAsset }) {
    const { isResizing, handleProps: resizeHandleProps } = useResizable({
        defaultSize: 380,
        minSize: 280,
        maxSize: 600,
        axis: 'horizontal',
        reverse: true,
        cssVar: '--panel-width',
    });
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
        // Pipeline mode: show asset detail when a segment is clicked
        if (assetType === 'pipeline' && selectedPipelineAsset && activeNav === 'overview') {
            return <PipelineAssetPanel asset={selectedPipelineAsset} />;
        }

        if (!parcel) {
            return (
                <div className="tab-empty">
                    {activeNav === 'overview' && assetType !== 'pipeline' && <FileUploadZone onUploadComplete={onUploadAnalyzed} />}
                    <p>{assetType === 'pipeline'
                        ? 'Click a pipeline segment on the map to view asset details.'
                        : 'Search for a property to view due diligence information.'
                    }</p>
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
                return <OverviewTab parcel={parcel} zoning={zoning} onUploadComplete={onUploadAnalyzed} />;
            case 'policies':
                return <PoliciesTab policies={visiblePolicies} loading={visiblePoliciesLoading} />;
            case 'datasets':
                return assetType === 'pipeline'
                    ? <InfraDatasetsTab />
                    : <DatasetsTab overlays={visibleOverlays} loading={visibleOverlaysLoading} />;
            case 'precedents':
                return <PrecedentsTab parcel={parcel} />;
            case 'finances':
                return <FinancesTab parcel={parcel} />;
            case 'documents':
                return <DocumentsTab planId={activePlanId} />;
            case 'standards':
                return <InfraStandardsTab asset={selectedPipelineAsset} />;
            case 'network':
                return <InfraNetworkTab asset={selectedPipelineAsset} />;
            case 'inspections':
                return <InfraInspectionsTab asset={selectedPipelineAsset} />;
            case 'history':
                return <InfraHistoryTab asset={selectedPipelineAsset} />;
            default:
                return <OverviewTab parcel={parcel} zoning={zoning} onUploadComplete={onUploadAnalyzed} />;
        }
    };

    return (
        <aside id="policy-panel" className={`${isOpen ? '' : 'panel-hidden'} backdrop-blur-xl`} style={{ userSelect: isResizing ? 'none' : undefined }}>
            <div {...resizeHandleProps} style={{ ...resizeHandleProps.style, left: -2 }} />
            <div id="policy-panel-header">
                <h2 id="policy-panel-title">
                    {assetType === 'pipeline' && selectedPipelineAsset
                        ? (selectedPipelineAsset.location || 'Water Main')
                        : (TAB_TITLES[activeNav] || 'Project Information')}
                </h2>
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
