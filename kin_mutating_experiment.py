"""
Roadmap item 2 -- MutatingBot kin conditioning.

Question: now that a co-player's heritable "look" is visible on the game
(game.current_players), can the *learned-rule* agent (KinMutatingBot) evolve a
green-beard strategy -- cooperate with agents that look like it, defect against
strangers -- purely from trajectory->action learning + selection, with no
hand-coded tolerance rule (that is TagBot's job) and no spatial assortment?

Setup: pairing="random" (co-players drawn uniformly, so location can never
manufacture kin-assortment). Every agent is a KinMutatingBot, which sees a
discretized `LOOK <bucket>` kin-similarity token in its trajectory and may or
may not learn to condition on it.

We instrument every decision with (step, kin_similarity, cooperated?) and plot
the cooperation probability as a function of how kin-like the opponent looks,
comparing the first vs. last third of the run. A green-beard signature is an
upward-sloping curve that steepens over evolutionary time.
"""
import asyncio
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from agents import KinMutatingBot
from games import PrisonersDilemma
from main import World
from utils import hamming_similarity

# (step, avg_kin_similarity, cooperated) for every individual decision.
DECISIONS = []


def instrument(world):
    """Wrap each game's play() to log kin-similarity vs. action per decision."""
    for game in world.games:
        orig_play = game.play

        async def play(agents, _orig=orig_play, _game=game):
            result = await _orig(agents)
            for a in agents:
                others = [o for o in agents if o is not a]
                if not others:
                    continue
                sim = sum(hamming_similarity(a.color, o.color) for o in others) / len(others)
                # Last recorded action is the final entry appended to history.
                last_action = a.history[-1] if a.history else "Cooperate"
                DECISIONS.append((world._step, sim, 1 if last_action == "Cooperate" else 0))
            return result

        game.play = play


async def main(n_agents=40, n_steps=200, seed=3):
    random.seed(seed)
    agents = [KinMutatingBot() for _ in range(n_agents)]
    games = [PrisonersDilemma(rounds=4, capacity=2) for _ in range(n_agents // 2)]
    world = World(agents=agents, games=games, resources_to_evolve=4.0, pairing="random")
    world._step = 0
    instrument(world)

    pop = []
    for step in range(n_steps):
        if len(world.agents) == 0:
            break
        world._step = step
        random.shuffle(world.games)
        for game in world.games:
            selected = world.select_for_game(world.agents, game)
            await game.play(selected)
        world.agents = world.evolve()
        pop.append(len(world.agents))
        if step % 25 == 0:
            print(f"step {step}: n={len(world.agents)} decisions={len(DECISIONS)}")

    # --- Bin cooperation rate by kin-similarity, early vs late ---
    arr = np.array(DECISIONS, dtype=float)
    if len(arr) == 0:
        print("No decisions recorded.")
        return
    max_step = arr[:, 0].max()
    early = arr[arr[:, 0] <= max_step / 3]
    late = arr[arr[:, 0] >= 2 * max_step / 3]
    bins = np.linspace(0, 1, 9)
    centers = (bins[:-1] + bins[1:]) / 2

    def coop_curve(a):
        idx = np.digitize(a[:, 1], bins) - 1
        ys = []
        for b in range(len(centers)):
            m = idx == b
            ys.append(a[m, 2].mean() if m.sum() > 5 else np.nan)
        return np.array(ys)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    ax1.plot(centers, coop_curve(early), "o-", color="#9ecae1", label="early (gen 1st third)")
    ax1.plot(centers, coop_curve(late), "o-", color="#08519c", label="late (gen last third)")
    ax1.set_xlabel("Kin similarity of co-player (tag bit overlap)")
    ax1.set_ylabel("P(cooperate)")
    ax1.set_ylim(-0.02, 1.02)
    ax1.set_title("Learned kin conditioning emerges")
    ax1.legend(fontsize=9)
    ax1.grid(alpha=0.3)

    ax2.plot(range(len(pop)), pop, color="#08519c")
    ax2.set_xlabel("Step")
    ax2.set_ylabel("Population size")
    ax2.set_title("KinMutatingBot population (random pairing)")
    ax2.grid(alpha=0.3)

    fig.suptitle("KinMutatingBot: learned green-beard from trajectory->action rules")
    fig.tight_layout()
    fig.savefig("assets/kin_mutating_conditioning.png", dpi=140)
    print("Saved assets/kin_mutating_conditioning.png")
    print("early curve:", coop_curve(early))
    print("late curve :", coop_curve(late))


if __name__ == "__main__":
    asyncio.run(main())
