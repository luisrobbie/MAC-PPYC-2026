from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import uvicorn
import numpy as np
import threading

app = FastAPI()

GRID_WIDTH = 50
GRID_HEIGHT = 30

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

def next_generation(grid):
    new_grid = np.zeros_like(grid)
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            neighbors = get_neighbors(grid, x, y)
            alive = grid[y, x] == 1
            if alive and neighbors in [2, 3]:
                new_grid[y, x] = 1
            elif not alive and neighbors == 3:
                new_grid[y, x] = 1
            else:
                new_grid[y, x] = 0
    return new_grid

def count_alive(grid):
    return int(np.sum(grid))

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
    with game_state["lock"]:
        game_state["grid"] = next_generation(game_state["grid"])
        game_state["generation"] += 1
        return {
            "generation": game_state["generation"],
            "alive": count_alive(game_state["grid"]),
            "grid": game_state["grid"].tolist()
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

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
