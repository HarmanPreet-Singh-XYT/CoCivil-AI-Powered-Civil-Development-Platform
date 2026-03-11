import { useMemo } from 'react';
import * as THREE from 'three';
import { ROOM_COLORS } from '../lib/floorPlanHelpers.js';

const WALL_COLOR = '#333333';
const WALL_HEIGHT = 2.8;
const FLOOR_Y_SPACING = 3.5;

/* Compute the XY centroid and bounding size for a single floor
   so each floor is independently centered at the origin. */
function computeFloorBounds(floor) {
  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;

  for (const room of floor.rooms ?? []) {
    for (const [x, y] of room.polygon ?? []) {
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
  }
  for (const wall of floor.walls ?? []) {
    for (const pt of [wall.start, wall.end]) {
      if (pt[0] < minX) minX = pt[0];
      if (pt[0] > maxX) maxX = pt[0];
      if (pt[1] < minY) minY = pt[1];
      if (pt[1] > maxY) maxY = pt[1];
    }
  }

  if (!isFinite(minX)) return { cx: 0, cy: 0, w: 20, h: 20 };

  return {
    cx: (minX + maxX) / 2,
    cy: (minY + maxY) / 2,
    w: maxX - minX + 2,
    h: maxY - minY + 2,
  };
}

function RoomMesh({ room, yOffset, isSelected, onClick, cx, cy }) {
  const geometry = useMemo(() => {
    if (!room.polygon || room.polygon.length < 3) return null;
    const shape = new THREE.Shape();
    shape.moveTo(room.polygon[0][0] - cx, room.polygon[0][1] - cy);
    for (let i = 1; i < room.polygon.length; i++) {
      shape.lineTo(room.polygon[i][0] - cx, room.polygon[i][1] - cy);
    }
    shape.closePath();
    const geo = new THREE.ExtrudeGeometry(shape, { depth: 0.15, bevelEnabled: false });
    geo.rotateX(-Math.PI / 2);
    geo.translate(0, yOffset, 0);
    return geo;
  }, [room.polygon, yOffset, cx, cy]);

  if (!geometry) return null;

  const color = ROOM_COLORS[room.type] || ROOM_COLORS.other;

  return (
    <mesh
      geometry={geometry}
      onClick={(e) => { e.stopPropagation(); onClick?.(room); }}
      castShadow
      receiveShadow
    >
      <meshStandardMaterial
        color={color}
        roughness={0.7}
        metalness={0.1}
        emissive={isSelected ? '#c8a55c' : '#000000'}
        emissiveIntensity={isSelected ? 0.4 : 0}
      />
    </mesh>
  );
}

function WallMesh({ wall, yOffset, cx, cy }) {
  const geometry = useMemo(() => {
    const sx = wall.start[0] - cx;
    const sy = wall.start[1] - cy;
    const ex = wall.end[0] - cx;
    const ey = wall.end[1] - cy;

    const dx = ex - sx;
    const dy = ey - sy;
    const length = Math.sqrt(dx * dx + dy * dy);
    if (length < 0.01) return null;

    const thickness = wall.thickness_m || 0.2;
    const geo = new THREE.BoxGeometry(length, WALL_HEIGHT, thickness);

    const wcx = (sx + ex) / 2;
    const wcz = (sy + ey) / 2;
    const angle = Math.atan2(dy, dx);

    const matrix = new THREE.Matrix4();
    matrix.makeRotationY(-angle);
    matrix.setPosition(wcx, yOffset + WALL_HEIGHT / 2, wcz);
    geo.applyMatrix4(matrix);

    return geo;
  }, [wall, yOffset, cx, cy]);

  if (!geometry) return null;

  return (
    <mesh geometry={geometry} castShadow receiveShadow>
      <meshStandardMaterial color={WALL_COLOR} roughness={0.8} metalness={0.05} />
    </mesh>
  );
}

export default function FloorPlanView({ floorPlans, activeFloor, selectedRoom, onRoomClick }) {
  if (!floorPlans?.floor_plans?.length) return null;

  const allFloors = floorPlans.floor_plans;

  // Pre-compute per-floor bounds so each floor is centered independently
  const boundsMap = useMemo(() => {
    const map = new Map();
    for (const floor of allFloors) {
      map.set(floor.floor_number, computeFloorBounds(floor));
    }
    return map;
  }, [allFloors]);

  // Use the largest floor dimensions for the slab size
  const slabSize = useMemo(() => {
    let maxW = 20, maxH = 20;
    for (const b of boundsMap.values()) {
      if (b.w > maxW) maxW = b.w;
      if (b.h > maxH) maxH = b.h;
    }
    return { w: maxW, h: maxH };
  }, [boundsMap]);

  const floors = activeFloor != null
    ? allFloors.filter((f) => f.floor_number === activeFloor)
    : allFloors;

  return (
    <group>
      {floors.map((floor) => {
        const yOffset = floor.floor_number * FLOOR_Y_SPACING;
        const bounds = boundsMap.get(floor.floor_number) || { cx: 0, cy: 0 };
        return (
          <group key={floor.floor_number}>
            {/* Floor slab — sized to largest floor footprint */}
            <mesh position={[0, yOffset - 0.05, 0]} receiveShadow>
              <boxGeometry args={[slabSize.w, 0.1, slabSize.h]} />
              <meshStandardMaterial color="#222222" roughness={1} transparent opacity={0.3} />
            </mesh>

            {/* Rooms */}
            {floor.rooms?.map((room, i) => (
              <RoomMesh
                key={`room-${floor.floor_number}-${i}`}
                room={room}
                yOffset={yOffset}
                cx={bounds.cx}
                cy={bounds.cy}
                isSelected={selectedRoom?.name === room.name && selectedRoom?.floor === floor.floor_number}
                onClick={(r) => onRoomClick?.({ ...r, floor: floor.floor_number })}
              />
            ))}

            {/* Walls */}
            {floor.walls?.map((wall, i) => (
              <WallMesh
                key={`wall-${floor.floor_number}-${i}`}
                wall={wall}
                yOffset={yOffset}
                cx={bounds.cx}
                cy={bounds.cy}
              />
            ))}
          </group>
        );
      })}
    </group>
  );
}
