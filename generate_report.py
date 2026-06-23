"""
generate_report.py
==================
Run this script from inside your SOC-folder to generate a PDF progress report.

    cd path/to/SOC-folder
    python generate_report.py

It reads plots from your existing results/ folder structure and compiles
everything into:  results/project_report.pdf

Requirements:  pip install reportlab
"""

import os
import glob
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable, Image, KeepTogether
)
from reportlab.platypus.flowables import Flowable

# ─────────────────────────────────────────────────────────────
# PATHS  — adjust ROOT if you run from a different directory
# ─────────────────────────────────────────────────────────────
ROOT        = "."                          # run from inside SOC-folder
RESULTS     = os.path.join(ROOT, "results")
OUTPUT_PDF  = os.path.join(RESULTS, "project_report.pdf")

PATHS = {
    "ac_hc_plots"       : os.path.join(RESULTS, "ac_hc_plots"),
    "wide_csv"          : os.path.join(RESULTS, "wide_csv"),
    "resampled_csv"     : os.path.join(RESULTS, "resampled_csv"),
    "feature_importance": os.path.join(RESULTS, "xgboost", "feature_importance"),
    "final_validation"  : os.path.join(RESULTS, "xgboost", "final_validation"),
    "hypersearch"       : os.path.join(RESULTS, "xgboost", "hypersearch"),
    "val_curves"        : os.path.join(RESULTS, "xgboost", "hypersearch", "validation_curves"),
}

PAGE_W, PAGE_H = A4
MARGIN = 2.2 * cm


# ─────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────
base_styles = getSampleStyleSheet()

def make_styles():
    s = {}
    s["title"] = ParagraphStyle(
        "ReportTitle", parent=base_styles["Title"],
        fontSize=22, textColor=colors.HexColor("#1a2e4a"),
        spaceAfter=6, alignment=TA_CENTER, fontName="Helvetica-Bold"
    )
    s["subtitle"] = ParagraphStyle(
        "Subtitle", parent=base_styles["Normal"],
        fontSize=12, textColor=colors.HexColor("#4a6fa5"),
        spaceAfter=4, alignment=TA_CENTER, fontName="Helvetica"
    )
    s["h1"] = ParagraphStyle(
        "H1", parent=base_styles["Heading1"],
        fontSize=15, textColor=colors.HexColor("#1a2e4a"),
        spaceBefore=18, spaceAfter=6,
        borderPad=4, fontName="Helvetica-Bold",
        borderWidth=0, leading=18
    )
    s["h2"] = ParagraphStyle(
        "H2", parent=base_styles["Heading2"],
        fontSize=12, textColor=colors.HexColor("#2c5282"),
        spaceBefore=12, spaceAfter=4, fontName="Helvetica-Bold"
    )
    s["h3"] = ParagraphStyle(
        "H3", parent=base_styles["Heading3"],
        fontSize=10.5, textColor=colors.HexColor("#2d3748"),
        spaceBefore=8, spaceAfter=3, fontName="Helvetica-BoldOblique"
    )
    s["body"] = ParagraphStyle(
        "Body", parent=base_styles["Normal"],
        fontSize=10, leading=15, spaceAfter=6,
        alignment=TA_JUSTIFY, fontName="Helvetica"
    )
    s["bullet"] = ParagraphStyle(
        "Bullet", parent=base_styles["Normal"],
        fontSize=10, leading=14, spaceAfter=3,
        leftIndent=16, firstLineIndent=-10,
        fontName="Helvetica"
    )
    s["code"] = ParagraphStyle(
        "Code", parent=base_styles["Code"],
        fontSize=8.5, leading=12, spaceAfter=4,
        backColor=colors.HexColor("#f7fafc"),
        borderColor=colors.HexColor("#cbd5e0"),
        borderWidth=0.5, borderPad=6,
        fontName="Courier"
    )
    s["caption"] = ParagraphStyle(
        "Caption", parent=base_styles["Normal"],
        fontSize=8.5, textColor=colors.HexColor("#718096"),
        alignment=TA_CENTER, spaceAfter=8, fontName="Helvetica-Oblique"
    )
    s["toc"] = ParagraphStyle(
        "TOC", parent=base_styles["Normal"],
        fontSize=10.5, leading=18, fontName="Helvetica",
        textColor=colors.HexColor("#2d3748")
    )
    return s

