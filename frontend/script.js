console.log("SCRIPT LOADED", new Date().toLocaleTimeString());

window.addEventListener("beforeunload", () => {
    console.log("PAGE IS UNLOADING");
});

// ==========================================
// TrustGuard AI
// Frontend Behaviour Capture & Analytics
// ==========================================

// -------------------------
// HTML Elements
// -------------------------
const typingArea = document.getElementById("typingArea");

const dwellDisplay = document.getElementById("dwell");
const flightDisplay = document.getElementById("flight");
const speedDisplay = document.getElementById("speed");
const velocityDisplay = document.getElementById("velocity");
const clicksDisplay = document.getElementById("clicks");

const avgDwellDisplay = document.getElementById("avgDwell");
const stdDwellDisplay = document.getElementById("stdDwell");
const avgFlightDisplay = document.getElementById("avgFlight");
const stdFlightDisplay = document.getElementById("stdFlight");
const avgVelocityDisplay = document.getElementById("avgVelocity");

const sessionTimeDisplay = document.getElementById("sessionTime");
const featureSessionTimeDisplay = document.getElementById("featureSessionTime");

const trustScoreDisplay = document.getElementById("trustScore");
const progressBar = document.getElementById("progressBar");
const alertText = document.getElementById("alertText");
const alertCard = document.getElementById("alertCard");
const gaugeProgress = document.getElementById("gaugeProgress");

const resetBtn = document.getElementById("resetBtn");
const exportBtn = document.getElementById("exportBtn");
const startBtn = document.getElementById("startBtn");
const endBtn = document.getElementById("endBtn");
const policySelect = document.getElementById("policySelect");

const backendBanner = document.getElementById("backendBanner");
const backendBannerText = document.getElementById("backendBannerText");

// -------------------------
// Backend
// -------------------------
const API_URL = "http://127.0.0.1:8000";

let sessionId = null;
let lastSecurityState = "NORMAL";
let currentThreshold = 50;
let uploadInterval = null;
let reconnectTimeout = null;
let backendOnline = null; // null = unknown, true/false once we know

// -------------------------
// Variables
// -------------------------
let keyDownTime = 0;
let previousKeyUp = 0;
let typingStartTime = 0;
let typingEndTime = 0;
let activeTypingTime = 0;

let sessionStart = Date.now();

let totalCharacters = 0;
let clickCount = 0;

let lastMouseX = 0;
let lastMouseY = 0;
let lastMouseTime = Date.now();

let dwellTimes = [];
let dwellTimestamps = [];
let flightTimes = [];
let flightTimestamps = [];
let mouseVelocities = [];
let mouseVelocityTimestamps = [];

// ==========================================
// Live Telemetry Logger
// ==========================================
function logTelemetry(message, type = 'info') {
    const feed = document.getElementById("telemetryFeed");
    if (!feed) return;
    
    // Remove default system log if present
    const firstChild = feed.querySelector(".feed-system");
    if (firstChild && feed.childNodes.length === 1 && message !== "Security session metrics re-initialized.") {
        firstChild.remove();
    }
    
    const entry = document.createElement("div");
    entry.className = `feed-entry feed-${type}`;
    
    const time = new Date().toLocaleTimeString().split(" ")[0];
    entry.innerHTML = `<span class="feed-time">[${time}]</span> <span class="feed-msg">${message}</span>`;
    
    feed.appendChild(entry);
    feed.scrollTop = feed.scrollHeight;
    
    // Limit log stack to last 30 entries
    while (feed.childNodes.length > 35) {
        feed.removeChild(feed.firstChild);
    }
}

// ==========================================
// Backend Connection Status
// ==========================================
function setBackendStatus(online, message) {
    if (online === backendOnline) {
        return; // no change
    }

    backendOnline = online;

    if (online) {
        backendBanner.classList.remove("backend-hidden");
        backendBanner.classList.add("backend-online");
        backendBannerText.textContent = message || "✔ Connected to TrustGuard nodes";

        setTimeout(() => {
            if (backendOnline) {
                backendBanner.classList.add("backend-hidden");
            }
        }, 3000);
    } else {
        backendBanner.classList.remove("backend-hidden");
        backendBanner.classList.remove("backend-online");
        backendBannerText.textContent = message || "⚠ Security node unreachable — retrying...";
    }
}

// ==========================================
// Start Backend Session
// ==========================================
async function startSession() {
    try {
        const response = await fetch(API_URL + "/session/start", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                user_id: "Sandeep",
                demo_mode: true
            })
        });

        if (!response.ok) {
            throw new Error("Server responded with " + response.status);
        }

        const data = await response.json();
        sessionId = data.session_id;

        console.log("✅ Session Started:", sessionId);
        logTelemetry(`Session established. Token: ${sessionId.substring(0, 8)}...`, "api");
        setBackendStatus(true);

        // Update badge and button state
        const badge = document.getElementById("sessionStatusBadge");
        if (badge) {
            badge.textContent = "🟢 ACTIVE SESSION";
            badge.className = "session-badge active-badge";
            badge.style = ""; // Reset terminal styles
        }
        if (startBtn) startBtn.disabled = true;
        if (endBtn) endBtn.disabled = false;

        if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
            reconnectTimeout = null;
        }
    }
    catch (error) {
        console.error("startSession failed:", error);
        sessionId = null;
        setBackendStatus(false, "⚠ Can't reach authentication node — retrying...");
        logTelemetry("Connection node offline. Reconnecting...", "danger");
        scheduleReconnect();
    }
}

