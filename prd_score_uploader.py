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

# Precompute max possible score per parameter
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

def _s(text):
    return str(text).encode("latin-1", "ignore").decode("latin-1")

def _avg_numeric_from_display(series):
    s = series.astype(str).str.extract(r'([\d.]+)')[0]
    nums = pd.to_numeric(s, errors='coerce')
    return nums.mean()

def _lowest_params_by_impact(group, top_k=3):
    scores = []
    for p in weights.keys():
        try:
            avg_val = _avg_numeric_from_display(group[p])
        except Exception:
            avg_val = None
        if pd.isna(avg_val):
            avg_val = 0.0
        max_possible = param_max.get(p, 1) or 1
        ratio = avg_val / max_possible
        scores.append((p, ratio))
    scores.sort(key=lambda x: x[1])
    return [p for p, _ in scores[:top_k]]

def generate_pdf(data, filename):
    overall_avg = data['Total Score'].mean()
    color = get_color_by_score(overall_avg)

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()

    logo_path = "Combo.png"
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=10, w=30)

    pdf.set_xy(10, 20)
    pdf.set_font("Arial", style='B', size=14)
    pdf.cell(0, 10, txt=_s("PRD Rating Report"), ln=True, align='C')
    pdf.set_font("Arial", style='', size=12)
    pdf.set_text_color(*color)
    pdf.cell(0, 10, txt=_s(f"Overall Average Score: {overall_avg:.2f}"), ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    # Sort PRDs
    prd_avg = data.groupby("PRD Name")["Total Score"].mean().sort_values()
    sorted_prds = prd_avg.index.tolist()

    for prd_name in sorted_prds:
        group = data[data["PRD Name"] == prd_name]

        # Header
        pdf.set_font("Arial", style='B', size=12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(200, 10, txt=_s(f"PRD: {prd_name}"), ln=True, fill=True)

        avg_score = group["Total Score"].mean()
        if avg_score < 8:
            low_params = _lowest_params_by_impact(group, top_k=3)
            human_list = ", ".join(low_params) if low_params else "a few parameters"
            pdf.set_font("Arial", style='I', size=9)
            pdf.set_text_color(255, 0, 0)
            pdf.multi_cell(
                0, 6,
                _s(
                    f"Note: This PRD averaged {avg_score:.2f}. "
                    f"This was due to lower scores in: {human_list}. "

                )
            )
            pdf.set_text_color(0, 0, 0)

        # Table
        col_names = ['Role'] + list(weights.keys()) + ['Total Score']
        col_width = 195 / len(col_names)

        # Header row
        pdf.set_fill_color(180, 200, 255)
        pdf.set_font("Arial", style='B', size=8.5)  # headers
        for col in col_names:
            pdf.cell(col_width, 8, _s(col), border=1, align='C', fill=True)
        pdf.ln()

        # Data rows (font size 6 for individual ratings)
        fill = False
        pdf.set_font("Arial", size=6)  # <<< changed to 6
        for _, row in group.iterrows():
            for col in col_names:
                value = str(row.get(col, ''))
                pdf.cell(col_width, 8, _s(value), border=1, align='C', fill=fill)
            pdf.ln()
            fill = not fill

        # Average row
        pdf.set_font("Arial", style='B', size=8)
        pdf.set_fill_color(220, 220, 250)
        pdf.cell(col_width, 8, _s("Average"), border=1, align='C', fill=True)

        for col in col_names[1:]:
            try:
                avg_val = _avg_numeric_from_display(group[col])
                if pd.isna(avg_val):
                    pdf.set_fill_color(240, 240, 255)
                    pdf.cell(col_width, 8, _s(""), border=1, align='C', fill=True)
                else:
                    if col == 'Total Score':
                        r, g, b = get_color_by_score(avg_val)
                        pdf.set_fill_color(r, g, b)
                    else:
                        pdf.set_fill_color(240, 240, 255)
                    pdf.cell(col_width, 8, _s(f"{avg_val:.2f}"), border=1, align='C', fill=True)
            except Exception:
                pdf.set_fill_color(240, 240, 255)
                pdf.cell(col_width, 8, _s(""), border=1, align='C', fill=True)

        pdf.ln()
        pdf.ln(4)

        # Comments
        comments = group["Comments"].dropna().astype(str).str.strip()
        comments = comments[comments != '']
        if not comments.empty:
            pdf.set_font("Arial", style='B', size=9)
            pdf.set_fill_color(255, 250, 205)
            pdf.cell(0, 7, _s("Reviewer Comments"), ln=True, fill=True)
            pdf.set_font("Arial", size=8)
            for c in comments.unique().tolist():
                pdf.multi_cell(0, 5, _s(f"- {c}"))
            pdf.ln(2)

        pdf.ln(8)

    pdf.output(filename)

# ---------------- Streamlit App ----------------

st.set_page_config(page_title="PRD Rating Report Generator")

# Top logos aligned left & right
with st.container():
    col_left, col_spacer, col_right = st.columns([1, 6, 1])  # middle spacer
    LOGO_WIDTH = 240  # smaller size

    with col_left:
        if os.path.exists("Combo.png"):
            st.image(Image.open("Combo.png"), width=LOGO_WIDTH)


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
