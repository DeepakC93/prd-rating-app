import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os

# ----------------------------
# Helper Functions
# ----------------------------

def get_color_by_score(score):
    """Return RGB tuple based on PRD SOP scoring rules."""
    if score >= 9:
        return (0, 153, 0)      # Green
    elif score >= 7:
        return (255, 204, 0)    # Yellow
    else:
        return (255, 77, 77)    # Red

def _s(val):
    """Safe string conversion (for unicode compatibility)."""
    try:
        return str(val)
    except Exception:
        return val.encode('latin-1', 'replace').decode('latin-1')

def _avg_numeric_from_display(series):
    """Extract numeric part if column has values like 'Fully Covered (2)'."""
    nums = []
    for v in series:
        if pd.isna(v):
            continue
        s = str(v)
        if '(' in s and ')' in s:
            try:
                nums.append(float(s.split('(')[-1].split(')')[0]))
            except Exception:
                pass
        else:
            try:
                nums.append(float(s))
            except Exception:
                pass
    return sum(nums)/len(nums) if nums else None

# ----------------------------
# PDF Generator
# ----------------------------

def generate_pdf(df, filename):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Sort PRDs by total average score (low to high)
    grouped = df.groupby("PRD Title")
    prd_scores = []
    for prd, group in grouped:
        avg_total = _avg_numeric_from_display(group["Total Score"])
        prd_scores.append((prd, group, avg_total))
    prd_scores.sort(key=lambda x: (x[2] if x[2] is not None else 999))

    for prd, group, avg_total in prd_scores:
        pdf.add_page()

        # Logo
        if os.path.exists("logo.png"):
            pdf.image("logo.png", 10, 8, 20)

        pdf.set_font("Arial", style='B', size=14)
        pdf.cell(0, 10, f"PRD: {prd}", ln=True, align='L')

        # Show note if average < 7
        if avg_total is not None and avg_total < 7:
            pdf.set_font("Arial", size=10)
            pdf.set_text_color(200, 0, 0)
            pdf.multi_cell(0, 8, "⚠ This PRD received a lower overall score.\n"
                                 "Some areas need more clarity or details. "
                                 "Improving them can raise the score.")
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        # Table
        col_names = ['Role'] + [c for c in group.columns if c not in ["PRD Title", "Comments"]]  # include role + ratings
        col_width = 195 / len(col_names)

        # Header row
        pdf.set_fill_color(180, 200, 255)
        pdf.set_font("Arial", style='B', size=8.5)
        for col in col_names:
            pdf.cell(col_width, 7, _s(col), border=1, align='C', fill=True)  # header
        pdf.ln()

        # Data rows
        fill = False
        pdf.set_font("Arial", size=6)  # compact font
        for _, row in group.iterrows():
            for col in col_names:
                value = str(row.get(col, ''))
                pdf.cell(col_width, 6, _s(value), border=1, align='C', fill=fill)
            pdf.ln()
            fill = not fill

        # Average row
        pdf.set_font("Arial", style='B', size=7)
        pdf.set_fill_color(220, 220, 250)
        pdf.cell(col_width, 6, _s("Average"), border=1, align='C', fill=True)

        for col in col_names[1:]:
            try:
                avg_val = _avg_numeric_from_display(group[col])
                if pd.isna(avg_val):
                    pdf.set_fill_color(240, 240, 255)
                    pdf.cell(col_width, 6, _s(""), border=1, align='C', fill=True)
                else:
                    if col == 'Total Score':
                        r, g, b = get_color_by_score(avg_val)
                        pdf.set_fill_color(r, g, b)
                        pdf.set_text_color(255, 255, 255) if avg_val < 7 else pdf.set_text_color(0, 0, 0)
                    else:
                        pdf.set_fill_color(240, 240, 255)
                        pdf.set_text_color(0, 0, 0)
                    pdf.cell(col_width, 6, _s(f"{avg_val:.2f}"), border=1, align='C', fill=True)
            except Exception:
                pdf.set_fill_color(240, 240, 255)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(col_width, 6, _s(""), border=1, align='C', fill=True)

        pdf.set_text_color(0, 0, 0)
        pdf.ln()

        # Comments section
        comments = group["Comments"].dropna().tolist() if "Comments" in group else []
        if comments:
            pdf.ln(4)
            pdf.set_font("Arial", style='B', size=9)
            pdf.cell(0, 6, "Reviewer Comments:", ln=True)
            pdf.set_font("Arial", size=8)
            for c in comments:
                pdf.multi_cell(0, 5, f"• {_s(c)}")
            pdf.ln(2)

        pdf.ln(6)  # spacing before next PRD

    pdf.output(filename)

# ----------------------------
# Streamlit App
# ----------------------------

st.set_page_config(page_title="PRD Rating Report", layout="wide")

col1, col2 = st.columns([6,1])
with col1:
    st.title("📊 PRD Rating Report Generator")
with col2:
    if os.path.exists("Marrow.png"):
        st.image("Marrow.png", use_container_width=True)

uploaded_file = st.file_uploader("Upload the PRD Ratings Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Rename Dev/QA roles → Rating 1, Rating 2 ...
    role_map = {old: f"Rating {i+1}" for i, old in enumerate(df['Role'].unique())}
    df['Role'] = df['Role'].map(role_map)

    st.subheader("Preview of Uploaded Data")
    st.dataframe(df)

    # Show summary in Streamlit
    st.subheader("PRD Average Scores Summary")
    summary = df.groupby("PRD Title")["Total Score"].mean().reset_index()
    summary.rename(columns={"Total Score": "Average Score"}, inplace=True)
    st.table(summary)

    # Generate PDF
    if st.button("Generate PDF Report"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            generate_pdf(df, tmp.name)
            with open(tmp.name, "rb") as f:
                st.download_button("📥 Download PDF", f, file_name="PRD_Report.pdf")
