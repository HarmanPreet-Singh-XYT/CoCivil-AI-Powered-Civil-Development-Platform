import { useState, useRef, useMemo, useCallback, useEffect, Suspense } from 'react';
import { createPortal } from 'react-dom';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import {
  alignmentToLocal,
  generatePipeSegment,
  generateManhole,
  generateFitting,
} from '../lib/infrastructureGeometry.js';

// ── DXF pipeline network colour map ────────────────────────────────────────
const DXF_PIPE_COLORS = {
  water_main:     '#2196f3',
  sanitary_sewer: '#795548',
  storm_sewer:    '#4caf50',
  gas_line:       '#ff9800',
};

// ── DXF network 3D mesh components ─────────────────────────────────────────
function DxfPipeMesh({ pipe, isSelected, onClick }) {
  const { geometry, position, quaternion } = useMemo(
    () => generatePipeSegment(
      [pipe.start[0], -(pipe.depth_m ?? 1.5), pipe.start[1]],
      [pipe.end[0],   -(pipe.depth_m ?? 1.5), pipe.end[1]],
      pipe.diameter_mm ?? 150,
    ),
    [pipe],
  );
  const color = DXF_PIPE_COLORS[pipe.pipe_type] ?? '#2196f3';
  return (
    <mesh geometry={geometry} position={position} quaternion={quaternion}
      onClick={(e) => { e.stopPropagation(); onClick(pipe); }}>
      <meshStandardMaterial color={color}
        emissive={isSelected ? color : '#000'} emissiveIntensity={isSelected ? 0.4 : 0}
        roughness={0.6} metalness={0.3} />
    </mesh>
  );
}

function DxfManholeMesh({ manhole, isSelected, onClick }) {
  const { geometry, position } = useMemo(
    () => generateManhole([manhole.position[0], 0, manhole.position[1]], manhole.depth_m ?? 2.0),
    [manhole],
  );
  return (
    <mesh geometry={geometry} position={position}
      onClick={(e) => { e.stopPropagation(); onClick(manhole); }}>
      <meshStandardMaterial color="#9e9e9e"
        emissive={isSelected ? '#9e9e9e' : '#000'} emissiveIntensity={isSelected ? 0.5 : 0}
        roughness={0.8} />
    </mesh>
  );
}

function DxfNodeMesh({ position, color, radius = 0.4, onClick }) {
  return (
    <mesh position={[position[0], 0.5, position[1]]}
      onClick={(e) => { e.stopPropagation(); onClick?.(); }}>
      <sphereGeometry args={[radius, 12, 8]} />
      <meshStandardMaterial color={color} roughness={0.5} metalness={0.2} />
    </mesh>
  );
}

function DxfNetworkScene({ pipelineData, selectedItem, onSelect }) {
  const pipes    = pipelineData?.pipes    ?? [];
  const manholes = pipelineData?.manholes ?? [];
  const valves   = pipelineData?.valves   ?? [];
  const hydrants = pipelineData?.hydrants ?? [];
  const fittings = pipelineData?.fittings ?? [];
  return (
    <>
      <ambientLight intensity={0.6} />
      <directionalLight position={[30, 50, 30]} intensity={0.8} castShadow />
      <directionalLight position={[-20, 30, -20]} intensity={0.3} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
        <planeGeometry args={[500, 500]} />
        <meshStandardMaterial color="#c8d4b8" roughness={1} />
      </mesh>
      {pipes.map((p, i) => (
        <DxfPipeMesh key={i} pipe={p} isSelected={selectedItem === p} onClick={onSelect} />
      ))}
      {manholes.map((m, i) => (
        <DxfManholeMesh key={i} manhole={m} isSelected={selectedItem === m} onClick={onSelect} />
      ))}
      {valves.map((v, i) => (
        <DxfNodeMesh key={i} position={v.position} color="#f44336" radius={0.5} onClick={() => onSelect(v)} />
      ))}
      {hydrants.map((h, i) => (
        <DxfNodeMesh key={i} position={h.position} color="#e91e63" radius={0.4} />
      ))}
      {fittings.map((f, i) => {
        const { geometry, position } = generateFitting([f.position[0], 0, f.position[1]], f.type, [0, 0, 0]);
        return (
          <mesh key={i} geometry={geometry} position={position}>
            <meshStandardMaterial color="#ff5722" roughness={0.5} />
          </mesh>
        );
      })}
      <OrbitControls enableDamping dampingFactor={0.08} />
    </>
  );
}

