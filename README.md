"""
generate_report.py
==================
Run this script from inside your SOC-folder to generate a PDF progress report.

    cd path/to/SOC-folder
    python generate_report.py

Requirements:  pip install reportlab
"""

import os
import glob
import pandas as pd
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
# PATHS
# ─────────────────────────────────────────────────────────────
ROOT       = "."
RESULTS    = os.path.join(ROOT, "results")
OUTPUT_PDF = os.path.join(RESULTS, "project_report.pdf")

PATHS = {
    "ac_hc_plots"       : os.path.join(RESULTS, "ac_hc_plots"),
    "wide_csv"          : os.path.join(RESULTS, "wide_csv"),
    "resampled_csv"     : os.path.join(RESULTS, "resampled_csv"),
    "feature_importance": os.path.join(RESULTS, "xgboost", "feature_importance"),
    "final_validation"  : os.path.join(RESULTS, "xgboost", "final_validation"),
    "hypersearch"       : os.path.join(RESULTS, "xgboost", "hypersearch"),
    "val_curves"        : os.path.join(RESULTS, "xgboost", "hypersearch", "validation_curves"),
    "tree_rules"        : os.path.join(RESULTS, "xgboost", "tree_rules"),
    "model_complexity"  : os.path.join(RESULTS, "xgboost"),
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
    elems = []
    if path and os.path.exists(path):
        img_w = width_cm * cm
        img_h = min(max_height_cm * cm, img_w * 0.6)
        try:
            elems.append(Image(path, width=img_w, height=img_h, kind="proportional"))
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
    matches = sorted(glob.glob(pattern))
    return matches[0] if matches else None

def glob_all(pattern):
    return sorted(glob.glob(pattern))

def kv_table(rows, col_widths=None):
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
    elems.append(Paragraph("Predictive Battery Management", S["title"]))
    elems.append(Paragraph("Through Usage Pattern Recognition", S["title"]))
    elems.append(sp(0.5))
    elems.append(hr("#4a6fa5", thickness=2))
    elems.append(sp(0.4))
    elems.append(Paragraph("Project Progress Report", S["subtitle"]))
    elems.append(sp(3))
    meta = [
        ["Project"  , "Predictive Battery Management Through Usage Pattern Recognition"],
        ["Model"    , "XGBoost (Daily Rolling-Window, Sequential Hyperparameter Tuning)"],
        ["Status"   , "In Progress"],
        ["Scope"    , "Data Preprocessing | Statistical Analysis | Model Training & Evaluation | Model Interpretability"],
    ]
    elems.append(kv_table(meta, col_widths=[3.5 * cm, 15.5 * cm]))
    elems.append(sp(1))
    elems.append(body(
        "This document summarises all work completed so far on the battery management project. "
        "It covers raw data preprocessing, hourly resampling, long-range dependence analysis "
        "(autocorrelation and Hurst exponent), XGBoost model training using a daily rolling "
        "window, hyperparameter tuning via sequential coordinate-wise search, final validation "
        "results, feature importance analysis, decision tree rule extraction and interpretation, "
        "and model complexity/inference time estimation. "
        "The report will continue to be updated as further work is completed."
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
        ("1",    "Project Overview & Problem Statement"),
        ("2",    "Dataset Description & File Structure"),
        ("3",    "Step 1 — Data Preprocessing & Hourly Resampling"),
        ("4",    "Step 2 — Statistical Analysis (Autocorrelation & Hurst Exponent)"),
        ("5",    "Step 3 — Data Format Transformation (Wide Daily Format)"),
        ("6",    "Step 4 — XGBoost Model (Daily Rolling-Window Training)"),
        ("6.1",  "  Feature Engineering"),
        ("6.2",  "  Training Strategy"),
        ("6.3",  "  Accuracy Metric"),
        ("7",    "Step 5 — Hyperparameter Tuning (Sequential Coordinate Search)"),
        ("7.1",  "  n_estimators"),
        ("7.2",  "  max_depth"),
        ("7.3",  "  learning_rate"),
        ("7.4",  "  subsample"),
        ("8",    "Step 6 — Final Combined Validation"),
        ("9",    "Step 7 — Feature Importance Analysis"),
        ("10",   "Step 8 — Decision Tree Rule Extraction & Interpretation"),
        ("10.1", "  What Was Extracted"),
        ("10.2", "  Interpretation of Results"),
        ("10.3", "  Visualisation Plots"),
        ("11",   "Step 9 — Model Complexity & Inference Time Analysis"),
        ("11.1", "  Methodology"),
        ("11.2", "  Model Size Scaling"),
        ("11.3", "  Inference Time"),
    ]
    for num, title in sections:
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
        "expected battery life, State of Charge (SoC) minimization etc."
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
        '&nbsp;&nbsp;&nbsp;&nbsp;tree_rules/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;← Tree rule extraction outputs<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;xgboost/<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;feature_importance/&nbsp;&nbsp;← Feature importance plots<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;final_validation/&nbsp;&nbsp;&nbsp;&nbsp;← Final predictions &amp; accuracy plots<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;model_size_vs_samples.png← Model size scaling plot<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;inference_time_vs_samples.png← Inference time plot<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;hypersearch/<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;validation_curves/&nbsp;&nbsp;&nbsp;← Val curve plots per hyperparameter<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;best_*.json&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;← Best value per hyperparameter<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;checkpoint_*.json&nbsp;&nbsp;&nbsp;&nbsp;← Resume checkpoints<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;results_*.csv&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;← Raw tuning results<br/>'
        '&nbsp;&nbsp;analyze.py&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;← Resampling + AC/HC analysis<br/>'
        '&nbsp;&nbsp;xgboost_hypersearch.py&nbsp;&nbsp;&nbsp;&nbsp;← Sequential hyperparameter tuning<br/>'
        '&nbsp;&nbsp;xgboost_final_validation.py← Final combined validation<br/>'
        '&nbsp;&nbsp;xgboost_feature_importance.py&nbsp;&nbsp;← Feature importance analysis<br/>'
        '&nbsp;&nbsp;xgboost_tree_rules.py&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;← Tree rule extraction<br/>'
        '&nbsp;&nbsp;model_size_curve.py&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;← Model complexity analysis<br/>'
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
        "and their dSocdt values are zeroed out before model training."
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
        "investigated: does the discharge behaviour of a user exhibit long-range "
        "temporal dependence? If past patterns genuinely influence future patterns "
        "over weeks, then sequence-aware models should outperform pattern-clustering "
        "approaches like SOM."
    ))
    elems += section_header("4.1  Autocorrelation Analysis", "h2")
    elems.append(body(
        "Pearson autocorrelation of the dSocdt discharge series was computed "
        "at lags 0 to 504 hours (3 weeks) for each device. Only discharge "
        "samples (dSocdt &lt; 0) were used. Vertical markers indicate daily (24h) "
        "and weekly (168h) periods."
    ))
    ac_plots = glob_all(os.path.join(PATHS["ac_hc_plots"], "*autocorr*.png"))
    if ac_plots:
        elems += insert_image(ac_plots[0], width_cm=15,
                              caption_text="Figure: Autocorrelation of dSocdt (discharge only) — lags 0 to 504 hours")
    else:
        elems += insert_image(None, caption_text="Figure: Autocorrelation plot")

    elems += section_header("4.2  Hurst Exponent (R/S Analysis)", "h2")
    elems.append(body(
        "The Hurst exponent H is estimated via Rescaled Range (R/S) analysis. "
        "H is the slope of the fitted line on the log(R/S) vs log(n) plot: "
        "H &gt; 0.5 = persistent (past predicts future); H ≈ 0.5 = random walk; "
        "H &lt; 0.5 = anti-persistent."
    ))
    hc_plots = glob_all(os.path.join(PATHS["ac_hc_plots"], "*hurst*.png"))
    if hc_plots:
        elems += insert_image(hc_plots[0], width_cm=13,
                              caption_text="Figure: Hurst exponent R/S analysis — slope = H")
    else:
        elems += insert_image(None, caption_text="Figure: Hurst exponent plot")

    elems += section_header("4.3  Results Across All Devices", "h2")
    h_rows = [
        ["H > 0.7 (Strong persistence)",  "Majority of devices", "Strong long-range dependence — highly predictable"],
        ["H = 0.5–0.6 (Mild)",            "Few devices",         "Some structure but weaker signal"],
        ["H = 0.4–0.5 (Near random)",     "Rare",                "Limited predictability"],
    ]
    elems.append(results_table(["Hurst Range", "Frequency", "Interpretation"], h_rows))
    elems.append(sp(0.3))
    elems.append(body(
        "<b>Conclusion:</b> The majority of devices show H &gt; 0.7, confirming "
        "that sequence-aware models (XGBoost with temporal features) should "
        "outperform SOM-based clustering. This finding directly motivates the model choice."
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
        "XGBoost requires a tabular feature matrix. The resampled CSVs are pivoted "
        "into a wide daily format via <b>battery_xgboost.py</b>:"
    ))
    elems.append(kv_table([
        ["Rows"    , "One row per calendar date"],
        ["Columns" , "dSocdt_h0…h23 | Soc_h0…h23 | ChargingStatus_h0…h23 (72 columns)"],
        ["dSocdt"  , "+ve values clipped to 0 (charging effect removed)"],
        ["Soc"     , "Forward/backward filled within each day for missing hours"],
        ["Saved to", "results/wide_csv/<device>_wide.csv"],
    ], col_widths=[3.5 * cm, 11.5 * cm]))
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
        "fashion. The prediction target is the 24-hour dSocdt profile of the next day."
    ))
    elems += section_header("6.1  Feature Engineering", "h2")
    elems.append(body(
        "For each prediction day, the full 14-day training window is flattened "
        "into a single feature vector. Per training day the following features are included:"
    ))
    for f in ["24 dSocdt values (hourly discharge rates, charging zeroed out)",
              "24 Soc values (hourly state of charge)",
              "Day of week (Monday=0 … Sunday=6)",
              "Day of month (1–31)", "Month (1–12)", "Year (e.g. 2024)"]:
        elems.append(bullet(f))
    elems.append(kv_table([
        ["Features per day",    "24 + 24 + 4 = 52"],
        ["Training window",     "14 days"],
        ["Total feature vector","14 × 52 = 728 features"],
        ["Output",              "24 dSocdt values for the next day (h0 … h23)"],
    ], col_widths=[4 * cm, 11 * cm]))

    elems += section_header("6.2  Training Strategy", "h2")
    elems.append(body(
        "Because each prediction iteration has only 13 labelled training samples, "
        "a zero-padded expanding context strategy is used: sample k uses days "
        "[train_start … train_start+k-1] padded with zeros to predict day train_start+k. "
        "The actual prediction uses the full real 14-day window. "
        "Predictions are clipped to ≤ 0. Always uses actual past values — no predicted values fed back."
    ))
    elems += section_header("6.3  Accuracy Metric", "h2")
    elems.append(body(
        "A prediction for a given hour is counted as correct if "
        "|predicted dSocdt − actual dSocdt| ≤ threshold (set to 2.0). "
        "Accuracy for a day = % of 24 hours that are correct. "
        "MAE and RMSE are also recorded per day and device as secondary metrics."
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
        "Full grid search was infeasible (~40 minutes per combination across all devices). "
        "Instead, a <b>sequential coordinate-wise search</b> was used: tune one parameter "
        "at a time while fixing all others, implemented in <b>battery_hypersearch.py</b> "
        "with checkpoint-based resumability and joblib parallelism."
    ))
    elems.append(sp(0.3))

    param_order = [
        ("7.1", "n_estimators",  "[10, 25, 50, 75, 100, 125, 150, 200, 250, 300, 350]",
         "25",   "val_curve_n_estimators.png"),
        ("7.2", "max_depth",     "[2, 3, 4, 5]",
         "2",    "val_curve_max_depth.png"),
        ("7.3", "learning_rate", "[0.01, 0.02, 0.05, 0.08, 0.10, 0.12, 0.15, 0.21, 0.24]",
         "0.05", "val_curve_learning_rate.png"),
        ("7.4", "subsample",     "[0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]",
         "0.95", "val_curve_subsample.png"),
    ]
    for num, pname, prange, pbest, plotfile in param_order:
        elems += section_header(f"{num}  {pname}", "h2")
        elems.append(kv_table([
            ["Values tested", prange],
            ["Best value",    pbest],
        ], col_widths=[3.5 * cm, 11.5 * cm]))
        elems.append(sp(0.2))
        plot_path = os.path.join(PATHS["val_curves"], plotfile)
        elems += insert_image(plot_path, width_cm=14,
                              caption_text=f"Figure: Validation curve for {pname}")

    elems += section_header("Final Selected Hyperparameters", "h2")
    elems.append(results_table(
        ["Parameter", "Values Tried", "Best Value", "Fixed In Next Steps"],
        [
            ["n_estimators",     "10–350",  "25",   "Steps 2, 3, 4"],
            ["max_depth",        "2, 3, 4, 5", "2", "Steps 3, 4"],
            ["learning_rate",    "0.01–0.24",  "0.05", "Step 4"],
            ["subsample",        "0.7–1.0",    "0.95", "—"],
            ["colsample_bytree", "fixed",       "0.8",  "All steps"],
        ]
    ))
    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────────────────────────
