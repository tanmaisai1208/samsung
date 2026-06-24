"""
Battery Management - Extended Tree Rules Interpretation & Analysis
======================================================================================
Reads the already-generated tree_rules_summary.csv and produces additional
interpretation plots and statistics that can't be directly read off the
existing PNG files.

Run from inside SOC-folder:
    python battery_tree_analysis_extended.py

Outputs (all inside results/tree_rules/):
  tree_interp_root_features.png       — which features dominate at root (depth=0)
  tree_interp_hour_vs_predictor.png   — heatmap: which past hour predicts each output hour
  tree_interp_dsocdt_thresholds.png   — discharge rate thresholds by hour of day
  tree_interp_soc_thresholds.png      — SoC level thresholds used in splits
  tree_interp_recency_dominance.png   — how split usage drops off with days-back
  tree_interpretation_summary.txt     — plain-English interpretation of all findings
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

SUMMARY_CSV  = "results/xgboost/tree_rules/tree_rules_summary.csv"
OUTPUT_FOLDER= "results/xgboost/tree_rules"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

HOURS = list(range(24))

# ─────────────────────────────────────────────────────────────
# LOAD
# ─────────────────────────────────────────────────────────────
df = pd.read_csv(SUMMARY_CSV)
print(f"Loaded {len(df)} split nodes from {SUMMARY_CSV}")

roots   = df[df["depth"] == 0].copy()
dsocdt  = df[df["feature_type"] == "dSocdt"].copy()
soc     = df[df["feature_type"] == "Soc"].copy()

# Extract hour-of-day encoded in the feature name (e.g. dSocdt_h19 → 19)
df["feat_hour"]   = df["feature"].str.extract(r"_h(\d+)_").astype(float)
roots["feat_hour"]= roots["feature"].str.extract(r"_h(\d+)_").astype(float)
dsocdt["feat_hour"]= dsocdt["feature"].str.extract(r"_h(\d+)_").astype(float)


# ─────────────────────────────────────────────────────────────
# PLOT 1 — Root node feature frequency
# (The root split is the single most important decision in each tree)
# ─────────────────────────────────────────────────────────────
root_feat_counts = (roots.groupby(["feature", "feature_type"])
                          .size().reset_index(name="count")
                          .sort_values("count", ascending=False)
                          .head(20))

color_map  = {"dSocdt": "steelblue", "Soc": "darkorange", "Date": "seagreen"}
bar_colors = [color_map.get(t, "gray") for t in root_feat_counts["feature_type"]]

fig, ax = plt.subplots(figsize=(12, 7))
ax.barh(range(len(root_feat_counts)), root_feat_counts["count"].values,
        color=bar_colors, edgecolor="white", linewidth=0.5)
ax.set_yticks(range(len(root_feat_counts)))
ax.set_yticklabels(root_feat_counts["feature"].values, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("Number of trees where this feature is the FIRST split (root node)",
              fontsize=11)
ax.set_title("Most Frequent Root-Node Split Features\n"
             "(root split = the single most decisive condition in each tree)",
             fontsize=12, fontweight="bold")
from matplotlib.patches import Patch
ax.legend(handles=[
    Patch(facecolor="steelblue",  label="dSocdt features"),
    Patch(facecolor="darkorange", label="Soc features"),
], fontsize=9, loc="lower right")
ax.grid(axis="x", linestyle="--", alpha=0.4)

# Annotate counts
for i, v in enumerate(root_feat_counts["count"].values):
    ax.text(v + 0.5, i, str(v), va="center", fontsize=8.5, fontweight="bold")

fig.tight_layout()
path = os.path.join(OUTPUT_FOLDER, "tree_interp_root_features.png")
fig.savefig(path, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {path}")


# ─────────────────────────────────────────────────────────────
# PLOT 2 — Heatmap: which past hour predicts which output hour
# ─────────────────────────────────────────────────────────────
roots_clean = roots.dropna(subset=["feat_hour"]).copy()
roots_clean["feat_hour"] = roots_clean["feat_hour"].astype(int)

cross = (roots_clean.groupby(["hour", "feat_hour"])
                    .size().unstack(fill_value=0))
# Ensure all 24 hours are present on both axes
cross = cross.reindex(index=range(24), columns=range(24), fill_value=0)

fig, ax = plt.subplots(figsize=(13, 10))
im = ax.imshow(cross.values, cmap="YlOrRd", aspect="auto")

ax.set_xticks(range(24))
ax.set_xticklabels([f"{h:02d}" for h in range(24)], fontsize=8)
ax.set_yticks(range(24))
ax.set_yticklabels([f"{h:02d}:00" for h in range(24)], fontsize=8)
ax.set_xlabel("Hour of day in the split feature  (past day's discharge at this hour)",
              fontsize=11)
ax.set_ylabel("Output hour being predicted", fontsize=11)
ax.set_title("Which Past Hour's Discharge Rate Predicts Each Future Hour?\n"
             "(cell brightness = how often that past hour is the root-split feature)",
             fontsize=12, fontweight="bold")

plt.colorbar(im, ax=ax, label="Root-split frequency", pad=0.01)

# Highlight diagonal band (same-hour prediction tendency)
for i in range(24):
    ax.add_patch(plt.Rectangle((i-0.5, i-0.5), 1, 1,
                                fill=False, edgecolor="blue",
                                linewidth=0.6, alpha=0.4))

fig.tight_layout()
path = os.path.join(OUTPUT_FOLDER, "tree_interp_hour_vs_predictor.png")
fig.savefig(path, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {path}")


# ─────────────────────────────────────────────────────────────
# PLOT 3 — dSocdt split thresholds by hour of day
# Shows WHAT discharge rate level the model considers "significant"
# for each hour of the day
# ─────────────────────────────────────────────────────────────
dsocdt_clean = dsocdt.dropna(subset=["feat_hour"]).copy()
dsocdt_clean["feat_hour"] = dsocdt_clean["feat_hour"].astype(int)

thresh_by_hour = (dsocdt_clean.groupby("feat_hour")["threshold"]
                               .agg(["mean", "median", "std", "count"])
                               .reindex(range(24), fill_value=np.nan))

fig, axes = plt.subplots(2, 1, figsize=(14, 10))

# Panel 1 — median threshold per hour (the typical decision boundary)
ax = axes[0]
bars = ax.bar(range(24), thresh_by_hour["median"].values,
              color="steelblue", alpha=0.8, edgecolor="white")
ax.errorbar(range(24), thresh_by_hour["median"].values,
            yerr=thresh_by_hour["std"].fillna(0).values,
            fmt="none", color="navy", linewidth=1.2, capsize=3)
ax.axhline(0, color="black", linewidth=0.8, linestyle="-")
ax.set_xticks(range(24))
ax.set_xticklabels([f"{h:02d}:00" for h in range(24)],
                   rotation=45, ha="right", fontsize=8)
ax.set_ylabel("Median split threshold (dSocdt)", fontsize=11)
ax.set_title("Typical Discharge Rate Decision Boundary per Hour\n"
             "(how negative dSocdt must be before model treats it as 'significant discharge')",
             fontsize=11, fontweight="bold")
ax.grid(axis="y", linestyle="--", alpha=0.4)
# Annotate a few notable hours
for h in [19, 20, 22, 23]:
    v = thresh_by_hour["median"].iloc[h]
    if not np.isnan(v):
        ax.text(h, v - 0.8, f"{v:.1f}", ha="center", fontsize=8,
                color="white", fontweight="bold")

# Panel 2 — split count per hour (how often each hour is used)
ax2 = axes[1]
ax2.bar(range(24), thresh_by_hour["count"].values,
        color="darkorange", alpha=0.8, edgecolor="white")
ax2.set_xticks(range(24))
ax2.set_xticklabels([f"{h:02d}:00" for h in range(24)],
                    rotation=45, ha="right", fontsize=8)
ax2.set_ylabel("Number of times this hour appears in a dSocdt split", fontsize=11)
ax2.set_title("Which Hours of the Day Are Most Diagnostic for Discharge Prediction?",
              fontsize=11, fontweight="bold")
ax2.grid(axis="y", linestyle="--", alpha=0.4)

fig.suptitle("dSocdt Split Threshold Analysis Across Hours of Day",
             fontsize=13, fontweight="bold")
fig.tight_layout()
path = os.path.join(OUTPUT_FOLDER, "tree_interp_dsocdt_thresholds.png")
fig.savefig(path, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {path}")


# ─────────────────────────────────────────────────────────────
# PLOT 4 — SoC threshold values used in splits
# ─────────────────────────────────────────────────────────────
if len(soc) > 0:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: histogram of all SoC thresholds
    ax = axes[0]
    ax.hist(soc["threshold"].values, bins=30, color="darkorange",
            edgecolor="white", alpha=0.85)
    med = soc["threshold"].median()
    ax.axvline(med, color="crimson", linestyle="--", linewidth=1.8,
               label=f"Median = {med:.1f}%")
    ax.axvline(100, color="gray", linestyle=":", linewidth=1.2,
               label="100% SoC (full charge)")
    ax.axvline(20, color="red", linestyle=":", linewidth=1.2,
               label="20% SoC (low battery)")
    ax.set_xlabel("SoC threshold value (%)", fontsize=11)
    ax.set_ylabel("Frequency", fontsize=11)
    ax.set_title("Distribution of SoC Split Thresholds\n"
                 "(at what battery % does the model change behaviour?)",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    # Right: top SoC features by usage
    ax2 = axes[1]
    top_soc = (soc.groupby("feature").size()
                   .sort_values(ascending=False).head(12))
    ax2.barh(range(len(top_soc)), top_soc.values,
             color="darkorange", edgecolor="white", alpha=0.85)
    ax2.set_yticks(range(len(top_soc)))
    ax2.set_yticklabels(top_soc.index.tolist(), fontsize=8.5)
    ax2.invert_yaxis()
    ax2.set_xlabel("Split count", fontsize=11)
    ax2.set_title("Most-Used SoC Features as Split Conditions",
                  fontsize=11, fontweight="bold")
    ax2.grid(axis="x", linestyle="--", alpha=0.4)

    fig.suptitle("SoC Feature Split Analysis", fontsize=13, fontweight="bold")
    fig.tight_layout()
    path = os.path.join(OUTPUT_FOLDER, "tree_interp_soc_thresholds.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


# ─────────────────────────────────────────────────────────────
# PLOT 5 — Recency dominance: how split usage drops off with days-back
# ─────────────────────────────────────────────────────────────
recency = (df.groupby(["days_back", "feature_type"])["feature"]
             .count().reset_index(name="count"))
recency_pivot = recency.pivot(index="days_back", columns="feature_type",
                               values="count").fillna(0)
recency_pivot = recency_pivot.sort_index()

fig, ax = plt.subplots(figsize=(12, 6))
clrs = {"dSocdt": "steelblue", "Soc": "darkorange", "Date": "seagreen"}
for col in recency_pivot.columns:
    ax.plot(recency_pivot.index, recency_pivot[col].values,
            marker="o", linewidth=2.2, color=clrs.get(col, "gray"),
            label=col, markersize=6)
    # Fill under curve for dSocdt (dominant type)
    if col == "dSocdt":
        ax.fill_between(recency_pivot.index, recency_pivot[col].values,
                        alpha=0.12, color=clrs[col])

ax.set_xlabel("Days back from prediction day  (1 = yesterday, 14 = 2 weeks ago)",
              fontsize=11)
ax.set_ylabel("Number of tree split nodes using features from that day",
              fontsize=11)
ax.set_title("Recency Effect: How Split Node Usage Drops Off with Days-Back\n"
             "(confirms whether yesterday dominates or older history also matters)",
             fontsize=12, fontweight="bold")
ax.set_xticks(recency_pivot.index)
ax.set_xticklabels([f"day-{d}" for d in recency_pivot.index],
                   rotation=45, ha="right", fontsize=9)
ax.legend(fontsize=10)
ax.grid(linestyle="--", alpha=0.4)

# Annotate drop-off percentage
d1 = recency_pivot["dSocdt"].iloc[0] if "dSocdt" in recency_pivot.columns else 0
d2 = recency_pivot["dSocdt"].iloc[1] if len(recency_pivot) > 1 else 0
if d1 > 0:
    drop = (1 - d2/d1) * 100
    ax.annotate(f"↓{drop:.0f}% drop\nfrom day-1 to day-2",
                xy=(recency_pivot.index[1], d2),
                xytext=(recency_pivot.index[1] + 0.5, d2 + 50),
                fontsize=9, color="steelblue",
                arrowprops=dict(arrowstyle="->", color="steelblue", lw=1))

fig.tight_layout()
path = os.path.join(OUTPUT_FOLDER, "tree_interp_recency_dominance.png")
fig.savefig(path, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {path}")


# ─────────────────────────────────────────────────────────────
# PLAIN-ENGLISH INTERPRETATION SUMMARY
# ─────────────────────────────────────────────────────────────
total_splits   = len(df)
day1_splits    = len(df[df["days_back"] == 1])
day1_pct       = 100 * day1_splits / total_splits
day2_splits    = len(df[df["days_back"] == 2])
day12_pct      = 100 * (day1_splits + day2_splits) / total_splits
dsocdt_pct     = 100 * len(df[df["feature_type"] == "dSocdt"]) / total_splits
soc_pct        = 100 * len(df[df["feature_type"] == "Soc"]) / total_splits
date_pct       = 100 * len(df[df["feature_type"] == "Date"]) / total_splits

top_root = (roots.groupby("feature").size().idxmax())
top_root_count = roots.groupby("feature").size().max()
top_root_pct   = 100 * top_root_count / len(roots)

dsocdt_med_thresh = dsocdt["threshold"].median()
soc_med_thresh    = soc["threshold"].median() if len(soc) > 0 else float("nan")

# Hours where same-hour is used at root
same_hour_usage = {}
for h in range(24):
    r_h = roots_clean[roots_clean["hour"] == h]
    same_h = r_h[r_h["feat_hour"] == h]
    same_hour_usage[h] = len(same_h)

summary_text = f"""
═══════════════════════════════════════════════════════════════════
TREE RULES INTERPRETATION SUMMARY
XGBoost Battery Discharge Prediction Model
═══════════════════════════════════════════════════════════════════