// ── DXF edit panel ──────────────────────────────────────────────────────────
function DxfEditPanel({ item, onClose, onSave }) {
  const [form, setForm] = useState({ ...item });
  const isPipe    = item && 'start' in item && 'end' in item;
  const isManhole = item && 'depth_m' in item && !('start' in item) && !(['gate','butterfly','ball','check'].includes(item.type));
  const isValve   = item && ['gate','butterfly','ball','check'].includes(item.type);
  const set = (k, v) => setForm((p) => ({ ...p, [k]: v }));
  return (
    <div style={{ position:'absolute', top:60, right:12, width:220, background:'rgba(20,20,20,0.92)',
      border:'1px solid rgba(255,255,255,0.12)', borderRadius:8, padding:12, zIndex:20, color:'#eee' }}>
      <div style={{ display:'flex', justifyContent:'space-between', marginBottom:10 }}>
        <b>{isPipe ? 'Pipe Segment' : isManhole ? 'Manhole' : isValve ? 'Valve' : 'Node'}</b>
        <button onClick={onClose} style={{ background:'none', border:'none', color:'#aaa', cursor:'pointer' }}>✕</button>
      </div>
      <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
        {isPipe && (<>
          <label style={{ fontSize:12 }}>Diameter (mm)<br/>
            <input type="number" value={form.diameter_mm ?? 150}
              onChange={(e) => set('diameter_mm', parseFloat(e.target.value)||150)}
              style={{ width:'100%', background:'#333', border:'1px solid #555', color:'#eee', borderRadius:4, padding:'2px 6px' }} />
          </label>
          <label style={{ fontSize:12 }}>Material<br/>
            <select value={form.material ?? 'PVC'} onChange={(e) => set('material', e.target.value)}
              style={{ width:'100%', background:'#333', border:'1px solid #555', color:'#eee', borderRadius:4, padding:'2px 6px' }}>
              <option>PVC</option><option>HDPE</option><option>DI</option><option>RCP</option><option>CSP</option>
            </select>
          </label>
          <label style={{ fontSize:12 }}>Pipe Type<br/>
            <select value={form.pipe_type ?? 'water_main'} onChange={(e) => set('pipe_type', e.target.value)}
              style={{ width:'100%', background:'#333', border:'1px solid #555', color:'#eee', borderRadius:4, padding:'2px 6px' }}>
              <option value="water_main">Water Main</option>
              <option value="sanitary_sewer">Sanitary Sewer</option>
              <option value="storm_sewer">Storm Sewer</option>
              <option value="gas_line">Gas Line</option>
            </select>
          </label>
          <label style={{ fontSize:12 }}>Depth (m)<br/>
            <input type="number" step="0.1" value={form.depth_m ?? 1.5}
              onChange={(e) => set('depth_m', parseFloat(e.target.value)||1.5)}
              style={{ width:'100%', background:'#333', border:'1px solid #555', color:'#eee', borderRadius:4, padding:'2px 6px' }} />
          </label>
        </>)}
        {isManhole && (<>
          <label style={{ fontSize:12 }}>ID<br/>
            <input value={form.id ?? ''} onChange={(e) => set('id', e.target.value)}
              style={{ width:'100%', background:'#333', border:'1px solid #555', color:'#eee', borderRadius:4, padding:'2px 6px' }} />
          </label>
          <label style={{ fontSize:12 }}>Depth (m)<br/>
            <input type="number" step="0.1" value={form.depth_m ?? 2.0}
              onChange={(e) => set('depth_m', parseFloat(e.target.value)||2.0)}
              style={{ width:'100%', background:'#333', border:'1px solid #555', color:'#eee', borderRadius:4, padding:'2px 6px' }} />
          </label>
          <label style={{ fontSize:12 }}>Rim Elevation (m)<br/>
            <input type="number" step="0.01" value={form.rim_elevation ?? ''}
              onChange={(e) => set('rim_elevation', e.target.value ? parseFloat(e.target.value) : null)}
              style={{ width:'100%', background:'#333', border:'1px solid #555', color:'#eee', borderRadius:4, padding:'2px 6px' }} />
          </label>
        </>)}
        {isValve && (<>
          <label style={{ fontSize:12 }}>Type<br/>
            <select value={form.type ?? 'gate'} onChange={(e) => set('type', e.target.value)}
              style={{ width:'100%', background:'#333', border:'1px solid #555', color:'#eee', borderRadius:4, padding:'2px 6px' }}>
              <option value="gate">Gate</option><option value="butterfly">Butterfly</option>
              <option value="ball">Ball</option><option value="check">Check</option>
            </select>
          </label>
          <label style={{ fontSize:12 }}>Diameter (mm)<br/>
            <input type="number" value={form.diameter_mm ?? 150}
              onChange={(e) => set('diameter_mm', parseFloat(e.target.value)||150)}
              style={{ width:'100%', background:'#333', border:'1px solid #555', color:'#eee', borderRadius:4, padding:'2px 6px' }} />
          </label>
        </>)}
      </div>
      <div style={{ display:'flex', gap:6, marginTop:12 }}>
        <button onClick={() => onSave(form)}
          style={{ flex:1, background:'#2196f3', border:'none', color:'#fff', borderRadius:4, padding:'4px 0', cursor:'pointer' }}>Apply</button>
        <button onClick={onClose}
          style={{ flex:1, background:'#333', border:'1px solid #555', color:'#eee', borderRadius:4, padding:'4px 0', cursor:'pointer' }}>Cancel</button>
      </div>
    </div>
  );
}

