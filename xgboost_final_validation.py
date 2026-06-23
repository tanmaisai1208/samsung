"""
Battery Management - Final Combined Validation with Best Hyperparameters
======================================================================================
Runs the daily rolling-window XGBoost model using the best hyperparameter
values found from sequential tuning in battery_hypersearch.py:

  n_estimators  = 25   (tuned in step 1)
  max_depth     = 2     (tuned in step 2)
  learning_rate = 0.05  (tuned in step 3)
  subsample     = 0.95   (tuned in step 4)
  colsample_bytree = 0.8 (fixed throughout)

Threshold sweep : ACC_THRESHOLD varied 1→10.
Cosine similarity: computed per day between actual and predicted dSocdt vectors,
                   then averaged per device and across all devices.

Outputs (all inside results/final_validation/):
  final_predictions_<device>.csv        — per-hour actual vs predicted + cosine sim
  final_summary_all_thresholds.csv      — all thresholds × devices combined
  final_summary_threshold_<T>.csv       — per-device metrics at threshold T
  cosine_similarity_summary.csv         — per-device mean cosine sim + overall mean
  final_validation_plot_<device>.png    — daily accuracy/MAE/actual-vs-pred (T=2)
  cosine_similarity_plot.png            — per-device + overall mean cosine sim bar chart
  threshold_accuracy_curve.png          — overall mean accuracy vs threshold value
"""

import os
import glob
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.multioutput import MultiOutputRegressor

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────
# BEST HYPERPARAMETERS
# ─────────────────────────────────────────────────────────────
BEST_PARAMS = {
    "n_estimators"   : 25,
    "max_depth"      : 2,
    "learning_rate"  : 0.05,
    "subsample"      : 0.95,
    "colsample_bytree": 0.8,
    "random_state"   : 42,
    "verbosity"      : 0,
}

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────
WIDE_CSV_FOLDER = "results/wide_csv"
OUTPUT_FOLDER   = "results/xgboost/final_validation"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

TRAIN_DAYS     = 14
THRESHOLDS     = list(range(1, 11))   # 1, 2, 3, ... 10
DEFAULT_PLOT_T = 2                    # threshold used for per-device plots
HOURS          = list(range(24))

# ─────────────────────────────────────────────────────────────
# COLUMN DEFINITIONS
# ─────────────────────────────────────────────────────────────
DSOCDT_COLS     = [f"dSocdt_h{h}" for h in HOURS]
SOC_COLS        = [f"Soc_h{h}"    for h in HOURS]
DATE_FEAT_COUNT = 4
FEATS_PER_DAY   = len(DSOCDT_COLS) + len(SOC_COLS) + DATE_FEAT_COUNT  # 52


# ─────────────────────────────────────────────────────────────
# FEATURE HELPERS
# ─────────────────────────────────────────────────────────────

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


def accuracy_at_threshold(actual, predicted, threshold):
    return float(np.mean(np.abs(actual - predicted) <= threshold)) * 100.0


def cosine_similarity(actual, predicted):
    """
    Cosine similarity between actual and predicted 24-hour dSocdt vectors.
    Range: -1 (opposite) to +1 (identical direction).
    Returns 0.0 if either vector is all-zeros (no discharge activity).
    """
    norm_a = np.linalg.norm(actual)
    norm_p = np.linalg.norm(predicted)
    if norm_a == 0.0 or norm_p == 0.0:
        return 0.0
    return float(np.dot(actual, predicted) / (norm_a * norm_p))


# ─────────────────────────────────────────────────────────────
# DAILY ROLLING PREDICTION  (runs once per device)
# ─────────────────────────────────────────────────────────────

