// ============================================================
// modules/canvas.js
// Three canvas renderers:
//  - drawBgRain()      Ambient cyber rain background
//  - drawKinematics()  Live mouse kinematics overlay
//  - drawSecOpsChart() SecOps real-time trust trend chart
// ============================================================

// -----------------------------------------------------------------------
// 1. Background cyber rain
// -----------------------------------------------------------------------
const bgCanvas = document.getElementById("bgCanvas");
const bgCtx = bgCanvas ? bgCanvas.getContext("2d") : null;
const BG_FONT_SIZE = 14;
let bgColumns = [];

function resizeBgCanvas() {
    if (!bgCanvas) return;
    bgCanvas.width = window.innerWidth;
    bgCanvas.height = window.innerHeight;
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

function drawBgRain() {
    if (!bgCanvas || !bgCtx) return;
    const isLight = document.documentElement.getAttribute("data-theme") === "light";
    bgCtx.fillStyle = isLight ? "rgba(248, 250, 252, 0.25)" : "rgba(5, 11, 20, 0.16)";
    bgCtx.fillRect(0, 0, bgCanvas.width, bgCanvas.height);
    bgCtx.font = `${BG_FONT_SIZE}px var(--font-mono)`;
    bgColumns.forEach(col => {
        col.chars.forEach((char, idx) => {
            const yPos = col.y + idx * BG_FONT_SIZE;
            if (yPos > 0 && yPos < bgCanvas.height) {
                if (idx === col.chars.length - 1) {
                    bgCtx.fillStyle = isLight ? "rgba(2, 132, 199, 0.45)" : "rgba(56, 189, 248, 0.30)";
                } else {
                    bgCtx.fillStyle = isLight ? "rgba(2, 132, 199, 0.20)" : "rgba(56, 189, 248, 0.12)";
                }
                bgCtx.fillText(char, col.x, yPos);
            }
        });
        col.y += col.speed;
        if (col.y > bgCanvas.height) {
            col.y = -BG_FONT_SIZE * col.chars.length;
            col.speed = 1.5 + Math.random() * 2.0;
        }
        if (Math.random() > 0.97) {
            col.chars[Math.floor(Math.random() * col.chars.length)] = Math.random() > 0.5 ? "1" : "0";
        }
    });
    requestAnimationFrame(drawBgRain);
}

export function initBgRain() {
    window.addEventListener("resize", resizeBgCanvas);
    resizeBgCanvas();
    if (bgCanvas && bgCtx) requestAnimationFrame(drawBgRain);
}

// -----------------------------------------------------------------------
// 2. Mouse kinematics canvas
// -----------------------------------------------------------------------
const kinCanvas = document.getElementById("kinematicsCanvas");
const kinCtx = kinCanvas ? kinCanvas.getContext("2d") : null;
let mouseHistory = [];
let clickRipples = [];
let currentCanvasMouseX = -1;
let currentCanvasMouseY = -1;

export function initKinematicsCanvas() {
    function resizeCanvas() {
        if (!kinCanvas || !kinCtx) return;
        const rect = kinCanvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        kinCanvas.width = rect.width * dpr;
        kinCanvas.height = (rect.height || 130) * dpr;
        kinCtx.scale(dpr, dpr);
    }
    window.addEventListener("resize", resizeCanvas);
    resizeCanvas();

    document.addEventListener("mousemove", (e) => {
        if (!kinCanvas) return;
        const rect = kinCanvas.getBoundingClientRect();
        currentCanvasMouseX = e.clientX - rect.left;
        currentCanvasMouseY = e.clientY - rect.top;
        mouseHistory.push({ x: currentCanvasMouseX, y: currentCanvasMouseY, age: 0 });
    });

    document.addEventListener("click", (e) => {
        if (!kinCanvas) return;
        const feed = document.getElementById("telemetryFeed");
        if (feed && feed.contains(e.target)) return;
        const rect = kinCanvas.getBoundingClientRect();
        clickRipples.push({ x: e.clientX - rect.left, y: e.clientY - rect.top, radius: 2, maxRadius: 30, alpha: 1.0 });
    });

    requestAnimationFrame(drawKinematics);
}

function drawKinematics() {
    if (!kinCanvas || !kinCtx) return;
    const isLight = document.documentElement.getAttribute("data-theme") === "light";

    if (mouseHistory.length > 1) {
        kinCtx.beginPath();
        kinCtx.strokeStyle = isLight ? "rgba(2, 132, 199, 0.6)" : "rgba(56, 189, 248, 0.3)";
        kinCtx.lineWidth = 2.5;
        kinCtx.lineCap = "round";
        kinCtx.lineJoin = "round";
        kinCtx.moveTo(mouseHistory[0].x, mouseHistory[0].y);
        for (let i = 1; i < mouseHistory.length; i++) kinCtx.lineTo(mouseHistory[i].x, mouseHistory[i].y);
        kinCtx.stroke();
    }

    mouseHistory.forEach(pt => pt.age++);
    mouseHistory = mouseHistory.filter(pt => pt.age < 25);

    if (currentCanvasMouseX >= 0 && currentCanvasMouseX <= kinCanvas.width &&
        currentCanvasMouseY >= 0 && currentCanvasMouseY <= kinCanvas.height) {
        kinCtx.beginPath();
        kinCtx.arc(currentCanvasMouseX, currentCanvasMouseY, 4, 0, 2 * Math.PI);
        kinCtx.fillStyle = "#38bdf8";
        kinCtx.shadowColor = "#38bdf8";
        kinCtx.shadowBlur = 10;
        kinCtx.fill();
        kinCtx.shadowBlur = 0;
    }

    clickRipples.forEach(ripple => {
        kinCtx.beginPath();
        kinCtx.arc(ripple.x, ripple.y, ripple.radius, 0, 2 * Math.PI);
        kinCtx.strokeStyle = `rgba(239, 68, 68, ${ripple.alpha})`;
        kinCtx.lineWidth = 1.5;
        kinCtx.stroke();
        ripple.radius += 1.5;
        ripple.alpha -= 0.04;
    });
    clickRipples = clickRipples.filter(ripple => ripple.alpha > 0);
    requestAnimationFrame(drawKinematics);
}

// -----------------------------------------------------------------------
// 3. SecOps real-time trust trend chart
// -----------------------------------------------------------------------
export function drawSecOpsChart(secopsHistory) {
    const secCanvas = document.getElementById("secopsChart");
    if (!secCanvas) return;
    const sCtx = secCanvas.getContext("2d");
    if (!sCtx) return;

    const rect = secCanvas.getBoundingClientRect();
    const width = rect.width > 0 ? rect.width : (secCanvas.parentElement ? secCanvas.parentElement.clientWidth : 600);
    const height = rect.height > 0 ? rect.height : 110;
    const dpr = window.devicePixelRatio || 1;

    secCanvas.width = width * dpr;
    secCanvas.height = height * dpr;
    sCtx.scale(dpr, dpr);

    const isLight = document.documentElement.getAttribute("data-theme") === "light";
    sCtx.clearRect(0, 0, width, height);
    if (secopsHistory.length < 2) return;

    const step = width / Math.max(secopsHistory.length - 1, 1);
    sCtx.beginPath();
    sCtx.moveTo(0, height - (secopsHistory[0] / 100) * (height - 20) - 10);
    for (let i = 1; i < secopsHistory.length; i++) {
        sCtx.lineTo(i * step, height - (secopsHistory[i] / 100) * (height - 20) - 10);
    }
    sCtx.strokeStyle = isLight ? "#0284c7" : "#38bdf8";
    sCtx.lineWidth = 2.5;
    sCtx.stroke();

    for (let i = 0; i < secopsHistory.length; i++) {
        const x = i * step;
        const y = height - (secopsHistory[i] / 100) * (height - 20) - 10;
        sCtx.beginPath();
        sCtx.arc(x, y, 3, 0, 2 * Math.PI);
        sCtx.fillStyle = secopsHistory[i] >= 50 ? "#10b981" : "#ef4444";
        sCtx.fill();
    }
}

// -----------------------------------------------------------------------
// 4. Spotlight glow — cursor tracking per card
// -----------------------------------------------------------------------
export function initSpotlightGlow() {
    document.querySelectorAll(".card").forEach(card => {
        card.addEventListener("mousemove", (e) => {
            const rect = card.getBoundingClientRect();
            card.style.setProperty("--mouse-x", `${e.clientX - rect.left}px`);
            card.style.setProperty("--mouse-y", `${e.clientY - rect.top}px`);
        });
    });
}
