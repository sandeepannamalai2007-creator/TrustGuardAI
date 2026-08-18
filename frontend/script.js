// ============================================================
// script.js  —  TrustGuard AI  —  Entry Point
//
// This file is intentionally thin: it only imports modules,
// wires up session lifecycle, and coordinates the application.
//
// Module map:
//   modules/api.js      — all backend communication
//   modules/capture.js  — keystroke/mouse biometric capture
//   modules/canvas.js   — background rain, kinematics, SecOps chart
//   modules/ui.js       — DOM updates, gauges, theme, telemetry log
//   modules/secops.js   — SecOps dashboard, step-up, lock/unlock
// ============================================================

import { apiStartSession, apiSendFeatures } from "./modules/api.js";
import {
    dwellTimes, dwellTimestamps, flightTimes, flightTimestamps,
    mouseVelocities, mouseVelocityTimestamps,
    totalCharacters, clickCount, activeTypingTime,
    pushFeature, pruneOldFeatures, resetCapture,
    average, standardDeviation,
    initCapture
} from "./modules/capture.js";
import { initBgRain, initKinematicsCanvas, initSpotlightGlow, drawSecOpsChart } from "./modules/canvas.js";
import {
    updateLiveStatus, logTelemetry, setBackendStatus,
    getBackendOnline, resetBackendOnline,
    updateDashboard, showError, initTheme,
    setThreshold, getThreshold
} from "./modules/ui.js";
import {
    recordSecOpsTelemetry, showStepUpModal, hideStepUpModal,
    initStepUpModal, initAdminOverrides, initAuditLedger,
    initCsvExport, initRetrainButton, lockWorkstation as _lockWorkstation
} from "./modules/secops.js";

// -----------------------------------------------------------------------
// Session state
// -----------------------------------------------------------------------
let sessionId = null;
let accessToken = null;
let lastSecurityState = "NORMAL";
let uploadInterval = null;
let reconnectTimeout = null;
let sessionStart = Date.now();

// Bot simulator state
let botInterval = null;
let currentThreatMode = "human";

const getSessionId = () => sessionId;

// -----------------------------------------------------------------------
// Initialise theme, canvas, spotlight, modules
// -----------------------------------------------------------------------
initTheme();
initBgRain();
initKinematicsCanvas();
initSpotlightGlow();
initCapture(logTelemetry);
initStepUpModal(getSessionId);
initAdminOverrides(getSessionId, () => lockWorkstation());
initAuditLedger();
initCsvExport();
initRetrainButton();

window.addEventListener("resize", () => drawSecOpsChart([]));
document.addEventListener("DOMContentLoaded", () => drawSecOpsChart([]));

// -----------------------------------------------------------------------
// Backend connection & session lifecycle
// -----------------------------------------------------------------------
function setStatus(online, message) {
    setBackendStatus(online, message);
}

function scheduleReconnect() {
    if (reconnectTimeout) return;
    reconnectTimeout = setTimeout(() => {
        reconnectTimeout = null;
        if (!sessionId) startSession();
    }, 5000);
}

async function startSession() {
    try {
        const userIdInput = document.getElementById("userIdInput");
        const data = await apiStartSession(userIdInput?.value || "Student_01");
        sessionId = data.session_id;
        accessToken = data.access_token || null;

        logTelemetry(`Session established. ID: ${sessionId.substring(0, 8)}...${accessToken ? " (JWT Active)" : ""}`, "api");
        updateLiveStatus("Authentication session established successfully.");
        setStatus(true);

        const badge = document.getElementById("sessionStatusBadge");
        if (badge) { badge.textContent = "🟢 ACTIVE SESSION"; badge.className = "session-badge active-badge"; badge.style = ""; }
        const copyBtn = document.getElementById("copySessionBtn");
        if (copyBtn) copyBtn.style.display = "inline-block";

        const startBtn = document.getElementById("startBtn");
        const endBtn = document.getElementById("endBtn");
        if (startBtn) startBtn.disabled = true;
        if (endBtn) endBtn.disabled = false;

        if (reconnectTimeout) { clearTimeout(reconnectTimeout); reconnectTimeout = null; }
    } catch (error) {
        console.error("startSession failed:", error);
        sessionId = null;
        setStatus(false, "⚠ Can't reach authentication node — retrying...");
        logTelemetry("Connection node offline. Reconnecting...", "danger");
        scheduleReconnect();
    }
}

