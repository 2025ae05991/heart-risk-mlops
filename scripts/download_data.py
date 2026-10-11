"""Run from the repository root: python scripts/download_data.py [--force]."""

import argparse

from heartml.data import acquire, prepare

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    path = acquire(force=args.force)
    frame = prepare(path)
    print(f"Prepared {len(frame)} rows, {len(frame.columns) - 1} raw predictors and binary target.")
