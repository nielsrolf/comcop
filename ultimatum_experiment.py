"""
Experiment: does a fairness norm evolve in the ultimatum game?

Selfish rationality predicts proposers offer ~0 and responders accept ~0. We
let a population of UltimatumBots (heritable `offer` and `threshold`) evolve
under the same resource/reproduction skeleton as the cooperation experiments,
and track the mean offer and mean acceptance threshold over time.

We run two pairing regimes:
  * pairing="random"    -> you bargain with a random stranger.
  * pairing="proximity" -> you tend to bargain with spatial neighbors (kin).

If proximity pairing pushes offers up, "fairness" here is partly kin-driven
generosity, mirroring Experiments 1-2.
"""
import asyncio
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agents import UltimatumBot
from games import UltimatumGame
from main import World


async def run_condition(pairing, n_agents=32, n_steps=200, seed=7, pie=2.0):
    random.seed(seed)
    agents = [UltimatumBot() for _ in range(n_agents)]
    games = [UltimatumGame(rounds=4, capacity=2, pie=pie) for _ in range(n_agents // 2)]
    world = World(agents=agents, games=games, resources_to_evolve=4.0, pairing=pairing)

    pop, offer, thr = [], [], []
    for _ in range(n_steps):
        if len(world.agents) == 0:
            break
        pop.append(len(world.agents))
        offer.append(sum(a.offer for a in world.agents) / len(world.agents))
        thr.append(sum(a.threshold for a in world.agents) / len(world.agents))
        random.shuffle(world.games)
        for game in world.games:
            await game.play(world.select_for_game(world.agents, game))
        world.agents = world.evolve()
    while len(pop) < n_steps:
        pop.append(0); offer.append(float("nan")); thr.append(float("nan"))
    return {"pop": pop, "offer": offer, "thr": thr}


async def main():
    results = {p: await run_condition(p) for p in ("random", "proximity")}

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    styles = {"random": dict(ls="--", color="#8c564b", label="random pairing"),
              "proximity": dict(ls="-", color="#2ca02c", label="proximity pairing")}
    for p, r in results.items():
        s = styles[p]
        steps = range(len(r["pop"]))
        axes[0].plot(steps, r["pop"], **s)
        axes[1].plot(steps, r["offer"], **s)
        axes[2].plot(steps, r["thr"], **s)

    axes[0].set_title("Population size"); axes[0].set_xlabel("Step"); axes[0].set_ylabel("agents")
    axes[1].set_title("Mean offer (proposer generosity)"); axes[1].set_xlabel("Step"); axes[1].set_ylim(0, 1)
    axes[2].set_title("Mean acceptance threshold"); axes[2].set_xlabel("Step"); axes[2].set_ylim(0, 1)
    for ax in axes[1:]:
        ax.axhline(0.5, color="grey", lw=0.8, ls=":")
    axes[0].legend(fontsize=9)
    fig.suptitle("Ultimatum game: evolution of offers and acceptance thresholds")
    fig.tight_layout()
    fig.savefig("assets/ultimatum_evolution.png", dpi=140)
    print("Saved assets/ultimatum_evolution.png")

    for p, r in results.items():
        live = [x for x in r["pop"] if x > 0]
        i = len(live) - 1
        print(f"  {p}: final_pop={r['pop'][i] if live else 0} "
              f"offer~{r['offer'][i]:.2f} thr~{r['thr'][i]:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
