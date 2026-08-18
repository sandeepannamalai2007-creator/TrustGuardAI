// ============================================================
// modules/ui.js
// All DOM updates: telemetry log, dashboard gauges, alert card,
// backend status banner, theme toggle, live ARIA status, error toast.
// ============================================================

// -------------------------
// ARIA live region
// -------------------------
export function updateLiveStatus(message) {
    const liveRegion = document.getElementById("statusLive");
    if (liveRegion) liveRegion.textContent = message;
}

// -------------------------
// Telemetry feed logger
// -------------------------
export function logTelemetry(message, type = "info") {
    const feed = document.getElementById("telemetryFeed");
    if (!feed) return;

    const firstChild = feed.querySelector(".feed-system");
    if (firstChild && feed.childNodes.length === 1 && message !== "Security session metrics re-initialized.") {
        firstChild.remove();
    }

    const entry = document.createElement("div");
    entry.className = `feed-entry feed-${type}`;

    const time = new Date().toLocaleTimeString().split(" ")[0];
    const timeSpan = document.createElement("span");
    timeSpan.className = "feed-time";
    timeSpan.textContent = `[${time}]`;
    const msgSpan = document.createElement("span");
    msgSpan.className = "feed-msg";
    msgSpan.textContent = message;

    entry.appendChild(timeSpan);
    entry.appendChild(document.createTextNode(" "));
    entry.appendChild(msgSpan);
    feed.appendChild(entry);
    feed.scrollTop = feed.scrollHeight;

    while (feed.childNodes.length > 35) {
        feed.removeChild(feed.firstChild);
    }
}

// -------------------------
// Backend status banner
// -------------------------
let _backendOnline = null;

export function setBackendStatus(online, message) {
    const backendBanner = document.getElementById("backendBanner");
    const backendBannerText = document.getElementById("backendBannerText");
    if (!backendBanner || !backendBannerText) return;

    if (online === _backendOnline) return;
    _backendOnline = online;

    if (online) {
        backendBanner.classList.remove("backend-hidden");
        backendBanner.classList.add("backend-online");
        backendBannerText.textContent = message || "✔ Connected to TrustGuard nodes";
        setTimeout(() => {
            if (_backendOnline) backendBanner.classList.add("backend-hidden");
        }, 3000);
    } else {
        backendBanner.classList.remove("backend-hidden");
        backendBanner.classList.remove("backend-online");
        backendBannerText.textContent = message || "⚠ Security node unreachable — retrying...";
    }
}

export function getBackendOnline() { return _backendOnline; }
export function resetBackendOnline() { _backendOnline = null; }

// -------------------------
// Dashboard gauge & alert card
// -------------------------
let _currentThreshold = 50;
export function setThreshold(t) { _currentThreshold = t; }
export function getThreshold() { return _currentThreshold; }

export function updateDashboard(score, dwellTimes, flightTimes, mouseVelocities,
    totalCharacters, activeTypingTime, sessionStart, average, standardDeviation) {

    const trustScoreDisplay = document.getElementById("trustScore");
    const progressBar = document.getElementById("progressBar");
    const alertText = document.getElementById("alertText");
    const alertCard = document.getElementById("alertCard");
    const gaugeProgress = document.getElementById("gaugeProgress");
    const avgDwellDisplay = document.getElementById("avgDwell");
    const stdDwellDisplay = document.getElementById("stdDwell");
    const avgFlightDisplay = document.getElementById("avgFlight");
    const stdFlightDisplay = document.getElementById("stdFlight");
    const avgVelocityDisplay = document.getElementById("avgVelocity");
    const sessionTimeDisplay = document.getElementById("sessionTime");
    const featureSessionTimeDisplay = document.getElementById("featureSessionTime");

    if (trustScoreDisplay) trustScoreDisplay.textContent = score + "%";
    const gaugeContainer = document.querySelector(".gauge-container");
    if (gaugeContainer) gaugeContainer.setAttribute("aria-valuenow", score);

    if (gaugeProgress) {
        const circumference = 263.89;
        const offset = circumference - (score / 100) * circumference;
        gaugeProgress.style.strokeDashoffset = offset;
        if (gaugeContainer) {
            gaugeContainer.classList.remove("genuine-gauge", "warning-gauge", "suspicious-gauge");
            if (score >= _currentThreshold) gaugeContainer.classList.add("genuine-gauge");
            else if (score >= (_currentThreshold - 20)) gaugeContainer.classList.add("warning-gauge");
            else gaugeContainer.classList.add("suspicious-gauge");
        }
    }

    if (progressBar) progressBar.style.width = score + "%";

    if (avgDwellDisplay) avgDwellDisplay.textContent = average(dwellTimes).toFixed(2) + " ms";
    if (stdDwellDisplay) stdDwellDisplay.textContent = standardDeviation(dwellTimes).toFixed(2) + " ms";
    if (avgFlightDisplay) avgFlightDisplay.textContent = average(flightTimes).toFixed(2) + " ms";
    if (stdFlightDisplay) stdFlightDisplay.textContent = standardDeviation(flightTimes).toFixed(2) + " ms";
    if (avgVelocityDisplay) avgVelocityDisplay.textContent = average(mouseVelocities).toFixed(2) + " px/s";

    const seconds = Math.floor((Date.now() - sessionStart) / 1000);
    if (sessionTimeDisplay) sessionTimeDisplay.textContent = seconds + " s";
    if (featureSessionTimeDisplay) featureSessionTimeDisplay.textContent = seconds + " s";

    if (alertCard) alertCard.classList.remove("genuine-alert", "warning-alert", "suspicious-alert");
    if (score >= _currentThreshold) {
        if (alertText) alertText.textContent = "✔ Genuine User";
        if (alertCard) alertCard.classList.add("genuine-alert");
    } else if (score >= (_currentThreshold - 20)) {
        if (alertText) alertText.textContent = "⚠ Medium Risk";
        if (alertCard) alertCard.classList.add("warning-alert");
    } else {
        if (alertText) alertText.textContent = "❌ Suspicious User";
        if (alertCard) alertCard.classList.add("suspicious-alert");
    }
}

// -------------------------
// Error toast
// -------------------------
export function showError(message) {
    const alertText = document.getElementById("alertText");
    const alertCard = document.getElementById("alertCard");
    if (alertText) alertText.textContent = "❌ " + message;
    if (alertCard) {
        alertCard.classList.remove("genuine-alert", "warning-alert");
        alertCard.classList.add("suspicious-alert");
    }
    updateLiveStatus("Error: " + message);
    logTelemetry("ERROR: " + message, "danger");
}

// -------------------------
// Theme toggle
// -------------------------
export function initTheme() {
    const themeToggle = document.getElementById("themeToggle");
    const savedTheme = localStorage.getItem("trustguard_theme") || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);
    if (themeToggle) {
        themeToggle.textContent = savedTheme === "light" ? "☀️ Theme" : "🌙 Theme";
        themeToggle.addEventListener("click", () => {
            const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
            const newTheme = currentTheme === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-theme", newTheme);
            localStorage.setItem("trustguard_theme", newTheme);
            themeToggle.textContent = newTheme === "light" ? "☀️ Theme" : "🌙 Theme";
            updateLiveStatus(`Theme switched to ${newTheme} mode.`);
        });
    }
}
