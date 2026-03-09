import { useCallback, useMemo } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import useResizable from '../hooks/useResizable.js';

const BUILDING_NAV_ITEMS = [
    { id: 'overview', label: 'Overview', icon: (<><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" /></>) },
    { id: 'finances', label: 'Finances', icon: (<><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></>) },
    { id: 'policies', label: 'Policies', icon: (<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />) },
    { id: 'datasets', label: 'Datasets', icon: (<><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" /></>) },
    { id: 'precedents', label: 'Precedents', icon: (<><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></>) },
];

const PIPELINE_NAV_ITEMS = [
    { id: 'overview', label: 'Overview', icon: (<><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" /></>) },
    { id: 'standards', label: 'Standards', icon: (<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />) },
    { id: 'network', label: 'Network', icon: (<><circle cx="5" cy="6" r="2" /><circle cx="19" cy="6" r="2" /><circle cx="12" cy="18" r="2" /><line x1="5" y1="8" x2="12" y2="16" /><line x1="19" y1="8" x2="12" y2="16" /></>) },
    { id: 'datasets', label: 'Datasets', icon: (<><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" /></>) },
    { id: 'inspections', label: 'Inspections', icon: (<><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></>) },
    { id: 'history', label: 'History', icon: (<><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></>) },
];

const NAV_BY_ASSET_TYPE = {
    building: BUILDING_NAV_ITEMS,
    pipeline: PIPELINE_NAV_ITEMS,
};

const ASSET_TYPES = [
    { id: 'building', label: 'Buildings' },
    { id: 'pipeline', label: 'Pipelines' },
];

const COLLAPSED_WIDTH = 52;
const DEFAULT_WIDTH = 160;
const MIN_WIDTH = 120;
const MAX_WIDTH = 280;

function shortAddress(item) {
    // Use the short address (e.g. "192 Spadina Avenue") if available,
    // otherwise take just the first segment before the city
    const raw = item.address || item.fullAddress || '';
    const parts = raw.split(',');
    return parts[0].trim();
}

export default function Sidebar({ isCollapsed, onToggleCollapse, activeNav, onNavClick, showHistory, onHistoryClick, onHistoryBack, historyItems, onHistoryItemClick, assetType, onAssetTypeChange }) {
    const { user, logout: auth0Logout } = useAuth0();

    const { isResizing, handleProps } = useResizable({
        defaultSize: DEFAULT_WIDTH,
        minSize: MIN_WIDTH,
        maxSize: MAX_WIDTH,
        axis: 'horizontal',
        cssVar: isCollapsed ? null : '--sidebar-width',
        disabled: isCollapsed,
    });

    if (isCollapsed) {
        document.documentElement.style.setProperty('--sidebar-width', `${COLLAPSED_WIDTH}px`);
    }

    const logout = useCallback(() => {
        auth0Logout({ logoutParams: { returnTo: window.location.origin } });
    }, [auth0Logout]);

    const initials = user
        ? (user.name || user.email || '?')
            .split(' ')
            .map((w) => w[0])
            .join('')
            .slice(0, 2)
            .toUpperCase()
        : '?';

    const currentAssetType = assetType || 'building';
    const NAV_ITEMS = useMemo(() => NAV_BY_ASSET_TYPE[currentAssetType] || BUILDING_NAV_ITEMS, [currentAssetType]);

    return (
        <nav id="sidebar" style={{ userSelect: isResizing ? 'none' : undefined }}>
            <div className="sidebar-top">
                <div className="sidebar-logo">
                    {isCollapsed
                        ? <span className="logo-collapsed"><span className="logo-accent">Co</span></span>
                        : <span className="logo-full"><span className="logo-accent">Co</span>Civil</span>
                    }
                </div>
                <div className="sidebar-divider" />

                {!isCollapsed && onAssetTypeChange && (
                    <div className="asset-type-selector">
                        {ASSET_TYPES.map((at) => (
                            <button
                                key={at.id}
                                className={`asset-type-btn${currentAssetType === at.id ? ' active' : ''}`}
                                onClick={() => onAssetTypeChange(at.id)}
                            >
                                {at.label}
                            </button>
                        ))}
                    </div>
                )}
                {!isCollapsed && onAssetTypeChange && <div className="sidebar-divider" />}

                {showHistory && !isCollapsed ? (
                    <>
                        <button className="history-back-btn" onClick={onHistoryBack}>
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="16" height="16">
                                <polyline points="15 18 9 12 15 6" />
                            </svg>
                            Back
                        </button>
                        <div className="history-list">
                            {(!historyItems || historyItems.length === 0) ? (
                                <div className="history-empty">No searches yet</div>
                            ) : (
                                historyItems.map((item, idx) => (
                                    <button key={idx} className="history-item" onClick={() => onHistoryItemClick(item)}>
                                        <svg className="history-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                                            <circle cx="12" cy="10" r="3" />
                                        </svg>
                                        <span className="history-item-address">{shortAddress(item)}</span>
                                    </button>
                                ))
                            )}
                        </div>
                    </>
                ) : (
                    <>
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
                        {!isCollapsed && assetType !== 'pipeline' && (
                            <>
                                <div className="sidebar-divider" />
                                <button className="nav-item" onClick={onHistoryClick}>
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                        <circle cx="12" cy="12" r="10" />
                                        <polyline points="12 6 12 12 16 14" />
                                    </svg>
                                    <span>History</span>
                                </button>
                            </>
                        )}
                    </>
                )}
            </div>

            <div className="sidebar-bottom">
                {user && (
                    <>
                        <div className="sidebar-divider" />

                        <div
                            className="sidebar-user"
                            title={isCollapsed ? (user.name || user.email) : undefined}
                        >
                            <div className="sidebar-user-avatar">
                                {user.picture
                                    ? <img src={user.picture} alt={user.name || 'User'} />
                                    : <span className="sidebar-user-initials">{initials}</span>
                                }
                                <span className="sidebar-user-status" />
                            </div>
                            {!isCollapsed && (
                                <div className="sidebar-user-info">
                                    <span className="sidebar-user-name">{user.name || 'User'}</span>
                                    <span className="sidebar-user-email">{user.email}</span>
                                </div>
                            )}
                        </div>

                        <button
                            className="nav-item nav-item--signout"
                            onClick={logout}
                            title={isCollapsed ? 'Sign Out' : undefined}
                        >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                                <polyline points="16 17 21 12 16 7" />
                                <line x1="21" y1="12" x2="9" y2="12" />
                            </svg>
                            <span>Sign Out</span>
                        </button>

                        <div className="sidebar-divider" />
                    </>
                )}

                <button className="nav-item" id="collapse-btn" onClick={onToggleCollapse}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        {isCollapsed ? <polyline points="9 18 15 12 9 6" /> : <polyline points="15 18 9 12 15 6" />}
                    </svg>
                    <span>{isCollapsed ? 'Expand' : 'Collapse'}</span>
                </button>
            </div>

            {!isCollapsed && <div {...handleProps} style={{ ...handleProps.style, right: -2 }} />}
        </nav>
    );
}
