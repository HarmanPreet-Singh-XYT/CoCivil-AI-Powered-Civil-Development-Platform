import { useState, useRef, useMemo, useCallback, useEffect, Suspense } from 'react';
import { createPortal } from 'react-dom';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import {
  extractFootprint,
  shrinkPolygon,
  makeCircularFootprint,
  subdivideFootprintIntoUnits,
} from '../lib/buildingGeometry.js';
import BlueprintOverlay from './BlueprintOverlay.jsx';
import FloorPlanView from './FloorPlanView.jsx';
import FloorPlanEditor from './floorplan/FloorPlanEditor.jsx';
import {
  createBranch,
  listBranches,
  commitVersion,
  listVersions,
  getUploadPages,
} from '../api.js';
import '../ModelViewer.css';

const DEFAULT_PARAMS = {
  storeys: 10,
  podium_storeys: 0,
  height_m: 35,
  setback_m: 0,
  typology: 'midrise',
  footprint_coverage: 0.6,
  unit_width: null,
  tower_shape: null,
};

const FLOOR_H = 3.3;
const FLOOR_GAP = 0.2;
const GROUND_FLOOR_H = 4.5;

const COLORS = {
  podium: '#8a7553',
  retail: '#6b5b3a',
  floor_even: '#c8a55c',
  floor_odd: '#d4b87a',
  townhouse_a: '#c8a55c',
  townhouse_b: '#a08040',
  townhouse_c: '#b89850',
  tower: '#c8a55c',
};

const COMPLIANCE_BADGES = {
  as_of_right: { color: '#4a7c59', label: 'As-of-right' },
  needs_variance: { color: '#c8a55c', label: 'Minor variance' },
  needs_rezoning: { color: '#c44', label: 'Rezoning required' },
  blocked: { color: '#c44', label: 'Blocked' },
  unknown: { color: '#666', label: 'Unknown' },
};

// ─── Helpers ────────────────────────────────────────────────────────────────────

function makeShapeFromPoints(pts) {
  const shape = new THREE.Shape();
  shape.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) shape.lineTo(pts[i][0], pts[i][1]);
  shape.closePath();
  return shape;
}

function makeFloorSlab(shape, floorH, yOffset) {
  const geo = new THREE.ExtrudeGeometry(shape, { depth: floorH, bevelEnabled: false });
  geo.rotateX(-Math.PI / 2);
  geo.translate(0, yOffset, 0);
  return geo;
}

function scaleFootprint(footprint, coverage) {
  return footprint.map(([x, z]) => [x * coverage, z * coverage]);
}

// ─── Typology builders ──────────────────────────────────────────────────────────

function buildMidrise(footprint, p) {
  const fp = scaleFootprint(footprint, p.footprint_coverage ?? 0.6);
  const shape = makeShapeFromPoints(fp);
  const storeys = p.storeys || 6;
  const pieces = [];
  let y = 0;
  for (let i = 0; i < storeys; i++) {
    pieces.push({
      geometry: makeFloorSlab(shape, FLOOR_H, y),
      color: i % 2 === 0 ? COLORS.floor_even : COLORS.floor_odd,
    });
    y += FLOOR_H + FLOOR_GAP;
  }
  return pieces;
}

function buildTowerOnPodium(footprint, p) {
  const fp = scaleFootprint(footprint, p.footprint_coverage ?? 0.45);
  const podiumShape = makeShapeFromPoints(fp);
  const podiumStoreys = p.podium_storeys || 3;
  const totalStoreys = p.storeys || 20;
  const towerStoreys = Math.max(0, totalStoreys - podiumStoreys);
  const pieces = [];

  let y = 0;
  for (let i = 0; i < podiumStoreys; i++) {
    const h = i === 0 ? GROUND_FLOOR_H : FLOOR_H;
    pieces.push({
      geometry: makeFloorSlab(podiumShape, h, y),
      color: i === 0 ? COLORS.retail : COLORS.podium,
    });
    y += h + FLOOR_GAP;
  }

  if (towerStoreys > 0) {
    const setback = p.setback_m || 3;
    const towerFP = shrinkPolygon(fp, setback);
    const towerShape = makeShapeFromPoints(towerFP);
    for (let i = 0; i < towerStoreys; i++) {
      pieces.push({
        geometry: makeFloorSlab(towerShape, FLOOR_H, y),
        color: i % 2 === 0 ? COLORS.floor_even : COLORS.floor_odd,
      });
      y += FLOOR_H + FLOOR_GAP;
    }
  }

  return pieces;
}

