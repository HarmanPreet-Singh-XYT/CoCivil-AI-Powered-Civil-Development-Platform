export const ROOM_COLORS = {
  living: '#4a7c59',
  bedroom: '#4a6b8a',
  kitchen: '#8a7553',
  bathroom: '#4a8a7c',
  hallway: '#666666',
  dining: '#7c6b4a',
  storage: '#5a5a5a',
  utility: '#5a6b5a',
  balcony: '#6b8a6b',
  garage: '#4a4a4a',
  office: '#6b6b8a',
  other: '#777777',
};

export function generateId(prefix) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

export function computeCentroid(polygon) {
  if (!polygon || polygon.length === 0) return [0, 0];
  let cx = 0;
  let cy = 0;
  for (const [x, y] of polygon) {
    cx += x;
    cy += y;
  }
  return [cx / polygon.length, cy / polygon.length];
}

export function ensureIds(floorPlans) {
  if (!floorPlans?.floor_plans) return floorPlans;

  const result = JSON.parse(JSON.stringify(floorPlans));
  for (const floor of result.floor_plans) {
    let wIdx = 0;
    let rIdx = 0;
    let oIdx = 0;

    if (floor.walls) {
      for (const wall of floor.walls) {
        if (!wall.id) wall.id = `w_${wIdx}`;
        if (wall.load_bearing === undefined) wall.load_bearing = 'unknown';
        wIdx++;
      }
    }

    if (floor.rooms) {
      for (const room of floor.rooms) {
        if (!room.id) room.id = `r_${rIdx}`;
        rIdx++;
      }
    }

    if (floor.openings) {
      for (const opening of floor.openings) {
        if (!opening.id) opening.id = `o_${oIdx}`;
        if (!opening.wall_id && floor.walls?.length > 0) {
          opening.wall_id = floor.walls[0].id;
        }
        oIdx++;
      }
    }
  }

  return result;
}