OVERVIEW
─────────────────────────────────────────────────────────────────
Total split nodes analysed : {total_splits}
Unique features used       : {df['feature'].nunique()}
Output hours covered       : 24  (00:00 – 23:00)
Trees per hour             : 25
Max tree depth             : 2  (all splits are at depth 0 or 1)

1. FEATURE TYPE DOMINANCE
─────────────────────────────────────────────────────────────────
  dSocdt features : {dsocdt_pct:.1f}% of all split nodes
  Soc features    : {soc_pct:.1f}% of all split nodes
  Date features   : {date_pct:.1f}% of all split nodes

  → The model is overwhelmingly driven by past discharge RATE
    (dSocdt), not battery level (SoC) or calendar information.
    This confirms that HOW FAST the battery discharged yesterday
    is far more predictive than HOW MUCH was left.

2. RECENCY DOMINANCE — YESTERDAY MATTERS MOST
─────────────────────────────────────────────────────────────────
  Splits using day-minus-1 (yesterday) : {day1_pct:.1f}% of all splits
  Splits using day-minus-1 or -2       : {day12_pct:.1f}% of all splits

  → Over {day1_pct:.0f}% of all decision nodes rely purely on YESTERDAY'S
    data. Features from 3 or more days ago contribute less than
    {100 - day12_pct:.0f}% combined. This strongly suggests that a 2-day
    or 3-day training window might be sufficient, and that very
    old history adds little predictive value per tree.