function buildPointTower(footprint, p) {
  const totalStoreys = p.storeys || 30;
  const pieces = [];
  let fp;

  if (p.tower_shape === 'circular') {
    const scaled = scaleFootprint(footprint, p.footprint_coverage ?? 0.45);
    let maxR = 0;
    for (const [x, z] of scaled) {
      const r = Math.sqrt(x * x + z * z);
      if (r > maxR) maxR = r;
    }
    fp = makeCircularFootprint(maxR * 0.5, 24);
  } else {
    const scaled = scaleFootprint(footprint, p.footprint_coverage ?? 0.45);
    fp = shrinkPolygon(scaled, 2);
  }

  const shape = makeShapeFromPoints(fp);
  let y = 0;
  for (let i = 0; i < totalStoreys; i++) {
    pieces.push({
      geometry: makeFloorSlab(shape, FLOOR_H, y),
      color: i % 2 === 0 ? COLORS.floor_even : COLORS.floor_odd,
    });
    y += FLOOR_H + FLOOR_GAP;
  }
  return pieces;
}

function buildTownhouse(footprint, p) {
  const fp = scaleFootprint(footprint, p.footprint_coverage ?? 0.55);
  const unitWidth = p.unit_width || 6;
  const storeys = p.storeys || 3;
  const units = subdivideFootprintIntoUnits(fp, unitWidth);
  const unitColors = [COLORS.townhouse_a, COLORS.townhouse_b, COLORS.townhouse_c];
  const pieces = [];

  for (const unit of units) {
    const shrunk = unit.points.map(([x, z], idx) => {
      if (idx === unit.points.length - 1) return [x + 0.1, z];
      const xAdj = unit.index === 0 ? x : x + 0.1;
      return [xAdj, z];
    });
    const shape = makeShapeFromPoints(shrunk);
    const color = unitColors[unit.index % unitColors.length];

    let y = 0;
    for (let f = 0; f < storeys; f++) {
      pieces.push({
        geometry: makeFloorSlab(shape, FLOOR_H, y),
        color,
      });
      y += FLOOR_H + FLOOR_GAP;
    }
  }
  return pieces;
}

function buildSlab(footprint, p) {
  const fp = scaleFootprint(footprint, p.footprint_coverage ?? 0.6);
  const shape = makeShapeFromPoints(fp);
  const storeys = p.storeys || 10;
  const pieces = [];
  let y = 0;
  for (let i = 0; i < storeys; i++) {
    pieces.push({
      geometry: makeFloorSlab(shape, FLOOR_H, y),
      color: i % 2 === 0 ? COLORS.floor_even : COLORS.floor_odd,
    });
    y += FLOOR_H + FLOOR_GAP;
  }
  return pieces;
}

function buildMixedUseMidrise(footprint, p) {
  const fp = scaleFootprint(footprint, p.footprint_coverage ?? 0.6);
  const shape = makeShapeFromPoints(fp);
  const storeys = p.storeys || 6;
  const pieces = [];
  let y = 0;
  for (let i = 0; i < storeys; i++) {
    const h = i === 0 ? GROUND_FLOOR_H : FLOOR_H;
    const color = i === 0 ? COLORS.retail : (i % 2 === 0 ? COLORS.floor_even : COLORS.floor_odd);
    pieces.push({
      geometry: makeFloorSlab(shape, h, y),
      color,
    });
    y += h + FLOOR_GAP;
  }
  return pieces;
}

function buildRealBuilding(footprint, p) {
  const shape = makeShapeFromPoints(footprint);
  const totalH = p.height_m || 35;
  const geo = new THREE.ExtrudeGeometry(shape, { depth: totalH, bevelEnabled: false });
  geo.rotateX(-Math.PI / 2);
  return [{ geometry: geo, color: COLORS.tower }];
}

const TYPOLOGY_BUILDERS = {
  midrise: buildMidrise,
  tower_on_podium: buildTowerOnPodium,
  point_tower: buildPointTower,
  townhouse: buildTownhouse,
  slab: buildSlab,
  mixed_use_midrise: buildMixedUseMidrise,
  real_building: buildRealBuilding,
};

