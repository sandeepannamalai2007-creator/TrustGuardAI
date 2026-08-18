// ============================================================
// modules/secops.js
// SecOps operator dashboard: real-time telemetry, step-up
// re-authentication modal, admin force lock/unlock, ledger,
// CSV export, ML retrain trigger, and workstation lockout overlay.
// ============================================================

import { apiVerifyStepUp, apiOverrideLock, apiOverrideUnlock,
         apiFetchAuditLogs, apiExportCsv, apiTriggerRetrain } from "./api.js";
import { logTelemetry, updateLiveStatus } from "./ui.js";
import { drawSecOpsChart } from "./canvas.js";

// -----------------------------------------------------------------------
// SecOps telemetry history & counter badges
// -----------------------------------------------------------------------
let secopsHistory = [100];

export function recordSecOpsTelemetry(score, state) {
    secopsHistory.push(score);
    if (secopsHistory.length > 30) secopsHistory.shift();

    const activeBadge = document.getElementById("secopsActiveBadge");
    const warningBadge = document.getElementById("secopsWarningBadge");
    const lockedBadge = document.getElementById("secopsLockedBadge");

    if (state === "LOCKED") {
        if (activeBadge) activeBadge.textContent = "ACTIVE: 0";
        if (warningBadge) warningBadge.textContent = "WARNING: 0";
        if (lockedBadge) lockedBadge.textContent = "LOCKED: 1";
    } else if (state === "SUSPICIOUS" || state === "HIGH_RISK") {
        if (activeBadge) activeBadge.textContent = "ACTIVE: 0";
        if (warningBadge) warningBadge.textContent = "WARNING: 1";
        if (lockedBadge) lockedBadge.textContent = "LOCKED: 0";
    } else {
        if (activeBadge) activeBadge.textContent = "ACTIVE: 1";
        if (warningBadge) warningBadge.textContent = "WARNING: 0";
        if (lockedBadge) lockedBadge.textContent = "LOCKED: 0";
    }
    drawSecOpsChart(secopsHistory);
}

// -----------------------------------------------------------------------
// Step-Up Re-Authentication Modal
// -----------------------------------------------------------------------
export function showStepUpModal() {
    const modal = document.getElementById("stepUpModal");
    if (modal) {
        modal.style.display = "flex";
        logTelemetry("[STEP-UP AUTH] Re-authentication challenge presented to user.", "warning");
        updateLiveStatus("Security warning: Step-up re-authentication required.");
    }
}

export function hideStepUpModal() {
    const modal = document.getElementById("stepUpModal");
    if (modal) modal.style.display = "none";
}

export function initStepUpModal(getSessionId, getAccessToken) {
    const verifyStepUpBtn = document.getElementById("verifyStepUpBtn");
    const stepUpPinInput = document.getElementById("stepUpPinInput");
    const stepUpErrorMsg = document.getElementById("stepUpErrorMsg");

    if (!verifyStepUpBtn) return;

    verifyStepUpBtn.addEventListener("click", async () => {
        const pin = stepUpPinInput ? stepUpPinInput.value.trim() : "";
        if (!pin) {
            if (stepUpErrorMsg) stepUpErrorMsg.textContent = "Please enter a PIN.";
            return;
        }
        try {
            await apiVerifyStepUp(getSessionId(), pin, getAccessToken ? getAccessToken() : null);
            hideStepUpModal();
            if (stepUpPinInput) stepUpPinInput.value = "";

            if (stepUpErrorMsg) stepUpErrorMsg.textContent = "";
            logTelemetry("[STEP-UP AUTH] Re-authentication successful! Trust state restored.", "success");
            updateLiveStatus("Step-Up verification successful. Normal security status restored.");
        } catch (error) {
            if (stepUpErrorMsg) stepUpErrorMsg.textContent = "❌ " + error.message;
            logTelemetry("Step-Up verification failed: " + error.message, "danger");
        }
    });
}

// -----------------------------------------------------------------------
// Admin force lock / unlock
// -----------------------------------------------------------------------
export function initAdminOverrides(getSessionId, onLock) {
    const forceLockBtn = document.getElementById("forceLockBtn");
    if (forceLockBtn) {
        forceLockBtn.addEventListener("click", async () => {
            if (!getSessionId()) return;
            try {
                const pin = prompt("Enter Admin PIN to force lock:");
                if (!pin) return;
                const response = await apiOverrideLock(getSessionId(), pin);
                if (response.ok) {
                    onLock();
                    logTelemetry("[ADMIN OVERRIDE] Workstation forcibly locked by admin.", "danger");
                }
            } catch (err) {
                console.error("Force lock error:", err);
            }
        });
    }

    const forceUnlockBtn = document.getElementById("forceUnlockBtn");
    if (forceUnlockBtn) {
        forceUnlockBtn.addEventListener("click", async () => {
            if (!getSessionId()) return;
            try {
                const pin = prompt("Enter Admin PIN to force unlock:");
                if (!pin) return;
                const response = await apiOverrideUnlock(getSessionId(), pin);
                if (response.ok) {
                    hideStepUpModal();
                    logTelemetry("[ADMIN OVERRIDE] Admin emergency unlock granted.", "success");
                    updateLiveStatus("Admin emergency unlock granted.");
                }
            } catch (err) {
                console.error("Force unlock error:", err);
            }
        });
    }
}

