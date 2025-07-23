import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os

# Mapping for textual ratings to numeric scores
score_map = {
    "Scope": {"Not covered": 0, "Partially covered": 0.5, "Fully covered": 1},
    "Design Ready": {"Not covered": 0, "Partially covered": 0.5, "Fully covered": 1.5},
    "PRD Handover": {"No": 0, "Yes": 1.5},
    "Requirement changes post handover": {"Changed N Time": 0, "Changed 1 Time": 0.5, "No changes": 2},
    "Completeness of Requirement Coverage": {"Not covered": 0, "Partially covered": 0.5, "Fully covered": 2},
    "Depth of tech Understanding Delivered": {"Not covered": 0, "Partially covered": 0.5, "Fully covered": 2},
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
    for key in weights:
        val = row.get(key, '')
        mapped = score_map[key].get(str(val).strip(), 0)
        scores[key] = mapped
    total = sum(scores.values())
    return scores, total

def generate_pdf(data, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 8, txt=self._sanitize_text(text), ln=True)
    pdf.ln(10)

    for prd, group in data.groupby('PRD Name'):
        pdf.set_font("Arial", style='B', size=12)
        pdf.cell(200, 10, txt=_sanitize_text(f"PRD: {prd}"), ln=True) 
        pdf.set_font("Arial", size=10)
        for _, row in group.iterrows():
            pdf.cell(200, 8, txt=_sanitize_text(f"- Role: {row['Role']}, Score: {row['Total Score']:.1f}"), ln=True)
        avg = group['Total Score'].mean()
        pdf.cell(200, 8, txt=_sanitize_text(f"→ Avg Score: {avg:.2f}"), ln=True)
        pdf.ln(5)

    def _sanitize_text(text):
    return str(text).encode("latin-1", "replace").decode("latin-1")

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

    st.success("File uploaded successfully!")

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
            label="📥 Download PDF Report",
            data=open(tmp.name, "rb").read(),
            file_name="prd_report.pdf",
            mime="application/pdf"
        )
        os.unlink(tmp.name)
