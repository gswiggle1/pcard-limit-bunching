"""Draw the three README figures from data/processed.pkl and results/*.csv."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from config import PROCESSED, RESULTS, FIGURES, POLICY_DATE, ODOT, PALETTE as P

plt.rcParams.update({"font.size": 11, "axes.edgecolor": P["ink2"], "axes.labelcolor": P["ink2"],
                     "xtick.color": P["ink2"], "ytick.color": P["ink2"]})
PRE, POST = "Before (Dec 2022 to Dec 2024)", "After (Jan 2025 to Sep 2026)"


def style(ax, title):
    ax.set_facecolor(P["surface"])
    ax.set_title(title, loc="left", fontsize=12, color=P["ink"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=P["grid"], lw=0.8)
    ax.set_axisbelow(True)


def fig_histograms(a):
    a = a[~a.higher_ed]
    bins = np.arange(3000, 7100, 100)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), facecolor=P["surface"])
    for ax, (title, sub) in zip(axes, [("State agencies excluding ODOT", a[a.agency != ODOT]),
                                       ("Department of Transportation (ODOT)", a[a.agency == ODOT])]):
        style(ax, title)
        for per, col, lab in [("pre", P["blue"], PRE), ("post", P["orange"], POST)]:
            s = sub[sub.period == per].amount
            c, _ = np.histogram(s, bins)
            ax.step(bins[:-1], c / len(s) * 1e5, where="post", color=col, lw=2, label=f"{lab}, n={len(s):,}")
        ax.axvline(5000, color=P["ink2"], ls="--", lw=1)
        ax.text(5060, ax.get_ylim()[1] * 0.93, "\\$5,000 old limit", color=P["ink2"], fontsize=10)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
        ax.set_xlabel("Transaction amount (\\$100 bins)")
        ax.legend(frameon=False, fontsize=10, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    axes[0].set_ylabel("Charges per 100k transactions")
    fig.suptitle("Charges pile up just under \\$5,000. Outside ODOT the spike shrinks after the limit rises; at ODOT it does not",
                 x=0.01, ha="left", fontsize=13, color=P["ink"])
    plt.tight_layout()
    fig.savefig(FIGURES / "fig1_distribution_near_5k.png", dpi=150, facecolor=P["surface"])


def fig_quarterly():
    q = pd.read_csv(RESULTS / "quarterly.csv")
    q = q[q.quarter != q.quarter.min()]  # first quarter has only one month of data
    fig, ax = plt.subplots(figsize=(11, 5), facecolor=P["surface"])
    style(ax, "Spike just under \\$5,000 by quarter: count in \\$4,800-4,999 relative to a typical \\$200 bin below it")
    quarters = sorted(q.quarter.unique())
    x = np.arange(len(quarters))
    for g, col, dy in [("ODOT", P["orange"], 0), ("Agencies excl. ODOT", P["blue"], -0.06), ("Universities", P["aqua"], 0.06)]:
        z = q[q.group == g].set_index("quarter").reindex(quarters)
        ax.plot(x, z.bunching_ratio, color=col, lw=2, marker="o", ms=5)
        ax.text(x[-1] + 0.25, z.bunching_ratio.iloc[-1] + dy, g, color=P["ink2"], va="center", fontsize=10)
    ax.axhline(1, color="#c3c2b7", lw=1)
    ax.text(-0.4, 0.97, "no spike = 1", color=P["ink2"], fontsize=9, va="top")
    xi = quarters.index("2025Q1")
    ax.axvline(xi - 0.5, color=P["ink2"], ls="--", lw=1)
    ax.text(xi - 0.4, ax.get_ylim()[1] * 0.96, "Limit raised to \\$25,000\n(Jan 2025)", color=P["ink2"], fontsize=9, va="top")
    ax.set_xticks(x[::2]); ax.set_xticklabels(quarters[::2], fontsize=9)
    ax.set_xlim(-0.5, len(x) + 1.6)
    ax.set_ylabel("Bunching ratio")
    plt.tight_layout()
    fig.savefig(FIGURES / "fig2_quarterly.png", dpi=150, facecolor=P["surface"])


def fig_mechanism():
    b = pd.read_csv(RESULTS / "bunching_pooled.csv")
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), facecolor=P["surface"])
    for ax, (T, title) in zip(axes, [(5000, "Extra charges just under \\$5,000 (old limit)"),
                                     (25000, "Extra charges just under \\$25,000 (new limit)")]):
        style(ax, title)
        x, w = np.arange(2), 0.36
        for i, (per, col, lab) in enumerate([("pre", P["blue"], PRE), ("post", P["orange"], POST)]):
            z = b[(b.threshold == T) & (b.period == per)].set_index("group").loc[["Agencies excl. ODOT", "ODOT"]]
            xs = x + (i - 0.5) * w
            ax.bar(xs, z.per100k, w - 0.04, color=col, label=lab, yerr=1.96 * z.se_per100k,
                   error_kw=dict(ecolor=P["ink2"], lw=1, capsize=3))
            for xx, v, e in zip(xs, z.per100k, z.se_per100k):
                ax.text(xx, max(v, 0) + 1.96 * e + ax.get_ylim()[1] * 0.01 + 1, f"{v:.0f}", ha="center", va="bottom", fontsize=9, color=P["ink"])
        ax.axhline(0, color=P["ink2"], lw=0.8)
        ax.set_xticks(x); ax.set_xticklabels(["All other state agencies", "Dept. of Transportation (ODOT)"])
        ax.set_ylabel("Per 100k transactions (95% CI)")
    axes[0].legend(frameon=False, fontsize=10, loc="upper left")
    fig.suptitle("Most agencies moved toward the new \\$25,000 limit; ODOT kept bunching at \\$5,000",
                 x=0.01, ha="left", fontsize=13, color=P["ink"])
    plt.tight_layout()
    fig.savefig(FIGURES / "fig3_mechanism.png", dpi=150, facecolor=P["surface"])


if __name__ == "__main__":
    FIGURES.mkdir(exist_ok=True)
    a = pd.read_pickle(PROCESSED)
    a["period"] = np.where(a.post < POLICY_DATE, "pre", "post")
    fig_histograms(a); fig_quarterly(); fig_mechanism()
    print("figures written to", FIGURES)