// ── DXF stats bar ───────────────────────────────────────────────────────────
function DxfStatsBar({ pipelineData }) {
  const s = pipelineData?.summary ?? {};
  const pipes = pipelineData?.pipes ?? [];
  const byType = pipes.reduce((a, p) => { a[p.pipe_type] = (a[p.pipe_type]??0)+1; return a; }, {});
  return (
    <div style={{ position:'absolute', bottom:0, left:0, right:0, height:36, background:'rgba(10,10,10,0.85)',
      display:'flex', alignItems:'center', gap:16, padding:'0 16px', fontSize:12, color:'#ccc', zIndex:10 }}>
      <span><strong style={{ color:'#fff' }}>{s.total_length_m ?? 0}m</strong> total</span>
      <span><strong style={{ color:'#fff' }}>{s.pipe_count ?? 0}</strong> segments</span>
      <span><strong style={{ color:'#fff' }}>{s.manhole_count ?? 0}</strong> manholes</span>
      {s.valve_count > 0 && <span><strong style={{ color:'#fff' }}>{s.valve_count}</strong> valves</span>}
      {s.hydrant_count > 0 && <span><strong style={{ color:'#fff' }}>{s.hydrant_count}</strong> hydrants</span>}
      {Object.entries(byType).map(([t, n]) => (
        <span key={t} style={{ color: DXF_PIPE_COLORS[t] ?? '#ccc' }}>{n}× {t.replace(/_/g,' ')}</span>
      ))}
    </div>
  );
}
import PipeNetworkEditor from './infrastructure/PipeNetworkEditor.jsx';
import ProfileView from './infrastructure/ProfileView.jsx';
import InfrastructureCompliancePanel from './infrastructure/InfrastructureCompliancePanel.jsx';
import InfrastructureCatalog from './infrastructure/InfrastructureCatalog.jsx';
import {
  createBranch,
  listBranches,
  commitVersion,
  listVersions,
} from '../api.js';
import '../InfrastructureViewer.css';
import '../ModelViewer.css';