# SECTION 8 — FINAL VALIDATION
# ─────────────────────────────────────────────────────────────

def section_final_validation():
    elems = []
    elems += section_header("8.  Step 6 — Final Combined Validation", "h1")
    elems.append(body(
        "After completing all four tuning steps, a final run of "
        "<b>battery_final_validation.py</b> was executed with all best "
        "hyperparameter values combined."
    ))
    elems.append(kv_table([
        ["n_estimators",     "25"],
        ["max_depth",        "2"],
        ["learning_rate",    "0.05"],
        ["subsample",        "0.95"],
        ["colsample_bytree", "0.8"],
        ["Training window",  "14 days (daily rolling, shift = 1 day)"],
        ["Prediction",       "Next single day's 24-hour dSocdt profile"],
        ["Accuracy metric",  "|pred − actual| ≤ 2.0 for each hour"],
    ], col_widths=[4 * cm, 11 * cm]))
    elems.append(sp(0.4))

    # Try to load final summary CSV
    summary_csv = os.path.join(PATHS["final_validation"], "final_summary_all_thresholds.csv")
    if os.path.exists(summary_csv):
        df = pd.read_csv(summary_csv)
        df2 = df[df["threshold"] == 2]
        rows = []
        for _, r in df2.iterrows():
            short = str(r["device"])[:18] + "…" if len(str(r["device"])) > 20 else str(r["device"])
            rows.append([short, f"{r['mean_accuracy_%']:.2f}%",
                         f"{r['mean_mae']:.5f}", f"{r['mean_rmse']:.5f}"])
        if rows:
            elems.append(results_table(
                ["Device", "Mean Accuracy (T=2)", "Mean MAE", "Mean RMSE"], rows))
            elems.append(sp(0.3))

    fv_plots = glob_all(os.path.join(PATHS["final_validation"], "*plot*.png"))
    if fv_plots:
        elems += insert_image(fv_plots[0], width_cm=15,
                              caption_text="Figure: Final validation — daily accuracy, MAE, cosine similarity, actual vs predicted")
    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────────────────────────
