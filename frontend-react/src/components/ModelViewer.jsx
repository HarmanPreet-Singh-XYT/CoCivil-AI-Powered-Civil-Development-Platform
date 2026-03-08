import { useState, useRef, useMemo, useCallback, useEffect, Suspense } from 'react';
import { createPortal } from 'react-dom';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import {
  extractFootprint,
  shrinkPolygon,
  makeCircularFootprint,
  subdivideFootprintIntoUnits,
} from '../lib/buildingGeometry.js';
import {
  alignmentToLocal,
  generatePipeSegment,
  generateManhole,
  generateFitting,
} from '../lib/infrastructureGeometry.js';
import {
  generateBridgeDeck,
  generateGirder,
  generateAbutment,
  generatePier,
  generateBarrier,
} from '../lib/bridgeGeometry.js';
import BlueprintOverlay from './BlueprintOverlay.jsx';
import FloorPlanView from './FloorPlanView.jsx';
import FloorPlanEditor from './floorplan/FloorPlanEditor.jsx';
import {
  createBranch,
  listBranches,
  commitVersion,
  listVersions,
  getUploadPages,
} from '../api.js';
import '../ModelViewer.css';

const DEFAULT_PARAMS = {
  storeys: 10,
  podium_storeys: 0,
  height_m: 35,
  setback_m: 0,
  typology: 'midrise',
  footprint_coverage: 0.6,
  unit_width: null,
  tower_shape: null,
};

const FLOOR_H = 3.3;
const FLOOR_GAP = 0.2;
const GROUND_FLOOR_H = 4.5;

const COLORS = {
  podium: '#8a7553',
  retail: '#6b5b3a',
  floor_even: '#c8a55c',
  floor_odd: '#d4b87a',
  townhouse_a: '#c8a55c',
  townhouse_b: '#a08040',
  townhouse_c: '#b89850',
  tower: '#c8a55c',
};

const COMPLIANCE_BADGES = {
  as_of_right: { color: '#4a7c59', label: 'As-of-right' },
  needs_variance: { color: '#c8a55c', label: 'Minor variance' },
  needs_rezoning: { color: '#c44', label: 'Rezoning required' },
  blocked: { color: '#c44', label: 'Blocked' },
  unknown: { color: '#666', label: 'Unknown' },
};

// ─── Helpers ────────────────────────────────────────────────────────────────────

function makeShapeFromPoints(pts) {
  const shape = new THREE.Shape();
  shape.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) shape.lineTo(pts[i][0], pts[i][1]);
  shape.closePath();
  return shape;
}

function makeFloorSlab(shape, floorH, yOffset) {
  const geo = new THREE.ExtrudeGeometry(shape, { depth: floorH, bevelEnabled: false });
  geo.rotateX(-Math.PI / 2);
  geo.translate(0, yOffset, 0);
  return geo;
}

function scaleFootprint(footprint, coverage) {
  return footprint.map(([x, z]) => [x * coverage, z * coverage]);
}

// ─── Detail materials ───────────────────────────────────────────────────────────

const windowMaterial = new THREE.MeshPhysicalMaterial({
  color: '#1a3a5a',
  metalness: 0.9,
  roughness: 0.05,
  transmission: 0.3,
  transparent: true,
});

const railingMaterial = new THREE.MeshStandardMaterial({
  color: '#aaccee',
  transparent: true,
  opacity: 0.3,
  metalness: 0.5,
  roughness: 0.1,
});

const canopyMaterial = new THREE.MeshStandardMaterial({
  color: '#2a2a2a',
  metalness: 0.6,
  roughness: 0.3,
});

const edgeMaterial = new THREE.LineBasicMaterial({ color: '#333333' });

// ─── Detail geometry helpers ────────────────────────────────────────────────────

function getFacesFromFootprint(pts) {
  const faces = [];
  for (let i = 0; i < pts.length; i++) {
    const a = pts[i];
    const b = pts[(i + 1) % pts.length];
    faces.push({ start: a, end: b });
  }
  return faces;
}

function generateWindowsForFace(start, end, floorY, floorH, isStorefront = false) {
  const dx = end[0] - start[0];
  const dz = end[1] - start[1];
  const faceLen = Math.sqrt(dx * dx + dz * dz);
  if (faceLen < 2) return [];

  const windowW = isStorefront ? 2.0 : 1.2;
  const windowH = isStorefront ? 2.5 : 1.2;
  const mullion = 0.6;
  const spacing = windowW + mullion;
  const count = Math.max(1, Math.floor((faceLen - mullion) / spacing));
  const totalSpan = count * spacing - mullion;
  const offsetStart = (faceLen - totalSpan) / 2;

  const nx = -dz / faceLen;
  const nz = dx / faceLen;

  const results = [];
  for (let i = 0; i < count; i++) {
    const t = (offsetStart + i * spacing + windowW / 2) / faceLen;
    const cx = start[0] + dx * t + nx * 0.02;
    const cz = start[1] + dz * t + nz * 0.02;
    const cy = floorY + (isStorefront ? windowH / 2 + 0.5 : floorH / 2);
    const angle = Math.atan2(dx, dz);

    results.push({
      type: 'window',
      position: [cx, cy, cz],
      rotation: [0, angle, 0],
      size: [windowW, windowH, 0.08],
    });
  }
  return results;
}

function generateBalcony(start, end, floorY) {
  const dx = end[0] - start[0];
  const dz = end[1] - start[1];
  const faceLen = Math.sqrt(dx * dx + dz * dz);
  if (faceLen < 3) return [];

  const nx = -dz / faceLen;
  const nz = dx / faceLen;
  const depth = 1.2;
  const mx = (start[0] + end[0]) / 2 + nx * depth / 2;
  const mz = (start[1] + end[1]) / 2 + nz * depth / 2;
  const angle = Math.atan2(dx, dz);

  return [
    {
      type: 'balcony_slab',
      position: [mx, floorY + 0.05, mz],
      rotation: [0, angle, 0],
      size: [faceLen * 0.8, 0.15, depth],
    },
    {
      type: 'railing',
      position: [mx + nx * depth / 2, floorY + 0.5, mz + nz * depth / 2],
      rotation: [0, angle, 0],
      size: [faceLen * 0.8, 0.9, 0.05],
    },
  ];
}

