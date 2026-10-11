"""Reproducible EDA plots with original codes and no learned preprocessing."""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from heartml.data import load_clean
from heartml.settings import NUMERIC, REPORTS, TARGET


def run() -> None:
    frame = load_clean()
    destination = REPORTS / "figures"
    destination.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook", palette=["#267b97", "#d56f48"])
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.5), constrained_layout=True)
    for ax, column in zip(axes.flat, NUMERIC, strict=False):
        sns.histplot(data=frame, x=column, hue=TARGET, bins=16, element="step", ax=ax)
        ax.set_title(column, weight="bold")
    axes.flat[-1].axis("off")
    fig.suptitle("Cleveland feature distributions by disease class", weight="bold")
    fig.savefig(destination / "histograms.png", dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8.5, 6), constrained_layout=True)
    sns.heatmap(
        frame[NUMERIC + [TARGET]].corr(),
        annot=True,
        fmt=".2f",
        vmin=-1,
        vmax=1,
        cmap="RdBu_r",
        square=True,
        ax=ax,
    )
    ax.set_title("Pearson correlation of numerical fields and target", weight="bold")
    fig.savefig(destination / "correlation.png", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    counts = frame[TARGET].value_counts().sort_index()
    axes[0].bar(["Absent (0)", "Present (1)"], counts, color=["#267b97", "#d56f48"])
    for i, count in enumerate(counts):
        axes[0].text(i, count + 2, str(count), ha="center", weight="bold")
    axes[0].set_ylim(0, counts.max() * 1.18)
    axes[0].set_title("Class balance")
    axes[0].set_ylabel("Patients")
    missing = frame.isna().sum()
    missing[missing > 0].plot.bar(ax=axes[1], color="#267b97", rot=0)
    axes[1].set_title("Missing values retained for fold-local imputation")
    axes[1].set_ylabel("Missing cells")
    fig.savefig(destination / "balance_missing.png", dpi=180)
    plt.close(fig)
    frame.describe().to_csv(REPORTS / "descriptive_statistics.csv")
    (REPORTS / "eda_summary.json").write_text(
        json.dumps(
            {
                "rows": len(frame),
                "class_counts": counts.to_dict(),
                "numeric_target_correlations": frame[NUMERIC + [TARGET]].corr()[TARGET].to_dict(),
            },
            indent=2,
        )
    )
    print(f"EDA plots written to {destination}")


if __name__ == "__main__":
    run()
