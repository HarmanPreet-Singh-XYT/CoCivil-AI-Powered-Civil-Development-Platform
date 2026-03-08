// API client — for connecting to the Arterial backend

const API_BASE = '/api/v1';

function authHeaders() {
    const token = localStorage.getItem('token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}

function getErrorMessage(data, status) {
    if (typeof data?.detail === 'string' && data.detail.trim()) return data.detail;
    if (Array.isArray(data?.detail) && data.detail.length > 0) {
        const messages = data.detail
            .map((item) => (typeof item === 'string' ? item.trim() : item?.msg?.trim?.() || ''))
            .filter(Boolean);
        if (messages.length > 0) return messages.join('; ');
    }
    if (typeof data?.error === 'string' && data.error.trim()) return data.error;
    if (typeof data?.message === 'string' && data.message.trim()) return data.message;
    return `API returned ${status}`;
}

function isAbortError(error) {
    return error?.name === 'AbortError';
}

async function apiFetch(url, options = {}) {
    const res = await fetch(url, { ...options, headers: { ...authHeaders(), ...options.headers } });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        const error = new Error(getErrorMessage(data, res.status));
        error.status = res.status;
        error.data = data;
        throw error;
    }
    return data;
}

// ─── Auth ───

export async function login({ email, password }) {
    return apiFetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        body: JSON.stringify({ email, password }),
    });
}

export async function register({ email, password, name, organization_name }) {
    return apiFetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        body: JSON.stringify({ email, password, name, organization_name }),
    });
}

// ─── Parcels ───

export async function searchParcels(address) {
    try {
        return await apiFetch(`${API_BASE}/parcels/search?address=${encodeURIComponent(address)}`);
    } catch {
        return [];
    }
}

export async function getParcel(parcelId, options = {}) {
    try {
        return await apiFetch(`${API_BASE}/parcels/${parcelId}`, options);
    } catch (error) {
        if (isAbortError(error)) throw error;
        return null;
    }
}

export async function getPolicyStack(parcelId, options = {}) {
    try {
        return await apiFetch(`${API_BASE}/parcels/${parcelId}/policy-stack`, options);
    } catch (error) {
        if (isAbortError(error)) throw error;
        return { parcel_id: parcelId, applicable_policies: [], citations: [] };
    }
}

export async function getParcelOverlays(parcelId, options = {}) {
    try {
        return await apiFetch(`${API_BASE}/parcels/${parcelId}/overlays`, options);
    } catch (error) {
        if (isAbortError(error)) throw error;
        return { parcel_id: parcelId, overlays: [] };
    }
}

export async function getParcelZoningAnalysis(parcelId, options = {}) {
    try {
        return await apiFetch(`${API_BASE}/parcels/${parcelId}/zoning-analysis`, options);
    } catch (error) {
        if (isAbortError(error)) throw error;
        return null;
    }
}

export async function getNearbyApplications(parcelId, options = {}) {
    try {
        return await apiFetch(`${API_BASE}/parcels/${parcelId}/nearby-applications`, options);
    } catch (error) {
        if (isAbortError(error)) throw error;
        return { parcel_id: parcelId, applications: [], total: 0 };
    }
}

export async function getParcelFinancialSummary(parcelId, options = {}) {
    try {
        return await apiFetch(`${API_BASE}/parcels/${parcelId}/financial-summary`, options);
    } catch (error) {
        if (isAbortError(error)) throw error;
        return null;
    }
}

// ─── Assistant ───

