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

import numpy as np
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


async def run_many(pairing, seeds, n_steps=150):
    """Run one pairing rule across many seeds; return per-step arrays of the
    CooperateBot and DefectBot counts, aligned to a common length."""
    coop_runs, defect_runs = [], []
    for seed in seeds:
        world = await run_world(pairing, n_steps=n_steps, seed=seed)
        coop_runs.append([c.get("CooperateBot", 0) for c in world.population_history])
        defect_runs.append([c.get("DefectBot", 0) for c in world.population_history])
    length = min(len(r) for r in coop_runs)
    coop = np.array([r[:length] for r in coop_runs], dtype=float)
    defect = np.array([r[:length] for r in defect_runs], dtype=float)
    return coop, defect


async def main():
    seeds = list(range(12))
    n_steps = 150
    spatial_coop, spatial_defect = await run_many("proximity", seeds, n_steps)
    mixed_coop, mixed_defect = await run_many("random", seeds, n_steps)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, coop, defect, title in [
        (axes[0], spatial_coop, spatial_defect, "Spatial pairing (location matters)"),
        (axes[1], mixed_coop, mixed_defect, "Well-mixed pairing (no location effect)"),
    ]:
        steps = range(coop.shape[1])
        for data, color, label in [
            (coop, "#2ca02c", "CooperateBot"),
            (defect, "#d62728", "DefectBot"),
        ]:
            mean = data.mean(axis=0)
            sd = data.std(axis=0)
            ax.plot(steps, mean, color=color, label=label, lw=2)
            ax.fill_between(steps, mean - sd, mean + sd, color=color, alpha=0.2)
        ax.set_title(title)
        ax.set_xlabel("Step")
    axes[0].set_ylabel("Population (mean $\\pm$ 1 SD)")
    axes[0].legend(loc="upper left")
    fig.suptitle(f"Cooperators only win when location creates kin-assortment "
                 f"(mean of {len(seeds)} seeds)")
    fig.tight_layout()
    fig.savefig("assets/location_cooperation_population.png", dpi=140)
    print("Saved assets/location_cooperation_population.png")

    import json
    payload = {
        "seeds": seeds,
        "spatial": {"coop": spatial_coop.tolist(), "defect": spatial_defect.tolist()},
        "mixed": {"coop": mixed_coop.tolist(), "defect": mixed_defect.tolist()},
    }
    with open("assets/location_cooperation_multiseed.json", "w") as f:
        json.dump(payload, f)
    print("Saved assets/location_cooperation_multiseed.json")

    def final(coop, defect):
        return (f"CooperateBot {coop[:, -1].mean():.1f}±{coop[:, -1].std():.1f}, "
                f"DefectBot {defect[:, -1].mean():.1f}±{defect[:, -1].std():.1f}")
    print("Final (spatial):", final(spatial_coop, spatial_defect))
    print("Final (well-mixed):", final(mixed_coop, mixed_defect))


if __name__ == "__main__":
    asyncio.run(main())
