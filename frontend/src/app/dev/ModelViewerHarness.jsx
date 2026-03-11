import { useState } from 'react';
import ModelViewer from '../components/ModelViewer.jsx';
import {
  sampleBlueprintPages,
  sampleFloorPlans,
  sampleModelParams,
  sampleParcel,
} from './modelViewerHarnessData.js';

export default function ModelViewerHarness() {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'radial-gradient(circle at top, #1f2937 0%, #0f172a 45%, #020617 100%)',
        color: '#f8fafc',
        fontFamily: 'ui-sans-serif, system-ui, sans-serif',
      }}
    >
      <div
        style={{
          position: 'fixed',
          top: 12,
          left: 12,
          zIndex: 8,
          display: 'flex',
          gap: 12,
          alignItems: 'center',
        }}
      >
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          style={{
            border: '1px solid rgba(248, 250, 252, 0.4)',
            background: 'rgba(15, 23, 42, 0.8)',
            color: '#f8fafc',
            borderRadius: 999,
            padding: '10px 14px',
            cursor: 'pointer',
          }}
        >
          Open Viewer Harness
        </button>
        <span style={{ opacity: 0.8 }}>
          Use `Massing`, `Interior`, and `Blueprint` to test the viewer states.
        </span>
      </div>

      <ModelViewer
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        parcelGeoJSON={sampleParcel}
        modelParams={sampleModelParams}
        isPanelOpen={false}
        isSidebarCollapsed
        isChatExpanded={false}
        floorPlans={sampleFloorPlans}
        blueprintPages={sampleBlueprintPages}
      />
    </div>
  );
}
