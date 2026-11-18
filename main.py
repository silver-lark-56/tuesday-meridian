"""Entry program for the news-image-20261117 bounty (make.fun).

The picture itself is drawn ahead of time by generate.py and stored in this
repository as entry.png. This program has exactly one job: place an exact
copy of that file where the grader expects it. It uses only the Python
standard library, performs no network access, and writes the same bytes on
every run, so two runs always produce identical output.
"""

import os
import shutil
import sys
from pathlib import Path


def main() -> int:
    here = Path(__file__).resolve().parent
    source = here / "entry.png"
    target_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    target = Path(target_dir) / "entry.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    print("wrote", target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
