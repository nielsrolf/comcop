"""
Aggregate green-beard experiment (smooth RGB-gradient tag, NO spatial structure).

The single-rollout figures elsewhere are one draw of a stochastic process. Here we
run the *same* setup many times and summarize the distribution:

  - agent:   GradientTagBot (continuous RGB "look", mutated by Gaussian drift)
  - pairing: "random" -> uniformly random co-players, i.e. NO location signal.
             Any kin-biased cooperation must come from reading the look alone.

For each of N_RUNS independent seeds we record, per step, the population size,
mean kin-tolerance threshold, and mean pairwise look-similarity. We then plot the
across-run MEAN with a 95% confidence band, and overlay one representative single
rollout so the reader can see both the typical trajectory and the run-to-run spread.
"""
import asyncio
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from agents import GradientTagBot
from games import PrisonersDilemma
from main import World
from utils import rgb_vector_similarity


def avg_pairwise_similarity(agents, max_pairs=200):
    n = len(agents)
    if n < 2:
        return float("nan")
    n_pairs = min(max_pairs, n * (n - 1) // 2)
    tot = 0.0
    for _ in range(n_pairs):
        a, b = random.sample(agents, 2)
        tot += rgb_vector_similarity(a.rgb, b.rgb)
    return tot / n_pairs


async def run_once(seed, n_agents=32, n_steps=150):
    random.seed(seed)
    agents = [GradientTagBot() for _ in range(n_agents)]
    games = [PrisonersDilemma(rounds=4, capacity=2) for _ in range(n_agents // 2)]
    world = World(agents=agents, games=games, resources_to_evolve=4.0, pairing="random")

    pop, tol, sim = [], [], []
    for _ in range(n_steps):
        n = len(world.agents)
        pop.append(n)
        if n:
            tol.append(sum(a.tolerance for a in world.agents) / n)
            sim.append(avg_pairwise_similarity(world.agents))
        else:
            tol.append(float("nan"))
            sim.append(float("nan"))
        if n == 0:
            # pad the rest and stop simulating
            pop += [0] * (n_steps - len(pop))
            tol += [float("nan")] * (n_steps - len(tol))
            sim += [float("nan")] * (n_steps - len(sim))
            break
        random.shuffle(world.games)
        for game in world.games:
            await game.play(world.select_for_game(world.agents, game))
        world.agents = world.evolve()
    return np.array(pop, float), np.array(tol, float), np.array(sim, float)


def band(ax, x, stack, color, label, ci=True):
    mean = np.nanmean(stack, axis=0)
    ax.plot(x, mean, color=color, lw=2, label=label)
    if ci:
        n = np.sum(~np.isnan(stack), axis=0)
        sd = np.nanstd(stack, axis=0)
        se = np.divide(sd, np.sqrt(np.maximum(n, 1)))
        ax.fill_between(x, mean - 1.96 * se, mean + 1.96 * se,
                        color=color, alpha=0.2, linewidth=0)


async def main(n_runs=100, n_steps=150):
    pops, tols, sims = [], [], []
    for s in range(n_runs):
        p, t, sm = await run_once(seed=1000 + s, n_steps=n_steps)
        pops.append(p); tols.append(t); sims.append(sm)
        if s % 20 == 0:
            print(f"run {s}: final_pop={p[-1]:.0f}")
    pops = np.vstack(pops); tols = np.vstack(tols); sims = np.vstack(sims)
    x = np.arange(n_steps)

    # one representative single rollout (median final population)
    order = np.argsort(pops[:, -1])
    rep = order[len(order) // 2]

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    for ax, stack, ttl, ylab, ylim in [
        (axes[0], pops, "Population size", "agents", None),
        (axes[1], tols, "Mean kin-tolerance threshold", "tolerance (0-1)", (0, 1)),
        (axes[2], sims, "Mean pairwise look-similarity", "similarity (0-1)", (0, 1)),
    ]:
        band(ax, x, stack, "#1f77b4", f"mean of {n_runs} runs (95% CI)")
        ax.plot(x, stack[rep], color="#9467bd", lw=1, alpha=0.8, ls="--",
                label="one single rollout")
        ax.set_title(ttl); ax.set_xlabel("Step"); ax.set_ylabel(ylab)
        if ylim:
            ax.set_ylim(*ylim)
    axes[0].legend(fontsize=8, loc="lower right")
    fig.suptitle(f"Gradient green-beard under random pairing (no location): "
                 f"{n_runs} runs, mean ± 95% CI")
    fig.tight_layout()
    fig.savefig("assets/gradient_tag_aggregate.png", dpi=140)
    print("Saved assets/gradient_tag_aggregate.png")

    print("\nFinal-step across-run summary:")
    for name, stack in [("pop", pops), ("tolerance", tols), ("similarity", sims)]:
        col = stack[:, -1]
        print(f"  {name}: mean={np.nanmean(col):.2f} "
              f"sd={np.nanstd(col):.2f} "
              f"[{np.nanpercentile(col,2.5):.2f}, {np.nanpercentile(col,97.5):.2f}]")


if __name__ == "__main__":
    asyncio.run(main())
