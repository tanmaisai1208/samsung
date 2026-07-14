Battery Management - Charging Schedule Prediction (Top-1 Peak per Day)
======================================================================================
Reuses the same daily rolling-window XGBoost model/features as
battery_final_validation.py (no clipping — full +ve/-ve dSocdt signal).

SIMPLIFIED OBJECTIVE:
  For each day, find the SINGLE strongest charging event (highest total SoC
  rise) in the ACTUAL curve and the SINGLE strongest in the PREDICTED curve.
  Compare their representative hours directly via MAE. No TP/FP/FN — with
  only one peak per side, this reduces cleanly to a pure timing-error metric.

Outputs (results/xgboost/charging_schedule/):
  charging_schedule_predictions_<device>.csv
  charging_schedule_summary.csv
  charging_schedule_mae_plot.png
  charging_schedule_sample_days_<device>.png
"""

import os
import glob
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from xgboost import XGBRegressor
from sklearn.multioutput import MultiOutputRegressor

warnings.filterwarnings("ignore")

BEST_PARAMS = {
    "n_estimators": 200, "max_depth": 2, "learning_rate": 0.1,
    "subsample": 0.95, "colsample_bytree": 0.8,
    "random_state": 42, "verbosity": 0,
}

WIDE_CSV_FOLDER = "results/wide_csv"
OUTPUT_FOLDER   = "results/xgboost/charging_schedule"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

TRAIN_DAYS = 14
HOURS      = list(range(24))

# Per-hour rate threshold to count an hour as "rising" (same as before)
MIN_HOURLY_RISE_ACTUAL = 0.007
MIN_HOURLY_RISE_PRED   = 0.0055

DSOCDT_COLS     = [f"dSocdt_h{h}" for h in HOURS]
SOC_COLS        = [f"Soc_h{h}"    for h in HOURS]
DATE_FEAT_COUNT = 4
FEATS_PER_DAY   = len(DSOCDT_COLS) + len(SOC_COLS) + DATE_FEAT_COUNT


def date_feats(date_str):
    ts = pd.Timestamp(date_str)
    return [float(ts.dayofweek), float(ts.day), float(ts.month), float(ts.year)]

def build_feature_row(wide, train_start, train_end):
    feats = []
    for i in range(train_start, train_end):
        feats.extend(wide.iloc[i][DSOCDT_COLS].tolist())
        feats.extend(wide.iloc[i][SOC_COLS].tolist())
        feats.extend(date_feats(wide.index[i]))
    return np.array(feats, dtype=float)

def build_padded_feature_row(wide, context_start, context_end, pad_days):
    feats = [0.0] * (pad_days * FEATS_PER_DAY)
    for i in range(context_start, context_end):
        feats.extend(wide.iloc[i][DSOCDT_COLS].tolist())
        feats.extend(wide.iloc[i][SOC_COLS].tolist())
        feats.extend(date_feats(wide.index[i]))
    return feats


def find_top_peak(dsocdt_24h, min_hourly_rise):
    """
    Scan a 24h dSocdt vector, find all contiguous rising runs (hourly rate >
    min_hourly_rise), and return the representative hour (rise-weighted
    average) of the run with the LARGEST total rise (sum*60). Returns None
    if no rising run exists at all.
    """
    n = len(dsocdt_24h)
    runs = []
    i = 0
    while i < n:
        v = dsocdt_24h[i]
        if not np.isnan(v) and v > min_hourly_rise:
            run_hours, run_vals = [i], [v]
            j = i + 1
            while j < n and not np.isnan(dsocdt_24h[j]) and dsocdt_24h[j] > min_hourly_rise:
                run_hours.append(j); run_vals.append(dsocdt_24h[j]); j += 1
            total_rise = float(np.sum(run_vals)) * 60
            weighted_hour = float(np.average(run_hours, weights=run_vals))
            runs.append((total_rise, weighted_hour))
            i = j
        else:
            i += 1
    if not runs:
        return None
    return max(runs, key=lambda x: x[0])[1]   # hour of the run with max total_rise


def run_predictions(wide, device_name):
    n_days, results = len(wide), []
    model = MultiOutputRegressor(XGBRegressor(**BEST_PARAMS), n_jobs=-1)
    total = n_days - TRAIN_DAYS
    print(f"  Predicting {total} days...")

    for predict_day_idx in range(TRAIN_DAYS, n_days):
        train_start, train_end = predict_day_idx - TRAIN_DAYS, predict_day_idx
        predict_date = wide.index[predict_day_idx]

        X_train, y_train = [], []
        for k in range(1, TRAIN_DAYS):
            target = wide.iloc[train_start + k][DSOCDT_COLS].values.astype(float)
            if np.any(np.isnan(target)):
                continue
            feats = build_padded_feature_row(wide, train_start, train_start + k, TRAIN_DAYS - k)
            X_train.append(feats); y_train.append(target)
        if len(X_train) < 2:
            continue

        model.fit(np.array(X_train, dtype=float), np.array(y_train, dtype=float))
        X_pred = build_feature_row(wide, train_start, train_end).reshape(1, -1)
        y_pred = model.predict(X_pred)[0]
        y_actual = wide.iloc[predict_day_idx][DSOCDT_COLS].values.astype(float)
        if np.all(np.isnan(y_actual)):
            continue

        actual_peak = find_top_peak(y_actual, MIN_HOURLY_RISE_ACTUAL)
        pred_peak   = find_top_peak(y_pred,   MIN_HOURLY_RISE_PRED)

        error = abs(actual_peak - pred_peak) if (actual_peak is not None and pred_peak is not None) else np.nan

        results.append({
            "predict_date": predict_date, "y_actual": y_actual, "y_pred": y_pred,
            "actual_peak": actual_peak, "pred_peak": pred_peak, "error": error,
        })
        if (predict_day_idx - TRAIN_DAYS) % 10 == 0 or predict_day_idx == n_days - 1:
            print(f"  Day {predict_day_idx - TRAIN_DAYS + 1:3d}/{total} | {predict_date} "
                  f"| actual={actual_peak} pred={pred_peak} err={error}")
    return results


def plot_mae_per_device(summary_df, plot_path):
    dev_data = summary_df[summary_df["device"] != "OVERALL_MEAN"]
    overall  = summary_df[summary_df["device"] == "OVERALL_MEAN"]
    short_names = [d[:12] + "…" if len(d) > 12 else d for d in dev_data["device"]]

    fig, ax = plt.subplots(figsize=(max(10, len(dev_data) * 1.2), 6))
    bars = ax.bar(range(len(dev_data)), dev_data["mae_hours"],
                  color="steelblue", edgecolor="white", zorder=3)
    if not overall.empty:
        ax.axhline(overall["mae_hours"].values[0], color="crimson", linestyle="--",
                   linewidth=1.8, label=f"Overall mean MAE: {overall['mae_hours'].values[0]:.2f} hrs")
    for bar, val in zip(bars, dev_data["mae_hours"]):
        if not pd.isna(val):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                    f"{val:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.set_xticks(range(len(dev_data))); ax.set_xticklabels(short_names, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("MAE (hours)", fontsize=11)
    ax.set_title("Top-1 Charging Peak — MAE per Device\n(hour error between actual and predicted strongest charging event)",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=9); ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout(); fig.savefig(plot_path, dpi=150, bbox_inches="tight"); plt.close(fig)
    print(f"  Saved: {plot_path}")


def plot_sample_days(results, device_name, plot_path, n_samples=6):
    if not results:
        return
    sample_idx = list(range(0, min(len(results), 7 * n_samples), 7))[:n_samples]
    n_cols, n_rows = 3, int(np.ceil(len(sample_idx) / 3))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 5 * n_rows))
    axes = np.array(axes).reshape(-1)
    fig.suptitle(f"Charging Schedule (Top-1 Peak) — {device_name}", fontsize=13, fontweight="bold")

    for panel_i, idx in enumerate(sample_idx):
        ax, r = axes[panel_i], results[idx]
        actual, pred = r["y_actual"], r["y_pred"]
        valid = ~np.isnan(actual)
        ax.plot(np.array(HOURS)[valid], actual[valid], color="steelblue", linewidth=1.8,
                marker="o", markersize=3, label="Actual dSocdt")
        ax.plot(HOURS, pred, color="crimson", linewidth=1.8, linestyle="--",
                marker="s", markersize=3, label="Predicted dSocdt")
        if r["actual_peak"] is not None:
            ax.axvline(r["actual_peak"], color="steelblue", linewidth=2, alpha=0.6, label="Actual peak")
        if r["pred_peak"] is not None:
            ax.axvline(r["pred_peak"], color="crimson", linestyle="--", linewidth=2, alpha=0.6, label="Predicted peak")
        err_str = f"{r['error']:.2f}hrs" if not pd.isna(r["error"]) else "N/A"
        ax.set_title(f"{r['predict_date']} | err={err_str}", fontsize=9)
        ax.set_xlabel("Hour of day", fontsize=8); ax.set_ylabel("dSocdt", fontsize=8)
        ax.set_xticks(range(0, 24, 4)); ax.legend(fontsize=7, loc="upper right")
        ax.grid(linestyle="--", alpha=0.3)
    for empty_i in range(len(sample_idx), len(axes)):
        axes[empty_i].axis("off")
    fig.tight_layout(); fig.savefig(plot_path, dpi=150, bbox_inches="tight"); plt.close(fig)
    print(f"  Saved: {plot_path}")


if __name__ == "__main__":
    print("=" * 65)
    print("CHARGING SCHEDULE PREDICTION — TOP-1 PEAK PER DAY")
    print("=" * 65)
    print(f"  Actual peak min hourly rise    : {MIN_HOURLY_RISE_ACTUAL}")
    print(f"  Predicted peak min hourly rise : {MIN_HOURLY_RISE_PRED}")
    print("=" * 65 + "\n")

    wide_files = sorted(glob.glob(os.path.join(WIDE_CSV_FOLDER, "*_wide.csv")))
    if not wide_files:
        raise FileNotFoundError(f"No *_wide.csv files in '{WIDE_CSV_FOLDER}'.")

    all_summary_rows = []

    for wf in wide_files:
        device_name = os.path.splitext(os.path.basename(wf))[0].replace("_wide", "")
        pred_path = os.path.join(OUTPUT_FOLDER, f"charging_schedule_predictions_{device_name}.csv")
        plot_path = os.path.join(OUTPUT_FOLDER, f"charging_schedule_sample_days_{device_name}.png")

        print("=" * 65); print(f"Device : {device_name}"); print("=" * 65)
        try:
            wide = pd.read_csv(wf, index_col="Date")
            if len(wide) <= TRAIN_DAYS:
                print("  Skipping: not enough days.\n"); continue

            results = run_predictions(wide, device_name)
            if not results:
                print("  No valid prediction days.\n"); continue

            pd.DataFrame([{
                "predict_date": r["predict_date"], "actual_peak_hr": r["actual_peak"],
                "pred_peak_hr": r["pred_peak"], "error_hrs": r["error"],
            } for r in results]).to_csv(pred_path, index=False)
            print(f"\n  Predictions CSV  →  {pred_path}")

            plot_sample_days(results, device_name, plot_path)

            errors = [r["error"] for r in results if not pd.isna(r["error"])]
            device_mae = float(np.mean(errors)) if errors else np.nan
            print(f"\n  MAE (hours)          : {device_mae:.3f}" if not np.isnan(device_mae) else "\n  MAE: N/A")
            print(f"  Matched day pairs    : {len(errors)} / {len(results)}")

            all_summary_rows.append({
                "device": device_name, "total_days": len(results),
                "matched_pairs": len(errors),
                "mae_hours": round(device_mae, 4) if not np.isnan(device_mae) else np.nan,
            })
        except Exception as e:
            import traceback
            print(f"  ERROR: {e}"); traceback.print_exc()
        print()

    summary_df = pd.DataFrame(all_summary_rows)
    if not summary_df.empty:
        overall_mae = round(float(np.nanmean(summary_df["mae_hours"])), 4)
        summary_df = pd.concat([summary_df, pd.DataFrame([{
            "device": "OVERALL_MEAN", "total_days": summary_df["total_days"].sum(),
            "matched_pairs": summary_df["matched_pairs"].sum(), "mae_hours": overall_mae,
        }])], ignore_index=True)

    summary_csv_path = os.path.join(OUTPUT_FOLDER, "charging_schedule_summary.csv")
    summary_df.to_csv(summary_csv_path, index=False)
    print(f"\nGlobal summary  →  {summary_csv_path}")

    if not summary_df.empty:
        plot_mae_per_device(summary_df, os.path.join(OUTPUT_FOLDER, "charging_schedule_mae_plot.png"))

    print("\n" + "=" * 65)
    print("FINAL SUMMARY")
    print("=" * 65)
    for _, row in summary_df.iterrows():
        mae_str = f"{row['mae_hours']:.2f} hrs" if not pd.isna(row['mae_hours']) else "N/A"
        print(f"  {row['device']:<35}  MAE={mae_str:>10}  matched={int(row['matched_pairs'])}/{int(row['total_days'])}")
    print("=" * 65)
    
