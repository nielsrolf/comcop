"""
Build script for the in-browser Multiagent Dynamics Explorer widget.

The widget is a static, self-contained HTML/JS file (client-side simulation,
Chart.js loaded from the jsdelivr CDN, no backend/server required). The
source of truth lives at widgets/kin_explorer.html; this script just copies
it into assets/ as the embed target, so the build is deterministic and the
document never depends on files outside the repo.

Usage:
    python3 widgets/build_kin_explorer.py
"""
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "widgets" / "kin_explorer.html"
DST = ROOT / "assets" / "kin_explorer.html"


def main():
    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, DST)
    print(f"Built {DST} from {SRC}")


if __name__ == "__main__":
    main()
