import { useState, useRef, useCallback, useEffect, useMemo, lazy, Suspense } from 'react';
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

const ModelViewer = lazy(() => import('./components/ModelViewer.jsx'));

export default function App() {
  const { isLoading, isAuthenticated, loginWithRedirect, user } = useAuth0();

  const [currentPage, setCurrentPage] = useState('landing');
  const [selectedParcel, setSelectedParcel] = useState(null);
  const [isPanelOpen, setIsPanelOpen] = useState(true);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [activeNav, setActiveNav] = useState('overview');
  const [savedParcels, setSavedParcels] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [isChatExpanded, setIsChatExpanded] = useState(false);
  const [modelParams, setModelParams] = useState(null);
  const [isModelOpen, setIsModelOpen] = useState(false);
  const [analyzedUploads, setAnalyzedUploads] = useState([]);
  const [floorPlans, setFloorPlans] = useState(null);
  const [projectId, setProjectId] = useState(null);
  const [activePlanId, setActivePlanId] = useState(null);

  const handleUploadAnalyzed = useCallback((upload) => {
    setAnalyzedUploads((prev) => {
      // Deduplicate by id
      if (prev.some((u) => u.id === upload.id)) return prev;
      return [...prev, upload];
    });
    // If upload has floor plan data, set it and open model viewer
    if (upload.extractedData?.floor_plans) {
      setFloorPlans(upload.extractedData.floor_plans);
      setProjectId(upload.id); // Use upload id as project scope
      setIsModelOpen(true);
    }
  }, []);

  const historyKey = useMemo(
    () => (user?.sub ? `arterial_history_${user.sub}` : null),
    [user?.sub]
  );

  const [searchHistory, setSearchHistory] = useState(() => {
    // Will be properly loaded once user is available
    return [];
  });

  // Load history from localStorage once user is available
  useEffect(() => {
    if (!historyKey) return;
    try {
      const stored = localStorage.getItem(historyKey);
      if (stored) setSearchHistory(JSON.parse(stored));
    } catch {
      // ignore corrupt data
    }
  }, [historyKey]);

  // Store pending address to process after authentication
  const [pendingAddress, setPendingAddress] = useState(null);

  const mapRef = useRef(null);

  const handleLocationSelected = useCallback(async (location) => {
    if (mapRef.current) {
      mapRef.current.flyTo(location.lng, location.lat, 18);
      mapRef.current.setMarker(location.lng, location.lat);
      mapRef.current.setProposedMassing(null, null);
    }

    const parcels = await searchParcels(location.shortAddress || location.address);
    const selected = buildParcelState(location, parcels);
    setSelectedParcel(selected);
    setIsPanelOpen(true);

    // Save to search history
    if (historyKey) {
      const entry = {
        address: location.shortAddress || location.address,
        fullAddress: location.address,
        lng: location.lng,
        lat: location.lat,
        timestamp: Date.now(),
      };
      setSearchHistory((prev) => {
        const filtered = prev.filter((h) => h.address !== entry.address);
        const updated = [entry, ...filtered].slice(0, 50);
        localStorage.setItem(historyKey, JSON.stringify(updated));
        return updated;
      });
    }

    if (mapRef.current && isResolvedParcel(selected) && selected.geom) {
      mapRef.current.setParcel(selected.geom);
    } else if (mapRef.current) {
      mapRef.current.setParcel(null);
    }
  }, [historyKey]);

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

  const handleHistoryItemClick = useCallback(
    (item) => {
      setShowHistory(false);
      handleLocationSelected({
        lng: item.lng,
        lat: item.lat,
        address: item.fullAddress,
        shortAddress: item.address,
      });
    },
    [handleLocationSelected]
  );

  const handleLandingNavigate = useCallback(
    async (address) => {
      // If user is not authenticated, store the address and redirect to login
      if (!isAuthenticated) {
        if (address) {
          setPendingAddress(address);
          // Store in sessionStorage so it persists through the redirect
          sessionStorage.setItem('pendingAddress', address);
        }
        loginWithRedirect({
          appState: { returnTo: '/dashboard', pendingAddress: address },
        });
        return;
      }

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
    [handleLocationSelected, isAuthenticated, loginWithRedirect]
  );

  // After authentication, process any pending address
  useEffect(() => {
    if (isAuthenticated && !isLoading && currentPage === 'landing') {
      const stored = sessionStorage.getItem('pendingAddress');
      if (stored) {
        sessionStorage.removeItem('pendingAddress');
        handleLandingNavigate(stored);
      }
    }
  }, [isAuthenticated, isLoading, currentPage, handleLandingNavigate]);

  // Redirect unauthenticated users away from dashboard
  useEffect(() => {
    if (!isLoading && !isAuthenticated && currentPage === 'dashboard') {
      loginWithRedirect();
    }
  }, [isLoading, isAuthenticated, currentPage, loginWithRedirect]);

  useEffect(() => {
    if (typeof document === 'undefined') return undefined;

    const isDashboard = currentPage === 'dashboard';
    document.body.classList.toggle(
      'sidebar-collapsed',
      isDashboard && isSidebarCollapsed
    );
    document.body.classList.toggle('panel-open', isDashboard && isPanelOpen);

    // Update persistent map padding so "center" = center of visible gap
    if (isDashboard && mapRef.current?.getMap()) {
      const left = isSidebarCollapsed ? 52 : 160;
      const right = isPanelOpen ? 380 : 0;
      const bottom = isChatExpanded ? 328 : 48;
      mapRef.current.getMap().easeTo({
        padding: { left, right, top: 0, bottom },
        duration: 300,
      });
    }

    return () => {
      document.body.classList.remove('sidebar-collapsed');
      document.body.classList.remove('panel-open');
    };
  }, [currentPage, isSidebarCollapsed, isPanelOpen, isChatExpanded]);

  // Landing — no auth gate
  if (currentPage === 'landing') {
    return <LandingPage onNavigate={handleLandingNavigate} />;
  }

  // Dashboard loading or waiting for auth
  if (isLoading || !isAuthenticated) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          background: '#fafafa',
        }}
      >
        <p>Loading...</p>
      </div>
    );
  }

  // Dashboard (authenticated only)
  return (
    <>

      <MapView
        ref={mapRef}
        isParcelResolved={selectedParcel !== null}
        onModelOpen={() => setIsModelOpen(true)}
        isPanelOpen={isPanelOpen}
        isSidebarCollapsed={isSidebarCollapsed}
        isChatExpanded={isChatExpanded}
        isModelOpen={isModelOpen}
      />
      <SearchBar onLocationSelected={handleLocationSelected} />
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={handleSidebarToggle}
        activeNav={activeNav}
        onNavClick={handleNavClick}
        showHistory={showHistory}
        onHistoryClick={() => setShowHistory(true)}
        onHistoryBack={() => setShowHistory(false)}
        historyItems={searchHistory}
        onHistoryItemClick={handleHistoryItemClick}
      />
      <PolicyPanel
        parcel={selectedParcel}
        isOpen={isPanelOpen}
        onClose={handlePanelClose}
        activeNav={activeNav}
        savedParcels={savedParcels}
        onSaveParcel={handleSaveParcel}
        onUploadAnalyzed={handleUploadAnalyzed}
        activePlanId={activePlanId}
      />
      {!isPanelOpen && (
        <button
          className="panel-reopen-tab"
          onClick={() => setIsPanelOpen(true)}
          title="Show project info"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
      )}
      <ChatPanel
        parcelContext={selectedParcel}
        onToggleExpand={setIsChatExpanded}
        modelParams={modelParams}
        onModelUpdate={(params) => { setModelParams(params); setIsModelOpen(true); }}
        analyzedUploads={analyzedUploads}
        activePlanId={activePlanId}
        onPlanComplete={(massing, planId) => {
          if (planId) setActivePlanId(planId);
          if (mapRef.current && selectedParcel?.geom) {
            mapRef.current.setProposedMassing(selectedParcel.geom, massing.height_m || (massing.storeys * 3.5));
          }
          setModelParams({
            storeys: massing.storeys || 0,
            podium_storeys: massing.typology === 'tower_on_podium' ? 4 : 0,
            height_m: massing.height_m || (massing.storeys * 3.5),
            setback_m: massing.assumptions_used?.stepback_m ?? 3.0,
            typology: massing.typology || 'midrise',
            footprint_coverage: massing.lot_coverage_pct ? massing.lot_coverage_pct / 100 : 0.6,
          });
        }}
      />
      <Suspense fallback={null}>
        <ModelViewer
          isOpen={isModelOpen}
          onClose={() => setIsModelOpen(false)}
          parcelGeoJSON={selectedParcel?.geom}
          modelParams={modelParams}
          isPanelOpen={isPanelOpen}
          isSidebarCollapsed={isSidebarCollapsed}
          isChatExpanded={isChatExpanded}
          floorPlans={floorPlans}
          projectId={projectId}
          parcelId={selectedParcel?.id}
        />
      </Suspense>
    </>
  );
}