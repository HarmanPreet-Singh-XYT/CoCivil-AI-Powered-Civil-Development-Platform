import { useState } from 'react';

export default function ScaleCalibration({ floorPlans, onCalibrate, onSkip }) {
  const [metresPerUnit, setMetresPerUnit] = useState(
    floorPlans?.scale?.metres_per_unit || 1.0
  );

  const handleCalibrate = () => {
    onCalibrate({
      calibrated: true,
      metres_per_unit: metresPerUnit,
      reference_points: [],
    });
  };

  return (
    <div className="scale-calibration-modal">
      <div className="scale-calibration-content">
        <h3>Scale Calibration</h3>
        <p>
          Enter the scale factor to convert drawing units to metres, or skip if
          the plan is already in metres.
        </p>

        <div className="scale-calibration-input-group">
          <label className="scale-calibration-label">
            Metres per drawing unit
          </label>
          <input
            type="number"
            className="scale-calibration-input"
            value={metresPerUnit}
            onChange={(e) => setMetresPerUnit(parseFloat(e.target.value) || 1)}
            min="0.001"
            step="0.01"
          />
        </div>

        <div className="scale-calibration-actions">
          <button onClick={handleCalibrate} className="scale-calibration-confirm">
            Calibrate
          </button>
          <button onClick={onSkip}>Skip (already in metres)</button>
        </div>
      </div>
    </div>
  );
}