def run_predictions(wide, device_name):
    """
    Returns list of per-day dicts with raw y_actual, y_pred, MAE, RMSE,
    and cosine similarity. Accuracy is computed later per threshold.
    """
    n_days  = len(wide)
    results = []

    model = MultiOutputRegressor(
        XGBRegressor(**BEST_PARAMS),
        n_jobs=-1
    )

    total = n_days - TRAIN_DAYS
    print(f"  Predicting {total} days...")

    for predict_day_idx in range(TRAIN_DAYS, n_days):
        train_start  = predict_day_idx - TRAIN_DAYS
        train_end    = predict_day_idx
        predict_date = wide.index[predict_day_idx]

        X_train, y_train = [], []
        for k in range(1, TRAIN_DAYS):
            pad_days = TRAIN_DAYS - k
            feats  = build_padded_feature_row(wide, train_start,
                                               train_start + k, pad_days)
            target = wide.iloc[train_start + k][DSOCDT_COLS].values.astype(float)
            X_train.append(feats)
            y_train.append(target)

        X_train = np.array(X_train, dtype=float)
        y_train = np.array(y_train, dtype=float)
        model.fit(X_train, y_train)

        X_pred   = build_feature_row(wide, train_start, train_end).reshape(1, -1)
        y_pred   = model.predict(X_pred)[0]
        y_pred   = np.clip(y_pred, a_min=None, a_max=0.0)
        y_actual = wide.iloc[predict_day_idx][DSOCDT_COLS].values.astype(float)

        cos_sim = cosine_similarity(y_actual, y_pred)
        mae     = round(mean_absolute_error(y_actual, y_pred), 6)
        rmse    = round(np.sqrt(mean_squared_error(y_actual, y_pred)), 6)

        results.append({
            "predict_date"   : predict_date,
            "train_start"    : wide.index[train_start],
            "train_end"      : wide.index[train_end - 1],
            "y_actual"       : y_actual,
            "y_pred"         : y_pred,
            "mae"            : mae,
            "rmse"           : rmse,
            "cosine_sim"     : round(cos_sim, 6),
        })

        if (predict_day_idx - TRAIN_DAYS) % 10 == 0 or predict_day_idx == n_days - 1:
            print(f"  Day {predict_day_idx - TRAIN_DAYS + 1:3d}/{total} "
                  f"| {predict_date} | MAE: {mae:.5f} | CosSim: {cos_sim:.4f}")

    return results


# ─────────────────────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────────────────────

def metrics_at_threshold(results, threshold):
    daily_accs = [
        accuracy_at_threshold(r["y_actual"], r["y_pred"], threshold)
        for r in results
    ]
    return {
        "mean_accuracy_%": round(float(np.mean(daily_accs)), 4),
        "mean_mae"        : round(float(np.mean([r["mae"]  for r in results])), 6),
        "mean_rmse"       : round(float(np.mean([r["rmse"] for r in results])), 6),
    }


# ─────────────────────────────────────────────────────────────
# PER-DEVICE PLOT
# ─────────────────────────────────────────────────────────────