function generateCanopy(footprintPts, groundFloorTop) {
  const faces = getFacesFromFootprint(footprintPts);
  const results = [];
  for (const { start, end } of faces) {
    const dx = end[0] - start[0];
    const dz = end[1] - start[1];
    const faceLen = Math.sqrt(dx * dx + dz * dz);
    if (faceLen < 3) continue;

    const nx = -dz / faceLen;
    const nz = dx / faceLen;
    const mx = (start[0] + end[0]) / 2 + nx * 0.5;
    const mz = (start[1] + end[1]) / 2 + nz * 0.5;
    const angle = Math.atan2(dx, dz);

    results.push({
      type: 'canopy',
      position: [mx, groundFloorTop - 0.15, mz],
      rotation: [0, angle, 0],
      size: [faceLen * 0.9, 0.1, 1.0],
    });
  }
  return results;
}

function generateRoofCap(footprintPts, topY) {
  const shape = makeShapeFromPoints(footprintPts);
  const geo = new THREE.ExtrudeGeometry(shape, { depth: 0.3, bevelEnabled: false });
  geo.rotateX(-Math.PI / 2);
  geo.translate(0, topY, 0);
  return { geometry: geo, color: '#555555', isRoof: true };
}

function generateEdges(slabGeo) {
  return new THREE.EdgesGeometry(slabGeo);
}

function buildDetails(footprintPts, pieces, opts = {}) {
  const {
    skipWindows = false,
    balconyFloors = null, // array of floor indices that get balconies, or null for none
    storefrontFloor = -1, // floor index for storefront treatment
    canopyFloor = -1,     // floor index whose top gets a canopy
  } = opts;

  const details = [];
  const faces = getFacesFromFootprint(footprintPts);

  // Edge lines for each floor slab
  for (const piece of pieces) {
    details.push({ type: 'edges', geometry: generateEdges(piece.geometry) });
  }

  if (skipWindows) return details;

  // Track cumulative Y for each piece
  let y = 0;
  for (let i = 0; i < pieces.length; i++) {
    const piece = pieces[i];
    // Compute floor height from geometry bounding box
    piece.geometry.computeBoundingBox();
    const bb = piece.geometry.boundingBox;
    const floorY = bb.min.y;
    const floorH = bb.max.y - bb.min.y;

    const isStorefront = i === storefrontFloor;

    // Windows on each face
    for (const { start, end } of faces) {
      const wins = generateWindowsForFace(start, end, floorY, floorH, isStorefront);
      details.push(...wins);
    }

    // Balconies
    if (balconyFloors && balconyFloors.includes(i)) {
      // Pick first two longest faces
      const sorted = [...faces].sort((a, b) => {
        const la = Math.hypot(a.end[0] - a.start[0], a.end[1] - a.start[1]);
        const lb = Math.hypot(b.end[0] - b.start[0], b.end[1] - b.start[1]);
        return lb - la;
      });
      for (let f = 0; f < Math.min(2, sorted.length); f++) {
        const balc = generateBalcony(sorted[f].start, sorted[f].end, floorY);
        details.push(...balc);
      }
    }
  }

  // Canopy
  if (canopyFloor >= 0 && canopyFloor < pieces.length) {
    pieces[canopyFloor].geometry.computeBoundingBox();
    const topY = pieces[canopyFloor].geometry.boundingBox.max.y;
    const canopies = generateCanopy(footprintPts, topY);
    details.push(...canopies);
  }

  // Roof cap
  if (pieces.length > 0) {
    const last = pieces[pieces.length - 1];
    last.geometry.computeBoundingBox();
    details.push(generateRoofCap(footprintPts, last.geometry.boundingBox.max.y));
  }

  return details;
}

// ─── Typology builders ──────────────────────────────────────────────────────────

function buildMidrise(footprint, p) {
  const fp = scaleFootprint(footprint, p.footprint_coverage ?? 0.6);
  const shape = makeShapeFromPoints(fp);
  const storeys = p.storeys || 6;
  const pieces = [];
  let y = 0;
  for (let i = 0; i < storeys; i++) {
    pieces.push({
      geometry: makeFloorSlab(shape, FLOOR_H, y),
      color: i % 2 === 0 ? COLORS.floor_even : COLORS.floor_odd,
    });
    y += FLOOR_H + FLOOR_GAP;
  }
  const balconyFloors = [];
  for (let i = 2; i < storeys; i += 2) balconyFloors.push(i);
  const details = buildDetails(fp, pieces, { balconyFloors });
  return { pieces, details };
}

function buildTowerOnPodium(footprint, p) {
  const fp = scaleFootprint(footprint, p.footprint_coverage ?? 0.45);
  const podiumShape = makeShapeFromPoints(fp);
  const podiumStoreys = p.podium_storeys || 3;
  const totalStoreys = p.storeys || 20;
  const towerStoreys = Math.max(0, totalStoreys - podiumStoreys);
  const pieces = [];

  let y = 0;
  for (let i = 0; i < podiumStoreys; i++) {
    const h = i === 0 ? GROUND_FLOOR_H : FLOOR_H;
    pieces.push({
      geometry: makeFloorSlab(podiumShape, h, y),
      color: i === 0 ? COLORS.retail : COLORS.podium,
    });
    y += h + FLOOR_GAP;
  }

  if (towerStoreys > 0) {
    const setback = p.setback_m || 3;
    const towerFP = shrinkPolygon(fp, setback);
    const towerShape = makeShapeFromPoints(towerFP);
    for (let i = 0; i < towerStoreys; i++) {
      pieces.push({
        geometry: makeFloorSlab(towerShape, FLOOR_H, y),
        color: i % 2 === 0 ? COLORS.floor_even : COLORS.floor_odd,
      });
      y += FLOOR_H + FLOOR_GAP;
    }
  }

  // Details: storefront on ground, canopy, balconies on tower floors
  const balconyFloors = [];
  for (let i = podiumStoreys + 1; i < pieces.length; i += 3) balconyFloors.push(i);
  const details = buildDetails(fp, pieces, {
    storefrontFloor: 0,
    canopyFloor: 0,
    balconyFloors,
  });
  return { pieces, details };
}

