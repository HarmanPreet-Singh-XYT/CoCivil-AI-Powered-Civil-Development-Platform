import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildParcelState,
  createResolvedParcel,
  createUnresolvedParcel,
  formatParcelContext,
  isResolvedParcel,
  isUnresolvedParcel,
} from './parcelState.js';

test('buildParcelState returns a resolved parcel when the backend returns a match', () => {
  const parcel = buildParcelState(
    { shortAddress: '123 King St W, Toronto', address: '123 King St W, Toronto, Ontario, Canada' },
    [{ id: 'parcel-1', zone_code: 'cr', lot_area_m2: 412.5 }]
  );

  assert.equal(parcel.status, 'resolved');
  assert.equal(parcel.id, 'parcel-1');
  assert.equal(parcel.zoning, 'CR');
  assert.equal(parcel.zoneCode, 'cr');
  assert.equal(parcel.lotArea, 412.5);
  assert.equal(isResolvedParcel(parcel), true);
  assert.equal(isUnresolvedParcel(parcel), false);
});

test('buildParcelState returns an unresolved parcel when there is no backend match', () => {
  const parcel = buildParcelState(
    { shortAddress: '404 Unknown Ave, Toronto', address: '404 Unknown Ave, Toronto, Ontario, Canada' },
    []
  );

  assert.equal(parcel.status, 'unresolved');
  assert.equal(parcel.id, null);
  assert.equal(parcel.zoning, null);
  assert.equal(parcel.zoneCode, null);
  assert.match(parcel.message, /No backend parcel match/i);
  assert.equal(isResolvedParcel(parcel), false);
  assert.equal(isUnresolvedParcel(parcel), true);
});

test('formatParcelContext only includes resolved parcel data', () => {
  const resolved = createResolvedParcel(
    { shortAddress: '20 Queen St W, Toronto' },
    { id: 'parcel-2', zone_code: 'RA', lot_area_m2: 250 }
  );
  const unresolved = createUnresolvedParcel({ shortAddress: '20 Queen St W, Toronto' });

  assert.equal(
    formatParcelContext(resolved),
    'Current parcel: 20 Queen St W, Toronto, Zoning: RA, Lot Area: 250m²'
  );
  assert.equal(formatParcelContext(unresolved), null);
});
