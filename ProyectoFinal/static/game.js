const CELL_SIZE = 20;
const GRID_WIDTH = 50;
const GRID_HEIGHT = 30;
const API_BASE = "/api/game";

const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

let grid = [];
let isPlaying = false;
let generation = 0;
let speed = 5;
let animationId = null;

function resizeCanvas() {
    const container = canvas.parentElement;
    const rect = container.getBoundingClientRect();
    const size = Math.min(rect.width, rect.height) - 20;

    canvas.width = size;
    canvas.height = size;
}

function draw() {
    const cellWidth = canvas.width / GRID_WIDTH;
    const cellHeight = canvas.height / GRID_HEIGHT;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (let y = 0; y < GRID_HEIGHT; y++) {
        for (let x = 0; x < GRID_WIDTH; x++) {
            if (grid[y] && grid[y][x] === 1) {
                ctx.fillStyle = '#22C55E';
                ctx.fillRect(x * cellWidth, y * cellHeight, cellWidth - 1, cellHeight - 1);
            }
        }
    }

    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 0.5;

    for (let x = 0; x <= GRID_WIDTH; x++) {
        ctx.beginPath();
        ctx.moveTo(x * (canvas.width / GRID_WIDTH), 0);
        ctx.lineTo(x * (canvas.width / GRID_WIDTH), canvas.height);
        ctx.stroke();
    }

    for (let y = 0; y <= GRID_HEIGHT; y++) {
        ctx.beginPath();
        ctx.moveTo(0, y * (canvas.height / GRID_HEIGHT));
        ctx.lineTo(canvas.width, y * (canvas.height / GRID_HEIGHT));
        ctx.stroke();
    }
}

function updateStats(alive) {
    document.getElementById('generation').textContent = generation;
    document.getElementById('alive').textContent = alive || 0;
}

async function apiCall(endpoint, method = 'GET') {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: method,
            headers: { 'Content-Type': 'application/json' }
        });
        return await response.json();
    } catch (error) {
        console.error('Error en API:', error);
        return null;
    }
}

async function getState() {
    const data = await apiCall('/state');
    if (data) {
        grid = data.grid;
        generation = data.generation;
        updateStats(data.alive);
        draw();
    }
}

async function nextGeneration() {
    const data = await apiCall('/next', 'POST');
    if (data) {
        grid = data.grid;
        generation = data.generation;
        updateStats(data.alive);
        draw();
    }
}

function animate() {
    if (isPlaying) {
        nextGeneration();
    }
    draw();

    const delay = 1000 / (speed * 2);
    setTimeout(() => {
        animationId = requestAnimationFrame(animate);
    }, delay);
}

function togglePlay() {
    isPlaying = !isPlaying;
    const btn = document.getElementById('playBtn');
    btn.textContent = isPlaying ? '⏸ Pausar' : '▶ Play';
    btn.classList.toggle('active', isPlaying);
    document.getElementById('status').textContent = isPlaying ? 'Ejecutando' : 'Pausado';
}

async function reset() {
    isPlaying = false;
    await apiCall('/init', 'POST');
    const playBtn = document.getElementById('playBtn');
    playBtn.textContent = '▶ Play';
    playBtn.classList.remove('active');
    document.getElementById('status').textContent = 'Pausado';
    await getState();
}

async function randomize() {
    const data = await apiCall('/randomize', 'POST');
    if (data) {
        grid = data.grid;
        generation = data.generation;
        updateStats(data.alive);
        draw();
    }
}

async function clear() {
    await apiCall('/clear', 'POST');
    await getState();
}

function changeSpeed() {
    speed = parseInt(document.getElementById('speedSlider').value);
    document.getElementById('speedValue').textContent = speed;
}

document.getElementById('playBtn').addEventListener('click', togglePlay);
document.getElementById('resetBtn').addEventListener('click', reset);
document.getElementById('randomBtn').addEventListener('click', randomize);
document.getElementById('clearBtn').addEventListener('click', clear);
document.getElementById('nextBtn').addEventListener('click', nextGeneration);
document.getElementById('speedSlider').addEventListener('input', changeSpeed);

canvas.addEventListener('click', async (e) => {
    const rect = canvas.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) * GRID_WIDTH / rect.width);
    const y = Math.floor((e.clientY - rect.top) * GRID_HEIGHT / rect.height);

    if (x >= 0 && x < GRID_WIDTH && y >= 0 && y < GRID_HEIGHT) {
        const data = await apiCall(`/set-cell/${x}/${y}`, 'POST');
        if (data) {
            grid = data.grid;
            updateStats(data.alive);
            draw();
        }
    }
});

async function init() {
    resizeCanvas();
    await getState();
    animate();
}

init();

window.addEventListener('resize', () => {
    resizeCanvas();
    draw();
});
