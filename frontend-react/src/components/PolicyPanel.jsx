import { useMemo } from 'react';

// Mock Toronto policy data
const MOCK_POLICIES = [
    { name: 'Toronto Official Plan (Land Use Designations)', extracts: 23 },
    { name: 'Toronto Zoning Volume 2', extracts: 5 },
    { name: 'Mid-Rise Design Guidelines', extracts: 0 },
    { name: 'Official Plan Chapter 2', extracts: 0 },
    { name: 'Official Plan Chapter 3', extracts: 0 },
    { name: 'Toronto Zoning Volume 3', extracts: 0 },
];

const MOCK_DATASETS = [
    {
        name: 'Official Plan Land Use Designations',
        description: 'General boundaries supporting the 2023 OP Consolidation; available in localized schedules',
        source: 'City of Toronto',
        values: 1,
    },
    {
        name: 'UrbanToronto',
        description: 'Founded in 2022 as an open database of applications, conversation, and building details across Toronto.',
        source: 'City of Vaughan',
        values: 14,
    },
    {
        name: 'Toronto Application Information Centre',
        description: 'The Application Information Centre (AIC) provides information on all active Community Planning applications.',
        source: 'City of Toronto',
        values: 40,
    },
    {
        name: 'Inclusionary Zoning Overlay',
        description: 'Boundaries surrounding the 2021 Inclusionary Zoning Mandate market areas.',
        source: 'City of Toronto',
        values: 1,
    },
];

const MOCK_INFO = {
    R: { units: '2 dwelling units', typology: 'Detached', height: '10 m', fsi: '0.6', uses: ['Dwelling Unit', 'Home Occupation'] },
    RD: { units: '2 dwelling units', typology: 'Semi-Detached', height: '10 m', fsi: '0.6', uses: ['Dwelling Unit', 'Home Occupation'] },
    RS: { units: '4 dwelling units', typology: 'Fourplex', height: '10 m', fsi: '1.0', uses: ['Dwelling Unit', 'Home Occupation'] },
    RT: { units: '6 dwelling units', typology: 'Townhouse', height: '12 m', fsi: '1.5', uses: ['Dwelling Unit', 'Home Occupation', 'Live-Work'] },
    RM: { units: '60 dwelling units', typology: 'Mid-Rise', height: '20 m', fsi: '2.5', uses: ['Dwelling Unit', 'Home Occupation', 'Retail'] },
    RA: { units: '120 dwelling units', typology: 'Apartment', height: '36 m', fsi: '3.5', uses: ['Dwelling Unit', 'Retail', 'Office'] },
    CR: { units: '80 dwelling units', typology: 'Mixed-Use', height: '30 m', fsi: '3.0', uses: ['Dwelling Unit', 'Retail', 'Office', 'Restaurant'] },
    CRE: { units: '100 dwelling units', typology: 'Mixed-Use', height: '45 m', fsi: '4.0', uses: ['Dwelling Unit', 'Retail', 'Office'] },
    I: { units: 'N/A', typology: 'Industrial', height: '15 m', fsi: '1.0', uses: ['Manufacturing', 'Warehouse', 'Office'] },
};

export default function PolicyPanel({ parcel, isOpen, onClose }) {
    const info = useMemo(() => {
        if (!parcel) return MOCK_INFO['R'];
        return MOCK_INFO[parcel.zoning] || MOCK_INFO['R'];
    }, [parcel]);

    return (
        <aside id="policy-panel" className={isOpen ? '' : 'panel-hidden'}>
            <div id="policy-panel-header">
                <h2 id="policy-panel-title">Project Information</h2>
                <button id="policy-panel-close" aria-label="Close panel" onClick={onClose}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                </button>
            </div>
            <div id="policy-panel-content">
                {/* Address */}
                <div id="policy-address" className="policy-section">
                    <p id="policy-address-text">
                        {parcel ? (parcel.address || 'Unknown Address') : 'Select a location to view project information'}
                    </p>
                </div>

                {/* Project Info Section */}
                {parcel && (
                    <div id="project-info-section" className="policy-section">
                        <div className="info-card">
                            <h3>Number of Units</h3>
                            <p className="info-description">
                                Loading spaces &amp; prescribed design patterns depend on the number of residential dwelling units.
                            </p>
                            <p className="info-value">
                                <span className="info-icon">≡</span> <span>{info.units}</span>
                            </p>
                        </div>
                        <div className="info-card">
                            <h3>Residential Building Typology</h3>
                            <p className="info-description">
                                Dwelling unit density and residential policies depend on construction form.
                            </p>
                            <p className="info-value">
                                <span className="info-icon">≡</span> <span>{info.typology}</span>
                            </p>
                        </div>
                        <div className="info-card">
                            <h3>Use</h3>
                            <p className="info-description">Select all relevant uses for your proposed construction.</p>
                            <div className="tag-list">
                                {info.uses.map((use) => (
                                    <span key={use} className="tag">{use}</span>
                                ))}
                            </div>
                        </div>
                        <div className="info-card">
                            <h3>Zoning</h3>
                            <p className="info-description">Applicable zoning designation for this parcel.</p>
                            <p className="info-value">
                                <span className="info-icon">≡</span> <span>{parcel.zoning} (Bylaw 569-2013)</span>
                            </p>
                        </div>
                        <div className="info-card">
                            <h3>Max Height</h3>
                            <p className="info-description">Maximum permitted building height under current zoning.</p>
                            <p className="info-value">
                                <span className="info-icon">≡</span> <span>{info.height}</span>
                            </p>
                        </div>
                        <div className="info-card">
                            <h3>FAR / FSI</h3>
                            <p className="info-description">Floor space index permitted for this lot.</p>
                            <p className="info-value">
                                <span className="info-icon">≡</span> <span>{info.fsi}</span>
                            </p>
                        </div>
                    </div>
                )}

                {/* Policies List Section */}
                {parcel && (
                    <div id="policies-list-section" className="policy-section">
                        <h3 className="section-header">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="section-icon">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                <polyline points="14 2 14 8 20 8" />
                            </svg>
                            Policies
                        </h3>
                        <p className="section-description">Subsets of legislation applying to the given parcel.</p>
                        <div id="policies-list">
                            {MOCK_POLICIES.map((p) => (
                                <div key={p.name} className="policy-item">
                                    <div className="item-left">
                                        <svg className="item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                            <polyline points="14 2 14 8 20 8" />
                                        </svg>
                                        <div>
                                            <div className="item-name">{p.name}</div>
                                        </div>
                                    </div>
                                    <div className="item-meta">{p.extracts} Extracts</div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Datasets List Section */}
                {parcel && (
                    <div id="datasets-list-section" className="policy-section">
                        <h3 className="section-header">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="section-icon">
                                <ellipse cx="12" cy="5" rx="9" ry="3" />
                                <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                                <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                            </svg>
                            Datasets
                        </h3>
                        <p className="section-description">Municipally-verified sources of truth, digitized rules and maps.</p>
                        <div id="datasets-list">
                            {MOCK_DATASETS.map((d) => (
                                <div key={d.name} className="dataset-item">
                                    <div className="item-left">
                                        <svg className="item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                            <ellipse cx="12" cy="5" rx="9" ry="3" />
                                            <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                                            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                                        </svg>
                                        <div>
                                            <div className="item-name">{d.name}</div>
                                            <div className="item-description">{d.description}</div>
                                        </div>
                                    </div>
                                    <div className="item-meta">{d.values} Values</div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </aside>
    );
}
