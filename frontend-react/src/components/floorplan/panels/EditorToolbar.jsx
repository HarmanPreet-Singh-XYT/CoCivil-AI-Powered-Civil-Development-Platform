// ── Cursor / Select ──────────────────────────────────────────
const SelectIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 3l15 9.5-7 1.5-3 7L5 3z" fill="currentColor" stroke="currentColor" strokeWidth="1.5" />
    <line x1="13" y1="13" x2="20" y2="20" stroke="currentColor" strokeWidth="2.5" />
  </svg>
);

// ── Wall (floor-plan cross-section) ──────────────────────────
const WallIcon = () => (
  <svg viewBox="0 0 24 24" fill="none">
    <rect x="2" y="9" width="20" height="6" fill="currentColor" rx="1" />
    <line x1="2"  y1="6" x2="2"  y2="18" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    <line x1="22" y1="6" x2="22" y2="18" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
  </svg>
);

// ── Door (plan-view arc swing) ────────────────────────────────
const DoorIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round">
    {/* Left wall stub */}
    <rect x="2" y="9" width="5" height="6" fill="currentColor" rx="0.5" />
    {/* Right wall stub */}
    <rect x="17" y="9" width="5" height="6" fill="currentColor" rx="0.5" />
    {/* Gap top/bottom lines */}
    <line x1="7" y1="9"  x2="17" y2="9"  stroke="currentColor" strokeWidth="1.5" />
    <line x1="7" y1="15" x2="17" y2="15" stroke="currentColor" strokeWidth="1.5" />
    {/* Door leaf */}
    <line x1="7" y1="9" x2="7" y2="3" stroke="currentColor" strokeWidth="1.5" />
    {/* Swing arc */}
    <path d="M7 9 A6 6 0 0 1 17 3" stroke="currentColor" strokeWidth="1.5" fill="none" strokeDasharray="2 1.5" />
  </svg>
);

// ── Window (plan-view triple line in wall gap) ────────────────
const WindowIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" strokeLinecap="round">
    {/* Left wall stub */}
    <rect x="2" y="9" width="5" height="6" fill="currentColor" rx="0.5" />
    {/* Right wall stub */}
    <rect x="17" y="9" width="5" height="6" fill="currentColor" rx="0.5" />
    {/* Three parallel glass lines */}
    <line x1="7" y1="9"  x2="17" y2="9"  stroke="currentColor" strokeWidth="1.5" />
    <line x1="7" y1="12" x2="17" y2="12" stroke="currentColor" strokeWidth="1.5" />
    <line x1="7" y1="15" x2="17" y2="15" stroke="currentColor" strokeWidth="1.5" />
  </svg>
);

// ── Eraser ────────────────────────────────────────────────────
const EraseIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 20H7L3 16l9.5-9.5 7.5 7.5L20 20z" />
    <line x1="5" y1="18" x2="14" y2="9" />
  </svg>
);

// ── Undo / Redo ───────────────────────────────────────────────
const UndoIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="9 14 4 9 9 4" />
    <path d="M20 20v-7a4 4 0 0 0-4-4H4" />
  </svg>
);

const RedoIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="15 14 20 9 15 4" />
    <path d="M4 20v-7a4 4 0 0 1 4-4h12" />
  </svg>
);

// ─────────────────────────────────────────────────────────────

const TOOLS = [
  { id: 'select', label: 'Select', icon: SelectIcon },
  { id: 'wall',   label: 'Wall',   icon: WallIcon   },
  { id: 'door',   label: 'Door',   icon: DoorIcon   },
  { id: 'window', label: 'Window', icon: WindowIcon },
  { id: 'delete', label: 'Erase',  icon: EraseIcon  },
];

export default function EditorToolbar({
  activeTool,
  onToolChange,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
}) {
  return (
    <div className="floorplan-toolbar">
      {TOOLS.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          className={`toolbar-icon-btn ${activeTool === id ? 'active' : ''}`}
          onClick={() => onToolChange(id)}
          title={label}
        >
          <Icon />
          <span className="toolbar-btn-label">{label}</span>
        </button>
      ))}

      <div className="toolbar-divider" />

      <button
        className="toolbar-icon-btn"
        onClick={onUndo}
        disabled={!canUndo}
        title="Undo (Ctrl+Z)"
      >
        <UndoIcon />
        <span className="toolbar-btn-label">Undo</span>
      </button>
      <button
        className="toolbar-icon-btn"
        onClick={onRedo}
        disabled={!canRedo}
        title="Redo (Ctrl+Y)"
      >
        <RedoIcon />
        <span className="toolbar-btn-label">Redo</span>
      </button>
    </div>
  );
}