async function sendFeatures() {
    pruneOldFeatures();

    if (!sessionId) {
        setStatus(false);
        scheduleReconnect();
        return;
    }

    const sessionSeconds = (Date.now() - sessionStart) / 1000;
    const activeTypingSeconds = Math.max(activeTypingTime / 1000, 1);

    const featureVector = {
        session_id: sessionId,
        avg_dwell_time_ms: average(dwellTimes),
        std_dwell_time_ms: standardDeviation(dwellTimes),
        avg_flight_time_ms: average(flightTimes),
        std_flight_time_ms: standardDeviation(flightTimes),
        typing_speed_cps: totalCharacters / activeTypingSeconds,
        avg_mouse_velocity_px_s: average(mouseVelocities),
        click_count: clickCount,
        keystroke_count: totalCharacters,
        session_duration_s: sessionSeconds
    };

    try {
        const data = await apiSendFeatures(featureVector, accessToken);
        setStatus(true);

        if (data.status === "error") {
            logTelemetry("Session expired. Resetting tokens.", "danger");
            sessionId = null;
            await startSession();
            return;
        }

        if (data.explanations?.length > 0) {
            data.explanations.forEach(exp => logTelemetry(`[COMPARE] ${exp}`, "info"));
        }

        if (data.security_state && data.security_state !== lastSecurityState) {
            const alertType = data.security_state === "LOCKED" ? "danger" : "warning";
            logTelemetry(`[SECURITY STATE] Workstation state escalated to: ${data.security_state}`, alertType);
            lastSecurityState = data.security_state;
        }

        logTelemetry(`Biometrics accepted. Score returned: ${data.trust_score}% | State: ${data.security_state || "NORMAL"}`, "api");
        recordSecOpsTelemetry(data.trust_score, data.security_state);

        if (data.step_up_required) showStepUpModal();
        if (data.adaptive_threshold) setThreshold(data.adaptive_threshold);

        if (data.trust_score === 0 && totalCharacters >= 5) {
            const stdDwellVal = standardDeviation(dwellTimes);
            const stdFlightVal = standardDeviation(flightTimes);
            if (stdDwellVal < 2.0 || stdFlightVal < 2.0) {
                logTelemetry(`[SECURITY CRITICAL] Automated bot signature detected! Variance below threshold (Dwell SD: ${stdDwellVal.toFixed(2)}ms)`, "danger");
            }
        }

        if (data.security_state === "LOCKED") { lockWorkstation(); return; }

        updateDashboard(data.trust_score, dwellTimes, flightTimes, mouseVelocities,
            totalCharacters, activeTypingTime, sessionStart, average, standardDeviation);
    } catch (error) {
        console.error("sendFeatures failed:", error);
        setStatus(false, "⚠ Lost link to authentication node — retrying...");
        logTelemetry("Link timeout. Connection interrupted.", "danger");
        sessionId = null;
        scheduleReconnect();
    }
}

// -----------------------------------------------------------------------
// Workstation lockout (needs local upload/bot interval refs)
// -----------------------------------------------------------------------
function lockWorkstation() {
    _lockWorkstation(uploadInterval, botInterval, resetSession, startSession);
    uploadInterval = null;
    botInterval = null;
}

