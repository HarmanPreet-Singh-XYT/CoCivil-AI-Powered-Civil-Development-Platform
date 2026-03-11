/**
 * Ontario / Toronto water main standards, network data, open datasets,
 * inspection protocols, and historical records.
 *
 * All content is sourced from authoritative references:
 *   - Ontario Provincial Standards (OPSS / OPSD) — MTO / MEA
 *   - AWWA standards (American Water Works Association)
 *   - CSA standards (Canadian Standards Association)
 *   - Ontario Regulation 170/03 (Safe Drinking Water Act, 2002)
 *   - City of Toronto Open Data Portal (open.toronto.ca)
 *   - Toronto Water capital budget and program documents
 *   - Toronto Engineering Construction Standards (ECS)
 *
 * Sources:
 *   https://municipalengineers.on.ca/resources/ops.html
 *   https://www.ontario.ca/laws/regulation/030170
 *   https://open.toronto.ca/
 *   https://www.toronto.ca/services-payments/water-environment/tap-water-in-toronto/
 *   https://www.toronto.ca/wp-content/uploads/2025/04/8dab-2025-Public-Book-TW-V1.pdf
 */

// ---------------------------------------------------------------------------
// Tab 1 — Standards
// Ontario Provincial Standards and referenced technical standards for water mains
// ---------------------------------------------------------------------------

