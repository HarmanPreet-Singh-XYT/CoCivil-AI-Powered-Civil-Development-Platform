import { useState, useCallback, useRef } from 'react';
import maplibregl from 'maplibre-gl';

/**
 * Layer configuration for all infrastructure datasets.
 * Each layer is lazy-loaded on first toggle.
 */
const LAYER_GROUPS = [
  {
    id: 'roads',
    label: 'Roads',
    icon: '\u{1F6E3}',
    layers: [
      {
        id: 'road-reconstruction',
        label: 'Road Reconstruction Program',
        file: '/data/road-reconstruction.geojson',
        type: 'line',
        color: '#e74c3c',
        width: 3,
        sizeMB: 0.5,
      },
    ],
  },
  {
    id: 'water',
    label: 'Water System',
    icon: '\u{1F4A7}',
    layers: [
      {
        id: 'parks-drinking-water',
        label: 'Parks Drinking Water Sources',
        file: '/data/parks-drinking-water.geojson',
        type: 'circle',
        color: '#3498db',
        radius: 5,
        sizeMB: 0.5,
      },
      {
        id: 'toronto-watermain',
        label: 'Toronto Watermain',
        file: '/data/toronto-watermain.geojson',
        type: 'line',
        color: '#2980b9',
        width: 2,
        sizeMB: 1.8,
      },
      {
        id: 'water-fitting',
        label: 'Water Fittings',
        file: '/data/water-fitting.geojson',
        type: 'circle',
        color: '#1abc9c',
        radius: 3,
        sizeMB: 2.5,
      },
      {
        id: 'water-hydrants',
        label: 'Water Hydrants',
        file: '/data/water-hydrants.geojson',
        type: 'circle',
        color: '#e67e22',
        radius: 4,
        sizeMB: 12.6,
      },
      {
        id: 'water-valve',
        label: 'Water Valves',
        file: '/data/water-valve.geojson',
        type: 'circle',
        color: '#9b59b6',
        radius: 3,
        sizeMB: 18.3,
      },
      {
        id: 'watermain-distribution',
        label: 'Watermain Distribution',
        file: '/data/watermain-distribution.geojson',
        type: 'line',
        color: '#16a085',
        width: 1.5,
        sizeMB: 38,
      },
    ],
  },
  {
    id: 'electric',
    label: 'EV Charging',
    icon: '\u26A1',
    layers: [
      {
        id: 'ev-charging',
        label: 'EV Charging Stations',
        file: '/data/ev-charging.geojson',
        type: 'circle',
        color: '#27ae60',
        radius: 7,
        sizeMB: 0.02,
      },
    ],
  },
];

const EMPTY_FC = { type: 'FeatureCollection', features: [] };