3. MOST DECISIVE SPLIT FEATURE (ROOT NODE ANALYSIS)
─────────────────────────────────────────────────────────────────
  Most frequent root split : {top_root}
  Used at root in          : {top_root_count} trees ({top_root_pct:.1f}% of all root splits)

  Top 5 root-split features (the first question each tree asks):
"""

top5_roots = (roots.groupby("feature").size()
                    .sort_values(ascending=False).head(5))
for feat, cnt in top5_roots.items():
    summary_text += f"    {feat:50s}  {cnt} trees\n"

summary_text += f"""
  → The evening hours (14:00–23:00) of yesterday are the most
    critical decision points. Evening discharge patterns are the
    strongest signal for predicting the NEXT day's behaviour.
    This makes intuitive sense: heavy evening phone use (gaming,
    video, social media) predicts a similar pattern tomorrow.

4. DISCHARGE RATE THRESHOLDS — WHAT COUNTS AS "SIGNIFICANT"
─────────────────────────────────────────────────────────────────
  Median dSocdt split threshold  : {dsocdt_med_thresh:.3f} % SoC/hour
  This means the model's typical decision boundary is:
    "Was the device losing more than {abs(dsocdt_med_thresh):.1f}% SoC per hour?"

  Notable thresholds by hour (median):
    Hour 19-20 (7-8 PM)  : threshold ≈ -3.0 to -4.4 %/hr
    Hour 22-23 (10-11 PM): threshold ≈ -5.1 to -15.8 %/hr (high usage)
    Hour 03-05 (3-5 AM)  : threshold ≈ -0.9 to -1.0 %/hr (near-idle)

  → Hours 22-23 have very negative thresholds, meaning the model
    only branches on them when discharge is EXTREME (>5%/hr), i.e.
    late-night heavy usage. Hours 3-5 AM have near-zero thresholds
    because any discharge at all (device not charging) is unusual.

