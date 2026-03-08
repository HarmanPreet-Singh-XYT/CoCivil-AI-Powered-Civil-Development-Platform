/**
 * Bridge geometry utilities for 3D visualization.
 * Generates Three.js geometries for bridge components: deck, girders, abutments, piers, barriers.
 */
import * as THREE from 'three';

/**
 * Generate a bridge deck (simple slab).
 * @param {number} span - length along bridge axis (m)
 * @param {number} width - transverse width (m)
 * @param {number} depth - structural depth / thickness (m)
 * @returns {{ geometry: THREE.BoxGeometry, size: number[] }}
 */
export function generateBridgeDeck(span, width, depth) {
  const geo = new THREE.BoxGeometry(span, depth, width);
  return { geometry: geo, size: [span, depth, width] };
}

/**
 * Generate an I-beam girder via ExtrudeGeometry.
 * @param {'i_beam'|'box'|'concrete'} type - girder cross-section type
 * @param {number} span - length along bridge axis (m)
 * @param {number} depth - girder depth (m)
 * @param {number} offset - transverse offset from centreline (m)
 * @returns {{ geometry: THREE.ExtrudeGeometry, offset: number }}
 */
export function generateGirder(type, span, depth, offset) {
  const flangeW = 0.3;
  const flangeH = 0.04;
  const webW = 0.02;

  let shape;
  if (type === 'box') {
    // Box girder — hollow rectangle
    const outerW = 0.5;
    shape = new THREE.Shape();
    shape.moveTo(-outerW / 2, 0);
    shape.lineTo(outerW / 2, 0);
    shape.lineTo(outerW / 2, depth);
    shape.lineTo(-outerW / 2, depth);
    shape.closePath();
    // Cut-out hole
    const wall = 0.04;
    const hole = new THREE.Path();
    hole.moveTo(-outerW / 2 + wall, wall);
    hole.lineTo(outerW / 2 - wall, wall);
    hole.lineTo(outerW / 2 - wall, depth - wall);
    hole.lineTo(-outerW / 2 + wall, depth - wall);
    hole.closePath();
    shape.holes.push(hole);
  } else {
    // I-beam (default for i_beam and concrete)
    shape = new THREE.Shape();
    // Bottom flange
    shape.moveTo(-flangeW / 2, 0);
    shape.lineTo(flangeW / 2, 0);
    shape.lineTo(flangeW / 2, flangeH);
    // Web right side
    shape.lineTo(webW / 2, flangeH);
    shape.lineTo(webW / 2, depth - flangeH);
    // Top flange
    shape.lineTo(flangeW / 2, depth - flangeH);
    shape.lineTo(flangeW / 2, depth);
    shape.lineTo(-flangeW / 2, depth);
    shape.lineTo(-flangeW / 2, depth - flangeH);
    // Web left side
    shape.lineTo(-webW / 2, depth - flangeH);
    shape.lineTo(-webW / 2, flangeH);
    shape.lineTo(-flangeW / 2, flangeH);
    shape.closePath();
  }

  const geo = new THREE.ExtrudeGeometry(shape, {
    depth: span,
    bevelEnabled: false,
  });
  // Rotate so extrusion runs along X-axis (span direction)
  geo.rotateY(Math.PI / 2);
  // Translate to centre along span
  geo.translate(-span / 2, 0, 0);

  return { geometry: geo, offset };
}

/**
 * Generate an abutment (end support).
 * @param {'gravity'|'cantilever'|'spill_through'} type
 * @param {number[]} position - [x, y, z]
 * @param {{ width: number, height: number, depth: number }} params
 * @returns {{ geometry: THREE.BoxGeometry, position: number[], size: number[] }}
 */
export function generateAbutment(type, position, params) {
  const w = params?.width || 2;
  const h = params?.height || 4;
  const d = params?.depth || 1.5;
  const geo = new THREE.BoxGeometry(d, h, w);
  return { geometry: geo, position, size: [d, h, w] };
}

/**
 * Generate a pier (intermediate support column).
 * @param {number} height - pier height (m)
 * @param {number} width - pier cap width (m)
 * @returns {{ geometry: THREE.BoxGeometry, size: number[] }}
 */
export function generatePier(height, width) {
  const columnW = 0.8;
  const geo = new THREE.BoxGeometry(columnW, height, width);
  return { geometry: geo, size: [columnW, height, width] };
}

/**
 * Generate a barrier / railing along bridge edge.
 * @param {number} length - barrier length (m)
 * @param {number} height - barrier height (m)
 * @param {'jersey'|'railing'|'parapet'} type
 * @returns {{ geometry: THREE.BoxGeometry, size: number[] }}
 */
export function generateBarrier(length, height, type) {
  const thickness = type === 'jersey' ? 0.4 : 0.15;
  const geo = new THREE.BoxGeometry(length, height, thickness);
  return { geometry: geo, size: [length, height, thickness] };
}
