import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os
from PIL import Image

# Canonical parameter aliases to standardize header names
canonical_params = {
@@ -74,67 +75,74 @@

# Streamlit App
st.set_page_config(page_title="PRD Rating Report Generator")

# Centered logo display
logo = Image.open("logo.png")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(logo, use_column_width=True)

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