# SECTION 9 — FEATURE IMPORTANCE
# ─────────────────────────────────────────────────────────────

def section_feature_importance():
    elems = []
    elems += section_header("9.  Step 7 — Feature Importance Analysis", "h1")
    elems.append(body(
        "XGBoost's built-in feature importance scores were extracted and visualised "
        "using <b>battery_feature_import.py</b>. The model is trained on pooled data "
        "from all devices and importance is averaged across all 24 hour-estimators."
    ))
    fi_plots = glob_all(os.path.join(PATHS["feature_importance"], "*.png"))
    for fp in fi_plots[:3]:
        elems += insert_image(fp, width_cm=14,
                              caption_text=f"Figure: {os.path.basename(fp)}")
    if not fi_plots:
        elems += insert_image(None, caption_text="Feature importance plots")
    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────────────────────────
# SECTION 10 — TREE RULE EXTRACTION & INTERPRETATION
# ─────────────────────────────────────────────────────────────

def section_tree_rules():
    elems = []
    elems += section_header(
        "10.  Step 8 — Decision Tree Rule Extraction & Interpretation", "h1")

    elems += section_header("10.1  What Was Extracted", "h2")
    elems.append(body(
        "XGBoost internally stores each boosting round as a decision tree. "
        "The script <b>battery_tree_rules.py</b> uses XGBoost's "
        "<i>get_booster().get_dump(dump_format='json')</i> to extract every split "
        "condition and leaf prediction from all trees of all 24 hour-estimators. "
        "A separate <b>battery_tree_analysis_extended.py</b> then analyses the "
        "extracted rules statistically and produces interpretation plots."
    ))
    elems.append(kv_table([
        ["Total split nodes",      "1,800  (25 trees × 3 nodes/tree × 24 hours)"],
        ["Unique features used",   "143 distinct features appeared as split conditions"],
        ["Trees per output hour",  "25"],
        ["Max tree depth",         "2  (root node + one level of child nodes)"],
        ["Output files",           "tree_rules_hour_XX.txt (one per hour) + tree_rules_all.txt"],
        ["Summary CSV",            "tree_rules_summary.csv — one row per split node"],
    ], col_widths=[4.5 * cm, 10.5 * cm]))
    elems.append(sp(0.3))
    elems.append(body(
        "An example of an extracted rule (from hour 16 prediction, Tree 1) is shown below. "
        "Each tree in XGBoost predicts a small residual contribution; the 25 trees' "
        "leaf values are summed to give the final predicted dSocdt for that hour:"
    ))
    elems.append(Paragraph(
        '<font name="Courier" size="8">'
        'if  dSocdt_h19_day_minus1  &lt;  -2.887200  :<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;if  dSocdt_h19_day_minus1  &lt;  -8.222100  :<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;→  predict  -0.154673<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;else  ( dSocdt_h19_day_minus1  &gt;=  -8.222100 ) :<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;→  predict  -0.045969<br/>'
        'else  ( dSocdt_h19_day_minus1  &gt;=  -2.887200 ) :<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;if  dSocdt_h21_day_minus1  &lt;  -1.279700  :<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;→  predict  -0.005868<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;else  ( dSocdt_h21_day_minus1  &gt;=  -1.279700 ) :<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;→  predict  +0.099016'
        '</font>', S["body"]
    ))
    elems.append(sp(0.3))

    elems += section_header("10.2  Interpretation of Results", "h2")
    elems.append(body(
        "<b>Feature type dominance:</b> 86.3% of all split nodes use dSocdt features, "
        "11.1% use SoC features, and only 2.7% use date/calendar features. "
        "This confirms that the model is overwhelmingly driven by past discharge "
        "<i>rate</i> — how fast the battery drained — rather than the battery level "
        "or the calendar date."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>Recency dominance:</b> 73.1% of all split conditions rely exclusively on "
        "yesterday's data (day-minus-1), and 90.9% rely on either yesterday or the day "
        "before. Features from 3 or more days ago collectively contribute less than 9%. "
        "This empirically confirms that recent history dominates prediction and that "
        "a very long training window adds diminishing returns per tree."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>Most decisive features (root node analysis):</b> The single most important "
        "first question each tree asks concerns the discharge rate at evening hours of "
        "yesterday. The top 5 root-split features are: "
        "dSocdt_h19_day_minus1 (64 trees), dSocdt_h14_day_minus1 (61 trees), "
        "dSocdt_h23_day_minus1 (47 trees), dSocdt_h20_day_minus1 (45 trees), "
        "dSocdt_h15_day_minus1 (41 trees). "
        "This shows that evening phone usage (14:00–23:00 yesterday) is the "
        "strongest predictor of tomorrow's discharge patterns — consistent with "
        "the intuition that heavy evening use (gaming, video) tends to repeat."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>Discharge rate thresholds:</b> The median split threshold across all "
        "dSocdt nodes is -2.999% SoC/hour, meaning the model's typical decision boundary "
        "is 'was the device losing more than 3% SoC per hour?' "
        "Hours 22–23 use far more negative thresholds (~-5 to -15.8%/hr), meaning the "
        "model only branches on late-night discharge when it is extreme. "
        "Hours 3–5 AM use near-zero thresholds (~-0.9 to -1.0%/hr) since any "
        "discharge at all during those hours is unusual."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>Hour-of-day split clusters:</b> From the heatmap (tree_interp_hour_vs_predictor.png) "
        "we observe that 54% of the splits based on hour of day belong to the evening cluster    "
        "(hours 14-23) and 23% belong to the morning cluster (hours 03-06)."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>SoC thresholds:</b> When SoC features appear, the model looks at SoC at "
        "10:00 (mid-morning) and 23:00 (end of day) from yesterday. The ~43% median "
        "threshold distinguishes users who ended the day above vs below half charge — "
        "a proxy for whether the device was charged during the day."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>Depth-2 trees:</b> Every tree makes at most 2 sequential binary decisions "
        "before predicting a leaf value. The final prediction for any hour = sum of all "
        "25 trees' leaf values. Each tree represents a simple rule of the form: "
        "'If [yesterday's evening dSocdt was below X] AND [a secondary condition holds] "
        "→ predict [small discharge increment].' "
        "The 25 trees together build up the full prediction by stacking these simple rules."
    ))
    elems.append(sp(0.3))

    elems += section_header("10.3  Visualisation Plots", "h2")

    tree_plots = [
        ("tree_interp_root_features.png",
         "Figure: Most frequent root-node split features — the first decision each tree makes"),
        ("tree_interp_hour_vs_predictor.png",
         "Figure: Heatmap of which past hour's dSocdt is used to predict each output hour"),
        ("tree_interp_dsocdt_thresholds.png",
         "Figure: Median dSocdt split threshold and split frequency by hour of day"),
        ("tree_interp_soc_thresholds.png",
         "Figure: SoC threshold distribution and most-used SoC split features"),
        ("tree_interp_recency_dominance.png",
         "Figure: How split node usage drops off with days-back (recency effect)"),
    ]

    for fname, cap in tree_plots:
        fpath = os.path.join(PATHS["tree_rules"], fname)
        elems += insert_image(fpath, width_cm=14, caption_text=cap)

    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────────────────────────
