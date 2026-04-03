import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path
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
# FILE UPLOADER
# ---------------------------
uploaded_files = st.file_uploader(
    "📁 Upload XML files",
    type=["xml"],
    accept_multiple_files=True
)

# ---------------------------
# PARSER (FULL LOGIC)
# ---------------------------
def parse_xml_to_tables(file):
    tables = []

    try:
        tree = ET.parse(file)
        root = tree.getroot()

        for jeline_num, jeline in enumerate(root.findall('.//JELINE'), 1):
            # DR/CR
            drcr_elem = jeline.find('.//DRCR')
            drcr = drcr_elem.text.strip() if drcr_elem is not None else '?'

            # Amount
            amount = jeline.find('.//AMOUNT')
            value = float(amount.find('VALUE').text or 0) if amount is not None else 0
            numdec = int(amount.find('NUMOFDEC').text or 0) if amount is not None else 0
            proper_amount = round(value / (10 ** numdec), numdec)

            drcr_label = f"{drcr} ({proper_amount})"

            # REFs & ELEMENTS
            refs = {
                ref.get('index'): (ref.text or '').strip() or '(empty)'
                for ref in jeline.findall('.//REF')
            }

            elements = {
                elem.get('index'): (elem.text or '').strip() or '(empty)'
                for elem in jeline.findall('.//ELEMENT')
            }

            # TABLE STRUCTURE (your mapping)
            rows = [
                [drcr_label, '30', '-', refs.get('30'), 'ACD#'],
                [drcr, '-', '1', elements.get('1'), 'Legal Entity'],
                [drcr, '2', '2', refs.get('2'), 'DOC TYPE (Receipt)'],
                [drcr, '3', '3', elements.get('3'), 'GL Account'],
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

            df['JELINE'] = jeline_num
            tables.append(df)

    except Exception as e:
        st.error(f"❌ Error parsing XML: {e}")

    return tables


# ---------------------------
# MAIN PROCESSING
# ---------------------------
if uploaded_files:

    all_tables = []
    progress = st.progress(0)

    for i, file in enumerate(uploaded_files):
        st.subheader(f"📄 {file.name}")

        tables = parse_xml_to_tables(file)

        if tables:
            combined = pd.concat(tables, ignore_index=True)
            st.dataframe(combined, use_container_width=True)
            all_tables.append(combined)
        else:
            st.warning("No JELINE data found")

        progress.progress((i + 1) / len(uploaded_files))

    # ---------------------------
    # SUMMARY
    # ---------------------------
    if all_tables:
        st.success(f"✅ Processed {len(uploaded_files)} file(s)")

        # Combine all
        full_df = pd.concat(all_tables, ignore_index=True)

        # ---------------------------
        # DOWNLOAD EXCEL
        # ---------------------------
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for i, df in enumerate(all_tables):
                df.to_excel(writer, sheet_name=f"File_{i+1}", index=False)

        st.download_button(
            label="📥 Download Excel Report",
            data=output.getvalue(),
            file_name="JELINE_ANALYSIS.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # ---------------------------
        # DOWNLOAD CSV
        # ---------------------------
        csv_data = full_df.to_csv(index=False)

        st.download_button(
            label="📥 Download CSV Summary",
            data=csv_data,
            file_name="JELINE_SUMMARY.csv",
            mime="text/csv"
        )

# ---------------------------
# EMPTY STATE
# ---------------------------
else:
    st.info("👆 Upload one or more XML files to begin analysis")
