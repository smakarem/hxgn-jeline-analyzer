import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import io

st.set_page_config(page_title="HxGN JELINE Analyzer", layout="wide")
st.title("🛠️ HxGN EAM JELINE XML Analyzer")

uploaded_files = st.file_uploader("Upload XML files", type=["xml"], accept_multiple_files=True)

def parse_xml(file):
    tables = []
    try:
        tree = ET.parse(file)
        root = tree.getroot()

        for jeline_num, jeline in enumerate(root.findall('.//JELINE'), 1):
            drcr_elem = jeline.find('.//DRCR')
            drcr = drcr_elem.text.strip() if drcr_elem is not None else '?'

            amount = jeline.find('.//AMOUNT')
            value = float(amount.find('VALUE').text or 0) if amount is not None else 0
            numdec = int(amount.find('NUMOFDEC').text or 0) if amount is not None else 0
            amt = round(value / (10 ** numdec), numdec)

            refs = {r.get('index'): (r.text or '').strip() or '(empty)' for r in jeline.findall('.//REF')}
            elems = {e.get('index'): (e.text or '').strip() or '(empty)' for e in jeline.findall('.//ELEMENT')}

            df = pd.DataFrame([
                [drcr, refs.get('1'), elems.get('1')],
                [drcr, refs.get('2'), elems.get('2')],
                [drcr, refs.get('3'), elems.get('3')],
            ], columns=["DRCR", "REF", "ELEMENT"])

            df["Amount"] = amt
            df["JELINE"] = jeline_num
            tables.append(df)

    except Exception as e:
        st.error(f"Error parsing file: {e}")

    return tables

if uploaded_files:
    all_tables = []

    for file in uploaded_files:
        st.write(f"Processing: {file.name}")
        tables = parse_xml(file)

        if tables:
            combined = pd.concat(tables, ignore_index=True)
            st.dataframe(combined)
            all_tables.append(combined)

    if all_tables:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for i, df in enumerate(all_tables):
                df.to_excel(writer, sheet_name=f"File_{i+1}", index=False)

        st.download_button("Download Excel", data=output.getvalue(), file_name="JELINE_ANALYSIS.xlsx")
