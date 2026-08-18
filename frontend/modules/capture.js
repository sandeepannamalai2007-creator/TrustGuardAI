// ============================================================
// modules/capture.js
// Biometric capture engine: keystroke timing, mouse velocity,
// sliding window feature management, and stat helpers.
// ============================================================

// -----------------------------------------------------------------------
// Sliding window state
// -----------------------------------------------------------------------
export let dwellTimes = [];
export let dwellTimestamps = [];
export let flightTimes = [];
export let flightTimestamps = [];
export let mouseVelocities = [];
export let mouseVelocityTimestamps = [];

export let totalCharacters = 0;
export let clickCount = 0;
export let activeTypingTime = 0;

let keyDownTime = 0;
let previousKeyUp = 0;
export let typingStartTime = 0;

let lastMouseX = 0;
let lastMouseY = 0;
let lastMouseTime = Date.now();

// -----------------------------------------------------------------------
// Stat helpers (pure functions — easy to unit test)
// -----------------------------------------------------------------------
export function average(arr) {
    if (arr.length === 0) return 0;
    return arr.reduce((a, b) => a + b, 0) / arr.length;
}

export function standardDeviation(arr) {
    if (arr.length === 0) return 0;
    const avg = average(arr);
    return Math.sqrt(average(arr.map(v => (v - avg) ** 2)));
}

// -----------------------------------------------------------------------
// Sliding window helpers
// -----------------------------------------------------------------------
export function pushFeature(timesArray, tsArray, value, maxLen) {
    timesArray.push(value);
    tsArray.push(Date.now());
    if (timesArray.length > maxLen) {
        timesArray.shift();
        tsArray.shift();
    }
}

export function pruneOldFeatures() {
    const now = Date.now();
    const windowMs = 30000;
    while (dwellTimestamps.length > 0 && now - dwellTimestamps[0] > windowMs) {
        dwellTimes.shift(); dwellTimestamps.shift();
    }
    while (flightTimestamps.length > 0 && now - flightTimestamps[0] > windowMs) {
        flightTimes.shift(); flightTimestamps.shift();
    }
    while (mouseVelocityTimestamps.length > 0 && now - mouseVelocityTimestamps[0] > windowMs) {
        mouseVelocities.shift(); mouseVelocityTimestamps.shift();
    }
}

// -----------------------------------------------------------------------
// Reset capture state
// -----------------------------------------------------------------------
export function resetCapture() {
    dwellTimes.length = 0;
    dwellTimestamps.length = 0;
    flightTimes.length = 0;
    flightTimestamps.length = 0;
    mouseVelocities.length = 0;
    mouseVelocityTimestamps.length = 0;
    totalCharacters = 0;
    clickCount = 0;
    activeTypingTime = 0;
    keyDownTime = 0;
    previousKeyUp = 0;
    typingStartTime = 0;
    lastMouseX = 0;
    lastMouseY = 0;
    lastMouseTime = Date.now();
}

// -----------------------------------------------------------------------
// Attach keystroke and mouse event listeners
// -----------------------------------------------------------------------
export function initCapture(logTelemetry) {
    const typingArea = document.getElementById("typingArea");
    const dwellDisplay = document.getElementById("dwell");
    const flightDisplay = document.getElementById("flight");
    const speedDisplay = document.getElementById("speed");
    const velocityDisplay = document.getElementById("velocity");
    const clicksDisplay = document.getElementById("clicks");

    if (!typingArea) return;

    typingArea.addEventListener("keydown", (event) => {
        keyDownTime = Date.now();
        if (typingStartTime === 0) {
            typingStartTime = keyDownTime;
            logTelemetry("Biometric collection started.", "system");
        }

        if (previousKeyUp !== 0) {
            const flight = keyDownTime - previousKeyUp;
            if (flight > 0 && flight < 2000) {
                if (flightDisplay) flightDisplay.textContent = flight + " ms";
                pushFeature(flightTimes, flightTimestamps, flight, 20);
                logTelemetry(`KEY_DN [${event.key}] | Flight: ${flight}ms`, "info");
            } else {
                logTelemetry(`KEY_DN [${event.key}] | Flight: pause`, "info");
            }
        } else {
            logTelemetry(`KEY_DN [${event.key}]`, "info");
        }
    });

    typingArea.addEventListener("keyup", (event) => {
        const keyUpTime = Date.now();
        const dwell = keyUpTime - keyDownTime;

        if (dwellDisplay) dwellDisplay.textContent = dwell + " ms";
        pushFeature(dwellTimes, dwellTimestamps, dwell, 20);
        previousKeyUp = keyUpTime;
        activeTypingTime += (keyUpTime - keyDownTime);
        totalCharacters++;

        const activeTypingSeconds = Math.max(activeTypingTime / 1000, 1);
        const cps = (totalCharacters / activeTypingSeconds).toFixed(2);
        if (speedDisplay) speedDisplay.textContent = cps + " cps";
        logTelemetry(`KEY_UP [${event.key}] | Dwell: ${dwell}ms | Speed: ${cps}cps`, "success");
    });

    document.addEventListener("click", (event) => {
        const feed = document.getElementById("telemetryFeed");
        if (feed && feed.contains(event.target)) return;
        clickCount++;
        if (clicksDisplay) clicksDisplay.textContent = clickCount;
        logTelemetry(`MOUSE_CLICK | Coord: (${event.clientX}, ${event.clientY})`, "warning");
    });

    document.addEventListener("mousemove", (event) => {
        const currentTime = Date.now();
        const dx = event.clientX - lastMouseX;
        const dy = event.clientY - lastMouseY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const dt = (currentTime - lastMouseTime) / 1000;
        if (dt > 0) {
            const velocity = distance / dt;
            if (velocityDisplay) velocityDisplay.textContent = velocity.toFixed(2) + " px/s";
            pushFeature(mouseVelocities, mouseVelocityTimestamps, velocity, 100);
        }
        lastMouseX = event.clientX;
        lastMouseY = event.clientY;
        lastMouseTime = currentTime;
    });
}
