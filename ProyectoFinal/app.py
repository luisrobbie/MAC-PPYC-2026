from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import uvicorn
import numpy as np
import threading
import asyncio
from concurrent.futures import ProcessPoolExecutor
import time

app = FastAPI()
executor = ProcessPoolExecutor(max_workers=4)

GRID_WIDTH = 50
GRID_HEIGHT = 30
NUM_THREADS = 4

game_state = {
    "grid": np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=int),
    "generation": 0,
    "lock": threading.Lock()
}

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
async def root():
    return FileResponse(str(static_dir / "index.html"))

def get_neighbors(grid, x, y):
    count = 0
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            nx = (x + dx) % GRID_WIDTH
            ny = (y + dy) % GRID_HEIGHT
            count += grid[ny, nx]
    return count

def _compute_chunk(grid, new_grid, y_start, y_end):
    """Calcula el siguiente estado para las filas [y_start, y_end)."""
    for y in range(y_start, y_end):
        for x in range(GRID_WIDTH):
            neighbors = get_neighbors(grid, x, y)
            alive = grid[y, x] == 1
            if alive and neighbors in [2, 3]:
                new_grid[y, x] = 1
            elif not alive and neighbors == 3:
                new_grid[y, x] = 1

def next_generation(grid):
    start_time = time.time()
    new_grid = np.zeros_like(grid)
    chunk_size = GRID_HEIGHT // NUM_THREADS
    threads = []

    for i in range(NUM_THREADS):
        y_start = i * chunk_size
        y_end = GRID_HEIGHT if i == NUM_THREADS - 1 else (i + 1) * chunk_size
        t = threading.Thread(target=_compute_chunk, args=(grid, new_grid, y_start, y_end))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    elapsed = time.time() - start_time
    print(f"[PARALELO] Generación calculada en {elapsed*1000:.2f}ms")
    return new_grid, elapsed

def count_alive(grid):
    return int(np.sum(grid))

def next_generation_sequential(grid):
    """Versión secuencial pura para comparación"""
    start_time = time.time()
    new_grid = np.zeros_like(grid)
    
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            neighbors = get_neighbors(grid, x, y)
            alive = grid[y, x] == 1
            if alive and neighbors in [2, 3]:
                new_grid[y, x] = 1
            elif not alive and neighbors == 3:
                new_grid[y, x] = 1
    
    elapsed = time.time() - start_time
    print(f"[SECUENCIAL] Generación calculada en {elapsed*1000:.2f}ms")
    return new_grid, elapsed

@app.get("/api/game/state")
async def get_state():
    with game_state["lock"]:
        return {
            "grid": game_state["grid"].tolist(),
            "generation": game_state["generation"],
            "alive": count_alive(game_state["grid"])
        }

@app.post("/api/game/init")
async def init_game():
    with game_state["lock"]:
        game_state["grid"] = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=int)
        game_state["generation"] = 0
    return {"status": "initialized"}

@app.post("/api/game/next")
async def next_step():
    total_start = time.time()
    
    # Tomar snapshot bajo lock para no bloquear lecturas durante el cómputo
    with game_state["lock"]:
        grid_snapshot = game_state["grid"].copy()

    # Ejecutar en ProcessPoolExecutor para paralelismo real sin bloquear el event loop
    loop = asyncio.get_event_loop()
    compute_start = time.time()
    new_grid, compute_internal = await loop.run_in_executor(executor, next_generation, grid_snapshot)
    compute_time = time.time() - compute_start

    with game_state["lock"]:
        game_state["grid"] = new_grid
        game_state["generation"] += 1
        total_time = time.time() - total_start
        
        # Imprimir tiempos en consola
        print(f"[GEN {game_state['generation']}] Interno: {compute_internal*1000:.2f}ms | Con overhead: {compute_time*1000:.2f}ms | Total: {total_time*1000:.2f}ms")
        
        return {
            "generation": game_state["generation"],
            "alive": count_alive(new_grid),
            "grid": new_grid.tolist(),
            "timing": {
                "compute_internal_ms": round(compute_internal * 1000, 2),
                "compute_with_overhead_ms": round(compute_time * 1000, 2),
                "total_ms": round(total_time * 1000, 2)
            }
        }

@app.post("/api/game/randomize")
async def randomize():
    with game_state["lock"]:
        game_state["grid"] = np.random.choice([0, 1], size=(GRID_HEIGHT, GRID_WIDTH), p=[0.7, 0.3])
        game_state["generation"] = 0
        return {
            "generation": game_state["generation"],
            "alive": count_alive(game_state["grid"]),
            "grid": game_state["grid"].tolist()
        }

@app.post("/api/game/clear")
async def clear():
    with game_state["lock"]:
        game_state["grid"] = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=int)
        game_state["generation"] = 0
    return {"status": "cleared"}

@app.post("/api/game/set-cell/{x}/{y}")
async def set_cell(x: int, y: int):
    if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT:
        with game_state["lock"]:
            game_state["grid"][y, x] = 1 - game_state["grid"][y, x]
            return {
                "alive": count_alive(game_state["grid"]),
                "grid": game_state["grid"].tolist()
            }
    return {"error": "Coordenadas fuera de rango"}

@app.get("/api/game/benchmark")
async def benchmark():
    """Compara rendimiento: paralelo vs secuencial"""
    with game_state["lock"]:
        grid_snapshot = game_state["grid"].copy()
    
    # Versión secuencial
    loop = asyncio.get_event_loop()
    seq_grid, seq_time = await loop.run_in_executor(executor, next_generation_sequential, grid_snapshot)
    
    # Versión paralela
    par_grid, par_time = await loop.run_in_executor(executor, next_generation, grid_snapshot)
    
    speedup = seq_time / par_time if par_time > 0 else 0
    
    return {
        "sequential_ms": round(seq_time * 1000, 2),
        "parallel_ms": round(par_time * 1000, 2),
        "speedup": round(speedup, 2),
        "improvement_percent": round((speedup - 1) * 100, 1)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
