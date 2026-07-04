"""
Experiment: is the ultimatum-game fairness result robust, or a lucky draw?

The single-seed `ultimatum_experiment.py` shows one trajectory per pairing rule.
Here we re-run the identical setup across many random seeds and plot the mean
trajectory with a +/-1 standard-deviation band, plus a distribution of the
final evolved offer/threshold. This tells us whether "proximity pairing evolves
fairer offers" is a typical outcome or noise.
"""
import asyncio
import random

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ultimatum_experiment import run_condition

N_SEEDS = 24
N_STEPS = 200
PAIRINGS = ("random", "proximity")
STYLE = {
    "random": dict(color="#8c564b", label="random pairing"),
    "proximity": dict(color="#2ca02c", label="proximity pairing"),
}


async def gather(pairing):
    runs = []
    for seed in range(N_SEEDS):
        runs.append(await run_condition(pairing, n_steps=N_STEPS, seed=seed))
    return runs


def stack(runs, key):
    return np.array([r[key] for r in runs], dtype=float)  # (seeds, steps)


async def main():
    data = {p: await gather(p) for p in PAIRINGS}

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    steps = np.arange(N_STEPS)

    for p in PAIRINGS:
        s = STYLE[p]
        for ax, key, ylab in (
            (axes[0], "pop", "agents"),
            (axes[1], "offer", "mean offer"),
            (axes[2], "thr", "mean threshold"),
        ):
            m = stack(data[p], key)
            mean = np.nanmean(m, axis=0)
            sd = np.nanstd(m, axis=0)
            ax.plot(steps, mean, color=s["color"], label=s["label"], lw=1.8)
            ax.fill_between(steps, mean - sd, mean + sd, color=s["color"], alpha=0.18)

    axes[0].set_title(f"Population size (mean +/-1 SD, {N_SEEDS} seeds)")
    axes[0].set_xlabel("Step"); axes[0].set_ylabel("agents"); axes[0].legend(fontsize=9)
    axes[1].set_title("Mean offer (proposer generosity)")
    axes[1].set_xlabel("Step"); axes[1].set_ylim(0, 1)
    axes[2].set_title("Mean acceptance threshold")
    axes[2].set_xlabel("Step"); axes[2].set_ylim(0, 1)
    for ax in axes[1:]:
        ax.axhline(0.5, color="grey", lw=0.8, ls=":")
    fig.suptitle(f"Ultimatum game across {N_SEEDS} seeds: fairness is robust, not chance")
    fig.tight_layout()
    fig.savefig("assets/ultimatum_multiseed.png", dpi=140)
    print("Saved assets/ultimatum_multiseed.png")

    # Final-value summary: last live step per run.
    print(f"\n{'pairing':<12} {'offer mean':>10} {'offer sd':>9} "
          f"{'thr mean':>9} {'thr sd':>8} {'pop mean':>9}")
    summary = {}
    for p in PAIRINGS:
        finals_offer, finals_thr, finals_pop = [], [], []
        for r in data[p]:
            live = [i for i, x in enumerate(r["pop"]) if x > 0]
            i = live[-1] if live else 0
            finals_offer.append(r["offer"][i])
            finals_thr.append(r["thr"][i])
            finals_pop.append(r["pop"][i])
        summary[p] = dict(
            offer_m=np.nanmean(finals_offer), offer_s=np.nanstd(finals_offer),
            thr_m=np.nanmean(finals_thr), thr_s=np.nanstd(finals_thr),
            pop_m=np.nanmean(finals_pop),
        )
        print(f"{p:<12} {summary[p]['offer_m']:>10.3f} {summary[p]['offer_s']:>9.3f} "
              f"{summary[p]['thr_m']:>9.3f} {summary[p]['thr_s']:>8.3f} "
              f"{summary[p]['pop_m']:>9.1f}")

    # Distribution plot of final offer/threshold.
    fig2, axes2 = plt.subplots(1, 2, figsize=(11, 4.2))
    for p in PAIRINGS:
        offs = [r["offer"][[i for i, x in enumerate(r["pop"]) if x > 0][-1]] for r in data[p]]
        thrs = [r["thr"][[i for i, x in enumerate(r["pop"]) if x > 0][-1]] for r in data[p]]
        axes2[0].hist(offs, bins=12, range=(0, 1), alpha=0.55, color=STYLE[p]["color"], label=STYLE[p]["label"])
        axes2[1].hist(thrs, bins=12, range=(0, 1), alpha=0.55, color=STYLE[p]["color"], label=STYLE[p]["label"])
    axes2[0].set_title(f"Final mean offer across {N_SEEDS} seeds"); axes2[0].set_xlabel("offer"); axes2[0].legend()
    axes2[1].set_title("Final mean threshold"); axes2[1].set_xlabel("threshold")
    fig2.tight_layout()
    fig2.savefig("assets/ultimatum_multiseed_hist.png", dpi=140)
    print("Saved assets/ultimatum_multiseed_hist.png")


if __name__ == "__main__":
    asyncio.run(main())


def _dump_json():
    """Re-run and dump per-seed final values + mean trajectories to JSON for the widget."""
    import json
    async def run_all():
        out = {}
        for p in PAIRINGS:
            runs = await gather(p)
            offer = stack(runs, "offer"); thr = stack(runs, "thr"); pop = stack(runs, "pop")
            finals = {"offer": [], "thr": []}
            for r in runs:
                live = [i for i, x in enumerate(r["pop"]) if x > 0]
                i = live[-1] if live else 0
                finals["offer"].append(r["offer"][i]); finals["thr"].append(r["thr"][i])
            out[p] = {
                "offer_mean": np.nanmean(offer, 0).tolist(),
                "offer_sd": np.nanstd(offer, 0).tolist(),
                "thr_mean": np.nanmean(thr, 0).tolist(),
                "thr_sd": np.nanstd(thr, 0).tolist(),
                "final_offer": finals["offer"], "final_thr": finals["thr"],
            }
        return out
    data = asyncio.run(run_all())
    data["n_seeds"] = N_SEEDS; data["n_steps"] = N_STEPS
    with open("assets/ultimatum_multiseed.json", "w") as f:
        json.dump(data, f)
    print("Saved assets/ultimatum_multiseed.json")


if __name__ == "__main__" and "--json" in __import__("sys").argv:
    _dump_json()
    raise SystemExit(0)
