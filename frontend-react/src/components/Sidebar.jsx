import { useState, useRef, useCallback, useEffect } from 'react';

const NAV_ITEMS = [
    { id: 'overview', label: 'Overview', icon: (<><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" /></>) },
    { id: 'massing', label: 'Massing', icon: (<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />) },
    { id: 'finances', label: 'Finances', icon: (<><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></>) },
    { id: 'entitlements', label: 'Entitlements', icon: (<><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></>) },
    { id: 'policies', label: 'Policies', icon: (<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />) },
    { id: 'datasets', label: 'Datasets', icon: (<><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" /></>) },
    { id: 'precedents', label: 'Precedents', icon: (<><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></>) },
];

const COLLAPSED_WIDTH = 52;
const DEFAULT_WIDTH = 160;
const MIN_WIDTH = 120;
const MAX_WIDTH = 280;

export default function Sidebar({ isCollapsed, onToggleCollapse, activeNav, onNavClick, showHistory, onHistoryClick, onHistoryBack, historyItems, onHistoryItemClick }) {
    const [width, setWidth] = useState(DEFAULT_WIDTH);
    const [isResizing, setIsResizing] = useState(false);
    const startXRef = useRef(null);
    const startWidthRef = useRef(null);

    // ── CSS variable drives #sidebar width AND all dependent elements ──────────
    // The CSS rule is: #sidebar { width: var(--sidebar-width) }
    // so we never set an inline width on the element — the var is the single source of truth.
    useEffect(() => {
        const effective = isCollapsed ? COLLAPSED_WIDTH : width;
        document.documentElement.style.setProperty('--sidebar-width', `${effective}px`);
    }, [isCollapsed, width]);

    // ── While dragging, kill transitions on everything so there's zero lag/gap ─
    useEffect(() => {
        const style = document.createElement('style');
        style.id = 'no-layout-transition';
        if (isResizing) {
            style.textContent = `
                #sidebar, #search-container, #chat-panel, #policy-panel, .panel-reopen-tab {
                    transition: none !important;
                }
            `;
            document.head.appendChild(style);
        }
        return () => {
            document.getElementById('no-layout-transition')?.remove();
        };
    }, [isResizing]);

    // ── Drag-to-resize ─────────────────────────────────────────────────────────
    const handleResizeStart = useCallback((e) => {
        if (isCollapsed) return;
        e.preventDefault();
        setIsResizing(true);
        startXRef.current = e.clientX;
        startWidthRef.current = width;
    }, [isCollapsed, width]);

    useEffect(() => {
        if (!isResizing) return;
        const onMove = (e) => {
            const delta = e.clientX - startXRef.current;
            const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startWidthRef.current + delta));
            setWidth(newWidth);
        };
        const onUp = () => setIsResizing(false);
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        return () => {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        };
    }, [isResizing]);

    return (
        <nav
            id="sidebar"
            style={{ userSelect: isResizing ? 'none' : undefined }}
        >
            <div className="sidebar-top">
                <div className="sidebar-logo">
                    {isCollapsed
                        ? <span className="logo-collapsed">a<span className="logo-accent">AI</span></span>
                        : <span className="logo-full">application<span className="logo-accent">AI</span></span>
                    }
                </div>
                <div className="sidebar-divider" />
                {NAV_ITEMS.map((item) => (
                    <button
                        key={item.id}
                        className={`nav-item${activeNav === item.id ? ' active' : ''}`}
                        onClick={() => onNavClick(item.id)}
                        title={isCollapsed ? item.label : undefined}
                    >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">{item.icon}</svg>
                        <span>{item.label}</span>
                    </button>
                ))}
            </div>

            <div className="sidebar-bottom">
                <button className="nav-item" id="collapse-btn" onClick={onToggleCollapse}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        {isCollapsed ? <polyline points="9 18 15 12 9 6" /> : <polyline points="15 18 9 12 15 6" />}
                    </svg>
                    <span>{isCollapsed ? 'Expand' : 'Collapse'}</span>
                </button>
            </div>

            {/* Right-edge drag handle */}
            {!isCollapsed && (
                <div
                    onMouseDown={handleResizeStart}
                    onMouseEnter={e => { if (!isResizing) e.currentTarget.style.background = 'rgba(200,165,92,0.15)'; }}
                    onMouseLeave={e => { if (!isResizing) e.currentTarget.style.background = 'transparent'; }}
                    style={{
                        position: 'absolute',
                        right: -2,
                        top: 0,
                        bottom: 0,
                        width: 4,
                        cursor: 'col-resize',
                        zIndex: 30,
                        background: isResizing ? 'rgba(200,165,92,0.3)' : 'transparent',
                        transition: 'background 0.15s',
                    }}
                />
            )}
        </nav>
    );
}