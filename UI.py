import streamlit as st
import pandas as pd
from io import BytesIO

# ===============================
# Page Config
# ===============================
st.set_page_config(
    page_title="AUM Classification Dashboard",
    page_icon="📊",
    layout="wide"
)

# ===============================
# DARK PROFESSIONAL THEME (CSS)
# ===============================
st.markdown("""
<style>

/* Global */
html, body, [class*="css"] {
    background-color: #020617;
    color: #e5e7eb;
}

/* Section container */
.section {
    background-color: #020617;
    padding: 25px;
    border-radius: 16px;
    border: 1px solid #1e293b;
    margin-top: 20px;
}

/* KPI Cards */
.metric-box {
    background: linear-gradient(135deg, #020617, #0f172a);
    border: 1px solid #1e293b;
    padding: 22px;
    border-radius: 16px;
    text-align: center;
    box-shadow: 0 10px 30px rgba(0,0,0,0.6);
}
.metric-title {
    font-size: 13px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.metric-value {
    font-size: 32px;
    font-weight: 700;
    margin-top: 6px;
    color: #38bdf8;
}

/* Buttons */
.stDownloadButton button {
    background: linear-gradient(135deg, #1e3a8a, #2563eb);
    color: white;
    border-radius: 12px;
    padding: 10px 20px;
    border: none;
    font-weight: 600;
}
.stDownloadButton button:hover {
    background: linear-gradient(135deg, #1e40af, #1d4ed8);
    transform: scale(1.02);
}

/* File uploader */
[data-testid="stFileUploader"] {
    background-color: #020617;
    border: 1px dashed #334155;
    border-radius: 12px;
    padding: 20px;
}

/* Expander */
.streamlit-expanderHeader {
    background-color: #020617;
    border: 1px solid #1e293b;
    border-radius: 10px;
    color: #e5e7eb;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #020617;
    border-right: 1px solid #1e293b;
}

</style>
""", unsafe_allow_html=True)

# ===============================
# HEADER
# ===============================
st.markdown("<h1 style='text-align:center;'>📊 AUM Data Tagging Model</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#94a3b8;'>Upload • Process • Review • Download</p>", unsafe_allow_html=True)
st.markdown("<hr style='border:1px solid #1e293b'>", unsafe_allow_html=True)

# ===============================
# FILE UPLOAD
# ===============================
uploaded_file = st.file_uploader("📤 Upload Excel File", type=["xlsx"])

if uploaded_file:

    with st.spinner("Processing file..."):
        df = pd.read_excel(uploaded_file)

        # ===============================
        # Clean column names
        # ===============================
        df.columns = (
            df.columns.astype(str)
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
        )

        # ===============================
        # ADD NEW COLUMNS
        # ===============================
        df["del_tag"] = ""
        df["ambit_first"] = ""
        df["custody"] = ""
        df["heldaway"] = ""
        df["advisory"] = ""
        df["length"] = None

        # ===============================
        # BOOLEAN FLAGS
        # ===============================
        is_ambit = df["client_name"].str.contains("ambit wealth private limited", case=False, na=False)
        is_dummy = df["client_name"].str.contains("dummy", case=False, na=False)

        is_del_mf  = df["security_code"].str.contains("mfapplication", case=False, na=False)
        is_del_tds = df["security_code"].str.contains("tdsaccount", case=False, na=False)
        is_del_int = df["security_code"].str.contains("intaccpur", case=False, na=False)

        is_dv_client = df["client_name"].str.contains("dovetail|varanium", case=False, na=False)
        ws_starts_pms = df["ws_account_code"].astype(str).str.startswith(("ND", "DS", "DM"), na=False)

        # ===============================
        # Ambit First
        # ===============================
        df.loc[
            df["ws_account_code"].astype(str).str.startswith("ND", na=False) &
            df["schemename"].str.contains("ambit first", case=False, na=False),
            "ambit_first"
        ] = "Ambit First"

        # ===============================
        # DEL TAG LOGIC
        # ===============================
        df.loc[is_ambit, "del_tag"] = "Del AWPL"
        df.loc[(df["del_tag"] == "") & is_dummy, "del_tag"] = "Del Dummy"
        df.loc[(df["del_tag"] == "") & is_del_mf, "del_tag"] = "Del MF"
        df.loc[(df["del_tag"] == "") & is_del_tds, "del_tag"] = "Del TDS"
        df.loc[(df["del_tag"] == "") & is_del_int, "del_tag"] = "Del INT"

        df.loc[
            (df["del_tag"] == "") &
            ws_starts_pms &
            ~is_dv_client,
            "del_tag"
        ] = "Del PMS"

        df.loc[
            (df["ambit_first"] == "Ambit First") &
            (df["del_tag"] == "Del PMS"),
            "del_tag"
        ] = ""

        # ===============================
        # LENGTH + PAN
        # ===============================
        df["length"] = df["ws_account_code"].astype(str).str.len()
        df.loc[(df["del_tag"] == "") & (df["length"] == 10), "del_tag"] = "Del PAN"

        # ===============================
        # Custody
        # ===============================
        custody_ws_codes = ["2902", "2903", "83364", "125254", "83950", "125217"]
        df.loc[
            df["ws_account_code"].astype(str).isin(custody_ws_codes) &
            df["security_code"].astype(str).str.startswith("EQ", na=False),
            "custody"
        ] = "Custody"

        # ===============================
        # Held Away
        # ===============================
        ambit_security_exclusion = (
            "ambit anchor|ambit build india|ambit alpha growth|ambit bespoke fi|"
            "ambit bespoke|ambit caliber|ambit caliber h|ambit iris|"
            "ambit liquid|ambit maximus smart factor|ambit multi-asset"
        )

        df.loc[
            (df["schemename"].astype(str).str.strip().str.lower() == "held away") &
            ~df["ws_account_code"].astype(str).str.contains("HA|HAN", case=False, na=False) &
            ~df["security_name"].str.contains(ambit_security_exclusion, case=False, na=False),
            "heldaway"
        ] = "Held Away"

        # ===============================
        # Advisory
        # ===============================
        advisory_ws_codes = ["124654", "1235529", "1235537", "1235526", "1235525", "126873"]
        df.loc[df["ws_account_code"].astype(str).isin(advisory_ws_codes), "advisory"] = "Advisory"

    # ===============================
    # KPI COUNTS
    # ===============================
    c1, c2, c3, c4, c5 = st.columns(5)

    kpis = [
        ("Ambit First", (df["ambit_first"] == "Ambit First").sum()),
        ("Custody", (df["custody"] == "Custody").sum()),
        ("Held Away", (df["heldaway"] == "Held Away").sum()),
        ("Advisory", (df["advisory"] == "Advisory").sum()),
        ("Length = 10", (df["length"] == 10).sum())
    ]

    for col, (title, value) in zip([c1, c2, c3, c4, c5], kpis):
        with col:
            st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-title">{title}</div>
                    <div class="metric-value">{value}</div>
                </div>
            """, unsafe_allow_html=True)

    # ===============================
    # DATA PREVIEW
    # ===============================
    with st.expander("🔍 View Processed Data"):
        st.dataframe(df, use_container_width=True)

    # ===============================
    # DOWNLOAD
    # ===============================
    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    st.download_button(
        "⬇️ Download Final Excel",
        data=output,
        file_name="AUM_Final_Single_File.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.success("✅ File processed successfully")

# ===============================
# FOOTER
# ===============================
st.markdown("<hr style='border:1px solid #1e293b'>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center;color:#64748b;'>AUM Classification Tool • Internal Analytics</p>",
    unsafe_allow_html=True
)
