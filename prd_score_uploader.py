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
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=18)
    pdf.cell(0, 12, txt=_sanitize_text("PRD Rating Report"), ln=True, align='C')

    overall_avg = data['Total Score'].mean()
    pdf.ln(5)
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, txt=f"Overall Average Score Across All PRDs: {overall_avg:.2f}", ln=True, align='C')

    image_path = None
    if overall_avg >= 9:
        image_path = "mood_images/happy.png"
    elif overall_avg >= 6:
        image_path = "mood_images/meh.png"
    else:
        image_path = "mood_images/sad.png"

    if image_path and os.path.exists(image_path):
        pdf.image(image_path, x=130, y=35, w=30)  # Centered and slightly larger

    pdf.ln(30)
    pdf.set_font("Arial", style='B', size=11)
    table_headers = ['Role'] + list(weights.keys()) + ['Total Score']
    col_width = 277 / len(table_headers)

    for prd, group in data.groupby('PRD Name'):
        avg = group['Total Score'].mean()
        color = f"Avg Score: {avg:.2f}"

        pdf.set_font("Arial", style='B', size=12)
        pdf.cell(0, 10, txt=_sanitize_text(f"PRD: {prd}"), ln=False)
        pdf.cell(0, 10, txt=color, align='R')
        pdf.ln()

        if avg < 7:
            lowest = []
            for param in weights:
                param_scores = group[param].apply(lambda x: x if isinstance(x, (int, float)) else None).dropna()
                avg_score = param_scores.mean() if not param_scores.empty else 0
                if avg_score < 0.6 * max(score_map[param].values()):
                    lowest.append(param)

            if lowest:
                reasons = ", ".join(lowest)
                pdf.set_text_color(255, 0, 0)
                pdf.set_font("Arial", style='', size=9)
                pdf.multi_cell(0, 8, f"Note: This PRD's score appears to be on the lower side, mainly due to relatively lower ratings in: {reasons}.")
                pdf.set_text_color(0, 0, 0)

        pdf.set_font("Arial", style='B', size=9)
        for header in table_headers:
            pdf.cell(col_width, 8, _sanitize_text(header), 1, 0, 'C')
        pdf.ln()
        pdf.set_font("Arial", size=9)

        for _, row in group.iterrows():
            row_vals = [row['Role']]
            for key in weights:
                orig_text = str(df.loc[row.name, key]).strip().lower()
                score = row.get(key, "")
                if isinstance(score, (int, float)):
                    val_display = f"{orig_text} ({score})"
                else:
                    val_display = "N/A"
                row_vals.append(val_display)
            row_vals.append(row['Total Score'])

            for val in row_vals:
                pdf.cell(col_width, 8, _sanitize_text(str(val)), 1, 0, 'L')
            pdf.ln()

        pdf.set_font("Arial", style='B', size=9)
        pdf.cell(col_width, 8, "Avg", 1, 0, 'C')
        for key in weights:
            valid_vals = group[key].apply(lambda x: x if isinstance(x, (int, float)) else None).dropna()
            avg_val = valid_vals.mean() if not valid_vals.empty else 0
            pdf.cell(col_width, 8, f"{avg_val:.2f}", 1, 0, 'C')

        r, g, b = get_color(avg)
        pdf.set_fill_color(r, g, b)
        pdf.cell(col_width, 8, f"{avg:.2f}", 1, 0, 'C', fill=True)
        pdf.ln(10)

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
        st.download_button(
            label="\U0001F4C5 Download PDF Report",
            data=open(tmp.name, "rb").read(),
            file_name="prd_report.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        os.unlink(tmp.name)

    st.subheader("\U0001F50D Converted Score Table")
    st.dataframe(result_df)