function buildPointTower(footprint, p) {
  const totalStoreys = p.storeys || 30;
  const pieces = [];
  let fp;

  if (p.tower_shape === 'circular') {
    const scaled = scaleFootprint(footprint, p.footprint_coverage ?? 0.45);
    let maxR = 0;
    for (const [x, z] of scaled) {
      const r = Math.sqrt(x * x + z * z);
      if (r > maxR) maxR = r;
    }
    fp = makeCircularFootprint(maxR * 0.5, 24);
  } else {
    const scaled = scaleFootprint(footprint, p.footprint_coverage ?? 0.45);
    fp = shrinkPolygon(scaled, 2);
  }

  const shape = makeShapeFromPoints(fp);
  let y = 0;
  for (let i = 0; i < totalStoreys; i++) {
    pieces.push({
      geometry: makeFloorSlab(shape, FLOOR_H, y),
      color: i % 2 === 0 ? COLORS.floor_even : COLORS.floor_odd,
    });
    y += FLOOR_H + FLOOR_GAP;
  }
  const balconyFloors = [];
  for (let i = 2; i < totalStoreys; i += 3) balconyFloors.push(i);
  const details = buildDetails(fp, pieces, { balconyFloors });
  return { pieces, details };
}

function buildTownhouse(footprint, p) {
  const fp = scaleFootprint(footprint, p.footprint_coverage ?? 0.55);
  const unitWidth = p.unit_width || 6;
  const storeys = p.storeys || 3;
  const units = subdivideFootprintIntoUnits(fp, unitWidth);
  const unitColors = [COLORS.townhouse_a, COLORS.townhouse_b, COLORS.townhouse_c];
  const pieces = [];

  for (const unit of units) {
    const shrunk = unit.points.map(([x, z], idx) => {
      if (idx === unit.points.length - 1) return [x + 0.1, z];
      const xAdj = unit.index === 0 ? x : x + 0.1;
      return [xAdj, z];
    });
    const shape = makeShapeFromPoints(shrunk);
    const color = unitColors[unit.index % unitColors.length];

    let y = 0;
    for (let f = 0; f < storeys; f++) {
      pieces.push({
        geometry: makeFloorSlab(shape, FLOOR_H, y),
        color,
      });
      y += FLOOR_H + FLOOR_GAP;
    }
  }
  // Townhouse: edges + roof cap only, no windows/balconies
  const details = [];
  for (const piece of pieces) {
    details.push({ type: 'edges', geometry: generateEdges(piece.geometry) });
  }
  if (pieces.length > 0) {
    const last = pieces[pieces.length - 1];
    last.geometry.computeBoundingBox();
    const fpAll = scaleFootprint(footprint, p.footprint_coverage ?? 0.55);
    details.push(generateRoofCap(fpAll, last.geometry.boundingBox.max.y));
  }
  return { pieces, details };
}

function buildSlab(footprint, p) {
  const fp = scaleFootprint(footprint, p.footprint_coverage ?? 0.6);
  const shape = makeShapeFromPoints(fp);
  const storeys = p.storeys || 10;
  const pieces = [];
  let y = 0;
  for (let i = 0; i < storeys; i++) {
    pieces.push({
      geometry: makeFloorSlab(shape, FLOOR_H, y),
      color: i % 2 === 0 ? COLORS.floor_even : COLORS.floor_odd,
    });
    y += FLOOR_H + FLOOR_GAP;
  }
  // Slab: windows + edges + roof, no balconies
  const details = buildDetails(fp, pieces);
  return { pieces, details };
}

function buildMixedUseMidrise(footprint, p) {
  const fp = scaleFootprint(footprint, p.footprint_coverage ?? 0.6);
  const shape = makeShapeFromPoints(fp);
  const storeys = p.storeys || 6;
  const pieces = [];
  let y = 0;
  for (let i = 0; i < storeys; i++) {
    const h = i === 0 ? GROUND_FLOOR_H : FLOOR_H;
    const color = i === 0 ? COLORS.retail : (i % 2 === 0 ? COLORS.floor_even : COLORS.floor_odd);
    pieces.push({
      geometry: makeFloorSlab(shape, h, y),
      color,
    });
    y += h + FLOOR_GAP;
  }
  const balconyFloors = [];
  for (let i = 2; i < storeys; i += 2) balconyFloors.push(i);
  const details = buildDetails(fp, pieces, {
    storefrontFloor: 0,
    canopyFloor: 0,
    balconyFloors,
  });
  return { pieces, details };
}

function buildRealBuilding(footprint, p) {
  const shape = makeShapeFromPoints(footprint);
  const totalH = p.height_m || 35;
  const geo = new THREE.ExtrudeGeometry(shape, { depth: totalH, bevelEnabled: false });
  geo.rotateX(-Math.PI / 2);
  const pieces = [{ geometry: geo, color: COLORS.tower }];
  const details = buildDetails(footprint, pieces, { skipWindows: true });
  return { pieces, details };
}

// ─── Infrastructure colors ──────────────────────────────────────────────────
const INFRA_COLORS = {
  water: '#2277bb',
  sanitary: '#886644',
  storm: '#44aa66',
  gas: '#ddaa22',
  deck: '#888888',
  girder: '#666666',
  abutment: '#aa9977',
  pier: '#999999',
  barrier: '#bbbbbb',
};

// ─── Infrastructure builders ────────────────────────────────────────────────

