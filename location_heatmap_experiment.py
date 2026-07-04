"""
Experiment 1 sweep: when does spatial structure actually rescue cooperation?

Location only manufactures kin-assortment if agents stay put long enough for
their offspring to remain their neighbors. If agents move fast, the spatial
correlation between parent and child decays and proximity pairing collapses
toward well-mixed pairing. So the two knobs that should decide a cooperator's
fate are:

  x-axis: agent speed (movement std per step) -- a proxy for "how much does
          location matter"; small speed => strong local kin-assortment.
  y-axis: initial fraction of CooperateBots in the founding population.

For each (speed, coop_fraction) cell we run the real World (proximity pairing)
for `n_steps` and record the mean final CooperateBot count across seeds. The
result is a phase diagram of cooperation.
"""
import asyncio
import random

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agents import CooperateBot, DefectBot
from games import PrisonersDilemma
from main import World


async def run_once(speed, coop_fraction, n_agents=30, n_steps=100, seed=0):
    random.seed(seed)
    n_coop = int(round(coop_fraction * n_agents))
    agents = (
        [CooperateBot(speed=speed) for _ in range(n_coop)]
        + [DefectBot(speed=speed) for _ in range(n_agents - n_coop)]
    )
    games = [PrisonersDilemma(rounds=4, capacity=2) for _ in range(len(agents) // 2)]
    world = World(agents=agents, games=games, resources_to_evolve=4.0, pairing="proximity")
    await world.run(n_steps, visualize_every=None)
    final = world.population_history[-1] if world.population_history else {}
    return final.get("CooperateBot", 0)


async def main():
    speeds = [0.01, 0.03, 0.06, 0.10, 0.16, 0.25]
    coop_fractions = [0.2, 0.35, 0.5, 0.65, 0.8]
    seeds = [0, 1, 2]

    grid = np.zeros((len(coop_fractions), len(speeds)))
    for i, cf in enumerate(coop_fractions):
        for j, sp in enumerate(speeds):
            vals = [await run_once(sp, cf, seed=s) for s in seeds]
            grid[i, j] = float(np.mean(vals))
            print(f"speed={sp:.2f} coop_frac={cf:.2f} -> mean final cooperators={grid[i, j]:.1f}")

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    im = ax.imshow(grid, origin="lower", aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(speeds)))
    ax.set_xticklabels([f"{s:.2f}" for s in speeds])
    ax.set_yticks(range(len(coop_fractions)))
    ax.set_yticklabels([f"{c:.0%}" for c in coop_fractions])
    ax.set_xlabel("Agent speed  (movement std / step — higher ⇒ location matters less)")
    ax.set_ylabel("Initial fraction of CooperateBots")
    ax.set_title("Experiment 1 phase diagram:\nfinal cooperator population (proximity pairing, mean of 3 seeds, 100 steps)")
    for i in range(len(coop_fractions)):
        for j in range(len(speeds)):
            ax.text(j, i, f"{grid[i, j]:.0f}", ha="center", va="center",
                    color="white" if grid[i, j] < grid.max() * 0.6 else "black", fontsize=10)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Final # CooperateBots")
    fig.tight_layout()
    fig.savefig("assets/location_speed_coop_heatmap.png", dpi=140)
    print("Saved assets/location_speed_coop_heatmap.png")


if __name__ == "__main__":
    asyncio.run(main())
