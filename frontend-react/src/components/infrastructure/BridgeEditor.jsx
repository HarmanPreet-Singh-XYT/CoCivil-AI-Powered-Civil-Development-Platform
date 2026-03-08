import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Stage, Layer, Line, Rect, Circle, Text, Group } from 'react-konva';
import BridgeProperties from './BridgeProperties.jsx';

const BRIDGE_COLORS = {
  deck: '#888888',
  girder: '#666666',
  abutment: '#aa9977',
  pier: '#999999',
  barrier: '#bbbbbb',
};

let _bridgeIdCounter = 0;
function generateId(prefix) {
  return `${prefix}_${Date.now().toString(36)}_${(++_bridgeIdCounter).toString(36)}`;
}

const MAX_HISTORY = 50;

export default function BridgeEditor({
  bridge,
  onBridgeChange,
}) {
  const stageRef = useRef(null);
  const containerRef = useRef(null);

  const [stageSize, setStageSize] = useState({ width: 800, height: 600 });
  const [stageScale, setStageScale] = useState(5);
  const [stagePosition, setStagePosition] = useState({ x: 0, y: 0 });

  const [activeTool, setActiveTool] = useState('select');
  const [selectedId, setSelectedId] = useState(null);
  const [selectedComponent, setSelectedComponent] = useState(null);

  // Undo/redo
  const [editHistory, setEditHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const data = useMemo(() => ({
    components: bridge?.components || [],
    span_m: bridge?.span_m || 40,
    deck_width_m: bridge?.deck_width_m || 12,
  }), [bridge]);

  // Selected component for properties
  const selectedComp = useMemo(() => {
    if (!selectedId) return null;
    return data.components.find((c) => c.id === selectedId) || null;
  }, [selectedId, data.components]);

  // Resize observer
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setStageSize({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  // Fit to view
  useEffect(() => {
    const spanM = data.span_m || 40;
    const widthM = data.deck_width_m || 12;
    const pad = 60;
    const scaleX = (stageSize.width - pad * 2) / (spanM + 10);
    const scaleY = (stageSize.height - pad * 2) / (widthM + 10);
    const fitScale = Math.min(scaleX, scaleY, 50);
    setStageScale(fitScale);
    setStagePosition({ x: stageSize.width / 2, y: stageSize.height / 2 });
  }, [data, stageSize]);

  // Init history
  useEffect(() => {
    if (bridge && editHistory.length === 0) {
      setEditHistory([JSON.parse(JSON.stringify(bridge))]);
      setHistoryIndex(0);
    }
  }, [bridge]);

  const cloneBridge = useCallback(() => JSON.parse(JSON.stringify(bridge || { components: [], span_m: 40, deck_width_m: 12 })), [bridge]);

  const pushChange = useCallback((newBridge) => {
    onBridgeChange?.(newBridge);
    setEditHistory((prev) => {
      const trimmed = prev.slice(0, historyIndex + 1);
      const next = [...trimmed, JSON.parse(JSON.stringify(newBridge))];
      return next.length > MAX_HISTORY ? next.slice(next.length - MAX_HISTORY) : next;
    });
    setHistoryIndex((prev) => Math.min(prev + 1, MAX_HISTORY - 1));
  }, [onBridgeChange, historyIndex]);

  const undo = useCallback(() => {
    if (historyIndex <= 0) return;
    const idx = historyIndex - 1;
    setHistoryIndex(idx);
    onBridgeChange?.(JSON.parse(JSON.stringify(editHistory[idx])));
  }, [historyIndex, editHistory, onBridgeChange]);

  const redo = useCallback(() => {
    if (historyIndex >= editHistory.length - 1) return;
    const idx = historyIndex + 1;
    setHistoryIndex(idx);
    onBridgeChange?.(JSON.parse(JSON.stringify(editHistory[idx])));
  }, [historyIndex, editHistory, onBridgeChange]);

  const handleDeselect = useCallback(() => {
    setSelectedId(null);
    setSelectedComponent(null);
  }, []);

  // Stage click for placing components
  const handleStageClick = useCallback((e) => {
    if (e.target !== e.target.getStage()) return;
    const stage = stageRef.current;
    if (!stage) return;
    const pointer = stage.getPointerPosition();
    const worldX = (pointer.x - stagePosition.x) / stageScale;
    const worldY = (pointer.y - stagePosition.y) / stageScale;

    const compType = activeTool;
    if (['deck', 'girder', 'abutment', 'pier', 'barrier'].includes(compType)) {
      const br = cloneBridge();
      if (!br.components) br.components = [];
      const newComp = {
        id: generateId(compType.slice(0, 2)),
        component_type: compType,
        position: [worldX, worldY],
        width_m: compType === 'deck' ? br.deck_width_m || 12 : 2,
        height_m: compType === 'pier' ? 8 : 1,
        depth_m: compType === 'deck' ? 0.3 : compType === 'girder' ? 1.2 : 1.5,
        span_m: br.span_m || 40,
      };
      br.components.push(newComp);
      pushChange(br);
    } else if (activeTool === 'select') {
      handleDeselect();
    }
  }, [activeTool, stagePosition, stageScale, cloneBridge, pushChange, handleDeselect]);

  const handleComponentUpdate = useCallback((updated) => {
    const br = cloneBridge();
    const idx = br.components.findIndex((c) => c.id === updated.id);
    if (idx >= 0) {
      br.components[idx] = { ...br.components[idx], ...updated };
      pushChange(br);
    }
  }, [cloneBridge, pushChange]);

  const deleteSelected = useCallback(() => {
    if (!selectedId) return;
    const br = cloneBridge();
    br.components = br.components.filter((c) => c.id !== selectedId);
    pushChange(br);
    handleDeselect();
  }, [selectedId, cloneBridge, pushChange, handleDeselect]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      if (!e.ctrlKey && !e.metaKey && !e.altKey) {
        switch (e.key) {
          case 'v': case 'V': setActiveTool('select'); return;
          case 'x': case 'X': setActiveTool('delete'); return;
          case 'Escape': handleDeselect(); return;
          case 'Delete': case 'Backspace': e.preventDefault(); deleteSelected(); return;
        }
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) { e.preventDefault(); undo(); }
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && e.shiftKey) { e.preventDefault(); redo(); }
      if ((e.ctrlKey || e.metaKey) && e.key === 'y') { e.preventDefault(); redo(); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [undo, redo, deleteSelected, handleDeselect]);

  // Zoom
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

  const tools = [
    { key: 'select', label: 'Select' },
    { key: 'deck', label: 'Deck' },
    { key: 'girder', label: 'Girder' },
    { key: 'abutment', label: 'Abutment' },
    { key: 'pier', label: 'Pier' },
    { key: 'barrier', label: 'Barrier' },
    { key: 'delete', label: 'Delete' },
    { key: 'measure', label: 'Measure' },
  ];

  const canvasCursor = useMemo(() => {
    if (['deck', 'girder', 'abutment', 'pier', 'barrier'].includes(activeTool)) return 'cell';
    if (activeTool === 'delete') return 'no-drop';
    if (activeTool === 'measure') return 'crosshair';
    return 'grab';
  }, [activeTool]);

  return (
    <div className="pipe-editor">
      {/* Reuse pipe-editor layout */}
      <div className="pipe-editor-toolbar">
        {tools.map((tool) => (
          <button
            key={tool.key}
            className={activeTool === tool.key ? 'active' : ''}
            onClick={() => setActiveTool(tool.key)}
          >
            {tool.label}
          </button>
        ))}
        <div className="toolbar-divider" />
        <div className="undo-redo-group">
          <button onClick={undo} disabled={historyIndex <= 0}>Undo</button>
          <button onClick={redo} disabled={historyIndex >= editHistory.length - 1}>Redo</button>
        </div>
      </div>

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
        >
          <Layer>
            {/* Draw each component as a 2D representation */}
            {data.components.map((comp) => {
              const isSelected = selectedId === comp.id;
              const color = BRIDGE_COLORS[comp.component_type] || '#888';

              if (comp.component_type === 'deck') {
                const w = comp.span_m || data.span_m || 40;
                const h = comp.width_m || data.deck_width_m || 12;
                return (
                  <Rect
                    key={comp.id}
                    x={comp.position[0] - w / 2}
                    y={comp.position[1] - h / 2}
                    width={w}
                    height={h}
                    fill={color}
                    stroke={isSelected ? '#c8a55c' : '#666'}
                    strokeWidth={isSelected ? 0.3 : 0.15}
                    onClick={() => {
                      if (activeTool === 'delete') { deleteSelected(); return; }
                      setSelectedId(comp.id);
                      setSelectedComponent(comp);
                    }}
                  />
                );
              }

              if (comp.component_type === 'pier') {
                return (
                  <Rect
                    key={comp.id}
                    x={comp.position[0] - 0.5}
                    y={comp.position[1] - (comp.width_m || 2) / 2}
                    width={1}
                    height={comp.width_m || 2}
                    fill={color}
                    stroke={isSelected ? '#c8a55c' : '#777'}
                    strokeWidth={isSelected ? 0.3 : 0.1}
                    onClick={() => {
                      if (activeTool === 'delete') { deleteSelected(); return; }
                      setSelectedId(comp.id);
                      setSelectedComponent(comp);
                    }}
                  />
                );
              }

              // Default: circle for fittings/generic
              return (
                <Circle
                  key={comp.id}
                  x={comp.position[0]}
                  y={comp.position[1]}
                  radius={1}
                  fill={color}
                  stroke={isSelected ? '#c8a55c' : '#666'}
                  strokeWidth={isSelected ? 0.3 : 0.1}
                  onClick={() => {
                    if (activeTool === 'delete') { deleteSelected(); return; }
                    setSelectedId(comp.id);
                    setSelectedComponent(comp);
                  }}
                />
              );
            })}

            {/* Span dimension line */}
            <Line
              points={[-data.span_m / 2, -data.deck_width_m / 2 - 3, data.span_m / 2, -data.deck_width_m / 2 - 3]}
              stroke="#c8a55c"
              strokeWidth={0.3}
              dash={[1, 0.5]}
              listening={false}
            />
            <Text
              x={0}
              y={-data.deck_width_m / 2 - 5}
              text={`Span: ${data.span_m}m`}
              fontSize={2}
              fill="#c8a55c"
              align="center"
              listening={false}
            />
          </Layer>
        </Stage>

        {/* Properties panel */}
        {selectedComp && (
          <BridgeProperties
            component={selectedComp}
            onUpdate={handleComponentUpdate}
            onClose={handleDeselect}
          />
        )}
      </div>
    </div>
  );
}
