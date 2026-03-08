import { useEffect, useRef, useImperativeHandle, forwardRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import '../ModelViewer.css';

const DEFAULT_CENTER = [-79.3832, 43.6532];
const DEFAULT_ZOOM = 13;

const EMPTY_FC = { type: 'FeatureCollection', features: [] };

const PIPE_COLORS = {
    water_main: '#2277bb',
    sanitary_sewer: '#886644',
    storm_sewer: '#44aa66',
    gas_line: '#ddaa22',
};

const MapView = forwardRef(function MapView({ isParcelResolved, onModelOpen, isPanelOpen, isSidebarCollapsed, isChatExpanded, isModelOpen, assetType, onInfraAssetClick }, ref) {
    const containerRef = useRef(null);
    const mapInstanceRef = useRef(null);
    const markerRef = useRef(null);
    const popupRef = useRef(null);
    const [mapLoaded, setMapLoaded] = useState(false);

    // Store geojson safely if set before map loads
    const pendingParcelRef = useRef(null);
    const pendingMassingRef = useRef(null);

    useImperativeHandle(ref, () => ({
        getMap() {
            return mapInstanceRef.current;
        },
        flyTo(lng, lat, zoom = 16) {
            if (!mapInstanceRef.current) return;
            mapInstanceRef.current.flyTo({
                center: [lng, lat],
                zoom,
                duration: 2200,
                essential: true,
                curve: 1.42,
            });
        },
        setMarker(lng, lat) {
            const map = mapInstanceRef.current;
            if (!map) return;
            if (markerRef.current) markerRef.current.remove();

            const el = document.createElement('div');
            el.style.cssText = 'width:36px;height:36px;cursor:pointer;filter:drop-shadow(0 2px 6px rgba(0,0,0,0.5));';
            el.innerHTML = `<svg viewBox="0 0 24 24" fill="#c8a55c" stroke="#1a1a1a" stroke-width="1.5" width="36" height="36"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3" fill="#1a1a1a"/></svg>`;

            markerRef.current = new maplibregl.Marker({ element: el, anchor: 'bottom' })
                .setLngLat([lng, lat])
                .addTo(map);
        },
        setParcel(geojson) {
            if (!mapLoaded) {
                pendingParcelRef.current = geojson;
                return;
            }
            const map = mapInstanceRef.current;
            if (!map) return;
            if (map.getSource('parcel')) {
                map.getSource('parcel').setData(geojson || EMPTY_FC);
            }

            // Re-show buildings if parcel clears
            if (!geojson && map.getLayer('osm-buildings-3d')) {
                map.setFilter('osm-buildings-3d', null);
            }
        },
        setProposedMassing(geojson, height_m) {
            if (!mapLoaded) {
                pendingMassingRef.current = { geojson, height_m };
                return;
            }
            const map = mapInstanceRef.current;
            if (!map) return;

            if (map.getSource('proposed-massing')) {
                map.getSource('proposed-massing').setData(geojson || EMPTY_FC);
            }

            if (height_m && geojson) {
                map.setPaintProperty('proposed-massing-extrusion', 'fill-extrusion-height', height_m);
                map.flyTo({
                    pitch: 60,
                    bearing: 20,
                    duration: 3000,
                    essential: true
                });
            } else if (geojson === null) {
                if (map.getSource('proposed-massing')) {
                    const data = map.getSource('proposed-massing')._data;
                    if (data?.features?.length > 0) {
                        map.flyTo({
                            pitch: 0,
                            bearing: 0,
                            duration: 2000,
                            essential: true
                        });
                    }
                }
            }
        },
        /** Load pipeline GeoJSON onto the map */
        setPipelines(geojson) {
            const map = mapInstanceRef.current;
            if (!map || !mapLoaded) return;
            const fc = geojson || EMPTY_FC;
            if (map.getSource('pipelines')) {
                map.getSource('pipelines').setData(fc);
            }
            setInfraEmpty(!fc.features || fc.features.length === 0);
        },
        /** Load bridge GeoJSON onto the map */
        setBridges(geojson) {
            const map = mapInstanceRef.current;
            if (!map || !mapLoaded) return;
            const fc = geojson || EMPTY_FC;
            if (map.getSource('bridges')) {
                map.getSource('bridges').setData(fc);
            }
            setInfraEmpty(!fc.features || fc.features.length === 0);
        },
    }));

    // Track whether infra data has been loaded
    const [infraEmpty, setInfraEmpty] = useState(false);

    // Toggle layer visibility and camera based on asset type
    useEffect(() => {
        const map = mapInstanceRef.current;
        if (!map || !mapLoaded) return;

        const buildingLayers = ['osm-buildings-3d', 'parcel-fill', 'parcel-line', 'proposed-massing-extrusion'];
        const pipelineLayers = ['pipelines-line', 'pipelines-line-casing', 'pipelines-label'];
        const bridgeLayers = ['bridges-circle', 'bridges-label'];

        for (const id of buildingLayers) {
            if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', assetType === 'building' ? 'visible' : 'none');
        }
        for (const id of pipelineLayers) {
            if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', assetType === 'pipeline' ? 'visible' : 'none');
        }
        for (const id of bridgeLayers) {
            if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', assetType === 'bridge' ? 'visible' : 'none');
        }

        // Adjust camera for infrastructure modes
        if (assetType !== 'building') {
            map.easeTo({ pitch: 0, bearing: 0, duration: 800 });
            setInfraEmpty(true); // assume empty until data loads
        } else {
            setInfraEmpty(false);
        }
    }, [assetType, mapLoaded]);

    useEffect(() => {
        if (mapInstanceRef.current) return;

        const map = new maplibregl.Map({
            container: containerRef.current,
            style: 'https://tiles.openfreemap.org/styles/liberty',
            center: DEFAULT_CENTER,
            zoom: DEFAULT_ZOOM,
            pitch: 0,
            bearing: 0,
            antialias: true,
            maxZoom: 19,
            minZoom: 8,
        });

        mapInstanceRef.current = map;

        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
        map.addControl(
            new maplibregl.GeolocateControl({
                positionOptions: { enableHighAccuracy: true },
                trackUserLocation: false,
            }),
            'top-right'
        );

        map.on('style.load', () => {
            setMapLoaded(true);

            // Hide POI / shop name labels, show house numbers instead
            const style = map.getStyle();
            if (style?.layers) {
                for (const layer of style.layers) {
                    if (layer.id.includes('poi') || layer.id.includes('shop') || layer.id.includes('amenity')) {
                        map.setLayoutProperty(layer.id, 'visibility', 'none');
                    }
                    if (layer.id.includes('housenumber') || layer.id.includes('house-number') || layer.id.includes('address')) {
                        map.setLayoutProperty(layer.id, 'visibility', 'visible');
                        map.setPaintProperty(layer.id, 'text-color', '#555555');
                        map.setPaintProperty(layer.id, 'text-opacity', 1);
                    }
                }
            }

            // Add housenumber layer if none exists in the style
            if (map.getSource('openmaptiles') && !style?.layers?.some(l => l.id.includes('housenumber'))) {
                map.addLayer({
                    id: 'housenumber-labels',
                    type: 'symbol',
                    source: 'openmaptiles',
                    'source-layer': 'housenumber',
                    minzoom: 16,
                    layout: {
                        'text-field': '{housenumber}',
                        'text-size': 11,
                        'text-anchor': 'center',
                        'text-allow-overlap': false,
                    },
                    paint: {
                        'text-color': '#444444',
                        'text-halo-color': '#ffffff',
                        'text-halo-width': 1.5,
                    }
                });
            }

            // ─── Building Layers ───────────────────────────
            map.addLayer({
                'id': 'osm-buildings-3d',
                'source': 'openmaptiles',
                'source-layer': 'building',
                'type': 'fill-extrusion',
                'minzoom': 14,
                'paint': {
                    'fill-extrusion-color': '#e0e0e0',
                    'fill-extrusion-height': ['get', 'render_height'],
                    'fill-extrusion-base': ['get', 'render_min_height'],
                    'fill-extrusion-opacity': 0.6
                }
            });

            map.addSource('parcel', {
                type: 'geojson',
                data: pendingParcelRef.current || EMPTY_FC
            });

            map.addLayer({
                id: 'parcel-fill',
                type: 'fill',
                source: 'parcel',
                paint: {
                    'fill-color': '#c8a55c',
                    'fill-opacity': 0.2
                }
            });

            map.addLayer({
                id: 'parcel-line',
                type: 'line',
                source: 'parcel',
                paint: {
                    'line-color': '#c8a55c',
                    'line-width': 2
                }
            });

            const pendingM = pendingMassingRef.current;
            map.addSource('proposed-massing', {
                type: 'geojson',
                data: pendingM?.geojson || EMPTY_FC
            });

            map.addLayer({
                id: 'proposed-massing-extrusion',
                type: 'fill-extrusion',
                source: 'proposed-massing',
                paint: {
                    'fill-extrusion-color': '#c8a55c',
                    'fill-extrusion-height': pendingM?.height_m || 10,
                    'fill-extrusion-base': 0,
                    'fill-extrusion-opacity': 0.85
                }
            });

            // ─── Pipeline Layers ───────────────────────────
            map.addSource('pipelines', { type: 'geojson', data: EMPTY_FC });

            // Dark casing line (wider, behind)
            map.addLayer({
                id: 'pipelines-line-casing',
                type: 'line',
                source: 'pipelines',
                layout: { visibility: 'none', 'line-cap': 'round', 'line-join': 'round' },
                paint: {
                    'line-color': '#111111',
                    'line-width': ['interpolate', ['linear'], ['zoom'], 12, 3, 16, 7, 19, 12],
                    'line-opacity': 0.6,
                },
            });

            // Colored pipe line (narrower, in front)
            map.addLayer({
                id: 'pipelines-line',
                type: 'line',
                source: 'pipelines',
                layout: { visibility: 'none', 'line-cap': 'round', 'line-join': 'round' },
                paint: {
                    'line-color': ['coalesce', ['get', 'color'], '#888888'],
                    'line-width': ['interpolate', ['linear'], ['zoom'], 12, 1.5, 16, 4, 19, 8],
                    'line-opacity': 0.9,
                },
            });

            // Pipeline labels at higher zoom
            map.addLayer({
                id: 'pipelines-label',
                type: 'symbol',
                source: 'pipelines',
                minzoom: 15,
                layout: {
                    visibility: 'none',
                    'symbol-placement': 'line',
                    'text-field': ['concat',
                        ['upcase', ['get', 'pipe_type']],
                        ['case', ['has', 'diameter_mm'],
                            ['concat', ' ', ['to-string', ['get', 'diameter_mm']], 'mm'],
                            ''
                        ]
                    ],
                    'text-size': 10,
                    'text-offset': [0, -1],
                    'text-allow-overlap': false,
                },
                paint: {
                    'text-color': '#f0ece4',
                    'text-halo-color': '#1a1a1a',
                    'text-halo-width': 1.5,
                },
            });

            // ─── Bridge Layers ─────────────────────────────
            map.addSource('bridges', { type: 'geojson', data: EMPTY_FC });

            map.addLayer({
                id: 'bridges-circle',
                type: 'circle',
                source: 'bridges',
                layout: { visibility: 'none' },
                paint: {
                    'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 4, 14, 8, 18, 14],
                    'circle-color': '#dd6644',
                    'circle-stroke-width': 2,
                    'circle-stroke-color': '#1a1a1a',
                    'circle-opacity': 0.9,
                },
            });

            map.addLayer({
                id: 'bridges-label',
                type: 'symbol',
                source: 'bridges',
                minzoom: 13,
                layout: {
                    visibility: 'none',
                    'text-field': ['coalesce', ['get', 'road_name'], ['get', 'bridge_type']],
                    'text-size': 11,
                    'text-offset': [0, 1.5],
                    'text-anchor': 'top',
                    'text-allow-overlap': false,
                },
                paint: {
                    'text-color': '#f0ece4',
                    'text-halo-color': '#1a1a1a',
                    'text-halo-width': 1.5,
                },
            });

            // ─── Click handlers for infrastructure ─────────
            map.on('click', 'pipelines-line', (e) => {
                if (!e.features?.length) return;
                const props = e.features[0].properties;
                if (popupRef.current) popupRef.current.remove();
                const label = (props.pipe_type || '').replace(/_/g, ' ');
                popupRef.current = new maplibregl.Popup({ closeButton: true, maxWidth: '260px' })
                    .setLngLat(e.lngLat)
                    .setHTML(`
                        <div style="font-family:Inter,sans-serif;font-size:12px;color:#1a1a1a">
                            <strong style="text-transform:capitalize">${label}</strong><br/>
                            ${props.diameter_mm ? `Diameter: ${props.diameter_mm}mm<br/>` : ''}
                            ${props.material ? `Material: ${props.material}<br/>` : ''}
                            ${props.install_year ? `Installed: ${props.install_year}<br/>` : ''}
                            ${props.depth_m ? `Depth: ${props.depth_m}m<br/>` : ''}
                            ${props.distance_m ? `<span style="color:#888">${props.distance_m}m away</span>` : ''}
                        </div>
                    `)
                    .addTo(map);
                if (onInfraAssetClick) onInfraAssetClick({ type: 'pipeline', ...props });
            });

            map.on('click', 'bridges-circle', (e) => {
                if (!e.features?.length) return;
                const props = e.features[0].properties;
                if (popupRef.current) popupRef.current.remove();
                popupRef.current = new maplibregl.Popup({ closeButton: true, maxWidth: '260px' })
                    .setLngLat(e.lngLat)
                    .setHTML(`
                        <div style="font-family:Inter,sans-serif;font-size:12px;color:#1a1a1a">
                            <strong>${props.road_name || 'Bridge'}</strong>
                            ${props.crossing_name ? `<br/>Over: ${props.crossing_name}` : ''}<br/>
                            Type: ${(props.bridge_type || '').replace(/_/g, ' ')}<br/>
                            ${props.span_m ? `Span: ${props.span_m}m<br/>` : ''}
                            ${props.year_built ? `Built: ${props.year_built}<br/>` : ''}
                            ${props.condition_rating ? `Condition: ${props.condition_rating}<br/>` : ''}
                            ${props.distance_m ? `<span style="color:#888">${props.distance_m}m away</span>` : ''}
                        </div>
                    `)
                    .addTo(map);
                if (onInfraAssetClick) onInfraAssetClick({ type: 'bridge', ...props });
            });

            // Cursor styling for interactive layers
            for (const layerId of ['pipelines-line', 'bridges-circle']) {
                map.on('mouseenter', layerId, () => { map.getCanvas().style.cursor = 'pointer'; });
                map.on('mouseleave', layerId, () => { map.getCanvas().style.cursor = ''; });
            }
        });

        return () => {
            map.remove();
            mapInstanceRef.current = null;
        };
    }, []);

    const MODE_LABELS = { building: null, pipeline: 'Pipeline Network', bridge: 'Bridge Inventory' };
    const MODE_ICONS = { pipeline: '⏣', bridge: '⌓' };
    const MODE_COLORS = { pipeline: '#44aa66', bridge: '#dd6644' };

    return (
        <>
            <div id="map" ref={containerRef} style={{ width: '100%', height: '100%', minHeight: '400px' }} />

            {/* Infrastructure mode banner */}
            {assetType !== 'building' && (
                <div style={{
                    position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)',
                    background: '#1a1a1a', border: `1px solid ${MODE_COLORS[assetType]}`,
                    borderRadius: 8, padding: '8px 20px', zIndex: 20,
                    display: 'flex', alignItems: 'center', gap: 8,
                    fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#f0ece4',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.5)', pointerEvents: 'none',
                }}>
                    <span style={{ fontSize: 18 }}>{MODE_ICONS[assetType]}</span>
                    <span style={{ color: MODE_COLORS[assetType], fontWeight: 600 }}>{MODE_LABELS[assetType]}</span>
                    <span style={{ color: '#888', fontSize: 11, marginLeft: 4 }}>
                        {assetType === 'pipeline' ? 'Water, Sanitary, Storm, Gas' : 'Road, Pedestrian, Culvert'}
                    </span>
                </div>
            )}

            {/* Empty state for infrastructure */}
            {assetType !== 'building' && infraEmpty && (
                <div style={{
                    position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                    background: 'rgba(26,26,26,0.92)', borderRadius: 12, padding: '32px 40px',
                    zIndex: 15, textAlign: 'center', maxWidth: 360,
                    fontFamily: 'Inter, sans-serif', color: '#f0ece4',
                    boxShadow: '0 8px 32px rgba(0,0,0,0.6)', border: '1px solid #333',
                }}>
                    <div style={{ fontSize: 36, marginBottom: 12, opacity: 0.6 }}>
                        {assetType === 'pipeline' ? '⏣' : '⌓'}
                    </div>
                    <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>
                        No {assetType === 'pipeline' ? 'pipeline' : 'bridge'} data in this area
                    </div>
                    <div style={{ fontSize: 12, color: '#888', lineHeight: 1.5 }}>
                        Run ingestion to load Toronto Open Data:<br/>
                        <code style={{ color: '#c8a55c', fontSize: 11 }}>
                            POST /api/v1/admin/ingest/{assetType === 'pipeline' ? 'water-mains' : 'bridges'}
                        </code>
                    </div>
                </div>
            )}

            {isParcelResolved && !isModelOpen && (
                <button
                    className="map-model-btn"
                    onClick={onModelOpen}
                    title="Open 3D Model"
                    style={{
                        right: `${(isPanelOpen ? 380 : 0) + 16}px`,
                        bottom: `${(isChatExpanded ? 328 : 48) + 16}px`,
                        transition: 'right 0.3s ease, bottom 0.3s ease',
                    }}
                >
                    ⬡ Model
                </button>
            )}
        </>
    );
});

export default MapView;