export const WATERMAIN_STANDARDS = {
  title: 'Standards',
  description:
    'Ontario Provincial Standards (OPSS / OPSD), AWWA, and CSA standards governing water main design, materials, and construction.',

  opss: [
    {
      id: 'OPSS.MUNI 441',
      edition: 'November 2014 (MEA edition)',
      title: 'Construction Specification for Watermain Installation in Open Cut',
      scope:
        'Covers installation of pressure watermains, service connections, valves, hydrants, ' +
        'and thrust restraints in open-cut trenches. Sets bedding, backfill, jointing, ' +
        'and testing requirements.',
      keyRequirements: [
        'Pipe laid in dry trench; dewatering per OPSS 517',
        'Bedding: granular material minimum 150 mm below pipe invert',
        'Minimum cover: 1.5 m to pipe crown (frost protection)',
        'Horizontal separation from sanitary sewer: 3.0 m minimum',
        'Pressure test: 1.5× working pressure or 1 035 kPa minimum, 2-hour hold',
        'Leakage allowance per AWWA C600 formula: L = ND√P / 7 400',
        'Disinfection per AWWA C651 before commissioning',
        'All materials NSF/ANSI 61 certified (contact with potable water)',
        'Thrust restraint: concrete blocking or mechanical restraint per design',
      ],
      referencedIn: 'Toronto ECS TS 441 (September 2017)',
      url: 'https://municipalengineers.on.ca/resources/ops.html',
    },
    {
      id: 'OPSS.MUNI 491',
      edition: 'November 2017',
      title: 'Construction Specification for Pipe Abandonment',
      scope:
        'Governs abandonment of existing watermains, sanitary sewers, and storm sewers ' +
        'including filling with low-strength grout and end-sealing procedures.',
      keyRequirements: [
        'Abandoned pipe filled with cellular grout or controlled low-strength material (CLSM)',
        'All service connections disconnected and capped',
        'Abandonment locations recorded on as-built drawings',
      ],
      url: 'https://municipalengineers.on.ca/resources/ops.html',
    },
    {
      id: 'OPSS.MUNI 493',
      edition: 'November 2021',
      title: 'Construction Specification for Watermain Lining',
      scope:
        'Cured-in-place pipe (CIPP) lining of existing watermains. Used by Toronto Water ' +
        'for structural rehabilitation of cast-iron distribution mains without open cut.',
      keyRequirements: [
        'Liner design per ASTM F1216 or ASTM F2019',
        'Pre-lining CCTV inspection required to assess pipe condition',
        'Pipe flushed, cleaned, and dried before liner installation',
        'NSF/ANSI 61 certification required for liner materials',
        'Post-lining CCTV inspection to confirm quality; defects repaired or removed',
        'Minimum liner thickness calculated for independent structural capacity',
      ],
      url: 'https://municipalengineers.on.ca/resources/ops.html',
    },
  ],

  opsd: [
    {
      id: 'OPSD 806.010',
      title: 'Watermain Bedding and Trench Backfill',
      description:
        'Standard drawing for granular bedding zones, pipe haunch support, and ' +
        'compaction requirements for pressure watermains in open cut.',
    },
    {
      id: 'OPSD 1105.010',
      title: 'Valve Chamber — Inline Gate Valve',
      description:
        'Standard chamber geometry, access frame and cover, ladder rungs, and ' +
        'ventilation for inline gate valve installations.',
    },
    {
      id: 'OPSD 1105.020',
      title: 'Valve Chamber — Butterfly Valve',
      description:
        'Chamber dimensions and access cover details for butterfly valves on ' +
        'transmission mains (typically 400 mm and larger).',
    },
    {
      id: 'OPSD 1106.010',
      title: 'Fire Hydrant Installation',
      description:
        'Hydrant lead pipe, tee connection, breakaway coupling, thrust block, ' +
        'and drain pit arrangement for dry-barrel fire hydrant installations.',
    },
  ],

  awwa: [
    {
      id: 'AWWA C151/A21.51',
      title: 'Ductile-Iron Pipe, Centrifugally Cast',
      applicability:
        'Pipe from 80 mm (3 in) to 1 600 mm (64 in) diameter. Pressure class ' +
        'selection per AWWA C150. Standard for Toronto transmission mains and ' +
        'large distribution mains where corrosion resistance required.',
      notes: 'Cement-mortar lining per AWWA C104; polyethylene encasement per AWWA C105 in corrosive soils.',
    },
    {
      id: 'AWWA C900',
      title: 'PVC Pressure Pipe and Fabricated Fittings, 4 in through 60 in',
      applicability:
        'Gasketed PVC pipe for distribution watermains. Dimension Ratio (DR) 18 most ' +
        'common in Ontario (pressure rating 235 psi / 1 620 kPa). Also certified to ' +
        'CSA B137.3.',
      notes: 'Pipe must bear both AWWA C900 and NSF/ANSI 61 marks.',
    },
    {
      id: 'AWWA C906',
      title: 'Polyethylene (PE) Pressure Pipe and Fittings, 4 in through 65 in',
      applicability:
        'HDPE pipe for directional drilling, pipe bursting, and corrosive environments. ' +
        'Pressure rating per DR classification (DR 11 = 160 psi working pressure). ' +
        'Also certified to CSA B137.1.',
      notes: 'Heat fusion joints only; mechanical couplings require manufacturer approval.',
    },
    {
      id: 'AWWA C509',
      title: 'Resilient-Seated Gate Valves for Water Supply Service',
      applicability:
        'Gate valves 50 mm to 500 mm for distribution watermains. Minimum 150 psi ' +
        'working pressure. Standard for isolation valves in Toronto distribution system.',
      notes: 'AWWA C515 covers larger-diameter (600 mm+) resilient-seated gate valves.',
    },
    {
      id: 'AWWA C504',
      title: 'Rubber-Seated Butterfly Valves',
      applicability:
        'Butterfly valves 50 mm to 3 600 mm. Class 150B standard for transmission ' +
        'main applications. Used on Toronto trunk mains 400 mm and larger.',
      notes: 'Operators and actuators specified separately; gear operators required for valves >300 mm.',
    },
    {
      id: 'AWWA C502',
      title: 'Dry-Barrel Fire Hydrants',
      applicability:
        'Dry-barrel hydrants for climates with freezing temperatures. Required operating ' +
        'torque: 200 ft-lb (270 N·m) maximum at operating nut. Minimum 5¼-inch main valve.',
      notes: 'Toronto standard: hydrant colour red with yellow bonnet; NFPA 291 flow rating required.',
    },
    {
      id: 'AWWA C600',
      title: 'Installation of Ductile-Iron Mains and Their Appurtenances',
      applicability:
        'Field installation, jointing, thrust restraint, pressure testing, and ' +
        'leakage testing of ductile-iron watermains.',
      notes: 'Pressure test: 1.5× operating pressure, minimum 1 hour. Leakage formula L = ND√P / 7 400.',
    },
    {
      id: 'AWWA C651',
      title: 'Disinfecting Water Mains',
      applicability:
        'Chlorination protocol before commissioning any new or repaired main. ' +
        'Minimum 25 mg/L free chlorine concentration, 24-hour contact time, ' +
        'then flush to residual ≤ 2.0 mg/L.',
      notes: 'Bacteriological samples (total coliform) required after flushing before service.',
    },
    {
      id: 'AWWA M17',
      title: 'Installation, Field Testing, and Maintenance of Fire Hydrants (Manual)',
      applicability:
        'Guidance manual (not mandatory standard) covering installation clearances, ' +
        'flow testing, and maintenance intervals for fire hydrants.',
      notes: 'Ontario Fire Code and local fire department requirements also apply.',
    },
  ],

  csa: [
    {
      id: 'CSA B137.3',
      title: 'Rigid Polyvinyl Chloride (PVC) Pipe for Pressure Applications',
      applicability:
        'Canadian companion standard to AWWA C900. Required alongside AWWA C900 ' +
        'for PVC watermain pipe sold in Ontario municipalities.',
    },
    {
      id: 'CSA B137.1',
      title: 'Polyethylene Pipe, Tubing, and Fittings for Cold-Pressure Service',
      applicability:
        'Canadian companion standard to AWWA C906 for HDPE watermain pipe.',
    },
    {
      id: 'NSF/ANSI 61',
      title: 'Drinking Water System Components — Health Effects',
      applicability:
        'Third-party certification required for all pipe, fittings, valves, coatings, ' +
        'and liners in contact with potable water. Mandatory under Ontario O.Reg 170/03.',
    },
  ],

  torontoLocalAmendments: [
    {
      ref: 'Toronto ECS TS 441 (September 2017)',
      title: 'Watermain Installation in Open Cut — Toronto Supplement',
      notes:
        'Supplements OPSS.MUNI 441 with Toronto-specific requirements: approved product ' +
        'list, hydrant locations at max 150 m spacing, cathodic protection for DI pipe ' +
        'in corrosive soils (soil resistivity < 2 000 ohm-cm), and warranty periods.',
      url: 'https://www.toronto.ca/wp-content/uploads/2017/11/8f21-ecs-specs-pipespecs-TS_441_Sep2017.pdf',
    },
    {
      ref: 'Toronto ECS TS 7.60 (January 2015)',
      title: 'CIPP Lining of Watermains',
      notes:
        'Toronto supplement for CIPP rehabilitation: liner design using ASTM F1216, ' +
        'minimum 6.5 mm liner thickness for distribution mains, CCTV before and after, ' +
        'NSF/ANSI 61 liner certification required.',
      url: 'https://www.toronto.ca/wp-content/uploads/2017/11/8fac-ecs-specs-pipespecs-TS_7.60_Jan2015.pdf',
    },
    {
      ref: 'Toronto ECS Chapter 6 (January 2022)',
      title: 'Material Specifications — Pipe and Appurtenances',
      notes:
        'Approved materials list: ductile iron (AWWA C151), PVC (AWWA C900 / CSA B137.3), ' +
        'PVCO (AWWA C909 / CSA B137.3.1), HDPE (AWWA C906 / CSA B137.1). ' +
        'All must be NSF/ANSI 61 certified.',
      url: 'https://www.toronto.ca/wp-content/uploads/2022/01/9435-ecs-specs-matspec-chapter-6-material-specifications.pdf',
    },
  ],
};