// ==========================================
// Reconnect Loop
// ==========================================
function scheduleReconnect() {
    if (reconnectTimeout) {
        return; // already queued
    }

    reconnectTimeout = setTimeout(() => {
        reconnectTimeout = null;
        if (!sessionId) {
            console.log("Attempting to reconnect to backend...");
            startSession();
        }
    }, 5000);
}

// ==========================================
// Keyboard Events
// ==========================================
typingArea.addEventListener("keydown", function (event) {
    keyDownTime = Date.now();
    if (typingStartTime === 0) {
        typingStartTime = keyDownTime;
        logTelemetry("Biometric collection started.", "system");
    }

    if (previousKeyUp !== 0) {
        const flight = keyDownTime - previousKeyUp;

        // Ignore pauses longer than 2 seconds
        if (flight > 0 && flight < 2000) {
            flightDisplay.textContent = flight + " ms";
            pushFeature(flightTimes, flightTimestamps, flight, 20);
            logTelemetry(`KEY_DN [${event.key}] | Flight: ${flight}ms`, "info");
        } else {
            logTelemetry(`KEY_DN [${event.key}] | Flight: pause`, "info");
        }
    } else {
        logTelemetry(`KEY_DN [${event.key}]`, "info");
    }
});

typingArea.addEventListener("keyup", function (event) {
    const keyUpTime = Date.now();
    const dwell = keyUpTime - keyDownTime;

    dwellDisplay.textContent = dwell + " ms";
    pushFeature(dwellTimes, dwellTimestamps, dwell, 20);

    previousKeyUp = keyUpTime;
    typingEndTime = keyUpTime;
    activeTypingTime += (keyUpTime - keyDownTime);

    totalCharacters++;

    const activeTypingSeconds = Math.max(activeTypingTime / 1000, 1);
    const cps = (totalCharacters / activeTypingSeconds).toFixed(2);
    speedDisplay.textContent = cps + " cps";

    logTelemetry(`KEY_UP [${event.key}] | Dwell: ${dwell}ms | Speed: ${cps}cps`, "success");
});

// ==========================================
// Mouse Events
// ==========================================
document.addEventListener("click", function (event) {
    // Prevent logging clicks inside the telemetry log scrollbar
    const feed = document.getElementById("telemetryFeed");
    if (feed && feed.contains(event.target)) {
        return;
    }
    
    clickCount++;
    clicksDisplay.textContent = clickCount;
    logTelemetry(`MOUSE_CLICK | Coord: (${event.clientX}, ${event.clientY})`, "warning");
});

document.addEventListener("mousemove", function (event) {
    const currentTime = Date.now();
    const dx = event.clientX - lastMouseX;
    const dy = event.clientY - lastMouseY;
    const distance = Math.sqrt(dx * dx + dy * dy);
    const dt = (currentTime - lastMouseTime) / 1000;

    if (dt > 0) {
        const velocity = distance / dt;
        velocityDisplay.textContent = velocity.toFixed(2) + " px/s";
        pushFeature(mouseVelocities, mouseVelocityTimestamps, velocity, 100);
    }

    lastMouseX = event.clientX;
    lastMouseY = event.clientY;
    lastMouseTime = currentTime;
});

// ==========================================
// Session Controls Initial State
// ==========================================

// ==========================================
// Utility Functions
// ==========================================
function pushFeature(timesArray, tsArray, value, maxLen) {
    timesArray.push(value);
    tsArray.push(Date.now());
    if (timesArray.length > maxLen) {
        timesArray.shift();
        tsArray.shift();
    }
}

function pruneOldFeatures() {
    const now = Date.now();
    const windowMs = 30000; // Drop entries older than 30 seconds

    while (dwellTimestamps.length > 0 && now - dwellTimestamps[0] > windowMs) {
        dwellTimes.shift();
        dwellTimestamps.shift();
    }
    while (flightTimestamps.length > 0 && now - flightTimestamps[0] > windowMs) {
        flightTimes.shift();
        flightTimestamps.shift();
    }
    while (mouseVelocityTimestamps.length > 0 && now - mouseVelocityTimestamps[0] > windowMs) {
        mouseVelocities.shift();
        mouseVelocityTimestamps.shift();
    }
}

