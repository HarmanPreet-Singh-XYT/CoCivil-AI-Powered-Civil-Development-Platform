import { useMemo, useCallback } from 'react';
import { Group, Arc, Line } from 'react-konva';

const GOLD = '#c8a55c';

function findWall(walls, wallId) {
  if (!walls) return null;
  return walls.find((w) => w.id === wallId) || null;
}

function positionOnWall(wall, offset) {
  const dx = wall.end[0] - wall.start[0];
  const dy = wall.end[1] - wall.start[1];
  const len = Math.sqrt(dx * dx + dy * dy);
  if (len === 0) return { x: wall.start[0], y: wall.start[1], angle: 0, ux: 0, uy: 0, len: 0 };

  const ux = dx / len;
  const uy = dy / len;
  const t = Math.min(Math.max(offset / len, 0), 1);

  return {
    x: wall.start[0] + dx * t,
    y: wall.start[1] + dy * t,
    angle: (Math.atan2(dy, dx) * 180) / Math.PI,
    ux,
    uy,
    len,
  };
}

export default function OpeningLayer({ openings, walls, selectedId, onSelect, scale = 1, onOpeningDrag }) {
  const openingData = useMemo(() => {
    if (!openings || !walls) return [];

    return openings.map((opening) => {
      const wall = findWall(walls, opening.wall_id);
      if (!wall) return null;

      const offset = opening.offset_along_wall || 0;
      const width = opening.width_m || 0.9;
      const pos = positionOnWall(wall, offset);

      return { opening, wall, pos, width };
    }).filter(Boolean);
  }, [openings, walls]);

  // Constrain drag to wall axis
  const makeDragBound = useCallback((wall) => {
    return (pos) => {
      const dx = wall.end[0] - wall.start[0];
      const dy = wall.end[1] - wall.start[1];
      const len = Math.sqrt(dx * dx + dy * dy);
      if (len === 0) return pos;

      const ux = dx / len;
      const uy = dy / len;

      // Project drag position onto wall line
      const px = pos.x - wall.start[0];
      const py = pos.y - wall.start[1];
      let t = (px * ux + py * uy) / len;
      t = Math.max(0.05, Math.min(0.95, t));

      return {
        x: wall.start[0] + ux * len * t,
        y: wall.start[1] + uy * len * t,
      };
    };
  }, []);

  if (!openings || openings.length === 0) return <Group />;

  return (
    <Group>
      {openingData.map(({ opening, wall, pos, width }) => {
        const isSelected = opening.id === selectedId;
        const strokeColor = isSelected ? GOLD : '#a8a29e';
        const draggable = isSelected && !!onOpeningDrag;

        const handleDragEnd = (e) => {
          if (!onOpeningDrag) return;
          const newX = e.target.x();
          const newY = e.target.y();
          const dx = wall.end[0] - wall.start[0];
          const dy = wall.end[1] - wall.start[1];
          const len = Math.sqrt(dx * dx + dy * dy);
          if (len === 0) return;
          const px = newX - wall.start[0];
          const py = newY - wall.start[1];
          const ux = dx / len;
          const uy = dy / len;
          const newOffset = Math.max(0, Math.min(len, px * ux + py * uy));
          onOpeningDrag(opening.id, newOffset);
        };

        if (opening.type === 'window') {
          const halfW = width / 2;
          const gap = 0.04;
          return (
            <Group
              key={opening.id}
              x={pos.x}
              y={pos.y}
              rotation={pos.angle}
              draggable={draggable}
              dragBoundFunc={draggable ? makeDragBound(wall) : undefined}
              onDragEnd={handleDragEnd}
              onClick={() => onSelect?.(opening.id)}
              onTap={() => onSelect?.(opening.id)}
            >
              <Line
                points={[-halfW, -gap, halfW, -gap]}
                stroke="#88b4d8"
                strokeWidth={2 / scale}
              />
              <Line
                points={[-halfW, gap, halfW, gap]}
                stroke="#88b4d8"
                strokeWidth={2 / scale}
              />
              {isSelected && (
                <Line
                  points={[-halfW, -gap * 3, halfW, -gap * 3, halfW, gap * 3, -halfW, gap * 3]}
                  closed
                  stroke={GOLD}
                  strokeWidth={1 / scale}
                />
              )}
            </Group>
          );
        }

        // Door: arc for swing + line for leaf
        const radius = width;
        const swingDir = opening.swing_direction === 'inward' ? 0 : 180;

        return (
          <Group
            key={opening.id}
            x={pos.x}
            y={pos.y}
            rotation={pos.angle}
            draggable={draggable}
            dragBoundFunc={draggable ? makeDragBound(wall) : undefined}
            onDragEnd={handleDragEnd}
            onClick={() => onSelect?.(opening.id)}
            onTap={() => onSelect?.(opening.id)}
          >
            {/* Door leaf */}
            <Line
              points={[0, 0, radius, 0]}
              stroke={strokeColor}
              strokeWidth={2 / scale}
            />
            {/* Door swing arc */}
            <Arc
              x={0}
              y={0}
              innerRadius={radius}
              outerRadius={radius}
              angle={90}
              rotation={swingDir === 180 ? -90 : 0}
              stroke={strokeColor}
              strokeWidth={1 / scale}
              dash={[4 / scale, 3 / scale]}
            />
          </Group>
        );
      })}
    </Group>
  );
}