// -----------------------------------------------------------------------
// Security Audit Ledger
// -----------------------------------------------------------------------
function renderAuditLogs(logs) {
    const auditTableBody = document.getElementById("auditTableBody");
    if (!auditTableBody) return;

    if (logs.length === 0) {
        auditTableBody.innerHTML = `<tr><td colspan="8" class="text-center" style="font-family: var(--font-primary); color: var(--text-muted);">No biometrics records found in the database.</td></tr>`;
        return;
    }

    auditTableBody.innerHTML = "";
    logs.forEach(log => {
        const row = document.createElement("tr");
        let datePart = "", timePart = "";
        if (log.timestamp) {
            const parts = log.timestamp.split("T");
            datePart = parts[0];
            timePart = parts[1] ? parts[1].substring(0, 8) : "";
        }
        let scoreClass = log.trust_score >= 80 ? "feed-success" : log.trust_score >= 50 ? "feed-warning" : "feed-danger";
        row.innerHTML = `
            <td><span class="feed-system">${datePart}</span> ${timePart}</td>
            <td><span class="feed-info">${log.student_id}</span></td>
            <td><span class="feed-system">${log.session_id}</span></td>
            <td><span class="${scoreClass}">${log.trust_score.toFixed(0)}%</span></td>
            <td>${log.decision_score.toFixed(3)}</td>
            <td>${log.avg_dwell.toFixed(1)} ms</td>
            <td>${log.avg_flight.toFixed(1)} ms</td>
            <td>${log.typing_speed.toFixed(2)} cps</td>
        `;
        auditTableBody.appendChild(row);
    });
}

export function initAuditLedger() {
    const ledgerLockPanel = document.getElementById("ledgerLockPanel");
    const ledgerTablePanel = document.getElementById("ledgerTablePanel");
    const adminPinInput = document.getElementById("adminPinInput");
    const unlockLedgerBtn = document.getElementById("unlockLedgerBtn");
    const refreshLedgerBtn = document.getElementById("refreshLedgerBtn");
    const lockLedgerBtn = document.getElementById("lockLedgerBtn");
    const ledgerBadge = document.getElementById("ledgerBadge");
    const ledgerErrorMsg = document.getElementById("ledgerErrorMsg");

    let unlockedPin = null;

    async function fetchLogs(pin) {
        if (ledgerErrorMsg) ledgerErrorMsg.textContent = "";
        try {
            const logs = await apiFetchAuditLogs(pin);
            renderAuditLogs(logs);
            unlockedPin = pin;
            if (ledgerLockPanel) ledgerLockPanel.classList.add("hidden-ledger-content");
            if (ledgerTablePanel) ledgerTablePanel.classList.remove("hidden-ledger-content");
            if (ledgerBadge) { ledgerBadge.textContent = "UNLOCKED"; ledgerBadge.classList.remove("suspicious-badge"); ledgerBadge.classList.add("human-badge"); }
            logTelemetry("Database security audit ledger successfully decrypted.", "success");
        } catch (error) {
            if (ledgerErrorMsg) ledgerErrorMsg.textContent = "❌ " + error.message;
            logTelemetry("Database access blocked: Unauthorized PIN.", "danger");
        }
    }

    function lockLedger() {
        unlockedPin = null;
        if (adminPinInput) adminPinInput.value = "";
        if (ledgerErrorMsg) ledgerErrorMsg.textContent = "";
        if (ledgerLockPanel) ledgerLockPanel.classList.remove("hidden-ledger-content");
        if (ledgerTablePanel) ledgerTablePanel.classList.add("hidden-ledger-content");
        if (ledgerBadge) { ledgerBadge.textContent = "LOCKED"; ledgerBadge.classList.remove("human-badge"); ledgerBadge.classList.add("suspicious-badge"); }
        logTelemetry("Security audit ledger locked.", "system");
    }

    if (unlockLedgerBtn) unlockLedgerBtn.addEventListener("click", () => { const pin = adminPinInput?.value.trim(); if (!pin) { if (ledgerErrorMsg) ledgerErrorMsg.textContent = "Please enter a PIN."; return; } fetchLogs(pin); });
    if (adminPinInput) adminPinInput.addEventListener("keydown", (e) => { if (e.key === "Enter") unlockLedgerBtn?.click(); });
    if (refreshLedgerBtn) refreshLedgerBtn.addEventListener("click", () => { if (unlockedPin) fetchLogs(unlockedPin); });
    if (lockLedgerBtn) lockLedgerBtn.addEventListener("click", lockLedger);
}