// ---------------------------------------------------------------------------
// Tab 2 — Network
// Civil engineering network analysis data for Toronto water distribution
// ---------------------------------------------------------------------------

export const WATERMAIN_NETWORK = {
  title: 'Network',
  description:
    'Toronto Water distribution network characteristics, pressure zones, and ' +
    'hydraulic analysis parameters relevant to civil engineering design.',

  systemOverview: {
    totalLength_km: 6100,
    transmissionMain_km: 550,
    distributionMain_km: 5550,
    pumpingStations: 18,
    elevatedTanks: 4,
    reservoirs: 11,
    pressureZones: 6,
    pressureDistricts: 13,
    source:
      'Toronto Water Wikipedia / City of Toronto Water Supply overview — ' +
      'https://en.wikipedia.org/wiki/Toronto_Water',
  },

  pressureZones: [
    {
      zone: 'Low Pressure Zone',
      typicalPressure_kPa: '275 – 415',
      description:
        'Lakefront and lower-elevation areas. Served directly by filtration plant ' +
        'distribution pumps without booster stations.',
      minResidualPressure_kPa: 275,
      maxStaticPressure_kPa: 690,
    },
    {
      zone: 'Intermediate Pressure Zone',
      typicalPressure_kPa: '345 – 550',
      description:
        'Mid-city elevations including downtown core. Maintained by intermediate ' +
        'booster pumping stations.',
      minResidualPressure_kPa: 345,
      maxStaticPressure_kPa: 690,
    },
    {
      zone: 'High Pressure Zone(s)',
      typicalPressure_kPa: '415 – 690',
      description:
        'North York, Scarborough, and Etobicoke upland areas. Served by high-lift ' +
        'pumping stations and pressure reducing valves (PRVs) at zone boundaries.',
      minResidualPressure_kPa: 415,
      maxStaticPressure_kPa: 690,
    },
  ],

  hydraulicDesignCriteria: {
    minResidualPressure_kPa: 275,
    maxStaticPressure_kPa: 690,
    minFireFlowResidual_kPa: 140,
    peakHourFactor: 2.0,
    maxDayFactor: 1.5,
    minVelocity_m_s: 0.3,
    maxVelocity_m_s: 3.0,
    designStandard: 'AWWA M31 — Distribution System Requirements for Fire Protection',
    notes:
      'Minimum 275 kPa (40 psi) residual during peak hour demand. ' +
      'Fire flow residual minimum 140 kPa (20 psi) at hydrant.',
  },

  pipeClassification: [
    {
      class: 'Trunk / Transmission Main',
      typicalDiameter_mm: '400 – 1 200',
      function:
        'Conveys treated water from filtration plants (R.C. Harris, F.J. Horgan, ' +
        'Island WTP) to pressure zones and storage reservoirs. Not tapped for ' +
        'direct service connections.',
      material: 'Ductile iron, prestressed concrete cylinder pipe (PCCP)',
      notes: 'WSP has rehabilitated >260 km of Toronto transmission mains via CIPP lining.',
    },
    {
      class: 'Primary Distribution Main',
      typicalDiameter_mm: '200 – 400',
      function:
        'Arterial grid forming the backbone of each pressure zone. Provides ' +
        'redundant supply paths and feeds secondary mains.',
      material: 'Ductile iron, PVC (AWWA C900)',
      notes: 'Typically on arterial roads; looped where possible for redundancy.',
    },
    {
      class: 'Secondary Distribution Main',
      typicalDiameter_mm: '150 – 200',
      function:
        'Local distribution to residential and commercial blocks. Fire hydrant ' +
        'spacing maximum 150 m (Toronto ECS TS 441).',
      material: 'PVC (AWWA C900 / CSA B137.3), ductile iron',
      notes: '150 mm is minimum diameter for new distribution mains (OPSS.MUNI 441).',
    },
    {
      class: 'Water Service Connection',
      typicalDiameter_mm: '19 – 50',
      function:
        'Individual service from distribution main to property line stop valve. ' +
        'Lead services being replaced under Toronto Capital Water Service Replacement Program.',
      material: 'Copper (type K), HDPE',
      notes:
        'Toronto has been replacing ~3 000 lead services per year. ' +
        'Target: all lead services eliminated by 2031.',
    },
  ],

  valveIsolation: {
    principle:
      'Toronto Water uses valve isolation zones to limit the number of ' +
      'customers affected during a main break or planned maintenance. ' +
      'Isolation is achieved by closing strategic gate or butterfly valves.',
    maxValveSpacing_m: 200,
    typicalIsolationZone:
      'One city block or fewer (approximately 80 – 120 m intervals on distribution mains)',
    valveTypes: [
      {
        type: 'Resilient Wedge Gate Valve (RWGV)',
        standard: 'AWWA C509',
        application: 'Distribution mains up to 400 mm; operated by T-bar wrench from street',
      },
      {
        type: 'Butterfly Valve',
        standard: 'AWWA C504',
        application: 'Transmission mains 400 mm and larger; gear-operated in valve chamber',
      },
      {
        type: 'Pressure Reducing Valve (PRV)',
        application: 'Zone boundary pressure management; automatically maintains downstream set-point',
      },
      {
        type: 'Air Release / Vacuum Valve',
        application: 'High points on transmission mains to release trapped air and prevent vacuum collapse',
      },
      {
        type: 'Check Valve',
        standard: 'AWWA C508',
        application: 'Pump discharge headers; prevents backflow on loss of power',
      },
    ],
  },

  networkAnalysisParameters: [
    {
      parameter: 'Hazen-Williams Coefficient (C)',
      description: 'Hydraulic roughness for friction loss calculations',
      values: {
        'PVC (new)': 150,
        'Ductile iron (new)': 130,
        'Cast iron (50+ years)': 80,
        'CIPP-lined cast iron': 140,
      },
      formula: 'V = 0.849 × C × R^0.63 × S^0.54',
    },
    {
      parameter: 'Fire Flow Demand',
      description: 'Design fire flow requirements by land use',
      values: {
        'Single-family residential': '1 900 L/min minimum',
        'Commercial / industrial': '3 800 – 9 500 L/min',
        'High-rise residential': '5 700 L/min',
      },
      standard: 'Ontario Building Code Div. B Part 3; NFPA 291',
    },
    {
      parameter: 'Leakage Rate (Real Losses)',
      description: 'Industry Infrastructure Leakage Index (ILI) target',
      toronto: 'Toronto Water reports system leakage as part of annual O.Reg 453/07 reporting',
      target: 'ILI < 2.0 (good performance benchmark per AWWA M36)',
    },
  ],

  interconnections: {
    description:
      'Toronto water system is interconnected with York Region (at Steeles Ave) and ' +
      'Peel Region (at Etobicoke boundary) via emergency tie connections. ' +
      'These connections are normally closed but can be activated under emergency conditions.',
    emergencyConnections: ['York Region — Steeles Ave W', 'Peel Region — Etobicoke Creek'],
  },
};

