// ===============================
// TrustGuard AI - Feature Capture
// ===============================

// Get HTML elements
const typingArea = document.getElementById("typingArea");

const dwellDisplay = document.getElementById("dwell");
const flightDisplay = document.getElementById("flight");
const speedDisplay = document.getElementById("speed");
const velocityDisplay = document.getElementById("velocity");
const clicksDisplay = document.getElementById("clicks");

// ===============================
// Variables
// ===============================

let keyDownTime = 0;
let previousKeyUp = 0;

let totalCharacters = 0;
let sessionStart = Date.now();

let clickCount = 0;

let lastMouseX = 0;
let lastMouseY = 0;
let lastMouseTime = Date.now();

// Arrays to store feature values
let dwellTimes = [];
let flightTimes = [];
let mouseVelocities = [];

// ===============================
// Key Press Event
// ===============================

typingArea.addEventListener("keydown", function () {

    keyDownTime = Date.now();

    if (previousKeyUp !== 0) {

        const flightTime = keyDownTime - previousKeyUp;

        flightDisplay.textContent = flightTime + " ms";

        flightTimes.push(flightTime);

    }

});

// ===============================
// Key Release Event
// ===============================

typingArea.addEventListener("keyup", function () {

    const keyUpTime = Date.now();

    const dwellTime = keyUpTime - keyDownTime;

    dwellDisplay.textContent = dwellTime + " ms";

    dwellTimes.push(dwellTime);

    previousKeyUp = keyUpTime;

    totalCharacters++;

    // Typing Speed
    const elapsedSeconds = (Date.now() - sessionStart) / 1000;

    const typingSpeed = (totalCharacters / elapsedSeconds).toFixed(2);

    speedDisplay.textContent = typingSpeed + " cps";

});

// ===============================
// Mouse Click Counter
// ===============================

document.addEventListener("click", function () {

    clickCount++;

    clicksDisplay.textContent = clickCount;

});

// ===============================
// Mouse Velocity
// ===============================

document.addEventListener("mousemove", function (event) {

    const currentTime = Date.now();

    const dx = event.clientX - lastMouseX;
    const dy = event.clientY - lastMouseY;

    const distance = Math.sqrt(dx * dx + dy * dy);

    const dt = (currentTime - lastMouseTime) / 1000;

    if (dt > 0) {

        const velocity = distance / dt;

        velocityDisplay.textContent = velocity.toFixed(2) + " px/s";

        mouseVelocities.push(velocity);

    }

    lastMouseX = event.clientX;
    lastMouseY = event.clientY;
    lastMouseTime = currentTime;

});