import { useMemo } from 'react';
import { Group, Line, Text } from 'react-konva';
import { wallLength } from '../../../lib/wallGeometry.js';

const DIM_COLOR = '#78716c';
const EXTENSION = 0.3; // extension line length in metres
const OFFSET = 0.4;    // offset from wall in metres

export default function DimensionLayer({ walls, rooms, scale = 1, showDimensions = true }) {
  const dimensions = useMemo(() => {
    if (!walls || !showDimensions) return [];

    return walls.map((wall) => {
      const dx = wall.end[0] - wall.start[0];
      const dy = wall.end[1] - wall.start[1];
      const len = wallLength(wall);
      if (len < 0.1) return null;

      // Unit vector along wall
      const ux = dx / len;
      const uy = dy / len;
      // Normal (perpendicular, pointing "outward")
      const nx = -uy;
      const ny = ux;

      // Offset the dimension line away from the wall
      const ox = nx * OFFSET;
      const oy = ny * OFFSET;

      // Extension line endpoints
      const ext = EXTENSION;
      const s = wall.start;
      const e = wall.end;

      return {
        id: wall.id,
        // Extension line 1 (from wall start outward)
        ext1: [s[0], s[1], s[0] + ox + nx * ext, s[1] + oy + ny * ext],
        // Extension line 2 (from wall end outward)
        ext2: [e[0], e[1], e[0] + ox + nx * ext, e[1] + oy + ny * ext],
        // Dimension line (between extension lines at offset)
        dimLine: [
          s[0] + ox, s[1] + oy,
          e[0] + ox, e[1] + oy,
        ],
        // Label position (midpoint of dimension line)
        labelX: (s[0] + e[0]) / 2 + ox,
        labelY: (s[1] + e[1]) / 2 + oy,
        label: `${len.toFixed(2)} m`,
        angle: (Math.atan2(dy, dx) * 180) / Math.PI,
      };
    }).filter(Boolean);
  }, [walls, showDimensions]);

  if (!showDimensions || dimensions.length === 0) return <Group />;

  const fontSize = 11 / scale;
  const strokeW = 0.5 / scale;

  return (
    <Group listening={false}>
      {dimensions.map((dim) => (
        <Group key={`dim-${dim.id}`}>
          {/* Extension lines */}
          <Line points={dim.ext1} stroke={DIM_COLOR} strokeWidth={strokeW} />
          <Line points={dim.ext2} stroke={DIM_COLOR} strokeWidth={strokeW} />
          {/* Dimension line */}
          <Line points={dim.dimLine} stroke={DIM_COLOR} strokeWidth={strokeW} />
          {/* Arrow heads at each end of dimension line */}
          <ArrowHead
            x={dim.dimLine[0]}
            y={dim.dimLine[1]}
            angle={dim.angle}
            scale={scale}
          />
          <ArrowHead
            x={dim.dimLine[2]}
            y={dim.dimLine[3]}
            angle={dim.angle + 180}
            scale={scale}
          />
          {/* Label */}
          <Text
            x={dim.labelX}
            y={dim.labelY}
            text={dim.label}
            fontSize={fontSize}
            fill={DIM_COLOR}
            align="center"
            offsetX={30 / scale}
            offsetY={fontSize + 2 / scale}
            width={60 / scale}
            rotation={Math.abs(dim.angle) > 90 ? dim.angle + 180 : dim.angle}
          />
        </Group>
      ))}
    </Group>
  );
}

function ArrowHead({ x, y, angle, scale }) {
  const size = 4 / scale;
  const rad = (angle * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);

  // Two lines forming an arrowhead
  const p1x = x + size * Math.cos(rad + 2.6);
  const p1y = y + size * Math.sin(rad + 2.6);
  const p2x = x + size * Math.cos(rad - 2.6);
  const p2y = y + size * Math.sin(rad - 2.6);

  return (
    <Line
      points={[p1x, p1y, x, y, p2x, p2y]}
      stroke={DIM_COLOR}
      strokeWidth={0.5 / scale}
    />
  );
}
