import { useEffect, useRef, useImperativeHandle, forwardRef } from 'react';
import maplibregl from 'maplibre-gl';

const DEFAULT_CENTER = [-79.3832, 43.6532];
const DEFAULT_ZOOM = 13;

const MapView = forwardRef(function MapView({ onParcelSelect }, ref) {
    const containerRef = useRef(null);
    const mapInstanceRef = useRef(null);
    const markerRef = useRef(null);

    useImperativeHandle(ref, () => ({
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
    }));

    useEffect(() => {
        if (mapInstanceRef.current) return;

        const map = new maplibregl.Map({
            container: containerRef.current,
            style: {
                version: 8,
                name: 'Arterial Cadastral',
                sources: {
                    'osm-tiles': {
                        type: 'raster',
                        tiles: [
                            'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
                            'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png',
                            'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png',
                        ],
                        tileSize: 256,
                        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                    },
                },
                layers: [
                    {
                        id: 'osm-base',
                        type: 'raster',
                        source: 'osm-tiles',
                        minzoom: 0,
                        maxzoom: 19,
                        paint: {
                            'raster-saturation': -0.75,
                            'raster-brightness-min': 0.08,
                            'raster-brightness-max': 0.5,
                            'raster-contrast': 0.2,
                        },
                    },
                ],
                glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
            },
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

        return () => {
            map.remove();
            mapInstanceRef.current = null;
        };
    }, []);

    return <div id="map" ref={containerRef} />;
});

export default MapView;