// -----------------------------------------------------------------------
// Reset session
// -----------------------------------------------------------------------
function resetSession() {
    if (uploadInterval) { clearInterval(uploadInterval); uploadInterval = null; }
    if (reconnectTimeout) { clearTimeout(reconnectTimeout); reconnectTimeout = null; }
    if (botInterval) { clearInterval(botInterval); clearTimeout(botInterval); botInterval = null; }

    const typingArea = document.getElementById("typingArea");
    if (typingArea) { typingArea.value = ""; typingArea.disabled = false; typingArea.placeholder = "Begin typing here to verify your behavioral profile..."; }

    resetCapture();
    sessionStart = Date.now();
    lastSecurityState = "NORMAL";
    currentThreatMode = "human";
    resetBackendOnline();

    const simStopBtn = document.getElementById("simStopBtn");
    const simBotBtn = document.getElementById("simBotBtn");
    const simRandBtn = document.getElementById("simRandBtn");
    const simulatorBadge = document.getElementById("simulatorBadge");
    if (simStopBtn) simStopBtn.classList.add("sim-btn-active");
    if (simBotBtn) simBotBtn.classList.remove("sim-btn-active");
    if (simRandBtn) simRandBtn.classList.remove("sim-btn-active");
    if (simulatorBadge) { simulatorBadge.textContent = "🟢 HUMAN MODE"; simulatorBadge.className = "session-badge active-badge human-badge"; simulatorBadge.style = ""; }

    // Reset stat displays
    ["dwell","flight","speed","velocity"].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = id === "speed" ? "0 cps" : id === "velocity" ? "0 px/s" : "0 ms"; });
    ["clicks"].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = "0"; });
    ["avgDwell","stdDwell","avgFlight","stdFlight"].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = "0 ms"; });
    ["avgVelocity"].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = "0 px/s"; });
    ["sessionTime","featureSessionTime"].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = "0 s"; });

    const trustScoreDisplay = document.getElementById("trustScore");
    if (trustScoreDisplay) trustScoreDisplay.textContent = "100%";
    const gaugeProgress = document.getElementById("gaugeProgress");
    if (gaugeProgress) gaugeProgress.style.strokeDashoffset = "0";
    const progressBar = document.getElementById("progressBar");
    if (progressBar) progressBar.style.width = "100%";
    const container = document.querySelector(".gauge-container");
    if (container) { container.classList.remove("genuine-gauge","warning-gauge","suspicious-gauge"); container.classList.add("genuine-gauge"); }
    const alertCard = document.getElementById("alertCard");
    if (alertCard) { alertCard.classList.remove("genuine-alert","warning-alert","suspicious-alert"); alertCard.classList.add("genuine-alert"); }
    const alertText = document.getElementById("alertText");
    if (alertText) alertText.textContent = "✔ Genuine User";

    const feed = document.getElementById("telemetryFeed");
    if (feed) feed.innerHTML = '<div class="feed-entry feed-system">[SYSTEM] Awaiting keystroke and mouse kinematics...</div>';
    logTelemetry("Security session metrics re-initialized.", "system");
}

// -----------------------------------------------------------------------
// Button wiring
// -----------------------------------------------------------------------
const startBtn = document.getElementById("startBtn");
const endBtn = document.getElementById("endBtn");
const resetBtn = document.getElementById("resetBtn");
const exportBtn = document.getElementById("exportBtn");
const policySelect = document.getElementById("policySelect");
const copySessionBtn = document.getElementById("copySessionBtn");

if (startBtn) {
    startBtn.addEventListener("click", async () => {
        resetSession();
        if (startBtn) startBtn.disabled = true;
        if (endBtn) endBtn.disabled = false;
        await startSession();
        if (uploadInterval) clearInterval(uploadInterval);
        uploadInterval = setInterval(sendFeatures, 5000);
        logTelemetry("Continuous authentication scanning activated.", "system");
    });
}

if (resetBtn) {
    resetBtn.addEventListener("click", () => {
        resetSession();
        if (startBtn) startBtn.disabled = false;
        if (endBtn) endBtn.disabled = true;
    });
}