# SECTION 11 — MODEL COMPLEXITY & INFERENCE TIME
# ─────────────────────────────────────────────────────────────

def section_model_complexity():
    elems = []
    elems += section_header(
        "11.  Step 9 — Model Complexity & Inference Time Analysis", "h1")

    elems += section_header("11.1  Methodology", "h2")
    elems.append(body(
        "To understand the practical footprint of the trained pipeline, "
        "<b>model_size_curve.py</b> was run to measure how model size (KB) and "
        "single-sample inference time (ms) scale with the number of training samples. "
        "The experiment uses synthetic data with the same feature structure as the "
        "real pipeline (728 features, 24 outputs) and the final best hyperparameters, "
        "varying training samples from 60 to 365 days in steps of 15."
    ))
    elems.append(kv_table([
        ["Feature vector",   "728 features per sample (14 days × 52 features/day)"],
        ["Output dimensions","24 (one dSocdt per hour)"],
        ["Model structure",  "MultiOutputRegressor wrapping XGBRegressor (24 sub-models)"],
        ["Serialisation",    "Python pickle — entire pipeline object serialised to .bin"],
        ["Sample range",     "60 to 365 training samples, step 15"],
        ["Inference",        "Single-sample prediction time measured per model"],
        ["n_estimators",     "25  |  max_depth: 2  |  lr: 0.05  |  subsample: 0.95"],
    ], col_widths=[4 * cm, 11 * cm]))
    elems.append(sp(0.3))

    elems += section_header("11.2  Model Size Scaling", "h2")
    elems.append(body(
        "The serialised model size ranges between approximately 618 KB and 621 KB "
        "across all tested training sample sizes. The variation is narrow — less than "
        "3 KB across a 6× range of training data volume. "
        "A polynomial fit (degree 3, R² = 0.629) captures a weak upward trend: "
        "more training samples leads to marginally larger trees as the model "
        "finds more diverse split thresholds to fit the data. "
        "The near-constant size is explained by the fixed model architecture — "
        "25 trees of depth 2 per output hour — which determines the number of "
        "nodes and parameters regardless of training set size. "
        "The model is lightweight and practical for deployment on resource-constrained devices."
    ))
    size_plot = os.path.join(PATHS["model_complexity"], "model_size_vs_samples.png")
    elems += insert_image(
        size_plot, width_cm=13,
        caption_text="Figure: Model size (KB) vs number of training samples — nearly constant due to fixed tree architecture"
    )

    elems += section_header("11.3  Inference Time", "h2")
    elems.append(body(
        "Single-sample inference time (the time to predict one day's 24-hour dSocdt "
        "profile) ranges between approximately 35 ms and 125 ms, with a median around "
        "47–50 ms. The scatter in the plot is primarily due to OS scheduling noise "
        "and Python interpreter overhead rather than true scaling behaviour — "
        "XGBoost tree traversal for a fixed-depth-2 model with 25 trees is "
        "O(depth × n_trees) = O(50) operations per output, which is effectively "
        "instantaneous compared to OS-level timing granularity. "
        "The practical implication is that the model can make a full next-day "
        "prediction in under 50 ms on a standard laptop CPU, making it highly "
        "suitable for real-time or near-real-time battery management applications."
    ))
    time_plot = os.path.join(PATHS["model_complexity"], "inference_time_vs_samples.png")
    elems += insert_image(
        time_plot, width_cm=13,
        caption_text="Figure: Single-sample inference time (ms) vs number of training samples — effectively constant at ~47 ms median"
    )

    elems.append(body(
        "<b>Summary:</b> The model has a fixed serialised size of ~620 KB and a "
        "median inference time of ~47 ms regardless of training data volume. "
        "Both metrics confirm that the XGBoost pipeline is computationally lightweight "
        "and well-suited for deployment in a battery management system where "
        "predictions need to be generated daily on device."
    ))
    elems.append(PageBreak())
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
    story += section_tree_rules()
    story += section_model_complexity()

    doc.build(story)
    print(f"\nReport generated:  {OUTPUT_PDF}")


if __name__ == "__main__":
    build_pdf()
