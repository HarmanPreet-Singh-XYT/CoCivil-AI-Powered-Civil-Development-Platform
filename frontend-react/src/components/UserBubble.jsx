import { useState, useRef, useEffect, useCallback } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import '../UserBubble.css';

export default function UserBubble() {
    const {
        isAuthenticated,
        user,
        logout: auth0Logout,
    } = useAuth0();

    const [isExpanded, setIsExpanded] = useState(false);
    const [isVisible, setIsVisible] = useState(false);
    const timeoutRef = useRef(null);
    const bubbleRef = useRef(null);

    const logout = useCallback(() => {
        auth0Logout({ logoutParams: { returnTo: window.location.origin } });
    }, [auth0Logout]);

    const handleMouseEnter = useCallback(() => {
        clearTimeout(timeoutRef.current);
        setIsExpanded(true);
        // Small delay so the width transition kicks in before content appears
        setTimeout(() => setIsVisible(true), 80);
    }, []);

    const handleMouseLeave = useCallback(() => {
        setIsVisible(false);
        timeoutRef.current = setTimeout(() => {
            setIsExpanded(false);
        }, 200);
    }, []);

    // Cleanup timeout on unmount
    useEffect(() => {
        return () => clearTimeout(timeoutRef.current);
    }, []);

    if (!isAuthenticated || !user) return null;

    const initials = (user.name || user.email || '?')
        .split(' ')
        .map((w) => w[0])
        .join('')
        .slice(0, 2)
        .toUpperCase();

    return (
        <div
            ref={bubbleRef}
            className={`ub ${isExpanded ? 'ub--expanded' : ''}`}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
            {/* Avatar — always visible */}
            <div className="ub-avatar">
                {user.picture ? (
                    <img src={user.picture} alt={user.name || 'User'} />
                ) : (
                    <span className="ub-initials">{initials}</span>
                )}
                {/* Online dot */}
                <span className="ub-status" />
            </div>

            {/* Expanded content */}
            <div className={`ub-content ${isVisible ? 'ub-content--visible' : ''}`}>
                <div className="ub-info">
                    <span className="ub-name">{user.name || 'User'}</span>
                    <span className="ub-email">{user.email}</span>
                </div>

                <div className="ub-divider" />

                <button className="ub-action" onClick={logout}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                        <polyline points="16 17 21 12 16 7" />
                        <line x1="21" y1="12" x2="9" y2="12" />
                    </svg>
                    Sign Out
                </button>
            </div>
        </div>
    );
}