S = make_styles()


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def hr(color="#cbd5e0", thickness=0.5):
    return HRFlowable(width="100%", thickness=thickness,
                      color=colors.HexColor(color), spaceAfter=6, spaceBefore=2)


def section_header(text, level="h1"):
    return [hr("#2c5282" if level == "h1" else "#a0aec0",
               thickness=1.5 if level == "h1" else 0.5),
            Paragraph(text, S[level]),
            Spacer(1, 0.2 * cm)]


def body(text):
    return Paragraph(text, S["body"])


def bullet(text, symbol="•"):
    return Paragraph(f"{symbol}  {text}", S["bullet"])


def caption(text):
    return Paragraph(text, S["caption"])


def sp(h=0.3):
    return Spacer(1, h * cm)


def insert_image(path, width_cm=14, caption_text=None, max_height_cm=10):
    """Insert image if file exists, otherwise insert a placeholder note."""
    elems = []
    if path and os.path.exists(path):
        img_w = width_cm * cm
        img_h = min(max_height_cm * cm, img_w * 0.6)
        try:
            elems.append(Image(path, width=img_w, height=img_h,
                               kind="proportional"))
        except Exception:
            elems.append(body(f"[Image could not be loaded: {os.path.basename(path)}]"))
    else:
        name = os.path.basename(path) if path else "image"
        elems.append(Paragraph(
            f'<font color="#a0aec0"><i>[Plot not found: {name} — '
            f'run the corresponding script to generate it]</i></font>',
            S["body"]
        ))
    if caption_text:
        elems.append(caption(caption_text))
    elems.append(sp(0.3))
    return elems


def glob_first(pattern):
    """Return first file matching glob pattern, or None."""
    matches = sorted(glob.glob(pattern))
    return matches[0] if matches else None


def glob_all(pattern):
    return sorted(glob.glob(pattern))


def kv_table(rows, col_widths=None):
    """Two-column key-value table."""
    if col_widths is None:
        col_widths = [5 * cm, 10 * cm]
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#edf2f7")),
        ("TEXTCOLOR",  (0, 0), (0, -1), colors.HexColor("#2d3748")),
        ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",   (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9.5),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1),
         [colors.white, colors.HexColor("#f7fafc")]),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e0")),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    return t


def results_table(header, rows):
    """General styled table with header row."""
    data = [header] + rows
    col_w = (PAGE_W - 2 * MARGIN) / len(header)
    t = Table(data, colWidths=[col_w] * len(header))
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#2c5282")),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#ebf4ff")]),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#bee3f8")),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


# ─────────────────────────────────────────────────────────────
# COVER PAGE
# ─────────────────────────────────────────────────────────────

def cover_page():
    elems = []
    elems.append(sp(3))
    elems.append(Paragraph(
        "Predictive Battery Management", S["title"]))
    elems.append(Paragraph(
        "Through Usage Pattern Recognition", S["title"]))
    elems.append(sp(0.5))
    elems.append(hr("#4a6fa5", thickness=2))
    elems.append(sp(0.4))
    elems.append(Paragraph("Project Progress Report", S["subtitle"]))
    elems.append(sp(3))

    meta = [
        ["Project"  , "Predictive Battery Management Through Usage Pattern Recognition"],
        ["Model"    , "XGBoost (Daily Rolling-Window, Sequential Hyperparameter Tuning)"],
        ["Status"   , "In Progress"],
        ["Scope"    , "Data Preprocessing  |  Statistical Analysis  |  Model Training & Evaluation"],
    ]
    elems.append(kv_table(meta, col_widths=[3.5 * cm, 11.5 * cm]))
    elems.append(sp(1))
    elems.append(Paragraph(
        "This document summarises all work completed so far on the battery "
        "management project. It covers raw data preprocessing, hourly resampling, "
        "long-range dependence analysis (autocorrelation and Hurst exponent), "
        "XGBoost model training using a daily rolling window, hyperparameter tuning "
        "via sequential coordinate-wise search, and final validation results. "
        "The report will continue to be updated as further work is completed.",
        S["body"]
    ))
    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────────────────────────
