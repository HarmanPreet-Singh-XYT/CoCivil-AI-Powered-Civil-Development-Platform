import { useMemo } from 'react';
import { Group, Line, Text } from 'react-konva';
import { ROOM_COLORS, computeCentroid } from '../../../lib/floorPlanHelpers.js';

const GOLD = '#c8a55c';

function flattenPolygon(polygon) {
  const pts = [];
  for (const [x, y] of polygon) {
    pts.push(x, y);
  }
  return pts;
}

export default function RoomLayer({ rooms, selectedId, onSelect, scale = 1, complianceResult, activeTool }) {
  const roomData = useMemo(() => {
    if (!rooms) return [];
    return rooms.map((room) => {
      const polygon = room.polygon || [];
      const flatPts = flattenPolygon(polygon);
      const centroid = computeCentroid(polygon);
      const color = ROOM_COLORS[room.room_type] || ROOM_COLORS.other;
      const areaSqm = room.area_sqm || 0;
      const areaSqft = (areaSqm * 10.764).toFixed(0);
      const label = `${room.name || room.room_type || 'Room'}\n${areaSqm.toFixed(1)} m\u00B2 (${areaSqft} sq ft)`;
      return { room, flatPts, centroid, color, label };
    });
  }, [rooms]);

  if (!rooms || rooms.length === 0) return <Group />;

  return (
    <Group listening={activeTool === 'select' || activeTool === 'room'}>
      {roomData.map(({ room, flatPts, centroid, color, label }) => {
        const isSelected = room.id === selectedId;

        return (
          <Group key={room.id}>
            <Line
              points={flatPts}
              closed
              fill={color}
              opacity={isSelected ? 0.5 : 0.3}
              stroke={isSelected ? GOLD : color}
              strokeWidth={isSelected ? 2 / scale : 1 / scale}
              onClick={(e) => onSelect?.(room.id, e)}
              onTap={(e) => onSelect?.(room.id, e)}
            />
            <Text
              x={centroid[0]}
              y={centroid[1]}
              text={label}
              fontSize={14 / scale}
              fill="#f0ece4"
              align="center"
              offsetX={50 / scale}
              offsetY={14 / scale}
              width={100 / scale}
              shadowColor="#000000"
              shadowBlur={3 / scale}
              shadowOpacity={0.7}
              listening={false}
            />
          </Group>
        );
      })}
    </Group>
  );
}