export default function InfrastructureLayerControl({ mapRef }) {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState({ roads: true, water: true, electric: true });
  const [activeLayerIds, setActiveLayerIds] = useState(new Set());
  const [loadingLayerIds, setLoadingLayerIds] = useState(new Set());
  const geojsonCache = useRef({});

  const toggleGroup = useCallback((groupId) => {
    setExpandedGroups((prev) => ({ ...prev, [groupId]: !prev[groupId] }));
  }, []);

  const addLayerToMap = useCallback((map, layerConfig, data) => {
    const sourceId = `infra-${layerConfig.id}`;

    if (!map.getSource(sourceId)) {
      map.addSource(sourceId, { type: 'geojson', data });
    }

    if (layerConfig.type === 'line') {
      if (!map.getLayer(sourceId)) {
        map.addLayer({
          id: sourceId,
          type: 'line',
          source: sourceId,
          paint: {
            'line-color': layerConfig.color,
            'line-width': layerConfig.width || 2,
            'line-opacity': 0.8,
          },
        });
      }
    } else {
      // circle for point data
      if (!map.getLayer(sourceId)) {
        map.addLayer({
          id: sourceId,
          type: 'circle',
          source: sourceId,
          paint: {
            'circle-color': layerConfig.color,
            'circle-radius': layerConfig.radius || 4,
            'circle-opacity': 0.85,
            'circle-stroke-color': '#fff',
            'circle-stroke-width': 1,
          },
        });
      }

      // Add a popup on click for point layers
      map.on('click', sourceId, (e) => {
        if (!e.features?.length) return;
        const props = e.features[0].properties;
        const rows = Object.entries(props)
          .filter(([k]) => !k.startsWith('_'))
          .map(([k, v]) => `<tr><td style="font-weight:600;padding:2px 8px 2px 0;color:#888;white-space:nowrap">${k}</td><td style="padding:2px 0">${v ?? ''}</td></tr>`)
          .join('');
        const html = `<table style="font-size:12px;max-width:300px">${rows}</table>`;

        new maplibregl.Popup({ maxWidth: '340px' })
          .setLngLat(e.lngLat)
          .setHTML(html)
          .addTo(map);
      });

      map.on('mouseenter', sourceId, () => { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mouseleave', sourceId, () => { map.getCanvas().style.cursor = ''; });
    }
  }, []);

  const removeLayerFromMap = useCallback((map, layerConfig) => {
    const sourceId = `infra-${layerConfig.id}`;
    if (map.getLayer(sourceId)) map.removeLayer(sourceId);
    if (map.getSource(sourceId)) map.removeSource(sourceId);
  }, []);

  const toggleLayer = useCallback(async (layerConfig) => {
    const map = mapRef.current?.getMap();
    if (!map) return;

    const isActive = activeLayerIds.has(layerConfig.id);

    if (isActive) {
      // Turn off
      removeLayerFromMap(map, layerConfig);
      setActiveLayerIds((prev) => {
        const next = new Set(prev);
        next.delete(layerConfig.id);
        return next;
      });
    } else {
      // Turn on — fetch data if not cached
      if (!geojsonCache.current[layerConfig.id]) {
        setLoadingLayerIds((prev) => new Set(prev).add(layerConfig.id));
        try {
          const res = await fetch(layerConfig.file);
          const data = await res.json();
          geojsonCache.current[layerConfig.id] = data;
        } catch (err) {
          console.error(`Failed to load ${layerConfig.file}:`, err);
          setLoadingLayerIds((prev) => {
            const next = new Set(prev);
            next.delete(layerConfig.id);
            return next;
          });
          return;
        }
        setLoadingLayerIds((prev) => {
          const next = new Set(prev);
          next.delete(layerConfig.id);
          return next;
        });
      }

      addLayerToMap(map, layerConfig, geojsonCache.current[layerConfig.id]);
      setActiveLayerIds((prev) => new Set(prev).add(layerConfig.id));
    }
  }, [mapRef, activeLayerIds, addLayerToMap, removeLayerFromMap]);

  // Need maplibregl for popups — import at module top won't work since it's already imported in MapView.
  // We'll use dynamic import inline or just rely on the global. Actually let's import it.
  // The popup import is handled below via the map's maplibregl reference.

  return (
    <div style={{
      position: 'absolute',
      bottom: 16,
      left: 16,
      zIndex: 10,
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    }}>
      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen((v) => !v)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '8px 14px',
          background: isOpen ? '#1a1a1a' : 'rgba(26,26,26,0.9)',
          color: '#e0d6c2',
          border: '1px solid rgba(200,165,92,0.3)',
          borderRadius: 8,
          cursor: 'pointer',
          fontSize: 13,
          fontWeight: 500,
          backdropFilter: 'blur(12px)',
          transition: 'all 0.2s',
          boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
        }}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <polygon points="12 2 2 7 12 12 22 7" />
          <polyline points="2 17 12 22 22 17" />
          <polyline points="2 12 12 17 22 12" />
        </svg>
        Layers
        {activeLayerIds.size > 0 && (
          <span style={{
            background: '#c8a55c',
            color: '#1a1a1a',
            borderRadius: '50%',
            width: 18,
            height: 18,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 10,
            fontWeight: 700,
          }}>
            {activeLayerIds.size}
          </span>
        )}
      </button>

      {/* Layer Panel */}
      {isOpen && (
        <div style={{
          position: 'absolute',
          bottom: 44,
          left: 0,
          width: 280,
          maxHeight: 420,
          overflowY: 'auto',
          background: 'rgba(26,26,26,0.95)',
          border: '1px solid rgba(200,165,92,0.2)',
          borderRadius: 10,
          padding: '8px 0',
          backdropFilter: 'blur(16px)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        }}>
          <div style={{
            padding: '8px 14px 6px',
            fontSize: 11,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: '#888',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            marginBottom: 4,
          }}>
            Infrastructure Layers
          </div>

          {LAYER_GROUPS.map((group) => (
            <div key={group.id}>
              {/* Group Header */}
              <button
                onClick={() => toggleGroup(group.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  width: '100%',
                  padding: '8px 14px',
                  background: 'none',
                  border: 'none',
                  color: '#e0d6c2',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: 600,
                  textAlign: 'left',
                }}
              >
                <span style={{ fontSize: 14 }}>{group.icon}</span>
                {group.label}
                <svg
                  width="12" height="12" viewBox="0 0 24 24"
                  fill="none" stroke="currentColor" strokeWidth="2"
                  style={{
                    marginLeft: 'auto',
                    transform: expandedGroups[group.id] ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s',
                  }}
                >
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>

              {/* Layer Items */}
              {expandedGroups[group.id] && group.layers.map((layer) => {
                const isActive = activeLayerIds.has(layer.id);
                const isLoading = loadingLayerIds.has(layer.id);

                return (
                  <label
                    key={layer.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '6px 14px 6px 34px',
                      cursor: isLoading ? 'wait' : 'pointer',
                      fontSize: 12,
                      color: isActive ? '#e0d6c2' : '#999',
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'none'; }}
                  >
                    {/* Custom Checkbox */}
                    <span
                      onClick={(e) => {
                        e.preventDefault();
                        if (!isLoading) toggleLayer(layer);
                      }}
                      style={{
                        width: 16,
                        height: 16,
                        borderRadius: 4,
                        border: isActive ? 'none' : '1.5px solid #555',
                        background: isActive ? layer.color : 'transparent',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        transition: 'all 0.15s',
                      }}
                    >
                      {isActive && (
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      )}
                      {isLoading && (
                        <span style={{
                          width: 10,
                          height: 10,
                          border: '2px solid transparent',
                          borderTop: `2px solid ${layer.color}`,
                          borderRadius: '50%',
                          animation: 'infra-spin 0.8s linear infinite',
                        }} />
                      )}
                    </span>

                    <span style={{ flex: 1 }}>{layer.label}</span>

                    {layer.sizeMB > 5 && (
                      <span style={{
                        fontSize: 9,
                        color: '#666',
                        padding: '1px 5px',
                        background: 'rgba(255,255,255,0.05)',
                        borderRadius: 3,
                      }}>
                        {layer.sizeMB}MB
                      </span>
                    )}
                  </label>
                );
              })}
            </div>
          ))}
        </div>
      )}

      {/* Spinner animation */}
      <style>{`
        @keyframes infra-spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
