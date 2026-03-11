/**
 * Infrastructure geometry utilities for pipe network 3D visualization.
 * Converts alignment coordinates into Three.js geometry for pipes, manholes, and fittings.
 */
import * as THREE from 'three';

/**
 * Convert alignment coordinates (array of [lng, lat] or [x, y, z]) to local metre offsets.
 * Centres the alignment at [0, 0, 0].
 */
export function alignmentToLocal(coordinates) {
  if (!coordinates?.length) return [];

  const has3D = coordinates[0].length >= 3;

  // Detect if coords are geographic (lng/lat) or already metric
  const isGeo = Math.abs(coordinates[0][0]) <= 180 && Math.abs(coordinates[0][1]) <= 90;

  if (!isGeo) {
    // Already metric — just centre
    let cx = 0, cy = 0, cz = 0;
    for (const pt of coordinates) {
      cx += pt[0]; cy += pt[1]; cz += (pt[2] || 0);
    }
    cx /= coordinates.length;
    cy /= coordinates.length;
    cz /= coordinates.length;
    return coordinates.map((pt) => [pt[0] - cx, pt[2] != null ? pt[2] - cz : 0, pt[1] - cy]);
  }

  // Geographic — convert to metres
  let sumLng = 0, sumLat = 0, sumElev = 0;
  for (const pt of coordinates) {
    sumLng += pt[0];
    sumLat += pt[1];
    sumElev += (pt[2] || 0);
  }
  const cLng = sumLng / coordinates.length;
  const cLat = sumLat / coordinates.length;
  const cElev = sumElev / coordinates.length;
  const cosLat = Math.cos((cLat * Math.PI) / 180);
  const M = 111320;

  return coordinates.map((pt) => [
    (pt[0] - cLng) * M * cosLat,
    has3D ? (pt[2] || 0) - cElev : 0,
    (pt[1] - cLat) * M,
  ]);
}

/**
 * Generate a CylinderGeometry pipe segment between two 3D points.
 * @param {number[]} start - [x, y, z]
 * @param {number[]} end - [x, y, z]
 * @param {number} diameter_mm - pipe diameter in millimetres
 * @returns {{ geometry: THREE.CylinderGeometry, position: number[], quaternion: THREE.Quaternion }}
 */
export function generatePipeSegment(start, end, diameter_mm) {
  const radius = (diameter_mm / 1000) / 2;
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];
  const dz = end[2] - start[2];
  const length = Math.sqrt(dx * dx + dy * dy + dz * dz);

  const geo = new THREE.CylinderGeometry(radius, radius, length, 12, 1);

  // Position at midpoint
  const position = [
    (start[0] + end[0]) / 2,
    (start[1] + end[1]) / 2,
    (start[2] + end[2]) / 2,
  ];

  // Rotate cylinder (default Y-axis) to align with segment direction
  const direction = new THREE.Vector3(dx, dy, dz).normalize();
  const quaternion = new THREE.Quaternion();
  quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);

  return { geometry: geo, position, quaternion, length };
}

/**
 * Generate a vertical manhole shaft.
 * @param {number[]} position - [x, y, z] at ground level
 * @param {number} depth_m - depth of manhole below position
 * @returns {{ geometry: THREE.CylinderGeometry, position: number[] }}
 */
export function generateManhole(position, depth_m) {
  const radius = 0.6;
  const geo = new THREE.CylinderGeometry(radius, radius, depth_m, 16, 1);
  // Centre vertically: shaft goes from position.y down by depth_m
  const pos = [position[0], position[1] - depth_m / 2, position[2]];
  return { geometry: geo, position: pos };
}

/**
 * Generate a fitting geometry (elbow, tee, or reducer).
 * @param {number[]} position - [x, y, z]
 * @param {'elbow'|'tee'|'reducer'} type
 * @param {number[]} rotation - [rx, ry, rz] Euler angles
 * @returns {{ geometry: THREE.BufferGeometry, position: number[], rotation: number[] }}
 */
export function generateFitting(position, type, rotation) {
  let geo;
  switch (type) {
    case 'elbow':
      // Torus section for elbow
      geo = new THREE.TorusGeometry(0.3, 0.1, 8, 12, Math.PI / 2);
      break;
    case 'tee':
      // Cross-shaped: use a sphere as simplified representation
      geo = new THREE.SphereGeometry(0.2, 12, 8);
      break;
    case 'reducer':
      // Cone for reducer
      geo = new THREE.ConeGeometry(0.2, 0.4, 12);
      break;
    default:
      geo = new THREE.SphereGeometry(0.15, 8, 6);
  }
  return { geometry: geo, position, rotation: rotation || [0, 0, 0] };
}