const INFRA_COLORS = {
  water: '#2277bb',
  sanitary: '#886644',
  storm: '#44aa66',
  gas: '#ddaa22',
};

const COMPLIANCE_BADGES = {
  as_of_right: { color: '#4a7c59', label: 'Compliant' },
  needs_variance: { color: '#c8a55c', label: 'Minor issue' },
  needs_rezoning: { color: '#c44', label: 'Non-compliant' },
  blocked: { color: '#c44', label: 'Blocked' },
  unknown: { color: '#666', label: 'Unknown' },
};

// ─── Compliance badge ──────────────────────────────────────────────────────
function ComplianceBadge({ status }) {
  const badge = COMPLIANCE_BADGES[status] || COMPLIANCE_BADGES.unknown;
  return (
    <span className="compliance-badge" style={{ color: badge.color }}>
      <span className="compliance-dot" style={{ backgroundColor: badge.color }} />
      {badge.label}
    </span>
  );
}

// ─── Commit Modal ──────────────────────────────────────────────────────────
function CommitModal({ onCommit, onCancel, changeSummary }) {
  const [message, setMessage] = useState('Infrastructure update');
  return (
    <div className="commit-modal-overlay" onClick={onCancel}>
      <div className="commit-modal" onClick={(e) => e.stopPropagation()}>
        <h3>Commit Design Changes</h3>
        <label>
          Message:
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Describe your changes..."
            autoFocus
          />
        </label>
        {changeSummary && (
          <div className="commit-changes">
            <span className="commit-changes-label">Changes:</span>
            {changeSummary.split('; ').map((c, i) => (
              <div key={i} className="commit-change-item">{c}</div>
            ))}
          </div>
        )}
        <div className="commit-modal-actions">
          <button className="model-ctrl-btn" onClick={onCancel}>Cancel</button>
          <button
            className="model-ctrl-btn commit-btn"
            onClick={() => onCommit(message || 'Infrastructure update')}
            disabled={!message.trim()}
          >
            Commit
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── History Panel ─────────────────────────────────────────────────────────
function HistoryPanel({ versions, branches, currentBranch, onSelectVersion, onSwitchBranch, onClose }) {
  return (
    <div className="history-panel">
      <div className="history-header">
        <span>Version History — {currentBranch?.name || 'main'}</span>
        <button className="history-close" onClick={onClose}>x</button>
      </div>
      <div className="history-list">
        {versions.map((v) => {
          const badge = COMPLIANCE_BADGES[v.compliance_status] || COMPLIANCE_BADGES.unknown;
          return (
            <div key={v.id} className="history-item" onClick={() => onSelectVersion(v)}>
              <span className="history-version">v{v.version_number}</span>
              <span className="history-message">{v.message}</span>
              <span className="compliance-dot" style={{ backgroundColor: badge.color }} title={badge.label} />
            </div>
          );
        })}
      </div>
      {branches.length > 1 && (
        <div className="history-branches">
          {branches.filter((b) => b.id !== currentBranch?.id).map((b) => (
            <button key={b.id} className="history-branch-btn" onClick={() => onSwitchBranch(b)}>
              Branch: {b.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── 3D Infrastructure Mesh ────────────────────────────────────────────────
function InfrastructureMesh({ alignment, infraType, params }) {
  const buildResult = useMemo(() => {
    if (!alignment?.length) {
      // Generate default alignment
      const defaultAlignment = [];
      for (let i = 0; i <= 10; i++) {
        defaultAlignment.push([i * 10, 0, 0]);
      }
      const localPts = defaultAlignment;
      return buildPipeline3D(localPts, params);
    }

    const localPts = alignmentToLocal(alignment);
    return buildPipeline3D(localPts, params);
  }, [alignment, infraType, params]);

  return (
    <group>
      {buildResult.pieces.map((piece, i) => {
        const meshProps = {};
        if (piece.position) meshProps.position = piece.position;
        if (piece.quaternion) meshProps.quaternion = piece.quaternion;
        if (piece.rotation) meshProps.rotation = piece.rotation;

        return (
          <mesh key={i} geometry={piece.geometry} castShadow receiveShadow {...meshProps}>
            <meshStandardMaterial color={piece.color} roughness={0.6} metalness={0.1} />
          </mesh>
        );
      })}
      {buildResult.details.map((d, i) => {
        if (d.type === 'fitting') {
          return (
            <mesh key={`f${i}`} geometry={d.geometry} position={d.position} rotation={d.rotation}>
              <meshStandardMaterial color={d.color} roughness={0.4} metalness={0.2} />
            </mesh>
          );
        }
        return null;
      })}
    </group>
  );
}

function buildPipeline3D(localPts, params) {
  const pieces = [];
  const details = [];
  const pipeType = params?.pipe_type || 'water';
  const diameter = params?.diameter_mm || 300;
  const color = INFRA_COLORS[pipeType] || INFRA_COLORS.water;

  for (let i = 0; i < localPts.length - 1; i++) {
    const seg = generatePipeSegment(localPts[i], localPts[i + 1], diameter);
    pieces.push({ geometry: seg.geometry, color, position: seg.position, quaternion: seg.quaternion });
  }

  // Manholes at ends
  for (const pt of [localPts[0], localPts[localPts.length - 1]]) {
    if (pt) {
      const mh = generateManhole(pt, params?.manhole_depth_m || 2.5);
      pieces.push({ geometry: mh.geometry, color: '#444444', position: mh.position });
    }
  }

  return { pieces, details };
}

// ─── Ground plane ──────────────────────────────────────────────────────────
function Ground() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]} receiveShadow>
      <planeGeometry args={[600, 600]} />
      <meshStandardMaterial color="#1a1a1a" roughness={1} />
    </mesh>
  );
}

// ─── 3D Scene ──────────────────────────────────────────────────────────────
function InfraScene({ alignment, infraType, params, controlsRef }) {
  return (
    <>
      <ambientLight intensity={0.4} />
      <directionalLight position={[60, 120, 60]} intensity={1.2} castShadow shadow-mapSize-width={1024} shadow-mapSize-height={1024} />
      <directionalLight position={[-40, 60, -40]} intensity={0.4} />
      <OrbitControls ref={controlsRef} enablePan minDistance={5} maxDistance={500} maxPolarAngle={Math.PI / 2 - 0.02} />
      <Suspense fallback={null}>
        <InfrastructureMesh alignment={alignment} infraType={infraType} params={params} />
      </Suspense>
      <Ground />
    </>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────
export default function InfrastructureViewer({
  isOpen,
  onClose,
  alignment,
  infraType,
  infraParams,
  isPanelOpen,
  isSidebarCollapsed,
  isChatExpanded,
  projectId,
  network,
  onNetworkChange,
  // DXF pipeline network props
  pipelineData,
  onPipelineDataChange,
  assetType,
  modelParams,
}) {
  // ── DXF network state (when pipelineData is provided) ──
  const [dxfSelectedItem, setDxfSelectedItem] = useState(null);
  const [localPipelineData, setLocalPipelineData] = useState(null);
  const [isDxfDirty, setIsDxfDirty] = useState(false);

  const activePipelineData = localPipelineData ?? pipelineData ?? null;

  const handleDxfSelect = useCallback((item) => {
    setDxfSelectedItem((prev) => (prev === item ? null : item));
  }, []);

  const handleDxfSave = useCallback((updatedItem) => {
    if (!activePipelineData) return;
    const updateList = (list) => list.map((it) => (it === dxfSelectedItem ? { ...it, ...updatedItem } : it));
    const updated = {
      ...activePipelineData,
      pipes:    updateList(activePipelineData.pipes ?? []),
      manholes: updateList(activePipelineData.manholes ?? []),
      valves:   updateList(activePipelineData.valves ?? []),
    };
    setLocalPipelineData(updated);
    setDxfSelectedItem(null);
    setIsDxfDirty(true);
    onPipelineDataChange?.(updated);
  }, [activePipelineData, dxfSelectedItem, onPipelineDataChange]);

  // If we have DXF pipeline data, render the dedicated network viewer
  if (isOpen && activePipelineData?.type === 'pipeline_network') {
    const sidebarW = isSidebarCollapsed ? 52 : 160;
    const panelW   = isPanelOpen ? 380 : 0;
    const chatH    = isChatExpanded ? 328 : 48;
    return createPortal(
      <div style={{ position:'fixed', top:0, left:sidebarW, right:panelW, bottom:chatH,
        background:'#111', zIndex:6, transition:'left 0.3s,right 0.3s,bottom 0.3s', display:'flex', flexDirection:'column' }}>
        {/* Header */}
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between',
          padding:'8px 16px', background:'rgba(0,0,0,0.6)', zIndex:10, flexShrink:0 }}>
          <span style={{ color:'#eee', fontWeight:600 }}>Pipeline Network Viewer</span>
          <div style={{ display:'flex', gap:8 }}>
            {isDxfDirty && (
              <button onClick={() => { onPipelineDataChange?.(localPipelineData); setIsDxfDirty(false); }}
                style={{ background:'#2196f3', border:'none', color:'#fff', borderRadius:4, padding:'4px 12px', cursor:'pointer', fontSize:12 }}>
                Save changes
              </button>
            )}
            <button onClick={onClose}
              style={{ background:'none', border:'1px solid #555', color:'#eee', borderRadius:4, padding:'4px 10px', cursor:'pointer', fontSize:12 }}>
              ✕
            </button>
          </div>
        </div>
        {/* Canvas area */}
        <div style={{ flex:1, position:'relative', overflow:'hidden' }}>
          <Canvas camera={{ position:[0,30,60], fov:55 }} shadows gl={{ antialias:true }}
            onPointerMissed={() => setDxfSelectedItem(null)}>
            <Suspense fallback={null}>
              <DxfNetworkScene pipelineData={activePipelineData} selectedItem={dxfSelectedItem} onSelect={handleDxfSelect} />
            </Suspense>
          </Canvas>
          {dxfSelectedItem && (
            <DxfEditPanel item={dxfSelectedItem} onClose={() => setDxfSelectedItem(null)} onSave={handleDxfSave} />
          )}
          <DxfStatsBar pipelineData={activePipelineData} />
        </div>
      </div>,
      document.body,
    );
  }
  const controlsRef = useRef(null);
  const params = infraParams || {};

  // View state
  const [viewMode, setViewMode] = useState('model_3d');
  const [editMode, setEditMode] = useState(false);
  const [showCatalog, setShowCatalog] = useState(false);

  // Version control state
  const [currentBranch, setCurrentBranch] = useState(null);
  const [branches, setBranches] = useState([]);
  const [versions, setVersions] = useState([]);
  const [currentVersion, setCurrentVersion] = useState(null);
  const [isDirty, setIsDirty] = useState(false);
  const [showCommitModal, setShowCommitModal] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showBranchInput, setShowBranchInput] = useState(false);
  const [branchName, setBranchName] = useState('');

  // Load branches
  useEffect(() => {
    if (!projectId || !isOpen) return;
    listBranches(projectId).then(async (data) => {
      if (data?.length > 0) {
        setBranches(data);
        if (!currentBranch) setCurrentBranch(data[0]);
      } else {
        try {
          const branch = await createBranch(projectId, 'main', null);
          setBranches([branch]);
          setCurrentBranch(branch);
        } catch (e) {
          console.error('Failed to create main branch:', e);
        }
      }
    }).catch(() => {});
  }, [projectId, isOpen]);

  // Load versions
  useEffect(() => {
    if (!currentBranch) return;
    listVersions(currentBranch.id).then((data) => {
      setVersions(data || []);
      if (data?.length > 0) setCurrentVersion(data[0]);
    }).catch(() => {});
  }, [currentBranch]);

  const handleCommit = useCallback(async (message) => {
    if (!currentBranch) return;
    try {
      const result = await commitVersion(currentBranch.id, {
        infraParams: params,
        network,
        message,
      });
      setCurrentVersion(result);
      setVersions((prev) => [result, ...prev]);
      setIsDirty(false);
      setShowCommitModal(false);
    } catch (err) {
      console.error('Commit failed:', err);
    }
  }, [currentBranch, params, network]);

  const handleSelectVersion = useCallback((version) => {
    setCurrentVersion(version);
    setShowHistory(false);
  }, []);

  const handleSwitchBranch = useCallback((branch) => {
    setCurrentBranch(branch);
    setShowHistory(false);
  }, []);

  const handleCreateBranch = useCallback(async () => {
    if (!projectId || !branchName.trim()) return;
    try {
      const branch = await createBranch(projectId, branchName.trim(), currentVersion?.id);
      setBranches((prev) => [...prev, branch]);
      setCurrentBranch(branch);
      setBranchName('');
      setShowBranchInput(false);
    } catch (err) {
      console.error('Branch creation failed:', err);
    }
  }, [projectId, branchName, currentVersion]);

  if (!isOpen) return null;

  const sidebarW = isSidebarCollapsed ? 52 : 160;
  const panelW = isPanelOpen ? 380 : 0;
  const chatH = isChatExpanded ? 328 : 48;

  const closeBtn = createPortal(
    <button
      className="model-close-btn"
      onPointerDown={(e) => { e.stopPropagation(); e.preventDefault(); onClose(); }}
      aria-label="Close viewer"
      style={{
        position: 'fixed',
        top: 12,
        right: (isPanelOpen ? 380 : 0) + 16,
        zIndex: 99999,
        transition: 'right 0.3s ease',
      }}
    >x</button>,
    document.body
  );

  const is2DEditor = editMode && (viewMode === 'plan' || viewMode === 'model_3d');
  const showProfile = viewMode === 'profile';

  return (
    <>
      {closeBtn}
      <div className="model-overlay" />
      <div
        className="model-canvas-area infra-canvas-area"
        style={{
          position: 'fixed',
          top: is2DEditor ? 68 : 0,
          left: sidebarW,
          right: panelW,
          bottom: chatH,
          zIndex: 6,
          transition: 'left 0.3s ease, right 0.3s ease, bottom 0.3s ease',
        }}
      >
        {is2DEditor ? (
          <PipeNetworkEditor
            network={network}
            onNetworkChange={(newNet) => { onNetworkChange?.(newNet); setIsDirty(true); }}
          />
        ) : showProfile ? (
          <ProfileView segments={network?.segments} alignment={alignment} />
        ) : (
          <Canvas
            camera={{ position: [0, 30, 60], fov: 45 }}
            shadows
            style={{ width: '100%', height: '100%', background: 'transparent' }}
            eventPrefix="client"
          >
            <InfraScene
              alignment={alignment}
              infraType={infraType || 'pipeline'}
              params={params}
              controlsRef={controlsRef}
            />
          </Canvas>
        )}

        {/* Commit modal */}
        {showCommitModal && (
          <CommitModal
            onCommit={handleCommit}
            onCancel={() => setShowCommitModal(false)}
          />
        )}

        {/* History panel */}
        {showHistory && (
          <HistoryPanel
            versions={versions}
            branches={branches}
            currentBranch={currentBranch}
            onSelectVersion={handleSelectVersion}
            onSwitchBranch={handleSwitchBranch}
            onClose={() => setShowHistory(false)}
          />
        )}

        {/* Catalog */}
        {showCatalog && editMode && (
          <InfrastructureCatalog mode={infraType} />
        )}
      </div>

      {/* Controls bar */}
      <div
        className="model-controls infra-controls"
        style={{
          position: 'fixed',
          left: sidebarW,
          right: panelW,
          bottom: chatH,
          zIndex: 7,
          transition: 'left 0.3s ease, right 0.3s ease, bottom 0.3s ease',
        }}
      >
        {/* Version control bar */}
        {projectId && (
          <div className="version-control-bar">
            <select
              className="branch-selector"
              value={currentBranch?.id || ''}
              onChange={(e) => {
                const b = branches.find((br) => br.id === e.target.value);
                if (b) setCurrentBranch(b);
              }}
            >
              {branches.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
            {currentVersion && (
              <span className="version-info">
                v{currentVersion.version_number} "{currentVersion.message}"
              </span>
            )}
            {currentVersion && <ComplianceBadge status={currentVersion.compliance_status} />}
            {isDirty && <span className="dirty-indicator">Modified</span>}
            <div className="version-actions">
              {isDirty && (
                <button className="model-ctrl-btn commit-btn" onClick={() => setShowCommitModal(true)}>
                  Commit
                </button>
              )}
              {showBranchInput ? (
                <span className="branch-input-group">
                  <input
                    type="text"
                    className="branch-name-input"
                    value={branchName}
                    onChange={(e) => setBranchName(e.target.value)}
                    placeholder="Branch name"
                    onKeyDown={(e) => e.key === 'Enter' && handleCreateBranch()}
                  />
                  <button className="model-ctrl-btn" onClick={handleCreateBranch}>Create</button>
                  <button className="model-ctrl-btn" onClick={() => setShowBranchInput(false)}>x</button>
                </span>
              ) : (
                <button className="model-ctrl-btn" onClick={() => setShowBranchInput(true)}>
                  New Branch
                </button>
              )}
              <button className="model-ctrl-btn" onClick={() => setShowHistory(!showHistory)}>
                History {showHistory ? '\u25b4' : '\u25be'}
              </button>
            </div>
          </div>
        )}

        {/* View mode + controls */}
        <div className="infra-controls-row">
          <div className="infra-view-toggle">
            {[
              { key: 'model_3d', label: '3D Model' },
              { key: 'plan', label: 'Plan' },
              { key: 'profile', label: 'Profile' },
            ].map((mode) => (
              <button
                key={mode.key}
                className={`model-ctrl-btn ${viewMode === mode.key ? 'active' : ''}`}
                onClick={() => setViewMode(mode.key)}
                disabled={mode.disabled}
              >
                {mode.label}
              </button>
            ))}
          </div>

          {/* Edit mode toggle */}
          <label className="infra-edit-toggle">
            <input
              type="checkbox"
              checked={editMode}
              onChange={(e) => setEditMode(e.target.checked)}
            />
            Edit
          </label>

          {editMode && (
            <button
              className={`model-ctrl-btn ${showCatalog ? 'active' : ''}`}
              onClick={() => setShowCatalog(!showCatalog)}
            >
              Catalog
            </button>
          )}

          {/* Reset camera */}
          {viewMode === 'model_3d' && (
            <button
              className="model-ctrl-btn"
              onClick={() => {
                if (controlsRef.current) {
                  controlsRef.current.object.position.set(0, 30, 60);
                  controlsRef.current.target.set(0, 0, 0);
                  controlsRef.current.update();
                }
              }}
              title="Reset camera"
            >
              Reset
            </button>
          )}

          <span className="infra-info">
            Pipeline Network
            {params?.pipe_type ? ` \u00b7 ${params.pipe_type}` : ''}
          </span>
        </div>
      </div>
    </>
  );
}
