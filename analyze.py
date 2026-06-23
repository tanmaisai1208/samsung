import glob
import os

"""
Battery Management - Predictive Battery Management Through Usage Pattern Recognition
======================================================================================
Task 1: Resample raw data to hourly intervals using interpolation
Task 2: Autocorrelation and Hurst Exponent (R/S Analysis) on discharge-only dSoCdt series
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.gridspec import GridSpec
import warnings
warnings.filterwarnings("ignore")

RAW_FOLDER = os.path.expanduser(
    r"~/Downloads/raw/raw"
)

OUTPUT_FOLDER = "results"
CSV_FOLDER = os.path.join(OUTPUT_FOLDER, "resampled_csv")
PLOT_FOLDER = os.path.join(OUTPUT_FOLDER, "ac_hc_plots")

os.makedirs(CSV_FOLDER, exist_ok=True)
os.makedirs(PLOT_FOLDER, exist_ok=True)

MAX_LAG       = 504         
HURST_MIN_WIN = 24   # 24 hrs = 1 day     
HURST_MAX_WIN = 504  # 504 hrs = 3 weeks
HURST_N_WINS  = 30   # number of window sizes (log-spaced)

csv_files = glob.glob(os.path.join(RAW_FOLDER, "*.csv"))
print(f"Found {len(csv_files)} CSV files")

# ─────────────────────────────────────────────────────────────
# TASK 1 – HOURLY RESAMPLING
# ─────────────────────────────────────────────────────────────
print("=" * 65)
print("TASK 1: Hourly Resampling via Interpolation")
print("=" * 65)

summary_results = []

count=1
for INPUT_FILE in csv_files:
    try:
        base_name = os.path.splitext(os.path.basename(INPUT_FILE))[0]

        OUTPUT_CSV = os.path.join(
            CSV_FOLDER,
            f"{base_name}_hourly.csv"
            # f"hourly_{count}.csv"
        )

        PLOT_AUTOCORR = os.path.join(
            PLOT_FOLDER,
            f"autocorr_{count}.png"
        )

        PLOT_HURST = os.path.join(
            PLOT_FOLDER,
            f"hurst_{count}.png"
        )

        print("\n" + "="*70)
        print(f"Processing: {os.path.basename(INPUT_FILE)}")
        print("="*70)

        df = pd.read_csv(INPUT_FILE)

        print(f"  Raw rows loaded : {len(df)}")

        df["dt"] = pd.to_datetime(df["DateTime"], format="mixed", utc=True)
        df["dt"] = df["dt"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        df = df.sort_values("dt").reset_index(drop=True)

        df = df.set_index("dt")

        NUM_COLS = ["Soc", "DischargeLevel"]

        start_hour = df.index.min().floor("h")
        end_hour   = df.index.max().ceil("h")
        hourly_idx = pd.date_range(start=start_hour, end=end_hour, freq="h")
        print(f"  Hourly slots needed : {len(hourly_idx)}  "
            f"({start_hour}  →  {end_hour})")

        df_num = df[NUM_COLS].copy()

        combined_idx = df_num.index.union(hourly_idx)
        df_num = df_num.reindex(combined_idx)

        df_num = df_num.interpolate(method="time", limit_direction="both")

        df_hourly_num = df_num.reindex(hourly_idx)

        df_hourly = pd.DataFrame(index=hourly_idx)
        df_hourly.index.name = "dt"

        device_id = df["ID"].iloc[0]
        df_hourly["ID"]            = device_id
        df_hourly["TimeStamp"]     = (df_hourly.index.astype(np.int64) // 10**9).astype(int)
        df_hourly["Soc"]           = df_hourly_num["Soc"].round(4)
        df_hourly["DischargeLevel"]= df_hourly_num["DischargeLevel"].round(4)
        df_hourly["DateTime"]      = df_hourly.index.strftime("%Y-%m-%d %H:%M:%S")
        df_hourly["Date"]          = df_hourly.index.strftime("%Y-%m-%d")
        df_hourly["dayofweek"]     = df_hourly.index.dayofweek          # Mon=0
        df_hourly["dayname"]       = df_hourly.index.day_name()
        df_hourly["month"]         = df_hourly.index.month
        df_hourly["monthname"]     = df_hourly.index.month_name()

        df_hourly["dSocdt"] = df_hourly["Soc"].diff()
        df_hourly["dSocdt"] = df_hourly["dSocdt"].fillna(0)
        df_hourly["dSocdt"] = df_hourly["dSocdt"].round(6)

        df_hourly["ChargingStatus"] = (df_hourly["dSocdt"] > 0).astype(int)

        COL_ORDER = ["ID", "TimeStamp", "ChargingStatus", "Soc", "DischargeLevel",
                    "DateTime", "Date", "dayofweek", "dayname",
                    "month", "monthname", "dSocdt"]
        df_hourly = df_hourly[COL_ORDER].reset_index(drop=True)

        df_hourly.to_csv(OUTPUT_CSV, index=False)
        print(f"  Resampled rows saved : {len(df_hourly)}  →  {OUTPUT_CSV}")
        print(f"  SoC range after resample: {df_hourly['Soc'].min():.2f} – {df_hourly['Soc'].max():.2f}")

        # ─────────────────────────────────────────────────────────────
        # TASK 2 – AUTOCORRELATION & HURST EXPONENT (discharge only)
        # ─────────────────────────────────────────────────────────────
        print()
        print("=" * 65)
        print("TASK 2: Autocorrelation and Hurst Exponent (discharge dSoCdt only)")
        print("=" * 65)

        discharge_mask = df_hourly["dSocdt"] < 0
        dsocdt_discharge  = df_hourly.loc[discharge_mask, "dSocdt"].values.astype(float)
        print(f"  Total hourly rows   : {len(df_hourly)}")
        print(f"  Discharge-only rows : {len(dsocdt_discharge)}")

        if len(dsocdt_discharge) < MAX_LAG + 1:
            print(
                f"Skipping {base_name}: "
                f"only {len(dsocdt_discharge)} discharge samples"
            )
            continue

        def autocorr_at_lag(series: np.ndarray, lag: int) -> float:
            """Pearson autocorrelation at a given lag."""
            if lag == 0:
                return 1.0
            n    = len(series)
            x    = series[:n - lag] - series[:n - lag].mean()
            y    = series[lag:]      - series[lag:].mean()
            denom = np.std(series[:n - lag]) * np.std(series[lag:])
            if denom == 0:
                return np.nan
            return np.dot(x, y) / (len(x) * denom)

        lags      = np.arange(0, MAX_LAG + 1)
        autocorrs = np.array([autocorr_at_lag(dsocdt_discharge, lag) for lag in lags])

        conf_bound = 1.96 / np.sqrt(len(dsocdt_discharge))


        fig1, ax1 = plt.subplots(figsize=(14, 5))

        markerline, stemlines, baseline = ax1.stem(
            lags, autocorrs, linefmt="steelblue", markerfmt=" ", basefmt="k-"
        )
        stemlines.set_linewidth(0.6)

        ax1.axhline( conf_bound, color="red",   linestyle="--", linewidth=1.2,
                    label=f"95% confidence (±{conf_bound:.3f})")
        ax1.axhline(-conf_bound, color="red",   linestyle="--", linewidth=1.2)
        ax1.axhline(0,           color="black", linestyle="-",  linewidth=0.8)

        for week in range(1, MAX_LAG // 168 + 1):
            ax1.axvline(week * 168, color="green",  linestyle=":", linewidth=1.0,
                        alpha=0.7, label=f"Week {week}" if week == 1 else "")
        for day in range(24, MAX_LAG + 1, 24):
            ax1.axvline(day, color="orange", linestyle=":", linewidth=0.5, alpha=0.3)

        ax1.set_xlim(-5, MAX_LAG + 5)
        ax1.set_ylim(-1.05, 1.05)
        ax1.set_xlabel("Lag (hours)", fontsize=12)
        ax1.set_ylabel("Autocorrelation", fontsize=12)
        ax1.set_title("Autocorrelation of dSoCdt Time-Series\n"
                    "(Discharge-only samples | Lags 0–504 hrs = 3 weeks)",
                    fontsize=13, fontweight="bold")

        ax1.xaxis.set_minor_locator(ticker.MultipleLocator(24))
        ax1.xaxis.set_major_locator(ticker.MultipleLocator(72))

        ax2_twin = ax1.twiny()
        ax2_twin.set_xlim(ax1.get_xlim())
        week_ticks = np.arange(0, MAX_LAG + 1, 168)
        ax2_twin.set_xticks(week_ticks)
        ax2_twin.set_xticklabels([f"W{int(w/168)}" for w in week_ticks], fontsize=9)
        ax2_twin.set_xlabel("Weeks", fontsize=10)

        handles, labels = ax1.get_legend_handles_labels()

        seen = set(); uhandles, ulabels = [], []
        for h, l in zip(handles, labels):
            if l not in seen:
                seen.add(l); uhandles.append(h); ulabels.append(l)
        ax1.legend(uhandles, ulabels, fontsize=9, loc="upper right")

        ax1.grid(axis="y", linestyle="--", alpha=0.4)
        fig1.tight_layout()
        fig1.savefig(PLOT_AUTOCORR, dpi=150, bbox_inches="tight")
        plt.close(fig1)
        print(f"  Autocorrelation plot saved → {PLOT_AUTOCORR}")


        def rs_analysis(series: np.ndarray, window: int) -> float:
            """
            Compute mean R/S statistic for non-overlapping windows of given size.
            R/S = (max cumdev - min cumdev) / std_dev  for each window.
            Returns the mean R/S across all windows.
            """
            n        = len(series)
            n_windows= n // window
            if n_windows == 0:
                return np.nan
            rs_vals  = []
            for i in range(n_windows):
                chunk = series[i * window : (i + 1) * window]
                mean  = chunk.mean()
                devs  = np.cumsum(chunk - mean)        
                R     = devs.max() - devs.min()      
                S     = chunk.std(ddof=1)              
                if S == 0:
                    continue
                rs_vals.append(R / S)
            return np.mean(rs_vals) if rs_vals else np.nan


        window_sizes = np.unique(
            np.logspace(
                np.log10(HURST_MIN_WIN),
                np.log10(min(HURST_MAX_WIN, len(dsocdt_discharge) // 2)),
                num=HURST_N_WINS,
                dtype=int
            )
        )
        window_sizes = window_sizes[window_sizes >= 2]   # sanity: at least 2 pts/window

        rs_values = np.array([rs_analysis(dsocdt_discharge, w) for w in window_sizes])

        valid = ~np.isnan(rs_values)
        if valid.sum() < 2:
            print(f"Skipping {base_name}: insufficient valid R/S points")
            continue
        log_w  = np.log10(window_sizes[valid].astype(float))
        log_rs = np.log10(rs_values[valid])

        coeffs  = np.polyfit(log_w, log_rs, 1)
        H       = coeffs[0]                     
        fit_line= np.poly1d(coeffs)

        print(f"\n  Window sizes tested  : {window_sizes[valid].tolist()}")
        print(f"  Corresponding R/S    : {np.round(rs_values[valid], 3).tolist()}")
        print(f"\n  ► Hurst Exponent H  = {H:.4f}")
        if H > 0.55:
            regime = "Persistent (long-range dependence detected — H > 0.5)"
        elif H < 0.45:
            regime = "Anti-persistent (mean-reverting series — H < 0.5)"
        else:
            regime = "Random walk / no long-range dependence (H ≈ 0.5)"
        print(f"  ► Interpretation    : {regime}")

        summary_results.append({
            "User": base_name,
            "HourlyRows": len(df_hourly),
            "DischargeRows": len(dsocdt_discharge),
            "HurstExponent": round(H, 4),
            "Regime": regime
        })

        fig2, ax3 = plt.subplots(figsize=(9, 6))

        ax3.scatter(log_w, log_rs, color="steelblue", s=60, zorder=5,
                    label="R/S values (log-log)")
        ax3.plot(log_w, fit_line(log_w), color="crimson", linewidth=2,
                label=f"Fitted line  (slope = H = {H:.4f})")

        x_range = np.linspace(log_w.min(), log_w.max(), 100)
        ref_mid = fit_line(log_w.min()) + 0.5 * (x_range - log_w.min())
        ax3.plot(x_range, ref_mid, color="gray", linestyle="--", linewidth=1,
                alpha=0.6, label="Reference H=0.5 (random walk)")

        ax3.set_xlabel("log₁₀(Window size in hours)", fontsize=12)
        ax3.set_ylabel("log₁₀(R/S)", fontsize=12)
        ax3.set_title(
            f"Hurst Exponent via R/S Analysis\n"
            f"(Discharge-only dSoCdt | H = {H:.4f} — {regime.split('(')[0].strip()})",
            fontsize=13, fontweight="bold"
        )
        ax3.legend(fontsize=10)
        ax3.grid(True, linestyle="--", alpha=0.5)

        for w, rs in zip(window_sizes[valid][[0, len(window_sizes[valid])//2, -1]],
                        rs_values[valid][[0, len(window_sizes[valid])//2, -1]]):
            ax3.annotate(f"n={w}\nR/S={rs:.2f}",
                        xy=(np.log10(w), np.log10(rs)),
                        xytext=(8, 6), textcoords="offset points",
                        fontsize=7.5, color="navy",
                        arrowprops=dict(arrowstyle="-", color="gray", lw=0.8))

        fig2.tight_layout()
        fig2.savefig(PLOT_HURST, dpi=150, bbox_inches="tight")
        plt.close(fig2)
        print(f"  Hurst exponent plot  saved → {PLOT_HURST}")

        print()
        print("=" * 65)
        print("SUMMARY")
        print("=" * 65)
        print(f"  Resampled CSV         : {OUTPUT_CSV}")
        print(f"  Autocorrelation plot  : {PLOT_AUTOCORR}")
        print(f"  Hurst exponent plot   : {PLOT_HURST}")
        print(f"  H = {H:.4f}  →  {regime}")
        print("=" * 65)

        count=count+1
    except Exception as e:
        print(f"Error processing {INPUT_FILE}: {e}")
        continue

summary_df = pd.DataFrame(summary_results)

summary_df.to_csv(
    os.path.join(OUTPUT_FOLDER, "all_users_summary.csv"),
    index=False
)

print("\nSummary saved to all_users_summary.csv")