"""
War vs Peace, part 2 -- location vs no-location, averaged over many seeds.

Two questions, one experiment:

  1. Does *spatial structure* change the evolutionary outcome? We run the
     identical setup under both pairing rules (see main.py):
       * pairing="proximity" -> the agents nearest each game fight/trade, and
         because children spawn beside parents, neighbours tend to be kin.
       * pairing="random"    -> co-players are drawn uniformly; location is
         irrelevant, the world is well-mixed.

  2. Is the effect robust? Every trajectory is averaged over N_SEEDS runs and
     reported as mean +/-1 SD, so nothing below is a single lucky seed.

For each pairing we record full per-step trajectories -- population, total
welfare, mean evolved aggression, and mean weapon budget -- for three
contrasting environments:

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

PAIRINGS = ["proximity", "random"]

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


async def run_trajectory(pairing, determinism, roi, seed):
    """Return per-step arrays (length N_STEPS) for one seed."""
    random.seed(seed)
    agents = [WarPeaceBot(speed=0.03) for _ in range(N_AGENTS)]
    games = [WarPeaceGame(capacity=2, determinism=determinism, roi=roi)
             for _ in range(N_AGENTS // 2)]
    world = World(agents=agents, games=games, resources_to_evolve=4.0,
                  pairing=pairing)

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
    for pairing in PAIRINGS:
        out[pairing] = {}
        for name, cfg in CONDITIONS.items():
            runs = [await run_trajectory(pairing, cfg["determinism"], cfg["roi"], s)
                    for s in range(N_SEEDS)]
            out[pairing][name] = runs
            print(f"done {pairing}/{name}: {cfg}")
    return out


def stats(runs, key):
    m = np.array([r[key] for r in runs], dtype=float)
    return np.nanmean(m, axis=0), np.nanstd(m, axis=0)


def summarize(data):
    out = {"n_seeds": N_SEEDS, "n_steps": N_STEPS, "pairings": {}}
    for pairing, conds in data.items():
        block = {"conditions": {}}
        for name, runs in conds.items():
            cfg = CONDITIONS[name]
            entry = {"determinism": cfg["determinism"], "roi": cfg["roi"]}
            for key in ("pop", "welfare", "aggr", "weap"):
                mean, sd = stats(runs, key)
                entry[key + "_mean"] = np.nan_to_num(mean).tolist()
                entry[key + "_sd"] = np.nan_to_num(sd).tolist()
            block["conditions"][name] = entry
        out["pairings"][pairing] = block
    return out


async def main():
    data = await gather()
    steps = np.arange(N_STEPS)

    panels = [
        ("pop", "Population"),
        ("welfare", "Total welfare"),
        ("aggr", "Mean aggression P(attack)"),
        ("weap", "Mean weapon budget"),
    ]
    # Rows: proximity (location) vs random (well-mixed).
    fig, axes = plt.subplots(len(PAIRINGS), 4, figsize=(18, 8.4), sharex=True)
    for row, pairing in enumerate(PAIRINGS):
        for col, (key, title) in enumerate(panels):
            ax = axes[row, col]
            for name, runs in data[pairing].items():
                mean, sd = stats(runs, key)
                c = STYLE[name]
                ax.plot(steps, mean, color=c, lw=1.9, label=name)
                ax.fill_between(steps, mean - sd, mean + sd, color=c, alpha=0.15)
            if row == 0:
                ax.set_title(title)
            if row == len(PAIRINGS) - 1:
                ax.set_xlabel("step")
            if key in ("aggr", "weap"):
                ax.set_ylim(0, 1)
        tag = "proximity (location)" if pairing == "proximity" else "random (well-mixed)"
        axes[row, 0].set_ylabel(f"{tag}\n", fontsize=11)
    axes[0, 0].legend(fontsize=9)
    fig.suptitle(f"War vs Peace: location (top) vs well-mixed (bottom), "
                 f"mean +/-1 SD over {N_SEEDS} seeds")
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
