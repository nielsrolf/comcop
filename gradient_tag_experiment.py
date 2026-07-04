"""
Smooth-color-gradient green-beard experiment.

Two questions, one script:

1. Mutation scheme. TagBot's 24-bit tag mutates by flipping ONE bit per birth
   (coarse, discontinuous jumps). GradientTagBot's look is a continuous RGB
   vector mutated by adding Gaussian noise and clipping to [0,1]^3, so lineages
   drift smoothly through color space. Does the smooth version still evolve
   kin-recognition, and does it cluster more tightly?

2. Does location matter. We run each mutation scheme under BOTH:
     - pairing="random"    -> no spatial structure (tag recognition only)
     - pairing="proximity" -> spatial structure (neighbors tend to be kin)

We track, per step: population size, mean kin-tolerance threshold, and mean
pairwise look-similarity (continuous L1 similarity for gradient bots, Hamming
for bit-flip bots). One 2x2 figure summarizes all four conditions.
"""
import asyncio
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agents import TagBot, GradientTagBot
from games import PrisonersDilemma
from main import World
from utils import hamming_similarity, rgb_vector_similarity


def pair_similarity(a, b):
    if hasattr(a, "rgb") and hasattr(b, "rgb"):
        return rgb_vector_similarity(a.rgb, b.rgb)
    return hamming_similarity(a.color, b.color)


def avg_pairwise_similarity(agents, max_pairs=300):
    n = len(agents)
    if n < 2:
        return float("nan")
    n_pairs = min(max_pairs, n * (n - 1) // 2)
    return sum(pair_similarity(*random.sample(agents, 2)) for _ in range(n_pairs)) / n_pairs


async def run_condition(bot_cls, pairing, n_agents=32, n_steps=200, seed=7):
    random.seed(seed)
    agents = [bot_cls() for _ in range(n_agents)]
    games = [PrisonersDilemma(rounds=4, capacity=2) for _ in range(n_agents // 2)]
    world = World(agents=agents, games=games, resources_to_evolve=4.0, pairing=pairing)

    pop, tol, sim = [], [], []
    for step in range(n_steps):
        if len(world.agents) == 0:
            break
        pop.append(len(world.agents))
        tol.append(sum(a.tolerance for a in world.agents) / len(world.agents))
        sim.append(avg_pairwise_similarity(world.agents))
        random.shuffle(world.games)
        for game in world.games:
            await game.play(world.select_for_game(world.agents, game))
        world.agents = world.evolve()
    # pad so all series have equal length for plotting
    while len(pop) < n_steps:
        pop.append(0); tol.append(float("nan")); sim.append(float("nan"))
    return {"pop": pop, "tol": tol, "sim": sim}


async def main():
    conditions = {
        ("bitflip", "random"):     (TagBot, "random"),
        ("bitflip", "proximity"):  (TagBot, "proximity"),
        ("gradient", "random"):    (GradientTagBot, "random"),
        ("gradient", "proximity"): (GradientTagBot, "proximity"),
    }
    results = {}
    for key, (cls, pairing) in conditions.items():
        print("running", key)
        results[key] = await run_condition(cls, pairing)

    styles = {
        ("bitflip", "random"):     dict(color="#d62728", ls="--", label="bit-flip · random"),
        ("bitflip", "proximity"):  dict(color="#d62728", ls="-",  label="bit-flip · proximity"),
        ("gradient", "random"):    dict(color="#1f77b4", ls="--", label="gradient · random"),
        ("gradient", "proximity"): dict(color="#1f77b4", ls="-",  label="gradient · proximity"),
    }

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    for key, r in results.items():
        s = styles[key]
        steps = range(len(r["pop"]))
        axes[0].plot(steps, r["pop"], **s)
        axes[1].plot(steps, r["tol"], **s)
        axes[2].plot(steps, r["sim"], **s)

    axes[0].set_title("Population size"); axes[0].set_xlabel("Step"); axes[0].set_ylabel("agents")
    axes[1].set_title("Mean kin-tolerance threshold"); axes[1].set_xlabel("Step"); axes[1].set_ylim(0, 1)
    axes[2].set_title("Mean pairwise look-similarity"); axes[2].set_xlabel("Step"); axes[2].set_ylim(0, 1)
    axes[0].legend(fontsize=8, loc="upper right")
    fig.suptitle("Smooth RGB-gradient vs one-bit-flip tag mutation, under random vs proximity pairing")
    fig.tight_layout()
    fig.savefig("assets/gradient_tag_mutation.png", dpi=140)
    print("Saved assets/gradient_tag_mutation.png")

    print("\nFinal-state summary:")
    for key, r in results.items():
        live = [p for p in r["pop"] if p > 0]
        print(f"  {key}: final_pop={r['pop'][len(live)-1] if live else 0} "
              f"tol~{r['tol'][len(live)-1] if live else float('nan'):.2f} "
              f"sim~{r['sim'][len(live)-1] if live else float('nan'):.2f}")


if __name__ == "__main__":
    asyncio.run(main())
