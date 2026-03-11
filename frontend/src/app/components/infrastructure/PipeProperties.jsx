import { useState, useCallback } from 'react';

const MATERIALS = ['PVC', 'HDPE', 'DI', 'Concrete', 'Steel', 'Copper'];
const PIPE_TYPES = ['water', 'sanitary', 'storm', 'gas'];

export default function PipeProperties({ segment, onUpdate, onClose }) {
  if (!segment) return null;

  const handleChange = useCallback((field, value) => {
    onUpdate?.({ ...segment, [field]: value });
  }, [segment, onUpdate]);

  return (
    <div className="infra-properties-panel">
      <div className="infra-properties-header">
        <span>Pipe Segment</span>
        <button onClick={onClose}>x</button>
      </div>
      <div className="infra-property-row">
        <span className="infra-property-label">Type</span>
        <select
          className="infra-property-select"
          value={segment.pipe_type || 'water'}
          onChange={(e) => handleChange('pipe_type', e.target.value)}
        >
          {PIPE_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>
      <div className="infra-property-row">
        <span className="infra-property-label">Diameter (mm)</span>
        <input
          className="infra-property-input"
          type="number"
          value={segment.diameter_mm || 300}
          onChange={(e) => handleChange('diameter_mm', Number(e.target.value))}
          min={50}
          max={3000}
          step={25}
        />
      </div>
      <div className="infra-property-row">
        <span className="infra-property-label">Material</span>
        <select
          className="infra-property-select"
          value={segment.material || 'PVC'}
          onChange={(e) => handleChange('material', e.target.value)}
        >
          {MATERIALS.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>
      <div className="infra-property-row">
        <span className="infra-property-label">Slope (%)</span>
        <input
          className="infra-property-input"
          type="number"
          value={segment.slope_pct ?? 1.0}
          onChange={(e) => handleChange('slope_pct', Number(e.target.value))}
          min={0}
          max={20}
          step={0.1}
        />
      </div>
      <div className="infra-property-row">
        <span className="infra-property-label">Invert Elev. (m)</span>
        <input
          className="infra-property-input"
          type="number"
          value={segment.invert_elevation ?? 0}
          onChange={(e) => handleChange('invert_elevation', Number(e.target.value))}
          step={0.01}
        />
      </div>
      <div className="infra-property-row">
        <span className="infra-property-label">Length (m)</span>
        <span className="infra-property-value">{(segment.length_m ?? 0).toFixed(1)}</span>
      </div>
    </div>
  );
}
