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

# ---------------------------
# SESSION STATE
# ---------------------------
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

st.title("🛠️ HxGN EAM JELINE XML Analyzer")
st.markdown(
    "Upload XML files → Analyze JELINE → Capture SIGN values → "
    "Click a row to view raw XML → Export Excel"
)

# ---------------------------
# COLUMN ORDER
# ---------------------------
COLUMN_ORDER = [
    "XML Label",
    "FileName",
    "JELINE",
    "SIGN",
    "DR/CR (Amount)",
    "ACD#",
    "Legal Entity",
    "SITE",
    "DOC TYPE",
    "GL AP GNRI",
    "Business / Customer",
    "PO / Supplier",
    "Store",
    "DEPT NA",
    "Receipt#",
    "PO #",
    "PART#"
]

# ---------------------------
# FILE CONTROLS
# ---------------------------
col1, col2 = st.columns([1, 5])

with col1:
    if st.button("🗑️ Clear Files"):
        st.session_state.uploader_key += 1
        st.rerun()

# ---------------------------
# FILE UPLOADER
# ---------------------------
uploaded_files = st.file_uploader(
    "📁 Upload XML files",
    type=["xml"],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}"
)

if uploaded_files:
    st.success(f"📂 {len(uploaded_files)} file(s) loaded")

# ---------------------------
# PARSER
# ---------------------------
def parse_xml_to_tables(file_obj, filename):
    tables = []

    tree = ET.parse(file_obj)
    root = tree.getroot()

    doctype_elem = root.find(".//JEHEADER/DOCTYPE")
    doctype = (
        doctype_elem.text.strip()
        if doctype_elem is not None and doctype_elem.text
        else "(empty)"
    )

    for jeline_num, jeline in enumerate(root.findall(".//JELINE"), 1):

        # ---------------------------
        # SIGN
        # ---------------------------
        sign_elem = jeline.find("SIGN")
        sign_value = (
            sign_elem.text.strip()
            if sign_elem is not None and sign_elem.text
            else "(empty)"
        )

        # ---------------------------
        # DR/CR + Amount
        # ---------------------------
        drcr_elem = jeline.find(".//DRCR")
        drcr = (
            drcr_elem.text.strip()
            if drcr_elem is not None and drcr_elem.text
            else "?"
        )

        amount = jeline.find(".//AMOUNT")

        try:
            value = (
                float(amount.find("VALUE").text or 0)
                if amount is not None
                else 0
            )
            numdec = (
                int(amount.find("NUMOFDEC").text or 0)
                if amount is not None
                else 0
            )
            proper_amount = round(value / (10 ** numdec), numdec)
        except Exception:
            proper_amount = 0

        drcr_label = f"{drcr} ({proper_amount})"

        # ---------------------------
        # REFS
        # ---------------------------
        refs = {
            ref.get("index"): (ref.text or "").strip() or "(empty)"
            for ref in jeline.findall(".//REF")
        }

        # ---------------------------
        # ELEMENTS
        # ---------------------------
        elements = {
            elem.get("index"): (elem.text or "").strip() or "(empty)"
            for elem in jeline.findall(".//ELEMENT")
        }

        # ---------------------------
        # ROWS
        # ---------------------------
        rows = [
            [drcr_label, refs.get("30"), "ACD#"],
            [drcr_label, elements.get("1"), "Legal Entity"],
            [drcr_label, elements.get("2"), "SITE"],
            [drcr_label, doctype, "DOC TYPE"],
            [drcr_label, elements.get("3"), "GL AP GNRI"],
            [drcr_label, elements.get("4"), "Business / Customer"],
            [drcr_label, refs.get("5"), "PO / Supplier"],
            [drcr_label, elements.get("6"), "Store"],
            [drcr_label, elements.get("7"), "DEPT NA"],
            [drcr_label, elements.get("8"), "Receipt#"],
            [drcr_label, elements.get("9"), "PO #"],
            [drcr_label, elements.get("11"), "PART#"]
        ]

        df = pd.DataFrame(
            rows,
            columns=["DR/CR (Amount)", "Value", "Meaning"]
        )

        df["FileName"] = filename
        df["JELINE"] = jeline_num
        df["SIGN"] = sign_value

        tables.append(df)

    return tables