function buildPipelineNetwork(alignment, params) {
  const localPts = alignmentToLocal(alignment);
  if (localPts.length < 2) return { pieces: [], details: [] };

  const pieces = [];
  const details = [];
  const pipeType = params?.pipe_type || 'water';
  const diameter = params?.diameter_mm || 300;
  const color = INFRA_COLORS[pipeType] || INFRA_COLORS.water;
  const manholeSpacing = params?.manhole_spacing_m || 120;

  // Generate pipe segments between consecutive alignment points
  let accumulatedLength = 0;
  let lastManholeAt = 0;

  for (let i = 0; i < localPts.length - 1; i++) {
    const seg = generatePipeSegment(localPts[i], localPts[i + 1], diameter);
    pieces.push({
      geometry: seg.geometry,
      color,
      position: seg.position,
      quaternion: seg.quaternion,
      type: 'pipe',
    });

    // Place manholes at spacing intervals
    accumulatedLength += seg.length;
    if (accumulatedLength - lastManholeAt >= manholeSpacing || i === 0) {
      const mh = generateManhole(localPts[i], params?.manhole_depth_m || 2.5);
      pieces.push({
        geometry: mh.geometry,
        color: '#444444',
        position: mh.position,
        type: 'manhole',
      });
      lastManholeAt = accumulatedLength;
    }
  }

  // End manhole
  const lastPt = localPts[localPts.length - 1];
  const endMH = generateManhole(lastPt, params?.manhole_depth_m || 2.5);
  pieces.push({
    geometry: endMH.geometry,
    color: '#444444',
    position: endMH.position,
    type: 'manhole',
  });

  // Fittings at bends
  for (let i = 1; i < localPts.length - 1; i++) {
    const v1 = [localPts[i][0] - localPts[i - 1][0], localPts[i][1] - localPts[i - 1][1], localPts[i][2] - localPts[i - 1][2]];
    const v2 = [localPts[i + 1][0] - localPts[i][0], localPts[i + 1][1] - localPts[i][1], localPts[i + 1][2] - localPts[i][2]];
    const dot = v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2];
    const mag1 = Math.sqrt(v1[0] ** 2 + v1[1] ** 2 + v1[2] ** 2);
    const mag2 = Math.sqrt(v2[0] ** 2 + v2[1] ** 2 + v2[2] ** 2);
    const angle = mag1 > 0 && mag2 > 0 ? Math.acos(Math.min(1, dot / (mag1 * mag2))) : 0;

    if (angle > 0.1) {
      const fit = generateFitting(localPts[i], 'elbow', [0, 0, 0]);
      details.push({
        type: 'fitting',
        geometry: fit.geometry,
        position: fit.position,
        rotation: fit.rotation,
        color,
      });
    }
  }

  return { pieces, details };
}

function buildBridge(alignment, params) {
  const localPts = alignmentToLocal(alignment);
  const pieces = [];
  const details = [];

  // Compute total span and direction
  const first = localPts[0] || [0, 0, 0];
  const last = localPts[localPts.length - 1] || [20, 0, 0];
  const span = Math.sqrt(
    (last[0] - first[0]) ** 2 + (last[1] - first[1]) ** 2 + (last[2] - first[2]) ** 2
  ) || 20;

  const deckWidth = params?.deck_width_m || 12;
  const deckDepth = params?.deck_depth_m || 0.3;
  const girderDepth = params?.girder_depth_m || 1.2;
  const barrierHeight = params?.barrier_height_m || 1.1;
  const pierCount = params?.pier_count || Math.max(0, Math.floor(span / 25) - 1);
  const pierHeight = params?.pier_height_m || 8;

  const midX = (first[0] + last[0]) / 2;
  const midY = (first[1] + last[1]) / 2;
  const midZ = (first[2] + last[2]) / 2;

  // Direction angle for rotation
  const angle = Math.atan2(last[2] - first[2], last[0] - first[0]);

  // Deck
  const deck = generateBridgeDeck(span, deckWidth, deckDepth);
  pieces.push({
    geometry: deck.geometry,
    color: INFRA_COLORS.deck,
    position: [midX, midY, midZ],
    rotation: [0, angle, 0],
    type: 'deck',
  });

  // Girders (typically 4-6 across width)
  const girderCount = params?.girder_count || Math.max(2, Math.round(deckWidth / 2.5));
  const girderType = params?.girder_type || 'i_beam';
  for (let g = 0; g < girderCount; g++) {
    const transOffset = -deckWidth / 2 + (g + 0.5) * (deckWidth / girderCount);
    const gir = generateGirder(girderType, span, girderDepth, transOffset);
    pieces.push({
      geometry: gir.geometry,
      color: INFRA_COLORS.girder,
      position: [midX, midY - deckDepth / 2 - girderDepth, midZ + transOffset],
      rotation: [0, angle, 0],
      type: 'girder',
    });
  }

  // Abutments (at each end)
  const abutW = deckWidth + 1;
  const abutH = pierHeight;
  const abutD = 1.5;
  const abutStart = generateAbutment('gravity', first, { width: abutW, height: abutH, depth: abutD });
  pieces.push({
    geometry: abutStart.geometry,
    color: INFRA_COLORS.abutment,
    position: [first[0], first[1] - abutH / 2, first[2]],
    rotation: [0, angle, 0],
    type: 'abutment',
  });
  const abutEnd = generateAbutment('gravity', last, { width: abutW, height: abutH, depth: abutD });
  pieces.push({
    geometry: abutEnd.geometry,
    color: INFRA_COLORS.abutment,
    position: [last[0], last[1] - abutH / 2, last[2]],
    rotation: [0, angle, 0],
    type: 'abutment',
  });

  // Piers
  for (let p = 0; p < pierCount; p++) {
    const t = (p + 1) / (pierCount + 1);
    const px = first[0] + (last[0] - first[0]) * t;
    const py = first[1] + (last[1] - first[1]) * t;
    const pz = first[2] + (last[2] - first[2]) * t;
    const pier = generatePier(pierHeight, deckWidth * 0.6);
    pieces.push({
      geometry: pier.geometry,
      color: INFRA_COLORS.pier,
      position: [px, py - pierHeight / 2, pz],
      rotation: [0, angle, 0],
      type: 'pier',
    });
  }

  // Barriers (both sides)
  const bar = generateBarrier(span, barrierHeight, params?.barrier_type || 'jersey');
  for (const side of [-1, 1]) {
    const transOffset = side * (deckWidth / 2);
    pieces.push({
      geometry: bar.geometry.clone(),
      color: INFRA_COLORS.barrier,
      position: [midX, midY + deckDepth / 2 + barrierHeight / 2, midZ + transOffset],
      rotation: [0, angle, 0],
      type: 'barrier',
    });
  }

  return { pieces, details };
}

