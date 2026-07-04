"""
Experiment 3 -- War vs Peace: when does evolution disarm?

Agents split a budget between weapons and peaceful production and carry a
heritable probability of attacking on contact (WarPeaceBot). Two environmental
knobs shape selection:

  x-axis: determinism of war outcomes -- how reliably the better-armed agent
          wins a fight (0 = coin flip, 1 = strength always decides).
  y-axis: return on investment (RoI) of peaceful capital -- how lucrative peace
          is when nobody attacks.

For each (determinism, roi) cell we run the real World for `n_steps` and record
the mean *total welfare* (sum of all agents' resources) and, separately, the
mean evolved aggression. Two heatmaps summarize the phase space.
"""
import asyncio
import random

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agents import WarPeaceBot
from games import WarPeaceGame
from main import World


async def run_once(determinism, roi, n_agents=30, n_steps=80, seed=0):
    random.seed(seed)
    agents = [WarPeaceBot(speed=0.03) for _ in range(n_agents)]
    games = [WarPeaceGame(capacity=2, determinism=determinism, roi=roi)
             for _ in range(n_agents // 2)]
    world = World(agents=agents, games=games, resources_to_evolve=4.0, pairing="proximity")
    for _ in range(n_steps):
        if len(world.agents) == 0:
            break
        random.shuffle(world.games)
        for game in world.games:
            await game.play(world.select_for_game(world.agents, game))
        world.agents = world.evolve()
    if not world.agents:
        return 0.0, float("nan")
    welfare = sum(a.total_reward for a in world.agents)
    aggression = sum(a.aggression for a in world.agents) / len(world.agents)
    return welfare, aggression


async def main():
    determinisms = [0.0, 0.25, 0.5, 0.75, 1.0]
    rois = [0.5, 1.0, 1.5, 2.0, 3.0]
    seeds = [0, 1, 2]

    welfare = np.zeros((len(rois), len(determinisms)))
    aggr = np.zeros((len(rois), len(determinisms)))
    for i, roi in enumerate(rois):
        for j, det in enumerate(determinisms):
            w, a = zip(*[await run_once(det, roi, seed=s) for s in seeds])
            welfare[i, j] = float(np.mean(w))
            aggr[i, j] = float(np.nanmean(a))
            print(f"det={det:.2f} roi={roi:.1f} -> welfare={welfare[i,j]:.0f} aggr={aggr[i,j]:.2f}")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4))
    for ax, grid, title, cmap, label in [
        (axes[0], welfare, "Total welfare (sum of resources)", "viridis", "welfare"),
        (axes[1], aggr, "Mean evolved aggression", "magma", "P(attack)"),
    ]:
        im = ax.imshow(grid, origin="lower", aspect="auto", cmap=cmap)
        ax.set_xticks(range(len(determinisms)))
        ax.set_xticklabels([f"{d:.2f}" for d in determinisms])
        ax.set_yticks(range(len(rois)))
        ax.set_yticklabels([f"{r:.1f}" for r in rois])
        ax.set_xlabel("War-outcome determinism (strength decides)")
        ax.set_ylabel("Peaceful RoI")
        ax.set_title(title)
        vmax = np.nanmax(grid)
        for i in range(len(rois)):
            for j in range(len(determinisms)):
                v = grid[i, j]
                ax.text(j, i, f"{v:.0f}" if label == "welfare" else f"{v:.2f}",
                        ha="center", va="center", fontsize=9,
                        color="white" if v < vmax * 0.6 else "black")
        fig.colorbar(im, ax=ax, label=label)
    fig.suptitle("War vs Peace: welfare and evolved aggression across the (determinism, RoI) plane")
    fig.tight_layout()
    fig.savefig("assets/war_peace_heatmap.png", dpi=140)
    print("Saved assets/war_peace_heatmap.png")


if __name__ == "__main__":
    asyncio.run(main())
