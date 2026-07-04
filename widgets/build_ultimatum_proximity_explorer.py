"""Build the embedded live ultimatum-game simulation widget (proximity pairing).

The widget is a static, self-contained HTML/JS file: a client-side simulation of
the ultimatum game under *proximity* pairing (each game recruits the agents
nearest its location, so neighbors tend to be kin). Agents carry heritable
``offer`` and ``threshold`` genes and evolve by accumulating resources, matching
``UltimatumGame`` / ``UltimatumBot`` in the Python backend. It loads Chart.js from
the jsdelivr CDN and needs no server. The source of truth lives at
widgets/ultimatum_proximity_explorer.html; this script copies it to assets/ as the
embed target so the build is deterministic.

Usage:
    python3 widgets/build_ultimatum_proximity_explorer.py
"""
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "widgets" / "ultimatum_proximity_explorer.html"
DST = ROOT / "assets" / "ultimatum_proximity_explorer.html"


def main():
    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, DST)
    print(f"Built {DST} from {SRC}")


if __name__ == "__main__":
    main()
