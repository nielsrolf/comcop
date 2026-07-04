"""
Build script for the embedded green-beard simulation widget (Experiment 2).

The widget is a static, self-contained HTML/JS file: a client-side re-implementation
of the tag-based kin-recognition experiment with uniformly random pairing. It loads
Chart.js from the jsdelivr CDN and needs no backend. The source of truth lives at
widgets/greenbeard_explorer.html; this script copies it to assets/ as the embed
target so the build is deterministic and the document never depends on files
outside the repo.

Usage:
    python3 widgets/build_greenbeard_explorer.py
"""
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "widgets" / "greenbeard_explorer.html"
DST = ROOT / "assets" / "greenbeard_explorer.html"


def main():
    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, DST)
    print(f"Built {DST} from {SRC}")


if __name__ == "__main__":
    main()
