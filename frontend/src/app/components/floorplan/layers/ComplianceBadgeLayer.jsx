import { Group, Circle, Text } from 'react-konva';
import { computeCentroid } from '../../../lib/floorPlanHelpers.js';

function getElementPosition(elementId, rooms, walls, openings) {
  const room = rooms?.find((r) => r.id === elementId);
  if (room?.polygon) return computeCentroid(room.polygon);

  const wall = walls?.find((w) => w.id === elementId);
  if (wall) {
    return [
      (wall.start[0] + wall.end[0]) / 2,
      (wall.start[1] + wall.end[1]) / 2,
    ];
  }

  const opening = openings?.find((o) => o.id === elementId);
  if (opening?.position) return opening.position;

  return null;
}

const SEVERITY_COLOR = {
  error: '#f87171',
  blocker: '#f87171',
  warning: '#fbbf24',
  pass: '#4ade80',
};

export default function ComplianceBadgeLayer({
  complianceResult,
  rooms,
  walls,
  openings,
  scale = 1,
  selectedElementId,
  onBadgeClick,
}) {
  if (!complianceResult?.rules) return <Group />;

  // Group rules by element_id
  const byElement = {};
  for (const rule of complianceResult.rules) {
    const eid = rule.element_id;
    if (!eid) continue;
    if (!byElement[eid]) byElement[eid] = [];
    byElement[eid].push(rule);
  }

  const badges = [];
  const radius = 8 / scale;

  for (const [elementId, rules] of Object.entries(byElement)) {
    const pos = getElementPosition(elementId, rooms, walls, openings);
    if (!pos) continue;

    // Determine worst severity
    const hasError = rules.some(
      (r) => r.severity === 'error' || r.severity === 'blocker'
    );
    const hasWarning = rules.some((r) => r.severity === 'warning');
    const allPass = rules.every(
      (r) => r.severity === 'pass' || r.severity === 'compliant'
    );

    // Only show green badges on selected element
    if (allPass && elementId !== selectedElementId) continue;

    const color = hasError
      ? SEVERITY_COLOR.error
      : hasWarning
        ? SEVERITY_COLOR.warning
        : SEVERITY_COLOR.pass;

    const violationCount = rules.filter(
      (r) => r.severity !== 'pass' && r.severity !== 'compliant'
    ).length;

    badges.push(
      <Group
        key={elementId}
        x={pos[0]}
        y={pos[1]}
        onClick={() => onBadgeClick?.(rules[0])}
        onTap={() => onBadgeClick?.(rules[0])}
      >
        <Circle
          radius={radius}
          fill={color}
          stroke="#ffffff"
          strokeWidth={1 / scale}
        />
        {violationCount > 1 && (
          <Text
            text={String(violationCount)}
            fontSize={10 / scale}
            fill="#ffffff"
            fontStyle="bold"
            align="center"
            verticalAlign="middle"
            offsetX={(5 / scale)}
            offsetY={(5 / scale)}
            width={(10 / scale)}
            height={(10 / scale)}
          />
        )}
      </Group>
    );
  }

  return <Group>{badges}</Group>;
}