export const INFRASTRUCTURE_BUILDERS = {
  pipeline: buildPipelineNetwork,
  bridge: buildBridge,
};

const TYPOLOGY_BUILDERS = {
  midrise: buildMidrise,
  tower_on_podium: buildTowerOnPodium,
  point_tower: buildPointTower,
  townhouse: buildTownhouse,
  slab: buildSlab,
  mixed_use_midrise: buildMixedUseMidrise,
  real_building: buildRealBuilding,
};

// ─── Building mesh ─────────────────────────────────────────────────────────────

function BuildingMesh({ parcelGeoJSON, params }) {
  const p = params || DEFAULT_PARAMS;

  const buildResult = useMemo(() => {
    const footprint = extractFootprint(parcelGeoJSON);
    const isRealBuilding = p.typology === 'real_building' || (p.footprint_coverage ?? 0) >= 1.0;
    const typology = isRealBuilding ? 'real_building' : (p.typology || 'midrise');
    const builder = TYPOLOGY_BUILDERS[typology] || TYPOLOGY_BUILDERS.midrise;
    const result = builder(footprint, p);
    // Backward compat: if builder returns an array, wrap it
    if (Array.isArray(result)) return { pieces: result, details: [] };
    return result;
  }, [parcelGeoJSON, p]);

  const { pieces, details } = buildResult;

  return (
    <group>
      {pieces.map((piece, i) => (
        <mesh key={i} geometry={piece.geometry} castShadow receiveShadow>
          <meshStandardMaterial color={piece.color} roughness={0.6} metalness={0.1} />
        </mesh>
      ))}
      {details.map((d, i) => {
        if (d.type === 'edges') {
          return (
            <lineSegments key={`e${i}`} geometry={d.geometry}>
              <lineBasicMaterial color="#333333" />
            </lineSegments>
          );
        }
        if (d.type === 'window') {
          return (
            <mesh key={`w${i}`} position={d.position} rotation={d.rotation}>
              <boxGeometry args={d.size} />
              <meshPhysicalMaterial
                color="#1a3a5a"
                metalness={0.9}
                roughness={0.05}
                transmission={0.3}
                transparent
              />
            </mesh>
          );
        }
        if (d.type === 'balcony_slab') {
          return (
            <mesh key={`bs${i}`} position={d.position} rotation={d.rotation} castShadow>
              <boxGeometry args={d.size} />
              <meshStandardMaterial color="#d8c48a" roughness={0.5} metalness={0.1} />
            </mesh>
          );
        }
        if (d.type === 'railing') {
          return (
            <mesh key={`r${i}`} position={d.position} rotation={d.rotation}>
              <boxGeometry args={d.size} />
              <meshStandardMaterial color="#aaccee" transparent opacity={0.3} metalness={0.5} roughness={0.1} />
            </mesh>
          );
        }
        if (d.type === 'canopy') {
          return (
            <mesh key={`c${i}`} position={d.position} rotation={d.rotation} castShadow>
              <boxGeometry args={d.size} />
              <meshStandardMaterial color="#2a2a2a" metalness={0.6} roughness={0.3} />
            </mesh>
          );
        }
        if (d.isRoof) {
          return (
            <mesh key={`rf${i}`} geometry={d.geometry} castShadow>
              <meshStandardMaterial color={d.color} roughness={0.4} metalness={0.2} />
            </mesh>
          );
        }
        return null;
      })}
    </group>
  );
}

// ─── Ground plane ──────────────────────────────────────────────────────────────

function Ground() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]} receiveShadow>
      <planeGeometry args={[600, 600]} />
      <meshStandardMaterial color="#1a1a1a" roughness={1} />
    </mesh>
  );
}

// ─── Scene wrapper ─────────────────────────────────────────────────────────────

function Scene({
  parcelGeoJSON,
  params,
  controlsRef,
  viewMode,
  floorPlans,
  blueprintPages,
  activeFloor,
  selectedRoom,
  onRoomClick,
}) {
  return (
    <>
      <ambientLight intensity={0.4} />
      <directionalLight
        position={[60, 120, 60]}
        intensity={1.2}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      <directionalLight position={[-40, 60, -40]} intensity={0.4} />

      <OrbitControls
        ref={controlsRef}
        enablePan={false}
        minDistance={10}
        maxDistance={400}
        maxPolarAngle={Math.PI / 2 - 0.02}
      />

      <Suspense fallback={null}>
        {viewMode === 'massing' && (
          <BuildingMesh parcelGeoJSON={parcelGeoJSON} params={params} />
        )}
        {viewMode === 'interior' && floorPlans && (
          <FloorPlanView
            floorPlans={floorPlans}
            activeFloor={activeFloor}
            selectedRoom={selectedRoom}
            onRoomClick={onRoomClick}
          />
        )}
        {viewMode === 'blueprint' && blueprintPages?.length > 0 && (
          <BlueprintOverlay
            pages={blueprintPages}
            activeFloor={activeFloor}
          />
        )}
      </Suspense>

      <Ground />
    </>
  );
}

// ─── Compliance badge ──────────────────────────────────────────────────────────

function ComplianceBadge({ status }) {
  const badge = COMPLIANCE_BADGES[status] || COMPLIANCE_BADGES.unknown;
  return (
    <span className="compliance-badge" style={{ color: badge.color }}>
      <span className="compliance-dot" style={{ backgroundColor: badge.color }} />
      {badge.label}
    </span>
  );
}