function average(arr) {
    if (arr.length === 0) return 0;
    return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function standardDeviation(arr) {
    if (arr.length === 0) return 0;
    const avg = average(arr);
    const squareDiffs = arr.map(value => {
        const diff = value - avg;
        return diff * diff;
    });
    return Math.sqrt(average(squareDiffs));
}

// ==========================================
// Send Features to Backend
// ==========================================
async function sendFeatures() {
    console.log(">>> sendFeatures()");

    // Prune old metrics to enforce the time-based sliding window
    pruneOldFeatures();

    if (!sessionId) {
        console.warn("No active session yet — skipping upload cycle.");
        setBackendStatus(false);
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

    console.log("About to call backend:", featureVector);
    logTelemetry("Uploading behavioral biometrics payload...", "api");

    try {
        const response = await fetch("http://127.0.0.1:8000/session/features", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(featureVector)
        });

        if (!response.ok) {
            throw new Error("Server responded with " + response.status);
        }

        const data = await response.json();
        console.log("Backend Response:", data);
        setBackendStatus(true);

        if (data.status === "error") {
            console.warn("Session expired on backend — establishing fresh token.");
            logTelemetry("Session expired. Resetting tokens.", "danger");
            sessionId = null;
            await startSession();
            return;
        }

        // Print per-feature comparisons to telemetry feed
        if (data.explanations && data.explanations.length > 0) {
            data.explanations.forEach(exp => {
                logTelemetry(`[COMPARE] ${exp}`, "info");
            });
        }

        // Monitor security state machine transitions
        if (data.security_state && data.security_state !== lastSecurityState) {
            const alertType = data.security_state === "LOCKED" ? "danger" : "warning";
            logTelemetry(`[SECURITY STATE] Workstation state escalated to: ${data.security_state}`, alertType);
            lastSecurityState = data.security_state;
        }

        logTelemetry(`Biometrics accepted. Score returned: ${data.trust_score}% | State: ${data.security_state || 'NORMAL'}`, "api");
        
        // Anti-spoofing logs for variance checks
        if (data.trust_score === 0 && totalCharacters >= 5) {
            const stdDwellVal = standardDeviation(dwellTimes);
            const stdFlightVal = standardDeviation(flightTimes);
            if (stdDwellVal < 2.0 || stdFlightVal < 2.0) {
                logTelemetry(`[SECURITY CRITICAL] Automated bot signature detected! Variance below threshold (Dwell SD: ${stdDwellVal.toFixed(2)}ms)`, "danger");
            }
        }

        // Trigger full-screen administrative lockout if state machine reached LOCKED
        if (data.security_state === "LOCKED") {
            lockWorkstation();
            return;
        }

        updateDashboard(data.trust_score);
    }
    catch (error) {
        console.error("sendFeatures failed:", error);
        setBackendStatus(false, "⚠ Lost link to authentication node — retrying...");
        logTelemetry("Link timeout. Connection interrupted.", "danger");
        sessionId = null;
        scheduleReconnect();
    }
}

// ==========================================
// Update Dashboard
// ==========================================
function updateDashboard(score) {
    console.log("updateDashboard()");

    // Update circular gauge score
    trustScoreDisplay.textContent = score + "%";

    // Update circular progress line
    if (gaugeProgress) {
        // Circumference is 263.89
        const circumference = 263.89;
        const offset = circumference - (score / 100) * circumference;
        gaugeProgress.style.strokeDashoffset = offset;
        
        // Handle color states
        const container = document.querySelector(".gauge-container");
        if (container) {
            container.classList.remove("genuine-gauge", "warning-gauge", "suspicious-gauge");
            if (score >= currentThreshold) {
                container.classList.add("genuine-gauge");
            } else if (score >= (currentThreshold - 20)) {
                container.classList.add("warning-gauge");
            } else {
                container.classList.add("suspicious-gauge");
            }
        }
    }

    // Update legacy progress bar for script backward compatibility
    if (progressBar) {
        progressBar.style.width = score + "%";
    }

    avgDwellDisplay.textContent = average(dwellTimes).toFixed(2) + " ms";
    stdDwellDisplay.textContent = standardDeviation(dwellTimes).toFixed(2) + " ms";
    avgFlightDisplay.textContent = average(flightTimes).toFixed(2) + " ms";
    stdFlightDisplay.textContent = standardDeviation(flightTimes).toFixed(2) + " ms";
    avgVelocityDisplay.textContent = average(mouseVelocities).toFixed(2) + " px/s";

    const seconds = Math.floor((Date.now() - sessionStart) / 1000);
    sessionTimeDisplay.textContent = seconds + " s";
    featureSessionTimeDisplay.textContent = seconds + " s";

    // Alert Card states update
    if (alertCard) {
        alertCard.classList.remove("genuine-alert", "warning-alert", "suspicious-alert");
    }

    if (score >= currentThreshold) {
        alertText.textContent = "✔ Genuine User";
        if (alertCard) alertCard.classList.add("genuine-alert");
    }
    else if (score >= (currentThreshold - 20)) {
        alertText.textContent = "⚠ Medium Risk";
        if (alertCard) alertCard.classList.add("warning-alert");
    }
    else {
        alertText.textContent = "❌ Suspicious User";
        if (alertCard) alertCard.classList.add("suspicious-alert");
    }
}

// ==========================================
// Reset Session
// ==========================================
function resetSession() {
    console.log(">>> resetSession() EXECUTED <<<");

    if (uploadInterval) {
        clearInterval(uploadInterval);
        uploadInterval = null;
    }

    if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
    }

    // Clear and enable typing area
    typingArea.value = "";
    typingArea.disabled = false;
    typingArea.placeholder = "Begin typing here to verify your behavioral profile...";

    // Reset simulation configurations
    if (botInterval) {
        clearInterval(botInterval);
        clearTimeout(botInterval);
        botInterval = null;
    }
    currentThreatMode = "human";

    if (simStopBtn) simStopBtn.classList.add("sim-btn-active");
    if (simBotBtn) simBotBtn.classList.remove("sim-btn-active");
    if (simRandBtn) simRandBtn.classList.remove("sim-btn-active");

    if (simulatorBadge) {
        simulatorBadge.textContent = "🟢 HUMAN MODE";
        simulatorBadge.className = "session-badge active-badge human-badge";
        simulatorBadge.style = "";
    }

    // Reset counters
    totalCharacters = 0;
    clickCount = 0;
    lastSecurityState = "NORMAL";

    // Reset timing
    keyDownTime = 0;
    previousKeyUp = 0;
    typingStartTime = 0;
    typingEndTime = 0;
    activeTypingTime = 0;
    sessionStart = Date.now();

    // Clear arrays
    dwellTimes = [];
    dwellTimestamps = [];
    flightTimes = [];
    flightTimestamps = [];
    mouseVelocities = [];
    mouseVelocityTimestamps = [];

    // Reset displays
    dwellDisplay.textContent = "0 ms";
    flightDisplay.textContent = "0 ms";
    speedDisplay.textContent = "0 cps";
    velocityDisplay.textContent = "0 px/s";
    clicksDisplay.textContent = "0";

    avgDwellDisplay.textContent = "0 ms";
    stdDwellDisplay.textContent = "0 ms";
    avgFlightDisplay.textContent = "0 ms";
    stdFlightDisplay.textContent = "0 ms";
    avgVelocityDisplay.textContent = "0 px/s";

    sessionTimeDisplay.textContent = "0 s";
    featureSessionTimeDisplay.textContent = "0 s";

    trustScoreDisplay.textContent = "100%";
    if (gaugeProgress) {
        gaugeProgress.style.strokeDashoffset = "0";
    }
    if (progressBar) {
        progressBar.style.width = "100%";
    }
    
    const container = document.querySelector(".gauge-container");
    if (container) {
        container.classList.remove("genuine-gauge", "warning-gauge", "suspicious-gauge");
        container.classList.add("genuine-gauge");
    }

    if (alertCard) {
        alertCard.classList.remove("genuine-alert", "warning-alert", "suspicious-alert");
        alertCard.classList.add("genuine-alert");
    }
    alertText.textContent = "✔ Genuine User";

    // Clear terminal feed
    const feed = document.getElementById("telemetryFeed");
    if (feed) {
        feed.innerHTML = '<div class="feed-entry feed-system">[SYSTEM] Awaiting keystroke and mouse kinematics...</div>';
    }
    logTelemetry("Security session metrics re-initialized.", "system");

    console.log("Session Reset Complete");
}