// ─── Building mesh ─────────────────────────────────────────────────────────────

function BuildingMesh({ parcelGeoJSON, params }) {
  const p = params || DEFAULT_PARAMS;

  const pieces = useMemo(() => {
    const footprint = extractFootprint(parcelGeoJSON);
    const isRealBuilding = p.typology === 'real_building' || (p.footprint_coverage ?? 0) >= 1.0;
    const typology = isRealBuilding ? 'real_building' : (p.typology || 'midrise');
    const builder = TYPOLOGY_BUILDERS[typology] || TYPOLOGY_BUILDERS.midrise;
    return builder(footprint, p);
  }, [parcelGeoJSON, p]);

  return (
    <group>
      {pieces.map((piece, i) => (
        <mesh key={i} geometry={piece.geometry} castShadow receiveShadow>
          <meshStandardMaterial color={piece.color} roughness={0.6} metalness={0.1} />
        </mesh>
      ))}
    </group>
  );
}

// ─── Ground plane ──────────────────────────────────────────────────────────────

function Ground() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]} receiveShadow>
      <planeGeometry args={[600, 600]} />
      <meshStandardMaterial color="#1a1a1a" roughness={1} />
    </mesh>
  );
}

// ─── Scene wrapper ─────────────────────────────────────────────────────────────

function Scene({
  parcelGeoJSON,
  params,
  controlsRef,
  viewMode,
  floorPlans,
  blueprintPages,
  activeFloor,
  selectedRoom,
  onRoomClick,
}) {
  return (
    <>
      <ambientLight intensity={0.4} />
      <directionalLight
        position={[60, 120, 60]}
        intensity={1.2}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      <directionalLight position={[-40, 60, -40]} intensity={0.4} />

      <OrbitControls
        ref={controlsRef}
        enablePan={false}
        minDistance={10}
        maxDistance={400}
        maxPolarAngle={Math.PI / 2 - 0.02}
      />

      <Suspense fallback={null}>
        {viewMode === 'massing' && (
          <BuildingMesh parcelGeoJSON={parcelGeoJSON} params={params} />
        )}
        {viewMode === 'interior' && floorPlans && (
          <FloorPlanView
            floorPlans={floorPlans}
            activeFloor={activeFloor}
            selectedRoom={selectedRoom}
            onRoomClick={onRoomClick}
          />
        )}
        {viewMode === 'blueprint' && blueprintPages?.length > 0 && (
          <BlueprintOverlay
            pages={blueprintPages}
            activeFloor={activeFloor}
          />
        )}
      </Suspense>

      <Ground />
    </>
  );
}

// ─── Compliance badge ──────────────────────────────────────────────────────────

function ComplianceBadge({ status }) {
  const badge = COMPLIANCE_BADGES[status] || COMPLIANCE_BADGES.unknown;
  return (
    <span className="compliance-badge" style={{ color: badge.color }}>
      <span className="compliance-dot" style={{ backgroundColor: badge.color }} />
      {badge.label}
    </span>
  );
}

// ─── Commit Modal ──────────────────────────────────────────────────────────────