// ---------------------------------------------------------------------------
// Tab 3 — Datasets
// Real Toronto Open Data and provincial datasets for water infrastructure
// ---------------------------------------------------------------------------

export const WATERMAIN_DATASETS = {
  title: 'Datasets',
  description:
    'Official open data sources for Toronto water infrastructure. All datasets are ' +
    'available under the Open Government Licence – Toronto (v2.0) unless noted.',

  torontoOpenData: [
    {
      name: 'Watermain Breaks',
      publisher: 'Toronto Water',
      portalUrl: 'https://open.toronto.ca/dataset/watermain-breaks/',
      ckanUrl: 'https://ckan0.cf.opendata.inter.prod-toronto.ca/ne/dataset/watermain-breaks',
      formats: ['XLSX', 'SHP'],
      refreshCycle: 'Annual',
      coverage: '1990 – 2016 (27 years of break incidents)',
      coordinateSystem: 'MTM NAD 27 (3-degree), also Lat/Long',
      fields: [
        { name: 'BREAK_DATE', type: 'Date', description: 'Date of watermain break reported' },
        { name: 'BREAK_YEAR', type: 'Integer', description: 'Year of watermain break reported' },
        { name: 'XCOORD', type: 'Float', description: 'MTM NAD 27 Easting (metres)' },
        { name: 'YCOORD', type: 'Float', description: 'MTM NAD 27 Northing (metres)' },
      ],
      notes:
        'Dataset spans 27 years to 2016. Use for break frequency analysis, age-break ' +
        'correlation studies, and rehabilitation prioritization.',
    },
    {
      name: 'Water Network (City Utility Mapping — CUMAP)',
      publisher: 'Toronto Water / Engineering & Construction Services',
      portalUrl: 'https://www.toronto.ca/city-government/data-research-maps/utility-maps-engineering-drawings/',
      formats: ['DXF', 'Shapefile (on request)'],
      refreshCycle: 'Continuous (daily updates to master GIS)',
      fields: [
        { name: 'PIPE_MATERIAL', type: 'String', description: 'Material code (CI, DI, PVC, AC, etc.)' },
        { name: 'DIAMETER_MM', type: 'Integer', description: 'Nominal internal diameter in millimetres' },
        { name: 'YEAR_INSTALLED', type: 'Integer', description: 'Year of original installation' },
        { name: 'PIPE_TYPE', type: 'String', description: 'Functional class (transmission, distribution)' },
        { name: 'PRESSURE_ZONE', type: 'String', description: 'Assigned pressure zone designation' },
      ],
      notes:
        'Full GIS dataset requires ECS Engineering Drawing request (EngDrawings@toronto.ca, 416-338-7954). ' +
        'Publicly available within former East York, Etobicoke, North York, Scarborough, York boundaries.',
    },
    {
      name: 'Water System Map for Development',
      publisher: 'Toronto Water',
      portalUrl: 'https://www.toronto.ca/services-payments/building-construction/infrastructure-city-construction/water-system-map/',
      formats: ['Interactive web map'],
      refreshCycle: 'As updated',
      notes:
        'Public-facing map showing watermain locations, diameters, and pressure zones. ' +
        'Intended for development pre-consultation and servicing reports.',
    },
    {
      name: 'Building Permits',
      publisher: 'Toronto Building',
      portalUrl: 'https://open.toronto.ca/dataset/building-permits-active-permits/',
      formats: ['CSV', 'JSON', 'SHP'],
      refreshCycle: 'Daily',
      notes:
        'Contains infrastructure-related permits; cross-reference with watermain data ' +
        'to identify planned road openings and service connections.',
    },
  ],

  provincialDatasets: [
    {
      name: 'Ontario Integrated Hydrology (OIH) — Watercourses',
      publisher: 'Ministry of Natural Resources and Forestry (MNRF) / LIO',
      url: 'https://geohub.lio.gov.on.ca/',
      format: 'Shapefile, GeoJSON',
      notes:
        'Provincial watershed boundaries relevant to water supply catchment areas and ' +
        'source water protection planning under Clean Water Act, 2006.',
    },
    {
      name: 'Ontario Drinking Water Systems Registry',
      publisher: 'Ministry of the Environment, Conservation and Parks (MECP)',
      url: 'https://www.ontario.ca/data/ontario-drinking-water-systems-registry',
      format: 'CSV',
      notes:
        'Registry of all licensed municipal drinking water systems under Safe Drinking Water Act, 2002. ' +
        'Includes Toronto Water system characteristics and operator certification details.',
    },
    {
      name: 'MPAC Assessment Data (municipal infrastructure)',
      publisher: 'Municipal Property Assessment Corporation',
      url: 'https://www.mpac.ca/',
      format: 'Tabular (restricted access)',
      notes:
        'Asset values used in municipal asset management plans per O.Reg 588/17 ' +
        '(Asset Management Planning for Municipal Infrastructure).',
    },
  ],

  apiAccess: {
    torontoCKAN: {
      baseUrl: 'https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/',
      packageSearch: 'package_search?q=water',
      packageShow: 'package_show?id=watermain-breaks',
      notes: 'Standard CKAN API v3. No authentication required for public datasets.',
    },
    pythonExample: `import requests
r = requests.get(
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show",
    params={"id": "watermain-breaks"}
)
resources = r.json()["result"]["resources"]`,
  },
};

