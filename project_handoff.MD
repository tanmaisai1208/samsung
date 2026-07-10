# PROJECT HANDOFF DOCUMENT
## Predictive Battery Management Through Usage Pattern Recognition

---

# QUICK CONTEXT (Read This First — 5 Minute Overview)

This is a college/research project for Tanmai, developed with a mentor. The goal: predict a phone's future battery discharge patterns from historical State-of-Charge (SoC) time-series data, and eventually suggest optimal charging schedules. The reference paper used Self-Organizing Maps (SOM) and got 32–64% weekly accuracy; we're using XGBoost to beat that.

**Two full methodology approaches have been built:**
- **Approach 1** (git `main` branch, folder `results_1`): +ve dSocdt (charging) values were clipped to 0, hourly resampling used interpolation. This let us predict discharge only. Diagnostic testing later revealed the model could not distinguish charging from mild discharge (inverted signal, F1 = 0.03–0.47 for charging detection) — a fundamental flaw.
- **Approach 2** (git `test` branch, folder `results_2`): +ve dSocdt retained (not clipped), resampling changed to average-of-raw-samples-in-±30min-window instead of interpolation, missing hours left as NaN (XGBoost handles NaN natively — no fabrication of data). This fixed the charging blind spot.

Current final hyperparameters (Approach 2): `n_estimators=200, max_depth=2, learning_rate=0.1, subsample=0.95, colsample_bytree=0.8`. Training strategy: **daily rolling window** — train on the preceding 14 actual days (creating 13 synthetic training samples per window via expanding zero-padded sub-windows), predict the single next day's 24 hourly dSocdt values, then slide forward by 1 day and repeat. Accuracy metric: % of hours where `|predicted − actual| ≤ threshold`.

We completed: preprocessing, autocorrelation/Hurst exponent analysis (confirms long-range dependence, H>0.5 for most devices), sequential one-at-a-time hyperparameter tuning, final validation with threshold sweep + cosine similarity, feature importance (dSocdt ~62.5%, Soc ~35.8%, Date ~1.7% in Approach 2), tree rule extraction + interpretation (with visual heatmaps), model size/inference time analysis, and a two-part PDF report generator.

**Currently active work:** a NEW task, split off into `battery_charging_schedule.py`, which reuses the same trained model/features but changes the objective from "predict every hour's dSocdt" to "predict the single hour when the biggest charging event happens each day" (top-1-peak-per-day), evaluated via MAE in hours between actual and predicted peak times. This is for the "suggest optimal charging schedule" use case. We are currently tuning two threshold constants (`MIN_HOURLY_RISE_ACTUAL`, `MIN_HOURLY_RISE_PRED`) to minimize MAE; best so far is ~7.8 hrs at (0.007, 0.0055), and we were mid-way through recommending trying (0.009, 0.007) next when this handoff was triggered.

**User's working style:** wants code fast, minimal preamble, doesn't want re-explanation of things already established, prefers being told "just these N lines changed" rather than reading whole files when only small edits are needed (but will explicitly ask for the "whole file" when needed), runs everything locally on Windows (paths show `C:\Users\...\Desktop\Soc`), iterates a lot via trial-and-error with real numeric feedback from actual runs.

---

# 1. PROJECT OVERVIEW

## What is this project?
An academic/research project titled **"Predictive Battery Management Through Usage Pattern Recognition"**, developed by a student (Tanmai) in collaboration with a mentor. The core task: given historical smartphone battery State-of-Charge (SoC) time-series data for many device/users, train a model to predict future battery discharge behavior on an hourly basis, and — as a downstream use case — recommend/predict when a user is likely to charge their phone (optimal charging schedule suggestions).

## Overall Objective
1. Preprocess raw, irregularly-sampled battery telemetry into clean, regular hourly time series per device.
2. Establish whether the data exhibits **long-range temporal dependence** (via autocorrelation and Hurst exponent analysis) to justify model choice.
3. Train a supervised ML model (XGBoost, later possibly LSTM/Transformer) to predict the next day's 24 hourly discharge-rate (dSocdt) values, using a **daily rolling window** of the preceding 14 days as context.
4. Tune hyperparameters rigorously (sequential coordinate-wise search, since full grid search was computationally infeasible).
5. Validate final model performance with multiple metrics (threshold-based accuracy, MAE, RMSE, cosine similarity).
6. Interpret the model (feature importance, decision tree rule extraction, SHAP planned) to understand *why* it makes its predictions and build trust/explainability.
7. Assess practical deployability (model size, inference time).
8. **Diagnose and fix a major methodological flaw**: originally we clipped positive dSocdt (charging) to zero, assuming "usage" only mattered. This turned out to structurally prevent the model from ever learning to recognize charging events, which was discovered via targeted diagnostic testing (Task A/B). This led to a full methodology revision (Approach 2).
9. Extend the model to a new downstream task: **predicting the timing of charging events** (not just hourly discharge magnitude), to support the "suggest optimal charging schedule" real-world use case.

## Real-world problem solved
Smartphone battery management — if we can predict how a specific user's phone will discharge tomorrow (hour by hour) and when they're likely to plug in to charge, we can:
- Suggest optimal charging windows (e.g., off-peak electricity, or before an important event).
- Warn users of likely low-battery periods.
- Potentially extend battery lifespan by recommending healthier charging habits (e.g., avoid unnecessary top-ups).

## Expected Deliverables
- Full preprocessing pipeline (raw CSV → hourly resampled → wide daily format).
- Statistical analysis outputs (autocorrelation, Hurst exponent, per-device and aggregate).
- Trained XGBoost model with tuned hyperparameters.
- Comprehensive validation results and plots.
- Model interpretability artifacts (feature importance, tree rules, SHAP planned).
- Model complexity/deployability analysis.
- A two-part PDF project report (Approach 1 vs Approach 2) generated via a Python/ReportLab script, auto-populated from actual result files.
- (In progress) A charging-schedule-prediction extension with its own MAE-based evaluation.
- (Not yet started) Comparison against LSTM and/or Transformer models; possibly Tensor Networks (discussed but likely deprioritized).

---

# 2. BACKGROUND AND MOTIVATION

## Why this project was started
The mentor assigned this as a research project to predict smartphone battery usage patterns and eventually provide actionable charging suggestions. A reference paper existed that used **Self-Organizing Maps (SOM)** for pattern clustering, with reported weekly accuracies (test windows of 7 days each, sliding by 1 week over a 45-day dataset):

| Test Window | SOM Accuracy |
|---|---|
| Days 1–7 | 56.10% |
| Days 8–14 | 32.61% |
| Days 15–21 | 57.14% |
| Days 22–28 | 64.10% |
| Days 29–35 | 60.00% |
| Days 36–42 | 54.17% |
| Days 43–45 | 41.18% |

Our goal was to **beat these numbers** using a different (non-clustering) approach.

## Why XGBoost was chosen
- SOM is unsupervised and does not exploit temporal ordering — it clusters patterns but doesn't model sequence dependence.
- We first computed the **Hurst exponent** across devices and found H > 0.7 for most devices (strong long-range persistence), meaning past discharge patterns genuinely predict future patterns over multi-day/weekly horizons. This directly motivated using a model that could ingest a multi-day window of features (XGBoost with a flattened 14-day feature vector) rather than pure pattern-matching.
- XGBoost was suggested as more tractable to implement than LSTM/Transformer initially, and interpretable (tree rules, feature importance) which mattered for a research report.

## Alternative approaches discussed and rejected/deprioritized
1. **LSTM / Bidirectional LSTM**: Built a full implementation (`battery_lstm.py`) using the same daily-rolling-window strategy, BiLSTM(128)→Dropout→BiLSTM(64)→Dropout→Dense(24), trained with Huber loss, autoregressive prediction over the test week, MinMaxScaler fit only on train data to avoid leakage. Expected only modest improvement (+8–12%) over XGBoost given the tiny training set (13 samples per window) — LSTMs are data-hungry and 13 samples is far too few to reliably learn attention/gating; XGBoost's tree splits are more sample-efficient for this regime. This was built but not necessarily the final chosen path — the project reverted to focus on XGBoost extensively (hyperparameter tuning, interpretability, methodology revision) rather than pursuing LSTM further, at least as of the most recent conversation turns.
2. **Transformers**: Discussed in depth (self-attention mechanism, multi-head attention, positional encoding explained in detail). Verdict: theoretically promising for modeling "which past day matters most" via attention, but **high overfitting risk** given only ~13-14 training samples per window; would need a lightweight variant (Temporal Fusion Transformer / PatchTST). Not yet implemented.
3. **Tensor Networks (specifically Matrix Product State / Tensor Train)**: Explained in depth (physics-origin, decomposing large tensors into chains of small linked tensors, bond dimension as capacity control). Verdict: parameter-efficient and theoretically well-suited to local correlation structure, but tooling is immature (research-stage libraries like `torchmps`), no established pattern for multi-output regression, and implementation complexity is high relative to expected gain. **Deprioritized below Transformers** per mentor's guidance that Transformers would be "easier to try."
4. Neither LSTM, Transformer, nor Tensor Network work has been carried forward into the Approach-2-corrected pipeline yet — this is explicitly listed as future work.

