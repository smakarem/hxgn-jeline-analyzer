import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import io

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="HxGN JELINE Analyzer",
    layout="wide"
)

st.title("🛠️ HxGN EAM JELINE XML Analyzer")
st.markdown("Upload XML files → Analyze JELINE → Export Excel")

# ---------------------------
# COLUMN ORDER
# ---------------------------
COLUMN_ORDER = [
    "FileName",
    "JELINE",
    "DR/CR (Amount)",
    "ACD#",
    "Legal Entity",
    "DOC TYPE",
    "GL AP GNRI",
    "Business / Customer",
    "PO / Supplier",
    "Store",
    "SITE",
    "Receipt #",
    "PO #",
    "PART##"
]

# ---------------------------
# FILE UPLOADER
# ---------------------------
uploaded_files = st.file_uploader(
    "📁 Upload XML files",
    type=["xml"],
    accept_multiple_files=True
)

# ---------------------------
# PARSER
# ---------------------------
def parse_xml_to_tables(file, filename):
    tables = []

    tree = ET.parse(file)
    root = tree.getroot()

    doctype_elem = root.find('.//JEHEADER/DOCTYPE')
    doctype = doctype_elem.text.strip() if doctype_elem is not None and doctype_elem.text else '(empty)'

    for jeline_num, jeline in enumerate(root.findall('.//JELINE'), 1):

        drcr_elem = jeline.find('.//DRCR')
        drcr = drcr_elem.text.strip() if drcr_elem is not None and drcr_elem.text else '?'

        amount = jeline.find('.//AMOUNT')
        value = float(amount.find('VALUE').text or 0) if amount is not None else 0
        numdec = int(amount.find('NUMOFDEC').text or 0) if amount is not None else 0
        proper_amount = round(value / (10 ** numdec), numdec)

        drcr_label = f"{drcr} ({proper_amount})"

        refs = {
            ref.get('index'): (ref.text or '').strip() or '(empty)'
            for ref in jeline.findall('.//REF')
        }

        elements = {
            elem.get('index'): (elem.text or '').strip() or '(empty)'
            for elem in jeline.findall('.//ELEMENT')
        }

        rows = [
            [drcr_label, refs.get('30'), 'ACD#'],
            [drcr_label, elements.get('1'), 'Legal Entity'],
            [drcr_label, doctype, 'DOC TYPE'],
            [drcr_label, elements.get('3'), 'GL AP GNRI'],
            [drcr_label, elements.get('4'), 'Business / Customer'],
            [drcr_label, refs.get('5'), 'PO / Supplier'],
            [drcr_label, elements.get('6'), 'Store / Location'],
            [drcr_label, elements.get('7'), 'Segment 1'],
            [drcr_label, elements.get('8'), 'Receipt #'],
            [drcr_label, elements.get('9'), 'PO #'],
            [drcr_label, elements.get('11'), 'PART#']
        ]

        df = pd.DataFrame(rows, columns=[
            'DR/CR (Amount)',
            'Value',
            'Meaning'
        ])

        df["FileName"] = filename
        df["JELINE"] = jeline_num

        tables.append(df)

    return tables

# ---------------------------
# MAIN
# ---------------------------
if uploaded_files:

    all_tables = []
    progress = st.progress(0)

    for i, file in enumerate(uploaded_files):
        all_tables.extend(parse_xml_to_tables(file, file.name))
        progress.progress((i + 1) / len(uploaded_files))

    if all_tables:

        full_df = pd.concat(all_tables, ignore_index=True)

        st.success(f"✅ Processed {len(uploaded_files)} file(s)")

        # ---------------------------
        # 1️⃣ GET DR/CR PER JELINE
        # ---------------------------
        drcr_df = full_df[["FileName", "JELINE", "DR/CR (Amount)"]].drop_duplicates()

        # ---------------------------
        # 2️⃣ PIVOT WITHOUT DR/CR
        # ---------------------------
        pivot_df = full_df.pivot_table(
            index=["FileName", "JELINE"],
            columns="Meaning",
            values="Value",
            aggfunc="first"
        ).reset_index()

        pivot_df.columns.name = None

        # ---------------------------
        # 3️⃣ MERGE BACK DR/CR
        # ---------------------------
        final_df = pd.merge(pivot_df, drcr_df, on=["FileName", "JELINE"], how="left")

        # ---------------------------
        # 4️⃣ COLUMN ORDER
        # ---------------------------
        existing_cols = [c for c in COLUMN_ORDER if c in final_df.columns]
        remaining_cols = [c for c in final_df.columns if c not in existing_cols]
        final_df = final_df[existing_cols + remaining_cols]

        # ---------------------------
        # DISPLAY
        # ---------------------------
        st.dataframe(final_df, use_container_width=True)

        st.caption("🔴 DR = Debit | 🟢 CR = Credit")

        # ---------------------------
        # EXPORT
        # ---------------------------
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, sheet_name="JELINE", index=False)

        st.download_button(
            "📥 Download Excel",
            output.getvalue(),
            file_name="JELINE_ANALYSIS.xlsx"
        )

        st.download_button(
            "📥 Download CSV",
            final_df.to_csv(index=False),
            file_name="JELINE_ANALYSIS.csv"
        )

else:
    st.info("👆 Upload XML files to begin")