// ---------------------------------------------------------------------------
// Tab 4 — Inspections
// Real inspection protocols and Ontario regulatory requirements
// ---------------------------------------------------------------------------

export const WATERMAIN_INSPECTIONS = {
  title: 'Inspections',
  description:
    'Inspection methods, protocols, and regulatory requirements for municipal water mains in Ontario.',

  regulatoryFramework: [
    {
      regulation: 'O.Reg 170/03 — Drinking Water Systems',
      act: 'Safe Drinking Water Act, 2002 (S.O. 2002, c. 32)',
      url: 'https://www.ontario.ca/laws/regulation/030170',
      summary:
        'Establishes mandatory operational checks, sampling frequencies, and record-keeping ' +
        'for all municipal residential drinking water systems. Requires the owner/operating ' +
        'authority to document all maintenance activities and make records available for ' +
        'MECP inspection. Records retained 2–15 years depending on parameter.',
      keyRequirements: [
        'Scheduled maintenance inspections logged and retained',
        'Water quality sampling at prescribed frequencies',
        'Annual summary report to MECP and local Medical Officer of Health',
        'Corrective actions documented within 30 days of inspection finding',
      ],
    },
    {
      regulation: 'O.Reg 453/07 — Municipal Drinking Water Licensing',
      act: 'Safe Drinking Water Act, 2002',
      summary:
        'Requires municipal drinking water systems to obtain and maintain a Drinking Water Works ' +
        'Permit (DWWP). Major infrastructure changes (new mains, pump stations) require permit amendment.',
    },
    {
      regulation: 'O.Reg 588/17 — Asset Management Planning',
      act: 'Infrastructure for Jobs and Prosperity Act, 2015',
      summary:
        'Requires municipalities to develop and update asset management plans covering all ' +
        'municipal infrastructure including water mains. Plans must include condition assessments, ' +
        'levels of service, and lifecycle costs.',
    },
    {
      regulation: 'Environmental Compliance Approval (ECA)',
      act: 'Ontario Water Resources Act (R.S.O. 1990, c. O.40)',
      summary:
        'MECP approval required for new watermain installations, pumping stations, and ' +
        'major rehabilitation works. Routine replacements may qualify for Municipal Class EA ' +
        'self-filing process (Schedule A or A+).',
    },
  ],

  inspectionMethods: [
    {
      method: 'CCTV Inspection (Closed Circuit Television)',
      applicability: 'Post-rehabilitation inspection; large-diameter transmission mains (>300 mm)',
      description:
        'Remote-controlled camera deployed inside the pipe records video of internal condition. ' +
        'Defect coding per NASSCO PACP standards (Pipeline Assessment and Certification Program). ' +
        'Toronto Water uses CCTV as mandatory post-CIPP lining quality verification (ECS TS 7.60).',
      outputs: ['Defect coding log', 'Video recording', 'Condition grade (1–5)'],
      equipment: 'Self-propelled CCTV crawler or tractor-mounted camera',
      notes:
        'Machine learning tools (e.g., WSP PipeTube) now automate defect identification ' +
        "from CCTV video on Toronto's CIPP inspection program.",
    },
    {
      method: 'Acoustic Leak Detection',
      applicability: 'Distribution mains (all diameters); transmission mains (EchoWave for large diameter)',
      description:
        'Acoustic sensors placed on hydrants and valves detect vibration signatures of pipe leaks. ' +
        'Correlators compute leak position based on time-of-arrival difference between sensor pairs. ' +
        'EchoWave technology by Echologics is used on Toronto\'s large-diameter PCCP transmission mains ' +
        '(16" to 90" diameter; >60 miles of transmission main inspected globally).',
      outputs: ['Leak location (within ±1 m)', 'Leak severity estimate (flow rate)', 'Survey report'],
      standards: 'AWWA M36 (Water Audits and Loss Control Programs)',
    },
    {
      method: 'Hydrostatic Pressure Testing',
      applicability: 'All new watermain installations before commissioning (mandatory per OPSS.MUNI 441)',
      description:
        'New or repaired main is pressurized to test pressure and held for minimum 2 hours. ' +
        'Pressure drop and volume of make-up water measured against leakage allowance formula.',
      testPressure: '1.5× design working pressure or 1 035 kPa (150 psi), whichever is greater',
      duration: '2 hours minimum (OPSS.MUNI 441)',
      leakageFormula: 'L = ND√P / 7 400 (AWWA C600); L = litres/hour, N = joints, D = diameter mm, P = pressure kPa',
      standard: 'AWWA C600 (DI pipe); AWWA C605 (PVC pipe); OPSS.MUNI 441',
    },
    {
      method: 'Cathodic Protection Survey',
      applicability: 'Ductile iron and steel pipe in corrosive soils',
      description:
        'Impressed current or sacrificial anode cathodic protection systems protect metallic pipe ' +
        'from external corrosion. Annual pipe-to-soil potential surveys (close-interval survey) ' +
        'verify system is operating within protective range (−0.85 V CSE criterion).',
      frequency: 'Annual pipe-to-soil potential readings; 3–5 year close-interval survey',
      criterionVoltage: '−850 mV (copper-sulfate electrode) protective potential',
      standard: 'NACE SP0169 — Control of External Corrosion on Underground Metallic Piping',
      torontoApplication:
        'Toronto ECS TS 441: cathodic protection required for DI pipe in soils with ' +
        'resistivity < 2 000 ohm-cm. Sacrificial magnesium anodes installed at ~10 m intervals.',
    },
    {
      method: 'Acoustic Emission (AE) / Pipe Wall Condition Assessment',
      applicability: 'Prestressed concrete cylinder pipe (PCCP) transmission mains',
      description:
        'Hydrophone deployed inside flowing main detects high-frequency acoustic emissions from ' +
        'wire breaks in PCCP. Broken wire count indicates remaining structural capacity.',
      outputs: ['Wire break count per pipe segment', 'Failure risk ranking', 'Replacement priority'],
      notes: 'Non-interrupting inspection (main remains in service during testing).',
    },
    {
      method: 'Leak Noise Correlation (Listening Survey)',
      applicability: 'Distribution mains; routine system-wide survey',
      description:
        'Ground microphones or hydrant listening equipment detect sound of water escaping pipe wall. ' +
        'Frequency-based correlation locates leak between two sensor points.',
      frequency: 'Annual system-wide survey recommended (AWWA M36)',
      outputs: ['Leak location', 'Priority repair list'],
    },
    {
      method: 'Flow and Pressure Monitoring',
      applicability: 'District metered areas (DMAs); pressure zone management',
      description:
        'Permanent or temporary data loggers on mains record pressure and flow. ' +
        'Minimum night flow (MNF) analysis identifies unexplained leakage in a DMA.',
      standard: 'AWWA M36 — Water Audits and Loss Control Programs',
      outputs: ['Non-revenue water (NRW) volume', 'DMA infrastructure leakage index (ILI)'],
    },
  ],

  disinfectionProtocol: {
    standard: 'AWWA C651 (Disinfecting Water Mains)',
    chlorineDose_mg_L: 25,
    contactTime_hours: 24,
    maxHoldTime_hours: 32,
    flushTarget_mg_L: 2.0,
    bacteriologicalVerification:
      'Two consecutive sets of samples (24 h apart) showing absence of total coliforms',
    notes:
      'After flushing, residual chlorine in released water must not exceed 2.0 mg/L free chlorine ' +
      'before discharge to municipal storm system (may require neutralization).',
  },
};