// ==========================================
// Export Session Data
// ==========================================
function exportSession() {
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
        session_duration_s: sessionSeconds,
        trust_score: trustScoreDisplay.textContent
    };

    const blob = new Blob(
        [JSON.stringify(data, null, 4)],
        { type: "application/json" }
    );

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "trustguard_session.json";
    a.click();
    URL.revokeObjectURL(url);
    logTelemetry("Exported session biometrics vector to JSON.", "system");
}

// ==========================================
// Button Events
// ==========================================
startBtn.addEventListener("click", async () => {
    console.log("1. Start button clicked");
    resetSession();
    console.log("2. resetSession completed");
    
    if (startBtn) startBtn.disabled = true;
    if (endBtn) endBtn.disabled = false;
    
    await startSession();
    console.log("3. startSession completed");
    
    if (uploadInterval) {
        clearInterval(uploadInterval);
    }

    console.log("4. Creating interval");
    uploadInterval = setInterval(() => {
        console.log("Interval fired");
        sendFeatures();
    }, 5000);

    console.log("5. Interval created", uploadInterval);
    logTelemetry("Continuous authentication scanning activated.", "system");
});

resetBtn.addEventListener("click", () => {
    console.log("🔥 RESET BUTTON CLICKED");
    resetSession();
    if (startBtn) startBtn.disabled = false;
    if (endBtn) endBtn.disabled = true;
});

exportBtn.addEventListener("click", () => {
    exportSession();
});

endBtn.addEventListener("click", () => {
    console.log("■ END SESSION CLICKED");
    
    if (uploadInterval) {
        clearInterval(uploadInterval);
        uploadInterval = null;
    }
    
    if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
    }
    
    sessionId = null;
    
    if (startBtn) startBtn.disabled = false;
    if (endBtn) endBtn.disabled = true;
    
    const badge = document.getElementById("sessionStatusBadge");
    if (badge) {
        badge.textContent = "🔴 SESSION TERMINATED";
        badge.className = "session-badge";
        badge.style.background = "rgba(239, 68, 68, 0.1)";
        badge.style.border = "1px solid var(--clr-suspicious)";
        badge.style.color = "var(--clr-suspicious)";
        badge.style.boxShadow = "0 0 10px rgba(239, 68, 68, 0.2)";
    }
    
    typingArea.disabled = true;
    typingArea.placeholder = "[SESSION TERMINATED] Start session to resume continuous monitoring.";
    
    logTelemetry("Continuous authentication monitoring terminated.", "system");
});

