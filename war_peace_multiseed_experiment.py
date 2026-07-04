"""
War vs Peace, part 2 -- how do things evolve *on average*, and is the effect
robust across seeds?

The single heatmap in `war_peace_experiment.py` only reports the *final* state
of each (determinism, RoI) cell. Here we instead record full per-step
trajectories -- population, total welfare, mean evolved aggression, and mean
weapon budget -- and average them across many seeds (with +/-1 SD bands) for a
few contrasting environments:

  * "peaceful"  : low determinism, high RoI   -> evolution should disarm
  * "arms race" : high determinism, mid RoI   -> aggression + weapons climb
  * "collapse"  : high determinism, low RoI   -> upkeep not covered, extinction

Run standalone to produce assets/war_peace_multiseed.png, or with `--json` to
dump assets/war_peace_multiseed.json for the interactive widget.
"""
import asyncio
import random
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agents import WarPeaceBot
from games import WarPeaceGame
from main import World

N_SEEDS = 20
N_STEPS = 80
N_AGENTS = 30

CONDITIONS = {
    "peaceful":  dict(determinism=0.25, roi=2.0),
    "arms race": dict(determinism=1.00, roi=1.5),
    "collapse":  dict(determinism=1.00, roi=0.75),
}
STYLE = {
    "peaceful":  "#2ca02c",
    "arms race": "#d62728",
    "collapse":  "#7f7f7f",
}


async def run_trajectory(determinism, roi, seed):
    """Return per-step arrays (length N_STEPS) for one seed."""
    random.seed(seed)
    agents = [WarPeaceBot(speed=0.03) for _ in range(N_AGENTS)]
    games = [WarPeaceGame(capacity=2, determinism=determinism, roi=roi)
             for _ in range(N_AGENTS // 2)]
    world = World(agents=agents, games=games, resources_to_evolve=4.0,
                  pairing="proximity")

    pop, welfare, aggr, weap = [], [], [], []
    for _ in range(N_STEPS):
        if world.agents:
            random.shuffle(world.games)
            for game in world.games:
                await game.play(world.select_for_game(world.agents, game))
            world.agents = world.evolve()
        n = len(world.agents)
        pop.append(n)
        welfare.append(sum(a.total_reward for a in world.agents) if n else 0.0)
        aggr.append(sum(a.aggression for a in world.agents) / n if n else np.nan)
        weap.append(sum(a.weapon_fraction for a in world.agents) / n if n else np.nan)
    return dict(pop=pop, welfare=welfare, aggr=aggr, weap=weap)


async def gather():
    out = {}
    for name, cfg in CONDITIONS.items():
        runs = [await run_trajectory(cfg["determinism"], cfg["roi"], s)
                for s in range(N_SEEDS)]
        out[name] = runs
        print(f"done {name}: {cfg}")
    return out


def stats(runs, key):
    m = np.array([r[key] for r in runs], dtype=float)
    return np.nanmean(m, axis=0), np.nanstd(m, axis=0)


def summarize(data):
    out = {"n_seeds": N_SEEDS, "n_steps": N_STEPS, "conditions": {}}
    for name, runs in data.items():
        cfg = CONDITIONS[name]
        entry = {"determinism": cfg["determinism"], "roi": cfg["roi"]}
        for key in ("pop", "welfare", "aggr", "weap"):
            mean, sd = stats(runs, key)
            entry[key + "_mean"] = np.nan_to_num(mean).tolist()
            entry[key + "_sd"] = np.nan_to_num(sd).tolist()
        out["conditions"][name] = entry
    return out


async def main():
    data = await gather()
    steps = np.arange(N_STEPS)

    fig, axes = plt.subplots(1, 4, figsize=(18, 4.4))
    panels = [
        ("pop", "Population"),
        ("welfare", "Total welfare"),
        ("aggr", "Mean aggression P(attack)"),
        ("weap", "Mean weapon budget"),
    ]
    for ax, (key, title) in zip(axes, panels):
        for name, runs in data.items():
            mean, sd = stats(runs, key)
            c = STYLE[name]
            ax.plot(steps, mean, color=c, lw=1.9, label=name)
            ax.fill_between(steps, mean - sd, mean + sd, color=c, alpha=0.15)
        ax.set_title(title)
        ax.set_xlabel("step")
        if key in ("aggr", "weap"):
            ax.set_ylim(0, 1)
    axes[0].legend(fontsize=9)
    fig.suptitle(f"War vs Peace dynamics averaged over {N_SEEDS} seeds "
                 f"(mean +/-1 SD)")
    fig.tight_layout()
    fig.savefig("assets/war_peace_multiseed.png", dpi=140)
    print("Saved assets/war_peace_multiseed.png")


def dump_json():
    data = asyncio.run(gather())
    import json
    with open("assets/war_peace_multiseed.json", "w") as f:
        json.dump(summarize(data), f)
    print("Saved assets/war_peace_multiseed.json")


if __name__ == "__main__":
    if "--json" in sys.argv:
        dump_json()
    else:
        asyncio.run(main())