def plot_device(results, device_name, plot_path, threshold=DEFAULT_PLOT_T):
    dates      = [r["predict_date"] for r in results]
    accuracies = [accuracy_at_threshold(r["y_actual"], r["y_pred"], threshold)
                  for r in results]
    maes       = [r["mae"]        for r in results]
    cos_sims   = [r["cosine_sim"] for r in results]
    mean_acc   = np.mean(accuracies)

    fig, axes = plt.subplots(4, 1, figsize=(16, 17))
    fig.suptitle(
        f"Final Validation — {device_name}\n"
        f"n_estimators={BEST_PARAMS['n_estimators']}  "
        f"max_depth={BEST_PARAMS['max_depth']}  "
        f"lr={BEST_PARAMS['learning_rate']}  "
        f"subsample={BEST_PARAMS['subsample']}  "
        f"(accuracy shown at threshold={threshold})",
        fontsize=11, fontweight="bold"
    )

    tick_step = max(1, len(dates) // 15)

    # Panel 1 — daily accuracy + 7-day rolling mean
    ax = axes[0]
    ax.plot(dates, accuracies, color="steelblue", linewidth=1.0,
            alpha=0.6, label="Daily accuracy")
    roll7 = pd.Series(accuracies).rolling(7, min_periods=1).mean().tolist()
    ax.plot(dates, roll7, color="navy", linewidth=2.0, label="7-day rolling mean")
    ax.axhline(mean_acc, color="crimson", linestyle="-", linewidth=1.5,
               label=f"Overall mean: {mean_acc:.1f}%")
    ax.axhline(50, color="gray", linestyle="--", linewidth=1.0, label="50% reference")
    ax.set_ylabel("Accuracy (%)", fontsize=11)
    ax.set_title(f"Daily Accuracy  (threshold = {threshold})", fontsize=11)
    ax.set_ylim(0, 110)
    ax.legend(fontsize=9)
    ax.grid(linestyle="--", alpha=0.4)
    ax.set_xticks(dates[::tick_step])
    ax.set_xticklabels(dates[::tick_step], rotation=45, ha="right", fontsize=8)

    # Panel 2 — daily MAE
    ax2 = axes[1]
    ax2.bar(range(len(maes)), maes, color="steelblue", alpha=0.7)
    ax2.axhline(np.mean(maes), color="crimson", linestyle="-", linewidth=1.5,
                label=f"Mean MAE: {np.mean(maes):.4f}")
    ax2.set_ylabel("MAE", fontsize=11)
    ax2.set_title("Daily MAE", fontsize=11)
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    ax2.set_xticks(range(0, len(maes), max(1, len(maes) // 15)))
    ax2.set_xticklabels(dates[::max(1, len(dates) // 15)],
                        rotation=45, ha="right", fontsize=8)

    # Panel 3 — daily cosine similarity
    ax3 = axes[2]
    colors_cs = ["steelblue" if c >= 0 else "salmon" for c in cos_sims]
    ax3.bar(range(len(cos_sims)), cos_sims, color=colors_cs, alpha=0.75)
    mean_cs = np.mean(cos_sims)
    ax3.axhline(mean_cs, color="crimson", linestyle="-", linewidth=1.5,
                label=f"Mean cosine sim: {mean_cs:.4f}")
    ax3.axhline(0, color="black", linestyle="-", linewidth=0.8)
    ax3.set_ylabel("Cosine Similarity", fontsize=11)
    ax3.set_title("Daily Cosine Similarity (Actual vs Predicted dSocdt)", fontsize=11)
    ax3.set_ylim(-1.1, 1.1)
    ax3.legend(fontsize=9)
    ax3.grid(axis="y", linestyle="--", alpha=0.4)
    ax3.set_xticks(range(0, len(cos_sims), max(1, len(cos_sims) // 15)))
    ax3.set_xticklabels(dates[::max(1, len(dates) // 15)],
                        rotation=45, ha="right", fontsize=8)

    # Panel 4 — actual vs predicted for ~8 sampled days
    ax4 = axes[3]
    sample_idx = list(range(0, len(results), max(1, len(results) // 8)))
    cmap = plt.cm.tab10
    for si, idx in enumerate(sample_idx):
        r     = results[idx]
        color = cmap(si % 10)
        ax4.plot(HOURS, r["y_actual"], color=color, linewidth=1.6,
                 label=f"{r['predict_date']} actual")
        ax4.plot(HOURS, r["y_pred"],   color=color, linewidth=1.4,
                 linestyle="--", alpha=0.8)

    solid_p = mpatches.Patch(color="gray", label="Actual (solid)")
    dash_p  = mpatches.Patch(color="gray", label="Predicted (dashed)")
    handles, lbls = ax4.get_legend_handles_labels()
    ax4.legend(handles + [solid_p, dash_p],
               lbls   + ["Actual (solid)", "Predicted (dashed)"],
               fontsize=7, ncol=5, loc="lower right")
    ax4.set_xlabel("Hour of day", fontsize=11)
    ax4.set_ylabel("dSocdt (discharge rate)", fontsize=11)
    ax4.set_title("Actual vs Predicted dSocdt — Sample Days", fontsize=11)
    ax4.set_xticks(HOURS)
    ax4.grid(linestyle="--", alpha=0.3)

    fig.tight_layout()
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Device plot saved  →  {plot_path}")


# ─────────────────────────────────────────────────────────────
# COSINE SIMILARITY SUMMARY PLOT
# ─────────────────────────────────────────────────────────────

def plot_cosine_summary(cosine_df):
    """
    Bar chart: mean cosine similarity per device + overall mean line.
    """
    devices  = cosine_df["device"].tolist()
    means    = cosine_df["mean_cosine_sim"].tolist()
    overall  = cosine_df[cosine_df["device"] == "OVERALL_MEAN"]["mean_cosine_sim"].values
    dev_data = cosine_df[cosine_df["device"] != "OVERALL_MEAN"]

    fig, ax = plt.subplots(figsize=(max(10, len(dev_data) * 1.2), 6))

    colors = ["steelblue" if v >= 0.5 else ("orange" if v >= 0 else "salmon")
              for v in dev_data["mean_cosine_sim"]]
    bars = ax.bar(range(len(dev_data)), dev_data["mean_cosine_sim"],
                  color=colors, edgecolor="white", linewidth=0.8, zorder=3)

    if len(overall) > 0:
        ax.axhline(overall[0], color="crimson", linestyle="-", linewidth=2.0,
                   label=f"Overall mean: {overall[0]:.4f}", zorder=5)

    ax.axhline(0, color="black", linestyle="-", linewidth=0.8)

    for bar, val in zip(bars, dev_data["mean_cosine_sim"]):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01, f"{val:.3f}",
                ha="center", va="bottom", fontsize=8, fontweight="bold")

    # Shorten device names for x-axis labels (first 12 chars)
    short_names = [d[:12] + "…" if len(d) > 12 else d
                   for d in dev_data["device"]]
    ax.set_xticks(range(len(dev_data)))
    ax.set_xticklabels(short_names, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Mean Cosine Similarity", fontsize=12)
    ax.set_ylim(-1.1, 1.2)
    ax.set_title(
        "Mean Cosine Similarity between Actual and Predicted dSocdt\n"
        "(per device, averaged over all predicted days)",
        fontsize=12, fontweight="bold"
    )
    ax.legend(fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    plot_path = os.path.join(OUTPUT_FOLDER, "cosine_similarity_plot.png")
    fig.tight_layout()
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Cosine similarity plot saved  →  {plot_path}")


# ─────────────────────────────────────────────────────────────
# THRESHOLD ACCURACY CURVE PLOT
# ─────────────────────────────────────────────────────────────

def plot_threshold_curve(threshold_summary_df):
    devices    = threshold_summary_df["device"].unique()
    thresholds = sorted(threshold_summary_df["threshold"].unique())

    fig, ax = plt.subplots(figsize=(11, 6))
    cmap = plt.cm.tab10

    all_means = []
    for di, device in enumerate(devices):
        dev_df = threshold_summary_df[threshold_summary_df["device"] == device]
        accs   = [dev_df[dev_df["threshold"] == t]["mean_accuracy_%"].values[0]
                  for t in thresholds]
        short  = device[:14] + "…" if len(device) > 14 else device
        ax.plot(thresholds, accs, marker="o", linewidth=1.3,
                color=cmap(di % 10), alpha=0.5, label=short)
        all_means.append(accs)

    overall = np.mean(all_means, axis=0)
    ax.plot(thresholds, overall, marker="D", linewidth=2.5,
            color="black", label="Overall mean", zorder=5)

    for t, acc in zip(thresholds, overall):
        ax.annotate(f"{acc:.1f}%", xy=(t, acc),
                    xytext=(0, 7), textcoords="offset points",
                    ha="center", fontsize=8, color="black", fontweight="bold")

    ax.set_xlabel("Accuracy Threshold", fontsize=12)
    ax.set_ylabel("Mean Accuracy (%)", fontsize=12)
    ax.set_title(
        "Overall Mean Accuracy vs Threshold Value\n"
        f"(Best params: n_est={BEST_PARAMS['n_estimators']}, "
        f"depth={BEST_PARAMS['max_depth']}, "
        f"lr={BEST_PARAMS['learning_rate']}, "
        f"subsample={BEST_PARAMS['subsample']})",
        fontsize=12, fontweight="bold"
    )
    ax.set_xticks(thresholds)
    ax.legend(fontsize=7, ncol=3, loc="lower right")
    ax.grid(linestyle="--", alpha=0.4)
    ax.set_ylim(0, 110)

    plot_path = os.path.join(OUTPUT_FOLDER, "threshold_accuracy_curve.png")
    fig.tight_layout()
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Threshold curve saved  →  {plot_path}")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 65)
    print("FINAL COMBINED VALIDATION — BEST HYPERPARAMETERS")
    print("=" * 65)
    for k, v in BEST_PARAMS.items():
        if k not in ("random_state", "verbosity"):
            print(f"  {k:20s} = {v}")
    print(f"\n  Thresholds evaluated : {THRESHOLDS}")
    print("=" * 65 + "\n")

    wide_files = sorted(glob.glob(os.path.join(WIDE_CSV_FOLDER, "*_wide.csv")))
    if not wide_files:
        raise FileNotFoundError(
            f"No *_wide.csv files in '{WIDE_CSV_FOLDER}'. "
            "Run battery_xgboost.py first."
        )

    all_threshold_rows = []
    cosine_rows        = []   # one row per device for cosine summary

    for wf in wide_files:
        device_name = os.path.splitext(os.path.basename(wf))[0].replace("_wide", "")
        pred_path   = os.path.join(OUTPUT_FOLDER, f"final_predictions_{device_name}.csv")
        plot_path   = os.path.join(OUTPUT_FOLDER, f"final_validation_plot_{device_name}.png")

        print("=" * 65)
        print(f"Device : {device_name}")
        print("=" * 65)

        try:
            wide = pd.read_csv(wf, index_col="Date")
            wide[DSOCDT_COLS] = wide[DSOCDT_COLS].clip(upper=0)

            if len(wide) <= TRAIN_DAYS:
                print(f"  Skipping: not enough days.\n")
                continue

            # Run model once — get raw predictions + cosine sim per day
            results = run_predictions(wide, device_name)
            if not results:
                continue

            # Save raw per-hour predictions CSV (includes cosine sim per day)
            pred_rows = []
            for r in results:
                for h in HOURS:
                    pred_rows.append({
                        "predict_date"  : r["predict_date"],
                        "train_start"   : r["train_start"],
                        "train_end"     : r["train_end"],
                        "hour"          : h,
                        "actual_dSocdt" : round(float(r["y_actual"][h]), 6),
                        "pred_dSocdt"   : round(float(r["y_pred"][h]),   6),
                        "abs_error"     : round(abs(float(r["y_actual"][h])
                                                    - float(r["y_pred"][h])), 6),
                        "daily_cosine_sim": r["cosine_sim"],  # same value for all 24 rows of that day
                    })
            pd.DataFrame(pred_rows).to_csv(pred_path, index=False)
            print(f"\n  Raw predictions CSV  →  {pred_path}")

            # Per-device plot (4 panels now including cosine sim)
            plot_device(results, device_name, plot_path, threshold=DEFAULT_PLOT_T)

            # Threshold sweep (accuracy/MAE/RMSE only — model output is fixed)
            print(f"\n  Threshold sweep:")
            for T in THRESHOLDS:
                m = metrics_at_threshold(results, T)
                print(f"    T={T:2d}  →  acc={m['mean_accuracy_%']:.2f}%  "
                      f"mae={m['mean_mae']:.5f}  rmse={m['mean_rmse']:.5f}")
                all_threshold_rows.append({
                    "device"         : device_name,
                    "threshold"      : T,
                    "mean_accuracy_%": m["mean_accuracy_%"],
                    "mean_mae"       : m["mean_mae"],
                    "mean_rmse"      : m["mean_rmse"],
                    "n_estimators"   : BEST_PARAMS["n_estimators"],
                    "max_depth"      : BEST_PARAMS["max_depth"],
                    "learning_rate"  : BEST_PARAMS["learning_rate"],
                    "subsample"      : BEST_PARAMS["subsample"],
                })

            # Cosine similarity summary for this device
            mean_cos = round(float(np.mean([r["cosine_sim"] for r in results])), 6)
            min_cos  = round(float(np.min ([r["cosine_sim"] for r in results])), 6)
            max_cos  = round(float(np.max ([r["cosine_sim"] for r in results])), 6)
            print(f"\n  Cosine similarity — mean: {mean_cos:.4f}  "
                  f"min: {min_cos:.4f}  max: {max_cos:.4f}")

            cosine_rows.append({
                "device"          : device_name,
                "mean_cosine_sim" : mean_cos,
                "min_cosine_sim"  : min_cos,
                "max_cosine_sim"  : max_cos,
                "total_days"      : len(results),
            })

        except Exception as e:
            import traceback
            print(f"  ERROR: {e}")
            traceback.print_exc()

        print()

    # ── Save combined threshold summary CSV ──────────────────
    threshold_df = pd.DataFrame(all_threshold_rows)
    all_thresh_path = os.path.join(OUTPUT_FOLDER, "final_summary_all_thresholds.csv")
    threshold_df.to_csv(all_thresh_path, index=False)
    print(f"All-threshold summary  →  {all_thresh_path}")

    # ── Save cosine similarity summary CSV ───────────────────
    cosine_df = pd.DataFrame(cosine_rows)
    # Append overall mean row
    if not cosine_df.empty:
        overall_cos = round(float(cosine_df["mean_cosine_sim"].mean()), 6)
        cosine_df = pd.concat([
            cosine_df,
            pd.DataFrame([{
                "device"          : "OVERALL_MEAN",
                "mean_cosine_sim" : overall_cos,
                "min_cosine_sim"  : round(float(cosine_df["min_cosine_sim"].min()), 6),
                "max_cosine_sim"  : round(float(cosine_df["max_cosine_sim"].max()), 6),
                "total_days"      : cosine_df["total_days"].sum(),
            }])
        ], ignore_index=True)

    cos_csv_path = os.path.join(OUTPUT_FOLDER, "cosine_similarity_summary.csv")
    cosine_df.to_csv(cos_csv_path, index=False)
    print(f"Cosine similarity summary  →  {cos_csv_path}")

    # ── Plots ─────────────────────────────────────────────────
    plot_threshold_curve(threshold_df)
    plot_cosine_summary(cosine_df)

    # ── Final console summary ─────────────────────────────────
    print("\n" + "=" * 65)
    print("OVERALL MEAN ACCURACY PER THRESHOLD  (across all devices)")
    print("=" * 65)
    print(f"  {'Threshold':>10}  {'Mean Accuracy':>15}  {'Mean MAE':>12}  {'Mean RMSE':>12}")
    print("  " + "─" * 55)
    for T in THRESHOLDS:
        t_df = threshold_df[threshold_df["threshold"] == T]
        print(f"  {T:>10}  {t_df['mean_accuracy_%'].mean():>14.2f}%  "
              f"{t_df['mean_mae'].mean():>12.5f}  "
              f"{t_df['mean_rmse'].mean():>12.5f}")

    print("\n" + "=" * 65)
    print("COSINE SIMILARITY SUMMARY  (across all devices)")
    print("=" * 65)
    for _, row in cosine_df.iterrows():
        print(f"  {row['device']:<35}  mean={row['mean_cosine_sim']:.4f}  "
              f"min={row['min_cosine_sim']:.4f}  max={row['max_cosine_sim']:.4f}")
    print("=" * 65)