from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import uvicorn
import numpy as np
import threading
import time
from multiprocessing import Pool
from typing import Optional

app = FastAPI()

GRID_WIDTH  = 50
GRID_HEIGHT = 30
NUM_THREADS = 4   

game_state = {
    "grid":       np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=int),
    "generation": 0,
    "lock":       threading.Lock()
}

_pool: Optional[Pool] = None

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
async def root():
    return FileResponse(str(static_dir / "index.html"))


def _compute_chunk(args):
    grid_list, y_start, y_end, width, height = args
    grid = np.array(grid_list, dtype=int)

    chunk_rows = []
    for y in range(y_start, y_end):
        row = []
        for x in range(width):
            neighbors = 0
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx = (x + dx) % width
                    ny = (y + dy) % height
                    neighbors += grid[ny, nx]
            alive = grid[y, x] == 1
            if alive and neighbors in [2, 3]:
                row.append(1)
            elif not alive and neighbors == 3:
                row.append(1)
            else:
                row.append(0)
        chunk_rows.append(row)

    return y_start, chunk_rows


def next_generation(grid):
    global _pool
    height, width = grid.shape
    grid_list = grid.tolist()

    chunk_size = GRID_HEIGHT // NUM_THREADS
    tasks = []
    for i in range(NUM_THREADS):
        y_start = i * chunk_size
        y_end   = GRID_HEIGHT if i == NUM_THREADS - 1 else (i + 1) * chunk_size
        tasks.append((grid_list, y_start, y_end, width, height))

    # ── Medir el tiempo real de cómputo paralelo ──
    start = time.perf_counter()
    results = _pool.map(_compute_chunk, tasks)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    print(f"Generación calculada en {elapsed_ms} ms")

    new_grid = np.zeros_like(grid)
    for y_start, chunk_rows in results:
        for i, row in enumerate(chunk_rows):
            new_grid[y_start + i] = row

    return new_grid, elapsed_ms


def count_alive(grid):
    return int(np.sum(grid))


@app.on_event("startup")
def startup():
    global _pool
    _pool = Pool(processes=NUM_THREADS)

@app.on_event("shutdown")
def shutdown():
    global _pool
    if _pool:
        _pool.close()
        _pool.join()


@app.get("/api/game/state")
async def get_state():
    with game_state["lock"]:
        return {
            "grid":       game_state["grid"].tolist(),
            "generation": game_state["generation"],
            "alive":      count_alive(game_state["grid"])
        }

@app.post("/api/game/init")
async def init_game():
    with game_state["lock"]:
        game_state["grid"]       = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=int)
        game_state["generation"] = 0
    return {"status": "initialized"}

@app.post("/api/game/next")
async def next_step():
    with game_state["lock"]:
        grid_snapshot = game_state["grid"].copy()

    new_grid, elapsed_ms = next_generation(grid_snapshot)

    with game_state["lock"]:
        game_state["grid"]       = new_grid
        game_state["generation"] += 1
        return {
            "generation": game_state["generation"],
            "alive":      count_alive(new_grid),
            "grid":       new_grid.tolist(),
            "ms":         elapsed_ms       
        }

@app.post("/api/game/randomize")
async def randomize():
    with game_state["lock"]:
        game_state["grid"]       = np.random.choice([0, 1], size=(GRID_HEIGHT, GRID_WIDTH), p=[0.7, 0.3])
        game_state["generation"] = 0
        return {
            "generation": game_state["generation"],
            "alive":      count_alive(game_state["grid"]),
            "grid":       game_state["grid"].tolist()
        }

@app.post("/api/game/clear")
async def clear():
    with game_state["lock"]:
        game_state["grid"]       = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=int)
        game_state["generation"] = 0
    return {"status": "cleared"}

@app.post("/api/game/set-cell/{x}/{y}")
async def set_cell(x: int, y: int):
    if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT:
        with game_state["lock"]:
            game_state["grid"][y, x] = 1 - game_state["grid"][y, x]
            return {
                "alive": count_alive(game_state["grid"]),
                "grid":  game_state["grid"].tolist()
            }
    return {"error": "Coordenadas fuera de rango"}

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.set_start_method("spawn", force=True)
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
