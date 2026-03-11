export const SNAP_GRID = 0.05; // 5cm
export const SNAP_ENDPOINT_THRESHOLD = 0.1; // 10cm

export function distanceBetweenPoints(p1, p2) {
  const dx = p2[0] - p1[0];
  const dy = p2[1] - p1[1];
  return Math.sqrt(dx * dx + dy * dy);
}

export function wallLength(wall) {
  return distanceBetweenPoints(wall.start, wall.end);
}

export function snapToGrid(point) {
  return [
    Math.round(point[0] / SNAP_GRID) * SNAP_GRID,
    Math.round(point[1] / SNAP_GRID) * SNAP_GRID,
  ];
}

export function snapToEndpoint(point, walls) {
  let closest = null;
  let minDist = SNAP_ENDPOINT_THRESHOLD;

  for (const wall of walls) {
    for (const ep of [wall.start, wall.end]) {
      const d = distanceBetweenPoints(point, ep);
      if (d < minDist) {
        minDist = d;
        closest = ep;
      }
    }
  }

  return closest || snapToGrid(point);
}

export function wallToRect(wall) {
  const dx = wall.end[0] - wall.start[0];
  const dy = wall.end[1] - wall.start[1];
  const length = Math.sqrt(dx * dx + dy * dy);
  const angle = Math.atan2(dy, dx);
  const cx = (wall.start[0] + wall.end[0]) / 2;
  const cy = (wall.start[1] + wall.end[1]) / 2;
  const thickness = wall.thickness_m || 0.2;

  return { cx, cy, length, angle, thickness };
}

export function recalculateRoomArea(polygon) {
  if (!polygon || polygon.length < 3) return 0;
  // Shoelace formula
  let area = 0;
  const n = polygon.length;
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    area += polygon[i][0] * polygon[j][1];
    area -= polygon[j][0] * polygon[i][1];
  }
  return Math.abs(area) / 2;
}

export function computeMinDimension(polygon) {
  if (!polygon || polygon.length < 2) return 0;

  // Axis-aligned bounding box min dimension
  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;
  for (const [x, y] of polygon) {
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }

  return Math.min(maxX - minX, maxY - minY);
}

export function pointInPolygon(point, polygon) {
  const [px, py] = point;
  let inside = false;
  const n = polygon.length;

  for (let i = 0, j = n - 1; i < n; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    const intersect =
      yi > py !== yj > py && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }

  return inside;
}

export function updateRoomsAfterWallEdit(rooms, oldPoint, newPoint) {
  if (!rooms) return rooms;

  return rooms.map((room) => {
    if (!room.polygon) return room;

    const updated = room.polygon.map((pt) => {
      if (Math.abs(pt[0] - oldPoint[0]) < 0.01 && Math.abs(pt[1] - oldPoint[1]) < 0.01) {
        return [newPoint[0], newPoint[1]];
      }
      return pt;
    });

    return {
      ...room,
      polygon: updated,
      area_sqm: recalculateRoomArea(updated),
    };
  });
}

// Generate a rectangular room and its 4 bounding walls
export function generateRoomAndWalls(x, y, width, height, type, generateId) {
  // Snapped coordinates
  const sx = Math.round(x / SNAP_GRID) * SNAP_GRID;
  const sy = Math.round(y / SNAP_GRID) * SNAP_GRID;
  const sw = Math.max(SNAP_GRID, Math.round(width / SNAP_GRID) * SNAP_GRID);
  const sh = Math.max(SNAP_GRID, Math.round(height / SNAP_GRID) * SNAP_GRID);

  const polygon = [
    [sx, sy],
    [sx + sw, sy],
    [sx + sw, sy + sh],
    [sx, sy + sh],
  ];

  const roomId = generateId('r');
  const room = {
    id: roomId,
    room_type: type || 'other',
    polygon,
    area_sqm: recalculateRoomArea(polygon),
  };

  const walls = [
    { start: [sx, sy], end: [sx + sw, sy] },            // Top
    { start: [sx + sw, sy], end: [sx + sw, sy + sh] },  // Right
    { start: [sx + sw, sy + sh], end: [sx, sy + sh] },  // Bottom
    { start: [sx, sy + sh], end: [sx, sy] },            // Left
  ].map((w) => ({
    id: generateId('w'),
    start: w.start,
    end: w.end,
    type: 'interior',
    load_bearing: 'unknown',
    thickness_m: 0.15,
  }));

  return { room, walls };
}

// Check if two line segments (walls) are identical or fully overlapping
function linesOverlap(a1, a2, b1, b2) {
  const tol = 0.01;
  const match = (p1, p2) => Math.abs(p1[0] - p2[0]) < tol && Math.abs(p1[1] - p2[1]) < tol;
  
  if ((match(a1, b1) && match(a2, b2)) || (match(a1, b2) && match(a2, b1))) {
    return true; // Exact match (reversed or not)
  }
  
  // Future enhancement: Handle partial overlaps if blocks are offset
  return false;
}

// Merge overlapping walls to prevent Z-fighting and duplicate topology
export function mergeOverlappingWalls(existingWalls, newWalls) {
  const resultingWalls = [...existingWalls];
  const wallsToAdd = [];

  for (const newWall of newWalls) {
    let isDuplicate = false;
    for (let i = 0; i < resultingWalls.length; i++) {
      const exWall = resultingWalls[i];
      if (linesOverlap(newWall.start, newWall.end, exWall.start, exWall.end)) {
        // They overlap, so we turn the existing wall into a definitive 'interior' wall 
        // and discard the new overlapping segment
        resultingWalls[i] = {
          ...exWall,
          type: 'interior'
        };
        isDuplicate = true;
        break;
      }
    }
    if (!isDuplicate) {
      wallsToAdd.push(newWall);
    }
  }

  return [...resultingWalls, ...wallsToAdd];
}
