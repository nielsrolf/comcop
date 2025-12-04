# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a multiagent evolutionary simulation framework where agents play iterated games (primarily Prisoner's Dilemma), accumulate rewards, and evolve over time. The simulation includes a Python backend for game logic and evolution, and a React frontend for visualization.

## Architecture

### Backend (Python)

The simulation consists of several key components:

- **agents.py**: Base `Agent` class and implementations:
  - `RandomAgent`: Chooses actions randomly
  - `CooperateBot`: Always cooperates
  - `DefectBot`: Always defects
  - `MutatingBot`: Learns rules from game trajectories, mutates patterns and actions during reproduction, and evolves colored "looks" represented as binary strings

- **games.py**: Base `Game` class and implementations:
  - `PrisonersDilemma`: Repeated game with configurable rounds, capacity, noise, and location
  - Rewards are distributed based on cooperation/defection patterns

- **main.py**: Core simulation engine:
  - `World` class orchestrates agent-game interactions
  - Agents move in 2D space (locations wrapped on [0,1] x [0,1] torus)
  - Proximity-based game selection (agents closest to games participate)
  - Evolution: agents consume 1 resource/step, reproduce when accumulating >4 resources (configurable)
  - Outputs timestamped world visualizations to `worlds/{world_id}/` directory

- **server.py**: FastAPI backend with WebSocket support:
  - `/init_world` (POST): Initialize world state from frontend
  - `/world_state` (GET): Get current world state
  - `/population_plot` (GET): Generate matplotlib population plot
  - `/ws` (WebSocket): Stream simulation steps in real-time

- **models.py**: LLM integration layer (unused in current simulation but provides scaffolding for LLM agents)
  - Supports OpenAI, Anthropic, Perplexity, and Together AI APIs
  - Agent class with conversation history and bash execution capability

- **utils.py**: Color conversion utilities (binary strings ↔ RGB hex codes)

### Frontend (React)

Located in `multiagent-simulation/`:

- **SimulationApp.js**: Main UI component
  - Canvas-based 2D visualization
  - Click to place agents/games
  - Real-time WebSocket updates
  - Step-by-step replay with slider
  - Agent hover tooltips (resources, speed)
  - Population plot rendering

### Key Design Patterns

1. **Asynchronous game execution**: All game logic uses `async/await` to support future LLM-based agents
2. **Location-based selection**: Agents are selected for games based on proximity in 2D space
3. **Binary string genetics**: MutatingBot colors and "looks" are binary strings that mutate during reproduction
4. **Rule-based learning**: MutatingBot learns trajectory→action mappings with priority-weighted policies

## Development Commands

### Backend

```bash
# Run simulation locally (generates visualization frames + video)
python main.py

# Start FastAPI server for frontend
python server.py
# Server runs on http://localhost:8000

# Start server with uvicorn directly
uvicorn server:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd multiagent-simulation

# Install dependencies
npm install

# Start development server (http://localhost:3000)
npm start

# Build for production
npm build

# Run tests
npm test
```

## World Output Structure

Simulations create timestamped directories in `worlds/{YYYYMMDDHHMMSS}/`:
- `world_state_round_NNNNNN.png`: Visualization frames
- `population.png`: Population dynamics over time
- `individuals.png`: Individual agent colors over time
- `output.mp4`: Video compilation (requires ffmpeg)

## Important Implementation Notes

1. **Agent reproduction**: When `agent.total_reward > resources_to_evolve` (default 4.0), agents call `.child()` which:
   - Deep copies the agent
   - Spawns child near parent with Gaussian noise
   - For MutatingBot: mutates rules (10% chance per rule), mutates color (flips one bit), mutates speed

2. **Game reward distribution**: In PrisonersDilemma, total reward is distributed proportionally to defection rate, with defectors getting larger shares

3. **Trajectory syntax for MutatingBot**: Observations include:
   - Game start marker: `# Start PrisonersDilemma`
   - Round prompts: `// Round N: Please choose your next action.`
   - Results: `// {name} selected {action} and scored {reward}`
   - Compact action notation: `{my_action} {opponent1_action} {opponent2_action} ...`

4. **Color representation**: Colors are 24-bit binary strings (3 bytes, space-separated bits), converted to hex with `binary_to_rgb()` and `rgb_to_binary()`

5. **WebSocket protocol**: Server continuously runs `world.run(1)` and sends full `WorldState` JSON after each step

## API Dependencies

The codebase includes integration for multiple LLM APIs (models.py):
- OpenAI (GPT models)
- Anthropic (Claude models)
- Perplexity
- Together AI

These require API keys set in environment variables:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `PERPLEXITY`
- `TOGETHER_API_KEY`

Currently unused in the active simulation but available for extending agents with LLM reasoning.
