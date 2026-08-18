// ============================================================
// modules/api.js
// Handles all backend communication: fetch wrapper, session
// lifecycle (start), step-up verification, admin login, and admin actions.
// ============================================================

export const API_URL = "http://127.0.0.1:8000";

let adminAccessToken = null;

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
 * Requires a valid Bearer token matching session_id and user_id.
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
 * Requires Bearer JWT matching session_id and user_id.
 */
export async function apiVerifyStepUp(sessionId, pin, accessToken) {
    const headers = { "Content-Type": "application/json" };
    if (accessToken) {
        headers["Authorization"] = `Bearer ${accessToken}`;
    }

    const response = await fetchWithTimeout(`${API_URL}/session/step-up/verify`, {
        method: "POST",
        headers,
        body: JSON.stringify({ session_id: sessionId, pin })
    }, 10000);
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Verification failed");
    }
    return response.json();
}

/**
 * Helper to obtain or reuse Admin JWT token
 */
export async function getAdminToken(adminPin) {
    if (adminAccessToken) return adminAccessToken;
    const response = await fetchWithTimeout(`${API_URL}/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ admin_pin: adminPin })
    }, 10000);
    if (!response.ok) {
        throw new Error("Admin authentication failed (invalid PIN)");
    }
    const data = await response.json();
    adminAccessToken = data.access_token;
    return adminAccessToken;
}

/**
 * POST /session/override/lock — admin force-lock.
 * Requires Admin JWT + Admin PIN.
 */
export async function apiOverrideLock(sessionId, adminPin) {
    const token = await getAdminToken(adminPin);
    return fetchWithTimeout(`${API_URL}/session/override/lock`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ session_id: sessionId, admin_pin: adminPin })
    }, 10000);
}

/**
 * POST /session/override/unlock — admin emergency unlock.
 * Requires Admin JWT + Admin PIN.
 */
export async function apiOverrideUnlock(sessionId, adminPin) {
    const token = await getAdminToken(adminPin);
    return fetchWithTimeout(`${API_URL}/session/override/unlock`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ session_id: sessionId, admin_pin: adminPin })
    }, 10000);
}

/**
 * GET /session/history — admin audit ledger.
 * Requires Admin JWT + Admin PIN header.
 */
export async function apiFetchAuditLogs(pin) {
    const token = await getAdminToken(pin);
    const response = await fetchWithTimeout(`${API_URL}/session/history`, {
        method: "GET",
        headers: {
            "X-Admin-PIN": pin,
            "Authorization": `Bearer ${token}`
        }
    }, 10000);
    if (response.status === 403) throw new Error("Invalid Security PIN or Admin Role");
    if (!response.ok) throw new Error("Server error: " + response.status);
    return response.json();
}

/**
 * GET /session/export/csv — download audit CSV.
 * Requires Admin JWT + Admin PIN header.
 */
export async function apiExportCsv(pin) {
    const token = await getAdminToken(pin);
    const response = await fetchWithTimeout(`${API_URL}/session/export/csv`, {
        method: "GET",
        headers: {
            "X-Admin-PIN": pin,
            "Authorization": `Bearer ${token}`
        }
    }, 10000);
    if (!response.ok) throw new Error("HTTP error " + response.status);
    return response.text();
}

/**
 * POST /admin/retrain — trigger ML model retraining.
 * Requires Admin JWT + Admin PIN header.
 */
export async function apiTriggerRetrain(adminPin, force = false) {
    const token = await getAdminToken(adminPin);
    const response = await fetchWithTimeout(
        `${API_URL}/admin/retrain?force=${force}`, {
            method: "POST",
            headers: {
                "X-Admin-PIN": adminPin,
                "Authorization": `Bearer ${token}`
            }
        }, 30000
    );
    if (!response.ok) throw new Error("Retrain failed: " + response.status);
    return response.json();
}
