import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import maplibregl from 'maplibre-gl';

const QUERIES = [
    "What's the max building height at 100 Queen St W?",
    "Can I build a 12-storey condo at Yonge and Eglinton?",
    "What are the setback requirements for RM zoning?",
    "Is my property in an inclusionary zoning area?",
    "What's the permitted FSI for this lot?",
    "Do I need a minor variance for a rear addition?",
    "What Official Plan policies apply to this site?",
    "Can I convert this duplex to a fourplex?",
    "What's the angular plane from the north lot line?",
    "Are there heritage overlay restrictions here?",
];

function useTypewriter(strings, typingSpeed = 45, pauseTime = 2200, erasingSpeed = 25) {
    const [displayText, setDisplayText] = useState('');
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isTyping, setIsTyping] = useState(true);

    useEffect(() => {
        const current = strings[currentIndex];
        let timeout;

        if (isTyping) {
            if (displayText.length < current.length) {
                timeout = setTimeout(() => {
                    setDisplayText(current.slice(0, displayText.length + 1));
                }, typingSpeed);
            } else {
                timeout = setTimeout(() => setIsTyping(false), pauseTime);
            }
        } else {
            if (displayText.length > 0) {
                timeout = setTimeout(() => {
                    setDisplayText(displayText.slice(0, -1));
                }, erasingSpeed);
            } else {
                setCurrentIndex((prev) => (prev + 1) % strings.length);
                setIsTyping(true);
            }
        }

        return () => clearTimeout(timeout);
    }, [displayText, currentIndex, isTyping, strings, typingSpeed, pauseTime, erasingSpeed]);

    return displayText;
}