# TABLE OF CONTENTS
# ─────────────────────────────────────────────────────────────

def toc():
    elems = []
    elems += section_header("Table of Contents", "h1")
    sections = [
        ("1", "Project Overview & Problem Statement"),
        ("2", "Dataset Description & File Structure"),
        ("3", "Step 1 — Data Preprocessing & Hourly Resampling"),
        ("4", "Step 2 — Statistical Analysis  (Autocorrelation & Hurst Exponent)"),
        ("5", "Step 3 — Data Format Transformation  (Wide Daily Format)"),
        ("6", "Step 4 — XGBoost Model  (Daily Rolling-Window Training)"),
        ("6.1", "  Feature Engineering"),
        ("6.2", "  Training Strategy"),
        ("6.3", "  Accuracy Metric"),
        ("7", "Step 5 — Hyperparameter Tuning  (Sequential Coordinate Search)"),
        ("7.1", "  n_estimators"),
        ("7.2", "  max_depth"),
        ("7.3", "  learning_rate"),
        ("7.4", "  subsample"),
        ("8", "Step 6 — Final Combined Validation"),
        ("9", "Step 7 — Feature Importance Analysis"),
        ("10", "Next Steps"),
    ]
    for num, title in sections:
        dot_leader = "." * max(1, 60 - len(num) - len(title))
        elems.append(Paragraph(
            f'<font name="Helvetica-Bold">{num}</font>  {title}',
            S["toc"]
        ))
    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────────────────────────
# SECTION 1 — PROJECT OVERVIEW
# ─────────────────────────────────────────────────────────────

def section_overview():
    elems = []
    elems += section_header("1.  Project Overview & Problem Statement", "h1")
    elems.append(body(
        "The goal of this project is to predict future battery usage patterns "
        "of mobile devices by learning from historical State-of-Charge (SoC) "
        "time-series data. Accurate prediction of discharge behaviour enables "
        "intelligent suggestions to users — such as optimal charging times, "
        "expected battery life, and anomaly detection for degraded cells."
    ))
    elems.append(sp(0.5))
    return elems


# ─────────────────────────────────────────────────────────────
# SECTION 2 — DATASET & FILE STRUCTURE
# ─────────────────────────────────────────────────────────────

