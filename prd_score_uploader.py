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

def generate_pdf(data, filename):
    overall_avg = data['Total Score'].mean()

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt="PRD Rating Report", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Overall Average Score: {overall_avg:.2f}", ln=True, align='C')
    pdf.ln(10)

    # Summary Section: List of PRDs with average scores
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(200, 10, txt="Summary of PRD Average Scores", ln=True)
    summary = data.groupby('PRD Name')['Total Score'].mean().reset_index()
    for _, row in summary.iterrows():
        pdf.set_font("Arial", size=11)
        pdf.cell(200, 8, txt=f"{row['PRD Name']}: {row['Total Score']:.2f}", ln=True)

    pdf.add_page()
    for prd_name, group in data.groupby('PRD Name'):
        pdf.set_font("Arial", style='B', size=12)
        pdf.cell(200, 10, txt=f"PRD: {prd_name}", ln=True)
        pdf.set_font("Arial", size=10)

        col_names = ['Role'] + list(weights.keys()) + ['Total Score']

        header_line = ' | '.join(['Rating'] + list(weights.keys()) + ['Total Score'])
        pdf.multi_cell(0, 10, header_line)

        for idx, (_, row) in enumerate(group.iterrows()):
            row_values = [f"Rating {idx+1}"] + [str(row.get(col, '')) for col in list(weights.keys()) + ['Total Score']]
            row_line = ' | '.join(row_values)
            pdf.multi_cell(0, 10, row_line)

        pdf.ln(5)

    pdf.output(filename)

# Streamlit App
st.set_page_config(page_title="PRD Rating Report Generator")

logo = Image.open("logo.png")
with st.container():
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.image(logo, width=150)
    st.markdown("</div>", unsafe_allow_html=True)

st.title("\U0001F4CA PRD Rating Report Generator")
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
    result_df = result_df[['PRD Name', 'Role'] + [col for col in result_df.columns if col not in ['PRD Name', 'Role']]]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        generate_pdf(result_df, tmp.name)

        with open(tmp.name, "rb") as f:
            st.download_button(
                label="\U0001F4C4 Download PDF Report",
                data=f,
                file_name="prd_report.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        os.unlink(tmp.name)

    # New summary section at the top in Streamlit
    st.subheader("\U0001F4CA Summary of PRD Scores")
    prd_summary = result_df.groupby("PRD Name")["Total Score"].mean().reset_index()
    prd_summary.columns = ["PRD Name", "Average Score"]
    st.dataframe(prd_summary)

    st.subheader("\U0001F50D Converted Score Table")
    st.dataframe(result_df)
