import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Stage, Layer, Line, Circle, Arrow, Text, Group } from 'react-konva';
import PipeProperties from './PipeProperties.jsx';
import InfrastructureCompliancePanel from './InfrastructureCompliancePanel.jsx';
import './PipeNetworkEditor.css';

const MAX_HISTORY = 50;
const SNAP_GRID = 1; // 1m grid
const MANHOLE_MAX_SPACING = 120; // OPSD max spacing in metres
const PIPE_COLORS = {
  water: '#2277bb',
  sanitary: '#886644',
  storm: '#44aa66',
  gas: '#ddaa22',
};

let _idCounter = 0;
function generateId(prefix) {
  return `${prefix}_${Date.now().toString(36)}_${(++_idCounter).toString(36)}`;
}

function snapToGrid(pt) {
  return [
    Math.round(pt[0] / SNAP_GRID) * SNAP_GRID,
    Math.round(pt[1] / SNAP_GRID) * SNAP_GRID,
  ];
}

function snapToEndpoint(pt, segments, manholes) {
  const threshold = 1.5;
  let closest = pt;
  let minDist = threshold;

  const checkPoint = (p) => {
    const d = Math.hypot(pt[0] - p[0], pt[1] - p[1]);
    if (d < minDist) {
      minDist = d;
      closest = p;
    }
  };

  for (const seg of (segments || [])) {
    checkPoint(seg.start);
    checkPoint(seg.end);
  }
  for (const mh of (manholes || [])) {
    checkPoint(mh.position);
  }

  return closest === pt ? snapToGrid(pt) : closest;
}

function distPt(a, b) {
  return Math.hypot(a[0] - b[0], a[1] - b[1]);
}