if (exportBtn) {
    exportBtn.addEventListener("click", () => {
        const sessionSeconds = (Date.now() - sessionStart) / 1000;
        const data = {
            session_id: sessionId,
            avg_dwell_time_ms: average(dwellTimes),
            std_dwell_time_ms: standardDeviation(dwellTimes),
            avg_flight_time_ms: average(flightTimes),
            std_flight_time_ms: standardDeviation(flightTimes),
            typing_speed_cps: totalCharacters / Math.max(sessionSeconds, 1),
            avg_mouse_velocity_px_s: average(mouseVelocities),
            click_count: clickCount,
            session_duration_s: sessionSeconds
        };
        const blob = new Blob([JSON.stringify(data, null, 4)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a"); a.href = url; a.download = "trustguard_session.json"; a.click();
        URL.revokeObjectURL(url);
        logTelemetry("Exported session biometrics vector to JSON.", "system");
    });
}

if (endBtn) {
    endBtn.addEventListener("click", () => {
        if (uploadInterval) { clearInterval(uploadInterval); uploadInterval = null; }
        if (reconnectTimeout) { clearTimeout(reconnectTimeout); reconnectTimeout = null; }
        sessionId = null;
        if (startBtn) startBtn.disabled = false;
        if (endBtn) endBtn.disabled = true;
        const badge = document.getElementById("sessionStatusBadge");
        if (badge) { badge.textContent = "🔴 SESSION TERMINATED"; badge.className = "session-badge"; badge.style.background = "rgba(239,68,68,0.1)"; badge.style.border = "1px solid var(--clr-suspicious)"; badge.style.color = "var(--clr-suspicious)"; }
        const typingArea = document.getElementById("typingArea");
        if (typingArea) { typingArea.disabled = true; typingArea.placeholder = "[SESSION TERMINATED] Start session to resume continuous monitoring."; }
        logTelemetry("Continuous authentication monitoring terminated.", "system");
    });
}

if (policySelect) {
    policySelect.addEventListener("change", (e) => {
        const val = e.target.value;
        if (val === "strict") { setThreshold(75); logTelemetry("Security Policy escalated to Strict (75% Threshold).", "warning"); }
        else if (val === "relaxed") { setThreshold(30); logTelemetry("Security Policy reduced to Relaxed (30% Threshold).", "info"); }
        else { setThreshold(50); logTelemetry("Security Policy reset to Balanced (50% Threshold).", "system"); }
        const rawScore = parseInt(document.getElementById("trustScore")?.textContent);
        if (!isNaN(rawScore)) updateDashboard(rawScore, dwellTimes, flightTimes, mouseVelocities, totalCharacters, activeTypingTime, sessionStart, average, standardDeviation);
    });
}

if (copySessionBtn) {
    copySessionBtn.addEventListener("click", () => {
        if (sessionId) {
            navigator.clipboard.writeText(sessionId);
            copySessionBtn.textContent = "✔ Copied!";
            updateLiveStatus("Session ID copied to clipboard.");
            setTimeout(() => { copySessionBtn.textContent = "📋 Copy ID"; }, 2000);
        }
    });
}

// -----------------------------------------------------------------------
// Threat & Bot Simulator
// -----------------------------------------------------------------------
const simStopBtn = document.getElementById("simStopBtn");
const simBotBtn = document.getElementById("simBotBtn");
const simRandBtn = document.getElementById("simRandBtn");
const simulatorBadge = document.getElementById("simulatorBadge");
const typingArea = document.getElementById("typingArea");

function setThreatMode(mode) {
    if (currentThreatMode === mode) return;
    currentThreatMode = mode;
    if (botInterval) { clearInterval(botInterval); clearTimeout(botInterval); botInterval = null; }
    if (simStopBtn) simStopBtn.classList.remove("sim-btn-active");
    if (simBotBtn) simBotBtn.classList.remove("sim-btn-active");
    if (simRandBtn) simRandBtn.classList.remove("sim-btn-active");
    if (simulatorBadge) simulatorBadge.classList.remove("human-badge","bot-badge","attacker-badge");

    if (mode === "human") {
        if (simStopBtn) simStopBtn.classList.add("sim-btn-active");
        if (simulatorBadge) { simulatorBadge.textContent = "🟢 HUMAN MODE"; simulatorBadge.classList.add("human-badge"); }
        if (typingArea) { typingArea.disabled = false; typingArea.placeholder = "Begin typing here to train or verify your behavioral profile..."; }
        logTelemetry("Simulator deactivated. Restored Human control.", "system");
    } else if (mode === "bot") {
        if (simBotBtn) simBotBtn.classList.add("sim-btn-active");
        if (simulatorBadge) { simulatorBadge.textContent = "🤖 SCRIPT BOT"; simulatorBadge.classList.add("bot-badge"); }
        if (typingArea) { typingArea.disabled = true; typingArea.placeholder = "[SIMULATION RUNNING] Script Bot automated keystrokes typing..."; }
        logTelemetry("Simulator activated: Script Bot timing spoofing.", "warning");
        if (!sessionId && startBtn) startBtn.click();
        const text = "trustguard_bot_timing_evasion_attack_vector_spoof";
        let index = 0;
        botInterval = setInterval(() => {
            if (currentThreatMode !== "bot") return;
            if (index >= text.length) index = 0;
            const char = text[index++];
            if (typingArea) typingArea.value += char;
            const dwell = 100.0 + (Math.random() * 0.4 - 0.2);
            const flight = 100.0 + (Math.random() * 0.4 - 0.2);
            pushFeature(dwellTimes, dwellTimestamps, dwell, 20);
            pushFeature(flightTimes, flightTimestamps, flight, 20);
            logTelemetry(`[BOT] KEY_UP [${char}] | Dwell: ${dwell.toFixed(1)}ms | Flight: ${flight.toFixed(1)}ms`, "danger");
        }, 120);
    } else if (mode === "attacker") {
        if (simRandBtn) simRandBtn.classList.add("sim-btn-active");
        if (simulatorBadge) { simulatorBadge.textContent = "⚠️ ERRATIC ATTACKER"; simulatorBadge.classList.add("attacker-badge"); }
        if (typingArea) { typingArea.disabled = true; typingArea.placeholder = "[SIMULATION RUNNING] Erratic Attacker typing simulation..."; }
        logTelemetry("Simulator activated: Erratic Attacker (high-variance anomaly).", "warning");
        if (!sessionId && startBtn) startBtn.click();
        const text = "erratic_attack_payload_chaos";
        let index = 0;
        const typeNext = () => {
            if (currentThreatMode !== "attacker") return;
            if (index >= text.length) index = 0;
            const char = text[index++];
            if (typingArea) typingArea.value += char;
            const dwell = 500.0 + (Math.random() * 800.0);
            const flight = 50.0 + (Math.random() * 150.0);
            pushFeature(dwellTimes, dwellTimestamps, dwell, 20);
            pushFeature(flightTimes, flightTimestamps, flight, 20);
            logTelemetry(`[ATTACKER] KEY_UP [${char}] | Dwell: ${dwell.toFixed(0)}ms | Flight: ${flight.toFixed(0)}ms`, "warning");
            botInterval = setTimeout(typeNext, 150 + Math.random() * 450);
        };
        botInterval = setTimeout(typeNext, 200);
    }
}

if (simStopBtn) simStopBtn.addEventListener("click", () => setThreatMode("human"));
if (simBotBtn) simBotBtn.addEventListener("click", () => setThreatMode("bot"));
if (simRandBtn) simRandBtn.addEventListener("click", () => setThreatMode("attacker"));

// -----------------------------------------------------------------------
// Animated loader dismiss
// -----------------------------------------------------------------------
window.addEventListener("DOMContentLoaded", () => {
    const loader = document.getElementById("appLoader");
    const wrapper = document.getElementById("dashboardWrapper");
    setTimeout(() => {
        if (loader) loader.classList.add("loader-fade-out");
        if (wrapper) wrapper.classList.add("dashboard-visible");
        setTimeout(() => { if (loader?.parentNode) loader.parentNode.removeChild(loader); }, 800);
        logTelemetry("Workstation initialized. Zero-trust continuous monitoring offline. Click 'Start Session' to begin.", "system");
    }, 3000);
});