def section_dataset():
    elems = []
    elems += section_header("2.  Dataset Description & File Structure", "h1")
    elems.append(body(
        "Multiple CSV files are provided, each corresponding to one device/user. "
        "Each file contains raw time-stamped SoC readings collected at irregular "
        "intervals (median gap ~15 minutes, max gap up to 18 days in some files). "
        "The data spans approximately 70 days per device."
    ))
    elems += section_header("Raw Data Columns", "h2")
    col_rows = [
        ["ID",             "Device identifier (ignored in modelling)"],
        ["TimeStamp",      "Unix timestamp (ignored in modelling)"],
        ["ChargingStatus", "0 = discharging, 1 = charging"],
        ["Soc",            "State of Charge — current battery percentage (0–100)"],
        ["DischargeLevel", "Raw discharge counter (used in resampling only)"],
        ["DateTime",       "Human-readable timestamp (yyyy-mm-dd HH:MM:SS)"],
        ["dSocdt",         "Rate of change of SoC from previous sample (+ve = charging, -ve = discharging, 0 = idle)"],
    ]
    elems.append(kv_table(col_rows, col_widths=[3.8 * cm, 11.2 * cm]))
    elems.append(sp(0.4))

    elems += section_header("Project File Structure", "h2")
    elems.append(Paragraph(
        '<font name="Courier" size="8.5">'
        'SOC-folder/<br/>'
        '&nbsp;&nbsp;results/<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;ac_hc_plots/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;← Autocorrelation &amp; Hurst exponent plots<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;resampled_csv/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;← Hourly-resampled CSVs (one per device)<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;wide_csv/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;← Pivoted daily-wide CSVs<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;xgboost/<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;feature_importance/&nbsp;&nbsp;← Feature importance plots<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;final_validation/&nbsp;&nbsp;&nbsp;&nbsp;← Final predictions &amp; accuracy plots<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;hypersearch/<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;validation_curves/&nbsp;&nbsp;&nbsp;← Val curve plots per hyperparameter<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;best_*.json&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;← Best value per hyperparameter<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;checkpoint_*.json&nbsp;&nbsp;&nbsp;&nbsp;← Resume checkpoints<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;results_*.csv&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;← Raw tuning results<br/>'
        '&nbsp;&nbsp;battery_analysis.py&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;← Resampling + AC/HC analysis<br/>'
        '&nbsp;&nbsp;battery_xgboost.py&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;← XGBoost daily rolling window<br/>'
        '&nbsp;&nbsp;battery_hypersearch.py&nbsp;&nbsp;&nbsp;&nbsp;← Sequential hyperparameter tuning<br/>'
        '&nbsp;&nbsp;battery_final_validation.py← Final combined validation<br/>'
        '&nbsp;&nbsp;battery_feature_import.py&nbsp;&nbsp;← Feature importance analysis<br/>'
        '&nbsp;&nbsp;generate_report.py&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;← This script<br/>'
        '</font>', S["body"]
    ))
    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────────────────────────
# SECTION 3 — PREPROCESSING
# ─────────────────────────────────────────────────────────────

def section_preprocessing():
    elems = []
    elems += section_header("3.  Step 1 — Data Preprocessing & Hourly Resampling", "h1")
    elems.append(body(
        "The raw CSV files contain samples at irregular intervals. The project "
        "requires uniformly-spaced hourly data for consistent model training. "
        "The following preprocessing pipeline is applied to every raw CSV file "
        "via <b>battery_analysis.py</b>:"
    ))
    steps = [
        "Parse DateTime column with mixed-format UTC timestamps; convert to IST (Asia/Kolkata) and strip timezone.",
        "Sort by timestamp and set as index.",
        "Create a clean hourly DatetimeIndex spanning start to end of data.",
        "Apply time-based linear interpolation on Soc and DischargeLevel columns to fill gaps.",
        "Re-derive dSocdt as the hourly difference of interpolated Soc.",
        "Re-derive all categorical columns (dayofweek, dayname, month, monthname) from the timestamp.",
        "Re-derive ChargingStatus from sign of interpolated dSocdt (+ve → 1, else → 0).",
        "Save resampled output to results/resampled_csv/<device>_hourly.csv.",
    ]
    for s in steps:
        elems.append(bullet(s))
    elems.append(sp(0.3))

    elems.append(kv_table([
        ["Input"      , "Raw CSVs with irregular timestamps (median gap ~15 min)"],
        ["Output"     , "Hourly CSVs — one row per hour, every hour, start to end"],
        ["Method"     , "pandas interpolate(method='time') — time-weighted linear"],
        ["Columns interpolated", "Soc, DischargeLevel, dSocdt"],
        ["Columns re-derived"  , "ChargingStatus, dayofweek, dayname, month, monthname"],
    ], col_widths=[4.5 * cm, 10.5 * cm]))
    elems.append(sp(0.5))

    elems += section_header("Charging vs Discharging", "h2")
    elems.append(body(
        "A core principle of this project is to model only device <i>usage</i> "
        "patterns, not charging behaviour. Therefore, all samples where "
        "<b>dSocdt &gt; 0</b> (charging) are excluded from statistical analysis "
        "and their dSocdt values are zeroed out before model training. "
        "Samples where dSocdt = 0 are also treated as neutral and ignored."
    ))
    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────────────────────────
