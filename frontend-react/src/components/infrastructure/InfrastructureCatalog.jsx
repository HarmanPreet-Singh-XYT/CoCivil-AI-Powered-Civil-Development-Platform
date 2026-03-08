const PIPE_ITEMS = [
  { id: 'pipe_water', label: 'Water', pipe_type: 'water', diameter_mm: 300 },
  { id: 'pipe_sanitary', label: 'Sanitary', pipe_type: 'sanitary', diameter_mm: 250 },
  { id: 'pipe_storm', label: 'Storm', pipe_type: 'storm', diameter_mm: 450 },
  { id: 'pipe_gas', label: 'Gas', pipe_type: 'gas', diameter_mm: 150 },
];

const FITTING_ITEMS = [
  { id: 'fit_manhole', label: 'Manhole', fitting_type: 'manhole' },
  { id: 'fit_elbow', label: 'Elbow', fitting_type: 'elbow' },
  { id: 'fit_tee', label: 'Tee', fitting_type: 'tee' },
  { id: 'fit_reducer', label: 'Reducer', fitting_type: 'reducer' },
];

const BRIDGE_ITEMS = [
  { id: 'br_deck', label: 'Deck', component: 'deck' },
  { id: 'br_girder', label: 'Girder', component: 'girder' },
  { id: 'br_abutment', label: 'Abutment', component: 'abutment' },
  { id: 'br_pier', label: 'Pier', component: 'pier' },
  { id: 'br_barrier', label: 'Barrier', component: 'barrier' },
];

export default function InfrastructureCatalog({ mode, onDragStart }) {
  const handleDragStart = (e, item) => {
    e.dataTransfer.setData('application/json', JSON.stringify(item));
    e.dataTransfer.effectAllowed = 'copy';
    onDragStart?.(item);
  };

  return (
    <div className="infra-catalog">
      <div className="infra-catalog-header">Components</div>

      {(mode === 'pipeline' || !mode) && (
        <>
          <div className="infra-catalog-section">
            <div className="infra-catalog-section-title">Pipes</div>
            <div className="infra-catalog-items">
              {PIPE_ITEMS.map((item) => (
                <div
                  key={item.id}
                  className="infra-catalog-item"
                  draggable
                  onDragStart={(e) => handleDragStart(e, item)}
                >
                  {item.label}
                </div>
              ))}
            </div>
          </div>
          <div className="infra-catalog-section">
            <div className="infra-catalog-section-title">Fittings</div>
            <div className="infra-catalog-items">
              {FITTING_ITEMS.map((item) => (
                <div
                  key={item.id}
                  className="infra-catalog-item"
                  draggable
                  onDragStart={(e) => handleDragStart(e, item)}
                >
                  {item.label}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {(mode === 'bridge' || !mode) && (
        <div className="infra-catalog-section">
          <div className="infra-catalog-section-title">Bridge</div>
          <div className="infra-catalog-items">
            {BRIDGE_ITEMS.map((item) => (
              <div
                key={item.id}
                className="infra-catalog-item"
                draggable
                onDragStart={(e) => handleDragStart(e, item)}
              >
                {item.label}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
