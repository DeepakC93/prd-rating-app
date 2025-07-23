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
    "requirement changes post handover": "Requirement changes post handover",
    "completeness of requirement coverage": "Completeness of Requirement Coverage",
    "depth of tech understanding delivered": "Depth of tech Understanding Delivered",
    "prd name": "PRD Name",
    "role": "Role",
}

# Mapping for textual ratings to numeric scores
score_map = {
    "Scope": {"not covered": 0, "partially covered": 0.5, "fully covered": 1},
    "Design Ready": {"not covered": 0, "partially covered": 0.5, "fully covered": 1.5},
    "PRD Handover": {"no": 0, "yes": 1.5},
    "Requirement changes post handover": {"changed n time": 0, "changed 1 time": 0.5, "no changes": 2},
    "Completeness of Requirement Coverage": {"not covered": 0, "partially covered": 0.5, "fully covered": 2},
    "Depth of tech Understanding Delivered": {"not covered": 0, "partially covered": 0.5, "fully covered": 2},
}

# Weights of each parameter
weights = {
    "Scope": 1,
    "Design Ready": 1.5,
    "PRD Handover": 1.5,
    "Requirement changes post handover": 2,
    "Completeness of Requirement Coverage": 2,
    "Depth of tech Understanding Delivered": 2,
}

def convert_to_score(row):
    scores = {}
    for param_key in weights:
        val = row.get(param_key, '')
        val_normalized = str(val).strip().lower()
        options = score_map.get(param_key, {})
        mapped = options.get(val_normalized, 0)
        scores[param_key] = mapped
    total = sum(scores.values())
    return scores, total

def _sanitize_text(text):
    return str(text).encode("latin-1", "replace").decode("latin-1")

def generate_pdf(data, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=_sanitize_text("PRD Rating Report"), ln=True, align='C')
    pdf.ln(10)

    for prd, group in data.groupby('PRD Name'):
        avg = group['Total Score'].mean()
        color = "🟢" if avg >= 9 else "🟠" if avg >= 6 else "🔴"
        pdf.set_font("Arial", style='B', size=12)
        pdf.cell(200, 10, txt=_sanitize_text(f"{color} PRD: {prd}"), ln=True)
        pdf.set_font("Arial", size=10)
        for _, row in group.iterrows():
            pdf.cell(200, 8, txt=_sanitize_text(f"- Role: {row['Role']}, Score: {row['Total Score']:.1f}"), ln=True)
        pdf.cell(200, 8, txt=_sanitize_text(f"→ Avg Score: {avg:.2f}"), ln=True)
        pdf.ln(5)

    pdf.output(filename)

# Streamlit App
st.set_page_config(page_title="PRD Rating Report Generator")
st.title("📊 PRD Rating Report Generator")
st.markdown("Upload the PRD score sheet (CSV or Excel) and get the report in PDF format.")

uploaded_file = st.file_uploader("Upload PRD Rating Sheet", type=["csv", "xlsx"])

if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip().str.lower()

    # Rename uploaded columns to canonical names
    rename_dict = {}
    for col in df.columns:
        for alias, canon in canonical_params.items():
            if alias in col:
                rename_dict[col] = canon
                break

    df.rename(columns=rename_dict, inplace=True)

    # Normalize relevant scoring cells
    for canon in weights.keys():
        if canon in df.columns:
            df[canon] = df[canon].astype(str).str.strip().str.lower()

    # Normalize PRD Name and Role columns too
    if 'PRD Name' in df.columns:
        df['PRD Name'] = df['PRD Name'].astype(str).str.strip()
    else:
        df['PRD Name'] = [f"PRD-{i+1}" for i in range(len(df))]

    if 'Role' in df.columns:
        df['Role'] = df['Role'].astype(str).str.strip()
    else:
        df['Role'] = 'Unknown'

    st.success("File uploaded and normalized!")

    # Convert scores
    all_scores = []
    for idx, row in df.iterrows():
        scores, total = convert_to_score(row)
        scores['PRD Name'] = row.get('PRD Name', f"PRD-{idx+1}")
        scores['Role'] = row.get('Role', 'Unknown')
        scores['Total Score'] = total
        all_scores.append(scores)

    result_df = pd.DataFrame(all_scores)
    st.subheader("🔍 Converted Score Table")
    st.dataframe(result_df)

    # Generate PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        generate_pdf(result_df, tmp.name)
        st.download_button(
            label="📅 Download PDF Report",
            data=open(tmp.name, "rb").read(),
            file_name="prd_report.pdf",
            mime="application/pdf"
        )
        os.unlink(tmp.name)