// -----------------------------------------------------------------------
// CSV Export
// -----------------------------------------------------------------------
export function initCsvExport() {
    const exportCsvBtn = document.getElementById("exportCsvBtn");
    if (!exportCsvBtn) return;

    exportCsvBtn.addEventListener("click", async () => {
        try {
            const pin = prompt("Enter Admin PIN to export CSV:");
            if (!pin) return;
            const csvText = await apiExportCsv(pin);
            const blob = new Blob([csvText], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "trustguard_audit_report.csv";
            a.click();
            URL.revokeObjectURL(url);
            logTelemetry("[COMPLIANCE] Exported security audit ledger report to CSV.", "success");
        } catch (err) {
            logTelemetry("CSV Export failed: " + err.message, "danger");
        }
    });
}

// -----------------------------------------------------------------------
// ML Retrain Trigger
// -----------------------------------------------------------------------
export function initRetrainButton() {
    const retrainBtn = document.getElementById("retrainBtn");
    if (!retrainBtn) return;

    retrainBtn.addEventListener("click", async () => {
        const pin = prompt("Enter Admin PIN to trigger model retraining:");
        if (!pin) return;
        retrainBtn.disabled = true;
        retrainBtn.textContent = "Retraining...";
        try {
            const result = await apiTriggerRetrain(pin);
            logTelemetry(`[ML RETRAIN] ${result.message}`, result.triggered ? "success" : "info");
        } catch (err) {
            logTelemetry("Retrain failed: " + err.message, "danger");
        } finally {
            retrainBtn.disabled = false;
            retrainBtn.textContent = "🔄 Retrain Model";
        }
    });
}

// -----------------------------------------------------------------------
// Workstation lockout overlay
// -----------------------------------------------------------------------
export function lockWorkstation(uploadInterval, botInterval, resetSession, startSession) {
    console.warn("🔒 WORKSTATION LOCKED!");
    if (uploadInterval) clearInterval(uploadInterval);
    if (botInterval) clearInterval(botInterval);

    const typingArea = document.getElementById("typingArea");
    const simStopBtn = document.getElementById("simStopBtn");
    const simBotBtn = document.getElementById("simBotBtn");
    const simRandBtn = document.getElementById("simRandBtn");

    if (typingArea) { typingArea.value = ""; typingArea.disabled = true; typingArea.placeholder = "🔴 WORKSTATION LOCKED - Biometrics Policy Violated"; }
    if (simStopBtn) simStopBtn.disabled = true;
    if (simBotBtn) simBotBtn.disabled = true;
    if (simRandBtn) simRandBtn.disabled = true;

    let lockOverlay = document.getElementById("securityLockOverlay");
    if (!lockOverlay) {
        lockOverlay = document.createElement("div");
        lockOverlay.id = "securityLockOverlay";
        Object.assign(lockOverlay.style, {
            position: "fixed", top: "0", left: "0", width: "100vw", height: "100vh",
            backgroundColor: "rgba(8, 8, 12, 0.98)", backdropFilter: "blur(12px)",
            zIndex: "999999", display: "flex", flexDirection: "column",
            justifyContent: "center", alignItems: "center",
            color: "#ff0055", fontFamily: "'Outfit', sans-serif", textAlign: "center"
        });
        lockOverlay.innerHTML = `
            <div style="padding:50px;border:2px solid #ff0055;border-radius:16px;background:rgba(255,0,85,0.04);box-shadow:0 0 40px rgba(255,0,85,0.2);max-width:540px;animation:lockGlow 2s infinite alternate;">
                <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#ff0055" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom:25px;filter:drop-shadow(0 0 8px rgba(255,0,85,0.6));"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                <h1 style="color:#ff0055;margin-bottom:15px;font-size:2.2rem;font-weight:800;letter-spacing:2px;text-transform:uppercase;">🔒 WORKSTATION LOCKED</h1>
                <p style="color:#cbd5e1;margin-bottom:35px;line-height:1.6;font-size:1.1rem;max-width:440px;margin-left:auto;margin-right:auto;">Continuous identity authentication has suspended this terminal session due to consecutive keystroke anomalies or script bot spoofing signals.</p>
                <button id="lockResetBtn" style="padding:14px 35px;font-size:1.05rem;font-weight:700;color:#ffffff;background:#ff0055;border:none;border-radius:8px;cursor:pointer;text-transform:uppercase;letter-spacing:1.5px;transition:all 0.3s;box-shadow:0 0 15px rgba(255,0,85,0.3);">Unlock & Restart Session</button>
            </div>
            <style>@keyframes lockGlow{from{box-shadow:0 0 20px rgba(255,0,85,0.15);transform:scale(0.98);}to{box-shadow:0 0 45px rgba(255,0,85,0.35);transform:scale(1);}}</style>
        `;
        document.body.appendChild(lockOverlay);
        document.getElementById("lockResetBtn").addEventListener("click", () => {
            lockOverlay.remove();
            if (simStopBtn) simStopBtn.disabled = false;
            if (simBotBtn) simBotBtn.disabled = false;
            if (simRandBtn) simRandBtn.disabled = false;
            resetSession();
            startSession();
        });
    }
}