export default function PipeNetworkEditor({
  network,
  onNetworkChange,
  parcelId,
}) {
  const stageRef = useRef(null);
  const containerRef = useRef(null);

  const [stageSize, setStageSize] = useState({ width: 800, height: 600 });
  const [stageScale, setStageScale] = useState(5); // pixels per metre
  const [stagePosition, setStagePosition] = useState({ x: 0, y: 0 });

  const [activeTool, setActiveTool] = useState('select');
  const [selectedId, setSelectedId] = useState(null);
  const [selectedType, setSelectedType] = useState(null); // 'segment' | 'manhole' | 'fitting'

  // Pipe drawing state
  const [drawStart, setDrawStart] = useState(null);
  const [drawPreview, setDrawPreview] = useState(null);
  const [drawPipeType, setDrawPipeType] = useState('water');

  // Compliance
  const [complianceResult, setComplianceResult] = useState(null);
  const [showCompliance, setShowCompliance] = useState(true);
  const complianceTimerRef = useRef(null);

  // Undo/redo
  const [editHistory, setEditHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  // Normalize network data
  const net = useMemo(() => ({
    segments: network?.segments || [],
    manholes: network?.manholes || [],
    fittings: network?.fittings || [],
    pipe_type: network?.pipe_type || 'water',
  }), [network]);

  // Selected segment for properties panel
  const selectedSegment = useMemo(() => {
    if (selectedType !== 'segment' || !selectedId) return null;
    return net.segments.find((s) => s.id === selectedId) || null;
  }, [selectedId, selectedType, net.segments]);

  // Resize observer
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setStageSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  // Fit to view on mount
  useEffect(() => {
    const points = [];
    net.segments.forEach((s) => { points.push(s.start, s.end); });
    net.manholes.forEach((m) => { points.push(m.position); });
    if (points.length === 0) {
      setStagePosition({ x: stageSize.width / 2, y: stageSize.height / 2 });
      return;
    }
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const [x, y] of points) {
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
    const dataW = maxX - minX || 1;
    const dataH = maxY - minY || 1;
    const pad = 60;
    const scaleX = (stageSize.width - pad * 2) / dataW;
    const scaleY = (stageSize.height - pad * 2) / dataH;
    const fitScale = Math.min(scaleX, scaleY, 100);
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    setStageScale(fitScale);
    setStagePosition({
      x: stageSize.width / 2 - cx * fitScale,
      y: stageSize.height / 2 - cy * fitScale,
    });
  }, [net, stageSize]);

  // Init history
  useEffect(() => {
    if (network && editHistory.length === 0) {
      setEditHistory([JSON.parse(JSON.stringify(network))]);
      setHistoryIndex(0);
    }
  }, [network]);

  // Debounced compliance check
  const runCompliance = useCallback((data) => {
    if (complianceTimerRef.current) clearTimeout(complianceTimerRef.current);
    complianceTimerRef.current = setTimeout(async () => {
      try {
        const res = await fetch('/api/v1/compliance/infrastructure', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ network: data, parcel_id: parcelId }),
        });
        if (res.ok) setComplianceResult(await res.json());
      } catch { /* silent */ }
    }, 400);
  }, [parcelId]);

  const cloneNet = useCallback(() => JSON.parse(JSON.stringify(network || { segments: [], manholes: [], fittings: [] })), [network]);

  const pushChange = useCallback((newNet) => {
    onNetworkChange?.(newNet);
    setEditHistory((prev) => {
      const trimmed = prev.slice(0, historyIndex + 1);
      const next = [...trimmed, JSON.parse(JSON.stringify(newNet))];
      return next.length > MAX_HISTORY ? next.slice(next.length - MAX_HISTORY) : next;
    });
    setHistoryIndex((prev) => Math.min(prev + 1, MAX_HISTORY - 1));
    runCompliance(newNet);
  }, [onNetworkChange, historyIndex, runCompliance]);

  const undo = useCallback(() => {
    if (historyIndex <= 0) return;
    const idx = historyIndex - 1;
    setHistoryIndex(idx);
    const snap = editHistory[idx];
    onNetworkChange?.(JSON.parse(JSON.stringify(snap)));
  }, [historyIndex, editHistory, onNetworkChange]);

  const redo = useCallback(() => {
    if (historyIndex >= editHistory.length - 1) return;
    const idx = historyIndex + 1;
    setHistoryIndex(idx);
    const snap = editHistory[idx];
    onNetworkChange?.(JSON.parse(JSON.stringify(snap)));
  }, [historyIndex, editHistory, onNetworkChange]);

  // Auto-place manholes based on OPSD spacing
  const autoPlaceManholes = useCallback((data) => {
    const existingMH = [...(data.manholes || [])];
    for (const seg of (data.segments || [])) {
      const len = distPt(seg.start, seg.end);
      if (len > MANHOLE_MAX_SPACING) {
        const count = Math.floor(len / MANHOLE_MAX_SPACING);
        for (let i = 1; i <= count; i++) {
          const t = (i * MANHOLE_MAX_SPACING) / len;
          const pos = [
            seg.start[0] + (seg.end[0] - seg.start[0]) * t,
            seg.start[1] + (seg.end[1] - seg.start[1]) * t,
          ];
          // Check if manhole already exists near this position
          const alreadyExists = existingMH.some((m) => distPt(m.position, pos) < 2);
          if (!alreadyExists) {
            existingMH.push({
              id: generateId('mh'),
              position: snapToGrid(pos),
              depth_m: 2.5,
            });
          }
        }
      }
    }
    data.manholes = existingMH;
    return data;
  }, []);

  const handleDeselect = useCallback(() => {
    setSelectedId(null);
    setSelectedType(null);
  }, []);

  // Stage click
  const handleStageClick = useCallback((e) => {
    if (e.target !== e.target.getStage()) return;
    const stage = stageRef.current;
    if (!stage) return;
    const pointer = stage.getPointerPosition();
    const worldX = (pointer.x - stagePosition.x) / stageScale;
    const worldY = (pointer.y - stagePosition.y) / stageScale;

    if (activeTool === 'pipe_run') {
      const snapped = snapToEndpoint([worldX, worldY], net.segments, net.manholes);
      if (!drawStart) {
        setDrawStart(snapped);
        setDrawPreview(snapped);
      } else {
        if (distPt(drawStart, snapped) > 0.5) {
          const data = cloneNet();
          if (!data.segments) data.segments = [];
          const segLen = distPt(drawStart, snapped);
          data.segments.push({
            id: generateId('seg'),
            start: drawStart,
            end: snapped,
            pipe_type: drawPipeType,
            diameter_mm: 300,
            material: 'PVC',
            slope_pct: 1.0,
            invert_elevation: 0,
            length_m: segLen,
          });
          autoPlaceManholes(data);
          pushChange(data);
        }
        setDrawStart(null);
        setDrawPreview(null);
      }
    } else if (activeTool === 'manhole') {
      const snapped = snapToGrid([worldX, worldY]);
      const data = cloneNet();
      if (!data.manholes) data.manholes = [];
      data.manholes.push({
        id: generateId('mh'),
        position: snapped,
        depth_m: 2.5,
      });
      pushChange(data);
    } else if (activeTool === 'fitting') {
      const snapped = snapToEndpoint([worldX, worldY], net.segments, net.manholes);
      const data = cloneNet();
      if (!data.fittings) data.fittings = [];
      data.fittings.push({
        id: generateId('fit'),
        position: snapped,
        type: 'elbow',
      });
      pushChange(data);
    } else if (activeTool === 'select') {
      handleDeselect();
    }
  }, [activeTool, drawStart, drawPipeType, stagePosition, stageScale, net, cloneNet, pushChange, autoPlaceManholes, handleDeselect]);

  const handleStageMouseMove = useCallback((e) => {
    if (activeTool !== 'pipe_run' || !drawStart) return;
    const stage = stageRef.current;
    if (!stage) return;
    const pointer = stage.getPointerPosition();
    const worldX = (pointer.x - stagePosition.x) / stageScale;
    const worldY = (pointer.y - stagePosition.y) / stageScale;
    setDrawPreview(snapToEndpoint([worldX, worldY], net.segments, net.manholes));
  }, [activeTool, drawStart, stagePosition, stageScale, net]);

  // Delete selected
  const deleteSelected = useCallback(() => {
    if (!selectedId || !selectedType) return;
    const data = cloneNet();
    if (selectedType === 'segment') {
      data.segments = data.segments.filter((s) => s.id !== selectedId);
    } else if (selectedType === 'manhole') {
      data.manholes = data.manholes.filter((m) => m.id !== selectedId);
    } else if (selectedType === 'fitting') {
      data.fittings = data.fittings.filter((f) => f.id !== selectedId);
    }
    pushChange(data);
    handleDeselect();
  }, [selectedId, selectedType, cloneNet, pushChange, handleDeselect]);

  // Segment property update
  const handleSegmentUpdate = useCallback((updated) => {
    const data = cloneNet();
    const idx = data.segments.findIndex((s) => s.id === updated.id);
    if (idx >= 0) {
      data.segments[idx] = { ...data.segments[idx], ...updated };
      pushChange(data);
    }
  }, [cloneNet, pushChange]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      if (!e.ctrlKey && !e.metaKey && !e.altKey) {
        switch (e.key) {
          case 'v': case 'V': setActiveTool('select'); return;
          case 'p': case 'P': setActiveTool('pipe_run'); return;
          case 'm': case 'M': setActiveTool('manhole'); return;
          case 'f': case 'F': setActiveTool('fitting'); return;
          case 'x': case 'X': setActiveTool('delete'); return;
          case 'Escape':
            if (drawStart) { setDrawStart(null); setDrawPreview(null); }
            else handleDeselect();
            return;
          case 'Delete': case 'Backspace':
            e.preventDefault();
            deleteSelected();
            return;
        }
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) { e.preventDefault(); undo(); }
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && e.shiftKey) { e.preventDefault(); redo(); }
      if ((e.ctrlKey || e.metaKey) && e.key === 'y') { e.preventDefault(); redo(); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [undo, redo, deleteSelected, handleDeselect, drawStart]);

  // Clear draw state on tool change
  useEffect(() => {
    if (activeTool !== 'pipe_run') {
      setDrawStart(null);
      setDrawPreview(null);
    }
  }, [activeTool]);

  // Zoom handler
  const handleWheel = useCallback((e) => {
    e.evt.preventDefault();
    const stage = stageRef.current;
    if (!stage) return;
    const pointer = stage.getPointerPosition();
    const oldScale = stage.scaleX();
    const scaleBy = 1.08;
    const newScale = e.evt.deltaY < 0 ? oldScale * scaleBy : oldScale / scaleBy;
    const clamped = Math.max(0.5, Math.min(200, newScale));
    const mousePointTo = {
      x: (pointer.x - stage.x()) / oldScale,
      y: (pointer.y - stage.y()) / oldScale,
    };
    setStageScale(clamped);
    setStagePosition({
      x: pointer.x - mousePointTo.x * clamped,
      y: pointer.y - mousePointTo.y * clamped,
    });
  }, []);

  const canvasCursor = useMemo(() => {
    if (activeTool === 'pipe_run') return 'crosshair';
    if (activeTool === 'manhole') return 'cell';
    if (activeTool === 'fitting') return 'copy';
    if (activeTool === 'delete') return 'no-drop';
    if (activeTool === 'measure') return 'crosshair';
    return 'grab';
  }, [activeTool]);

  const tools = [
    { key: 'select', label: 'Select', shortcut: 'V' },
    { key: 'pipe_run', label: 'Pipe Run', shortcut: 'P' },
    { key: 'manhole', label: 'Manhole', shortcut: 'M' },
    { key: 'fitting', label: 'Fitting', shortcut: 'F' },
    { key: 'delete', label: 'Delete', shortcut: 'X' },
    { key: 'measure', label: 'Measure', shortcut: '' },
  ];

  return (
    <div className="pipe-editor">
      {/* Toolbar */}
      <div className="pipe-editor-toolbar">
        {tools.map((tool) => (
          <button
            key={tool.key}
            className={activeTool === tool.key ? 'active' : ''}
            onClick={() => setActiveTool(tool.key)}
          >
            {tool.label}
            {tool.shortcut && <span className="toolbar-shortcut">{tool.shortcut}</span>}
          </button>
        ))}
        <div className="toolbar-divider" />
        {activeTool === 'pipe_run' && (
          <select
            className="infra-property-select"
            value={drawPipeType}
            onChange={(e) => setDrawPipeType(e.target.value)}
            style={{ margin: '0 4px', fontSize: '11px' }}
          >
            <option value="water">Water</option>
            <option value="sanitary">Sanitary</option>
            <option value="storm">Storm</option>
            <option value="gas">Gas</option>
          </select>
        )}
        <div className="toolbar-divider" />
        <div className="undo-redo-group">
          <button onClick={undo} disabled={historyIndex <= 0} title="Undo (Ctrl+Z)">Undo</button>
          <button onClick={redo} disabled={historyIndex >= editHistory.length - 1} title="Redo (Ctrl+Y)">Redo</button>
        </div>
      </div>

      {/* Canvas */}
      <div className="pipe-editor-canvas" ref={containerRef} style={{ cursor: canvasCursor }}>
        <Stage
          ref={stageRef}
          width={stageSize.width}
          height={stageSize.height}
          scaleX={stageScale}
          scaleY={stageScale}
          x={stagePosition.x}
          y={stagePosition.y}
          draggable={activeTool === 'select' && !selectedId}
          onWheel={handleWheel}
          onDragEnd={(e) => setStagePosition({ x: e.target.x(), y: e.target.y() })}
          onClick={handleStageClick}
          onTap={handleStageClick}
          onMouseMove={handleStageMouseMove}
        >
          <Layer>
            {/* Grid */}
            {(() => {
              const gridLines = [];
              const gridStep = 10;
              const visibleW = stageSize.width / stageScale;
              const visibleH = stageSize.height / stageScale;
              const startX = Math.floor(-stagePosition.x / stageScale / gridStep) * gridStep - gridStep;
              const startY = Math.floor(-stagePosition.y / stageScale / gridStep) * gridStep - gridStep;
              for (let x = startX; x < startX + visibleW + gridStep * 2; x += gridStep) {
                gridLines.push(
                  <Line
                    key={`gx${x}`}
                    points={[x, startY, x, startY + visibleH + gridStep * 2]}
                    stroke="#333"
                    strokeWidth={0.5 / stageScale}
                    listening={false}
                  />
                );
              }
              for (let y = startY; y < startY + visibleH + gridStep * 2; y += gridStep) {
                gridLines.push(
                  <Line
                    key={`gy${y}`}
                    points={[startX, y, startX + visibleW + gridStep * 2, y]}
                    stroke="#333"
                    strokeWidth={0.5 / stageScale}
                    listening={false}
                  />
                );
              }
              return gridLines;
            })()}

            {/* Pipe segments */}
            {net.segments.map((seg) => {
              const color = PIPE_COLORS[seg.pipe_type] || PIPE_COLORS.water;
              const isSelected = selectedId === seg.id;
              const strokeW = Math.max(2 / stageScale, (seg.diameter_mm || 300) / 1000);

              // Midpoint for flow arrow
              const mx = (seg.start[0] + seg.end[0]) / 2;
              const my = (seg.start[1] + seg.end[1]) / 2;

              return (
                <Group key={seg.id}>
                  <Line
                    points={[seg.start[0], seg.start[1], seg.end[0], seg.end[1]]}
                    stroke={isSelected ? '#c8a55c' : color}
                    strokeWidth={strokeW}
                    hitStrokeWidth={6 / stageScale}
                    onClick={() => {
                      if (activeTool === 'delete') {
                        const data = cloneNet();
                        data.segments = data.segments.filter((s) => s.id !== seg.id);
                        pushChange(data);
                      } else {
                        setSelectedId(seg.id);
                        setSelectedType('segment');
                      }
                    }}
                  />
                  {/* Flow direction arrow */}
                  <Arrow
                    points={[
                      mx - (seg.end[0] - seg.start[0]) * 0.05,
                      my - (seg.end[1] - seg.start[1]) * 0.05,
                      mx + (seg.end[0] - seg.start[0]) * 0.05,
                      my + (seg.end[1] - seg.start[1]) * 0.05,
                    ]}
                    pointerLength={3 / stageScale}
                    pointerWidth={3 / stageScale}
                    fill={color}
                    stroke={color}
                    strokeWidth={1 / stageScale}
                    listening={false}
                    opacity={0.7}
                  />
                </Group>
              );
            })}

            {/* Manholes */}
            {net.manholes.map((mh) => {
              const isSelected = selectedId === mh.id;
              return (
                <Circle
                  key={mh.id}
                  x={mh.position[0]}
                  y={mh.position[1]}
                  radius={1.2}
                  fill={isSelected ? '#c8a55c' : '#555'}
                  stroke={isSelected ? '#c8a55c' : '#888'}
                  strokeWidth={0.3}
                  onClick={() => {
                    if (activeTool === 'delete') {
                      const data = cloneNet();
                      data.manholes = data.manholes.filter((m) => m.id !== mh.id);
                      pushChange(data);
                    } else {
                      setSelectedId(mh.id);
                      setSelectedType('manhole');
                    }
                  }}
                />
              );
            })}

            {/* Fittings */}
            {net.fittings.map((fit) => {
              const isSelected = selectedId === fit.id;
              return (
                <Circle
                  key={fit.id}
                  x={fit.position[0]}
                  y={fit.position[1]}
                  radius={0.8}
                  fill={isSelected ? '#c8a55c' : '#aa6633'}
                  stroke={isSelected ? '#fff' : '#886644'}
                  strokeWidth={0.2}
                  onClick={() => {
                    if (activeTool === 'delete') {
                      const data = cloneNet();
                      data.fittings = data.fittings.filter((f) => f.id !== fit.id);
                      pushChange(data);
                    } else {
                      setSelectedId(fit.id);
                      setSelectedType('fitting');
                    }
                  }}
                />
              );
            })}

            {/* Draw preview */}
            {drawStart && drawPreview && (
              <>
                <Line
                  points={[drawStart[0], drawStart[1], drawPreview[0], drawPreview[1]]}
                  stroke={PIPE_COLORS[drawPipeType] || '#c8a55c'}
                  strokeWidth={2 / stageScale}
                  dash={[6 / stageScale, 4 / stageScale]}
                  listening={false}
                />
                <Circle
                  x={drawStart[0]}
                  y={drawStart[1]}
                  radius={4 / stageScale}
                  fill={PIPE_COLORS[drawPipeType] || '#c8a55c'}
                  listening={false}
                />
                <Circle
                  x={drawPreview[0]}
                  y={drawPreview[1]}
                  radius={3 / stageScale}
                  fill={PIPE_COLORS[drawPipeType] || '#c8a55c'}
                  opacity={0.6}
                  listening={false}
                />
                {/* Length label */}
                <Text
                  x={(drawStart[0] + drawPreview[0]) / 2}
                  y={(drawStart[1] + drawPreview[1]) / 2 - 3 / stageScale}
                  text={`${distPt(drawStart, drawPreview).toFixed(1)}m`}
                  fontSize={10 / stageScale}
                  fill="#c8a55c"
                  listening={false}
                />
              </>
            )}
          </Layer>
        </Stage>

        {/* Properties panel */}
        {selectedSegment && (
          <PipeProperties
            segment={selectedSegment}
            onUpdate={handleSegmentUpdate}
            onClose={handleDeselect}
          />
        )}
      </div>

      {/* Compliance panel */}
      {showCompliance && (
        <InfrastructureCompliancePanel
          results={complianceResult}
          onClose={() => setShowCompliance(false)}
        />
      )}
    </div>
  );
}
