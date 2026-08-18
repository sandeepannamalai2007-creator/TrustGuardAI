// ============================================================
// modules/api.js
// Handles all backend communication: fetch wrapper, session
// lifecycle (start), and feature submission.
// ============================================================

export const API_URL = "http://127.0.0.1:8000";

/**
 * fetch() with an AbortController timeout.
 */
export async function fetchWithTimeout(url, options = {}, timeoutMs = 10000) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await fetch(url, { ...options, signal: controller.signal });
        clearTimeout(id);
        return response;
    } catch (error) {
        clearTimeout(id);
        throw error;
    }
}

/**
 * POST /session/start — creates a new backend session and returns
 * { session_id, access_token }.
 */
export async function apiStartSession(userId = "Student_01") {
    const response = await fetchWithTimeout(API_URL + "/session/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, demo_mode: true })
    }, 10000);

    if (!response.ok) {
        throw new Error("Server responded with " + response.status);
    }
    return response.json();
}

/**
 * POST /session/features — submits a biometric feature vector.
 * Requires a valid Bearer token if JWT is active.
 */
export async function apiSendFeatures(featureVector, accessToken) {
    const headers = { "Content-Type": "application/json" };
    if (accessToken) {
        headers["Authorization"] = `Bearer ${accessToken}`;
    }

    const response = await fetchWithTimeout(`${API_URL}/session/features`, {
        method: "POST",
        headers,
        body: JSON.stringify(featureVector)
    }, 10000);

    if (!response.ok) {
        throw new Error("Server responded with " + response.status);
    }
    return response.json();
}

/**
 * POST /session/step-up/verify — submits user re-auth PIN.
 */
export async function apiVerifyStepUp(sessionId, pin) {
    const response = await fetchWithTimeout(`${API_URL}/session/step-up/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, pin })
    }, 10000);
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Verification failed");
    }
    return response.json();
}

/**
 * POST /session/override/lock — admin force-lock.
 */
export async function apiOverrideLock(sessionId, adminPin) {
    return fetchWithTimeout(`${API_URL}/session/override/lock`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, admin_pin: adminPin })
    }, 10000);
}

/**
 * POST /session/override/unlock — admin emergency unlock.
 */
export async function apiOverrideUnlock(sessionId, adminPin) {
    return fetchWithTimeout(`${API_URL}/session/override/unlock`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, admin_pin: adminPin })
    }, 10000);
}

/**
 * GET /session/history — admin audit ledger.
 */
export async function apiFetchAuditLogs(pin) {
    const response = await fetchWithTimeout(`${API_URL}/session/history`, {
        method: "GET",
        headers: { "X-Admin-PIN": pin }
    }, 10000);
    if (response.status === 403) throw new Error("Invalid Security PIN");
    if (!response.ok) throw new Error("Server error: " + response.status);
    return response.json();
}

/**
 * GET /session/export/csv — download audit CSV.
 */
export async function apiExportCsv(pin) {
    const response = await fetchWithTimeout(`${API_URL}/session/export/csv`, {
        method: "GET",
        headers: { "X-Admin-PIN": pin }
    }, 10000);
    if (!response.ok) throw new Error("HTTP error " + response.status);
    return response.text();
}

/**
 * POST /admin/retrain — trigger ML model retraining.
 */
export async function apiTriggerRetrain(adminPin, force = false) {
    const response = await fetchWithTimeout(
        `${API_URL}/admin/retrain?force=${force}`, {
            method: "POST",
            headers: { "X-Admin-PIN": adminPin }
        }, 30000
    );
    if (!response.ok) throw new Error("Retrain failed: " + response.status);
    return response.json();
}