# ---------------------------
# MAIN
# ---------------------------
if uploaded_files:

    all_tables = []
    raw_xml_map = {}

    progress = st.progress(0)

    for i, file in enumerate(uploaded_files):

        try:
            file_bytes = file.getvalue()

            raw_xml_map[file.name] = file_bytes.decode(
                "utf-8",
                errors="replace"
            )

            file_tables = parse_xml_to_tables(
                io.BytesIO(file_bytes),
                file.name
            )

            all_tables.extend(file_tables)

        except Exception as e:
            st.error(f"❌ Error parsing {file.name}: {e}")

        progress.progress((i + 1) / len(uploaded_files))

    if all_tables:

        full_df = pd.concat(all_tables, ignore_index=True)

        st.success(f"✅ Processed {len(uploaded_files)} file(s)")

        # ---------------------------
        # GET UNIQUE JELINE INFO
        # ---------------------------
        jeline_info_df = full_df[
            ["FileName", "JELINE", "DR/CR (Amount)", "SIGN"]
        ].drop_duplicates()

        # ---------------------------
        # PIVOT
        # ---------------------------
        pivot_df = full_df.pivot_table(
            index=["FileName", "JELINE"],
            columns="Meaning",
            values="Value",
            aggfunc="first"
        ).reset_index()

        pivot_df.columns.name = None

        # ---------------------------
        # MERGE BACK DR/CR + SIGN
        # ---------------------------
        final_df = pd.merge(
            pivot_df,
            jeline_info_df,
            on=["FileName", "JELINE"],
            how="left"
        )

        # ---------------------------
        # ADD XML LABEL
        # ---------------------------
        final_df.insert(0, "XML Label", "View XML")

        # ---------------------------
        # COLUMN ORDER
        # ---------------------------
        existing_cols = [
            c for c in COLUMN_ORDER
            if c in final_df.columns
        ]

        remaining_cols = [
            c for c in final_df.columns
            if c not in existing_cols
        ]

        final_df = final_df[
            existing_cols + remaining_cols
        ]

        # ---------------------------
        # DISPLAY
        # ---------------------------
        st.subheader("📋 Parsed JELINE Table")

        selection = st.dataframe(
            final_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )

        st.caption("🔴 DR = Debit | 🟢 CR = Credit")

        # ---------------------------
        # RAW XML PANEL
        # ---------------------------
        if selection and selection["selection"]["rows"]:

            selected_idx = selection["selection"]["rows"][0]

            selected_file = final_df.iloc[selected_idx]["FileName"]

            st.subheader(f"📄 Raw XML: {selected_file}")

            st.code(
                raw_xml_map[selected_file],
                language="xml"
            )

            st.download_button(
                label="📥 Download Selected Raw XML",
                data=raw_xml_map[selected_file],
                file_name=selected_file,
                mime="application/xml"
            )

        # ---------------------------
        # EXPORT EXCEL
        # ---------------------------
        output = io.BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:
            final_df.to_excel(
                writer,
                sheet_name="JELINE",
                index=False
            )

        st.download_button(
            "📥 Download Excel",
            output.getvalue(),
            file_name="JELINE_ANALYSIS.xlsx",
            mime=(
                "application/"
                "vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )

        # ---------------------------
        # EXPORT CSV
        # ---------------------------
        st.download_button(
            "📥 Download CSV",
            final_df.to_csv(index=False),
            file_name="JELINE_ANALYSIS.csv",
            mime="text/csv"
        )

else:
    st.info("👆 Upload XML files to begin")