if (policySelect) {
    policySelect.addEventListener("change", (e) => {
        const val = e.target.value;
        if (val === "strict") {
            currentThreshold = 75;
            logTelemetry("Security Policy escalated to Strict (75% Threshold).", "warning");
        } else if (val === "relaxed") {
            currentThreshold = 30;
            logTelemetry("Security Policy reduced to Relaxed (30% Threshold).", "info");
        } else {
            currentThreshold = 50;
            logTelemetry("Security Policy reset to Balanced (50% Threshold).", "system");
        }
        
        const rawScore = parseInt(trustScoreDisplay.textContent);
        if (!isNaN(rawScore)) {
            updateDashboard(rawScore);
        }
    });
}

// ==========================================================================
// Live Mouse Kinematics Canvas Drawing
// ==========================================================================
const canvas = document.getElementById("kinematicsCanvas");
const ctx = canvas ? canvas.getContext("2d") : null;
let mouseHistory = [];
let clickRipples = [];

function resizeCanvas() {
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
}
window.addEventListener("resize", resizeCanvas);
resizeCanvas(); // Initial adjustment

let currentCanvasMouseX = -1;
let currentCanvasMouseY = -1;

document.addEventListener("mousemove", (e) => {
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    currentCanvasMouseX = x;
    currentCanvasMouseY = y;
    
    mouseHistory.push({ x, y, age: 0 });
});

document.addEventListener("click", (e) => {
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const feed = document.getElementById("telemetryFeed");
    if (feed && feed.contains(e.target)) return;
    
    clickRipples.push({ x, y, radius: 2, maxRadius: 30, alpha: 1.0 });
});