# SECTION 4 — AC & HURST
# ─────────────────────────────────────────────────────────────

def section_statistical():
    elems = []
    elems += section_header(
        "4.  Step 2 — Statistical Analysis (Autocorrelation & Hurst Exponent)", "h1")
    elems.append(body(
        "Before training any predictive model, a key research question was "
        "investigated: <i>does the discharge behaviour of a user exhibit "
        "long-range temporal dependence?</i> If past patterns genuinely "
        "influence future patterns over weeks, then sequence-aware models "
        "should outperform pattern-clustering approaches like SOM."
    ))

    elems += section_header("4.1  Autocorrelation Analysis", "h2")
    elems.append(body(
        "Pearson autocorrelation of the dSocdt discharge series was computed "
        "at lags 0 to 504 hours (3 weeks) for each device. Only discharge "
        "samples (dSocdt &lt; 0) were used. The 95% confidence bounds "
        "(Bartlett approximation: ±1.96/√n) are overlaid. Vertical markers "
        "indicate daily (24h) and weekly (168h) periods."
    ))

    # Insert first AC plot found
    ac_plots = glob_all(os.path.join(PATHS["ac_hc_plots"], "*autocorr*.png"))
    if ac_plots:
        elems += insert_image(ac_plots[0], width_cm=15,
                              caption_text="Figure 1: Autocorrelation of dSocdt (discharge only) — lags 0 to 504 hours")
    else:
        elems += insert_image(None, caption_text="Figure 1: Autocorrelation plot (run battery_analysis.py to generate)")

    elems += section_header("4.2  Hurst Exponent (R/S Analysis)", "h2")
    elems.append(body(
        "The Hurst exponent H is estimated via Rescaled Range (R/S) analysis "
        "over log-spaced window sizes from 24 to 504 hours. H is the slope of "
        "the fitted line on the log(R/S) vs log(n) plot:"
    ))
    elems.append(bullet("H &gt; 0.5 → Persistent (long-range dependence) — past behaviour predicts future"))
    elems.append(bullet("H ≈ 0.5 → Random walk — no exploitable pattern"))
    elems.append(bullet("H &lt; 0.5 → Anti-persistent — mean-reverting series"))
    elems.append(sp(0.2))

    hc_plots = glob_all(os.path.join(PATHS["ac_hc_plots"], "*hurst*.png"))
    if hc_plots:
        elems += insert_image(hc_plots[0], width_cm=13,
                              caption_text="Figure 2: Hurst exponent R/S analysis — slope = H")
    else:
        elems += insert_image(None, caption_text="Figure 2: Hurst exponent plot")

    elems += section_header("4.3  Results Across All Devices", "h2")
    elems.append(body(
        "After running battery_analysis.py on all device files, the following "
        "distribution of Hurst exponents was observed:"
    ))
    h_rows = [
        ["H &gt; 0.7 (Strong persistence)",   "Majority of devices", "Strong long-range dependence — highly predictable patterns"],
        ["H = 0.5–0.6 (Mild persistence)",     "Few devices",         "Some structure but weaker signal"],
        ["H = 0.4–0.5 (Near random / anti)",   "Rare",                "Limited predictability for these users"],
    ]
    elems.append(results_table(
        ["Hurst Range", "Frequency", "Interpretation"], h_rows))
    elems.append(sp(0.3))
    elems.append(body(
        "<b>Conclusion:</b> The majority of devices show strong long-range "
        "dependence (H &gt; 0.7), confirming that sequence-aware models such as "
        "XGBoost with temporal feature engineering should outperform SOM-based "
        "clustering. This finding directly motivates the model choice."
    ))
    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────────────────────────