// ─── Commit Modal ──────────────────────────────────────────────────────────────

function CommitModal({ onCommit, onCancel, changeSummary }) {
  const [message, setMessage] = useState('Design update');

  return (
    <div className="commit-modal-overlay" onClick={onCancel}>
      <div className="commit-modal" onClick={(e) => e.stopPropagation()}>
        <h3>Commit Design Changes</h3>
        <label>
          Message:
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Describe your changes..."
            autoFocus
          />
        </label>
        {changeSummary && (
          <div className="commit-changes">
            <span className="commit-changes-label">Changes:</span>
            {changeSummary.split('; ').map((c, i) => (
              <div key={i} className="commit-change-item">{c}</div>
            ))}
          </div>
        )}
        <div className="commit-modal-actions">
          <button className="model-ctrl-btn" onClick={onCancel}>Cancel</button>
          <button
            className="model-ctrl-btn commit-btn"
            onClick={() => onCommit(message || 'Design update')}
            disabled={!message.trim()}
          >
            Commit
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── History Panel ─────────────────────────────────────────────────────────────

function HistoryPanel({ versions, branches, currentBranch, onSelectVersion, onSwitchBranch, onClose }) {
  return (
    <div className="history-panel">
      <div className="history-header">
        <span>Version History — {currentBranch?.name || 'main'}</span>
        <button className="history-close" onClick={onClose}>×</button>
      </div>
      <div className="history-list">
        {versions.map((v) => {
          const badge = COMPLIANCE_BADGES[v.compliance_status] || COMPLIANCE_BADGES.unknown;
          return (
            <div
              key={v.id}
              className="history-item"
              onClick={() => onSelectVersion(v)}
            >
              <span className="history-version">v{v.version_number}</span>
              <span className="history-message">{v.message}</span>
              <span className="compliance-dot" style={{ backgroundColor: badge.color }} title={badge.label} />
            </div>
          );
        })}
      </div>
      {branches.length > 1 && (
        <div className="history-branches">
          {branches.filter((b) => b.id !== currentBranch?.id).map((b) => (
            <button key={b.id} className="history-branch-btn" onClick={() => onSwitchBranch(b)}>
              Branch: {b.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Room info panel ───────────────────────────────────────────────────────────

function RoomInfoPanel({ room, onClose }) {
  if (!room) return null;
  return (
    <div className="room-info-panel">
      <div className="room-info-header">
        <span>{room.name}</span>
        <button onClick={onClose}>×</button>
      </div>
      <div className="room-info-body">
        <div><span className="room-info-label">Type:</span> {room.type}</div>
        <div><span className="room-info-label">Area:</span> {room.area_m2?.toFixed(1)} m²</div>
        <div><span className="room-info-label">Floor:</span> {room.floor}</div>
      </div>
    </div>
  );
}

// ─── Main modal ────────────────────────────────────────────────────────────────

export default function ModelViewer({
  isOpen, onClose, parcelGeoJSON, modelParams, isPanelOpen, isSidebarCollapsed, isChatExpanded,
  floorPlans, blueprintPages: blueprintPagesProp, projectId, parcelId,
}) {
  const controlsRef = useRef(null);
  const params = modelParams || DEFAULT_PARAMS;

  // View state
  const [viewMode, setViewMode] = useState('massing');
  const [activeFloor, setActiveFloor] = useState(null);
  const [selectedRoom, setSelectedRoom] = useState(null);

  // Version control state
  const [currentBranch, setCurrentBranch] = useState(null);
  const [branches, setBranches] = useState([]);
  const [versions, setVersions] = useState([]);
  const [currentVersion, setCurrentVersion] = useState(null);
  const [isDirty, setIsDirty] = useState(false);
  const [showCommitModal, setShowCommitModal] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showBranchInput, setShowBranchInput] = useState(false);
  const [branchName, setBranchName] = useState('');

  // Track uncommitted changes
  const [uncommittedFloorPlans, setUncommittedFloorPlans] = useState(null);
  const [uncommittedModelParams, setUncommittedModelParams] = useState(null);
  const [blueprintPages, setBlueprintPages] = useState(blueprintPagesProp || []);

  const embeddedBlueprintPages = useMemo(() => {
    if (blueprintPagesProp?.length) return blueprintPagesProp;
    if (floorPlans?.blueprint_pages?.length) return floorPlans.blueprint_pages;
    if (floorPlans?.pages?.length) return floorPlans.pages;
    return [];
  }, [blueprintPagesProp, floorPlans]);

  // Load branches when projectId changes
  useEffect(() => {
    if (!projectId || !isOpen) return;
    listBranches(projectId).then(async (data) => {
      if (data?.length > 0) {
        setBranches(data);
        if (!currentBranch) setCurrentBranch(data[0]);
      } else {
        // Auto-create a "main" branch so commits work immediately
        try {
          const branch = await createBranch(projectId, 'main', null);
          setBranches([branch]);
          setCurrentBranch(branch);
        } catch (e) {
          console.error('Failed to auto-create main branch:', e);
        }
      }
    }).catch(() => {});
  }, [projectId, isOpen]);

  useEffect(() => {
    if (!isOpen) return undefined;
    if (embeddedBlueprintPages.length > 0) {
      setBlueprintPages(embeddedBlueprintPages);
      return undefined;
    }
    if (!projectId) {
      setBlueprintPages([]);
      return undefined;
    }

    let isCancelled = false;
    getUploadPages(projectId)
      .then((pages) => {
        if (!isCancelled) setBlueprintPages(pages || []);
      })
      .catch(() => {
        if (!isCancelled) setBlueprintPages([]);
      });

    return () => {
      isCancelled = true;
    };
  }, [embeddedBlueprintPages, isOpen, projectId]);

  // Load versions when branch changes
  useEffect(() => {
    if (!currentBranch) return;
    listVersions(currentBranch.id).then((data) => {
      setVersions(data || []);
      if (data?.length > 0) {
        setCurrentVersion(data[0]);
      }
    }).catch(() => {});
  }, [currentBranch]);

  // Detect dirty state
  useEffect(() => {
    if (!currentVersion) {
      // No version yet — treat any existing params/plans as uncommitted
      const hasContent = modelParams || floorPlans;
      setIsDirty(!!hasContent);
      if (modelParams) setUncommittedModelParams(modelParams);
      if (floorPlans) setUncommittedFloorPlans(floorPlans);
      return;
    }
    const paramsChanged = JSON.stringify(modelParams) !== JSON.stringify(currentVersion.model_params);
    const plansChanged = floorPlans && JSON.stringify(floorPlans) !== JSON.stringify(currentVersion.floor_plans);
    setIsDirty(paramsChanged || plansChanged);
    if (paramsChanged) setUncommittedModelParams(modelParams);
    if (plansChanged) setUncommittedFloorPlans(floorPlans);
  }, [modelParams, floorPlans, currentVersion]);

  const handleCommit = useCallback(async (message) => {
    if (!currentBranch) return;
    try {
      const result = await commitVersion(currentBranch.id, {
        floorPlans: floorPlans || uncommittedFloorPlans,
        modelParams: modelParams || uncommittedModelParams,
        message,
        parcelId,
      });
      setCurrentVersion(result);
      setVersions((prev) => [result, ...prev]);
      setIsDirty(false);
      setShowCommitModal(false);
      setUncommittedFloorPlans(null);
      setUncommittedModelParams(null);
    } catch (err) {
      console.error('Commit failed:', err);
      alert('Commit failed — please try again.');
    }
  }, [currentBranch, floorPlans, modelParams, parcelId, uncommittedFloorPlans, uncommittedModelParams]);

  const handleFloorPlansChange = useCallback((newPlans) => {
    setUncommittedFloorPlans(newPlans);
    setIsDirty(true);
  }, []);

  const handleDiscard = useCallback(() => {
    if (!currentVersion) return;
    if (!window.confirm('Discard all uncommitted changes?')) return;
    setIsDirty(false);
    setUncommittedFloorPlans(null);
    setUncommittedModelParams(null);
  }, [currentVersion]);

  const handleCreateBranch = useCallback(async () => {
    if (!projectId || !branchName.trim()) return;
    try {
      const branch = await createBranch(projectId, branchName.trim(), currentVersion?.id);
      setBranches((prev) => [...prev, branch]);
      setCurrentBranch(branch);
      setBranchName('');
      setShowBranchInput(false);
    } catch (err) {
      console.error('Branch creation failed:', err);
    }
  }, [projectId, branchName, currentVersion]);

  const handleSelectVersion = useCallback((version) => {
    setCurrentVersion(version);
    setShowHistory(false);
  }, []);

  const handleSwitchBranch = useCallback((branch) => {
    setCurrentBranch(branch);
    setShowHistory(false);
  }, []);

  // Change summary for commit modal
  const changeSummary = useMemo(() => {
    if (!currentVersion || !modelParams) return null;
    const oldP = currentVersion.model_params || {};
    const changes = [];
    for (const key of ['height_m', 'storeys', 'footprint_coverage', 'typology', 'setback_m']) {
      if (oldP[key] !== modelParams[key] && modelParams[key] != null) {
        const label = key.replace(/_/g, ' ');
        changes.push(`${label}: ${oldP[key] ?? '–'} → ${modelParams[key]}`);
      }
    }
    return changes.length > 0 ? changes.join('; ') : null;
  }, [currentVersion, modelParams]);

  const hasFloorPlans = floorPlans?.floor_plans?.length > 0;
  const hasBlueprintPages = blueprintPages.length > 0;
  const selectableFloors = useMemo(() => {
    if (floorPlans?.floor_plans?.length) {
      return floorPlans.floor_plans.map((fp) => fp.floor_number);
    }
    if (blueprintPages.length > 0) {
      return blueprintPages.map((_, idx) => idx + 1);
    }
    return [];
  }, [blueprintPages, floorPlans]);

  useEffect(() => {
    if (viewMode === 'interior' && !hasFloorPlans) {
      setViewMode(hasBlueprintPages ? 'blueprint' : 'massing');
      setSelectedRoom(null);
    }
    if (viewMode === 'blueprint' && !hasBlueprintPages) {
      setViewMode(hasFloorPlans ? 'interior' : 'massing');
    }
    if (viewMode === 'floorplan' && !hasFloorPlans) {
      setViewMode('massing');
    }
  }, [hasBlueprintPages, hasFloorPlans, viewMode]);

  if (!isOpen) return null;

  const totalH = Math.round(params.height_m || 0);
  const storeys = params.storeys || 0;
  const warnings = params.warnings || [];

  const closeBtn = createPortal(
    <button
      className="model-close-btn"
      onPointerDown={(e) => { e.stopPropagation(); e.preventDefault(); onClose(); }}
      aria-label="Close model"
      style={{
        position: 'fixed',
        top: 12,
        right: (isPanelOpen ? 380 : 0) + 16,
        zIndex: 99999,
        transition: 'right 0.3s ease',
      }}
    >✕</button>,
    document.body
  );

  const sidebarW = isSidebarCollapsed ? 52 : 160;
  const panelW = isPanelOpen ? 380 : 0;
  const chatH = isChatExpanded ? 328 : 48;

  return (
    <>
      {closeBtn}
      <div className="model-overlay" />
      <div
        className="model-canvas-area"
        style={{
          position: 'fixed',
          top: viewMode === 'floorplan' ? 68 : 0,
          left: sidebarW,
          right: panelW,
          bottom: chatH,
          zIndex: 6,
          transition: 'left 0.3s ease, right 0.3s ease, bottom 0.3s ease',
        }}
      >
        {viewMode === 'floorplan' ? (
          <FloorPlanEditor
            floorPlans={uncommittedFloorPlans || floorPlans}
            activeFloor={activeFloor}
            onFloorPlansChange={handleFloorPlansChange}
            parcelId={parcelId}
          />
        ) : (
          <Canvas
            camera={{ position: [0, 40, 80], fov: 45 }}
            shadows
            style={{ width: '100%', height: '100%', background: 'transparent' }}
            eventPrefix="client"
          >
            <Scene
              parcelGeoJSON={parcelGeoJSON}
              params={params}
              controlsRef={controlsRef}
              viewMode={viewMode}
              floorPlans={uncommittedFloorPlans || floorPlans}
              blueprintPages={blueprintPages}
              activeFloor={activeFloor}
              selectedRoom={selectedRoom}
              onRoomClick={setSelectedRoom}
            />
          </Canvas>
        )}

        {/* Room info panel */}
        <RoomInfoPanel room={selectedRoom} onClose={() => setSelectedRoom(null)} />

        {/* Commit modal */}
        {showCommitModal && (
          <CommitModal
            onCommit={handleCommit}
            onCancel={() => setShowCommitModal(false)}
            changeSummary={changeSummary}
          />
        )}

        {/* History panel */}
        {showHistory && (
          <HistoryPanel
            versions={versions}
            branches={branches}
            currentBranch={currentBranch}
            onSelectVersion={handleSelectVersion}
            onSwitchBranch={handleSwitchBranch}
            onClose={() => setShowHistory(false)}
          />
        )}
      </div>

      {/* Controls bar */}
      <div
        className="model-controls"
        style={{
          position: 'fixed',
          left: sidebarW,
          right: panelW,
          bottom: chatH,
          zIndex: 7,
          transition: 'left 0.3s ease, right 0.3s ease, bottom 0.3s ease',
          flexDirection: 'column',
          gap: 0,
        }}
      >
        {/* Version control bar */}
        {projectId && (
          <div className="version-control-bar">
            {/* Branch selector */}
            <select
              className="branch-selector"
              value={currentBranch?.id || ''}
              onChange={(e) => {
                const b = branches.find((br) => br.id === e.target.value);
                if (b) setCurrentBranch(b);
              }}
            >
              {branches.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>

            {/* Current version info */}
            {currentVersion && (
              <span className="version-info">
                v{currentVersion.version_number} "{currentVersion.message}"
              </span>
            )}

            {/* Compliance badge */}
            {currentVersion && <ComplianceBadge status={currentVersion.compliance_status} />}

            {/* Dirty indicator */}
            {isDirty && <span className="dirty-indicator">Modified</span>}

            {/* Actions */}
            <div className="version-actions">
              {isDirty && (
                <>
                  <button className="model-ctrl-btn commit-btn" onClick={() => setShowCommitModal(true)}>
                    Commit
                  </button>
                  <button className="model-ctrl-btn" onClick={handleDiscard}>
                    Discard
                  </button>
                </>
              )}

              {showBranchInput ? (
                <span className="branch-input-group">
                  <input
                    type="text"
                    className="branch-name-input"
                    value={branchName}
                    onChange={(e) => setBranchName(e.target.value)}
                    placeholder="Branch name"
                    onKeyDown={(e) => e.key === 'Enter' && handleCreateBranch()}
                  />
                  <button className="model-ctrl-btn" onClick={handleCreateBranch}>Create</button>
                  <button className="model-ctrl-btn" onClick={() => setShowBranchInput(false)}>×</button>
                </span>
              ) : (
                <button className="model-ctrl-btn" onClick={() => setShowBranchInput(true)}>
                  New Branch
                </button>
              )}

              <button
                className="model-ctrl-btn"
                onClick={() => setShowHistory(!showHistory)}
              >
                History {showHistory ? '▴' : '▾'}
              </button>
            </div>
          </div>
        )}

        {/* View mode + floor selector + existing controls */}
        <div className="model-controls-row">
          {/* View mode toggles */}
          <div className="view-mode-toggle">
            {[
              { key: 'massing', disabled: false, title: '' },
              { key: 'interior', disabled: !hasFloorPlans, title: 'Upload a DXF to view interior' },
              { key: 'floorplan', disabled: !hasFloorPlans, title: 'Edit floor plan (2D)' },
            ].map((mode) => (
              <button
                key={mode.key}
                className={`model-ctrl-btn ${viewMode === mode.key ? 'active' : ''}`}
                onClick={() => {
                  setViewMode(mode.key);
                  if (mode.key !== 'interior') setSelectedRoom(null);
                }}
                disabled={mode.disabled}
                title={mode.disabled ? mode.title : ''}
              >
                {mode.key.charAt(0).toUpperCase() + mode.key.slice(1)}
              </button>
            ))}
          </div>

          {/* Floor selector */}
          {selectableFloors.length > 0 && viewMode !== 'massing' && (
            <div className="floor-selector">
              <button
                className={`model-ctrl-btn floor-btn ${activeFloor === null ? 'active' : ''}`}
                onClick={() => setActiveFloor(null)}
              >
                All
              </button>
              {selectableFloors.map((floorNumber) => (
                <button
                  key={floorNumber}
                  className={`model-ctrl-btn floor-btn ${activeFloor === floorNumber ? 'active' : ''}`}
                  onClick={() => setActiveFloor(floorNumber)}
                >
                  F{floorNumber}
                </button>
              ))}
            </div>
          )}

          {/* Reset + info */}
          <button
            className="model-ctrl-btn"
            onClick={() => {
              if (controlsRef.current) {
                controlsRef.current.object.position.set(0, 40, 80);
                controlsRef.current.target.set(0, 0, 0);
                controlsRef.current.update();
              }
            }}
            title="Reset camera"
          >
            ↺ Reset
          </button>
          <span className="model-info">
            {storeys} storeys · {totalH}m
            {params.typology ? ` · ${params.typology.replace(/_/g, ' ')}` : ''}
            {warnings.length > 0 && (
              <span className="model-warnings" title={warnings.join('\n')}>
                {' · ⚠ '}{warnings.length} zone limit{warnings.length > 1 ? 's' : ''} applied
              </span>
            )}
          </span>
        </div>
      </div>
    </>
  );
}
