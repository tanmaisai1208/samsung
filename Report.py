"""
generate_report.py
==================
Run from inside your project folder to generate the full PDF progress report,
covering BOTH the original (Approach 1 / "main" branch) and the revised
(Approach 2 / "test" branch) methodology.

Folder convention (as used by the project's git branches):
    results_old/   <- results copied from the "main" branch  (Approach 1)
    results/   <- results already in the "test" branch    (Approach 2)

    cd path/to/project-folder
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
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable, Image
)

# ─────────────────────────────────────────────────────────────
# PATHS — two parallel result sets
# ─────────────────────────────────────────────────────────────
ROOT       = "."
R1         = os.path.join(ROOT, "results_old")   # Approach 1 (main branch)
R2         = os.path.join(ROOT, "results")   # Approach 2 (test branch)
OUTPUT_PDF = os.path.join(ROOT, "project_report.pdf")

PATHS_1 = {
    "ac_hc_plots"       : os.path.join(R1, "ac_hc_plots"),
    "feature_importance": os.path.join(R1, "xgboost", "feature_importance"),
    "final_validation"  : os.path.join(R1, "xgboost", "final_validation"),
    "hypersearch"       : os.path.join(R1, "xgboost", "hypersearch"),
    "val_curves"        : os.path.join(R1, "xgboost", "hypersearch", "validation_curves"),
    "tree_rules"        : os.path.join(R1, "xgboost", "tree_rules"),
    "all_users_summary" : os.path.join(R1, "all_users_summary.csv"),
    "model_size"        : os.path.join(R1, "xgboost", "model_size_vs_samples.png"),
    "inference_time"    : os.path.join(R1, "xgboost", "inference_time_vs_samples.png"),
    # Task A/B plots not yet copied into this results folder — placeholder paths.
    # Replace these once you add the charging-diagnostic PNGs to results_1/xgboost/final_validation/
    "charging_discrimination": os.path.join(R1, "xgboost", "final_validation", "charging_discrimination_plot.png"),
    "charging_detection"      : os.path.join(R1, "xgboost", "final_validation", "charging_event_detection_plot.png"),
    "charging_eps_sweep"      : os.path.join(R1, "xgboost", "final_validation", "charging_zero_threshold_sweep_plot.png"),
}

PATHS_2 = {
    "ac_hc_plots"       : os.path.join(R2, "ac_hc_plots"),
    "feature_importance": os.path.join(R2, "xgboost", "feature_importance"),
    "final_validation"  : os.path.join(R2, "xgboost", "final_validation"),
    "hypersearch"       : os.path.join(R2, "xgboost", "hypersearch"),
    "val_curves"        : os.path.join(R2, "xgboost", "hypersearch", "validation_curves"),
    "tree_rules"        : os.path.join(R2, "xgboost", "tree_rules"),
    "all_users_summary" : os.path.join(R2, "all_users_summary.csv"),
    "charging_schedule" : os.path.join(R2, "xgboost", "charging_schedule"),
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
        spaceAfter=6, alignment=TA_CENTER, fontName="Helvetica-Bold")
    s["subtitle"] = ParagraphStyle(
        "Subtitle", parent=base_styles["Normal"],
        fontSize=12, textColor=colors.HexColor("#4a6fa5"),
        spaceAfter=4, alignment=TA_CENTER, fontName="Helvetica")
    s["h1"] = ParagraphStyle(
        "H1", parent=base_styles["Heading1"],
        fontSize=15, textColor=colors.HexColor("#1a2e4a"),
        spaceBefore=18, spaceAfter=6, fontName="Helvetica-Bold", leading=18)
    s["h2"] = ParagraphStyle(
        "H2", parent=base_styles["Heading2"],
        fontSize=12, textColor=colors.HexColor("#2c5282"),
        spaceBefore=12, spaceAfter=4, fontName="Helvetica-Bold")
    s["h3"] = ParagraphStyle(
        "H3", parent=base_styles["Heading3"],
        fontSize=10.5, textColor=colors.HexColor("#3a6ea5"),
        spaceBefore=8, spaceAfter=3, fontName="Helvetica-Bold")
    s["treebox"] = ParagraphStyle(
        "TreeBox", parent=base_styles["Normal"],
        fontSize=9, leading=14, fontName="Courier",
        textColor=colors.HexColor("#2d3748"))
    s["overview"] = ParagraphStyle(
        "Overview", parent=base_styles["Normal"],
        fontSize=9.5, leading=13.5, spaceAfter=6,
        alignment=TA_JUSTIFY, fontName="Helvetica-Oblique",
        textColor=colors.HexColor("#1a4971"),
        backColor=colors.HexColor("#eef6fc"),
        borderColor=colors.HexColor("#a9d2ef"), borderWidth=0.6,
        borderPadding=8)
    s["body"] = ParagraphStyle(
        "Body", parent=base_styles["Normal"],
        fontSize=10, leading=15, spaceAfter=6,
        alignment=TA_JUSTIFY, fontName="Helvetica")
    s["bullet"] = ParagraphStyle(
        "Bullet", parent=base_styles["Normal"],
        fontSize=10, leading=14, spaceAfter=3,
        leftIndent=16, firstLineIndent=-10, fontName="Helvetica")
    s["caption"] = ParagraphStyle(
        "Caption", parent=base_styles["Normal"],
        fontSize=8.5, textColor=colors.HexColor("#718096"),
        alignment=TA_CENTER, spaceAfter=8, fontName="Helvetica-Oblique")
    s["toc"] = ParagraphStyle(
        "TOC", parent=base_styles["Normal"],
        fontSize=10.5, leading=18, fontName="Helvetica",
        textColor=colors.HexColor("#2d3748"))
    s["warnbox"] = ParagraphStyle(
        "WarnBox", parent=base_styles["Normal"],
        fontSize=10, leading=15, spaceAfter=6,
        alignment=TA_JUSTIFY, fontName="Helvetica",
        textColor=colors.HexColor("#7a1f1f"),
        backColor=colors.HexColor("#fff5f5"),
        borderColor=colors.HexColor("#feb2b2"), borderWidth=0.6,
        borderPadding=8)
    s["notebox"] = ParagraphStyle(
        "NoteBox", parent=base_styles["Normal"],
        fontSize=9.5, leading=13, spaceAfter=6,
        alignment=TA_JUSTIFY, fontName="Helvetica-Oblique",
        textColor=colors.HexColor("#744210"),
        backColor=colors.HexColor("#fffbea"),
        borderColor=colors.HexColor("#f6e05e"), borderWidth=0.6,
        borderPadding=8)
    return s

S = make_styles()


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def hr(color="#cbd5e0", thickness=0.5):
    return HRFlowable(width="100%", thickness=thickness,
                      color=colors.HexColor(color), spaceAfter=6, spaceBefore=2)

def section_header(text, level="h1", anchor=None):
    heading_text = f'<a name="{anchor}"/>{text}' if anchor else text
    return [hr("#2c5282" if level == "h1" else "#a0aec0",
               thickness=1.5 if level == "h1" else 0.5),
            Paragraph(heading_text, S[level]),
            Spacer(1, 0.2 * cm)]

def body(text):
    return Paragraph(text, S["body"])

def warnbox(text):
    return Paragraph(text, S["warnbox"])

def notebox(text):
    return Paragraph(text, S["notebox"])

def bullet(text, symbol="•"):
    return Paragraph(f"{symbol}  {text}", S["bullet"])

def caption(text):
    return Paragraph(text, S["caption"])

def sp(h=0.3):
    return Spacer(1, h * cm)

def tree_box(title, lines):
    """Renders a monospace ASCII-tree box (e.g. at the start of a Part)
    showing the section outline that follows, so the structure is
    visible before the detailed content starts. `lines` is a list of
    either plain strings, or (text, anchor) tuples that render as
    clickable internal PDF links jumping straight to that section."""
    rendered = []
    for line in lines:
        if isinstance(line, tuple):
            text, anchor = line
            rendered.append(f'<a href="#{anchor}" color="#2c5282">{text}</a>'
                             if anchor else text)
        else:
            rendered.append(line)
    body_text = f"<b>{title}</b><br/>" + "<br/>".join(rendered)
    t = Table([[Paragraph(body_text, S["treebox"])]], colWidths=[(PAGE_W - 2 * MARGIN)])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7fafc")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#a0aec0")),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    return [t, sp(0.4)]

def section_overview(text):
    """Short 2-3 line 'Section Overview' box placed right under a major
    section heading, previewing what that section covers."""
    return [Paragraph(f"<b>Section Overview:</b> {text}", S["overview"]), sp(0.15)]

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
            f'<font color="#a0aec0"><i>[Plot not found: {name} — placeholder, '
            f'add the file to this path once available]</i></font>', S["body"]))
    if caption_text:
        elems.append(caption(caption_text))
    elems.append(sp(0.3))
    return elems

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
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
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
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ebf4ff")]),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#bee3f8")),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t

def hurst_breakdown(csv_path):
    """Returns (n_total, n_persistent, n_random, n_anti, mean_h) or None."""
    if not os.path.exists(csv_path):
        return None
    df = pd.read_csv(csv_path)
    n_total = len(df)
    n_pers  = df["Regime"].str.contains("Persistent").sum()
    n_rand  = df["Regime"].str.contains("Random").sum()
    n_anti  = df["Regime"].str.contains("Anti").sum()
    mean_h  = df["HurstExponent"].mean()
    return n_total, n_pers, n_rand, n_anti, mean_h

def feature_type_breakdown(csv_path):
    """Returns dict {type: pct} or None."""
    if not os.path.exists(csv_path):
        return None
    df = pd.read_csv(csv_path)
    totals = df.groupby("feature_type")["importance"].sum()
    total_sum = totals.sum()
    return {k: 100 * v / total_sum for k, v in totals.items()}


# ─────────────────────────────────────────────────────────────
# COVER PAGE & TOC
# ─────────────────────────────────────────────────────────────

def cover_page():
    elems = []
    elems.append(sp(2.5))
    elems.append(Paragraph("Predictive Battery Management", S["title"]))
    elems.append(Paragraph("Through Usage Pattern Recognition", S["title"]))
    elems.append(sp(0.5))
    elems.append(hr("#4a6fa5", thickness=2))
    elems.append(sp(0.4))
    elems.append(Paragraph("Project Progress Report — Two-Approach Methodology", S["subtitle"]))
    elems.append(sp(2.5))
    meta = [
        ["Project" , "Predictive Battery Management Through Usage Pattern Recognition"],
        ["Model"   , "XGBoost (Daily Rolling-Window, Sequential Hyperparameter Tuning)"],
        ["Status"  , "In Progress — Approach 2 (revised methodology) complete"],
        ["Scope"   , "Data Preprocessing | Statistical Analysis | Model Training | "
                      "Interpretability | Model Complexity | Methodology Revision"],
    ]
    elems.append(kv_table(meta, col_widths=[3.5 * cm, 11.5 * cm]))
    elems.append(sp(1))
    elems.append(body(
        "This report documents two successive approaches. <b>Approach 1</b> "
        "(results_old/, main branch) clipped positive dSocdt values to zero and "
        "used interpolation-based hourly resampling. Diagnostic analysis of "
        "Approach 1 revealed the model could not reliably distinguish charging "
        "events from light usage, motivating a methodology revision. "
        "<b>Approach 2</b> (results/, test branch) retains positive dSocdt "
        "values, uses average-based resampling with explicit NaN handling, and "
        "repeats the full pipeline. This report is a living document."
    ))
    elems.append(PageBreak())
    return elems

def toc():
    elems = []
    elems += section_header("Table of Contents", "h1")
    sections = [
        ("PART A", "APPROACH 1 — ORIGINAL METHODOLOGY  (results_1/)"),
        ("1",  "Project Overview & Problem Statement"),
        ("2",  "Dataset Description & File Structure"),
        ("3",  "Data Preprocessing (Interpolation-Based Resampling)"),
        ("4",  "Statistical Analysis — Autocorrelation & Hurst Exponent"),
        ("5",  "XGBoost Model & Hyperparameter Tuning"),
        ("6",  "Final Validation Results"),
        ("7",  "Feature Importance Analysis"),
        ("8",  "Tree Rule Extraction & Interpretation"),
        ("9",  "Model Size & Inference Time Analysis"),
        ("10", "Charging-Detection Diagnostic (Task A & Task B)"),
        ("11", "Limitations Identified in Approach 1"),
        ("PART B", "APPROACH 2 — REVISED METHODOLOGY  (results_2/)"),
        ("12", "Motivation for Methodology Revision"),
        ("13", "Revised Data Preprocessing (Average-Based Resampling)"),
        ("14", "Revised Hyperparameter Tuning"),
        ("15", "Revised Final Validation Results"),
        ("16", "Revised Feature Importance Analysis"),
        ("17", "Revised Tree Rule Extraction & Interpretation"),
        ("18", "Comparison: Approach 1 vs Approach 2"),
        ("19", "Charging Schedule Prediction (Pooled Model, Walk-Forward Retrain)"),
        ("20", "Hyperparameter Dump & Sequential Regularization Tuning"),
        ("21", "Next Steps"),
    ]
    for num, title in sections:
        if num == "PART A":
            elems.append(sp(0.15))
            elems.append(Paragraph(
                f'<a href="#parta" color="#7a1f1f"><font name="Helvetica-Bold">{title}</font></a>',
                S["toc"]))
            elems.append(sp(0.1))
        elif num == "PART B":
            elems.append(sp(0.15))
            elems.append(Paragraph(
                f'<a href="#partb" color="#7a1f1f"><font name="Helvetica-Bold">{title}</font></a>',
                S["toc"]))
            elems.append(sp(0.1))
        else:
            # tree-style connector prefix + clickable link straight to the section
            connector = '&nbsp;&nbsp;&nbsp;<font color="#a0aec0">├─</font>&nbsp;'
            elems.append(Paragraph(
                f'{connector}<a href="#sec{num}" color="#2c5282">'
                f'<font name="Helvetica-Bold">{num}</font>  {title}</a>', S["toc"]))
    elems.append(PageBreak())
    return elems


# ═════════════════════════════════════════════════════════════
# PART A — APPROACH 1
# ═════════════════════════════════════════════════════════════

def part_a_divider():
    elems = []
    elems.append(sp(6))
    elems.append(Paragraph('<a name="parta"/>PART A', S["title"]))
    elems.append(Paragraph("APPROACH 1 — ORIGINAL METHODOLOGY", S["subtitle"]))
    elems.append(sp(0.5))
    elems.append(hr("#7a1f1f", thickness=2))
    elems.append(sp(1))
    elems.append(body(
        "Positive dSocdt values (charging) were clipped to zero, and hourly "
        "resampling used time-based linear interpolation to fill gaps. This "
        "approach was later found to have a specific limitation, analysed in "
        "Section 10, which motivated the revision described in Part B."
    ))
    elems.append(sp(0.3))
    elems += tree_box("Part A structure", [
        "PART A — Approach 1 (Original Methodology)",
        ("├── 1. Project Overview &amp; Problem Statement", "sec1"),
        ("├── 2. Dataset Description &amp; File Structure", "sec2"),
        ("├── 3. Data Preprocessing (Interpolation-Based Resampling)", "sec3"),
        ("├── 4. Statistical Analysis — Autocorrelation &amp; Hurst Exponent", "sec4"),
        ("├── 5. XGBoost Model &amp; Hyperparameter Tuning", "sec5"),
        ("├── 6. Final Validation Results", "sec6"),
        ("├── 7. Feature Importance Analysis", "sec7"),
        ("├── 8. Tree Rule Extraction &amp; Interpretation", "sec8"),
        ("├── 9. Model Size &amp; Inference Time Analysis", "sec9"),
        ("├── 10. Charging-Detection Diagnostic (Task A &amp; Task B)", "sec10"),
        ("└── 11. Limitations Identified in Approach 1  →  motivates Part B", "sec11"),
    ])
    elems.append(PageBreak())
    return elems

def s1_overview():
    elems = []
    elems += section_header("1.  Project Overview & Problem Statement", "h1", anchor="sec1")
    elems += section_overview(
        "States the project's goal and why a data-driven approach is needed "
        "over rule-based battery management."
    )
    elems.append(body(
        "The goal of this project is to predict future battery usage patterns "
        "of mobile devices by learning from historical State-of-Charge (SoC) "
        "time-series data. Accurate prediction of discharge behaviour enables "
        "intelligent suggestions to users — such as optimal charging times, "
        "expected battery life, and anomaly detection for degraded cells."
    ))
    elems.append(sp(0.5))
    return elems

def s2_dataset():
    elems = []
    elems += section_header("2.  Dataset Description & File Structure", "h1", anchor="sec2")
    elems += section_overview(
        "Describes the raw per-device CSV format and the meaning of each "
        "column used downstream."
    )
    elems.append(body(
        "Multiple CSV files are provided, each corresponding to one device/user, "
        "with raw time-stamped SoC readings at irregular intervals."
    ))
    col_rows = [
        ["ID",             "Device identifier (ignored in modelling)"],
        ["TimeStamp",      "Unix timestamp (ignored in modelling)"],
        ["ChargingStatus", "0 = discharging, 1 = charging"],
        ["Soc",            "State of Charge — current battery percentage (0–100)"],
        ["DischargeLevel", "Raw discharge counter"],
        ["DateTime",       "Human-readable timestamp"],
        ["dSocdt",         "Rate of change of SoC (+ve = charging, -ve = discharging, 0 = idle)"],
    ]
    elems.append(kv_table(col_rows, col_widths=[3.8 * cm, 11.2 * cm]))
    elems.append(PageBreak())
    return elems

def s3_preprocessing_v1():
    elems = []
    elems += section_header(
        "3.  Data Preprocessing (Interpolation-Based Resampling)", "h1", anchor="sec3")
    elems += section_overview(
        "Details the Approach 1 preprocessing pipeline, including the "
        "+ve-dSocdt clipping decision later found to be a limitation."
    )
    elems.append(body(
        "Implemented in <b>battery_analysis.py</b>:"))
    for s in [
        "Parse DateTime (mixed-format UTC) → convert to IST → strip timezone.",
        "Create a clean hourly DatetimeIndex spanning start to end of data.",
        "Apply time-based linear interpolation on Soc and DischargeLevel to fill gaps.",
        "Re-derive dSocdt as the hourly difference of interpolated Soc.",
        "Re-derive categorical columns (dayofweek, dayname, month, monthname).",
        "CLIP all +ve dSocdt values to 0 — charging effect removed before modelling.",
    ]:
        elems.append(bullet(s))
    elems.append(sp(0.3))
    elems.append(warnbox(
        "<b>Key design choice (later found problematic):</b> Positive dSocdt "
        "values were clipped to zero so that only usage/discharge behaviour would "
        "be modelled. This made a true charging hour indistinguishable from a "
        "genuinely idle hour — both appeared as zero in the training target."
    ))
    elems.append(PageBreak())
    return elems

def s4_statistical_v1():
    elems = []
    elems += section_header(
        "4.  Statistical Analysis — Autocorrelation & Hurst Exponent", "h1", anchor="sec4")
    elems += section_overview(
        "Tests whether discharge behaviour has long-range dependence, "
        "justifying a multi-day rolling-window model over simpler alternatives."
    )
    elems.append(body(
        "The key question investigated: does discharge behaviour exhibit "
        "long-range temporal dependence? Pearson autocorrelation of the dSocdt "
        "series was computed at lags 0–504 hours (discharge-only samples); the "
        "Hurst exponent H was estimated per device via Rescaled Range (R/S) analysis."
    ))
    ac_plots = glob_all(os.path.join(PATHS_1["ac_hc_plots"], "autocorr_*.png"))
    if ac_plots:
        elems += insert_image(ac_plots[0], width_cm=15,
            caption_text=f"Figure: Sample autocorrelation plot (device 1 of {len(ac_plots)} analysed)")
    hc_plots = glob_all(os.path.join(PATHS_1["ac_hc_plots"], "hurst_*.png"))
    if hc_plots:
        elems += insert_image(hc_plots[0], width_cm=13,
            caption_text=f"Figure: Sample Hurst exponent R/S plot (device 1 of {len(hc_plots)} analysed)")

    hb = hurst_breakdown(PATHS_1["all_users_summary"])
    if hb:
        n_total, n_pers, n_rand, n_anti, mean_h = hb
        elems.append(results_table(
            ["Regime", "Device Count", "% of Devices"],
            [
                ["Persistent (H > 0.5)",      str(n_pers), f"{100*n_pers/n_total:.1f}%"],
                ["Random walk (H ≈ 0.5)",     str(n_rand), f"{100*n_rand/n_total:.1f}%"],
                ["Anti-persistent (H < 0.5)", str(n_anti), f"{100*n_anti/n_total:.1f}%"],
                ["TOTAL",                     str(n_total), "100.0%"],
            ]))
        elems.append(sp(0.3))
        elems.append(body(
            f"Mean Hurst exponent across all {n_total} devices analysed: "
            f"<b>{mean_h:.3f}</b>. {n_pers} of {n_total} devices ({100*n_pers/n_total:.0f}%) "
            f"show persistent, long-range-dependent discharge behaviour, motivating "
            f"a sequence-aware model with a multi-day feature window over "
            f"pattern-clustering approaches such as SOM."
        ))
    elems.append(PageBreak())
    return elems

def s5_model_v1():
    elems = []
    elems += section_header("5.  XGBoost Model & Hyperparameter Tuning", "h1", anchor="sec5")
    elems += section_overview(
        "Describes the model architecture and the sequential coordinate-wise "
        "tuning of n_estimators, max_depth, learning_rate, and subsample."
    )
    elems.append(body(
        "XGBoost with a MultiOutputRegressor wrapper (one tree per output hour) "
        "was trained using a daily rolling window: each prediction day uses the "
        "preceding 14 actual days as context, flattened into a 728-feature vector "
        "(24 dSocdt + 24 Soc + 4 date features, per day, × 14 days)."
    ))
    elems.append(kv_table([
        ["Training window", "14 days, rolling by 1 day"],
        ["Features/day",    "24 dSocdt + 24 Soc + 4 date = 52"],
        ["Total features",  "14 × 52 = 728"],
        ["Tuning method",   "Sequential coordinate-wise search"],
    ], col_widths=[4 * cm, 11 * cm]))

    param_rows = [
        ("5.1", "n_estimators",  "10–350",              "25",   "58.94%", "val_curve_n_estimators.png"),
        ("5.2", "max_depth",     "2, 3, 4, 5",           "2",    "59.10%", "val_curve_max_depth.png"),
        ("5.3", "learning_rate", "0.01–0.24",            "0.05", "59.10%", "val_curve_learning_rate.png"),
        ("5.4", "subsample",     "0.7–1.0",              "0.95", "59.23%", "val_curve_subsample.png"),
    ]
    for num, pname, prange, pbest, pacc, plotfile in param_rows:
        elems += section_header(f"{num}  {pname}", "h2")
        elems.append(kv_table([
            ["Values tested", prange],
            ["Best value",    pbest],
            ["Best avg accuracy", pacc],
        ], col_widths=[3.5 * cm, 11.5 * cm]))
        elems.append(sp(0.2))
        plot_path = os.path.join(PATHS_1["val_curves"], plotfile)
        elems += insert_image(plot_path, width_cm=14,
            caption_text=f"Figure: Validation curve for {pname} (Approach 1)")

    elems += section_header("Final Selected Hyperparameters (Approach 1)", "h2")
    elems.append(results_table(
        ["Parameter", "Values Tried", "Best Value", "Best Avg Accuracy"],
        [
            ["n_estimators",    "10–350",   "25",   "58.94%"],
            ["max_depth",       "2, 3, 4, 5", "2",  "59.10%"],
            ["learning_rate",   "0.01–0.24", "0.05","59.10%"],
            ["subsample",       "0.7–1.0",   "0.95","59.23%"],
            ["colsample_bytree","fixed",     "0.8", "—"],
        ]))
    elems.append(PageBreak())
    return elems

def s6_final_validation_v1():
    elems = []
    elems += section_header("6.  Final Validation Results", "h1", anchor="sec6")
    elems += section_overview(
        "Reports Approach 1's accuracy-vs-threshold and cosine-similarity "
        "results using the tuned hyperparameters."
    )
    elems.append(body(
        "Final validation was run across all devices with a threshold sweep "
        "(|pred − actual| ≤ T) and cosine similarity between actual and predicted "
        "24-hour dSocdt vectors, using n_estimators=25, max_depth=2, "
        "learning_rate=0.05, subsample=0.95."
    ))
    thresh_csv = os.path.join(PATHS_1["final_validation"], "final_summary_all_thresholds.csv")
    if os.path.exists(thresh_csv):
        tdf = pd.read_csv(thresh_csv)
        overall = tdf.groupby("threshold")["mean_accuracy_%"].mean().reset_index()
        rows = [[f"{t:g}", f"{a:.2f}%"] for t, a in
                zip(overall["threshold"], overall["mean_accuracy_%"])]
        elems.append(results_table(["Accuracy Threshold", "Overall Mean Accuracy"], rows))
        elems.append(sp(0.3))

    tac_plot = os.path.join(PATHS_1["final_validation"], "threshold_accuracy_curve.png")
    elems += insert_image(tac_plot, width_cm=14,
        caption_text="Figure: Overall mean accuracy vs threshold value (Approach 1)")

    cos_plot = os.path.join(PATHS_1["final_validation"], "cosine_similarity_plot.png")
    elems += insert_image(cos_plot, width_cm=14,
        caption_text="Figure: Mean cosine similarity per device (Approach 1)")

    fv_plots = glob_all(os.path.join(PATHS_1["final_validation"], "final_validation_plot_*.png"))
    if fv_plots:
        elems += insert_image(fv_plots[0], width_cm=15,
            caption_text="Figure: Sample device — actual vs predicted dSocdt (Approach 1)")
    elems.append(PageBreak())
    return elems

def s7_feature_importance_v1():
    elems = []
    elems += section_header("7.  Feature Importance Analysis", "h1", anchor="sec7")
    elems += section_overview(
        "Breaks down which feature types (dSocdt / Soc / date) the Approach 1 "
        "model relies on most."
    )
    elems.append(body(
        "XGBoost's built-in feature importance was extracted from the pooled "
        "model, averaged across all 24 hour-estimators."
    ))
    fb = feature_type_breakdown(PATHS_1.get("feature_importance") and
                                os.path.join(PATHS_1["feature_importance"], "feature_importance.csv"))
    if fb:
        elems.append(results_table(
            ["Feature Type", "Total Importance Share"],
            [[k, f"{v:.1f}%"] for k, v in sorted(fb.items(), key=lambda x: -x[1])]))
        elems.append(sp(0.3))
        elems.append(body(
            "dSocdt dominates overwhelmingly (~86%), with Soc contributing a "
            "modest ~11% and date/calendar features contributing a negligible "
            "~2.6%. The model is therefore driven almost entirely by past "
            "discharge <i>rate</i>, not battery level or calendar context."
        ))

    fi_plots = glob_all(os.path.join(PATHS_1["feature_importance"], "*.png"))
    for fp in fi_plots[:3]:
        elems += insert_image(fp, width_cm=14, caption_text=f"Figure: {os.path.basename(fp)}")
    elems.append(PageBreak())
    return elems

def s8_tree_rules_v1():
    elems = []
    elems += section_header("8.  Tree Rule Extraction & Interpretation", "h1", anchor="sec8")
    elems += section_overview(
        "Extracts actual decision-tree split rules to interpret what the "
        "model has learned — recency dominance, key thresholds, and hour clusters."
    )
    elems.append(body(
        "Decision tree rules were extracted via <b>battery_tree_rules.py</b> "
        "using XGBoost's <i>get_booster().get_dump(dump_format='json')</i>, "
        "covering every split condition and leaf value across all trees of all "
        "24 hour-estimators."
    ))
    tree_plots = [
        ("tree_interp_root_features.png",     "Figure: Most frequent root-node split features"),
        ("tree_interp_hour_vs_predictor.png", "Figure: Past-hour vs future-hour root-split heatmap"),
        ("tree_interp_dsocdt_thresholds.png", "Figure: dSocdt split thresholds by hour"),
        ("tree_interp_soc_thresholds.png",    "Figure: SoC threshold distribution"),
        ("tree_interp_recency_dominance.png", "Figure: Split node usage vs days-back"),
    ]
    for fname, cap in tree_plots:
        fpath = os.path.join(PATHS_1["tree_rules"], fname)
        elems += insert_image(fpath, width_cm=14, caption_text=f"{cap} (Approach 1)")
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
    elems.append(PageBreak())
    return elems

def s9_model_complexity_v1():
    elems = []
    elems += section_header("9.  Model Size & Inference Time Analysis", "h1", anchor="sec9")
    elems += section_overview(
        "Assesses deployability by measuring model size and inference time "
        "as training data volume grows."
    )
    elems.append(body(
        "To assess deployability, the trained model's serialised size and "
        "per-sample inference time were measured as a function of the number of "
        "training samples used."
    ))
    elems += insert_image(PATHS_1["model_size"], width_cm=14,
        caption_text="Figure: Model size (KB) vs number of training samples")
    elems += insert_image(PATHS_1["inference_time"], width_cm=14,
        caption_text="Figure: Inference time vs number of training samples")
    elems.append(body(
        "Both model size and inference time remain modest and grow slowly with "
        "the amount of training data, indicating the pipeline is lightweight "
        "enough for practical on-device or edge deployment even as more "
        "historical data accumulates."
    ))
    elems.append(PageBreak())
    return elems

def s10_charging_diagnostic():
    elems = []
    elems += section_header(
        "10.  Charging-Detection Diagnostic (Task A & Task B)", "h1", anchor="sec10")
    elems += section_overview(
        "Diagnostic tests that reveal Approach 1's inverted-signal blind spot "
        "around charging detection — the direct motivation for Part B."
    )
    elems.append(body(
        "Two diagnostic checks were run on the Approach 1 model to test whether "
        "the +ve-dSocdt clipping had hidden weaknesses:"
    ))
    elems.append(bullet(
        "<b>Task A (Discrimination):</b> Does the model's predicted dSocdt for "
        "hours where ground truth was charging (dSocdt = 0) look statistically "
        "different from hours where ground truth was mild discharge?"))
    elems.append(bullet(
        "<b>Task B (Event Detection):</b> Treating |predicted dSocdt| ≤ epsilon "
        "as 'model predicts charging', how well does this match true charging "
        "hours (precision, recall, F1)?"))
    elems.append(sp(0.3))

    elems += insert_image(PATHS_1["charging_discrimination"], width_cm=15,
        caption_text="Figure: Predicted dSocdt — actual-charging vs actual-mild-discharge hours, per device")
    elems.append(body(
        "<b>Finding:</b> For every device tested, mean predicted dSocdt during "
        "actual-charging hours was <i>more negative</i> than during actual-mild-"
        "discharge hours — an <b>inverted signal</b>. The model associates strong "
        "recent discharge momentum with both 'more discharge tomorrow' and, "
        "coincidentally, with hours that turn out to be charging (heavy usage "
        "commonly precedes a user plugging in their device)."
    ))

    elems += insert_image(PATHS_1["charging_detection"], width_cm=15,
        caption_text="Figure: Precision / Recall / F1-score per device (epsilon = 0.5)")
    elems.append(body(
        "<b>Finding:</b> F1-scores for charging event detection ranged from "
        "approximately 0.03 to 0.47 across devices — well below the 0.5 "
        "threshold considered minimally acceptable, and highly inconsistent "
        "between devices."
    ))

    elems += insert_image(PATHS_1["charging_eps_sweep"], width_cm=14,
        caption_text="Figure: F1-score vs epsilon (the 'near-zero' threshold for calling a prediction 'charging')")
    elems.append(body(
        "No choice of epsilon between 0.1 and 2.0 produced consistently strong "
        "F1 scores across devices — this is not a threshold-tuning problem. The "
        "model genuinely lacks the information needed to detect charging events "
        "reliably under Approach 1."
    ))
    elems.append(PageBreak())
    return elems

def s11_limitations():
    elems = []
    elems += section_header("11.  Limitations Identified in Approach 1", "h1", anchor="sec11")
    elems += section_overview(
        "Summarizes Approach 1's root-cause limitation and the decision to "
        "revise the methodology in Part B."
    )
    elems.append(warnbox(
        "<b>Root cause:</b> Clipping +ve dSocdt to 0 destroyed the only "
        "information that could have taught the model to recognise charging as "
        "a distinct event. Making 'charging' and 'idle, no discharge' "
        "indistinguishable in the training target structurally prevented the "
        "model from learning a genuine charging signal."
    ))
    elems.append(bullet(
        "<b>Interpolation manufactured data that never existed.</b> Time-based "
        "linear interpolation filled every missing hourly slot with a plausible "
        "but fabricated value."))
    elems.append(bullet(
        "<b>No explicit charging signal for downstream tasks.</b> Any feature "
        "built on this model (e.g. charging-time recommendations) would inherit "
        "the same blind spot."))
    elems.append(bullet(
        "<b>Standard metrics alone did not reveal the issue.</b> Accuracy/MAE/"
        "cosine-similarity on the clipped dSocdt looked reasonable; the "
        "charging blind spot only became visible via dedicated Task A/B diagnostics."))
    elems.append(sp(0.4))
    elems.append(body(
        "<b>Decision:</b> The methodology was revised — Approach 2 (Part B) "
        "retains +ve dSocdt values and replaces interpolation with an "
        "averaging-based resampling scheme that leaves genuinely missing hours "
        "as NaN rather than fabricating values."
    ))
    elems.append(PageBreak())
    return elems


# ═════════════════════════════════════════════════════════════
# PART B — APPROACH 2
# ═════════════════════════════════════════════════════════════

def part_b_divider():
    elems = []
    elems.append(sp(6))
    elems.append(Paragraph('<a name="partb"/>PART B', S["title"]))
    elems.append(Paragraph("APPROACH 2 — REVISED METHODOLOGY", S["subtitle"]))
    elems.append(sp(0.5))
    elems.append(hr("#2c5282", thickness=2))
    elems.append(sp(1))
    elems.append(body(
        "This part repeats the full pipeline under the revised methodology "
        "motivated by the limitations found in Part A."
    ))
    elems.append(sp(0.3))
    elems += tree_box("Part B structure", [
        "PART B — Approach 2 (Revised Methodology)",
        ("├── 12. Motivation for Methodology Revision", "sec12"),
        ("├── 13. Revised Data Preprocessing (Average-Based Resampling)", "sec13"),
        ("├── 14. Revised Hyperparameter Tuning", "sec14"),
        ("├── 15. Revised Final Validation Results", "sec15"),
        ("├── 16. Revised Feature Importance Analysis", "sec16"),
        ("├── 17. Revised Tree Rule Extraction &amp; Interpretation", "sec17"),
        ("├── 18. Comparison: Approach 1 vs Approach 2", "sec18"),
        ("├── 19. Charging Schedule Prediction (Pooled Model, Walk-Forward Retrain)", "sec19"),
        ("├── 20. Hyperparameter Dump &amp; Sequential Regularization Tuning", "sec20"),
        ("└── 21. Next Steps", "sec21"),
    ])
    elems.append(PageBreak())
    return elems

def s12_motivation():
    elems = []
    elems += section_header("12.  Motivation for Methodology Revision", "h1", anchor="sec12")
    elems += section_overview(
        "Lays out the two core changes in Approach 2: retaining +ve dSocdt "
        "and switching from interpolation to NaN-aware averaging."
    )
    elems.append(bullet(
        "<b>Retain +ve dSocdt values.</b> Charging hours are no longer clipped "
        "to zero, giving the model genuine signed dSocdt information to "
        "distinguish charging, idle, and discharging."))
    elems.append(bullet(
        "<b>Average-based hourly resampling instead of interpolation.</b> For "
        "each target hour H, raw rows in [H−30min, H+30min) are averaged. If "
        "none fall in that window, the hour is left as NaN — XGBoost's native "
        "handling of missing values means no artificial filling is needed."))
    elems.append(sp(0.3))
    elems.append(body(
        "Both changes required corresponding updates throughout the pipeline: "
        "resampling, the wide-CSV pivot, hyperparameter tuning, final "
        "validation, feature importance, and tree rule extraction all needed "
        "NaN-safe handling and removal of the +ve-value clipping step."
    ))
    elems.append(PageBreak())
    return elems

def s13_preprocessing_v2():
    elems = []
    elems += section_header(
        "13.  Revised Data Preprocessing (Average-Based Resampling)", "h1", anchor="sec13")
    elems += section_overview(
        "Explains the ±30-minute averaging resampling scheme and why NaN is "
        "preferred over interpolation for missing hours."
    )
    elems.append(body(
        "Implemented in <b>battery_resample_and_pivot.py</b>:"
    ))
    elems.append(kv_table([
        ["Step 1", "For each date/hour H, average ChargingStatus, Soc, "
                   "DischargeLevel, dSocdt over raw rows in [H−30min, H+30min)."],
        ["No data in window", "Fill entire hour-row with NaN (not interpolated)."],
        ["Step 2",  "Pivot to wide format: dSocdt_h0…h23 | Soc_h0…h23 (48 cols). "
                    "+ve dSocdt retained. Missing hours remain NaN."],
    ], col_widths=[3.2 * cm, 12.8 * cm]))
    elems.append(sp(0.3))
    elems.append(body(
        "<b>Why NaN instead of interpolation:</b> XGBoost's tree-splitting "
        "algorithm learns, during training, which branch to send missing values "
        "down based on which direction minimises loss — using genuinely "
        "observed data rather than inventing values never actually measured."
    ))
    elems.append(PageBreak())
    return elems

def s14_hyperparam_v2():
    elems = []
    elems += section_header("14.  Revised Hyperparameter Tuning", "h1", anchor="sec14")
    elems += section_overview(
        "Repeats the sequential hyperparameter search on the revised, "
        "NaN-aware wide-format data."
    )
    elems.append(body(
        "Sequential coordinate-wise tuning was repeated on the revised wide "
        "CSVs (NaN-aware, +ve dSocdt retained) using <b>battery_hypersearch.py</b>."
    ))
    param_order = [
        ("14.1", "n_estimators",  "10–250",           "200",  "val_curve_n_estimators.png"),
        ("14.2", "max_depth",     "2, 3, 4",          "2",    "val_curve_max_depth.png"),
        ("14.3", "learning_rate", "0.01–0.2",         "0.1",  "val_curve_learning_rate.png"),
        ("14.4", "subsample",     "0.7–0.95",         "0.95", "val_curve_subsample.png"),
    ]
    for num, pname, prange, pbest, plotfile in param_order:
        elems += section_header(f"{num}  {pname}", "h2")
        elems.append(kv_table([
            ["Values tested", prange],
            ["Best value",    pbest],
        ], col_widths=[3.5 * cm, 11.5 * cm]))
        elems.append(sp(0.2))
        plot_path = os.path.join(PATHS_2["val_curves"], plotfile)
        elems += insert_image(plot_path, width_cm=14,
            caption_text=f"Figure: Validation curve for {pname} (Approach 2)")

    elems += section_header("Final Selected Hyperparameters (Approach 2)", "h2")
    elems.append(results_table(
        ["Parameter", "Values Tried", "Best Value", "Best Avg Accuracy"],
        [
            ["n_estimators",    "10–250",   "200",  "68.27%"],
            ["max_depth",       "2, 3, 4",  "2",    "68.27%"],
            ["learning_rate",   "0.01–0.2", "0.1",  "68.49%"],
            ["subsample",       "0.7–0.95", "0.95", "68.78%"],
            ["colsample_bytree","fixed",    "0.8",  "—"],
        ]))
    elems.append(PageBreak())
    return elems

def s15_final_validation_v2():
    elems = []
    elems += section_header("15.  Revised Final Validation Results", "h1", anchor="sec15")
    elems += section_overview(
        "Reports Approach 2's accuracy-vs-threshold and cosine-similarity "
        "results using the newly tuned hyperparameters."
    )
    elems.append(body(
        "Final validation was re-run with n_estimators=200, max_depth=2, "
        "learning_rate=0.1, subsample=0.95, colsample_bytree=0.8 on the "
        "NaN-aware, +ve-dSocdt-retained data. Task A/B charging diagnostics "
        "were removed from this stage since the limitation they detected is "
        "now addressed directly by retaining +ve dSocdt in training."
    ))
    thresh_csv = os.path.join(PATHS_2["final_validation"], "final_summary_all_thresholds.csv")
    if os.path.exists(thresh_csv):
        tdf = pd.read_csv(thresh_csv)
        overall = tdf.groupby("threshold")["mean_accuracy_%"].mean().reset_index()
        rows = [[f"{t:.4f}", f"{a:.2f}%"] for t, a in
                zip(overall["threshold"], overall["mean_accuracy_%"])]
        elems.append(results_table(["Accuracy Threshold", "Overall Mean Accuracy"], rows))
        elems.append(sp(0.3))

    cos_csv = os.path.join(PATHS_2["final_validation"], "cosine_similarity_summary.csv")
    if os.path.exists(cos_csv):
        cdf = pd.read_csv(cos_csv)
        overall_row = cdf[cdf["device"] == "OVERALL_MEAN"]
        if not overall_row.empty:
            elems.append(body(
                f"Overall mean cosine similarity: "
                f"<b>{overall_row['mean_cosine_sim'].values[0]:.4f}</b> over "
                f"{int(overall_row['total_days'].values[0])} device-days. Some "
                f"devices show missing (not zero) cosine similarity where all "
                f"predicted days were entirely NaN in ground truth, preserving "
                f"the distinction between 'poor prediction' and "
                f"'no ground truth available'."
            ))
    elems.append(sp(0.3))

    tac_plot = glob_all(os.path.join(PATHS_2["final_validation"], "*hreshold*ccuracy*.png"))
    if tac_plot:
        elems += insert_image(tac_plot[0], width_cm=14,
            caption_text="Figure: Overall mean accuracy vs threshold value (Approach 2)")
    cos_plot = os.path.join(PATHS_2["final_validation"], "cosine_similarity_plot.png")
    elems += insert_image(cos_plot, width_cm=14,
        caption_text="Figure: Mean cosine similarity per device (Approach 2)")
    fv_plots = glob_all(os.path.join(PATHS_2["final_validation"], "final_validation_plot_*.png"))
    if fv_plots:
        elems += insert_image(fv_plots[0], width_cm=15,
            caption_text="Figure: Sample device — actual vs predicted dSocdt (Approach 2)")
    elems.append(PageBreak())
    return elems

def s16_feature_importance_v2():
    elems = []
    elems += section_header("16.  Revised Feature Importance Analysis", "h1", anchor="sec16")
    elems += section_overview(
        "Compares Approach 2's feature-type balance against Approach 1, "
        "showing SoC becoming materially more informative."
    )
    fb = feature_type_breakdown(os.path.join(PATHS_2["feature_importance"], "feature_importance.csv"))
    if fb:
        elems.append(results_table(
            ["Feature Type", "Total Importance Share"],
            [[k, f"{v:.1f}%"] for k, v in sorted(fb.items(), key=lambda x: -x[1])]))
        elems.append(sp(0.3))
        elems.append(body(
            "Compared to Approach 1 (dSocdt ~86%, Soc ~11%), Approach 2 shows a "
            "more balanced split. With charging information now present in "
            "dSocdt, the model has a richer signal directly, but SoC level also "
            "becomes more informative since it now correlates meaningfully with "
            "imminent or recent charging — a relationship invisible when dSocdt "
            "was clipped."
        ))
    fi_plots = glob_all(os.path.join(PATHS_2["feature_importance"], "*.png"))
    for fp in fi_plots[:3]:
        elems += insert_image(fp, width_cm=14, caption_text=f"Figure: {os.path.basename(fp)}")
    elems.append(PageBreak())
    return elems

def s17_tree_rules_v2():
    elems = []
    elems += section_header(
        "17.  Revised Tree Rule Extraction & Interpretation", "h1", anchor="sec17")
    elems += section_overview(
        "Re-extracts decision rules from the Approach 2 model, highlighting "
        "the new signed dSocdt thresholds and stronger recency dominance."
    )
    elems.append(body(
        "Decision tree rules were re-extracted from the Approach 2 model. "
        "<b>Key structural difference:</b> dSocdt split thresholds can now be "
        "positive or negative. A threshold like <i>'dSocdt_h10 &gt; 0.003'</i> "
        "represents a genuine charging-rate boundary that could not exist under "
        "the clipped Approach 1 data."
    ))
    tree_plots = [
        ("tree_interp_root_features.png",     "Figure: Most frequent root-node split features (Approach 2)"),
        ("tree_interp_hour_vs_predictor.png", "Figure: Past-hour vs future-hour root-split heatmap (Approach 2)"),
        ("tree_interp_dsocdt_thresholds.png", "Figure: dSocdt split thresholds by hour, signed (Approach 2)"),
        ("tree_interp_soc_thresholds.png",    "Figure: SoC threshold distribution (Approach 2)"),
        ("tree_interp_recency_dominance.png", "Figure: Split node usage vs days-back (Approach 2)"),
    ]
    for fname, cap in tree_plots:
        fpath = os.path.join(PATHS_2["tree_rules"], fname)
        elems += insert_image(fpath, width_cm=14, caption_text=cap)

    elems.append(body(
        "<b>Recency dominance — even stronger than Approach 1:</b> 96.0% of all "
        "split conditions rely exclusively on yesterday's data (day-minus-1), "
        "and 99.9% rely on either yesterday or the day before. Essentially none "
        "of the model's decisions draw on data older than 2 days. This is a "
        "sharper concentration on recent history than Approach 1's 73.1% / 90.9% "
        "figures, suggesting that once charging information is available "
        "directly in dSocdt, the model relies even more heavily on the most "
        "immediate past rather than needing older days to compensate for "
        "missing signal."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>Most decisive features (root node analysis):</b> The top 5 "
        "root-split features are: dSocdt_h17_day_minus1 (75 trees), "
        "dSocdt_h20_day_minus1 (66 trees), dSocdt_h4_day_minus1 (50 trees), "
        "Soc_h8_day_minus1 (49 trees), and day_day_minus1 (49 trees). "
        "Evening hours (17:00, 20:00) again dominate as in Approach 1, but a "
        "new pattern emerges: an early-morning hour (04:00) and a mid-morning "
        "SoC feature (08:00) now also appear among the top root splits — signals "
        "that were essentially invisible in Approach 1 because clipping removed "
        "the charging information that gives these hours their predictive value "
        "(a device charging overnight and reaching a certain SoC by 08:00 is now "
        "directly informative)."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>Discharge/charge rate thresholds — now signed:</b> Across all dSocdt "
        "split nodes, 76.6% of thresholds are negative (discharge-side boundaries) "
        "and 22.7% are positive (charging-side boundaries) — a capability that "
        "did not exist in Approach 1, where 100% of thresholds were forced "
        "negative or zero by clipping. Per-hour median thresholds show a clear "
        "day/night pattern: hours 0:00–20:00 all have small negative median "
        "thresholds (roughly -0.0003 to -0.0018), consistent with light-to-moderate "
        "discharge, while hours 21:00–23:00 flip to small <b>positive</b> median "
        "thresholds (+0.0013 to +0.0027) — directly capturing the late-evening "
        "charging pattern that Approach 1 could never represent."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>Feature type balance at the root:</b> Root-node splits are 63.4% "
        "dSocdt, 31.3% Soc, and 5.2% Date — noticeably more balanced than "
        "Approach 1's overwhelming dSocdt dominance. This mirrors the global "
        "feature importance shift reported in Section 16 (dSocdt ~62.5%, Soc "
        "~35.8%) and reinforces that Soc now plays a materially larger role in "
        "the model's earliest, most decisive splits — plausibly because SoC "
        "level is now a more direct proxy for 'has this device recently "
        "finished charging' once dSocdt itself carries charging information."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>SoC thresholds:</b> The median SoC split threshold is 51.0%, close "
        "to the halfway mark, similar in spirit to Approach 1's ~43% threshold. "
        "The most-used SoC features are now Soc_h21, Soc_h22, Soc_h8, Soc_h0, and "
        "Soc_h23 (all from day-minus-1) — a cluster of late-evening and midnight "
        "hours plus one mid-morning hour, suggesting the model uses SoC "
        "specifically around the hours when charging is most likely to begin or "
        "end."
    ))
    elems.append(sp(0.2))
    elems.append(PageBreak())
    return elems

def s18_comparison():
    elems = []
    elems += section_header("18.  Comparison: Approach 1 vs Approach 2", "h1", anchor="sec18")
    elems += section_overview(
        "Side-by-side summary table contrasting the two approaches across "
        "every dimension covered in Parts A and B."
    )
    elems.append(results_table(
        ["Aspect", "Approach 1", "Approach 2"],
        [
            ["+ve dSocdt handling",  "Clipped to 0",                    "Retained as-is"],
            ["Resampling method",    "Time-based linear interpolation", "Average within ±30 min window"],
            ["Missing hours",        "Filled by interpolation",         "Left as NaN, handled natively"],
            ["dSocdt importance",    "~86.3%",                          "~62.5%"],
            ["Soc importance",       "~10.9%",                          "~35.8%"],
            ["Date importance",      "~2.6%",                           "~1.7%"],
            ["Charging detection",   "F1 = 0.03–0.47 (poor)",           "Native — charging is part of dSocdt"],
            ["Best hyperparameters", "n_est=25, depth=2, lr=0.05, sub=0.95",
                                     "n_est=200, depth=2, lr=0.1, sub=0.95"],
        ]))
    elems.append(sp(0.4))
    elems.append(body(
        "<b>Overall assessment:</b> Approach 2 directly addresses the "
        "structural blind spot found in Approach 1, giving the model genuine "
        "access to charging information rather than forcing it to infer "
        "charging indirectly through correlated discharge patterns. The more "
        "balanced feature importance split between dSocdt and Soc in Approach 2 "
        "is itself evidence of a richer, more physically grounded model of "
        "battery behaviour."
    ))
    elems.append(PageBreak())
    return elems

def s19_charging_schedule():
    elems = []
    elems += section_header(
        "19.  Charging Schedule Prediction (Pooled Model, Walk-Forward Retrain)", "h1", anchor="sec19")
    elems += section_overview(
        "Introduces the second use case (predicting the daily charging hour), "
        "the two-stage classifier design, and the walk-forward retrain protocol "
        "that reduced MAE from ~7.5–9.5 hrs to ~3.0 hrs."
    )
    elems.append(body(
        "Beyond predicting the full 24-hour dSocdt curve, a downstream task was "
        "built on top of the Approach 2 model: predicting the single hour of the "
        "day when the device's main charging event occurs, so that charging-time "
        "recommendations can be generated. This is implemented in "
        "<b>xgboost_charging_schedule.py</b>."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>Ground-truth labeling.</b> For each day, the actual charging hour is "
        "found by scanning the day's dSocdt vector for contiguous rising runs "
        "above a minimum-rise noise floor (dSocdt &gt; 0.0095), and taking the "
        "rise-weighted hour of whichever run has the largest total rise. A day "
        "with no such run is labeled a no-event day."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>Two-stage classifier.</b> Rather than regressing all 24 hourly "
        "dSocdt values and thresholding the prediction to find a peak — which "
        "plateaued around 7.5–9.5 hrs MAE across several earlier attempts — the "
        "task is split into two XGBoost classifiers: <b>Stage 1</b> predicts "
        "whether a charging event happens at all that day (binary), and "
        "<b>Stage 2</b>, trained only on days Stage 1 identifies as event days, "
        "predicts which 4-hour bucket (6 buckets covering the 24-hour day) the "
        "event falls into. The predicted bucket's center hour is used as the "
        "final predicted charging hour."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>Pooled per-device features.</b> Each day is represented by 12 "
        "compact, causally-computed features rather than a raw multi-day block: "
        "calendar (day-of-week, day, month, year), recency (days since the last "
        "charging event, and that event's hour), rolling dSocdt behaviour "
        "(3-day and 7-day rolling mean/std of the day's strongest hourly rise), "
        "habit (mean hour of the last 10 charging events seen), and battery "
        "state (yesterday's minimum and end-of-day SoC)."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>Walk-forward rolling retrain.</b> Rather than a single train/test "
        "split, the model is retrained every 7 days on a fixed-size rolling "
        "window of the most recent 60 days of history, then used to predict the "
        "next 7 days, then retrained again on the next 60-day window — "
        "simulating how the model would behave in an actual deployment, where "
        "the timeline keeps moving forward and the training window ages out "
        "old days as new ones arrive, rather than assuming a fixed, known total "
        "day count."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>Calibrated event threshold.</b> Instead of a fixed 0.5 cutoff on "
        "Stage 1's predicted event-probability, the decision threshold is "
        "calibrated separately for each rolling window by sweeping candidate "
        "thresholds against that window's own training labels (no test data "
        "involved) and selecting whichever maximizes F1 for the event class. "
        "This corrects for devices with a naturally low or high event rate, "
        "which under a fixed threshold defaulted to always predicting no-event."
    ))
    elems.append(sp(0.3))

    summary_csv = os.path.join(PATHS_2["charging_schedule"], "charging_schedule_summary.csv")
    if os.path.exists(summary_csv):
        sdf = pd.read_csv(summary_csv)
        rows = [[str(r["device"])[:28], str(r["total_days"]), str(r["matched_pairs"]),
                 f"{r['mae_hours']:.2f} hrs" if pd.notna(r["mae_hours"]) else "N/A"]
                for _, r in sdf.iterrows()]
        elems.append(results_table(
            ["Device", "Predicted Days", "Matched Pairs", "MAE (hours)"], rows))
        elems.append(sp(0.3))

    mae_plot = os.path.join(PATHS_2["charging_schedule"], "charging_schedule_mae_plot.png")
    elems += insert_image(mae_plot, width_cm=14,
        caption_text="Figure: MAE per device — charging schedule prediction (walk-forward, pooled model)")

    sample_plots = glob_all(os.path.join(PATHS_2["charging_schedule"], "charging_schedule_sample_days_*.png"))
    if sample_plots:
        elems += insert_image(sample_plots[0], width_cm=15,
            caption_text="Figure: Sample device — actual dSocdt vs actual/predicted charging peak, held-out days")

    elems.append(body(
        "<b>Result:</b> The pooled walk-forward approach reduced overall MAE to "
        "approximately 3.0 hours, a substantial improvement over the ~7.5–9.5 "
        "hr range seen with per-day-retrained models trained on only the "
        "preceding 13–14 days. Some devices with very few total days of history "
        "still show no matched day-pairs, reflecting genuine data scarcity for "
        "those devices rather than a model or threshold issue."
    ))
    elems.append(PageBreak())
    return elems


def s20_hyperparam_tuning():
    elems = []
    elems += section_header(
        "20.  Hyperparameter Dump & Sequential Regularization Tuning", "h1", anchor="sec20")
    elems += section_overview(
        "Extends both the trajectory-projection model (Section 15) and the "
        "charging-schedule model (Section 19) with a second round of tuning, "
        "targeting regularization parameters that were left at their XGBoost "
        "defaults in the original hyperparameter search."
    )
    elems.append(body(
        "The hyperparameter values selected in Sections 5 and 14 covered only "
        "<i>n_estimators</i>, <i>max_depth</i>, <i>learning_rate</i>, and "
        "<i>subsample</i>. To check whether further gains were available, the "
        "full effective configuration of each trained XGBoost model was "
        "dumped via <b>booster.save_config()</b>, which returns every "
        "parameter the model actually used — including defaults that were "
        "never explicitly set. Comparing this dump against the tuned "
        "parameters showed five regularization-related parameters still "
        "sitting at their untouched defaults: <b>reg_lambda</b> (L2), "
        "<b>reg_alpha</b> (L1), <b>min_split_loss</b> (gamma), "
        "<b>min_child_weight</b>, and <b>colsample_bytree</b>."
    ))
    elems.append(sp(0.2))
    elems.append(body(
        "<b>Method.</b> Each of the five parameters was swept one at a time "
        "using the same sequential coordinate-wise approach as the original "
        "hyperparameter search (Sections 5 and 14): sweep one parameter "
        "across a candidate range with everything else held fixed, pick the "
        "best value, fix it, then move to the next parameter. The trajectory "
        "model was evaluated by mean cosine similarity across all devices; "
        "the charging-schedule model was evaluated by overall MAE (hours) "
        "across all devices, run through its full walk-forward simulation "
        "for every candidate value."
    ))
    elems.append(sp(0.3))

    elems += section_header("20.1  Trajectory Projection — Tuning Results", "h2")
    elems.append(body(
        "Sweeping reg_lambda produced the largest single gain, improving "
        "mean cosine similarity meaningfully; the remaining four parameters "
        "(reg_alpha, min_split_loss, min_child_weight, colsample_bytree) "
        "showed no measurable change across their tested ranges once "
        "reg_lambda was fixed, and were therefore left at their default "
        "values."
    ))
    elems.append(results_table(
        ["Parameter", "Tested Range", "Selected Value"],
        [
            ["reg_lambda",       "0, 0.1, 0.5, 1, 2, 5, 10", "10"],
            ["reg_alpha",        "0, 0.1, 0.5, 1, 2, 5",     "0.1 (default retained)"],
            ["min_split_loss",   "0, 0.1, 0.5, 1, 2, 5",     "0.1 (default retained)"],
            ["min_child_weight", "1, 3, 5, 7, 10",           "1 (default retained)"],
            ["colsample_bytree", "0.4–1.0",                  "0.8 (unchanged)"],
        ]))
    elems.append(sp(0.3))
    elems.append(body(
        "<b>Result:</b> Overall accuracy at the standard 0.003 threshold "
        "improved from <b>80%</b> to <b>84.3%</b> after applying the tuned "
        "reg_lambda value on top of the Section 15 hyperparameters."
    ))
    elems.append(sp(0.3))

    elems += section_header("20.2  Charging Schedule Prediction — Tuning Results", "h2")
    elems.append(body(
        "The same five-parameter sweep was repeated on the charging-schedule "
        "model (Section 19), applying each candidate identically to both the "
        "Stage 1 event classifier and the Stage 2 bucket classifier, with the "
        "full walk-forward retrain simulation re-run per candidate value."
    ))
    elems.append(results_table(
        ["Parameter", "Applied To", "Selected Value"],
        [
            ["reg_lambda",       "Stage 1 &amp; Stage 2", "Tuned"],
            ["reg_alpha",        "Stage 1 &amp; Stage 2", "Tuned"],
            ["min_split_loss",   "Stage 1 &amp; Stage 2", "Tuned"],
            ["min_child_weight", "Stage 1 &amp; Stage 2", "Tuned"],
        ]))
    elems.append(sp(0.3))
    elems.append(body(
        "<b>Result:</b> Overall MAE for charging-hour prediction improved "
        "from the ~3.0 hr walk-forward baseline (Section 19) to "
        "<b>2.12 hours</b> after applying the tuned regularization values."
    ))
    elems.append(sp(0.3))

    elems += section_header("20.3  Summary", "h2")
    elems.append(results_table(
        ["Use Case", "Metric", "Before Tuning", "After Tuning"],
        [
            ["Trajectory Projection",  "Accuracy @ 0.003 threshold", "80%",    "84.3%"],
            ["Charging Schedule",      "MAE (hours)",                "~3.0 hrs", "2.12 hrs"],
        ]))
    elems.append(sp(0.3))
    elems.append(body(
        "<b>Overall assessment:</b> Regularization tuning — specifically "
        "reg_lambda — was the parameter with the most impact for both use "
        "cases, consistent with the small per-window training-sample counts "
        "used throughout this project (~13 samples for trajectory windows, "
        "~13–50 samples per charging-schedule retrain window), where "
        "controlling overfitting matters more than further adjusting split "
        "or sampling behaviour."
    ))
    elems.append(PageBreak())
    return elems


def s21_next_steps():
    elems = []
    elems += section_header("21.  Next Steps", "h1", anchor="sec21")
    for item in [
        " ",
    ]:
        elems.append(bullet(item))
    elems.append(sp(1))
    elems.append(hr())
    elems.append(Paragraph(
        "<i>This report was auto-generated by generate_report.py. "
        "Re-run at any time to refresh with the latest plots and results.</i>",
        S["caption"]))
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

    story += part_a_divider()
    story += s1_overview()
    story += s2_dataset()
    story += s3_preprocessing_v1()
    story += s4_statistical_v1()
    story += s5_model_v1()
    story += s6_final_validation_v1()
    story += s7_feature_importance_v1()
    story += s8_tree_rules_v1()
    story += s9_model_complexity_v1()
    story += s10_charging_diagnostic()
    story += s11_limitations()

    story += part_b_divider()
    story += s12_motivation()
    story += s13_preprocessing_v2()
    story += s14_hyperparam_v2()
    story += s15_final_validation_v2()
    story += s16_feature_importance_v2()
    story += s17_tree_rules_v2()
    story += s18_comparison()
    story += s19_charging_schedule()
    story += s20_hyperparam_tuning()
    story += s21_next_steps()

    doc.build(story)
    print(f"\nReport generated:  {OUTPUT_PDF}")


if __name__ == "__main__":
    os.makedirs(R2, exist_ok=True)
    build_pdf()