# SECTION 5 — WIDE FORMAT
# ─────────────────────────────────────────────────────────────

def section_wide_format():
    elems = []
    elems += section_header(
        "5.  Step 3 — Data Format Transformation (Wide Daily Format)", "h1")
    elems.append(body(
        "XGBoost requires a tabular feature matrix. To convert the hourly "
        "time-series into a form suitable for daily prediction, the resampled "
        "CSVs are pivoted into a <b>wide daily format</b> via <b>battery_xgboost.py</b>:"
    ))
    elems.append(kv_table([
        ["Rows"   , "One row per calendar date"],
        ["Columns", "dSocdt_h0 … dSocdt_h23  |  Soc_h0 … Soc_h23  (48 columns)"],
        ["dSocdt" , "+ve values clipped to 0 (charging effect removed)"],
        ["Soc"    , "Forward/backward filled within each day for any missing hours"],
        ["Saved to", "results/wide_csv/<device>_wide.csv"],
    ], col_widths=[3.5 * cm, 11.5 * cm]))
    elems.append(sp(0.3))
    elems.append(body(
        "This wide format means each row represents a full day's 24-hour "
        "discharge profile, which becomes both the training target and "
        "part of the feature context for adjacent rows."
    ))
    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────────────────────────
# SECTION 6 — XGBOOST MODEL
# ─────────────────────────────────────────────────────────────

def section_model():
    elems = []
    elems += section_header(
        "6.  Step 4 — XGBoost Model (Daily Rolling-Window Training)", "h1")
    elems.append(body(
        "The core prediction model uses XGBoost with a MultiOutputRegressor "
        "wrapper (one tree per output hour) trained in a daily rolling-window "
        "fashion. The prediction target is the 24-hour dSocdt profile of the "
        "next day."
    ))

    elems += section_header("6.1  Feature Engineering", "h2")
    elems.append(body(
        "For each prediction day, the full 14-day training window is flattened "
        "into a single feature vector. Per training day, the following features "
        "are included:"
    ))
    elems.append(bullet("24 dSocdt values  (hourly discharge rates, charging zeroed out)"))
    elems.append(bullet("24 Soc values  (hourly state of charge)"))
    elems.append(bullet("Day of week  (Monday=0 … Sunday=6)"))
    elems.append(bullet("Day of month  (1–31)"))
    elems.append(bullet("Month  (1–12)"))
    elems.append(bullet("Year  (e.g. 2024)"))
    elems.append(sp(0.2))
    elems.append(kv_table([
        ["Features per day"   , "24 + 24 + 4 = 52"],
        ["Training window"    , "14 days"],
        ["Total feature vector", "14 × 52 = 728 features"],
        ["Output"             , "24 dSocdt values for the next day (h0 … h23)"],
    ], col_widths=[4 * cm, 11 * cm]))

    elems += section_header("6.2  Training Strategy", "h2")
    elems.append(body(
        "Because each prediction iteration has only 13 labelled training samples "
        "(expanding sub-windows within the 14-day block), a zero-padded expanding "
        "context strategy is used:"
    ))
    elems.append(bullet(
        "Sample k: use days [train_start … train_start+k-1] as context, "
        "padded with zeros at front, to predict day train_start+k (k = 1 … 13)"))
    elems.append(bullet(
        "This generates 13 training samples per prediction — sufficient for XGBoost "
        "without data leakage from the unseen test day."))
    elems.append(bullet(
        "The actual prediction uses the full real 14-day window as context → "
        "predicts the immediately next unseen day."))
    elems.append(bullet(
        "Predictions are clipped to ≤ 0 (discharge can never be positive)."))
    elems.append(bullet(
        "Always uses ACTUAL past values — no predicted values fed back."))

    elems += section_header("6.3  Accuracy Metric", "h2")
    elems.append(body(
        "A prediction for a given hour is counted as <b>correct</b> if "
        "|predicted dSocdt − actual dSocdt| ≤ threshold (set to 2.0 in this project). "
        "Accuracy for a day = percentage of 24 hours that are correct. "
        "Device accuracy = mean of all daily accuracies. "
        "Overall accuracy = mean across all devices."
    ))
    elems.append(body(
        "MAE and RMSE are also recorded per day and per device as secondary metrics."
    ))
    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────────────────────────
