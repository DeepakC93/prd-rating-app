import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os
from PIL import Image

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

    col_names = [col for col in data.columns if col != 'PRD Name']
    col_widths = [pdf.get_string_width(col) + 10 for col in col_names]
    col_widths = [max(w, 25) for w in col_widths]

    line_height = 8
    max_width = sum(col_widths)
    page_width = pdf.w - 2 * pdf.l_margin
    scale = page_width / max_width
    col_widths = [w * scale for w in col_widths]

    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", style="B", size=10)
    for i, col in enumerate(col_names):
        pdf.cell(col_widths[i], line_height, _sanitize_text(col), border=1, align='C', fill=True)
    pdf.ln(line_height)
    pdf.set_font("Arial", style="", size=10)

    for _, row in data.iterrows():
        for i, col in enumerate(col_names):
            val = row[col]
            if col == "Total Score":
                if isinstance(val, (int, float)):
                    r, g, b = get_color(val)
                    pdf.set_fill_color(r, g, b)
                else:
                    pdf.set_fill_color(255, 255, 255)
            else:
                pdf.set_fill_color(255, 255, 255)

            text = str(val)
            pdf.cell(col_widths[i], line_height, _sanitize_text(text), border=1, align='C', fill=True)
        pdf.ln(line_height)

    pdf.output(filename)

# Streamlit App
st.set_page_config(page_title="PRD Rating Report Generator")

# Centered and resized logo display
logo = Image.open("logo.png")
logo.thumbnail((60, 60))
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(logo, use_container_width=True)

st.title("📊 PRD Rating Report Generator")
st.markdown("Upload the PRD score sheet (CSV or Excel) and get the report in PDF format.")

uploaded_file = st.file_uploader("Upload PRD Rating Sheet", type=["csv", "xlsx"])

if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip().str.lower()

    rename_dict = {}
    for col in df.columns:
        for alias, canon in canonical_params.items():
            if alias in col:
                rename_dict[col] = canon
                break

    df.rename(columns=rename_dict, inplace=True)

    for canon in weights.keys():
        if canon in df.columns:
            df[canon] = df[canon].astype(str).str.strip().str.lower()

    if 'PRD Name' in df.columns:
        df['PRD Name'] = df['PRD Name'].astype(str).str.strip()
    else:
        df['PRD Name'] = [f"PRD-{i+1}" for i in range(len(df))]

    if 'Role' in df.columns:
        df['Role'] = df['Role'].astype(str).str.strip()
    else:
        df['Role'] = 'Unknown'

    st.success("File uploaded and normalized!")

    all_scores = []
    for idx, row in df.iterrows():
        scores, total = convert_to_score(row)
        scores['PRD Name'] = row.get('PRD Name', f"PRD-{idx+1}")
        scores['Role'] = row.get('Role', 'Unknown')
        scores['Total Score'] = total
        all_scores.append(scores)

    result_df = pd.DataFrame(all_scores)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        generate_pdf(result_df, tmp.name)
        st.markdown("### 📥 Download Your Report")
        st.download_button(
            label="📅 Download PDF Report",
            data=open(tmp.name, "rb").read(),
            file_name="prd_report.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="download-btn"
        )
        os.unlink(tmp.name)

    st.subheader("🔍 Converted Score Table")
    display_df = result_df[['PRD Name', 'Role'] + [col for col in result_df.columns if col not in ['PRD Name', 'Role']]]
    st.dataframe(display_df)
