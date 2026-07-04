"""
Baseline experiment: does spatial structure ("location") let cooperators
outcompete defectors?

This reproduces/extends the one experiment the doc says is "already
implemented": CooperateBot vs DefectBot in a repeated Prisoner's Dilemma,
where children spawn near their parents. With spatial pairing, a
cooperator's neighbors are disproportionately its own offspring/siblings, so
cooperation gets rewarded locally even though defectors always beat
cooperators in a single 1-on-1 game. Without spatial structure (agents
paired uniformly at random every round), that assortment disappears.

We run the identical starting population and rules through both pairing
modes (World(pairing="proximity") vs World(pairing="random"), see main.py)
and plot the two population trajectories side by side.
"""
import asyncio
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agents import CooperateBot, DefectBot
from games import PrisonersDilemma
from main import World


def make_population(n_cooperate=15, n_defect=15):
    return [CooperateBot() for _ in range(n_cooperate)] + [DefectBot() for _ in range(n_defect)]


async def run_world(pairing, n_steps=150, seed=0):
    random.seed(seed)
    agents = make_population()
    games = [PrisonersDilemma(rounds=4, capacity=2) for _ in range(len(agents) // 2)]
    world = World(agents=agents, games=games, resources_to_evolve=4.0, pairing=pairing)
    await world.run(n_steps, visualize_every=None)
    return world


async def main():
    spatial = await run_world("proximity", seed=42)
    mixed = await run_world("random", seed=42)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, world, title in [
        (axes[0], spatial, "Spatial pairing (location matters)"),
        (axes[1], mixed, "Well-mixed pairing (no location effect)"),
    ]:
        coop = [c.get("CooperateBot", 0) for c in world.population_history]
        defect = [c.get("DefectBot", 0) for c in world.population_history]
        ax.stackplot(
            range(len(coop)), coop, defect,
            labels=["CooperateBot", "DefectBot"],
            colors=["#2ca02c", "#d62728"], alpha=0.85,
        )
        ax.set_title(title)
        ax.set_xlabel("Step")
    axes[0].set_ylabel("Population")
    axes[0].legend(loc="upper left")
    fig.suptitle("Cooperators only win when location creates kin-assortment")
    fig.tight_layout()
    fig.savefig("assets/location_cooperation_population.png", dpi=140)
    print("Saved assets/location_cooperation_population.png")

    final_spatial = spatial.population_history[-1]
    final_mixed = mixed.population_history[-1]
    print("Final (spatial):", dict(final_spatial))
    print("Final (well-mixed):", dict(final_mixed))


if __name__ == "__main__":
    asyncio.run(main())
