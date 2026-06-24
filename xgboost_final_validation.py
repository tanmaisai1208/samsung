"""
Battery Management - Feature Importance Analysis
======================================================================================
Trains XGBoost with the best hyperparameters found during tuning,
then extracts and visualises average feature importance across all 24 output
estimators (one per hour).

Changes from previous version:
  - Date/day/month/year features REMOVED (only 0.026% importance)
  - TRAIN_DAYS reduced from 14 to 7 (days 8-14 showed negligible importance)
  - Features per day : 24 dSocdt + 24 Soc = 48
  - Total features   : 7 × 48 = 336

Outputs:
  feature_importance.csv          — all features ranked by importance
  feature_importance_top30.png    — bar chart of top 30 features
  feature_importance_by_type.png  — grouped bar: dSocdt vs Soc features
  feature_importance_by_day.png   — how importance decays over the 7-day lookback
"""

import os
import glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from xgboost import XGBRegressor
from sklearn.multioutput import MultiOutputRegressor

# ─────────────────────────────────────────────────────────────
# BEST HYPERPARAMETERS
# ─────────────────────────────────────────────────────────────
BEST_PARAMS = {
    "n_estimators"    : 25,
    "max_depth"       : 2,
    "learning_rate"   : 0.05,
    "subsample"       : 0.95,
    "colsample_bytree": 0.8,
}

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────
WIDE_CSV_FOLDER = "results/wide_csv"
OUTPUT_FOLDER   = "results/xgboost/feature_importance"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

OUTPUT_CSV   = os.path.join(OUTPUT_FOLDER, "feature_importance.csv")
PLOT_TOP30   = os.path.join(OUTPUT_FOLDER, "feature_importance_top30.png")
PLOT_BY_TYPE = os.path.join(OUTPUT_FOLDER, "feature_importance_by_type.png")
PLOT_BY_DAY  = os.path.join(OUTPUT_FOLDER, "feature_importance_by_day.png")

TRAIN_DAYS = 7      # reduced from 14 — days 8-14 showed negligible importance
HOURS      = list(range(24))

# ─────────────────────────────────────────────────────────────
# COLUMN DEFINITIONS
# ─────────────────────────────────────────────────────────────
DSOCDT_COLS   = [f"dSocdt_h{h}" for h in HOURS]
SOC_COLS      = [f"Soc_h{h}"    for h in HOURS]

# Date features REMOVED (0.026% importance — negligible)
# Features per day : 24 dSocdt + 24 Soc = 48
# Total features   : 7 × 48 = 336
FEATS_PER_DAY  = len(DSOCDT_COLS) + len(SOC_COLS)   # 48
TOTAL_FEATURES = TRAIN_DAYS * FEATS_PER_DAY          # 336

# ─────────────────────────────────────────────────────────────
# FEATURE NAMES
# day_minus7 = oldest (7 days back), day_minus1 = most recent (yesterday)
# ─────────────────────────────────────────────────────────────
feature_names = []
for day_pos in range(TRAIN_DAYS):           # 0 = oldest, 6 = most recent
    days_back = TRAIN_DAYS - day_pos        # 7 = oldest, 1 = most recent
    day_label = f"day_minus{days_back}"

    for h in HOURS:
        feature_names.append(f"dSocdt_h{h}_{day_label}")
    for h in HOURS:
        feature_names.append(f"Soc_h{h}_{day_label}")

assert len(feature_names) == TOTAL_FEATURES, \
    f"Feature name count mismatch: {len(feature_names)} vs {TOTAL_FEATURES}"


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def build_padded_feature_row(wide, context_start, context_end, pad_days):
    """Zero-padded partial window — dSocdt + Soc only, no date features."""
    feats = [0.0] * (pad_days * FEATS_PER_DAY)
    for i in range(context_start, context_end):
        feats.extend(wide.iloc[i][DSOCDT_COLS].tolist())
        feats.extend(wide.iloc[i][SOC_COLS].tolist())
    return feats


# ─────────────────────────────────────────────────────────────
# BUILD TRAINING DATA  (pooled across all devices)
# ─────────────────────────────────────────────────────────────
all_X, all_y = [], []

wide_files = sorted(glob.glob(os.path.join(WIDE_CSV_FOLDER, "*_wide.csv")))
if not wide_files:
    raise FileNotFoundError(f"No *_wide.csv files found in '{WIDE_CSV_FOLDER}'.")

for wf in wide_files:
    print(f"Processing: {os.path.basename(wf)}")
    wide = pd.read_csv(wf, index_col="Date")
    wide[DSOCDT_COLS] = wide[DSOCDT_COLS].clip(upper=0)

    if len(wide) <= TRAIN_DAYS:
        print(f"  Skipping: not enough days ({len(wide)}).")
        continue

    for predict_day_idx in range(TRAIN_DAYS, len(wide)):
        train_start = predict_day_idx - TRAIN_DAYS
        for k in range(1, TRAIN_DAYS):
            pad_days = TRAIN_DAYS - k
            feats  = build_padded_feature_row(wide, train_start,
                                               train_start + k, pad_days)
            target = wide.iloc[train_start + k][DSOCDT_COLS].values.astype(float)
            all_X.append(feats)
            all_y.append(target)

X = np.array(all_X, dtype=float)
y = np.array(all_y, dtype=float)
print(f"\nTotal training samples : {len(X)}")
print(f"Feature vector length  : {X.shape[1]}  (expected {TOTAL_FEATURES})")


# ─────────────────────────────────────────────────────────────
# TRAIN MODEL
# ─────────────────────────────────────────────────────────────
print("\nTraining XGBoost with best hyperparameters...")
base_model = XGBRegressor(**BEST_PARAMS, random_state=42, verbosity=0)
model      = MultiOutputRegressor(base_model, n_jobs=-1)
model.fit(X, y)
print("Training complete.")


