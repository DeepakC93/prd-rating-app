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
        display_val = f"{val.title()} ({mapped})"
        scores[param_key] = display_val
        total_score += mapped
        total_weight += weights[param_key]
    normalized_total = round(total_score * 10 / total_weight, 2) if total_weight else 0
    return scores, normalized_total

def get_color_by_score(score):
    if score >= 8:
        return (144, 238, 144)  # light green
    elif 6 <= score < 8:
        return (255, 165, 0)    # orange
    else:
        return (255, 99, 71)    # red

def generate_pdf(data, filename):
    overall_avg = data['Total Score'].mean()
    color = get_color_by_score(overall_avg)

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()

    # Logo
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=10, w=30)

    pdf.set_xy(10, 20)
    pdf.set_font("Arial", style='B', size=14)
    pdf.cell(0, 10, txt="PRD Rating Report", ln=True, align='C')
    pdf.set_font("Arial", style='', size=12)
    pdf.set_text_color(*color)
    pdf.cell(0, 10, txt=f"Overall Average Score: {overall_avg:.2f}", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    # Sort PRDs by average score (low to high)
    prd_order = data.groupby("PRD Name")["Total Score"].mean().sort_values().index
    data = data.set_index("PRD Name").loc[prd_order].reset_index()

    for prd_name, group in data.groupby('PRD Name'):
        prd_avg = group['Total Score'].mean()

        # PRD Title
        pdf.set_font("Arial", style='B', size=12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(200, 10, txt=f"PRD: {prd_name}", ln=True, fill=True)

        # Friendly note if average < 7
        if prd_avg < 7:
            lowest_params = {}
            for param in weights.keys():
                numeric_vals = pd.to_numeric(
                    group[param].astype(str).str.extract(r'([\d.]+)')[0],
                    errors='coerce'
                )
                avg_val = numeric_vals.mean()
                if not pd.isna(avg_val):
                    lowest_params[param] = avg_val

            # Pick the 2 lowest scoring parameters
            low_keys = sorted(lowest_params, key=lowest_params.get)[:2]
            low_text = " and ".join(low_keys)

            pdf.set_font("Arial", style='', size=9)
            pdf.set_text_color(255, 99, 71)  # highlight red
            pdf.multi_cell(0, 6,
                f"Note: This PRD scored a bit low mainly due to **{low_text}**. "
                "Improving these areas can really boost the score 🚀"
            )
            pdf.set_text_color(0, 0, 0)
            pdf.ln(3)

        pdf.set_font("Arial", size=8)

        col_names = ['Role'] + list(weights.keys()) + ['Total Score']
        col_width = 195 / len(col_names)

        # Table header
        pdf.set_fill_color(180, 200, 255)
        pdf.set_font("Arial", style='B', size=8)
        for col in col_names:
            pdf.cell(col_width, 8, col, border=1, align='C', fill=True)
        pdf.ln()

        # Table rows
        fill = False
        pdf.set_font("Arial", size=6)
        for _, row in group.iterrows():
            for col in col_names:
                value = str(row.get(col, ''))
                pdf.cell(col_width, 10, value, border=1, align='C', fill=fill)
            pdf.ln()
            fill = not fill

        # Average row
        pdf.set_font("Arial", style='B', size=8)
        pdf.set_fill_color(220, 220, 250)
        pdf.cell(col_width, 8, "Average", border=1, align='C', fill=True)

        for col in col_names[1:]:
            try:
                numeric_vals = pd.to_numeric(group[col].astype(str).str.extract(r'([\d.]+)')[0], errors='coerce')
                avg_val = numeric_vals.mean()

                if pd.isna(avg_val):
                    pdf.set_fill_color(240, 240, 255)
                    pdf.cell(col_width, 8, "", border=1, align='C', fill=True)
                else:
                    if col == 'Total Score':
                        r, g, b = get_color_by_score(avg_val)
                        pdf.set_fill_color(r, g, b)
                    else:
                        pdf.set_fill_color(240, 240, 255)
                    pdf.cell(col_width, 8, f"{avg_val:.2f}", border=1, align='C', fill=True)
            except Exception:
                pdf.set_fill_color(240, 240, 255)
                pdf.cell(col_width, 8, "", border=1, align='C', fill=True)

        pdf.ln()
        pdf.ln(8)  # spacing between tables

        # Show comments (bulleted)
        comments = group['Comments'].dropna().astype(str).unique()
        if len(comments) > 0:
            pdf.set_font("Arial", style='B', size=9)
            pdf.cell(0, 8, "Reviewer Comments:", ln=True)
            pdf.set_font("Arial", size=8)
            for c in comments:
                pdf.multi_cell(0, 6, f"• {c}")
            pdf.ln(5)

    pdf.output(filename)

# Streamlit App
st.set_page_config(page_title="PRD Rating Report Generator")

# Add two logos: left and right
col1, col2, col3 = st.columns([1,6,1])
with col1:
    st.image("logo.png", width=100)
with col3:
    if os.path.exists("Marrow.png"):
        st.image("Marrow.png", width=100)

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

    if 'Comments' not in df.columns:
        df['Comments'] = ''

    st.success("File uploaded and normalized!")

    all_scores = []
    for idx, row in df.iterrows():
        scores, total = convert_to_score(row)
        scores['PRD Name'] = row.get('PRD Name', f"PRD-{idx+1}")
        scores['Role'] = row.get('Role', 'Unknown')
        scores['Total Score'] = total
        scores['Comments'] = row.get('Comments', '')
        all_scores.append(scores)

    result_df = pd.DataFrame(all_scores)
    result_df = result_df[['PRD Name', 'Role'] + list(weights.keys()) + ['Total Score', 'Comments']]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        generate_pdf(result_df, tmp.name)

        with open(tmp.name, "rb") as f:
            st.download_button(
                label="📄 Download PDF Report",
                data=f,
                file_name="prd_report.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        os.unlink(tmp.name)

    st.subheader("📊 Summary of PRD Scores")
    prd_summary = result_df.groupby("PRD Name")[["Total Score"]].mean().reset_index()
    prd_summary.columns = ["PRD Name", "Average Score"]
    st.dataframe(prd_summary)

    st.subheader("🔍 Converted Score Table")
    st.dataframe(result_df)
