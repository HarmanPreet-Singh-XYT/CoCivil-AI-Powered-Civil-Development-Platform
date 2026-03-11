import { useDraggable } from '@dnd-kit/core';
import './DragDropCatalog.css';

const ROOM_TEMPLATES = [
    { id: 'tpl-bed-3x3', type: 'room', roomType: 'bedroom', width: 3, height: 3, label: 'Bedroom', dims: '3x3m', color: '#4a6b8a' },
    { id: 'tpl-bed-4x4', type: 'room', roomType: 'bedroom', width: 4, height: 4, label: 'Master Bed', dims: '4x4m', color: '#4a6b8a' },
    { id: 'tpl-bath-2x2', type: 'room', roomType: 'bathroom', width: 2, height: 2, label: 'Bathroom', dims: '2x2m', color: '#4a8a7c' },
    { id: 'tpl-bath-2x3', type: 'room', roomType: 'bathroom', width: 2, height: 3, label: 'Lrg Bathroom', dims: '2x3m', color: '#4a8a7c' },
    { id: 'tpl-living-5x5', type: 'room', roomType: 'living', width: 5, height: 5, label: 'Living', dims: '5x5m', color: '#4a7c59' },
    { id: 'tpl-kitchen-3x4', type: 'room', roomType: 'kitchen', width: 3, height: 4, label: 'Kitchen', dims: '3x4m', color: '#8a7553' },
    { id: 'tpl-hall-1x3', type: 'room', roomType: 'hallway', width: 1, height: 3, label: 'Hallway', dims: '1x3m', color: '#666666' },
    { id: 'tpl-storage-2x1', type: 'room', roomType: 'storage', width: 2, height: 1.5, label: 'Storage', dims: '2x1.5m', color: '#5a5a5a' },
];

const OPENING_TEMPLATES = [
    { id: 'tpl-door-900', type: 'opening', openingType: 'door', width: 0.9, label: 'Standard Door', size: '900mm' },
    { id: 'tpl-door-1200', type: 'opening', openingType: 'door', width: 1.2, label: 'Double Door', size: '1200mm' },
    { id: 'tpl-win-1000', type: 'opening', openingType: 'window', width: 1.0, label: 'Standard Window', size: '1000mm' },
    { id: 'tpl-win-2000', type: 'opening', openingType: 'window', width: 2.0, label: 'Large Window', size: '2000mm' },
];

function DraggableItem({ template }) {
    const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
        id: template.id,
        data: template,
    });

    return (
        <div
            ref={setNodeRef}
            className={`catalog-item ${isDragging ? 'dragging' : ''}`}
            {...listeners}
            {...attributes}
            title={template.label}
        >
            <div
                className="catalog-item-preview"
                style={template.color ? { backgroundColor: `${template.color}40`, border: `2px solid ${template.color}` } : {}}
            >
                {template.type === 'room' && <span className="item-icon">⬜</span>}
                {template.type === 'opening' && <span className="item-icon">{template.openingType === 'door' ? '🚪' : '🪟'}</span>}
            </div>
            <div className="catalog-item-info">
                <span className="item-label">{template.label}</span>
                <span className="item-dims">{template.dims || template.size}</span>
            </div>
        </div>
    );
}

export default function DragDropCatalog() {
    return (
        <div className="drag-drop-catalog">
            <div className="catalog-header">Build Catalog</div>

            <div className="catalog-section">
                <div className="catalog-section-title">Rooms</div>
                <div className="catalog-grid">
                    {ROOM_TEMPLATES.map(tpl => <DraggableItem key={tpl.id} template={tpl} />)}
                </div>
            </div>

            <div className="catalog-section">
                <div className="catalog-section-title">Openings</div>
                <div className="catalog-grid">
                    {OPENING_TEMPLATES.map(tpl => <DraggableItem key={tpl.id} template={tpl} />)}
                </div>
            </div>
        </div>
    );
}
