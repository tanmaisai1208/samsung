"""
battery_resample_and_pivot.py
==============================
Two-step pipeline operating on the original raw CSV files.

STEP 1 — Average-based hourly resampling  (NO interpolation)
─────────────────────────────────────────────────────────────
For each target hour H (0 – 23) on each calendar date:
  • Collect all raw rows whose timestamp falls in [H:00 - 30min, H:00 + 30min)
    i.e. the 1-hour window centred on H:00
  • Average ChargingStatus, Soc, DischargeLevel, dSocdt across those rows
  • If NO raw rows fall in that window → fill the entire hour-row with NaN
    (XGBoost handles NaN natively — better than forcing interpolation)
  • Derive dayofweek, dayname, month, monthname from the timestamp

Output: results/resampled_csv/<device>_hourly.csv
        One row per (date, hour) — 24 rows per day maximum.
        Rows with no data contribution are NaN.

STEP 2 — Pivot to wide daily format  (NO clipping of +ve dSocdt)
─────────────────────────────────────────────────────────────────
Rows    = calendar dates
Columns = dSocdt_h0…h23  |  Soc_h0…h23      (48 columns)
          +ve dSocdt (charging hours) kept as-is.
          Missing hours → NaN in the wide CSV (XGBoost handles internally).

Output: results/wide_csv/<device>_wide.csv

Run from SOC-folder:
    python battery_resample_and_pivot.py
"""

import os
import glob
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────
# PATHS  ← adjust RAW_FOLDER to point at your raw CSVs
# ─────────────────────────────────────────────────────────────
RAW_FOLDER       = "raw"                       # folder containing original raw CSVs
RESAMPLED_FOLDER = "results/resampled_csv"
WIDE_FOLDER      = "results/wide_csv"

os.makedirs(RESAMPLED_FOLDER, exist_ok=True)
os.makedirs(WIDE_FOLDER,      exist_ok=True)

HOURS = list(range(24))

# Columns to average when aggregating rows into one hourly slot
AVG_COLS = ["ChargingStatus", "Soc", "DischargeLevel", "dSocdt"]

# Wide CSV column lists
DSOCDT_COLS = [f"dSocdt_h{h}" for h in HOURS]
SOC_COLS    = [f"Soc_h{h}"    for h in HOURS]


# ═════════════════════════════════════════════════════════════
# STEP 1 — AVERAGE-BASED HOURLY RESAMPLING
# ═════════════════════════════════════════════════════════════