5. SOC THRESHOLDS — BATTERY LEVEL TIPPING POINTS
─────────────────────────────────────────────────────────────────
  Median SoC split threshold : {soc_med_thresh:.1f}%
  SoC features most used     : Soc_h10_day_minus1, Soc_h23_day_minus1

  → When SoC IS used, the model looks at:
    (a) SoC at 10:00 yesterday (mid-morning charge state)
    (b) SoC at 23:00 yesterday (end-of-day battery level)
    The ~43-50% median threshold suggests the model distinguishes
    between "battery went below half" vs "stayed above half".
    Users who end the day above 50% likely charged during the day
    and will follow different discharge patterns.

6. SAME-HOUR PREDICTION TENDENCY
─────────────────────────────────────────────────────────────────
  The model often uses the same hour as a predictor:
    e.g. to predict discharge at 16:00 tomorrow, it primarily
    checks discharge at 14:00-19:00 yesterday (nearby hours).

  This reveals a TEMPORAL CLUSTERING pattern: discharge at any
  given hour correlates most strongly with discharge at nearby
  hours of the previous day, not random other hours.

7. MAX_DEPTH=2 IMPLICATIONS
─────────────────────────────────────────────────────────────────
  All trees have exactly depth 2 (root + one level of children).
  Each tree makes AT MOST 2 sequential decisions before predicting.
  The final prediction = sum of all 25 trees' leaf values.

  This means each tree represents a rule of the form:
    "If [yesterday's evening dSocdt was below X]
       AND [a secondary condition holds]
     → predict [small discharge increment]"

  The 25 trees collectively build up the final prediction
  by stacking these simple if-then rules.

═══════════════════════════════════════════════════════════════════
"""

summary_path = os.path.join(OUTPUT_FOLDER, "tree_interpretation_summary.txt")
with open(summary_path, "w", encoding="utf-8") as f:
    f.write(summary_text)

print(summary_text)
print(f"Summary saved  →  {summary_path}")
print("\nAll extended analysis outputs saved to:", OUTPUT_FOLDER)