import { ROOM_COLORS } from '../../../lib/floorPlanHelpers.js';

const ROOM_TYPES = Object.keys(ROOM_COLORS);

export default function RoomTypeSelector({ currentType, onTypeChange, position }) {
  return (
    <div
      className="room-type-selector"
      style={{
        left: position?.x ?? 0,
        top: position?.y ?? 0,
      }}
    >
      <div className="room-type-grid">
        {ROOM_TYPES.map((type) => (
          <button
            key={type}
            className={`room-type-btn ${type === currentType ? 'room-type-btn--active' : ''}`}
            onClick={() => onTypeChange(type)}
          >
            <span
              className="room-type-swatch"
              style={{ background: ROOM_COLORS[type] }}
            />
            <span className="room-type-label">{type}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