def resample_to_hourly(raw_csv_path: str, out_csv_path: str) -> pd.DataFrame:
    """
    Read one raw device CSV and produce an hourly-averaged DataFrame.

    Algorithm:
      1. Parse DateTime (timezone-aware → convert to IST → strip tz)
      2. For every calendar date in the data range AND every hour 0–23:
           window = [H:00 - 30 min,  H:00 + 30 min)
           average all AVG_COLS rows whose timestamp falls in window
           if no rows → NaN row
      3. Derive categorical columns from the timestamp
      4. Save to out_csv_path
    """
    df = pd.read_csv(raw_csv_path)

    # ── Parse and localise DateTime ──────────────────────────
    df["dt"] = pd.to_datetime(df["DateTime"], format="mixed", utc=True)
    df["dt"] = df["dt"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.sort_values("dt").reset_index(drop=True)

    # ── Date range: one calendar date at a time ──────────────
    start_date = df["dt"].dt.date.min()
    end_date   = df["dt"].dt.date.max()
    all_dates  = pd.date_range(start=str(start_date),
                                end=str(end_date),   freq="D")

    records = []
    for day in all_dates:
        day_str = day.strftime("%Y-%m-%d")

        for h in HOURS:
            # Window centred on H:00 of this day
            centre   = day + pd.Timedelta(hours=h)
            win_lo   = centre - pd.Timedelta(minutes=30)   # inclusive
            win_hi   = centre + pd.Timedelta(minutes=30)   # exclusive

            mask = (df["dt"] >= win_lo) & (df["dt"] < win_hi)
            bucket = df.loc[mask, AVG_COLS]

            if bucket.empty:
                # No data in this window → NaN row (let XGBoost handle it)
                row = {
                    "DateTime"      : centre.strftime("%Y-%m-%d %H:%M:%S"),
                    "Date"          : day_str,
                    "hour"          : h,
                    "dayofweek"     : centre.dayofweek,
                    "dayname"       : centre.day_name(),
                    "month"         : centre.month,
                    "monthname"     : centre.month_name(),
                    "ChargingStatus": np.nan,
                    "Soc"           : np.nan,
                    "DischargeLevel": np.nan,
                    "dSocdt"        : np.nan,
                }
            else:
                avgs = bucket.mean()
                row = {
                    "DateTime"      : centre.strftime("%Y-%m-%d %H:%M:%S"),
                    "Date"          : day_str,
                    "hour"          : h,
                    "dayofweek"     : centre.dayofweek,
                    "dayname"       : centre.day_name(),
                    "month"         : centre.month,
                    "monthname"     : centre.month_name(),
                    "ChargingStatus": avgs["ChargingStatus"],
                    "Soc"           : avgs["Soc"],
                    "DischargeLevel": avgs["DischargeLevel"],
                    "dSocdt"        : avgs["dSocdt"],
                }
            records.append(row)

    hourly = pd.DataFrame(records)

    # Summary stats
    total_slots = len(hourly)
    nan_slots   = hourly["Soc"].isna().sum()
    filled_slots= total_slots - nan_slots

    print(f"    Hourly slots : {total_slots}  |  "
          f"Filled: {filled_slots}  |  NaN (no raw data): {nan_slots}  "
          f"({100 * nan_slots / total_slots:.1f}%)")

    hourly.to_csv(out_csv_path, index=False)
    return hourly


# ═════════════════════════════════════════════════════════════
# STEP 2 — PIVOT TO WIDE DAILY FORMAT
# ═════════════════════════════════════════════════════════════

def pivot_to_wide(hourly_csv_path: str, wide_csv_path: str) -> None:
    """
    Convert hourly CSV to wide daily format.

    Columns: dSocdt_h0…h23 | Soc_h0…h23  (48 columns)
    +ve dSocdt kept as-is.  Missing hours → NaN (not filled).
    """
    df = pd.read_csv(hourly_csv_path)

    # Ensure hour column exists
    if "hour" not in df.columns:
        df["DateTime"] = pd.to_datetime(df["DateTime"])
        df["hour"]     = df["DateTime"].dt.hour
    if "Date" not in df.columns:
        df["DateTime"] = pd.to_datetime(df["DateTime"])
        df["Date"]     = df["DateTime"].dt.date.astype(str)

    rows = []
    for date, grp in df.groupby("Date", sort=True):
        grp = grp.set_index("hour")
        row = {"Date": date}

        for h in HOURS:
            if h in grp.index:
                row[f"dSocdt_h{h}"] = grp.loc[h, "dSocdt"]
                row[f"Soc_h{h}"]    = grp.loc[h, "Soc"]
            else:
                # Hour slot not present at all → NaN
                row[f"dSocdt_h{h}"] = np.nan
                row[f"Soc_h{h}"]    = np.nan

        rows.append(row)

    wide = pd.DataFrame(rows).set_index("Date")
    # Column order: all dSocdt first, then all Soc
    wide = wide[DSOCDT_COLS + SOC_COLS]
    wide.to_csv(wide_csv_path)

    # Sanity printout
    pos_count  = (wide[DSOCDT_COLS] > 0).values.sum()
    neg_count  = (wide[DSOCDT_COLS] < 0).values.sum()
    zero_count = (wide[DSOCDT_COLS] == 0).values.sum()
    nan_count  = wide[DSOCDT_COLS].isna().values.sum()
    print(f"    Wide shape   : {wide.shape}  |  "
          f"dSocdt — pos(charging): {pos_count}  "
          f"neg(discharge): {neg_count}  "
          f"zero: {zero_count}  NaN: {nan_count}")


# ═════════════════════════════════════════════════════════════
# MAIN LOOP
# ═════════════════════════════════════════════════════════════

raw_files = sorted(glob.glob(os.path.join(RAW_FOLDER, "*.csv")))
print(f"Found {len(raw_files)} raw CSV file(s) in '{RAW_FOLDER}'\n")

if not raw_files:
    raise FileNotFoundError(
        f"No CSV files found in '{RAW_FOLDER}'. "
        "Update RAW_FOLDER at the top of this script."
    )

for raw_path in raw_files:
    base_name   = os.path.splitext(os.path.basename(raw_path))[0]
    hourly_path = os.path.join(RESAMPLED_FOLDER, f"{base_name}_hourly.csv")
    wide_path   = os.path.join(WIDE_FOLDER,      f"{base_name}_wide.csv")

    print("=" * 65)
    print(f"Device : {base_name}")
    print("=" * 65)

    try:
        # ── Step 1: average-based hourly resampling ──────────
        print("  Step 1 — Averaging into hourly slots ...")
        resample_to_hourly(raw_path, hourly_path)
        print(f"    Saved → {hourly_path}")

        # ── Step 2: pivot to wide format ─────────────────────
        print("  Step 2 — Pivoting to wide daily format ...")
        pivot_to_wide(hourly_path, wide_path)
        print(f"    Saved → {wide_path}")

    except Exception as e:
        import traceback
        print(f"  ERROR: {e}")
        traceback.print_exc()

    print()

print("=" * 65)
print("Done. Check results/resampled_csv/ and results/wide_csv/")
print("=" * 65)
