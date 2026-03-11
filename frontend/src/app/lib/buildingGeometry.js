/**
 * Building geometry utilities for 3D model viewer.
 * Converts GeoJSON polygon footprints into Three.js geometry data.
 */

/**
 * Convert GeoJSON polygon coordinates to local XZ metre offsets.
 * Returns array of [x, z] pairs centred at [0,0].
 */
export function geoJSONPolygonToLocal(coordinates) {
  // coordinates is the outer ring: [[lng, lat], ...]
  const ring = coordinates[0];

  // Compute centroid
  let sumLng = 0, sumLat = 0;
  for (const [lng, lat] of ring) { sumLng += lng; sumLat += lat; }
  const cLng = sumLng / ring.length;
  const cLat = sumLat / ring.length;

  const cosLat = Math.cos((cLat * Math.PI) / 180);
  const METRES_PER_DEG_LAT = 111320;

  return ring.map(([lng, lat]) => [
    (lng - cLng) * METRES_PER_DEG_LAT * cosLat,
    (lat - cLat) * METRES_PER_DEG_LAT,
  ]);
}

/**
 * Shrink a convex/near-rectangular polygon inward by offsetM metres.
 * Naive centroid-based offset — works well for rectangular parcels.
 */
export function shrinkPolygon(points, offsetM) {
  if (offsetM <= 0) return points;

  const cx = points.reduce((s, p) => s + p[0], 0) / points.length;
  const cz = points.reduce((s, p) => s + p[1], 0) / points.length;

  return points.map(([x, z]) => {
    const dx = x - cx;
    const dz = z - cz;
    const dist = Math.sqrt(dx * dx + dz * dz) || 1;
    const ratio = Math.max(0, (dist - offsetM) / dist);
    return [cx + dx * ratio, cz + dz * ratio];
  });
}

/**
 * Build a simple rectangular footprint (metres) centred at origin.
 * Used when no real parcel geometry is available.
 */
export function defaultFootprint(widthM = 20, depthM = 15) {
  const hw = widthM / 2;
  const hd = depthM / 2;
  return [
    [-hw, -hd],
    [hw, -hd],
    [hw, hd],
    [-hw, hd],
    [-hw, -hd],
  ];
}

/**
 * Convert flat [x, z][] points to Three.js Shape (in XY space; Y maps to Z in 3D).
 */
export function pointsToShape(points) {
  // Dynamic import to avoid loading Three.js at module parse time
  const { Shape } = window.__THREE__ || {};
  if (Shape) {
    const shape = new Shape();
    shape.moveTo(points[0][0], points[0][1]);
    for (let i = 1; i < points.length; i++) shape.lineTo(points[i][0], points[i][1]);
    shape.closePath();
    return shape;
  }
  return null;
}

/**
 * Generate a circular footprint as an array of [x, z] points.
 */
export function makeCircularFootprint(radiusM, segments = 24) {
  const points = [];
  for (let i = 0; i <= segments; i++) {
    const angle = (i / segments) * Math.PI * 2;
    points.push([
      Math.cos(angle) * radiusM,
      Math.sin(angle) * radiusM,
    ]);
  }
  return points;
}

/**
 * Subdivide a rectangular footprint into row units along the X axis.
 * Returns array of { points, index } for each unit.
 */
export function subdivideFootprintIntoUnits(footprint, unitWidth = 6) {
  // Compute bounding box
  let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
  for (const [x, z] of footprint) {
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (z < minZ) minZ = z;
    if (z > maxZ) maxZ = z;
  }

  const totalWidth = maxX - minX;
  const unitCount = Math.max(1, Math.round(totalWidth / unitWidth));
  const actualUnitW = totalWidth / unitCount;

  const units = [];
  for (let i = 0; i < unitCount; i++) {
    const x0 = minX + i * actualUnitW;
    const x1 = x0 + actualUnitW;
    units.push({
      points: [
        [x0, minZ],
        [x1, minZ],
        [x1, maxZ],
        [x0, maxZ],
        [x0, minZ],
      ],
      index: i,
    });
  }
  return units;
}

/**
 * Extract footprint points from a GeoJSON geometry or Feature.
 * Falls back to default rectangular footprint.
 */
export function extractFootprint(parcelGeoJSON) {
  try {
    let geom = parcelGeoJSON;
    if (geom?.type === 'Feature') geom = geom.geometry;
    if (geom?.type === 'FeatureCollection') geom = geom.features?.[0]?.geometry;

    if (geom?.type === 'Polygon' && geom.coordinates?.length > 0) {
      return geoJSONPolygonToLocal(geom.coordinates);
    }
    if (geom?.type === 'MultiPolygon' && geom.coordinates?.length > 0) {
      return geoJSONPolygonToLocal(geom.coordinates[0]);
    }
  } catch {
    // fall through
  }
  return defaultFootprint();
}