function CommitModal({ onCommit, onCancel, changeSummary }) {
  const [message, setMessage] = useState('Design update');

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
            onClick={() => onCommit(message || 'Design update')}
            disabled={!message.trim()}
          >
            Commit
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── History Panel ─────────────────────────────────────────────────────────────

function HistoryPanel({ versions, branches, currentBranch, onSelectVersion, onSwitchBranch, onClose }) {
  return (
    <div className="history-panel">
      <div className="history-header">
        <span>Version History — {currentBranch?.name || 'main'}</span>
        <button className="history-close" onClick={onClose}>×</button>
      </div>
      <div className="history-list">
        {versions.map((v) => {
          const badge = COMPLIANCE_BADGES[v.compliance_status] || COMPLIANCE_BADGES.unknown;
          return (
            <div
              key={v.id}
              className="history-item"
              onClick={() => onSelectVersion(v)}
            >
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

// ─── Room info panel ───────────────────────────────────────────────────────────

function RoomInfoPanel({ room, onClose }) {
  if (!room) return null;
  return (
    <div className="room-info-panel">
      <div className="room-info-header">
        <span>{room.name}</span>
        <button onClick={onClose}>×</button>
      </div>
      <div className="room-info-body">
        <div><span className="room-info-label">Type:</span> {room.type}</div>
        <div><span className="room-info-label">Area:</span> {room.area_m2?.toFixed(1)} m²</div>
        <div><span className="room-info-label">Floor:</span> {room.floor}</div>
      </div>
    </div>
  );
}

// ─── Main modal ────────────────────────────────────────────────────────────────

export default function ModelViewer({
  isOpen, onClose, parcelGeoJSON, modelParams, isPanelOpen, isSidebarCollapsed, isChatExpanded,
  floorPlans, blueprintPages: blueprintPagesProp, projectId, parcelId,
}) {
  const controlsRef = useRef(null);
  const params = modelParams || DEFAULT_PARAMS;

  // View state
  const [viewMode, setViewMode] = useState('massing');
  const [activeFloor, setActiveFloor] = useState(null);
  const [selectedRoom, setSelectedRoom] = useState(null);

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

  // Track uncommitted changes
  const [uncommittedFloorPlans, setUncommittedFloorPlans] = useState(null);
  const [uncommittedModelParams, setUncommittedModelParams] = useState(null);
  const [blueprintPages, setBlueprintPages] = useState(blueprintPagesProp || []);

  const embeddedBlueprintPages = useMemo(() => {
    if (blueprintPagesProp?.length) return blueprintPagesProp;
    if (floorPlans?.blueprint_pages?.length) return floorPlans.blueprint_pages;
    if (floorPlans?.pages?.length) return floorPlans.pages;
    return [];
  }, [blueprintPagesProp, floorPlans]);

  // Load branches when projectId changes
  useEffect(() => {
    if (!projectId || !isOpen) return;
    listBranches(projectId).then((data) => {
      setBranches(data || []);
      if (data?.length > 0 && !currentBranch) {
        setCurrentBranch(data[0]);
      }
    }).catch(() => {});
  }, [projectId, isOpen]);

  useEffect(() => {
    if (!isOpen) return undefined;
    if (embeddedBlueprintPages.length > 0) {
      setBlueprintPages(embeddedBlueprintPages);
      return undefined;
    }
    if (!projectId) {
      setBlueprintPages([]);
      return undefined;
    }

    let isCancelled = false;
    getUploadPages(projectId)
      .then((pages) => {
        if (!isCancelled) setBlueprintPages(pages || []);
      })
      .catch(() => {
        if (!isCancelled) setBlueprintPages([]);
      });

    return () => {
      isCancelled = true;
    };
  }, [embeddedBlueprintPages, isOpen, projectId]);

  // Load versions when branch changes
  useEffect(() => {
    if (!currentBranch) return;
    listVersions(currentBranch.id).then((data) => {
      setVersions(data || []);
      if (data?.length > 0) {
        setCurrentVersion(data[0]);
      }
    }).catch(() => {});
  }, [currentBranch]);

  // Detect dirty state
  useEffect(() => {
    if (!currentVersion) {
      setIsDirty(false);
      return;
    }
    const paramsChanged = JSON.stringify(modelParams) !== JSON.stringify(currentVersion.model_params);
    const plansChanged = floorPlans && JSON.stringify(floorPlans) !== JSON.stringify(currentVersion.floor_plans);
    setIsDirty(paramsChanged || plansChanged);
    if (paramsChanged) setUncommittedModelParams(modelParams);
    if (plansChanged) setUncommittedFloorPlans(floorPlans);
  }, [modelParams, floorPlans, currentVersion]);

  const handleCommit = useCallback(async (message) => {
    if (!currentBranch) return;
    try {
      const result = await commitVersion(currentBranch.id, {
        floorPlans: floorPlans || uncommittedFloorPlans,
        modelParams: modelParams || uncommittedModelParams,
        message,
        parcelId,
      });
      setCurrentVersion(result);
      setVersions((prev) => [result, ...prev]);
      setIsDirty(false);
      setShowCommitModal(false);
      setUncommittedFloorPlans(null);
      setUncommittedModelParams(null);
    } catch (err) {
      console.error('Commit failed:', err);
    }
  }, [currentBranch, floorPlans, modelParams, parcelId, uncommittedFloorPlans, uncommittedModelParams]);

  const handleFloorPlansChange = useCallback((newPlans) => {
    setUncommittedFloorPlans(newPlans);
    setIsDirty(true);
  }, []);

  const handleDiscard = useCallback(() => {
    if (!currentVersion) return;
    if (!window.confirm('Discard all uncommitted changes?')) return;
    setIsDirty(false);
    setUncommittedFloorPlans(null);
    setUncommittedModelParams(null);
  }, [currentVersion]);

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

  const handleSelectVersion = useCallback((version) => {
    setCurrentVersion(version);
    setShowHistory(false);
  }, []);

  const handleSwitchBranch = useCallback((branch) => {
    setCurrentBranch(branch);
    setShowHistory(false);
  }, []);

  // Change summary for commit modal
  const changeSummary = useMemo(() => {
    if (!currentVersion || !modelParams) return null;
    const oldP = currentVersion.model_params || {};
    const changes = [];
    for (const key of ['height_m', 'storeys', 'footprint_coverage', 'typology', 'setback_m']) {
      if (oldP[key] !== modelParams[key] && modelParams[key] != null) {
        const label = key.replace(/_/g, ' ');
        changes.push(`${label}: ${oldP[key] ?? '–'} → ${modelParams[key]}`);
      }
    }
    return changes.length > 0 ? changes.join('; ') : null;
  }, [currentVersion, modelParams]);

  const hasFloorPlans = floorPlans?.floor_plans?.length > 0;
  const hasBlueprintPages = blueprintPages.length > 0;
  const selectableFloors = useMemo(() => {
    if (floorPlans?.floor_plans?.length) {
      return floorPlans.floor_plans.map((fp) => fp.floor_number);
    }
    if (blueprintPages.length > 0) {
      return blueprintPages.map((_, idx) => idx + 1);
    }
    return [];
  }, [blueprintPages, floorPlans]);

  useEffect(() => {
    if (viewMode === 'interior' && !hasFloorPlans) {
      setViewMode(hasBlueprintPages ? 'blueprint' : 'massing');
      setSelectedRoom(null);
    }
    if (viewMode === 'blueprint' && !hasBlueprintPages) {
      setViewMode(hasFloorPlans ? 'interior' : 'massing');
    }
    if (viewMode === 'floorplan' && !hasFloorPlans) {
      setViewMode('massing');
    }
  }, [hasBlueprintPages, hasFloorPlans, viewMode]);

  if (!isOpen) return null;

  const totalH = Math.round(params.height_m || 0);
  const storeys = params.storeys || 0;
  const warnings = params.warnings || [];

  const closeBtn = createPortal(
    <button
      className="model-close-btn"
      onPointerDown={(e) => { e.stopPropagation(); e.preventDefault(); onClose(); }}
      aria-label="Close model"
      style={{
        position: 'fixed',
        top: 12,
        right: (isPanelOpen ? 380 : 0) + 16,
        zIndex: 99999,
        transition: 'right 0.3s ease',
      }}
    >✕</button>,
    document.body
  );

  const sidebarW = isSidebarCollapsed ? 52 : 160;
  const panelW = isPanelOpen ? 380 : 0;
  const chatH = isChatExpanded ? 328 : 48;

  return (
    <>
      {closeBtn}
      <div className="model-overlay" />
      <div
        className="model-canvas-area"
        style={{
          position: 'fixed',
          top: viewMode === 'floorplan' ? 68 : 0,
          left: sidebarW,
          right: panelW,
          bottom: chatH,
          zIndex: 6,
          transition: 'left 0.3s ease, right 0.3s ease, bottom 0.3s ease',
        }}
      >
        {viewMode === 'floorplan' ? (
          <FloorPlanEditor
            floorPlans={uncommittedFloorPlans || floorPlans}
            activeFloor={activeFloor}
            onFloorPlansChange={handleFloorPlansChange}
            parcelId={parcelId}
          />
        ) : (
          <Canvas
            camera={{ position: [0, 40, 80], fov: 45 }}
            shadows
            style={{ width: '100%', height: '100%', background: 'transparent' }}
            eventPrefix="client"
          >
            <Scene
              parcelGeoJSON={parcelGeoJSON}
              params={params}
              controlsRef={controlsRef}
              viewMode={viewMode}
              floorPlans={uncommittedFloorPlans || floorPlans}
              blueprintPages={blueprintPages}
              activeFloor={activeFloor}
              selectedRoom={selectedRoom}
              onRoomClick={setSelectedRoom}
            />
          </Canvas>
        )}

        {/* Room info panel */}
        <RoomInfoPanel room={selectedRoom} onClose={() => setSelectedRoom(null)} />

        {/* Commit modal */}
        {showCommitModal && (
          <CommitModal
            onCommit={handleCommit}
            onCancel={() => setShowCommitModal(false)}
            changeSummary={changeSummary}
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
      </div>

      {/* Controls bar */}
      <div
        className="model-controls"
        style={{
          position: 'fixed',
          left: sidebarW,
          right: panelW,
          bottom: chatH,
          zIndex: 7,
          transition: 'left 0.3s ease, right 0.3s ease, bottom 0.3s ease',
          flexDirection: 'column',
          gap: 0,
        }}
      >
        {/* Version control bar */}
        {projectId && (
          <div className="version-control-bar">
            {/* Branch selector */}
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

            {/* Current version info */}
            {currentVersion && (
              <span className="version-info">
                v{currentVersion.version_number} "{currentVersion.message}"
              </span>
            )}

            {/* Compliance badge */}
            {currentVersion && <ComplianceBadge status={currentVersion.compliance_status} />}

            {/* Dirty indicator */}
            {isDirty && <span className="dirty-indicator">Modified</span>}

            {/* Actions */}
            <div className="version-actions">
              {isDirty && (
                <>
                  <button className="model-ctrl-btn commit-btn" onClick={() => setShowCommitModal(true)}>
                    Commit
                  </button>
                  <button className="model-ctrl-btn" onClick={handleDiscard}>
                    Discard
                  </button>
                </>
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
                  <button className="model-ctrl-btn" onClick={() => setShowBranchInput(false)}>×</button>
                </span>
              ) : (
                <button className="model-ctrl-btn" onClick={() => setShowBranchInput(true)}>
                  New Branch
                </button>
              )}

              <button
                className="model-ctrl-btn"
                onClick={() => setShowHistory(!showHistory)}
              >
                History {showHistory ? '▴' : '▾'}
              </button>
            </div>
          </div>
        )}

        {/* View mode + floor selector + existing controls */}
        <div className="model-controls-row">
          {/* View mode toggles */}
          <div className="view-mode-toggle">
            {[
              { key: 'massing', disabled: false, title: '' },
              { key: 'interior', disabled: !hasFloorPlans, title: 'Upload a DXF to view interior' },
              { key: 'floorplan', disabled: !hasFloorPlans, title: 'Edit floor plan (2D)' },
            ].map((mode) => (
              <button
                key={mode.key}
                className={`model-ctrl-btn ${viewMode === mode.key ? 'active' : ''}`}
                onClick={() => {
                  setViewMode(mode.key);
                  if (mode.key !== 'interior') setSelectedRoom(null);
                }}
                disabled={mode.disabled}
                title={mode.disabled ? mode.title : ''}
              >
                {mode.key.charAt(0).toUpperCase() + mode.key.slice(1)}
              </button>
            ))}
          </div>

          {/* Floor selector */}
          {selectableFloors.length > 0 && viewMode !== 'massing' && (
            <div className="floor-selector">
              <button
                className={`model-ctrl-btn floor-btn ${activeFloor === null ? 'active' : ''}`}
                onClick={() => setActiveFloor(null)}
              >
                All
              </button>
              {selectableFloors.map((floorNumber) => (
                <button
                  key={floorNumber}
                  className={`model-ctrl-btn floor-btn ${activeFloor === floorNumber ? 'active' : ''}`}
                  onClick={() => setActiveFloor(floorNumber)}
                >
                  F{floorNumber}
                </button>
              ))}
            </div>
          )}

          {/* Reset + info */}
          <button
            className="model-ctrl-btn"
            onClick={() => {
              if (controlsRef.current) {
                controlsRef.current.object.position.set(0, 40, 80);
                controlsRef.current.target.set(0, 0, 0);
                controlsRef.current.update();
              }
            }}
            title="Reset camera"
          >
            ↺ Reset
          </button>
          <span className="model-info">
            {storeys} storeys · {totalH}m
            {params.typology ? ` · ${params.typology.replace(/_/g, ' ')}` : ''}
            {warnings.length > 0 && (
              <span className="model-warnings" title={warnings.join('\n')}>
                {' · ⚠ '}{warnings.length} zone limit{warnings.length > 1 ? 's' : ''} applied
              </span>
            )}
          </span>
        </div>
      </div>
    </>
  );
}
