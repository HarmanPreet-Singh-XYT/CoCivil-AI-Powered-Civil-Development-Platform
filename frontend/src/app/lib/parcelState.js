const DEFAULT_UNRESOLVED_MESSAGE =
  'No backend parcel match was found for this address. Parcel-linked zoning, policy, and overlay data are unavailable until a parcel record is matched.';

function getDisplayAddress(location) {
  return location?.shortAddress || location?.address || 'Selected location';
}

// Preserve the full zone string when we have it, but also expose a short category label
// for compact chips and UI affordances.
function normalizeZoneCode(zoneCode) {
  if (typeof zoneCode !== 'string') return null;
  const match = zoneCode.trim().match(/^([A-Za-z]+)/);
  return match ? match[1].toUpperCase() : null;
}

export function createResolvedParcel(location, parcelMatch) {
  const zoneCode = parcelMatch?.zone_code ?? parcelMatch?.zoning ?? null;
  return {
    status: 'resolved',
    id: parcelMatch.id,
    address: getDisplayAddress(location),
    fullAddress: location?.address || getDisplayAddress(location),
    zoning: normalizeZoneCode(zoneCode),
    zoneCode,
    lotArea: Number.isFinite(parcelMatch?.lot_area_m2) ? parcelMatch.lot_area_m2 : null,
    geom: parcelMatch?.geom || null,
  };
}

export function createUnresolvedParcel(location, message = DEFAULT_UNRESOLVED_MESSAGE) {
  return {
    status: 'unresolved',
    id: null,
    address: getDisplayAddress(location),
    fullAddress: location?.address || getDisplayAddress(location),
    zoning: null,
    zoneCode: null,
    lotArea: null,
    message,
  };
}

export function buildParcelState(location, parcelMatches) {
  const firstMatch = Array.isArray(parcelMatches) ? parcelMatches[0] : null;
  if (firstMatch?.id) {
    return createResolvedParcel(location, firstMatch);
  }
  return createUnresolvedParcel(location);
}

export function isResolvedParcel(parcel) {
  return parcel?.status === 'resolved' && Boolean(parcel?.id);
}

export function isUnresolvedParcel(parcel) {
  return parcel?.status === 'unresolved';
}

export function formatParcelContext(parcel) {
  if (!isResolvedParcel(parcel)) return null;

  const parts = [`Current parcel: ${parcel.address}`];
  if (parcel.zoneCode || parcel.zoning) parts.push(`Zoning: ${parcel.zoneCode || parcel.zoning}`);
  if (Number.isFinite(parcel.lotArea)) parts.push(`Lot Area: ${parcel.lotArea}m²`);
  return parts.join(', ');
}

export { DEFAULT_UNRESOLVED_MESSAGE };
