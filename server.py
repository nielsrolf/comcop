from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import json
from pydantic import BaseModel
from typing import List, Tuple
from fastapi.responses import Response
import io
import matplotlib.pyplot as plt

# Import your existing simulation classes and functions
from main import World, RandomAgent, CooperateBot, DefectBot, PrisonersDilemma

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Agent(BaseModel):
    type: str
    location: Tuple[float, float]
    resources: float
    color: str

class Game(BaseModel):
    type: str
    location: Tuple[float, float]

class WorldState(BaseModel):
    agents: List[Agent]
    games: List[Game]

world = None

@app.post("/init_world")
async def init_world(state: WorldState):
    global world
    agents = []
    for agent_data in state.agents:
        if agent_data.type == "RandomAgent":
            agent = RandomAgent()
        elif agent_data.type == "CooperateBot":
            agent = CooperateBot()
        elif agent_data.type == "DefectBot":
            agent = DefectBot()
        else:
            continue  # Skip unknown agent types
        agent.location = agent_data.location
        agent.resources = agent_data.resources
        agents.append(agent)

    games = [PrisonersDilemma(rounds=4, capacity=2, location=game.location) for game in state.games]
    world = World(agents=agents, games=games)
    return {"message": "World initialized"}

@app.get("/world_state")
async def get_world_state():
    if world is None:
        return {"error": "World not initialized"}
    return WorldState(
        agents=[Agent(
            type=type(agent).__name__,
            location=agent.location,
            resources=agent.total_reward,
            color=agent.color if hasattr(agent, 'color') else '#000000'
        ) for agent in world.agents],
        games=[Game(
            type=type(game).__name__,
            location=game.location
        ) for game in world.games]
    )

@app.get("/population_plot")
async def get_population_plot():
    if world is None:
        return Response(content="World not initialized", status_code=400)
    
    plt.figure(figsize=(10, 6))
    world.population_plot()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    
    return Response(content=buf.getvalue(), media_type="image/png")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            if world is None:
                await websocket.send_text(json.dumps({"error": "World not initialized"}))
                await asyncio.sleep(1)
                continue

            await world.run(1)  # Run one step of the simulation
            state = await get_world_state()
            await websocket.send_text(state.json())
            await asyncio.sleep(0.1)  # Adjust this value to control simulation speed
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"Error in WebSocket: {str(e)}")
    finally:
        print("WebSocket connection closed")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)