## Why we moved from Approach 1 to Approach 2 (critical background)
After building the full pipeline (preprocessing → tuning → final validation → feature importance → tree rules) under Approach 1, the user asked for two diagnostic checks (**Task A and Task B**, described in detail below) to verify the model could tell charging apart from mild discharge. It could NOT — in fact it showed an **inverted signal** (predicted MORE negative values during actual charging hours than during actual mild-discharge hours), and F1-scores for "detecting" a charging event via near-zero predicted dSocdt ranged only 0.03–0.47 across devices, far below the ~0.5 minimum considered acceptable. Root cause: clipping +ve dSocdt to 0 during preprocessing made "charging" and "idle, no discharge" indistinguishable in the training target — the model had no way to ever learn genuine charging behavior; it could only infer it indirectly (and unreliably) via correlated discharge momentum. This directly motivated the full Approach 2 methodology revision.

---

# 3. COMPLETE TIMELINE OF THE PROJECT

### Stage 1 — Initial resampling + statistical analysis (Approach 1 origin)
- User had raw per-device CSVs with irregular timestamps (median gap ~15 min, sometimes gaps of up to 18 days).
- Built `battery_analysis.py`: parses DateTime (mixed format, UTC → converted to IST, tz stripped), sorts, builds a clean hourly DatetimeIndex spanning the full date range, applies **time-based linear interpolation** (`pandas.interpolate(method='time')`) on Soc and DischargeLevel to fill gaps, re-derives dSocdt as the hourly diff of interpolated Soc, re-derives dayofweek/dayname/month/monthname from timestamp, re-derives ChargingStatus from sign of dSocdt.
- Also in this same file: autocorrelation analysis (lags 0–504 hours = 3 weeks, discharge-only samples, i.e., dSocdt<0) and Hurst exponent via Rescaled Range (R/S) analysis over log-spaced window sizes 24–504 hours, with plots (autocorrelation stem plot with 95% confidence bounds; log(R/S) vs log(window) with fitted-line slope = H).
- Result across many devices: majority H > 0.7 (strong persistence), few in 0.5–0.6, very few 0.4–0.5. Confirmed long-range dependence, motivating sequence-aware modeling.
- Later extended to run on **multiple raw CSV files in a folder** (globbing), storing outputs into `results/resampled_csv/`, `results/ac_hc_plots/`, and a combined `all_users_summary.csv`.

### Stage 2 — Wide format transformation (Approach 1)
- XGBoost needs tabular features, not long time-series rows. Built the "pivot to wide" logic: rows = dates, columns = `dSocdt_h0...h23`, `Soc_h0...h23` (and originally `ChargingStatus_h0...h23` too, later dropped from feature set but sometimes still in the wide CSV).
- Critically, **+ve dSocdt values were clipped to 0** at this stage (`df[DSOCDT_COLS] = df[DSOCDT_COLS].clip(upper=0)`), based on the reasoning "we only care about usage/discharge behavior."

### Stage 3 — Daily rolling-window XGBoost training (`battery_xgboost.py`)
- User specified the exact training protocol after several iterations of clarification:
  - Take **days 1–14** as a training window, predict **day 15** (single next day, not a full week).
  - Then shift the window by **1 day**: train on days 2–15, predict day 16. Repeat until end of data.
  - This is different from an earlier (rejected) design where training window (2 weeks) and test window (1 week) both shifted by 1 week at a time, matching the SOM paper's evaluation style — user explicitly said this was NOT what they wanted; they wanted **daily** granularity, matching a more realistic "retrain every day on freshest data" deployment scenario.
  - Because each iteration only has 1 window to fit on, an "expanding sub-window" trick generates 13 synthetic training samples per iteration: sample k uses days `[train_start...train_start+k-1]` (zero-padded at front to reach the full 14-day feature length) to predict day `train_start+k`, for k=1..13.
  - Final prediction for the day of interest uses the **full real 14-day window** as input.
  - Predictions clipped to ≤ 0 in Approach 1 (removed in Approach 2, see below).
- Feature vector (Approach 1): for each of 14 days — 24 dSocdt + 24 Soc + 4 date features (dayofweek, day, month, year) = 52 features/day × 14 = **728 total features**. (Date features were later found to have negligible importance — 0.026%! — user tried removing them + reducing to 7-day window, but this *decreased* accuracy by ~0.5%, so reverted back to 14-day/728-feature setup. This is an important lesson.)
- Model: `MultiOutputRegressor(XGBRegressor(...))` — 24 independent XGBoost regressors, one per output hour, each seeing the same 728-dim input.
- Accuracy metric: for a given day, % of the 24 hours where `|predicted dSocdt − actual dSocdt| ≤ ACC_THRESHOLD`. Device accuracy = mean over all predicted days. Overall = mean over devices.

### Stage 4 — Hyperparameter tuning strategy discussion
- Full grid search (n_estimators × max_depth × learning_rate × subsample = ~648 combinations) was tried once but took too long (~40 min per combination across all devices).
- Mentor suggested **sequential/coordinate-wise tuning**: fix all params except one, sweep that one, pick its best value, fix it, move to the next param. Tune in order: n_estimators → max_depth → learning_rate → subsample.
- Built `battery_hypersearch.py` with:
  - `joblib.Parallel(n_jobs=-1, prefer="threads")` for parallel execution across param values.
  - JSON checkpoint files (`checkpoint_<param>.json`) so interrupted runs (e.g., laptop screen-locked) resume without recomputation — this was an explicit requirement ("keep running even if I lock the screen and go home").
  - Separate output files per parameter: `checkpoint_<param>.json`, `results_<param>.csv`, `best_<param>.json`, `validation_curves/val_curve_<param>.png` — NOT shared across params, so each tuning stage's evidence is preserved independently for the report.
  - Pre-computed feature matrices once per device (not per hyperparameter combo) for speed.
- User later fixed several bugs found when actually running this: sklearn's `MultiOutputRegressor.fit()` rejects NaN in **y** (targets) even though XGBoost itself handles NaN in **X** (features) natively — required skipping training samples where the target vector has NaN, and skipping prediction days where the actual vector is entirely NaN, and evaluating MAE/accuracy only on the non-NaN hours of a partially-NaN day (see Problems Encountered section for full details).
- Approach 1 final tuned hyperparameters: `n_estimators=25, max_depth=2, learning_rate=0.05, subsample=0.95, colsample_bytree=0.8` (colsample_bytree kept fixed throughout, never tuned).
- Approach 2 final tuned hyperparameters (after redoing tuning on revised data): `n_estimators=200, max_depth=2, learning_rate=0.1, subsample=0.95, colsample_bytree=0.8`. Note max_depth showed **identical accuracy (68.27%) for values 2, 3, and 4** — the simplest value (2) was kept to minimize overfitting risk given tiny per-window sample counts.

### Stage 5 — Final validation (`battery_final_validation.py`)
- Runs the daily rolling window one more time with the finally-chosen hyperparameters, across all devices, sweeping `ACC_THRESHOLD` over 1–10, and additionally computing **cosine similarity** between the actual and predicted 24-hour dSocdt vectors per day (captures whether the model gets the *shape* of the daily curve right, even if magnitudes are off).
- Also computes MAE and RMSE per day.
- Plots: `threshold_accuracy_curve.png` (overall mean accuracy vs threshold, one line per device + black "overall mean" line), `cosine_similarity_plot.png` (bar chart per device + overall mean line), and per-device plots.