// Canvas Drawing Loop
function drawKinematics() {
    if (!canvas || !ctx) return;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw mouse coordinate trace path
    if (mouseHistory.length > 1) {
        ctx.beginPath();
        ctx.strokeStyle = "rgba(56, 189, 248, 0.3)";
        ctx.lineWidth = 2.5;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        
        ctx.moveTo(mouseHistory[0].x, mouseHistory[0].y);
        for (let i = 1; i < mouseHistory.length; i++) {
            ctx.lineTo(mouseHistory[i].x, mouseHistory[i].y);
        }
        ctx.stroke();
    }
    
    // Update mouse trace age
    mouseHistory.forEach(pt => pt.age++);
    mouseHistory = mouseHistory.filter(pt => pt.age < 25);
    
    // Draw cursor indicator
    if (currentCanvasMouseX >= 0 && currentCanvasMouseX <= canvas.width &&
        currentCanvasMouseY >= 0 && currentCanvasMouseY <= canvas.height) {
        ctx.beginPath();
        ctx.arc(currentCanvasMouseX, currentCanvasMouseY, 4, 0, 2 * Math.PI);
        ctx.fillStyle = "#38bdf8";
        ctx.shadowColor = "#38bdf8";
        ctx.shadowBlur = 10;
        ctx.fill();
        ctx.shadowBlur = 0; // Reset shadow
    }
    
    // Draw expanding click ripples
    clickRipples.forEach(ripple => {
        ctx.beginPath();
        ctx.arc(ripple.x, ripple.y, ripple.radius, 0, 2 * Math.PI);
        ctx.strokeStyle = `rgba(239, 68, 68, ${ripple.alpha})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
        
        ripple.radius += 1.5;
        ripple.alpha -= 0.04;
    });
    
    clickRipples = clickRipples.filter(ripple => ripple.alpha > 0);
    
    requestAnimationFrame(drawKinematics);
}
requestAnimationFrame(drawKinematics);


// ==========================================================================
// Threat & Bot Simulator Controller
// ==========================================================================
const simStopBtn = document.getElementById("simStopBtn");
const simBotBtn = document.getElementById("simBotBtn");
const simRandBtn = document.getElementById("simRandBtn");
const simulatorBadge = document.getElementById("simulatorBadge");

let currentThreatMode = "human";
let botInterval = null;

function setThreatMode(mode) {
    if (currentThreatMode === mode) return;
    
    currentThreatMode = mode;
    
    // Clear existing timer loops
    if (botInterval) {
        clearInterval(botInterval);
        clearTimeout(botInterval);
        botInterval = null;
    }
    
    simStopBtn.classList.remove("sim-btn-active");
    simBotBtn.classList.remove("sim-btn-active");
    simRandBtn.classList.remove("sim-btn-active");
    
    simulatorBadge.classList.remove("human-badge", "bot-badge", "attacker-badge");
    
    if (mode === "human") {
        simStopBtn.classList.add("sim-btn-active");
        simulatorBadge.textContent = "🟢 HUMAN MODE";
        simulatorBadge.classList.add("human-badge");
        typingArea.disabled = false;
        typingArea.placeholder = "Begin typing here to train or verify your behavioral profile...";
        logTelemetry("Simulator deactivated. Restored Human control.", "system");
    } 
    else if (mode === "bot") {
        simBotBtn.classList.add("sim-btn-active");
        simulatorBadge.textContent = "🤖 SCRIPT BOT";
        simulatorBadge.classList.add("bot-badge");
        typingArea.disabled = true;
        typingArea.placeholder = "[SIMULATION RUNNING] Script Bot automated keystrokes typing...";
        logTelemetry("Simulator activated: Script Bot timing spoofing.", "warning");
        
        if (!sessionId) {
            startBtn.click();
        }
        
        const text = "trustguard_bot_timing_evasion_attack_vector_spoof";
        let index = 0;
        botInterval = setInterval(() => {
            if (currentThreatMode !== "bot") return;
            if (index >= text.length) index = 0;
            const char = text[index++];
            
            typingArea.value += char;
            
            // Mock timing vectors with zero variance (standard deviation < 2ms)
            const dwell = 100.0 + (Math.random() * 0.4 - 0.2); 
            const flight = 100.0 + (Math.random() * 0.4 - 0.2);
            
            pushFeature(dwellTimes, dwellTimestamps, dwell, 20);
            pushFeature(flightTimes, flightTimestamps, flight, 20);
            
            totalCharacters++;
            activeTypingTime += 100;
            
            const activeTypingSeconds = Math.max(activeTypingTime / 1000, 1);
            const cps = (totalCharacters / activeTypingSeconds).toFixed(2);
            speedDisplay.textContent = cps + " cps";
            
            dwellDisplay.textContent = dwell.toFixed(2) + " ms";
            flightDisplay.textContent = flight.toFixed(2) + " ms";
            
            logTelemetry(`[BOT] KEY_UP [${char}] | Dwell: ${dwell.toFixed(1)}ms | Flight: ${flight.toFixed(1)}ms`, "danger");
        }, 120);
    } 
    else if (mode === "attacker") {
        simRandBtn.classList.add("sim-btn-active");
        simulatorBadge.textContent = "⚠️ ERRATIC ATTACKER";
        simulatorBadge.classList.add("attacker-badge");
        typingArea.disabled = true;
        typingArea.placeholder = "[SIMULATION RUNNING] Erratic Attacker typing simulation...";
        logTelemetry("Simulator activated: Erratic Attacker (high-variance anomaly).", "warning");
        
        if (!sessionId) {
            startBtn.click();
        }
        
        const text = "erratic_attack_payload_chaos";
        let index = 0;
        
        const typeNext = () => {
            if (currentThreatMode !== "attacker") return;
            if (index >= text.length) index = 0;
            const char = text[index++];
            
            typingArea.value += char;
            
            // High variance distributions
            const dwell = 500.0 + (Math.random() * 800.0); 
            const flight = 50.0 + (Math.random() * 150.0);  
            
            pushFeature(dwellTimes, dwellTimestamps, dwell, 20);
            pushFeature(flightTimes, flightTimestamps, flight, 20);
            
            totalCharacters++;
            activeTypingTime += dwell;
            
            const activeTypingSeconds = Math.max(activeTypingTime / 1000, 1);
            const cps = (totalCharacters / activeTypingSeconds).toFixed(2);
            speedDisplay.textContent = cps + " cps";
            
            dwellDisplay.textContent = dwell.toFixed(1) + " ms";
            flightDisplay.textContent = flight.toFixed(1) + " ms";
            
            logTelemetry(`[ATTACKER] KEY_UP [${char}] | Dwell: ${dwell.toFixed(0)}ms | Flight: ${flight.toFixed(0)}ms`, "warning");
            
            const nextDelay = 150 + Math.random() * 450;
            botInterval = setTimeout(typeNext, nextDelay);
        };
        botInterval = setTimeout(typeNext, 200);
    }
}

simStopBtn.addEventListener("click", () => setThreatMode("human"));
simBotBtn.addEventListener("click", () => setThreatMode("bot"));
simRandBtn.addEventListener("click", () => setThreatMode("attacker"));


// ==========================================================================
// Secure Security Audit Ledger Database Logger
// ==========================================================================
const ledgerLockPanel = document.getElementById("ledgerLockPanel");
const ledgerTablePanel = document.getElementById("ledgerTablePanel");
const adminPinInput = document.getElementById("adminPinInput");
const unlockLedgerBtn = document.getElementById("unlockLedgerBtn");
const refreshLedgerBtn = document.getElementById("refreshLedgerBtn");
const lockLedgerBtn = document.getElementById("lockLedgerBtn");
const ledgerBadge = document.getElementById("ledgerBadge");
const ledgerErrorMsg = document.getElementById("ledgerErrorMsg");
const auditTableBody = document.getElementById("auditTableBody");

let unlockedPin = null;

async function fetchAuditLogs(pin) {
    ledgerErrorMsg.textContent = "";
    try {
        const response = await fetch("http://127.0.0.1:8000/session/history", {
            method: "GET",
            headers: {
                "X-Admin-PIN": pin
            }
        });
        
        if (response.status === 403) {
            throw new Error("Invalid Security PIN");
        }
        if (!response.ok) {
            throw new Error("Server error: " + response.status);
        }
        
        const logs = await response.json();
        renderAuditLogs(logs);
        
        // Decrypted successfully
        unlockedPin = pin;
        ledgerLockPanel.classList.add("hidden-ledger-content");
        ledgerTablePanel.classList.remove("hidden-ledger-content");
        
        ledgerBadge.textContent = "UNLOCKED";
        ledgerBadge.classList.remove("suspicious-badge");
        ledgerBadge.classList.add("human-badge");
        logTelemetry("Database security audit ledger successfully decrypted.", "success");
    } 
    catch (error) {
        console.error("fetchAuditLogs error:", error);
        ledgerErrorMsg.textContent = "❌ " + error.message;
        logTelemetry("Database access blocked: Unauthorized PIN.", "danger");
    }
}

function renderAuditLogs(logs) {
    if (!auditTableBody) return;
    
    if (logs.length === 0) {
        auditTableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center" style="font-family: var(--font-primary); color: var(--text-muted);">No biometrics records found in the database.</td>
            </tr>
        `;
        return;
    }
    
    auditTableBody.innerHTML = "";
    logs.forEach(log => {
        const row = document.createElement("tr");
        
        // Format ISO timestamp
        let datePart = "";
        let timePart = "";
        if (log.timestamp) {
            const parts = log.timestamp.split("T");
            datePart = parts[0];
            timePart = parts[1] ? parts[1].substring(0, 8) : "";
        }
        
        // Format trust score color indicators
        let scoreClass = "";
        if (log.trust_score >= 80) scoreClass = "feed-success";
        else if (log.trust_score >= 50) scoreClass = "feed-warning";
        else scoreClass = "feed-danger";
        
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

function lockLedger() {
    unlockedPin = null;
    adminPinInput.value = "";
    ledgerErrorMsg.textContent = "";
    
    ledgerLockPanel.classList.remove("hidden-ledger-content");
    ledgerTablePanel.classList.add("hidden-ledger-content");
    
    ledgerBadge.textContent = "LOCKED";
    ledgerBadge.classList.remove("human-badge");
    ledgerBadge.classList.add("suspicious-badge");
    
    logTelemetry("Security audit ledger locked.", "system");
}

unlockLedgerBtn.addEventListener("click", () => {
    const pin = adminPinInput.value.trim();
    if (!pin) {
        ledgerErrorMsg.textContent = "Please enter a PIN.";
        return;
    }
    fetchAuditLogs(pin);
});

adminPinInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        unlockLedgerBtn.click();
    }
});

refreshLedgerBtn.addEventListener("click", () => {
    if (unlockedPin) {
        fetchAuditLogs(unlockedPin);
    }
});

lockLedgerBtn.addEventListener("click", () => {
    lockLedger();
});

// ==========================================================================
// 3D Card Hover Tilt Effect
// ==========================================================================
const tiltCards = document.querySelectorAll(".card.glass");

tiltCards.forEach(card => {
    card.addEventListener("mousemove", (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        
        // Max 6 degrees rotation angle
        const rotateX = ((centerY - y) / centerY) * 6;
        const rotateY = ((x - centerX) / centerX) * 6;
        
        card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px) scale(1.01)`;
        card.style.boxShadow = `0 15px 35px rgba(56, 189, 248, 0.12)`;
        card.style.borderColor = `rgba(56, 189, 248, 0.35)`;
    });
    
    card.addEventListener("mouseleave", () => {
        card.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0) scale(1)`;
        card.style.boxShadow = `0 8px 32px rgba(0, 0, 0, 0.3)`;
        card.style.borderColor = `rgba(56, 189, 248, 0.15)`;
    });
});