# SECTION 7 — HYPERPARAMETER TUNING
# ─────────────────────────────────────────────────────────────

def section_hyperparam():
    elems = []
    elems += section_header(
        "7.  Step 5 — Hyperparameter Tuning (Sequential Coordinate Search)", "h1")
    elems.append(body(
        "Full grid search over all hyperparameter combinations was infeasible "
        "(each combination takes ~40 minutes across all devices). Instead, a "
        "<b>sequential coordinate-wise search</b> was used: tune one parameter "
        "at a time while fixing all others, then carry forward the best value "
        "found to the next parameter. This is implemented in "
        "<b>battery_hypersearch.py</b> with checkpoint-based resumability."
    ))
    elems.append(body(
        "The script uses joblib parallelism across CPU cores and writes each "
        "result to disk immediately, so interrupted runs resume from exactly "
        "where they stopped."
    ))
    elems.append(sp(0.3))

    param_order = [
        ("7.1", "n_estimators", "[10,25,50,75,100,125,150,200,250,300,350]",
         "25", "checkpoint_n_estimators.json", "val_curve_n_estimators.png"),
        ("7.2", "max_depth",     "[2, 3, 4, 5]",
         "2",   "checkpoint_max_depth.json",    "val_curve_max_depth.png"),
        ("7.3", "learning_rate", "[0.01, 0.02, 0.05, 0.08, 0.10, 0.12, 0.15, 0.21, 0.24]",
         "0.05","checkpoint_learning_rate.json","val_curve_learning_rate.png"),
        ("7.4", "subsample",     "[0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]",
         "0.95", "checkpoint_subsample.json",    "val_curve_subsample.png"),
    ]

    for num, pname, prange, pbest, ckfile, plotfile in param_order:
        elems += section_header(f"{num}  {pname}", "h2")
        elems.append(kv_table([
            ["Values tested", prange],
            ["Best value"   , pbest],
            ["Checkpoint"   , ckfile],
        ], col_widths=[3.5 * cm, 11.5 * cm]))
        elems.append(sp(0.2))
        plot_path = os.path.join(PATHS["val_curves"], plotfile)
        elems += insert_image(
            plot_path, width_cm=14,
            caption_text=f"Figure: Validation curve for {pname} — accuracy vs parameter value across all devices"
        )

    elems += section_header("Final Selected Hyperparameters", "h2")
    elems.append(results_table(
        ["Parameter", "Values Tried", "Best Value", "Fixed In Next Steps"],
        [
            ["n_estimators",    "10–350", "25",  "Steps 2, 3, 4"],
            ["max_depth",       "2, 3, 4, 5",           "2",    "Steps 3, 4"],
            ["learning_rate",   "0.01–0.24",         "0.05", "Step 4"],
            ["subsample",       "0.7–1.0",           "0.95",  "—"],
            ["colsample_bytree","fixed",              "0.8",  "All steps"],
        ]
    ))
    elems.append(sp(0.3))
    elems.append(body(
        "<b>Note on sequential tuning:</b> The best value of each parameter "
        "is found conditional on the fixed values of previously tuned parameters. "
        "This is an approximation of global optimisation but is practical given "
        "runtime constraints. A final combined validation (Section 8) confirms "
        "that the selected combination achieves the best overall accuracy."
    ))
    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────────────────────────
# SECTION 8 — FINAL VALIDATION
# ─────────────────────────────────────────────────────────────

