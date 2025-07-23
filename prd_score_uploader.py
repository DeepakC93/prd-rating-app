import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os

# Canonical parameter aliases to standardize header names
canonical_params = {
    "scope": "Scope",
    "design ready": "Design Ready",
    "prd handover": "PRD Handover",
    "requirement changes post handover": "Req. changes",
    "completeness of requirement coverage": "Coverage",
    "depth of tech understanding delivered": "Tech depth",
    "prd name": "PRD Name",
    "role": "Role",
}

# Mapping for textual ratings to numeric scores
score_map = {
    "Scope": {"not covered": 0, "partially covered": 0.5, "fully covered": 1},
    "Design Ready": {"not covered": 0, "partially covered": 0.5, "fully covered": 1.5},
    "PRD Handover": {"no": 0, "yes": 1.5},
    "Req. changes": {"changed n time": 0, "changed 1 time": 0.5, "no changes": 2},
    "Coverage": {"not covered": 0, "partially covered": 0.5, "fully covered": 2},
    "Tech depth": {"not covered": 0, "partially covered": 0.5, "fully covered": 2},
}

# Weights of each parameter
weights = {
    "Scope": 1,
    "Design Ready": 1.5,
    "PRD Handover": 1.5,
    "Req. changes": 2,
    "Coverage": 2,
    "Tech depth": 2,
}

def convert_to_score(row):
    scores = {}
    total_score = 0
    total_weight = 0

    for param_key in weights:
        val = row.get(param_key, '')
        val_normalized = str(val).strip().lower()

        if val_normalized == "not applicable":
            scores[param_key] = "N/A"
            continue

        mapped = score_map.get(param_key, {}).get(val_normalized, 0)
        scores[param_key] = mapped
        total_score += mapped
        total_weight += weights[param_key]

    normalized_total = round(total_score * 10 / total_weight, 2) if total_weight else 0
    return scores, normalized_total

def _sanitize_text(text):
    return str(text).encode("latin-1", "ignore").decode("latin-1")

def get_color(score):
    if score >= 9:
        return (0, 200, 0)  # Green
    elif score >= 6:
        return (255, 165, 0)  # Orange
    else:
        return (255, 0, 0)  # Red

def generate_pdf(data, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=10)

    col_names = [col for col in d]()_
