"""
Parameter sweep for take-profit tiers + stop-loss parameters using the project's synthetic generator.

Produces:
- heatmap_avg_return.png
- heatmap_p5_return.png
- heatmap_winrate.png
- tiers_comparison.png

Run (Windows):
    py -m tools.parameter_sweep
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import config
from data_feeder import generate_synthetic_data


Tier = Tuple[float, float]  # (profit_target, portion_to_sell)


@dataclass(frozen=True)
class Params:
    initial_sl: float
    trailing_sl: float
    tiers: Tuple[Tier, ...]


def backtest_one_path(prices: np.ndarray, p: Params) -> Dict[str, float]:
    """
    Simple long-only rule-set consistent with your config intent:
    - Enter at first price (no entry filter, to isolate exit params)
    - Initial stop: entry*(1-initial_sl)
    - Trailing stop: highest*(1-trailing_sl)
    - Effective stop = max(initial_stop, trailing_stop)
    - Tiered take profit sells portions of the *current remaining* position when targets hit
    - Exit remaining when stop is hit, otherwise liquidate at end
    Returns ROI and max drawdown on equity curve (marked-to-market).
    """
    entry = float(prices[0])
    if entry <= 0:
        return {"roi": 0.0, "max_dd": 0.0, "win": 0.0}

    # Normalize to 1.0 "token" position for simplicity
    remaining = 1.0
    cash = 0.0
    triggered = [False] * len(p.tiers)

    initial_stop = entry * (1.0 - p.initial_sl)
    highest = entry

    # Equity curve for drawdown
    equity_curve = []

    for px in prices:
        px = float(px)
        if px <= 0:
            continue

        highest = max(highest, px)
        trailing_stop = highest * (1.0 - p.trailing_sl)
        stop = max(initial_stop, trailing_stop)

        # Take-profit tiers
        for i, (target, portion) in enumerate(p.tiers):
            if triggered[i]:
                continue
            if px >= entry * (1.0 + target) and remaining > 1e-12:
                sell_qty = remaining * float(portion)
                remaining -= sell_qty
                cash += sell_qty * px
                triggered[i] = True

        # Stop-loss / exit remaining
        if remaining > 1e-12 and px <= stop:
            cash += remaining * px
            remaining = 0.0

        equity = cash + remaining * px
        equity_curve.append(equity)

        if remaining <= 1e-12:
            # position fully closed
            break

    # Liquidate if still open at end
    if remaining > 1e-12:
        cash += remaining * float(prices[-1])
        remaining = 0.0
        equity_curve.append(cash)

    final_equity = float(equity_curve[-1]) if equity_curve else 1.0
    roi = final_equity / entry - 1.0  # since initial "cost" is 1 token at entry price

    # Max drawdown on equity curve
    eq = np.array(equity_curve, dtype=float)
    peak = np.maximum.accumulate(eq) if len(eq) else np.array([1.0])
    dd = (eq - peak) / peak
    max_dd = float(dd.min()) if len(dd) else 0.0

    return {"roi": float(roi), "max_dd": float(max_dd), "win": 1.0 if roi > 0 else 0.0}


def simulate_metrics(p: Params, n_paths: int = 250, seed: int = 123) -> Dict[str, float]:
    rois = []
    dds = []
    wins = []

    rng = np.random.default_rng(seed)

    for _ in range(n_paths):
        # Try to vary generator randomness; if generate_synthetic_data uses numpy global RNG,
        # seeding here will still make runs differ.
        np.random.seed(int(rng.integers(0, 2**31 - 1)))

        df = generate_synthetic_data(
            config.SIM_INITIAL_PRICE,
            config.SIM_DRIFT,
            config.SIM_VOLATILITY,
            config.SIM_TIME_STEPS,
        )

        # Use close prices if present, else fall back to any numeric series
        if "close" in df.columns:
            prices = df["close"].to_numpy(dtype=float)
        else:
            # fallback: first numeric column
            col = next(c for c in df.columns if np.issubdtype(df[c].dtype, np.number))
            prices = df[col].to_numpy(dtype=float)

        out = backtest_one_path(prices, p)
        rois.append(out["roi"])
        dds.append(out["max_dd"])
        wins.append(out["win"])

    rois = np.array(rois, dtype=float)
    dds = np.array(dds, dtype=float)
    wins = np.array(wins, dtype=float)

    return {
        "mean_roi": float(rois.mean()),
        "p5_roi": float(np.percentile(rois, 5)),
        "winrate": float(wins.mean()),
        "mean_max_dd": float(dds.mean()),
    }


def make_heatmaps(results: pd.DataFrame, out_dir: str = ".") -> None:
    def heat(metric: str, title: str, fname: str) -> None:
        pivot = results.pivot(index="initial_sl", columns="trailing_sl", values=metric).sort_index()
        plt.figure(figsize=(9, 6))
        plt.imshow(pivot.values, aspect="auto", origin="lower")
        plt.colorbar(label=metric)
        plt.xticks(range(len(pivot.columns)), [f"{x:.2f}" for x in pivot.columns], rotation=45, ha="right")
        plt.yticks(range(len(pivot.index)), [f"{x:.2f}" for x in pivot.index])
        plt.xlabel("TRAILING_STOP_LOSS_PERCENT")
        plt.ylabel("INITIAL_STOP_LOSS_PERCENT")
        plt.title(title)
        plt.tight_layout()
        plt.savefig(f"{out_dir}/{fname}", dpi=160)
        plt.close()

    heat("mean_roi", "Mean ROI heatmap", "heatmap_avg_return.png")
    heat("p5_roi", "5th percentile ROI heatmap (downside)", "heatmap_p5_return.png")
    heat("winrate", "Win rate heatmap", "heatmap_winrate.png")


def tiers_comparison_chart(comp: pd.DataFrame, out_dir: str = ".") -> None:
    # Sort by mean_roi
    comp = comp.sort_values("mean_roi", ascending=False).copy()
    labels = comp["tiers_label"].tolist()
    vals = comp["mean_roi"].to_numpy()

    plt.figure(figsize=(10, 5))
    plt.bar(range(len(vals)), vals)
    plt.xticks(range(len(vals)), labels, rotation=30, ha="right")
    plt.ylabel("Mean ROI")
    plt.title("Take-profit tiers comparison")
    plt.tight_layout()
    plt.savefig(f"{out_dir}/tiers_comparison.png", dpi=160)
    plt.close()


def main() -> None:
    # Sweep SL parameters around your chosen values
    initial_sls = [0.05, 0.10, 0.15, 0.20, 0.25]
    trailing_sls = [0.10, 0.15, 0.20, 0.25, 0.30]

    # Compare a few tier sets (including your current one)
    tier_sets: List[Tuple[Tier, ...]] = [
        ((0.30, 0.33), (0.75, 0.33)),  # current
        ((0.25, 0.33), (0.60, 0.33)),
        ((0.30, 0.50), (0.75, 0.25)),
        ((0.20, 0.33), (0.50, 0.33)),
    ]

    # 1) Heatmaps for the CURRENT tiers (vary SLs)
    current_tiers = tier_sets[0]
    rows: List[Dict[str, Any]] = []
    for ini, tr in itertools.product(initial_sls, trailing_sls):
        p = Params(initial_sl=ini, trailing_sl=tr, tiers=current_tiers)
        m = simulate_metrics(p, n_paths=250, seed=123)
        rows.append(
            {
                "initial_sl": ini,
                "trailing_sl": tr,
                "mean_roi": m["mean_roi"],
                "p5_roi": m["p5_roi"],
                "winrate": m["winrate"],
                "mean_max_dd": m["mean_max_dd"],
            }
        )

    df = pd.DataFrame(rows)
    df.to_csv("sweep_sl_results.csv", index=False)
    make_heatmaps(df, out_dir=".")

    # 2) Compare tiers with fixed SLs near your config (0.15/0.20)
    comp_rows = []
    for tiers in tier_sets:
        p = Params(initial_sl=0.15, trailing_sl=0.20, tiers=tiers)
        m = simulate_metrics(p, n_paths=400, seed=999)
        comp_rows.append(
            {
                "tiers_label": " | ".join([f"+{t[0]*100:.0f}%:{t[1]*100:.0f}%" for t in tiers]),
                "mean_roi": m["mean_roi"],
                "p5_roi": m["p5_roi"],
                "winrate": m["winrate"],
                "mean_max_dd": m["mean_max_dd"],
            }
        )

    comp = pd.DataFrame(comp_rows)
    comp.to_csv("tiers_comparison.csv", index=False)
    tiers_comparison_chart(comp, out_dir=".")

    print("Wrote:")
    print("  sweep_sl_results.csv, heatmap_avg_return.png, heatmap_p5_return.png, heatmap_winrate.png")
    print("  tiers_comparison.csv, tiers_comparison.png")


if __name__ == "__main__":
    main()