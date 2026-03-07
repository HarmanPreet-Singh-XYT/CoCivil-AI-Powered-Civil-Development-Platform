// API client — for connecting to the Arterial backend
// Currently returns mock data; ready to switch to real API calls

const API_BASE = 'http://localhost:8000/api/v1';

/**
 * Search parcels by address
 */
export async function searchParcels(address) {
    try {
        const res = await fetch(`${API_BASE}/parcels/search?address=${encodeURIComponent(address)}`);
        if (res.ok) return await res.json();
    } catch {
        // Backend not running — return mock data
    }
    return [];
}

/**
 * Get a parcel by ID
 */
export async function getParcel(parcelId) {
    try {
        const res = await fetch(`${API_BASE}/parcels/${parcelId}`);
        if (res.ok) return await res.json();
    } catch {
        // Backend not running
    }
    return null;
}

/**
 * Get policy stack for a parcel
 */
export async function getPolicyStack(parcelId) {
    try {
        const res = await fetch(`${API_BASE}/parcels/${parcelId}/policy-stack`);
        if (res.ok) return await res.json();
    } catch {
        // Backend not running
    }
    return { parcel_id: parcelId, applicable_policies: [], citations: [] };
}

/**
 * Get overlays for a parcel
 */
export async function getParcelOverlays(parcelId) {
    try {
        const res = await fetch(`${API_BASE}/parcels/${parcelId}/overlays`);
        if (res.ok) return await res.json();
    } catch {
        // Backend not running
    }
    return { parcel_id: parcelId, overlays: [] };
}