// ---------------------------------------------------------------------------
// Tab 5 — History
// Historical data about Toronto's water system
// ---------------------------------------------------------------------------

export const WATERMAIN_HISTORY = {
  title: 'History',
  description:
    'Historical record of Toronto\'s water supply system, pipe age demographics, break trends, ' +
    'and capital replacement program milestones.',

  systemTimeline: [
    {
      period: 'Pre-1843',
      event: 'Manual water supply',
      description:
        'Water carters distributed water drawn manually from Lake Ontario, streams, and wells. ' +
        'No piped distribution system existed.',
    },
    {
      period: '1843 – 1872',
      event: 'Furniss Works (private water company)',
      description:
        'First piped water supply in Toronto operated by private company. Distribution via ' +
        'wood-stave and early cast-iron pipes.',
    },
    {
      period: '1873',
      event: 'City takes over water supply',
      description:
        'City of Toronto assumes control of the water system. Expansion of cast-iron pipe network begins.',
    },
    {
      period: '1878',
      event: 'Major infrastructure expansion',
      description:
        'Copp Clark & Co. city plan of 1878 documents watermains network. ' +
        '48-inch wood stave pipe crossing Toronto Island; 36-inch cast-iron main to mainland. ' +
        'Earliest surviving watermain segments date from this era.',
    },
    {
      period: '1910 – 1939',
      event: 'R.C. Harris Water Treatment Plant era',
      description:
        'Major transmission infrastructure built to serve expanding city. ' +
        'Cast-iron pipe predominates. Arthur Goss photographs document the water works construction.',
    },
    {
      period: '1950s – 1960s',
      event: 'Rapid expansion — thin-wall cast iron',
      description:
        'Post-war suburban expansion drove rapid watermain installation. ' +
        'Thin-wall cast-iron pipes installed across former Etobicoke, North York, and Scarborough. ' +
        'Projected design life: 80 years. These pipes are now at or beyond end of design life.',
    },
    {
      period: '1970s – 1980s',
      event: 'Transition to ductile iron and PVC',
      description:
        'Ductile iron (AWWA C151) replaces grey cast iron for new installations. ' +
        'PVC pipe introduced for smaller-diameter distribution mains.',
    },
    {
      period: '2007',
      event: 'Accelerated replacement program',
      description:
        'City Council allocates $87.7 million to begin systematic replacement of aging pipes, ' +
        'following a period of approximately 1 800 watermain breaks per year.',
    },
    {
      period: '2014',
      event: 'Break frequency at modern high',
      description:
        'Approximately 1 800 watermain breaks recorded. Prompted expanded capital investment.',
    },
    {
      period: '2020',
      event: 'Break frequency reduced to 681',
      description:
        'Significant reduction in annual breaks attributed to capital investment in pipe replacement ' +
        'and CIPP rehabilitation. 35–50 km replaced annually; 30–40 km CIPP-lined annually.',
    },
    {
      period: '2020 – 2030',
      event: '10-Year Capital Plan ($2.2 billion)',
      description:
        'In December 2020, Council approved $2.2 billion for water distribution capital improvements ' +
        'over the 2021–2030 period. Primary focus: watermain replacement and lead service renewal.',
    },
    {
      period: '2025 – 2034',
      event: 'Current 10-Year Capital Budget ($8.924 billion, all Toronto Water)',
      description:
        'Total Toronto Water capital plan of $8.924 billion including $728 million in 2025 alone. ' +
        '$5.429 billion allocated to aging linear watermain and sewer infrastructure. ' +
        'Target: infrastructure backlog reduced to <1% of total asset value.',
      source: 'https://www.toronto.ca/wp-content/uploads/2025/04/8dab-2025-Public-Book-TW-V1.pdf',
    },
  ],

  pipeAgeDemographics: {
    totalLength_km: 6100,
    averageAge_years: 61,
    ageDistribution: [
      { bracket: '0 – 30 years', percentage: 22, notes: 'Recently replaced or new development' },
      { bracket: '31 – 60 years', percentage: 42, notes: 'Approaching end of design life for thin-wall CI' },
      { bracket: '61 – 80 years', percentage: 22, notes: 'At or past design life; highest break risk' },
      { bracket: '80 – 100 years', percentage: 11, notes: 'Critical condition; priority replacement' },
      { bracket: '> 100 years', percentage: 13, notes: 'Extreme age; some sections from pre-1920 era' },
    ],
    dominantMaterial: 'Cast iron (CI) — approximately 71% of total network',
    secondMaterial: 'Ductile iron (DI) — approximately 16%',
    source:
      'Toronto Water capital budget documents and watermain age analysis. ' +
      'https://www.toronto.ca/services-payments/water-environment/tap-water-in-toronto/',
    notes:
      'Pipes installed in the 1950s–1960s (thin-wall CI) represent highest break risk. ' +
      '24% of the network is more than 80 years old.',
  },

  breakTrends: {
    data: [
      { year: 2007, breaks: 1800, notes: 'Approximate; prompted $87.7M emergency investment' },
      { year: 2014, breaks: 1800, notes: 'Modern high-water mark for break frequency' },
      { year: 2020, breaks: 681, notes: 'Significant reduction from capital investment' },
    ],
    reductionFactors: [
      'Annual replacement of 35–50 km of highest-risk watermain',
      'Annual CIPP structural lining of 30–40 km of distribution main',
      'Targeted cathodic protection program for ductile iron in corrosive soils',
      'Predictive analytics using historical break data to prioritize replacements',
    ],
    openDataset: {
      name: 'Watermain Breaks (1990–2016)',
      url: 'https://open.toronto.ca/dataset/watermain-breaks/',
      note: '27-year dataset enabling break-frequency trend analysis by material, diameter, and age cohort.',
    },
  },

  capitalReplacementPrograms: [
    {
      program: 'Watermain Replacement Program',
      rate: '35 – 50 km per year',
      description:
        'Full open-cut replacement of highest-priority mains identified through condition ' +
        'assessment, break history, and age. Includes replacement of lead service connections.',
    },
    {
      program: 'Watermain Rehabilitation — CIPP Structural Lining',
      rate: '30 – 40 km per year',
      description:
        'Trenchless rehabilitation using cured-in-place pipe (CIPP) lining. ' +
        'Suitable for structurally sound pipe with corrosion pitting or joint deterioration. ' +
        'WSP has completed >260 km for Toronto since program inception.',
      url: 'https://www.wsp.com/en-ca/projects/city-of-toronto-watermain-rehabilitation-program',
    },
    {
      program: 'Cathodic Protection Installation',
      description:
        'Sacrificial magnesium anode installation on ductile-iron pipe sections in corrosive soils. ' +
        'Extends pipe service life by 20–30 years.',
    },
    {
      program: 'Capital Water Service Replacement Program (Lead Services)',
      rate: '~3 000 services per year (during planned road construction)',
      description:
        'Replacement of lead water service pipes from main to property line. ' +
        'Program coordinates with scheduled road and watermain capital projects.',
      url: 'https://www.toronto.ca/services-payments/water-environment/tap-water-in-toronto/lead-drinking-water/capital-water-service-replacement-program/',
    },
  ],

  stateOfGoodRepairBacklog: {
    totalBacklog_billion: 2.194,
    asOf: '2024',
    watermainSharePct: 54.1,
    description:
      'As of end of 2024, Toronto Water\'s accumulated State of Good Repair (SOGR) backlog ' +
      'is estimated at $2.194 billion. Of this, 54.1% is attributable to aging linear watermain ' +
      'and sewer infrastructure. The 2025–2034 capital plan targets reducing this backlog to ' +
      'less than 1% of total asset value.',
    source: 'Toronto Water 2025 Capital Budget — https://www.toronto.ca/legdocs/mmis/2025/ex/bgrd/backgroundfile-258492.pdf',
  },
};

// ---------------------------------------------------------------------------
// Consolidated export for sidebar panel consumption
// ---------------------------------------------------------------------------

export const INFRASTRUCTURE_SIDEBAR_TABS = [
  WATERMAIN_STANDARDS,
  WATERMAIN_NETWORK,
  WATERMAIN_DATASETS,
  WATERMAIN_INSPECTIONS,
  WATERMAIN_HISTORY,
];

export default INFRASTRUCTURE_SIDEBAR_TABS;