def section_final_validation():
    elems = []
    elems += section_header(
        "8.  Step 6 — Final Combined Validation", "h1")
    elems.append(body(
        "After completing all four tuning steps, a final run of "
        "<b>battery_final_validation.py</b> was executed with all best "
        "hyperparameter values combined. This is the definitive accuracy "
        "result used for comparison against the SOM baseline."
    ))
    elems.append(kv_table([
        ["n_estimators",    "25"],
        ["max_depth",       "2"],
        ["learning_rate",   "0.05"],
        ["subsample",       "0.95"],
        ["colsample_bytree","0.8"],
        ["Training window", "14 days (daily rolling, shift = 1 day)"],
        ["Prediction",      "Next single day's 24-hour dSocdt profile"],
        ["Accuracy metric", "|pred − actual| ≤ 2.0 for each hour"],
    ], col_widths=[4 * cm, 11 * cm]))
    elems.append(sp(0.4))

    # Insert one final validation plot
    fv_plots = glob_all(os.path.join(PATHS["final_validation"], "*plot*.png"))
    if fv_plots:
        elems += insert_image(
            fv_plots[0], width_cm=15,
            caption_text="Figure: Final validation — daily accuracy, MAE, and actual vs predicted dSocdt"
        )
    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────────────────────────
# SECTION 9 — FEATURE IMPORTANCE
# ─────────────────────────────────────────────────────────────

def section_feature_importance():
    elems = []
    elems += section_header("9.  Step 7 — Feature Importance Analysis", "h1")
    elems.append(body(
        "After finalising the model, XGBoost's built-in feature importance "
        "scores (gain, weight, cover) were extracted and visualised using "
        "<b>battery_feature_import.py</b>. This identifies which hours and "
        "which types of features (dSocdt vs Soc vs date) contribute most "
        "to prediction accuracy."
    ))
    fi_plots = glob_all(os.path.join(PATHS["feature_importance"], "*.png"))
    for i, fp in enumerate(fi_plots[:3]):   # include up to 3 plots
        elems += insert_image(
            fp, width_cm=14,
            caption_text=f"Figure: Feature importance — {os.path.basename(fp)}"
        )
    if not fi_plots:
        elems += insert_image(
            None,
            caption_text="Feature importance plots (run battery_feature_import.py)"
        )
    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────────────────────────
# SECTION 10 — NEXT STEPS
# ─────────────────────────────────────────────────────────────

def section_next_steps():
    elems = []
    elems += section_header("10.  Next Steps", "h1")
    next_items = [
        "LSTM / Bidirectional LSTM model — compare against XGBoost using same daily rolling-window setup.",
        "Cross-user generalisation — train on pooled data from multiple devices, test on held-out devices.",
        "Threshold sensitivity analysis — evaluate how accuracy changes as ACC_THRESHOLD varies (1.0, 1.5, 2.0, 2.5).",
        "Cosine similarity analysis — already partially generated; complete interpretation and include in report.",
        "Final report write-up — formal academic-style documentation with literature comparison.",
    ]
    for item in next_items:
        elems.append(bullet(item))
    elems.append(sp(1))
    elems.append(hr())
    elems.append(Paragraph(
        "<i>This report was auto-generated by generate_report.py. "
        "Re-run at any time to refresh with the latest plots and results.</i>",
        S["caption"]
    ))
    return elems


# ─────────────────────────────────────────────────────────────
# BUILD PDF
# ─────────────────────────────────────────────────────────────

def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_PDF, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title="Battery Management Project Report",
        author="Project Team",
    )

    story = []
    story += cover_page()
    story += toc()
    story += section_overview()
    story += section_dataset()
    story += section_preprocessing()
    story += section_statistical()
    story += section_wide_format()
    story += section_model()
    story += section_hyperparam()
    story += section_final_validation()
    story += section_feature_importance()
    story += section_next_steps()

    doc.build(story)
    print(f"\nReport generated:  {OUTPUT_PDF}")


if __name__ == "__main__":
    import pandas   # ensure available
    build_pdf()