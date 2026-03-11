import { useState } from 'react';

export default function WallProperties({ wall, onWallUpdate, onWallDelete }) {
  const [confirmDelete, setConfirmDelete] = useState(false);

  if (!wall) return null;

  const length = Math.sqrt(
    Math.pow(wall.end[0] - wall.start[0], 2) +
    Math.pow(wall.end[1] - wall.start[1], 2)
  ).toFixed(2);

  const canDelete = wall.load_bearing === 'no';
  const deleteBlocked = wall.load_bearing === 'yes';
  const deleteUncertain = wall.load_bearing === 'unknown';

  return (
    <div className="wall-properties-panel">
      <h4 className="wall-properties-title">Wall Properties</h4>

      {/* Type toggle */}
      <div className="wall-prop-row">
        <span className="wall-prop-label">Type</span>
        <div className="wall-prop-toggle">
          <button
            className={`wall-toggle-btn ${wall.type === 'interior' ? 'wall-toggle-btn--active' : ''}`}
            onClick={() => onWallUpdate({ ...wall, type: 'interior' })}
          >
            Interior
          </button>
          <button
            className={`wall-toggle-btn ${wall.type === 'exterior' ? 'wall-toggle-btn--active' : ''}`}
            onClick={() => onWallUpdate({ ...wall, type: 'exterior' })}
          >
            Exterior
          </button>
        </div>
      </div>

      {/* Load-bearing */}
      <div className="wall-prop-row">
        <span className="wall-prop-label">Load-bearing</span>
        <div className="wall-prop-radio-group">
          {['unknown', 'yes', 'no'].map((val) => (
            <label key={val} className="wall-prop-radio">
              <input
                type="radio"
                name="load_bearing"
                value={val}
                checked={wall.load_bearing === val}
                onChange={() => onWallUpdate({ ...wall, load_bearing: val })}
              />
              {val.charAt(0).toUpperCase() + val.slice(1)}
            </label>
          ))}
        </div>
      </div>

      {/* Thickness */}
      <div className="wall-prop-row">
        <span className="wall-prop-label">
          Thickness: {(wall.thickness || 0.15).toFixed(2)}m
        </span>
        <input
          type="range"
          className="wall-prop-slider"
          min="0.1"
          max="0.4"
          step="0.01"
          value={wall.thickness || 0.15}
          onChange={(e) =>
            onWallUpdate({ ...wall, thickness: parseFloat(e.target.value) })
          }
        />
      </div>

      {/* Length (read-only) */}
      <div className="wall-prop-row">
        <span className="wall-prop-label">Length</span>
        <span className="wall-prop-value">{length}m</span>
      </div>

      {/* Delete */}
      <div className="wall-prop-delete-section">
        {deleteBlocked && (
          <div className="wall-prop-warning wall-prop-warning--error">
            Cannot delete a load-bearing wall
          </div>
        )}
        {deleteUncertain && (
          <div className="wall-prop-warning wall-prop-warning--warning">
            Confirm load-bearing status before deleting
          </div>
        )}
        {!confirmDelete ? (
          <button
            className="wall-prop-delete-btn"
            disabled={!canDelete}
            onClick={() => setConfirmDelete(true)}
          >
            Delete Wall
          </button>
        ) : (
          <div className="wall-prop-confirm-group">
            <span>Confirm delete?</span>
            <button
              className="wall-prop-confirm-yes"
              onClick={() => {
                onWallDelete(wall.id);
                setConfirmDelete(false);
              }}
            >
              Yes
            </button>
            <button
              className="wall-prop-confirm-no"
              onClick={() => setConfirmDelete(false)}
            >
              No
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
