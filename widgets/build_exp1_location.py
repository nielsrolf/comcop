"""
Build script for the Experiment 1 (location & cooperation) widget.

Self-contained static HTML/JS (Chart.js from jsdelivr CDN, client-side sim,
no backend). Source of truth: widgets/exp1_location.html; this copies it into
assets/ as the embed target so the build is deterministic.

Usage:
    python3 widgets/build_exp1_location.py
"""
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "widgets" / "exp1_location.html"
DST = ROOT / "assets" / "exp1_location.html"


def main():
    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, DST)
    print(f"Built {DST} from {SRC}")


if __name__ == "__main__":
    main()