export async function parseModel(text, currentParams = null, zoneCode = null, lotAreaM2 = null) {
    const payload = { text, current_params: currentParams };
    if (zoneCode) payload.zone_code = zoneCode;
    if (lotAreaM2) payload.lot_area_m2 = lotAreaM2;
    return apiFetch(`${API_BASE}/assistant/parse-model`, {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export async function chatWithAssistant({ messages, parcelContext = null, modelParams = null, zoneCode = null, uploadContext = null }) {
    const payload = { messages, parcel_context: parcelContext };
    if (modelParams) payload.model_params = modelParams;
    if (zoneCode) payload.zone_code = zoneCode;
    if (uploadContext?.length) payload.upload_context = uploadContext;
    const data = await apiFetch(`${API_BASE}/assistant/chat`, {
        method: 'POST',
        body: JSON.stringify(payload),
    });
    if (typeof data?.message !== 'string') throw new Error('Assistant response was malformed.');
    return {
        message: data.message,
        proposedAction: data.proposed_action ?? null,
        modelUpdate: data.model_update ?? null,
        contractors: data.contractors ?? [],
    };
}

// ─── Plans ───

export async function generatePlan(query, generateSubset = null) {
    const body = { query, auto_run: true };
    if (generateSubset && generateSubset !== 'all') {
        body.generate_subset = generateSubset;
    }
    return apiFetch(`${API_BASE}/plans/generate`, {
        method: 'POST',
        body: JSON.stringify(body),
    });
}

export async function getPlan(planId, options = {}) {
    return apiFetch(`${API_BASE}/plans/${planId}`, options);
}

export async function getPlanDocuments(planId, options = {}) {
    return apiFetch(`${API_BASE}/plans/${planId}/documents`, options);
}

export async function regeneratePlanDocument(planId, docType, extraContext = {}) {
    return apiFetch(`${API_BASE}/plans/${planId}/generate-document/${docType}`, {
        method: 'POST',
        body: JSON.stringify({ extra_context: extraContext }),
    });
}

export async function downloadPlanDocument(planId, docId, format = 'markdown') {
    const token = localStorage.getItem('token');
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(
        `${API_BASE}/plans/${planId}/documents/${docId}/download?format=${format}`,
        { headers }
    );
    if (!res.ok) throw new Error(`Download failed: ${res.status}`);
    return res;
}

export async function exportPlan(planId) {
    return apiFetch(`${API_BASE}/plans/${planId}/export`, {
        method: 'POST',
    });
}

// ─── Contractors ───

export async function getContractorRecommendations(planId, lat, lng) {
    try {
        return await apiFetch(`${API_BASE}/plans/${planId}/contractors?lat=${lat}&lng=${lng}`);
    } catch {
        return { contractors: [] };
    }
}

// ─── Uploads ───

export async function uploadDocument(file, options = {}) {
    const formData = new FormData();
    formData.append('file', file);
    const token = localStorage.getItem('token');
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    // Don't set Content-Type — browser sets it with boundary for multipart
    const res = await fetch(`${API_BASE}/uploads`, {
        method: 'POST',
        headers,
        body: formData,
        signal: options.signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        const error = new Error(getErrorMessage(data, res.status));
        error.status = res.status;
        error.data = data;
        throw error;
    }
    return data;
}

export async function getUpload(uploadId, options = {}) {
    return apiFetch(`${API_BASE}/uploads/${uploadId}`, options);
}

export async function getUploadPages(uploadId, options = {}) {
    return apiFetch(`${API_BASE}/uploads/${uploadId}/pages`, options);
}

export async function getUploadAnalysis(uploadId, options = {}) {
    return apiFetch(`${API_BASE}/uploads/${uploadId}/analysis`, options);
}

export async function generatePlanFromUpload(uploadId, projectName = null) {
    return apiFetch(`${API_BASE}/uploads/${uploadId}/generate-plan`, {
        method: 'POST',
        body: JSON.stringify(projectName ? { project_name: projectName } : {}),
    });
}

export async function generateResponseFromUpload(uploadId, responseType = 'correction_response') {
    return apiFetch(`${API_BASE}/uploads/${uploadId}/generate-response`, {
        method: 'POST',
        body: JSON.stringify({ response_type: responseType }),
    });
}

// ─── Infrastructure ───

export async function getNearbyPipelines(lat, lng, radius = 500, pipeType = null, options = {}) {
    try {
        let url = `${API_BASE}/infrastructure/pipelines/nearby?lat=${lat}&lng=${lng}&radius_m=${radius}`;
        if (pipeType) url += `&pipe_type=${pipeType}`;
        return await apiFetch(url, options);
    } catch (error) {
        if (isAbortError(error)) throw error;
        return { type: 'FeatureCollection', features: [] };
    }
}

export async function getNearbyBridges(lat, lng, radius = 2000, options = {}) {
    try {
        return await apiFetch(
            `${API_BASE}/infrastructure/bridges/nearby?lat=${lat}&lng=${lng}&radius_m=${radius}`,
            options
        );
    } catch (error) {
        if (isAbortError(error)) throw error;
        return { type: 'FeatureCollection', features: [] };
    }
}

export async function checkPipelineCompliance(params) {
    return apiFetch(`${API_BASE}/infrastructure/compliance/pipeline`, {
        method: 'POST',
        body: JSON.stringify(params),
    });
}

export async function checkBridgeCompliance(params) {
    return apiFetch(`${API_BASE}/infrastructure/compliance/bridge`, {
        method: 'POST',
        body: JSON.stringify(params),
    });
}

export async function parseInfraModel(text, currentParams = null, assetType = 'pipeline') {
    return apiFetch(`${API_BASE}/assistant/parse-infra-model`, {
        method: 'POST',
        body: JSON.stringify({ text, current_params: currentParams, asset_type: assetType }),
    });
}

export async function triggerWaterMainIngestion() {
    return apiFetch(`${API_BASE}/admin/ingest/water-mains`, { method: 'POST' });
}

export async function triggerSanitarySewerIngestion() {
    return apiFetch(`${API_BASE}/admin/ingest/sanitary-sewers`, { method: 'POST' });
}

export async function triggerStormSewerIngestion() {
    return apiFetch(`${API_BASE}/admin/ingest/storm-sewers`, { method: 'POST' });
}

export async function triggerBridgeIngestion() {
    return apiFetch(`${API_BASE}/admin/ingest/bridges`, { method: 'POST' });
}

// ─── Design Version Control ───

export async function createBranch(projectId, name, fromVersionId = null) {
    return apiFetch(`${API_BASE}/designs/${projectId}/branches`, {
        method: 'POST',
        body: JSON.stringify({ name, from_version_id: fromVersionId }),
    });
}

export async function listBranches(projectId) {
    try {
        return await apiFetch(`${API_BASE}/designs/${projectId}/branches`);
    } catch {
        return [];
    }
}

export async function commitVersion(branchId, { floorPlans, modelParams, message, parcelId }) {
    return apiFetch(`${API_BASE}/designs/branches/${branchId}/commit`, {
        method: 'POST',
        body: JSON.stringify({
            floor_plans: floorPlans,
            model_params: modelParams,
            message,
            parcel_id: parcelId,
        }),
    });
}

export async function listVersions(branchId) {
    try {
        return await apiFetch(`${API_BASE}/designs/branches/${branchId}/versions`);
    } catch {
        return [];
    }
}

export async function getVersion(versionId) {
    return apiFetch(`${API_BASE}/designs/versions/${versionId}`);
}

export async function getLatestVersion(branchId) {
    try {
        return await apiFetch(`${API_BASE}/designs/branches/${branchId}/latest`);
    } catch {
        return null;
    }
}