### Stage 6 — Per-device plot redesign (iterative refinement)
- Originally per-device plot had 4 stacked panels: daily accuracy w/ 7-day rolling mean, daily MAE, daily cosine similarity, and an overlaid actual-vs-predicted line plot for ~8 sampled days all on one axis (very cluttered).
- User explicitly requested simplification: **remove the first three panels entirely** (their aggregate values already feed the separate `cosine_similarity_plot.png` / `threshold_accuracy_curve.png` files, so per-device redundancy wasn't needed), and replace the cluttered overlay with a **grid of up to 6 separate subplots**, each showing ONE sampled day's actual (solid) vs predicted (dashed) 24-hour curve, sampled every 7 days, covering at most the first 48 days, arranged in a 3-column grid.
- Final function name: `plot_device()`, output: `final_validation_plot_<device>.png`.

### Stage 7 — Feature importance analysis (`battery_feature_import.py`)
- Trains XGBoost with best hyperparameters, pools data across ALL devices, extracts `feature_importances_` from each of the 24 per-hour `XGBRegressor` sub-estimators inside the `MultiOutputRegressor`, averages across hours.
- Three plots: top-30 features bar chart, importance-by-type (dSocdt vs Soc vs Date) grouped bar, importance-by-recency (days-back) grouped bar.
- Approach 1 result: dSocdt ≈ 86.3%, Soc ≈ 10.9–11.1%, Date ≈ 2.6–2.7%.
- This led directly to the (later reverted) experiment of dropping date features and reducing to a 7-day window — accuracy dropped ~0.5%, so this was abandoned; kept the original 14-day/728-feature setup for all subsequent work.

### Stage 8 — Tree rule extraction and interpretation (`battery_tree_rules.py` + `battery_tree_analysis_extended.py`)
- Uses XGBoost's `booster.get_dump(dump_format="json")` to extract every split node (feature, threshold, depth, node_id) from every tree of every one of the 24 hour-estimators. Recursively parses into human-readable if/then rule text.
- Outputs: `tree_rules_hour_XX.txt` (per hour), `tree_rules_all.txt` (combined), `tree_rules_summary.csv` (one row per split node).
- Extended interpretation script produces 5 plots: root-node feature frequency, an enhanced "past hour vs future hour" heatmap, dSocdt threshold-per-hour analysis, SoC threshold distribution, and recency-dominance line chart. Also writes `tree_interpretation_summary.txt`.
- Approach 1 key findings: 73.1% of splits use only yesterday's data (day-minus-1), 90.9% use yesterday-or-day-before; top root features are evening-hour dSocdt (h19, h14, h23, h20, h15 of day-minus-1); median dSocdt threshold ≈ -3.0%/hr; SoC threshold ≈ 43%.
- **Bug found and fixed**: hardcoded annotation-offset (`v - 0.8`) crushed Approach 2's much smaller dSocdt magnitudes (~0.0003–0.003) into an invisible sliver on the y-axis. Fixed by computing offset as a fraction of the actual data range instead of a hardcoded constant, and changing text format from `.1f` to `.4f`.
- Approach 2 key findings: 96.0% splits use day-minus-1 only, 99.9% use day-minus-1-or-2; top root features now include dSocdt_h17, dSocdt_h20, dSocdt_h4 (day_minus1) plus Soc_h8 and day_day_minus1; 76.6% of dSocdt thresholds negative, 22.7% positive (new capability, impossible under Approach 1's clipping); root splits 63.4% dSocdt / 31.3% Soc / 5.2% Date; SoC median threshold ≈ 51%.

### Stage 9 — Model complexity analysis (`model_size_curve.py`)
- Trains on synthetic data (same 728-feature structure, same hyperparameters) across training-sample-counts 60–365 (step 15), measures serialized model size (pickle, KB) and single-sample inference time (ms).
- Model size nearly constant (~618–621 KB), polynomial fit degree 3, R²=0.629. Inference time roughly constant, median ~47ms, scatter 35–125ms attributed to OS/interpreter noise.
- Conclusion: lightweight enough for on-device/edge deployment.

### Stage 10 — SHAP analysis (`battery_shap.py`)
- `shap.TreeExplainer` per hour-estimator (24 explainers), 200 sampled rows, 7 plots (summary bar, beeswarm, by-type, by-recency, dependence-top4, waterfall for 6 individual predictions, feature×hour heatmap), plus 2 CSVs.
- **Bug fixed**: `numpy.ndarray.ptp()` removed in NumPy 2.0; replaced both occurrences with `(arr.max() - arr.min())`.
- Built for Approach 1's context; not yet re-run for Approach 2.

### Stage 11 — Report generation (`generate_report.py`, ReportLab-based)
- First version: single-approach report (Approach 2 only), 11 sections, auto-pulls plots, computes live statistics from actual CSV/JSON files.
- Second version: extended to cover BOTH approaches — Part A (Approach 1, includes Section 7 "Charging-Detection Diagnostic" and Section 8 "Limitations Identified") + Part B (Approach 2).
- Third version (current): switched to the **`results_1` / `results_2` folder convention** (copies of `main` branch results and `test` branch results, both placed side-by-side in the `test` branch's working directory). `PATHS_1` and `PATHS_2` dicts. Added Section 9 "Model Size & Inference Time Analysis" for Approach 1. Expanded per-approach tree-rules interpretation prose to match the same depth for BOTH approaches (initially asymmetric — Approach 2's tree-rules section only showed plots with no interpretive text; fixed by computing real numbers from Approach 2's `tree_rules_summary.csv`).
- Task A/B diagnostic plots for Approach 1's Section 7/10 were NOT available in the results_1.zip the user uploaded (exist on a different device, to be added later) — handled via clearly-labeled placeholder paths + a `notebox()` explaining they're pending.

### Stage 12 — Task A / Task B charging diagnostics (within `battery_final_validation.py`, Approach 1)
- **Task A** (`charging_discrimination_stats`): splits (day,hour) pairs by ground truth into Group1 (actual dSocdt==0) and Group2 (actual mild discharge, -1.0 ≤ actual < 0), compares the model's PREDICTED values for each group. Computes `separation_gap = mean_pred_charging − mean_pred_mild`.
- **Task B** (`charging_event_detection_stats`): binary classification framing — ground truth positive = actual dSocdt==0, predicted positive = `|predicted dSocdt| ≤ epsilon`. Computes precision/recall/F1. Swept epsilon over [0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0].
- **Result**: separation_gap NEGATIVE for every device (inverted signal). User correctly pointed out the code should compare ABSOLUTE separation, not signed — fixed by adding `abs_separation_gap` and a `direction` field ("CORRECT" vs "INVERTED"). Root cause: the model learned "strong recent discharge momentum" as its dominant signal, and heavy discharge momentum often directly precedes a charging event in real life, so the model's momentum-based signal coincidentally but wrongly fires strongest right before charging. F1 scores ranged 0.03–0.47 across devices; F1>0.5 acceptable, >0.65 good, >0.8 very good for this use case — current results mostly below acceptable.
- This diagnostic finding is what triggered the full Approach 2 revision.

### Stage 13 — Approach 2 methodology change (the big pivot)
- User: "we shouldn't even do resampling of data into hourly format using interpolation" — instead:
  - For each target hour H (0-23) on each date, collect all RAW rows with timestamp in `[H:00 - 30min, H:00 + 30min)` and **average** ChargingStatus, Soc, DischargeLevel, dSocdt across them.
  - If NO raw rows fall in that window → fill the entire hour-row with **NaN** (not interpolated!) — user's reasoning: "XGBoost internally tries to fill the missing values in a better way."
  - Built as `battery_resample_and_pivot.py`: Step 1 = raw CSV → hourly-averaged CSV, Step 2 = hourly CSV → wide daily CSV, with **+ve dSocdt retained as-is** (no clipping) at both stages.
  - Required propagating NaN-safety through every downstream script (see Problems Encountered).
  - Removed Task A/Task B diagnostic code from `battery_final_validation.py` for Approach 2 (no longer needed).
  - Re-ran the Hurst/autocorrelation step across all 34 devices.

### Stage 14 — Charging Schedule Prediction (current active work, `battery_charging_schedule.py`)
- New downstream task, using the SAME trained model/features as `battery_final_validation.py` (no new hyperparameter tuning), but predicting WHEN (which hour) a "significant" charging event happens each day.
- **Critical clarification from user mid-development**: `dSocdt` represents **(fractional SoC change) / (minutes passed)** — a rate-per-minute, even after hourly averaging (averaging doesn't change the unit). Required `total_rise = sum(dSocdt over contiguous run) * 60` to convert accumulated per-minute rate into approximate total % SoC gained.
- Measured actual data (std of dSocdt across all devices ≈ 0.003) to calibrate thresholds empirically:
  - `MIN_HOURLY_RISE`: initially guessed 0.05 (too strict, detected ZERO events), corrected to **0.007** (≈2.3 std devs).
  - `MIN_CHARGE_RISE`: initially guessed 15.0 (assumed multi-hour events), discovered from an uploaded sample wide_csv that real charging events are almost always ISOLATED SINGLE-HOUR spikes (max observed run summed to ~1.08 after ×60). Corrected to **0.35**.
- Two parallel threshold sets (`_ACTUAL` vs `_PRED`) introduced because XGBoost's regression output systematically **underpredicts sharp single-hour spikes**. Predicted-side thresholds set looser initially (`MIN_HOURLY_RISE_PRED=0.004`, `MIN_CHARGE_RISE_PRED=0.20`).
- First full run (multi-event-per-day version, TP/FP/FN via nearest-event matching): detection rate ~80%, false alarm rate ~75% — user correctly diagnosed the percentage comparison as misleading (different denominators: days-with-actual-events vs days-without). Requested switching to **absolute counts**: TP/FP/FN, implemented via `plot_tp_fp()`.
- User requested tightening predicted-side threshold: `MIN_HOURLY_RISE_PRED` 0.004→0.0055; FP was still too high relative to TP.
- **Final major simplification**: user requested dropping the multi-event TP/FP/FN framework entirely — "take the TOP 1 peak only, in both actual trajectory and predicted trajectory." Collapses to `error = |actual_peak_hour − predicted_peak_hour|`, averaged into MAE (hours). Rewrote around `find_top_peak()`. Plots reduced to ONLY `charging_schedule_mae_plot.png` and `charging_schedule_sample_days_<device>.png`.
- User ran this and reported: `MIN_HOURLY_RISE_ACTUAL=0.007, PRED=0.0055` → MAE ≈ 7.8 hrs. Then tried LOWERING both (0.006/0.004) → MAE got WORSE (8.78 hrs). Diagnosed as evidence that loosening lets in spurious secondary bumps that can outrank the true peak — recommended TIGHTENING further, suggesting `MIN_HOURLY_RISE_ACTUAL≈0.009, PRED≈0.007` as the next test, with guidance to search empirically in ranges [0.008–0.012] actual / [0.006–0.009] predicted.
- **THIS IS WHERE THE CONVERSATION WAS CUT OFF FOR HANDOFF.** The user has not yet reported back results from trying the tighter thresholds.

---

# 4. DATASET DETAILS

## Source
Multiple raw CSV files, each representing one device/user's battery telemetry (exact collection mechanism never fully described, only the resulting CSV schema — presumably an Android battery-monitoring app).

## Raw CSV Schema
| Column | Meaning |
|---|---|
| `ID` | Device identifier (long hash-like string). Ignored in modeling. |
| `TimeStamp` | Unix timestamp. Ignored in modeling. |
| `ChargingStatus` | 0 = discharging, 1 = charging (binary flag per raw sample). |
| `Soc` | State of Charge, percentage (0–100). |
| `DischargeLevel` | Raw discharge counter (units not fully specified). |
| `DateTime` | Human-readable timestamp with timezone offset. Irregular sampling — raw gaps range from ~4 min to ~18 days; median ~15 min. |
| `Date` | Derived: `dd-mm-yyyy` string. |
| `dayofweek` | Derived: 0=Monday...6=Sunday. |
| `dayname` | Derived: e.g. "Monday". |
| `month` / `monthname` | Derived. |
| `dSocdt` | **Rate of change of SoC per MINUTE** (not per hour). Positive = charging, negative = discharging, ~0 = idle. Raw magnitude ~0.001–0.01. |

## Data size
- ~70 days of data per device in the original small test set (8 devices), later expanded to 12, then to ~34 devices.
- Raw row counts per device in the thousands (e.g. ~2,523 raw rows over ~70 days).
- After hourly resampling: up to 24 rows/day × ~70-74 days ≈ 1,650-1,780 hourly rows per device (some hours NaN in Approach 2).
- After wide-format pivoting: one row per calendar date, ~69-74 rows per device typically.

## Labels / Target Variable
No external label — self-supervised time-series forecasting. The target for training is the next day's 24 hourly `dSocdt` values (24-dim continuous regression target).

For Charging Schedule task: effective "target" is a single derived scalar per day — the hour-of-day of the single largest contiguous SoC-rise event, computed via peak-detection logic applied at evaluation time.

## Data splits
No traditional train/test split. **Daily rolling window**: for each day D (starting day 15+), train on days [D-14, D-1] (13 synthetic samples via expanding sub-windows), predict day D, slide forward 1 day, repeat. Feature-importance/tree-rules scripts pool ALL devices' data together instead (for global interpretability, not per-day accuracy).

## Assumptions made
- Data assumed India/IST-relevant (based on consistent tz conversion, never explicitly confirmed).
- ±30 min averaging window assumed wide enough to usually find contributing raw samples.
- "Significant" charging event operationally defined via thresholds, not any external ground-truth label.
- Device identity treated as opaque; no cross-device generalization built yet.

---

# 5. DATA PREPROCESSING

## Approach 1 (`battery_analysis.py`)
1. Parse `DateTime` with `pd.to_datetime(..., format="mixed", utc=True)`, then `.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)`.
2. Sort, set as index.
3. Build clean hourly `pd.date_range` spanning full date range.
4. Union raw irregular index with target hourly index, apply `df.interpolate(method="time", limit_direction="both")` on `Soc`/`DischargeLevel` — time-weighted linear interpolation.
5. Re-index to clean hourly slots.
6. Re-derive `dSocdt` as `Soc.diff()` on the hourly series.
7. Re-derive `dayofweek`/`dayname`/`month`/`monthname` from hourly index.
8. Re-derive `ChargingStatus` as `(dSocdt > 0).astype(int)`.
9. **Clip +ve dSocdt to 0** at wide-CSV-pivot stage.
10. Why: raw samples had irregular gaps (minutes to weeks); models need a fixed-shape 24-hour daily feature vector.

## Approach 2 (`battery_resample_and_pivot.py`) — corrected version
1. Parse DateTime same way.
2. For each date and target hour H (0-23): window `[H:00-30min, H:00+30min)`, average `ChargingStatus`/`Soc`/`DischargeLevel`/`dSocdt` across raw rows in window. If NO rows fall in window → entire hour-row set to **NaN** (not interpolated).
3. Categorical columns derived directly from target-hour timestamp (always known).
4. Why: interpolation fabricates data never measured; this, combined with the clip-to-zero step, destroyed the charging signal. Leaving true gaps as NaN and using XGBoost's native missing-value handling was explicitly preferred.
5. Wide pivot: rows=dates, columns=`dSocdt_h0...h23` + `Soc_h0...h23` (48 columns). **+ve dSocdt retained as-is.** Missing hours remain NaN.

## Missing values handling
- Approach 1: filled upstream via interpolation, downstream scripts never saw NaN.
- Approach 2: NaN preserved, requiring every consuming script to be NaN-aware:
  - Training targets: skip samples with any NaN in target (`if np.any(np.isnan(target)): continue`).
  - Evaluation: mask via `valid_mask = ~np.isnan(y_actual)` before any sklearn metric call or cosine similarity.
  - Skip fully-NaN prediction days entirely.
  - Skip windows with <2 clean training samples.
  - Use `np.nanmean()` / `skipna=True` / explicit `isna().all()` checks before `.idxmax()`.

## Feature selection
- All hourly dSocdt and Soc values across the 14-day window used.
- `DischargeLevel` and `ChargingStatus` NOT used as model input features.
- Date features included; tested removal (reverted — hurt accuracy by ~0.5%).

## Scaling
- XGBoost path: no scaling (tree-based, scale-invariant).
- LSTM path: `MinMaxScaler(feature_range=(-1,1))` fit only on training window per rolling iteration.

## Windowing details
- Window size: 14 days, fixed (7-day experiment reverted).
- Window shift: 1 day at a time (daily rolling, not weekly).
- Sample generation: expanding zero-padded sub-windows (13 samples per iteration).

---

# 6. FEATURE ENGINEERING

## Core per-day feature vector (both approaches)
1. **24 dSocdt values** (`dSocdt_h0`...`h23`) — primary signal, dominates model decisions (86% Approach 1, 62.5% Approach 2 importance).
2. **24 Soc values** (`Soc_h0`...`h23`) — absolute battery level context. Importance jumped from 11% (Approach 1) to 35.8% (Approach 2) — interpreted as SoC becoming a better proxy for "recently finished charging" once dSocdt itself carries charging info.
3. **4 date features per day** (dayofweek, day, month, year) — hypothesized to capture weekly/monthly seasonality. Individually tiny importance (~0.026-2.7%) but ablation removal DECREASED accuracy ~0.5% — kept in final pipeline.

Total: **14 days × 52 features/day = 728 features**.

## Zero-padding for expanding sub-windows
When a synthetic training sample uses fewer than 14 real days, missing earlier days are represented as all-zero 52-dim blocks, front-padded, keeping total input fixed at 728-dim.

## Derived features for Charging Schedule task (evaluation-time only, not model input)
- **Contiguous rising-run detection**: maximal contiguous sequence of hours where `dSocdt > MIN_HOURLY_RISE`.
- **Total rise per run**: `sum(dSocdt values in run) * 60` (converts per-minute rate-sum to approximate total % SoC gained).
- **Representative event hour**: rise-weighted average of hours in the run (`np.average(run_hours, weights=run_vals)`).
- **Top-1 peak selection**: among all runs in a day, pick the one with highest `total_rise`; return its representative hour (or `None` if no run qualifies).
- Two independently-tunable threshold sets: `MIN_HOURLY_RISE_ACTUAL` vs `MIN_HOURLY_RISE_PRED`.

---

# 7. MODELS AND ALGORITHMS USED

## 7.1 XGBoost (MultiOutputRegressor) — PRIMARY, FULLY IMPLEMENTED
- **Architecture**: 24 independent `XGBRegressor` instances (one per output hour), wrapped by `MultiOutputRegressor`.
- **Inputs**: 728-dim feature vector.
- **Outputs**: 24-dim vector (predicted dSocdt per hour of next day).
- **Hyperparameters (Approach 1)**: `n_estimators=25, max_depth=2, learning_rate=0.05, subsample=0.95, colsample_bytree=0.8`.
- **Hyperparameters (Approach 2)**: `n_estimators=200, max_depth=2, learning_rate=0.1, subsample=0.95, colsample_bytree=0.8`.
- **Why selected**: sample-efficient (works with only 13 samples/window), handles missing values natively, interpretable, fast, lightweight.
- **Advantages**: robust to tiny-sample regime; tree-split thresholds directly human-readable, gave genuine physical insight.
- **Limitations**: systematically underpredicts sharp single-hour spikes (regression-to-the-mean); can't natively produce a genuine charging-event classifier output.

## 7.2 Bidirectional LSTM (`battery_lstm.py`) — BUILT, NOT PRIMARY FOCUS
- **Architecture**: `Input(shape=(7,73))` → `Bidirectional(LSTM(128, return_sequences=True))` → `Dropout(0.3)` → `Bidirectional(LSTM(64))` → `Dropout(0.3)` → `Dense(24)`.
- Uses a DIFFERENT feature framing than XGBoost (7-day lookback, 73-dim/day: 24 dSocdt + 24 Soc + 24 ChargingStatus + 1 dayofweek) — never unified with the final 728-dim/14-day XGBoost configuration.
- **Hyperparameters**: `EPOCHS=80` (early stopping patience=12), `BATCH_SIZE=8`, Adam lr=1e-3, `ReduceLROnPlateau`, Huber loss, `shuffle=False`.
- **Performance**: NOT actually reported/evaluated in the conversation — built but results never discussed. Gap if continuing.

## 7.3 Transformer — DISCUSSED, NOT IMPLEMENTED
- Self-attention (Q/K/V, `softmax(QK^T/√d_k)V`), multi-head attention, positional encoding explained conceptually.
- Verdict: promising (matches tree-rules finding that day-minus-1 dominates but other days contribute) but high overfitting risk given ~13-sample windows; would need lightweight variant (TFT/PatchTST) and heavy regularization.
- Recommended as NEXT model to try (mentor's guidance), not yet started.

## 7.4 Tensor Networks (MPS/Tensor Train) — DISCUSSED, NOT IMPLEMENTED, LOWER PRIORITY
- Tensor decomposition into chains of small linked tensors, bond dimension = capacity control.
- Verdict: theoretically elegant for local-correlation structure, parameter-efficient, but immature tooling, no established multi-output regression pattern, high implementation complexity. Deprioritized below Transformers.

---

# 8. EXPERIMENTS PERFORMED

## Experiment 1: Full grid hyperparameter search
- **Objective**: exhaustive search over n_estimators × max_depth × learning_rate × subsample (~648 combos).
- **Result**: ~40 min per combination — infeasible.
- **Conclusion**: ABANDONED in favor of sequential coordinate-wise tuning.

## Experiment 2: Sequential tuning, Approach 1
- **Result**: n_estimators=25 (~58.94%), max_depth=2 (~59.10%), learning_rate=0.05 (~59.10%), subsample=0.95 (~59.23%).
- **Conclusion**: final config `{25, 2, 0.05, 0.95, 0.8}`.

## Experiment 3: Sequential tuning, Approach 2
- **Result**: n_estimators=200 (68.27%), max_depth=2 (68.27%, tied with 3/4), learning_rate=0.1 (68.49%), subsample=0.95 (68.78%).
- **Conclusion**: final config `{200, 2, 0.1, 0.95, 0.8}`. Accuracy improved substantially vs Approach 1 (~59%→~68%) from the corrected pipeline alone.

## Experiment 4: Removing date features + reducing window to 7 days
- **Configuration**: dropped 4 date features (52→48/day), TRAIN_DAYS 14→7 (728→336 total features).
- **Result**: accuracy DECREASED ~0.5%.
- **Conclusion**: REVERTED. Lesson: low individual feature importance doesn't prove safety of removal.

## Experiment 5: Task A/B Charging Diagnostics (Approach 1)
- **Result**: separation_gap NEGATIVE for every device (inverted signal); F1 0.03-0.47, inconsistent, no epsilon rescued it.
- **Conclusion**: Approach 1's clip-to-zero design structurally prevented charging-signal learning. Triggered the Approach 2 revision.
- **Lesson**: aggregate metrics didn't reveal this — only targeted diagnostic testing did.

## Experiment 6: Charging Schedule threshold calibration
- Round 1: `0.05/5.0` (guessed) → ZERO events detected. FAILED.
- Round 2: `0.007/0.35` (calibrated against real data std and observed single-hour-spike totals) → ~49 events/53 days. WORKING.
- Round 3 (multi-event TP/FP/FN): detection ~80%, false alarm ~75% — misleading due to denominator mismatch.
- Round 4: absolute counts (TP=97, FP=176, FN=40 overall) — FP nearly double TP; tightened `MIN_HOURLY_RISE_PRED` 0.004→0.0055.
- Round 5: simplified to top-1-peak-per-day, pure MAE metric.
- Round 6: `(0.007, 0.0055)` → MAE≈7.8hrs; `(0.006, 0.004)` [looser] → MAE≈8.78hrs (WORSE). Recommended tightening to `(0.009, 0.007)` — **NOT YET TESTED, conversation cut off here.**

## Experiment 7: SHAP Analysis (Approach 1)
- Successfully generated all 7 plots after fixing `.ptp()` bug. Specific numeric findings not deeply summarized in conversation — a gap; not re-run for Approach 2.

---

# 9. EVALUATION

## Metrics Used and Why
1. **Threshold-based accuracy**: `% hours where |predicted − actual| ≤ ACC_THRESHOLD`. Needed recalibration between approaches due to scale mismatch (Approach 1's dSocdt was `Soc.diff()`-based, larger magnitude; Approach 2's raw per-minute rate is much smaller, std≈0.003).
2. **MAE/RMSE**: standard regression error on 24-hour vectors.
3. **Cosine similarity**: captures curve SHAPE correctness independent of magnitude.
4. **Feature importance**: global model behavior understanding.
5. **Tree-rule statistics**: deeper interpretability than aggregate importance.
6. **Precision/Recall/F1** (Task B only): binary-classification framing for charging detection.
7. **MAE-in-hours** (Charging Schedule): purpose-built for "when does charging happen."
8. **Model size/inference time**: deployability.

## Numerical Results Summary

### Approach 1
| Metric | Value |
|---|---|
| Best hyperparameters | n_est=25, depth=2, lr=0.05, subsample=0.95 |
| Best avg accuracy (tuning) | ~59.23% |
| dSocdt / Soc / Date importance | 86.3% / 10.9-11.1% / 2.6-2.7% |
| Tree-rule recency (day-1 / day-1&2) | 73.1% / 90.9% |
| Model size / inference | ~618-621 KB / median ~47ms |
| Task A separation_gap | Negative for all devices (inverted) |
| Task B F1 | 0.03-0.47 |

### Approach 2
| Metric | Value |
|---|---|
| Best hyperparameters | n_est=200, depth=2, lr=0.1, subsample=0.95 |
| Best avg accuracy (tuning) | ~68.78% |
| dSocdt / Soc / Date importance | 62.5% / 35.8% / 1.7% |
| Tree-rule recency (day-1 / day-1&2) | 96.0% / 99.9% |
| dSocdt threshold sign split | 76.6% negative / 22.7% positive |
| Root split type balance | 63.4% / 31.3% / 5.2% |
| SoC median threshold | 51.0% |

### Charging Schedule task (most recent)
| Config | MAE (hours) |
|---|---|
| ACTUAL=0.007, PRED=0.0055 | ~7.8 hrs |
| ACTUAL=0.006, PRED=0.004 (looser) | ~8.78 hrs (worse) |
| Next test: ~0.009/~0.007 (tighter) | NOT YET TESTED |

Earlier multi-event version: TP=97, FP=176, FN=40, MAE≈5.81hrs (not directly comparable — different event-matching logic).

## Interpretation
Approach 2's accuracy (68% range) noticeably higher than Approach 1 (59% range), attributable to better resampling and richer unclipped signal. SOM baseline (32-64% weekly) not directly comparable due to different evaluation protocols (daily vs weekly) — not rigorously reconciled yet. Charging-schedule MAE (~7.8 hrs) still large in practical terms, actively being optimized.

## Comparison table (Approach 1 vs Approach 2)
| Aspect | Approach 1 | Approach 2 |
|---|---|---|
| +ve dSocdt handling | Clipped to 0 | Retained as-is |
| Resampling method | Interpolation | Average within ±30 min window |
| Missing hours | Filled by interpolation | Left as NaN, handled natively |
| dSocdt / Soc / Date importance | 86.3% / 10.9% / 2.6% | 62.5% / 35.8% / 1.7% |
| Charging detection | F1 = 0.03–0.47 (poor) | Native — charging is part of dSocdt |
| Best hyperparameters | 25/2/0.05/0.95 | 200/2/0.1/0.95 |

---

# 10. IMPORTANT TECHNICAL DISCUSSIONS

## 10.1 Daily vs weekly rolling window
User explicitly corrected an earlier weekly-shift design to daily-shift: train days1-14→predict day15, shift to days2-15→predict day16, etc. Trade-off: always trains on freshest data (recency-optimal) at cost of many more fit operations (56 vs ~8 iterations), which caused the "runs take 40+ min" problem motivating checkpointed/parallel tuning.

## 10.2 Zero-padded expanding sub-windows
Manufactures 13 quasi-independent training samples per rolling-window iteration (since 1 iteration naturally has only 1 sample). Samples overlap heavily (not truly independent) — accepted as "a pragmatic workaround... won't hurt much in practice."

## 10.3 Sequential vs full-grid tuning trade-off
User asked sophisticated question about whether best param values are conditional on tuning order. Answer: yes, this is a known limitation of coordinate-wise search (finds local, not global, optimum); mitigated by recording fixed values used at each stage (in `best_<param>.json`) and doing one final combined validation run to confirm the full set works together.

## 10.4 Checkpointing for long-running jobs
User needed to lock laptop screen and walk away without losing progress. Solution: joblib parallel + JSON checkpoint files tracking completed `(param_value, device)` pairs; results appended to CSV immediately, not held in memory.

## 10.5 Why separation_gap is always negative (deep ML reasoning)
Model's dominant feature is "yesterday evening's discharge magnitude." Heavy recent discharge is often the direct PRECURSOR to charging (user notices low battery, plugs in) — so the model's discharge-momentum signal spuriously but strongly correlates with "charging about to happen," producing a systematically inverted signal when repurposed for charging detection. Presented as a lagging-correlation/confounding-variable problem, not a code bug.

## 10.6 Units of dSocdt (critical, easily-missed detail)
dSocdt = (fractional SoC change)/(minutes elapsed) — a per-MINUTE rate, preserved as such even after hourly averaging. Directly required a `×60` conversion in the Charging Schedule task's "total rise" calculation. Getting this wrong initially led to zero detected events (see Problems Encountered).

## 10.7 Why loosening peak-detection threshold made MAE WORSE
Standard intuition (lower bar → more true positives → better) breaks down for TOP-1-SELECTION problems: loosening admits more NOISY candidates that can occasionally outrank the true (but XGBoost-flattened) peak. Loosening can hurt accuracy in top-1-selection framing even though it helps in simple detect-yes/no framing.

## 10.8 Percentage vs absolute-count metrics for imbalanced comparisons
Detection-rate and false-alarm-rate have DIFFERENT denominators (days-with-events vs days-without), so similar-looking percentages (80% vs 75%) can represent very different real severities. Fixed by switching to absolute counts (TP/FP/FN).

## 10.9 Feature importance vs actual necessity
Low individual importance score doesn't prove safety of removal — collective/interaction effects can be invisible to simple importance ranking. Only reliable test: actual end-to-end ablation (which is what was done, and it showed removal hurt accuracy).

## 10.10 Report-writing philosophy: one continuous document
User reasoned: continuing content in the same file (rather than two separate reports) better tells the narrative of "what challenges were faced → why we moved to the newer approach." Shaped the entire Part A/Part B report structure.

---

# 11. PROBLEMS ENCOUNTERED

## 11.1 `AttributeError: 'numpy.ndarray' object has no attribute 'ptp'`
- **Root cause**: `ndarray.ptp()` deprecated in NumPy 1.24, removed in 2.0.
- **Solution**: replaced both occurrences with `(arr.max() - arr.min())`.

## 11.2 `ValueError: Input y contains NaN` (sklearn MultiOutputRegressor.fit)
- **Root cause**: sklearn's wrapper validates the TARGET (y) array and rejects NaN, even though XGBoost tolerates NaN in FEATURES (X).
- **Solution**: `if np.any(np.isnan(target)): continue` when building the 13 expanding-subwindow training samples — skip any with NaN target.

## 11.3 `ValueError: Input contains NaN` (sklearn mean_absolute_error)
- **Root cause**: partially-NaN days (some hours missing) still passed NaN into metric functions during EVALUATION (not training).
- **Solution**: `valid_mask = ~np.isnan(y_actual)` applied to both actual and predicted arrays before any metric/cosine-similarity call. Wrapped into `safe_mae()`, `safe_rmse()`, NaN-aware `accuracy_at_threshold()`/`cosine_similarity()`.

## 11.4 100% accuracy during max_depth tuning (Approach 2)
- **Root cause**: `ACC_THRESHOLD` inherited unchanged from Approach 1's much larger dSocdt scale; Approach 2's per-minute-rate values (std≈0.003) trivially satisfied the old large threshold.
- **Solution**: recalibrate `ACC_THRESHOLD` proportional to the new data's actual std (~half a std dev as rule of thumb).

## 11.5 `ValueError: Encountered all NA values` (pandas idxmax())
- **Root cause**: for some devices, all prediction days got skipped by NaN-filtering, leaving `mean_accuracy` entirely NaN; `.idxmax()` raises this error on all-NaN Series.
- **Solution**: `if grp["mean_accuracy"].isna().all(): print("SKIPPED"); continue` guards before `.idxmax(skipna=True)`, plus a top-level all-NaN safety check.

## 11.6 Charging-event detection finding ZERO events (Round 1 threshold guess)
- **Root cause**: TWO compounding errors — `0.05` was ~16 std devs too strict; `5.0` assumed multi-hour sustained ramps but real events are isolated single-hour spikes.
- **Diagnosis**: user supplied an actual wide_csv sample; direct numpy analysis revealed true noise scale and run-length distribution.
- **Solution**: `MIN_HOURLY_RISE=0.007`, `MIN_CHARGE_RISE=0.35`, verified to detect ~49 events/53 days.

## 11.7 Detection-rate ≈ False-alarm-rate despite different real severity
- **Root cause**: different denominators (days-with-events vs days-without).
- **Solution**: switched to absolute TP/FP/FN counts with `plot_tp_fp()`.

## 11.8 MAE getting WORSE when loosening thresholds
- **Root cause**: loosening in a top-1-selection framing lets noisier candidates compete for "highest total_rise," sometimes beating the true (flattened) peak.
- **Solution (in progress, NOT YET CONFIRMED)**: recommended tighter thresholds (~0.009/~0.007) as next test — conversation cut off before user reported results.

---

# 12. CODE STRUCTURE

## Folder hierarchy
```
project-folder/                          (test branch checked out)
  results_1/                             <- copy of main branch's results (Approach 1)
    ac_hc_plots/
    resampled_csv/
    wide_csv/
    all_users_summary.csv
    xgboost/
      feature_importance/
        feature_importance.csv, feature_importance_top30.png,
        feature_importance_by_type.png, feature_importance_by_day.png
      final_validation/
        final_predictions_<device>.csv, final_summary_all_thresholds.csv,
        cosine_similarity_summary.csv, cosine_similarity_plot.png,
        threshold_accuracy_curve.png, final_validation_plot_<device>.png,
        charging_discrimination_plot.png (placeholder),
        charging_event_detection_plot.png (placeholder),
        charging_zero_threshold_sweep_plot.png (placeholder)
      hypersearch/
        checkpoint_<param>.json, results_<param>.csv, best_<param>.json,
        validation_curves/val_curve_<param>.png
      tree_rules/
        tree_rules_hour_00.txt...23.txt, tree_rules_all.txt,
        tree_rules_summary.csv, tree_interpretation_summary.txt,
        tree_interp_root_features.png, tree_interp_hour_vs_predictor.png,
        tree_interp_dsocdt_thresholds.png, tree_interp_soc_thresholds.png,
        tree_interp_recency_dominance.png
      model_size_vs_samples.png, inference_time_vs_samples.png
      shap/ (7 plots + 2 CSVs)

  results_2/                             <- Approach 2 results (test branch)
    (same substructure, from revised pipeline)
    xgboost/
      final_validation/  (no Task A/B files)
      charging_schedule/  <- NEW, Stage 14
        charging_schedule_predictions_<device>.csv,
        charging_schedule_summary.csv,
        charging_schedule_mae_plot.png,
        charging_schedule_sample_days_<device>.png
    project_report.pdf                   <- OUTPUT of generate_report.py

  battery_analysis.py                    <- Approach 1: resampling (interpolation) + AC/Hurst
  battery_resample_and_pivot.py          <- Approach 2: resampling (averaging, NaN) + pivot
  battery_pivot_wide.py                  <- (intermediate/legacy) wide-CSV pivot only
  battery_xgboost.py                     <- core daily-rolling XGBoost train/predict
  battery_hypersearch.py                 <- sequential hyperparameter tuning
  battery_final_validation.py            <- final validation (Approach 1 has Task A/B; Approach 2 doesn't)
  battery_feature_import.py              <- feature importance analysis
  battery_tree_rules.py                  <- tree rule extraction
  battery_tree_analysis_extended.py      <- tree rule interpretation plots + summary txt
  battery_lstm.py                        <- Bidirectional LSTM (built, not primary focus)
  model_size_curve.py                    <- model size/inference time analysis
  battery_shap.py                        <- SHAP analysis
  battery_charging_schedule.py           <- NEW: top-1-peak charging schedule prediction + MAE
  generate_report.py                     <- two-part PDF report generator
```

## Execution flow
1. `battery_resample_and_pivot.py` (Approach 2) or `battery_analysis.py` (Approach 1) — raw → resampled → wide CSVs.
2. Hurst/AC analysis (bundled in `battery_analysis.py` for Approach 1; separate re-run for Approach 2).
3. `battery_hypersearch.py` — run 4× sequentially (n_estimators → max_depth → learning_rate → subsample).
4. `battery_final_validation.py` — with tuned `BEST_PARAMS`.
5. `battery_feature_import.py` — pooled feature importance.
6. `battery_tree_rules.py` + `battery_tree_analysis_extended.py` — tree extraction + interpretation.
7. `model_size_curve.py` — independent, any time after BEST_PARAMS known.
8. `battery_shap.py` — pooled SHAP analysis.
9. `battery_charging_schedule.py` — reuses BEST_PARAMS, independent of steps 5-8.
10. `generate_report.py` — run LAST, reads both `results_1/` and `results_2/`.

## Key libraries
`pandas`, `numpy`, `xgboost`, `scikit-learn`, `matplotlib` (Agg backend), `joblib`, `json`, `shap`, `tensorflow`/`keras` (LSTM only), `reportlab` (report only), `pickle`/`os`/`time` (model_size_curve only).

## Environment note
User runs on **Windows** (PowerShell, `C:\Users\chennagiri.s\Desktop\Soc`). Use `os.path.join()` throughout for cross-platform safety.

---

# 13. CURRENT STATE OF THE PROJECT

## Completed and working
- Approach 1: full pipeline (resampling, AC/Hurst, tuning, final validation, feature importance, tree rules, model complexity, SHAP, Task A/B) — built and run with real results.
- Approach 2: full pipeline EXCEPT SHAP — built and run with real results.
- Two-part PDF report generator — tested end-to-end against real data, builds successfully.
- Charging Schedule prediction — functional, run multiple times, ACTIVELY BEING TUNED (not finalized).

## Partially complete
- SHAP: only Approach 1, not re-run for Approach 2 (known gap, listed in report's own Next Steps).
- Report's Task A/B section: placeholder paths for 3 plots pending user copying files in from another device.
- Model complexity analysis: only run for Approach 1's hyperparameters (n_est=25); not re-run for Approach 2's n_est=200.

## Needs testing / unfinished
- **Charging Schedule threshold tuning**: MOST RECENT active work. Current best MAE≈7.8hrs at (0.007, 0.0055). Next recommended test (0.009, 0.007) NOT YET TRIED — this is the immediate next action.
- LSTM: built but never actually run/evaluated/reported — unclear completion status.
- Transformer: zero code written, conceptually discussed only.
- Tensor Network: zero code written, deprioritized.
- Rigorous SOM-baseline comparison: not formally established (different evaluation granularities).

## Current best-performing solution
Core task: **Approach 2 XGBoost**, `n_estimators=200, max_depth=2, learning_rate=0.1, subsample=0.95, colsample_bytree=0.8`, ~68.78% tuning-stage accuracy.

Charging-Schedule task: same model reused, top-1-peak logic, MAE≈7.8hrs at current best thresholds — actively improving.

---

# 14. REMAINING WORK (Priority Order)

1. **[IMMEDIATE]** Continue Charging Schedule threshold tuning: try `MIN_HOURLY_RISE_ACTUAL≈0.009, MIN_HOURLY_RISE_PRED≈0.007` (and nearby values in ranges 0.008-0.012 actual / 0.006-0.009 predicted), report MAE, converge empirically.
2. Consider whether additional interpretive plots beyond MAE would help (e.g., reintroduce an error-distribution histogram if useful — was removed per user's simplification request but could be reconsidered).
3. Add Task A/B diagnostic PNGs into `results_1/xgboost/final_validation/` (file-copying only, no code changes needed).
4. Re-run `battery_shap.py` against Approach 2's model/data; write interpretive summary.
5. Re-run `model_size_curve.py` with Approach 2's hyperparameters (n_estimators=200); add corresponding report section to Part B.
6. Decide on and complete or deprioritize the LSTM comparison.
7. Implement a lightweight Transformer using the same evaluation protocol/feature framing, with small d_model (32-64), 2-4 heads, heavy dropout (0.3-0.5), weight decay.
8. (Lower priority) Tensor Network (MPS) implementation, only if specifically requested.
9. Establish rigorous SOM-baseline comparison methodology, reconciling daily vs weekly evaluation granularities.
10. Consider cross-device generalization (train pooled, test held-out devices) as an extension.
11. Final report polish once all analyses complete.

---

# 15. IMPORTANT ASSUMPTIONS

1. Raw CSV `DateTime` values reliably parse with `format="mixed", utc=True` then IST conversion — implies India/IST-relevant users (never explicitly confirmed).
2. ±30-minute averaging window is "wide enough" — specified directly, never empirically varied as a hyperparameter.
3. "Significant" charging events adequately captured by the two-threshold heuristic — no external ground-truth label exists; purely derived/calibrated against observed distributions.
4. 14-day lookback / 1-day shift is the correct final granularity — explicitly decided after rejecting weekly-shift and reverting a 7-day-window experiment.
5. Device IDs treated as fully independent in final_validation/charging_schedule (per-device models); pooled only for feature_importance/tree_rules interpretability purposes, not production generalization. No held-out-device testing performed.
6. XGBoost's native NaN-handling assumed acceptable substitute for imputation — not independently verified against an imputation baseline.
7. Hurst/autocorrelation findings justify the CHOSEN window length (14 days) directionally/qualitatively, not via precise quantitative derivation.
8. The ×60-minute conversion for "total rise" assumes the ±30-min-averaged hourly dSocdt uniformly applies across the full 60-minute hour — an approximation, not exact.

---

# 16. KEY INTUITIONS DEVELOPED

1. **Low individual feature importance ≠ safe to remove.** Date-feature-removal experiment cost ~0.5% accuracy despite 0.026% individual importance. Always validate removal with actual ablation, never trust importance-ranking alone.

2. **Aggregate metrics can hide structural blind spots.** Approach 1's accuracy/MAE/cosine-similarity all looked fine while the model had an inverted charging signal. Targeted diagnostic tests are essential, not just overall error rates.

3. **A model can learn a real but WRONG-DIRECTION correlation.** The inverted charging signal is a genuine confounding-variable trap — heavy discharge correlates with both "more discharge tomorrow" (useful) and "charging imminent" (backwards when repurposed). Watch for lagging-correlation traps when repurposing a model's output for a different question than it was trained for.

4. **Data units matter and are easy to silently get wrong.** The "per-minute not per-hour" dSocdt clarification directly explains early threshold miscalibration. Always re-derive/re-confirm a column's TRUE units from first principles, not from its name.

5. **Looser detection thresholds are not always "safer"** for TOP-1-SELECTION tasks — loosening admits more noise candidates that can outrank the true signal. Standard recall-vs-precision intuition breaks down here.

6. **Percentage metrics with different denominators can be deeply misleading.** Prefer absolute counts when comparing asymmetric categories, or always report denominators explicitly.

7. **XGBoost regression systematically underpredicts sharp, rare spikes** (regression-to-the-mean) — explains Task B struggles and the need for asymmetric actual-vs-predicted detection thresholds.

8. **Sequential/coordinate-wise hyperparameter tuning is a PRACTICAL compromise, not a global optimizer** — acceptable when properly documented and validated with a final combined run.

9. **Checkpointing isn't optional** for expensive, long-running per-device/per-hyperparameter loops.

10. **Prefer leaving genuine gaps as NaN over fabricating values via interpolation**, whenever the downstream model handles missing values natively. This was the single most consequential methodology decision in the project.

---

# 17. FREQUENTLY USED COMMANDS AND CODE SNIPPETS

## Standard XGBoost model instantiation
```python
from xgboost import XGBRegressor
from sklearn.multioutput import MultiOutputRegressor

BEST_PARAMS = {
    "n_estimators": 200, "max_depth": 2, "learning_rate": 0.1,
    "subsample": 0.95, "colsample_bytree": 0.8,
    "random_state": 42, "verbosity": 0,
}
model = MultiOutputRegressor(XGBRegressor(**BEST_PARAMS), n_jobs=-1)
```

## Date-feature extraction
```python
def date_feats(date_str):
    ts = pd.Timestamp(date_str)
    return [float(ts.dayofweek), float(ts.day), float(ts.month), float(ts.year)]
```

## Core feature-vector builder (full 14-day window)
```python
def build_feature_row(wide, train_start, train_end):
    feats = []
    for i in range(train_start, train_end):
        feats.extend(wide.iloc[i][DSOCDT_COLS].tolist())
        feats.extend(wide.iloc[i][SOC_COLS].tolist())
        feats.extend(date_feats(wide.index[i]))
    return np.array(feats, dtype=float)
```

## Zero-padded expanding sub-window builder
```python
def build_padded_feature_row(wide, context_start, context_end, pad_days):
    feats = [0.0] * (pad_days * FEATS_PER_DAY)
    for i in range(context_start, context_end):
        feats.extend(wide.iloc[i][DSOCDT_COLS].tolist())
        feats.extend(wide.iloc[i][SOC_COLS].tolist())
        feats.extend(date_feats(wide.index[i]))
    return feats
```

## NaN-safe training-sample construction
```python
X_train, y_train = [], []
for k in range(1, TRAIN_DAYS):
    target = wide.iloc[train_start + k][DSOCDT_COLS].values.astype(float)
    if np.any(np.isnan(target)):
        continue
    feats = build_padded_feature_row(wide, train_start, train_start + k, TRAIN_DAYS - k)
    X_train.append(feats); y_train.append(target)
if len(X_train) < 2:
    continue
```

## NaN-safe evaluation
```python
def accuracy_at_threshold(actual, predicted, threshold):
    valid = ~np.isnan(actual)
    if valid.sum() == 0:
        return np.nan
    return float(np.mean(np.abs(actual[valid] - predicted[valid]) <= threshold)) * 100.0
```

## Charging event / peak detection (top-1-peak, current design)
```python
def find_top_peak(dsocdt_24h, min_hourly_rise):
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
    return max(runs, key=lambda x: x[0])[1]
```

## Checkpoint load/save pattern
```python
def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_checkpoint(done_set):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(list(done_set), f)
```

## joblib parallel batch pattern
```python
import joblib
batch_results = joblib.Parallel(n_jobs=-1, prefer="threads")(
    joblib.delayed(process_value)(v, all_device_data, done_set)
    for v in batch
)
```

## Tree rule extraction core
```python
booster = xgb_estimator.get_booster()
tree_dumps = booster.get_dump(dump_format="json")
tree_json = json.loads(tree_dumps[tree_idx])
# has: nodeid, depth, split ("fN" feature index), split_condition (threshold),
# yes/no (child ids), children (list), or "leaf" (value) for leaves
```

## Wide CSV column naming convention
```python
HOURS = list(range(24))
DSOCDT_COLS = [f"dSocdt_h{h}" for h in HOURS]
SOC_COLS    = [f"Soc_h{h}"    for h in HOURS]
# wide CSV: index = "Date" (yyyy-mm-dd string), columns = DSOCDT_COLS + SOC_COLS
```

## Report generator's live-stat pattern
```python
def hurst_breakdown(csv_path):
    if not os.path.exists(csv_path):
        return None
    df = pd.read_csv(csv_path)
    n_total = len(df)
    n_pers  = df["Regime"].str.contains("Persistent").sum()
    n_rand  = df["Regime"].str.contains("Random").sum()
    n_anti  = df["Regime"].str.contains("Anti").sum()
    mean_h  = df["HurstExponent"].mean()
    return n_total, n_pers, n_rand, n_anti, mean_h
```

---

# 18. FINAL CONCLUSIONS SO FAR

## Current findings
- Long-range temporal dependence (H>0.5, mostly H>0.7) confirmed across most devices, validating the sequence-aware, multi-day-window modeling strategy.
- Approach 1's clip-to-zero design was a genuine, consequential flaw — structurally prevented the model from learning charging behavior, producing a measurably INVERTED signal.
- Approach 2 resolved this and also IMPROVED overall regression accuracy (~59%→~68%), shifting feature importance to be more physically sensible.
- The model is lightweight and practically deployable (per Approach 1's complexity analysis; needs re-verification for Approach 2's larger n_estimators).
- The newest Charging Schedule extension works functionally but has a fairly large MAE (~7.8 hours, trending toward improvement) — genuinely unfinished, actively-tuned work as of cutoff.

## Achievements
- Complete, reproducible, checkpoint-resumable pipeline from raw irregular CSVs through fully interpreted, validated, deployability-assessed XGBoost model — twice over — plus a live-data-driven comparative PDF report.
- A rigorous, evidence-based methodological correction (Approach 1→2) driven by targeted diagnostic testing.
- Deep model interpretability work providing genuine physical/behavioral insight beyond just accuracy numbers.

## Remaining research questions
- True achievable floor for Charging-Schedule MAE with regression-repurposed-as-event-detector vs a purpose-built classifier trained directly on ChargingStatus?
- Would Transformer/LSTM meaningfully outperform XGBoost given Approach 2's corrected data, or does the 13-samples-per-window constraint cap benefit regardless of model complexity?
- How does daily-granularity accuracy genuinely compare to SOM's weekly-granularity numbers? Not yet rigorously reconciled.

## Confidence in current approach
High confidence in the CORE methodology (Approach 2 pipeline + XGBoost daily rolling window) — well-validated, well-diagnosed, every major design choice documented and defensible. Lower (appropriately) confidence in the Charging-Schedule threshold calibration — explicitly acknowledged as ongoing, unfinished empirical work.

---

# 19. INSTRUCTIONS FOR FUTURE CLAUDE

## How to continue this project
1. Read the Quick Context section first, then this full document, before writing any code.
2. **Immediate next action**: help the user try tighter charging-schedule thresholds (`MIN_HOURLY_RISE_ACTUAL≈0.009, MIN_HOURLY_RISE_PRED≈0.007`, or nearby values) in `battery_charging_schedule.py`, interpret the MAE the user reports back, continue iterating empirically. Do NOT assume you know the "right" threshold analytically.
3. For small threshold/config-change requests: just make the exact requested edit and return the file, no re-derivation of settled decisions.
4. For genuinely NEW work: reason through the design carefully first (as was done for LSTM/Transformer/Tensor-Network discussions and the original charging-schedule design), but execute FAST once the design is settled.

## Important context that must not be forgotten
- **dSocdt is per-MINUTE, not per-hour**, even after hourly averaging. Any accumulation logic needs the `×60` conversion.
- **Two parallel result sets exist**: `results_1` (Approach 1/main) and `results_2` (Approach 2/test). The report generator uses `PATHS_1`/`PATHS_2` dicts. Don't collapse them.
- **Approach 1's Task A/B plots are still missing** from `results_1/xgboost/final_validation/` — placeholder paths in the report, no code change needed once files are added.
- **Charging-schedule reuses Approach 2's ALREADY-TUNED hyperparameters** — do not suggest re-tuning.
- **Top-1-peak-per-day is the CURRENT final simplification** — don't reintroduce multi-event TP/FP/FN matching or percentage-based rates unless explicitly asked.
- **Do not reintroduce interpolation-based resampling or +ve-dSocdt-clipping** anywhere in Approach 2 work.
- **14-day window / 728-feature configuration is FINAL** — the 7-day/date-removal experiment was tried and reverted.

## Mistakes to avoid
- Don't re-explain settled design decisions unless a new question is asked about them.
- Don't forget NaN-safety patterns for any new Approach 2 code (Section 17 snippets) — every omission caused a real crash previously.
- Don't assume percentage rate metrics are appropriate for asymmetric-category comparisons — prefer absolute counts.
- Don't assume "looser threshold = better" for top-1-selection logic — verify empirically.
- Don't silently reuse scale-dependent constants (like `ACC_THRESHOLD`) across different data distributions without recalibrating.

## Preferred coding style
- Flat, procedural scripts, one per pipeline stage, clear docstring at top.
- `os.path.join()` for all paths, never hardcoded slashes.
- `matplotlib.use("Agg")` always.
- Verbose, well-formatted console print statements throughout (`print(f"  Saved: {plot_path}")`) — valued, not noise.
- Config constants at the TOP of each script, clearly labeled sections.
- CSV outputs: clear, snake_case, self-describing column names.
- When only a few lines change: user often wants JUST those lines/diffs; when asked for "whole file," provide the complete runnable file.

## Preferred explanation style
- NEW/complex topics: thorough, structured, concrete numbers from real data, clear headers/tables.
- ROUTINE follow-ups: minimal/no preamble, just the requested artifact, maybe 1-3 sentences of what changed.
- When user says "just tell X" / "don't think too much" / "answer in short" — honor it literally.
- Distinguish clearly between confirmed empirical fact and reasoning-based hypothesis.

## User preferences observed
- Wants fast iteration, many short specific requests expecting quick direct responses.
- Runs code locally (Windows, VS Code, git branches main/test), reports back REAL console output — ground all reasoning in that, not hypotheticals.
- Sophisticated ML/stats understanding (coordinate-wise-tuning-order concern, percentage-denominator-mismatch insight, units clarification) — engage at technical peer level, don't over-simplify.
- Values reproducibility/traceability highly (checkpoints, best_<param>.json provenance, live-computed report stats) — maintain this rigor in new work.
- Cares about the project telling a coherent NARRATIVE for academic report purposes, not just raw performance — expect recurring documentation/report-writing requests.

---

*End of Handoff Document.*
