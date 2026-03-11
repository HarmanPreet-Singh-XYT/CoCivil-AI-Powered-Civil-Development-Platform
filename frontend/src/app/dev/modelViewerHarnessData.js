export const sampleParcel = {
  type: 'Feature',
  geometry: {
    type: 'Polygon',
    coordinates: [[
      [-79.3834, 43.6530],
      [-79.3829, 43.6530],
      [-79.3829, 43.6534],
      [-79.3834, 43.6534],
      [-79.3834, 43.6530],
    ]],
  },
  properties: {
    address: '100 Queen St W, Toronto',
  },
};

export const sampleModelParams = {
  storeys: 2,
  podium_storeys: 0,
  height_m: 8,
  setback_m: 1.5,
  typology: 'mixed_use_midrise',
  footprint_coverage: 0.72,
};

export const sampleFloorPlans = {
  floor_plans: [
    {
      floor_number: 1,
      floor_label: 'Floor 1',
      rooms: [
        {
          name: 'Lobby',
          type: 'hallway',
          polygon: [[-12, -8], [12, -8], [12, 8], [-12, 8]],
          area_m2: 192,
        },
        {
          name: 'Cafe',
          type: 'dining',
          polygon: [[-10, -18], [2, -18], [2, -9], [-10, -9]],
          area_m2: 108,
        },
        {
          name: 'Office',
          type: 'office',
          polygon: [[4, -18], [14, -18], [14, -9], [4, -9]],
          area_m2: 90,
        },
      ],
      walls: [
        { start: [-14, -20], end: [14, -20], thickness_m: 0.25, type: 'exterior' },
        { start: [14, -20], end: [14, 10], thickness_m: 0.25, type: 'exterior' },
        { start: [14, 10], end: [-14, 10], thickness_m: 0.25, type: 'exterior' },
        { start: [-14, 10], end: [-14, -20], thickness_m: 0.25, type: 'exterior' },
        { start: [-12, -8], end: [12, -8], thickness_m: 0.18, type: 'interior' },
      ],
    },
    {
      floor_number: 2,
      floor_label: 'Floor 2',
      rooms: [
        {
          name: 'Suite 201',
          type: 'living',
          polygon: [[-12, -16], [0, -16], [0, 2], [-12, 2]],
          area_m2: 216,
        },
        {
          name: 'Suite 202',
          type: 'bedroom',
          polygon: [[2, -16], [14, -16], [14, 2], [2, 2]],
          area_m2: 216,
        },
        {
          name: 'Hall',
          type: 'hallway',
          polygon: [[-12, 4], [14, 4], [14, 10], [-12, 10]],
          area_m2: 156,
        },
      ],
      walls: [
        { start: [-14, -18], end: [14, -18], thickness_m: 0.25, type: 'exterior' },
        { start: [14, -18], end: [14, 12], thickness_m: 0.25, type: 'exterior' },
        { start: [14, 12], end: [-14, 12], thickness_m: 0.25, type: 'exterior' },
        { start: [-14, 12], end: [-14, -18], thickness_m: 0.25, type: 'exterior' },
        { start: [1, -16], end: [1, 2], thickness_m: 0.18, type: 'interior' },
      ],
    },
  ],
};

export const sampleBlueprintPages = [
  { page_number: 1, url: '/toronto-dark-bg.png' },
  { page_number: 2, url: '/toronto-dark-bg.png' },
];