// ==========================================================================
// Ambient Binary Cyber Rain Background Canvas
// ==========================================================================
const bgCanvas = document.getElementById("bgCanvas");
const bgCtx = bgCanvas ? bgCanvas.getContext("2d") : null;

let bgColumns = [];
const bgFontSize = 14;

function resizeBgCanvas() {
    if (!bgCanvas) return;
    bgCanvas.width = window.innerWidth;
    bgCanvas.height = window.innerHeight;
    
    // Draw columns spacing
    const numColumns = Math.floor(bgCanvas.width / 26);
    bgColumns = [];
    for (let i = 0; i < numColumns; i++) {
        bgColumns.push({
            x: i * 26,
            y: Math.random() * -bgCanvas.height,
            speed: 1.5 + Math.random() * 2.0,
            chars: Array.from({ length: 15 }, () => Math.random() > 0.5 ? "1" : "0")
        });
    }
}

window.addEventListener("resize", resizeBgCanvas);
resizeBgCanvas(); // Initial trigger

function drawBgRain() {
    if (!bgCanvas || !bgCtx) return;
    
    // Fade overlay to draw trails
    bgCtx.fillStyle = "rgba(5, 11, 20, 0.16)"; 
    bgCtx.fillRect(0, 0, bgCanvas.width, bgCanvas.height);
    
    bgCtx.font = `${bgFontSize}px var(--font-mono)`;
    
    bgColumns.forEach(col => {
        col.chars.forEach((char, idx) => {
            const yPos = col.y + idx * bgFontSize;
            if (yPos > 0 && yPos < bgCanvas.height) {
                // Highlight leading block
                if (idx === col.chars.length - 1) {
                    bgCtx.fillStyle = "rgba(56, 189, 248, 0.30)";
                } else {
                    bgCtx.fillStyle = "rgba(56, 189, 248, 0.12)";
                }
                bgCtx.fillText(char, col.x, yPos);
            }
        });
        
        // Tick falling coordinates
        col.y += col.speed;
        
        if (col.y > bgCanvas.height) {
            col.y = -bgFontSize * col.chars.length;
            col.speed = 1.5 + Math.random() * 2.0;
        }
        
        // Organic stream values mutator
        if (Math.random() > 0.97) {
            col.chars[Math.floor(Math.random() * col.chars.length)] = Math.random() > 0.5 ? "1" : "0";
        }
    });
    
    requestAnimationFrame(drawBgRain);
}

