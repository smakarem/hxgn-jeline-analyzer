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
# COLUMN ORDER (BUSINESS LOGIC)
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
    "Store / Location",
    "Segment 1",
    "Receipt #",
    "PO #",
    "Unused"
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

    try:
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
                [drcr_label, '30', '-', refs.get('30'), 'ACD#'],
                [drcr, '-', '1', elements.get('1'), 'Legal Entity'],
                [drcr, '2', '2', doctype, 'DOC TYPE'],
                [drcr, '3', '3', elements.get('3'), 'GL AP GNRI'],
                [drcr, '4', '4', elements.get('4'), 'Business / Customer'],
                [drcr, '5', '5', refs.get('5'), 'PO / Supplier'],
                [drcr, '-', '6', elements.get('6'), 'Store / Location'],
                [drcr, '-', '7', elements.get('7'), 'Segment 1'],
                [drcr, '-', '8', elements.get('8'), 'Receipt #'],
                [drcr, '-', '9', elements.get('9'), 'PO #'],
                [drcr, '-', '10', elements.get('10'), 'Unused']
            ]

            df = pd.DataFrame(rows, columns=[
                'DR/CR (Amount)',
                'REF Index',
                'Element Index',
                'Value',
                'Meaning'
            ])

            df["FileName"] = filename
            df["JELINE"] = jeline_num

            tables.append(df)

        return tables

    except Exception as e:
        st.error(f"❌ Error parsing XML: {e}")
        return []

# ---------------------------
# COLOR FUNCTION (DR / CR)
# ---------------------------
def color_dr_cr(val):
    if isinstance(val, str):
        if val.startswith("D"):
            return "color: red; font-weight: bold;"
        elif val.startswith("C"):
            return "color: green; font-weight: bold;"
    return ""

# ---------------------------
# MAIN PROCESSING
# ---------------------------
if uploaded_files:

    all_tables = []
    progress = st.progress(0)

    for i, file in enumerate(uploaded_files):

        tables = parse_xml_to_tables(file, file.name)

        if tables:
            all_tables.extend(tables)

        progress.progress((i + 1) / len(uploaded_files))

    # ---------------------------
    # OUTPUT
    # ---------------------------
    if all_tables:

        full_df = pd.concat(all_tables, ignore_index=True)

        st.success(f"✅ Processed {len(uploaded_files)} file(s)")

        # ---------------------------
        # PIVOT (NO SPECIAL MERGING)
        # ---------------------------
        pivot_df = full_df.pivot_table(
            index=["FileName", "JELINE", "DR/CR (Amount)"],
            columns="Meaning",
            values="Value",
            aggfunc="first"
        ).reset_index()

        pivot_df.columns.name = None

        # ---------------------------
        # COLUMN ORDERING
        # ---------------------------
        existing_cols = [c for c in COLUMN_ORDER if c in pivot_df.columns]
        remaining_cols = [c for c in pivot_df.columns if c not in existing_cols]
        pivot_df = pivot_df[existing_cols + remaining_cols]

        # ---------------------------
        # COLOR DR/CR
        # ---------------------------
        styled_df = pivot_df.style.applymap(
            color_dr_cr,
            subset=["DR/CR (Amount)"]
        )

        st.dataframe(styled_df, use_container_width=True)

        # ---------------------------
        # EXCEL EXPORT
        # ---------------------------
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pivot_df.to_excel(writer, sheet_name="JELINE_WIDE", index=False)

        st.download_button(
            "📥 Download Excel",
            output.getvalue(),
            file_name="JELINE_ANALYSIS.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # ---------------------------
        # CSV EXPORT
        # ---------------------------
        st.download_button(
            "📥 Download CSV",
            pivot_df.to_csv(index=False),
            file_name="JELINE_ANALYSIS.csv",
            mime="text/csv"
        )

else:
    st.info("👆 Upload one or more XML files to begin analysis")
