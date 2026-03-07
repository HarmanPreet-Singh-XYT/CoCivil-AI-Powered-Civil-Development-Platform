import { useState, useRef, useCallback } from 'react';
import MapView from './components/MapView.jsx';
import SearchBar from './components/SearchBar.jsx';
import Sidebar from './components/Sidebar.jsx';
import PolicyPanel from './components/PolicyPanel.jsx';
import ChatPanel from './components/ChatPanel.jsx';
import LandingPage from './components/LandingPage.jsx';
import './landing.css';

export default function App() {
  const [currentPage, setCurrentPage] = useState('landing');
  const [selectedParcel, setSelectedParcel] = useState(null);
  const [isPanelOpen, setIsPanelOpen] = useState(true);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [activeNav, setActiveNav] = useState('overview');
  const [pendingAddress, setPendingAddress] = useState(null);

  const mapRef = useRef(null);

  const handleLocationSelected = useCallback((location) => {
    if (mapRef.current) {
      mapRef.current.flyTo(location.lng, location.lat, 16);
      mapRef.current.setMarker(location.lng, location.lat);
    }
    const zonings = ['R', 'RD', 'RS', 'RT', 'RM', 'RA', 'CR'];
    const randomZoning = zonings[Math.floor(Math.random() * zonings.length)];
    const parcel = {
      address: location.shortAddress || location.address,
      zoning: randomZoning,
      lotArea: 300 + Math.floor(Math.random() * 500),
    };
    setSelectedParcel(parcel);
    setIsPanelOpen(true);
  }, []);

  const handleParcelSelect = useCallback((parcel) => {
    setSelectedParcel(parcel);
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
  }, []);

  // Navigate from landing to dashboard
  const handleLandingNavigate = useCallback(async (address) => {
    setCurrentPage('dashboard');

    if (address) {
      // Geocode the address and fly to it
      try {
        const res = await fetch(
          `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(address + ' Toronto Canada')}&format=json&addressdetails=1&limit=1&countrycodes=ca`,
          { headers: { 'Accept-Language': 'en' } }
        );
        const results = await res.json();
        if (results.length > 0) {
          const result = results[0];
          const addr = result.address || {};
          const parts = [];
          if (addr.house_number) parts.push(addr.house_number);
          if (addr.road) parts.push(addr.road);
          let shortAddress = parts.join(' ') || result.display_name.split(',')[0];
          if (addr.city || addr.town) shortAddress += `, ${addr.city || addr.town}`;

          // Small delay to let the map mount
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
  }, [handleLocationSelected]);

  // Landing page
  if (currentPage === 'landing') {
    return <LandingPage onNavigate={handleLandingNavigate} />;
  }

  // Dashboard — apply body classes
  const bodyClasses = [];
  if (isSidebarCollapsed) bodyClasses.push('sidebar-collapsed');
  if (isPanelOpen) bodyClasses.push('panel-open');
  if (typeof document !== 'undefined') {
    document.body.className = bodyClasses.join(' ');
  }

  return (
    <>
      <MapView ref={mapRef} onParcelSelect={handleParcelSelect} />

      <SearchBar
        isSidebarCollapsed={isSidebarCollapsed}
        onLocationSelected={handleLocationSelected}
      />

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
      />

      {/* Small tab to reopen the panel when closed */}
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
