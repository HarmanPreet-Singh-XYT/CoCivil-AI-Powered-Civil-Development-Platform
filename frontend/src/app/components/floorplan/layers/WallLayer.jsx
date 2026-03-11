import { useMemo, useState } from 'react';
import { Group, Rect, Circle } from 'react-konva';
import { wallToRect, snapToGrid, snapToEndpoint } from '../../../lib/wallGeometry.js';

const GOLD = '#c8a55c';
const HANDLE_RADIUS_BASE = 5;

function wallFill(wall) {
  if (wall.load_bearing === 'yes') return '#8B4513';
  return wall.type === 'exterior' ? '#333333' : '#555555';
}

function wallDash(wall, scale) {
  if (wall.load_bearing === 'yes') return [8 / scale, 4 / scale];
  if (wall.load_bearing === 'unknown') return [3 / scale, 3 / scale];
  return undefined;
}

export default function WallLayer({
  walls,
  selectedId,
  onSelect,
  scale = 1,
  activeTool,
  onWallEndpointDrag,
  wallDragId,
  onWallCenterDragStart,
  onWallCenterDrag,
  onWallCenterDragEnd,
}) {
  const wallRects = useMemo(() => {
    if (!walls) return [];
    return walls.map((wall) => {
      const { cx, cy, length, angle, thickness } = wallToRect(wall);
      const logicalThickness = wall.type === 'exterior' ? 8 / scale : 4 / scale;
      const displayThickness = Math.max(logicalThickness, thickness);
      return { wall, cx, cy, length, angle, displayThickness };
    });
  }, [walls, scale]);

  if (!walls || walls.length === 0) return <Group />;

  // Walls should be clickable for select, door, window, and delete tools
  const listening = activeTool === 'select' || activeTool === 'door' || activeTool === 'window' || activeTool === 'delete';

  const [hoveredWallId, setHoveredWallId] = useState(null);

  return (
    <Group listening={listening}>
      {wallRects.map(({ wall, cx, cy, length, angle, displayThickness }) => {
        const isSelected = wall.id === selectedId;
        const isHovered = wall.id === hoveredWallId && activeTool === 'select';
        const isDragging = wall.id === wallDragId;
        const dash = wallDash(wall, scale);

        return (
          <Group key={wall.id}>
            <Rect
              x={cx}
              y={cy}
              width={length}
              height={displayThickness}
              offsetX={length / 2}
              offsetY={displayThickness / 2}
              rotation={(angle * 180) / Math.PI}
              fill={wallFill(wall)}
              stroke={isSelected ? GOLD : (isHovered ? GOLD : undefined)}
              strokeWidth={isSelected || isHovered ? 2 / scale : 0}
              dash={dash}
              opacity={isDragging ? 0.8 : 1}
              onMouseEnter={() => setHoveredWallId(activeTool === 'select' ? wall.id : null)}
              onMouseLeave={() => setHoveredWallId(null)}
              onClick={() => {
                if (activeTool === 'delete') {
                  onSelect?.(wall.id, 'delete');
                } else {
                  onSelect?.(wall.id);
                }
              }}
              onTap={() => onSelect?.(wall.id)}
            />

            {/* Center drag handle for moving entire wall (when selected in select mode) */}
            {isSelected && activeTool === 'select' && onWallCenterDragStart && (
              <Circle
                x={cx}
                y={cy}
                radius={6 / scale}
                fill={GOLD}
                stroke="#1a1a1a"
                strokeWidth={1.5 / scale}
                opacity={0.7}
                draggable
                cursor="grab"
                onMouseEnter={(e) => {
                  e.target.to({ opacity: 1, duration: 0.1 });
                }}
                onMouseLeave={(e) => {
                  if (wall.id !== wallDragId) {
                    e.target.to({ opacity: 0.7, duration: 0.1 });
                  }
                }}
                onDragStart={(e) => {
                  e.target.to({ opacity: 1, duration: 0 });
                  onWallCenterDragStart(wall.id, [e.target.x(), e.target.y()]);
                }}
                onDragMove={(e) => {
                  onWallCenterDrag?.(wall.id, [e.target.x(), e.target.y()]);
                }}
                onDragEnd={(e) => {
                  onWallCenterDragEnd?.();
                  e.target.to({ opacity: 0.7, duration: 0.1 });
                }}
              />
            )}

            {/* Drag handles for selected wall endpoints */}
            {isSelected && activeTool === 'select' && onWallEndpointDrag && (
              <>
                <Circle
                  x={wall.start[0]}
                  y={wall.start[1]}
                  radius={HANDLE_RADIUS_BASE / scale}
                  fill={GOLD}
                  stroke="#1a1a1a"
                  strokeWidth={1 / scale}
                  draggable
                  onDragMove={(e) => {
                    const pos = [e.target.x(), e.target.y()];
                    const snapped = snapToEndpoint(pos, walls);
                    e.target.x(snapped[0]);
                    e.target.y(snapped[1]);
                  }}
                  onDragEnd={(e) => {
                    const pos = [e.target.x(), e.target.y()];
                    onWallEndpointDrag(wall.id, 'start', pos);
                  }}
                />
                <Circle
                  x={wall.end[0]}
                  y={wall.end[1]}
                  radius={HANDLE_RADIUS_BASE / scale}
                  fill={GOLD}
                  stroke="#1a1a1a"
                  strokeWidth={1 / scale}
                  draggable
                  onDragMove={(e) => {
                    const pos = [e.target.x(), e.target.y()];
                    const snapped = snapToEndpoint(pos, walls);
                    e.target.x(snapped[0]);
                    e.target.y(snapped[1]);
                  }}
                  onDragEnd={(e) => {
                    const pos = [e.target.x(), e.target.y()];
                    onWallEndpointDrag(wall.id, 'end', pos);
                  }}
                />
              </>
            )}
          </Group>
        );
      })}
    </Group>
  );
}
