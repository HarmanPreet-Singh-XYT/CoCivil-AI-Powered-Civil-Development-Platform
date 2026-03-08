import { useCallback } from 'react';

const GIRDER_TYPES = ['i_beam', 'box', 'concrete'];
const BARRIER_TYPES = ['jersey', 'railing', 'parapet'];
const COMPONENT_LABELS = {
  deck: 'Bridge Deck',
  girder: 'Girder',
  abutment: 'Abutment',
  pier: 'Pier',
  barrier: 'Barrier',
};

export default function BridgeProperties({ component, onUpdate, onClose }) {
  if (!component) return null;

  const label = COMPONENT_LABELS[component.component_type] || 'Component';

  const handleChange = useCallback((field, value) => {
    onUpdate?.({ ...component, [field]: value });
  }, [component, onUpdate]);

  return (
    <div className="infra-properties-panel">
      <div className="infra-properties-header">
        <span>{label}</span>
        <button onClick={onClose}>x</button>
      </div>

      {component.component_type === 'deck' && (
        <>
          <div className="infra-property-row">
            <span className="infra-property-label">Width (m)</span>
            <input
              className="infra-property-input"
              type="number"
              value={component.width_m ?? 12}
              onChange={(e) => handleChange('width_m', Number(e.target.value))}
              min={3}
              max={40}
              step={0.5}
            />
          </div>
          <div className="infra-property-row">
            <span className="infra-property-label">Depth (m)</span>
            <input
              className="infra-property-input"
              type="number"
              value={component.depth_m ?? 0.3}
              onChange={(e) => handleChange('depth_m', Number(e.target.value))}
              min={0.1}
              max={2}
              step={0.05}
            />
          </div>
        </>
      )}

      {component.component_type === 'girder' && (
        <>
          <div className="infra-property-row">
            <span className="infra-property-label">Type</span>
            <select
              className="infra-property-select"
              value={component.girder_type || 'i_beam'}
              onChange={(e) => handleChange('girder_type', e.target.value)}
            >
              {GIRDER_TYPES.map((t) => (
                <option key={t} value={t}>{t.replace('_', ' ')}</option>
              ))}
            </select>
          </div>
          <div className="infra-property-row">
            <span className="infra-property-label">Depth (m)</span>
            <input
              className="infra-property-input"
              type="number"
              value={component.depth_m ?? 1.2}
              onChange={(e) => handleChange('depth_m', Number(e.target.value))}
              min={0.3}
              max={4}
              step={0.1}
            />
          </div>
        </>
      )}

      {component.component_type === 'pier' && (
        <>
          <div className="infra-property-row">
            <span className="infra-property-label">Height (m)</span>
            <input
              className="infra-property-input"
              type="number"
              value={component.height_m ?? 8}
              onChange={(e) => handleChange('height_m', Number(e.target.value))}
              min={1}
              max={50}
              step={0.5}
            />
          </div>
          <div className="infra-property-row">
            <span className="infra-property-label">Width (m)</span>
            <input
              className="infra-property-input"
              type="number"
              value={component.width_m ?? 6}
              onChange={(e) => handleChange('width_m', Number(e.target.value))}
              min={1}
              max={20}
              step={0.5}
            />
          </div>
        </>
      )}

      {component.component_type === 'barrier' && (
        <div className="infra-property-row">
          <span className="infra-property-label">Type</span>
          <select
            className="infra-property-select"
            value={component.barrier_type || 'jersey'}
            onChange={(e) => handleChange('barrier_type', e.target.value)}
          >
            {BARRIER_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      )}

      {component.span_m != null && (
        <div className="infra-property-row">
          <span className="infra-property-label">Span (m)</span>
          <span className="infra-property-value">{component.span_m.toFixed(1)}</span>
        </div>
      )}
    </div>
  );
}
