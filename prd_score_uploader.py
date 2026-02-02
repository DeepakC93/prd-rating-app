import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os
from PIL import Image

# Canonical parameter aliases
canonical_params = {
    "scope": "Scope",
    "design ready": "Design Ready",
    "prd handover": "PRD Handover",
    "requirement changes post handover": "Req. changes",
    "completeness of requirement coverage": "Coverage",
    "depth of tech understanding delivered": "Tech depth",
    "prd name": "PRD Name",
    "role": "Role",
    "comments": "Comments"
}

# Mapping textual ratings to numeric scores
score_map = {
    "Scope": {"not covered": 0, "partially covered": 0.5, "fully covered": 1},
    "Design Ready": {"not covered": 0, "partially covered": 0.5, "fully covered": 1.5},
    "PRD Handover": {"no": 0, "yes": 1.5},
    "Req. changes": {"changed n time": 0, "changed 1 time": 0.5, "no changes": 2},
    "Coverage": {"not covered": 0, "partially covered": 0.5, "fully covered": 2},
    "Tech depth": {"not covered": 0, "partially covered": 0.5, "fully covered": 2},
}

# Parameter weights
weights = {
    "Scope": 1,
    "Design Ready": 1.5,
    "PRD Handover": 1.5,
    "Req. changes": 2,
    "Coverage": 2,
    "Tech depth": 2,
}

param_max = {k: max(score_map[k].values()) for k in weights.keys()}

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
        scores[param_key] = f"{val.title()} ({mapped})"
        total_score += mapped
        total_weight += weights[param_key]
    normalized_total = round(total_score * 10 / total_weight, 2) if total_weight else 0
    return scores, normalized_total

def get_color_by_score(score):
    if score >= 8:
        return (144, 238, 144)
    elif 6 <= score < 8:
        return (255, 165, 0)
    else:
        return (255, 99, 71)

def _s(text):
    return str(text).encode("latin-1", "ignore").decode("latin-1")

def _avg_numeric_from_display(series):
    s = series.astype(str).str.extract(r'([\d.]+)')[0]
    return pd.to_numeric(s, errors='coerce').mean()

def _lowest_params_by_impact(group, top_k=3):
    scores = []
    for p in weights.keys():
        avg_val = _avg_numeric_from_display(group[p]) or 0
        ratio = avg_val / (param_max.get(p, 1) or 1)
        scores.append((p, ratio))
    scores.sort(key=lambda x: x[1])
    return [p for p, _ in scores[:top_k]]

def generate_pdf(data, filename):
    overall_avg = data['Total Score'].mean()
    color = get_color_by_score(overall_avg)

    pdf = FPDF()
    pdf.add_page()

    if os.path.exists("Combo.png"):
        pdf.image("Combo.png", x=10, y=10, w=30)

    pdf.set_xy(10, 20)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, _s("PRD Rating Report"), ln=True, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(*color)
    pdf.cell(0, 10, _s(f"Overall Average Score: {overall_avg:.2f}"), ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    prd_order = data.groupby("PRD Name")["Total Score"].mean().sort_values().index

    for prd in prd_order:
        group = data[data["PRD Name"] == prd]

        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(0, 10, _s(f"PRD: {prd}"), ln=True, fill=True)

        avg_score = group["Total Score"].mean()
        if avg_score < 8:
            weak = ", ".join(_lowest_params_by_impact(group))
            pdf.set_font("Arial", "I", 9)
            pdf.set_text_color(255, 0, 0)
            pdf.multi_cell(
                0, 6,
                _s(
                    f"Note: This PRD averaged {avg_score:.2f}. "
                    f"Improving {weak} can significantly boost the score."
                )
            )
            pdf.set_text_color(0, 0, 0)

        # 🔹 CHANGED: Role REMOVED from PDF
        col_names = list(weights.keys()) + ["Total Score"]
        col_width = 195 / len(col_names)

        pdf.set_font("Arial", "B", 8.5)
        pdf.set_fill_color(180, 200, 255)
        for col in col_names:
            pdf.cell(col_width, 8, _s(col), border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_font("Arial", size=6)
        fill = False
        for _, row in group.iterrows():
            for col in col_names:
                pdf.cell(col_width, 8, _s(row[col]), border=1, align="C", fill=fill)
            pdf.ln()
            fill = not fill

        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(220, 220, 250)
        pdf.cell(col_width, 8, _s("Average"), border=1, fill=True)

        for col in col_names[1:]:
            avg_val = _avg_numeric_from_display(group[col])
            if col == "Total Score":
                pdf.set_fill_color(*get_color_by_score(avg_val))
            else:
                pdf.set_fill_color(240, 240, 255)
            pdf.cell(col_width, 8, _s(f"{avg_val:.2f}"), border=1, fill=True)

        pdf.ln(6)

        comments = group["Comments"].dropna().unique()
        if len(comments):
            pdf.set_font("Arial", "B", 9)
            pdf.set_fill_color(255, 250, 205)
            pdf.cell(0, 7, _s("Reviewer Comments"), ln=True, fill=True)
            pdf.set_font("Arial", 8)
            for c in comments:
                pdf.multi_cell(0, 5, _s(f"- {c}"))

        pdf.ln(8)

    pdf.output(filename)

# ---------------- Streamlit App ----------------

st.set_page_config(page_title="PRD Rating Report Generator")

with st.container():
    col1, col2, col3 = st.columns([1, 6, 1])
    if os.path.exists("Combo.png"):
        with col1:
            st.image(Image.open("Combo.png"), width=240)

st.title("📊 PRD Rating Report Generator")
st.markdown("Upload the PRD score sheet (CSV or Excel) and get the report in PDF format.")

uploaded_file = st.file_uploader("Upload PRD Rating Sheet", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip().str.lower()
    df.rename(columns={k: v for k, v in canonical_params.items() if k in df.columns}, inplace=True)

    all_scores = []
    for _, row in df.iterrows():
        scores, total = convert_to_score(row)
        scores.update({
            "PRD Name": row.get("PRD Name"),
            "Role": row.get("Role"),
            "Total Score": total,
            "Comments": row.get("Comments", "")
        })
        all_scores.append(scores)

    result_df = pd.DataFrame(all_scores)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        generate_pdf(result_df, tmp.name)
        with open(tmp.name, "rb") as f:
            st.download_button("📄 Download PDF Report", f, "prd_report.pdf", "application/pdf")
        os.unlink(tmp.name)

    st.dataframe(result_df)
