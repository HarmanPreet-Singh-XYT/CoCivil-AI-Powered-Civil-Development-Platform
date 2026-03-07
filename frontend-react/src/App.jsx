import { useState, useRef, useCallback, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import MapView from './components/MapView.jsx';
import SearchBar from './components/SearchBar.jsx';
import Sidebar from './components/Sidebar.jsx';
import PolicyPanel from './components/PolicyPanel.jsx';
import ChatPanel from './components/ChatPanel.jsx';
import LandingPage from './components/LandingPage.jsx';
import { searchParcels } from './api.js';
import { buildParcelState, isResolvedParcel } from './lib/parcelState.js';
import './landing.css';

export default function App() {
  // ─── Auth0 (only needed for dashboard-level auth) ─────────────
  const {
    isLoading,
    isAuthenticated,
    logout: auth0Logout,
    user,
  } = useAuth0();

  // ─── App State ────────────────────────────────────────────────
  const [currentPage, setCurrentPage] = useState('landing');
  const [selectedParcel, setSelectedParcel] = useState(null);
  const [isPanelOpen, setIsPanelOpen] = useState(true);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [activeNav, setActiveNav] = useState('overview');
  const [savedParcels, setSavedParcels] = useState([]);

  const mapRef = useRef(null);

  // ─── Auth Handler (for dashboard sign out) ────────────────────
  const handleLogout = useCallback(() => {
    auth0Logout({ logoutParams: { returnTo: window.location.origin } });
    setSelectedParcel(null);
    setCurrentPage('landing');
  }, [auth0Logout]);

  // ─── Location / Parcel Handlers ──────────────────────────────
  const handleLocationSelected = useCallback(async (location) => {
    if (mapRef.current) {
      mapRef.current.flyTo(location.lng, location.lat, 16);
      mapRef.current.setMarker(location.lng, location.lat);
    }

    const parcels = await searchParcels(
      location.shortAddress || location.address
    );
    setSelectedParcel(buildParcelState(location, parcels));
    setIsPanelOpen(true);
  }, []);

  const handlePanelClose = useCallback(() => {
    setIsPanelOpen(false);
  }, []);

  const handleSidebarToggle = useCallback(() => {
    setIsSidebarCollapsed((prev) => !prev);
  }, []);

  const handleNavClick = useCallback((panel) => {
    setActiveNav(panel);
    setIsPanelOpen(true);
  }, []);

  const handleSaveParcel = useCallback((parcel) => {
    setSavedParcels((prev) => {
      if (!isResolvedParcel(parcel)) return prev;
      if (prev.some((p) => p.address === parcel.address)) return prev;
      return [...prev, parcel];
    });
  }, []);

  const handleLandingNavigate = useCallback(
    async (address) => {
      setCurrentPage('dashboard');

      if (address) {
        try {
          const res = await fetch(
            `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(
              address + ' Toronto Canada'
            )}&format=json&addressdetails=1&limit=1&countrycodes=ca`,
            { headers: { 'Accept-Language': 'en' } }
          );
          const results = await res.json();
          if (results.length > 0) {
            const result = results[0];
            const addr = result.address || {};
            const parts = [];
            if (addr.house_number) parts.push(addr.house_number);
            if (addr.road) parts.push(addr.road);
            let shortAddress =
              parts.join(' ') || result.display_name.split(',')[0];
            if (addr.city || addr.town)
              shortAddress += `, ${addr.city || addr.town}`;

            setTimeout(() => {
              handleLocationSelected({
                lng: parseFloat(result.lon),
                lat: parseFloat(result.lat),
                address: result.display_name,
                shortAddress,
              });
            }, 500);
          }
        } catch (err) {
          console.error('Geocoding error:', err);
        }
      }
    },
    [handleLocationSelected]
  );

  // ─── Body Class Side Effects ──────────────────────────────────
  useEffect(() => {
    if (typeof document === 'undefined') return undefined;

    const isDashboard = currentPage === 'dashboard';
    document.body.classList.toggle(
      'sidebar-collapsed',
      isDashboard && isSidebarCollapsed
    );
    document.body.classList.toggle('panel-open', isDashboard && isPanelOpen);

    return () => {
      document.body.classList.remove('sidebar-collapsed');
      document.body.classList.remove('panel-open');
    };
  }, [currentPage, isSidebarCollapsed, isPanelOpen]);

  // ─── Render: Landing Page ─────────────────────────────────────
  // No auth gate — LandingPage handles its own auth via useAuth0()
  if (currentPage === 'landing') {
    return <LandingPage onNavigate={handleLandingNavigate} />;
  }

  // ─── Render: Dashboard Loading ────────────────────────────────
  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        gap: '1rem',
        background: '#fafafa',
      }}>
        <p>Loading your session...</p>
      </div>
    );
  }

  // ─── Render: Dashboard ────────────────────────────────────────
  return (
    <>
      {/* User bar when authenticated */}
      {isAuthenticated && user && (
        <div style={{
          position: 'fixed',
          top: '12px',
          right: '12px',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '6px 14px',
          background: 'rgba(255,255,255,0.95)',
          backdropFilter: 'blur(8px)',
          borderRadius: '999px',
          boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
          fontSize: '0.85rem',
        }}>
          {user.picture && (
            <img
              src={user.picture}
              alt={user.name}
              style={{ width: 28, height: 28, borderRadius: '50%' }}
            />
          )}
          <span>{user.name || user.email}</span>
          <button
            onClick={handleLogout}
            style={{
              padding: '4px 12px',
              border: '1px solid #ddd',
              borderRadius: '999px',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: '0.8rem',
            }}
          >
            Sign Out
          </button>
        </div>
      )}

      <MapView ref={mapRef} />
      <SearchBar onLocationSelected={handleLocationSelected} />
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={handleSidebarToggle}
        activeNav={activeNav}
        onNavClick={handleNavClick}
      />
      <PolicyPanel
        parcel={selectedParcel}
        isOpen={isPanelOpen}
        onClose={handlePanelClose}
        activeNav={activeNav}
        savedParcels={savedParcels}
        onSaveParcel={handleSaveParcel}
      />
      {!isPanelOpen && (
        <button
          className="panel-reopen-tab"
          onClick={() => setIsPanelOpen(true)}
          title="Show project info"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
      )}
      <ChatPanel parcelContext={selectedParcel} />
    </>
  );
}