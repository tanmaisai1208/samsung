"""
Battery Management - Charging Schedule Prediction
======================================================================================
Reuses the same daily rolling-window XGBoost model and feature pipeline as
battery_final_validation.py (same hyperparameters, same 14-day window, no
clipping of +ve or -ve dSocdt — full signal retained).

CHANGE IN OBJECTIVE:
  Instead of evaluating hourly dSocdt regression accuracy, this script asks a
  different question: "At what hour of the day does the user actually start
  charging their device, and can the model predict that hour?"

DEFINITION OF A "CHARGING EVENT"  (dual constraint — dSocdt rate AND total SoC rise):
  A charging event is a contiguous run of hours where dSocdt exceeds a
  minimum per-hour rate threshold, AND the total SoC gained across that run
  (rate-sum converted to actual percentage via *60 minutes) exceeds a
  minimum total-rise threshold. Both constraints must hold — a single noisy
  hour above the rate threshold is not enough; the accumulated rise across
  the contiguous run must also be substantial.

    Actual curve    : per-hour dSocdt > MIN_HOURLY_RISE_ACTUAL
                       AND total_rise (sum(dSocdt)*60) >= MIN_CHARGE_RISE_ACTUAL
    Predicted curve : per-hour dSocdt > MIN_HOURLY_RISE_PRED
                       AND total_rise (sum(dSocdt)*60) >= MIN_CHARGE_RISE_PRED

  A looser threshold pair is used on the predicted side because XGBoost
  regression systematically underpredicts sharp single-hour charging spikes
  (regression toward the mean), so demanding the same strict thresholds on
  the predicted curve would almost always detect nothing.

  The representative "charging hour" for a detected run is the
  rise-magnitude-weighted average hour across that run (so a run like
  [+1, +8, +1] is centered near the +8 hour, not a flat midpoint).

METRIC:
  MAE — for each day, actual charging-event hours are matched to predicted
  charging-event hours (nearest-hour matching). The absolute hour difference
  between each matched pair is the "error" for that event. MAE is the mean
  of all these per-event errors across all devices and days.

  Absolute-count confusion-matrix-style metrics (NOT percentage-based
  detection/false-alarm rates, since those have inconsistent denominators
  across devices and make cross-device comparison misleading):
    - True Positives (TP)  : matched (actual, predicted) event pairs
    - False Positives (FP) : predicted events with no corresponding actual event
    - False Negatives (FN) : actual events with no corresponding predicted event

Outputs (all inside results/xgboost/charging_schedule/):
  charging_schedule_predictions_<device>.csv  — per-day actual vs predicted event times
  charging_schedule_summary.csv               — per-device MAE, TP/FP/FN counts, etc.
  charging_schedule_mae_plot.png              — MAE per device + overall mean
  charging_schedule_error_distribution.png    — histogram of hour-errors across all events
  charging_schedule_tp_fp_plot.png            — absolute TP / FP counts per device + mean
  charging_schedule_sample_days_<device>.png  — sample days showing actual vs predicted
                                                 dSocdt curves with marked charging events
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
from sklearn.multioutput import MultiOutputRegressor

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────
# MODEL HYPERPARAMETERS — identical to battery_final_validation.py
# ─────────────────────────────────────────────────────────────
BEST_PARAMS = {
    "n_estimators"    : 200,
    "max_depth"       : 2,
    "learning_rate"   : 0.1,
    "subsample"       : 0.95,
    "colsample_bytree": 0.8,
    "random_state"    : 42,
    "verbosity"       : 0,
}

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────
WIDE_CSV_FOLDER = "results/wide_csv"
OUTPUT_FOLDER   = "results/xgboost/charging_schedule"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

TRAIN_DAYS = 14
HOURS      = list(range(24))

# A charging event = contiguous rising run of hours where TOTAL SoC rise
# across the run is >= this many percentage points. Small blips (e.g. a
# single-hour +1% jitter) are ignored.
#
# NOTE: Empirically, charging events in this hourly-averaged dataset show up
# as ISOLATED single-hour spikes (runs rarely span more than 1-2 hours) rather
# than sustained multi-hour ramps. A single strong hour typically sums (after
# the *60 conversion) to roughly 0.4-1.1 in this dataset.
#
# Two separate threshold sets are used: XGBoost regression systematically
# underpredicts sharp single-hour spikes (regression toward the mean), so a
# looser threshold is used when scanning PREDICTED curves to compensate for
# this systematic peak-flattening, while the stricter thresholds (validated
# against real data) are retained for scanning ACTUAL curves.
MIN_HOURLY_RISE_ACTUAL = 0.007
MIN_CHARGE_RISE_ACTUAL = 0.35

MIN_HOURLY_RISE_PRED = 0.004
MIN_CHARGE_RISE_PRED = 0.20

# ─────────────────────────────────────────────────────────────
# COLUMN DEFINITIONS  (identical to final_validation.py)
# ─────────────────────────────────────────────────────────────
DSOCDT_COLS     = [f"dSocdt_h{h}" for h in HOURS]
SOC_COLS        = [f"Soc_h{h}"    for h in HOURS]
DATE_FEAT_COUNT = 4
FEATS_PER_DAY   = len(DSOCDT_COLS) + len(SOC_COLS) + DATE_FEAT_COUNT  # 52


# ─────────────────────────────────────────────────────────────
# FEATURE HELPERS  (identical to battery_final_validation.py)
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


# ─────────────────────────────────────────────────────────────
# CHARGING EVENT DETECTION  (dSocdt rate + total SoC rise, dual constraint)
# ─────────────────────────────────────────────────────────────

def detect_charging_events(dsocdt_24h, min_hourly_rise, min_total_rise):
    """
    Scan a 24-hour dSocdt vector and return a list of charging event times
    (representative hour for each contiguous significant-rise run).

    A "run" is a maximal contiguous sequence of hours where dSocdt >
    min_hourly_rise. The run counts as a genuine charging event only if the
    SUM of dSocdt across the run, converted to actual % SoC gained (rate-sum
    * 60 minutes), is >= min_total_rise.

    The representative hour for an event is the rise-magnitude-weighted
    average hour of the run (so a run like [+1, +8, +1] is centered near the
    +8 hour, not a flat midpoint).

    Returns: list of floats (hour values, can be fractional, e.g. 13.5)
    """
    events = []
    n = len(dsocdt_24h)
    i = 0
    while i < n:
        val = dsocdt_24h[i]
        if not np.isnan(val) and val > min_hourly_rise:
            run_hours = [i]
            run_vals  = [val]
            j = i + 1
            while j < n and not np.isnan(dsocdt_24h[j]) and dsocdt_24h[j] > min_hourly_rise:
                run_hours.append(j)
                run_vals.append(dsocdt_24h[j])
                j += 1
            total_rise = float(np.sum(run_vals)) * 60   # rate-sum -> actual % SoC gained
            if total_rise >= min_total_rise:
                weighted_hour = float(np.average(run_hours, weights=run_vals))
                events.append(weighted_hour)
            i = j
        else:
            i += 1
    return events


def match_events(actual_events, predicted_events):
    """
    Greedy nearest-hour matching between actual and predicted event lists.
    Returns list of (actual_hour, predicted_hour, abs_error) for matched pairs,
    plus counts of unmatched actual (false negatives) and unmatched
    predicted (false positives).
    """
    actual_remaining = list(actual_events)
    pred_remaining    = list(predicted_events)
    matches = []

    while actual_remaining and pred_remaining:
        best_pair = None
        best_dist = None
        for a in actual_remaining:
            for p in pred_remaining:
                d = abs(a - p)
                if best_dist is None or d < best_dist:
                    best_dist = d
                    best_pair = (a, p)
        matches.append((best_pair[0], best_pair[1], best_dist))
        actual_remaining.remove(best_pair[0])
        pred_remaining.remove(best_pair[1])

    n_false_negative = len(actual_remaining)   # actual events with no predicted match
    n_false_positive = len(pred_remaining)     # predicted events with no actual match
    return matches, n_false_negative, n_false_positive


# ─────────────────────────────────────────────────────────────
# DAILY ROLLING PREDICTION  (reuses same model/feature logic)
# ─────────────────────────────────────────────────────────────

def run_charging_schedule_predictions(wide, device_name):
    n_days  = len(wide)
    results = []

    model = MultiOutputRegressor(XGBRegressor(**BEST_PARAMS), n_jobs=-1)

    total = n_days - TRAIN_DAYS
    print(f"  Predicting {total} days...")

    for predict_day_idx in range(TRAIN_DAYS, n_days):
        train_start  = predict_day_idx - TRAIN_DAYS
        train_end    = predict_day_idx
        predict_date = wide.index[predict_day_idx]

        # Build training samples — skip any where target has NaN
        X_train, y_train = [], []
        for k in range(1, TRAIN_DAYS):
            target = wide.iloc[train_start + k][DSOCDT_COLS].values.astype(float)
            if np.any(np.isnan(target)):
                continue
            pad_days = TRAIN_DAYS - k
            feats    = build_padded_feature_row(wide, train_start,
                                                train_start + k, pad_days)
            X_train.append(feats)
            y_train.append(target)

        if len(X_train) < 2:
            continue

        X_train = np.array(X_train, dtype=float)
        y_train = np.array(y_train, dtype=float)
        model.fit(X_train, y_train)

        X_pred   = build_feature_row(wide, train_start, train_end).reshape(1, -1)
        y_pred   = model.predict(X_pred)[0]
        # No clipping — full signal retained, +ve and -ve both meaningful
        y_actual = wide.iloc[predict_day_idx][DSOCDT_COLS].values.astype(float)

        if np.all(np.isnan(y_actual)):
            continue

        # ── Detect charging events on both actual and predicted curves ──
        # Actual curve uses the stricter, real-data-validated thresholds;
        # predicted curve uses looser thresholds to compensate for XGBoost's
        # tendency to underpredict sharp single-hour charging spikes.
        actual_events    = detect_charging_events(
            y_actual, MIN_HOURLY_RISE_ACTUAL, MIN_CHARGE_RISE_ACTUAL)
        predicted_events = detect_charging_events(
            y_pred, MIN_HOURLY_RISE_PRED, MIN_CHARGE_RISE_PRED)

        matches, n_false_negative, n_false_positive = match_events(actual_events, predicted_events)

        results.append({
            "predict_date"    : predict_date,
            "y_actual"        : y_actual,
            "y_pred"          : y_pred,
            "actual_events"   : actual_events,
            "predicted_events": predicted_events,
            "matches"         : matches,
            "n_false_negative": n_false_negative,
            "n_false_positive": n_false_positive,
        })

        if (predict_day_idx - TRAIN_DAYS) % 10 == 0 or predict_day_idx == n_days - 1:
            print(f"  Day {predict_day_idx - TRAIN_DAYS + 1:3d}/{total} "
                  f"| {predict_date} | actual_events={len(actual_events)} "
                  f"pred_events={len(predicted_events)} matched={len(matches)}")

    return results


# ─────────────────────────────────────────────────────────────
# PLOTS
# ─────────────────────────────────────────────────────────────

def plot_mae_per_device(summary_df, plot_path):
    dev_data = summary_df[summary_df["device"] != "OVERALL_MEAN"]
    overall  = summary_df[summary_df["device"] == "OVERALL_MEAN"]

    short_names = [d[:12] + "…" if len(d) > 12 else d for d in dev_data["device"]]
    fig, ax = plt.subplots(figsize=(max(10, len(dev_data) * 1.2), 6))
    bars = ax.bar(range(len(dev_data)), dev_data["mae_hours"],
                  color="steelblue", edgecolor="white", linewidth=0.8, zorder=3)
    if not overall.empty:
        ax.axhline(overall["mae_hours"].values[0], color="crimson", linestyle="--",
                   linewidth=1.8, label=f"Overall mean MAE: {overall['mae_hours'].values[0]:.2f} hrs")
    for bar, val in zip(bars, dev_data["mae_hours"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f"{val:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.set_xticks(range(len(dev_data)))
    ax.set_xticklabels(short_names, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("MAE (hours)", fontsize=11)
    ax.set_title("Charging Schedule Prediction — MAE per Device\n"
                 "(mean absolute hour-difference between actual and predicted charging times)",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {plot_path}")


def plot_error_distribution(all_errors, plot_path):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(all_errors, bins=24, range=(0, 12), color="steelblue",
            edgecolor="white", alpha=0.85)
    mean_err = np.mean(all_errors)
    median_err = np.median(all_errors)
    ax.axvline(mean_err, color="crimson", linestyle="--", linewidth=1.8,
               label=f"Mean = {mean_err:.2f} hrs")
    ax.axvline(median_err, color="darkorange", linestyle=":", linewidth=1.8,
               label=f"Median = {median_err:.2f} hrs")
    ax.set_xlabel("Absolute hour error (|actual charging hour − predicted charging hour|)",
                  fontsize=11)
    ax.set_ylabel("Number of matched charging events", fontsize=11)
    ax.set_title("Distribution of Charging-Time Prediction Errors\n"
                 "(across all matched events, all devices)",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {plot_path}")


def plot_tp_fp(summary_df, plot_path):
    """
    Absolute-count confusion-matrix-style plot: True Positives (matched
    events) and False Positives (unmatched predicted events) per device,
    plus the mean across all devices. Replaces percentage-based
    detection/false-alarm-rate plots, which have inconsistent denominators
    across devices and make cross-device comparison misleading.
    """
    dev_data = summary_df[summary_df["device"] != "OVERALL_MEAN"].copy()
    overall  = summary_df[summary_df["device"] == "OVERALL_MEAN"]

    short_names = [d[:12] + "…" if len(d) > 12 else d for d in dev_data["device"]]
    x = np.arange(len(dev_data))
    width = 0.35

    fig, ax = plt.subplots(figsize=(max(10, len(dev_data) * 1.4), 6.5))
    bars_tp = ax.bar(x - width/2, dev_data["true_positive"], width,
                     label="True Positives (matched events)",
                     color="seagreen", edgecolor="white")
    bars_fp = ax.bar(x + width/2, dev_data["false_positive"], width,
                     label="False Positives (unmatched predicted events)",
                     color="salmon", edgecolor="white")

    for bar, val in zip(bars_tp, dev_data["true_positive"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                str(int(val)), ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    for bar, val in zip(bars_fp, dev_data["false_positive"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                str(int(val)), ha="center", va="bottom", fontsize=7.5, fontweight="bold")

    if not overall.empty:
        mean_tp = overall["true_positive"].values[0] / max(len(dev_data), 1)
        mean_fp = overall["false_positive"].values[0] / max(len(dev_data), 1)
        ax.axhline(mean_tp, color="darkgreen", linestyle="--", linewidth=1.6,
                   label=f"Mean TP/device: {mean_tp:.1f}")
        ax.axhline(mean_fp, color="darkred", linestyle=":", linewidth=1.6,
                   label=f"Mean FP/device: {mean_fp:.1f}")

    ax.set_xticks(x)
    ax.set_xticklabels(short_names, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Absolute event count", fontsize=11)
    ax.set_title(
        "Charging Event Detection — True Positives vs False Positives per Device\n"
        f"(actual: rate>{MIN_HOURLY_RISE_ACTUAL}, total≥{MIN_CHARGE_RISE_ACTUAL}  |  "
        f"predicted: rate>{MIN_HOURLY_RISE_PRED}, total≥{MIN_CHARGE_RISE_PRED})",
        fontsize=12, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {plot_path}")


def plot_sample_days(results, device_name, plot_path, n_samples=6):
    if not results:
        return
    sample_idx = list(range(0, min(len(results), 7 * n_samples), 7))[:n_samples]
    n_panels = len(sample_idx)
    n_cols   = 3
    n_rows   = int(np.ceil(n_panels / n_cols))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 5 * n_rows))
    axes = np.array(axes).reshape(-1)

    fig.suptitle(f"Charging Schedule — Actual vs Predicted — {device_name}",
                 fontsize=13, fontweight="bold")

    for panel_i, idx in enumerate(sample_idx):
        ax = axes[panel_i]
        r  = results[idx]
        actual, pred = r["y_actual"], r["y_pred"]
        valid = ~np.isnan(actual)

        ax.plot(np.array(HOURS)[valid], actual[valid], color="steelblue",
                linewidth=1.8, marker="o", markersize=3, label="Actual dSocdt")
        ax.plot(HOURS, pred, color="crimson", linewidth=1.8, linestyle="--",
                marker="s", markersize=3, label="Predicted dSocdt")

        for ev in r["actual_events"]:
            ax.axvline(ev, color="steelblue", linestyle="-", alpha=0.5, linewidth=2)
        for ev in r["predicted_events"]:
            ax.axvline(ev, color="crimson", linestyle="--", alpha=0.5, linewidth=2)

        mae_str = (f"{np.mean([m[2] for m in r['matches']]):.2f}hrs"
                  if r["matches"] else "N/A")
        ax.set_title(f"{r['predict_date']} | actual_ev={len(r['actual_events'])} "
                     f"pred_ev={len(r['predicted_events'])} | avg_err={mae_str}",
                     fontsize=9)
        ax.set_xlabel("Hour of day", fontsize=8)
        ax.set_ylabel("dSocdt", fontsize=8)
        ax.set_xticks(range(0, 24, 4))
        ax.legend(fontsize=7, loc="upper right")
        ax.grid(linestyle="--", alpha=0.3)

    for empty_i in range(n_panels, len(axes)):
        axes[empty_i].axis("off")

    fig.tight_layout()
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {plot_path}")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 65)
    print("CHARGING SCHEDULE PREDICTION")
    print("=" * 65)
    for k, v in BEST_PARAMS.items():
        if k not in ("random_state", "verbosity"):
            print(f"  {k:20s} = {v}")
    print(f"\n  Actual    — min hourly rise / min total rise : "
          f"{MIN_HOURLY_RISE_ACTUAL} / {MIN_CHARGE_RISE_ACTUAL}")
    print(f"  Predicted — min hourly rise / min total rise : "
          f"{MIN_HOURLY_RISE_PRED} / {MIN_CHARGE_RISE_PRED}")
    print("=" * 65 + "\n")

    wide_files = sorted(glob.glob(os.path.join(WIDE_CSV_FOLDER, "*_wide.csv")))
    if not wide_files:
        raise FileNotFoundError(f"No *_wide.csv files in '{WIDE_CSV_FOLDER}'.")

    all_summary_rows  = []
    all_errors_pooled = []

    for wf in wide_files:
        device_name = os.path.splitext(os.path.basename(wf))[0].replace("_wide", "")
        pred_path   = os.path.join(OUTPUT_FOLDER, f"charging_schedule_predictions_{device_name}.csv")
        plot_path   = os.path.join(OUTPUT_FOLDER, f"charging_schedule_sample_days_{device_name}.png")

        print("=" * 65)
        print(f"Device : {device_name}")
        print("=" * 65)

        try:
            wide = pd.read_csv(wf, index_col="Date")
            # NO clipping — full signal (+ve and -ve dSocdt) retained

            if len(wide) <= TRAIN_DAYS:
                print("  Skipping: not enough days.\n")
                continue

            results = run_charging_schedule_predictions(wide, device_name)
            if not results:
                print("  No valid prediction days produced.\n")
                continue

            # Save per-day predictions CSV + accumulate TP/FP/FN
            pred_rows = []
            all_device_errors   = []
            total_tp             = 0
            total_fp             = 0
            total_fn             = 0
            n_event_count_match  = 0

            for r in results:
                matched_errors = [m[2] for m in r["matches"]]
                all_device_errors.extend(matched_errors)
                all_errors_pooled.extend(matched_errors)

                total_tp += len(r["matches"])
                total_fp += r["n_false_positive"]
                total_fn += r["n_false_negative"]

                if len(r["actual_events"]) == len(r["predicted_events"]):
                    n_event_count_match += 1

                pred_rows.append({
                    "predict_date"      : r["predict_date"],
                    "actual_events"     : "; ".join(f"{e:.2f}" for e in r["actual_events"]),
                    "predicted_events"  : "; ".join(f"{e:.2f}" for e in r["predicted_events"]),
                    "n_actual_events"   : len(r["actual_events"]),
                    "n_predicted_events": len(r["predicted_events"]),
                    "true_positive"     : len(r["matches"]),
                    "false_positive"    : r["n_false_positive"],
                    "false_negative"    : r["n_false_negative"],
                    "matched_errors_hrs": "; ".join(f"{e:.2f}" for e in matched_errors),
                    "mean_error_hrs"    : round(float(np.mean(matched_errors)), 3) if matched_errors else np.nan,
                })

            pd.DataFrame(pred_rows).to_csv(pred_path, index=False)
            print(f"\n  Predictions CSV  →  {pred_path}")

            plot_sample_days(results, device_name, plot_path)

            device_mae = float(np.mean(all_device_errors)) if all_device_errors else np.nan
            event_count_match_rate = 100 * n_event_count_match / len(results)

            print(f"\n  MAE (hours)              : {device_mae:.3f}" if not np.isnan(device_mae) else "\n  MAE: N/A (no matched events)")
            print(f"  True Positives (TP)      : {total_tp}")
            print(f"  False Positives (FP)     : {total_fp}")
            print(f"  False Negatives (FN)     : {total_fn}")
            print(f"  Event count match rate   : {event_count_match_rate:.1f}%")

            all_summary_rows.append({
                "device"             : device_name,
                "total_days"         : len(results),
                "mae_hours"          : round(device_mae, 4) if not np.isnan(device_mae) else np.nan,
                "true_positive"      : total_tp,
                "false_positive"     : total_fp,
                "false_negative"     : total_fn,
                "event_count_match_%": round(event_count_match_rate, 2),
                "n_matched_events"   : len(all_device_errors),
            })

        except Exception as e:
            import traceback
            print(f"  ERROR: {e}")
            traceback.print_exc()

        print()

    # ── Global summary CSV ────────────────────────────────────
    summary_df = pd.DataFrame(all_summary_rows)
    if not summary_df.empty:
        overall_mae = round(float(np.nanmean(summary_df["mae_hours"])), 4)
        overall_ecm = round(float(summary_df["event_count_match_%"].mean()), 2)
        summary_df = pd.concat([
            summary_df,
            pd.DataFrame([{
                "device"             : "OVERALL_MEAN",
                "total_days"         : summary_df["total_days"].sum(),
                "mae_hours"          : overall_mae,
                "true_positive"      : summary_df["true_positive"].sum(),
                "false_positive"     : summary_df["false_positive"].sum(),
                "false_negative"     : summary_df["false_negative"].sum(),
                "event_count_match_%": overall_ecm,
                "n_matched_events"   : summary_df["n_matched_events"].sum(),
            }])
        ], ignore_index=True)

    summary_csv_path = os.path.join(OUTPUT_FOLDER, "charging_schedule_summary.csv")
    summary_df.to_csv(summary_csv_path, index=False)
    print(f"\nGlobal summary  →  {summary_csv_path}")

    # ── Plots ──────────────────────────────────────────────────
    if not summary_df.empty:
        plot_mae_per_device(summary_df,
            os.path.join(OUTPUT_FOLDER, "charging_schedule_mae_plot.png"))
        plot_tp_fp(summary_df,
            os.path.join(OUTPUT_FOLDER, "charging_schedule_tp_fp_plot.png"))

    if all_errors_pooled:
        plot_error_distribution(all_errors_pooled,
            os.path.join(OUTPUT_FOLDER, "charging_schedule_error_distribution.png"))

    # ── Final console summary ─────────────────────────────────
    print("\n" + "=" * 65)
    print("CHARGING SCHEDULE PREDICTION — FINAL SUMMARY")
    print("=" * 65)
    for _, row in summary_df.iterrows():
        mae_str = f"{row['mae_hours']:.2f} hrs" if not pd.isna(row['mae_hours']) else "N/A"
        print(f"  {row['device']:<35}  MAE={mae_str:>10}  "
              f"TP={int(row['true_positive']):>4}  FP={int(row['false_positive']):>4}  "
              f"FN={int(row['false_negative']):>4}  EventCountMatch={row['event_count_match_%']:.1f}%")
    print("=" * 65)