if (bgCanvas && bgCtx) {
    requestAnimationFrame(drawBgRain);
}

// ==========================================================================
// Animated Entry Loader Handler
// ==========================================================================
window.addEventListener("DOMContentLoaded", () => {
    const loader = document.getElementById("appLoader");
    const wrapper = document.getElementById("dashboardWrapper");

    // Wait 3 seconds for title and fill bar animations to finish
    setTimeout(() => {
        if (loader) {
            loader.classList.add("loader-fade-out");
        }
        if (wrapper) {
            wrapper.classList.add("dashboard-visible");
        }
        
        // Remove element from DOM after fade-out transition completes
        setTimeout(() => {
            if (loader && loader.parentNode) {
                loader.parentNode.removeChild(loader);
            }
        }, 800);
        
        logTelemetry("Workstation initialized. Zero-trust continuous monitoring offline. Click 'Start Session' to begin.", "system");
    }, 3000);
});


// ==========================================
// Workstation Administrative Lockout Overlay
// ==========================================
function lockWorkstation() {
    console.warn("🔒 WORKSTATION LOCKED!");

    // Clear telemetry loops
    if (uploadInterval) {
        clearInterval(uploadInterval);
        uploadInterval = null;
    }
    if (botInterval) {
        clearInterval(botInterval);
        botInterval = null;
    }

    // Lock workstation inputs
    typingArea.value = "";
    typingArea.disabled = true;
    typingArea.placeholder = "🔴 WORKSTATION LOCKED - Biometrics Policy Violated";

    // Disable threat simulator switches
    if (simStopBtn) simStopBtn.disabled = true;
    if (simBotBtn) simBotBtn.disabled = true;
    if (simRandBtn) simRandBtn.disabled = true;

    // Create and render full-screen blocker dynamic card
    let lockOverlay = document.getElementById("securityLockOverlay");
    if (!lockOverlay) {
        lockOverlay = document.createElement("div");
        lockOverlay.id = "securityLockOverlay";
        lockOverlay.style.position = "fixed";
        lockOverlay.style.top = "0";
        lockOverlay.style.left = "0";
        lockOverlay.style.width = "100vw";
        lockOverlay.style.height = "100vh";
        lockOverlay.style.backgroundColor = "rgba(8, 8, 12, 0.98)";
        lockOverlay.style.backdropFilter = "blur(12px)";
        lockOverlay.style.zIndex = "999999";
        lockOverlay.style.display = "flex";
        lockOverlay.style.flexDirection = "column";
        lockOverlay.style.justifyContent = "center";
        lockOverlay.style.alignItems = "center";
        lockOverlay.style.color = "#ff0055";
        lockOverlay.style.fontFamily = "'Outfit', sans-serif";
        lockOverlay.style.textAlign = "center";

        lockOverlay.innerHTML = `
            <div style="padding: 50px; border: 2px solid #ff0055; border-radius: 16px; background: rgba(255, 0, 85, 0.04); box-shadow: 0 0 40px rgba(255, 0, 85, 0.2); max-width: 540px; transform: scale(0.95); animation: lockGlow 2s infinite alternate;">
                <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#ff0055" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 25px; filter: drop-shadow(0 0 8px rgba(255, 0, 85, 0.6));">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
                <h1 style="color: #ff0055; margin-bottom: 15px; font-size: 2.2rem; font-weight: 800; letter-spacing: 2px; text-transform: uppercase;">🔒 WORKSTATION LOCKED</h1>
                <p style="color: #cbd5e1; margin-bottom: 35px; line-height: 1.6; font-size: 1.1rem; max-width: 440px; margin-left: auto; margin-right: auto;">
                    Continuous identity authentication has suspended this terminal session due to consecutive keystroke anomalies or script bot spoofing signals.
                </p>
                <button id="lockResetBtn" style="padding: 14px 35px; font-size: 1.05rem; font-weight: 700; color: #ffffff; background: #ff0055; border: none; border-radius: 8px; cursor: pointer; text-transform: uppercase; letter-spacing: 1.5px; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 0 15px rgba(255, 0, 85, 0.3);">
                    Unlock & Restart Session
                </button>
            </div>
            <style>
                @keyframes lockGlow {
                    from { box-shadow: 0 0 20px rgba(255, 0, 85, 0.15); transform: scale(0.98); }
                    to { box-shadow: 0 0 45px rgba(255, 0, 85, 0.35); transform: scale(1); }
                }
                #lockResetBtn:hover {
                    background: #e1004b;
                    box-shadow: 0 0 25px rgba(255, 0, 85, 0.6);
                    transform: translateY(-2px);
                }
                #lockResetBtn:active {
                    transform: translateY(1px);
                }
            </style>
        `;
        document.body.appendChild(lockOverlay);

        // Wire reset handler to restore control
        document.getElementById("lockResetBtn").addEventListener("click", function() {
            lockOverlay.remove();
            
            // Re-enable inputs
            if (simStopBtn) simStopBtn.disabled = false;
            if (simBotBtn) simBotBtn.disabled = false;
            if (simRandBtn) simRandBtn.disabled = false;

            resetSession();
            startSession();
        });
    }
}