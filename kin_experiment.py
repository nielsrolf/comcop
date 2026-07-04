"""
Kin-recognition ("green-beard") experiment.

This finishes the half-done "evolution of rules" experiment described in the
doc: does natural selection discover agents that cooperate with agents that
*look* like them (share a similar heritable, mutable "tag"/color) while
defecting against strangers -- without any spatial assortment doing the work
for them?

TagBot (agents.py) carries:
  - color: a 24-bit heritable tag, mutated by flipping one random bit per birth
  - tolerance in [0, 1]: cooperate with a co-player iff their tag similarity
    (fraction of matching bits) is >= tolerance

Population is paired uniformly at random each round (World(pairing="random")),
i.e. there is *no* spatial structure at all -- any kin-biased cooperation
that emerges must come purely from reading the tag, not from meeting
relatives more often. This isolates the tag-recognition mechanism from the
location-based mechanism already demonstrated in baseline_location_experiment.py.
"""
import asyncio
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agents import TagBot
from games import PrisonersDilemma
from main import World


async def main(n_agents=32, n_steps=250, seed=7):
    random.seed(seed)
    agents = [TagBot() for _ in range(n_agents)]
    games = [PrisonersDilemma(rounds=4, capacity=2) for _ in range(n_agents // 2)]
    world = World(agents=agents, games=games, resources_to_evolve=4.0, pairing="random")

    # Track (step, tolerance, color) for every living agent at every step,
    # so we can see both the average trend and whether tag-clusters form.
    individual_points = []

    orig_run_step_hook = world._avg_tolerance  # just to keep a reference; not modified

    for step in range(n_steps):
        if len(world.agents) == 0:
            break
        for a in world.agents:
            individual_points.append((step, a.tolerance, "#" + format(int(a.color.replace(" ", ""), 2), "06x")))
        random.shuffle(world.games)
        for game in world.games:
            selected = world.select_for_game(world.agents, game)
            await game.play(selected)
        world.agents = world.evolve()
        world.population_history.append({"TagBot": len(world.agents)})
        world.tolerance_history.append(world._avg_tolerance())
        world.similarity_history.append(world._avg_pairwise_similarity())
        if step % 25 == 0:
            print(f"step {step}: n={len(world.agents)} avg_tolerance={world.tolerance_history[-1]} "
                  f"avg_similarity={world.similarity_history[-1]}")

    # --- Figure 1: population size + avg tolerance + avg tag similarity ---
    fig, ax1 = plt.subplots(figsize=(10, 5))
    steps = range(len(world.tolerance_history))
    pop = [c.get("TagBot", 0) for c in world.population_history]
    ax1.plot(steps, pop, color="#1f77b4", label="Population size")
    ax1.set_xlabel("Step")
    ax1.set_ylabel("Population size", color="#1f77b4")
    ax1.tick_params(axis="y", labelcolor="#1f77b4")

    ax2 = ax1.twinx()
    tol = [t if t is not None else float("nan") for t in world.tolerance_history]
    sim = [s if s is not None else float("nan") for s in world.similarity_history]
    ax2.plot(steps, tol, color="#d62728", label="Avg. kin-tolerance threshold")
    ax2.plot(steps, sim, color="#2ca02c", linestyle="--", label="Avg. pairwise tag similarity")
    ax2.set_ylabel("Tolerance / similarity (0-1)")
    ax2.set_ylim(0, 1)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)
    fig.suptitle("Tag-based kin recognition: no location, pairing is uniformly random")
    fig.tight_layout()
    fig.savefig("assets/kin_cooperation_evolution.png", dpi=140)
    print("Saved assets/kin_cooperation_evolution.png")

    # --- Figure 2: every individual's tolerance over time, colored by its own tag ---
    fig2, ax = plt.subplots(figsize=(10, 5))
    xs = [p[0] for p in individual_points]
    ys = [p[1] for p in individual_points]
    cs = [p[2] for p in individual_points]
    ax.scatter(xs, ys, c=cs, s=10, alpha=0.6, linewidths=0)
    ax.set_xlabel("Step")
    ax.set_ylabel("Individual tolerance threshold")
    ax.set_title("Each dot = one living agent; color = its own visible tag")
    fig2.tight_layout()
    fig2.savefig("assets/kin_tolerance_individuals.png", dpi=140)
    print("Saved assets/kin_tolerance_individuals.png")

    print("Final population:", len(world.agents))
    print("Final avg tolerance:", world.tolerance_history[-1] if world.tolerance_history else None)
    print("Final avg similarity:", world.similarity_history[-1] if world.similarity_history else None)


if __name__ == "__main__":
    asyncio.run(main())
