"""Download the GoEmotions full dataset (with rater ids) into data/.

The data directory is gitignored; the archive is not redistributed here.
Source: Demszky et al., "GoEmotions: A Dataset of Fine-Grained Emotions"
(ACL 2020), https://github.com/google-research/google-research/tree/master/goemotions
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

BASE = "https://storage.googleapis.com/gresearch/goemotions/data/full_dataset"
FILES = ["goemotions_1.csv", "goemotions_2.csv", "goemotions_3.csv"]
DATA_DIR = Path(__file__).parent / "data"


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        dest = DATA_DIR / name
        if dest.exists() and dest.stat().st_size > 0:
            print(f"{name}: already present ({dest.stat().st_size / 1e6:.1f} MB)")
            continue
        url = f"{BASE}/{name}"
        print(f"downloading {url}")
        urllib.request.urlretrieve(url, dest)
        print(f"{name}: {dest.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