# ─────────────────────────────────────────────────────────────
# EXTRACT FEATURE IMPORTANCE
# ─────────────────────────────────────────────────────────────
importance_matrix = np.array([est.feature_importances_
                               for est in model.estimators_])   # (24, 336)
avg_importance    = importance_matrix.mean(axis=0)              # (336,)

importance_df = pd.DataFrame({
    "feature"   : feature_names,
    "importance": avg_importance,
})

importance_df["feature_type"] = importance_df["feature"].apply(
    lambda f: "dSocdt" if f.startswith("dSocdt") else "Soc"
)
importance_df["days_back"] = importance_df["feature"].str.extract(
    r"day_minus(\d+)"
).astype(int)

importance_df = importance_df.sort_values("importance", ascending=False).reset_index(drop=True)
importance_df.to_csv(OUTPUT_CSV, index=False)
print(f"\nFeature importance saved  →  {OUTPUT_CSV}")

print("\nTop 20 features:")
print(importance_df[["feature", "importance", "feature_type", "days_back"]]
      .head(20).to_string(index=False))


# ─────────────────────────────────────────────────────────────
# PLOT 1 — Top 30 features (horizontal bar chart)
# ─────────────────────────────────────────────────────────────
top30  = importance_df.head(30)
colors = top30["feature_type"].map(
    {"dSocdt": "steelblue", "Soc": "darkorange"}
)

fig, ax = plt.subplots(figsize=(12, 10))
ax.barh(range(len(top30)), top30["importance"].values,
        color=colors, edgecolor="white", linewidth=0.5)
ax.set_yticks(range(len(top30)))
ax.set_yticklabels(top30["feature"].values, fontsize=8)
ax.invert_yaxis()
ax.set_xlabel("Mean Feature Importance (avg across 24 hour estimators)", fontsize=11)
ax.set_title("Top 30 Most Important Features\n"
             "(XGBoost — dSocdt + Soc only, 7-day lookback, pooled across all devices)",
             fontsize=12, fontweight="bold")

from matplotlib.patches import Patch
ax.legend(handles=[
    Patch(facecolor="steelblue",  label="dSocdt features"),
    Patch(facecolor="darkorange", label="Soc features"),
], fontsize=9, loc="lower right")
ax.grid(axis="x", linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(PLOT_TOP30, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"Plot saved  →  {PLOT_TOP30}")


# ─────────────────────────────────────────────────────────────
# PLOT 2 — Importance by feature type
# ─────────────────────────────────────────────────────────────
type_summary = (importance_df.groupby("feature_type")["importance"]
                              .sum().reset_index()
                              .sort_values("importance", ascending=False))

fig, ax = plt.subplots(figsize=(6, 5))
bar_colors = [{"dSocdt": "steelblue", "Soc": "darkorange"}[t]
              for t in type_summary["feature_type"]]
ax.bar(type_summary["feature_type"], type_summary["importance"],
       color=bar_colors, edgecolor="white", width=0.4)
ax.set_xlabel("Feature Type", fontsize=12)
ax.set_ylabel("Total Importance (sum across all features of that type)", fontsize=10)
ax.set_title("Feature Importance by Type\n"
             "(dSocdt vs Soc — date features excluded)",
             fontsize=12, fontweight="bold")
ax.grid(axis="y", linestyle="--", alpha=0.4)
for bar, val in zip(ax.patches, type_summary["importance"]):
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.001, f"{val:.4f}",
            ha="center", va="bottom", fontsize=10, fontweight="bold")
fig.tight_layout()
fig.savefig(PLOT_BY_TYPE, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"Plot saved  →  {PLOT_BY_TYPE}")


# ─────────────────────────────────────────────────────────────
# PLOT 3 — Importance by days-back (recency over 7-day window)
# ─────────────────────────────────────────────────────────────
day_summary = (importance_df.groupby(["days_back", "feature_type"])["importance"]
                             .sum().reset_index())
pivot = day_summary.pivot(index="days_back", columns="feature_type",
                          values="importance").fillna(0)
pivot = pivot.sort_index(ascending=False)   # day_minus1 (most recent) on left

fig, ax = plt.subplots(figsize=(10, 6))
x      = np.arange(len(pivot))
width  = 0.35
types  = [c for c in ["dSocdt", "Soc"] if c in pivot.columns]
clrs   = {"dSocdt": "steelblue", "Soc": "darkorange"}
offsets= np.linspace(-(len(types)-1)*width/2, (len(types)-1)*width/2, len(types))

for t, offset in zip(types, offsets):
    ax.bar(x + offset, pivot[t], width=width, label=t,
           color=clrs[t], edgecolor="white", linewidth=0.5)

ax.set_xticks(x)
ax.set_xticklabels([f"day-{d}" for d in pivot.index], rotation=45, ha="right", fontsize=9)
ax.set_xlabel("Days back from prediction day  (day-1 = yesterday)", fontsize=11)
ax.set_ylabel("Total Importance (summed across features)", fontsize=11)
ax.set_title("Feature Importance by Recency  (7-day lookback)\n"
             "(Does the model rely more on recent days or older days?)",
             fontsize=12, fontweight="bold")
ax.legend(fontsize=10)
ax.grid(axis="y", linestyle="--", alpha=0.4)
fig.tight_layout()
fig.savefig(PLOT_BY_DAY, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"Plot saved  →  {PLOT_BY_DAY}")

print("\n" + "=" * 65)
print("Feature importance analysis complete.")
print(f"  CSV   : {OUTPUT_CSV}")
print(f"  Plots : {OUTPUT_FOLDER}/")
print("=" * 65)
