"""Run acquisition, EDA, and training in dependency order."""

import argparse

from heartml.data import acquire, prepare
from heartml.eda import run as eda
from heartml.train import train

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    prepare(acquire())
    eda()
    train(quick=args.quick)