export default function LandingPage({ onNavigate }) {
    const {
        isLoading,
        isAuthenticated,
        error,
        loginWithRedirect: login,
        logout: auth0Logout,
        user,
    } = useAuth0();

    const mapPreviewRef = useRef(null);
    const mapInstanceRef = useRef(null);
    const [address, setAddress] = useState('');
    const typedText = useTypewriter(QUERIES);

    const signup = useCallback(
        () => login({ authorizationParams: { screen_hint: 'signup' } }),
        [login]
    );

    const logout = useCallback(
        () => auth0Logout({ logoutParams: { returnTo: window.location.origin } }),
        [auth0Logout]
    );

    // Enable scrolling on body when landing page is active
    useEffect(() => {
        document.body.classList.add('lp-active');
        return () => document.body.classList.remove('lp-active');
    }, []);

    // Initialize bright map preview
    useEffect(() => {
        if (mapInstanceRef.current || !mapPreviewRef.current) return;

        const map = new maplibregl.Map({
            container: mapPreviewRef.current,
            style: {
                version: 8,
                sources: {
                    'osm-tiles': {
                        type: 'raster',
                        tiles: [
                            'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
                            'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png',
                        ],
                        tileSize: 256,
                    },
                },
                layers: [{
                    id: 'osm-base',
                    type: 'raster',
                    source: 'osm-tiles',
                    paint: {
                        'raster-saturation': -0.3,
                        'raster-brightness-min': 0.15,
                        'raster-brightness-max': 0.85,
                        'raster-contrast': 0.1,
                    },
                }],
            },
            center: [-79.3832, 43.6532],
            zoom: 13,
            interactive: true,
            attributionControl: false,
        });

        mapInstanceRef.current = map;
        return () => { map.remove(); mapInstanceRef.current = null; };
    }, []);

    const handleSubmit = useCallback((e) => {
        e.preventDefault();
        if (address.trim()) {
            onNavigate(address.trim());
        }
    }, [address, onNavigate]);

    return (
        <div className="lp">
            {/* Background */}
            <div className="lp-bg" />

            {/* ===== NAVBAR ===== */}
            <nav className="lp-nav">
                <div className="lp-nav-inner">
                    <div className="lp-nav-logo">
                        application<span>AI</span>
                    </div>
                    <div className="lp-nav-actions">
                        {isLoading ? (
                            <span className="lp-nav-link lp-nav-loading">Loading…</span>
                        ) : isAuthenticated ? (
                            <>
                                {user?.picture && (
                                    <img
                                        src={user.picture}
                                        alt={user.name}
                                        className="lp-nav-avatar"
                                    />
                                )}
                                <span className="lp-nav-greeting">
                                    {user?.name || user?.email}
                                </span>
                                <button className="lp-nav-link" onClick={logout}>
                                    Sign Out
                                </button>
                            </>
                        ) : (
                            <>
                                {error && (
                                    <span className="lp-nav-error">
                                        {error.message}
                                    </span>
                                )}
                                <button className="lp-nav-link" onClick={login}>
                                    Sign In
                                </button>
                                <button className="lp-nav-link" onClick={signup}>
                                    Sign Up
                                </button>
                            </>
                        )}
                        <button className="lp-nav-cta" onClick={() => onNavigate('')}>
                            Try Demo
                        </button>
                    </div>
                </div>
            </nav>

            {/* ===== HERO ===== */}
            <section className="lp-hero">
                <div className="lp-hero-content">
                    <div className="lp-hero-left">
                        {/* Typewriter */}
                        <div className="lp-typewriter-wrap">
                            <h1 className="lp-typewriter">
                                {typedText}
                                <span className="lp-cursor" />
                            </h1>
                        </div>
                        <p className="lp-motto">
                            The intelligence layer between policy and design. We read the
                            city's rules so you don't have to.
                        </p>
                    </div>

                    <div className="lp-hero-right">
                        {/* Bright map preview */}
                        <div className="lp-map-preview">
                            <div className="lp-map-container" ref={mapPreviewRef} />
                            <div className="lp-map-shine" />
                        </div>

                        {/* Address input */}
                        <form className="lp-address-bar" onSubmit={handleSubmit}>
                            <svg
                                className="lp-address-icon"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                            >
                                <circle cx="11" cy="11" r="8" />
                                <line x1="21" y1="21" x2="16.65" y2="16.65" />
                            </svg>
                            <input
                                type="text"
                                className="lp-address-input"
                                placeholder="Enter an address to get started..."
                                value={address}
                                onChange={(e) => setAddress(e.target.value)}
                            />
                            <kbd className="lp-address-kbd">↵</kbd>
                        </form>
                    </div>
                </div>

                {/* Scroll hint */}
                <div className="lp-scroll-hint">
                    <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                    >
                        <polyline points="6 9 12 15 18 9" />
                    </svg>
                </div>
            </section>

            {/* ===== OUR STORY ===== */}
            <section className="lp-section lp-story">
                <div className="lp-section-inner">
                    <div className="lp-section-label">Our Story</div>
                    <h2 className="lp-section-heading">
                        We started where every developer starts — buried in PDFs.
                    </h2>
                    <p className="lp-section-body">
                        Zoning bylaws scattered across hundreds of pages. Official Plan
                        policies in one tab, setback tables in another, heritage overlays
                        in a third. Hours wasted before a single sketch is drawn. We built
                        applicationAI because we lived this problem — and because we knew
                        AI could solve it. Our platform reads the city's rules so you
                        don't have to, turning weeks of due diligence into minutes of
                        conversation.
                    </p>
                </div>
            </section>

            {/* ===== OUR VISION ===== */}
            <section className="lp-section lp-vision">
                <div className="lp-section-inner lp-align-right">
                    <div className="lp-section-label">Our Vision</div>
                    <h2 className="lp-section-heading">
                        A world where building the right thing is the easy thing.
                    </h2>
                    <p className="lp-section-body">
                        Every city has rules. Most are written for lawyers, not builders.
                        We envision a future where any developer, architect, or planner
                        can instantly understand what's possible on any parcel — and make
                        smarter decisions from day one. applicationAI is the intelligence
                        layer between policy and design, making cities faster to build and
                        better to live in.
                    </p>
                </div>
            </section>

            {/* ===== FOOTER ===== */}
            <footer className="lp-footer">
                <span>© 2025 applicationAI</span>
                <span>Toronto, Canada</span>
            </footer>
        </div>
    );
}