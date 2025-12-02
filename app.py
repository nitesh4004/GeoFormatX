import streamlit as st
import geopandas as gpd
import pandas as pd
import fiona
import os
import tempfile
import gdown
import requests
from zipfile import ZipFile
from io import BytesIO
from shapely import wkt

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="GeoFormatX Ultimate",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enable KML drivers for fiona
fiona.drvsupport.supported_drivers['KML'] = 'rw'
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'

# Initialize Session State
if 'calc_result_gdf' not in st.session_state:
    st.session_state['calc_result_gdf'] = None
if 'calc_result_name' not in st.session_state:
    st.session_state['calc_result_name'] = "result"
if 'current_tab' not in st.session_state:
    st.session_state['current_tab'] = "home"

# --- 2. ENHANCED STYLING (Modern + Primary Blue #0068C9) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    code, pre {
        font-family: 'JetBrains Mono', monospace;
    }

    /* ROOT VARIABLES */
    :root {
        --primary: #0068C9;
        --primary-dark: #0053a6;
        --primary-light: #E8F0FF;
        --secondary: #F5F5F5;
        --border: #E0E0E0;
        --text-primary: #1a1a1a;
        --text-secondary: #666666;
        --success: #10B981;
        --warning: #F59E0B;
        --error: #EF4444;
    }

    @media (prefers-color-scheme: dark) {
        :root {
            --secondary: #1E1E1E;
            --border: #3a3a3a;
            --text-primary: #ffffff;
            --text-secondary: #b0b0b0;
        }
    }

    /* HERO SECTION */
    .hero-banner {
        background: linear-gradient(135deg, #0068C9 0%, #0053a6 100%);
        padding: 2.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0, 104, 201, 0.15);
    }

    .hero-banner h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    .hero-banner p {
        margin: 0.5rem 0 0 0;
        font-size: 1rem;
        opacity: 0.95;
    }

    /* FEATURE CARDS */
    .feature-card {
        background: #ffffff;
        border: 1px solid #E0E0E0;
        border-radius: 12px;
        padding: 1.5rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }

    .feature-card:hover {
        border-color: #0068C9;
        box-shadow: 0 8px 24px rgba(0, 104, 201, 0.12);
        transform: translateY(-2px);
    }

    .feature-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #0068C9, #0053a6);
        transform: scaleX(0);
        transform-origin: left;
        transition: transform 0.3s ease;
    }

    .feature-card:hover::before {
        transform: scaleX(1);
    }

    .feature-card h3 {
        margin: 0 0 0.5rem 0;
        color: #0068C9;
        font-size: 1.25rem;
        font-weight: 600;
    }

    .feature-card p {
        margin: 0;
        color: #666666;
        font-size: 0.95rem;
        line-height: 1.5;
    }

    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 0.75rem;
        display: block;
    }

    @media (prefers-color-scheme: dark) {
        .feature-card {
            background: #262730;
            border-color: #41424b;
        }

        .feature-card p {
            color: #b0b0b0;
        }
    }

    /* WORKFLOW INDICATOR */
    .workflow-steps {
        display: flex;
        align-items: center;
        margin: 2rem 0;
        gap: 0.5rem;
        flex-wrap: wrap;
    }

    .step {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        background: #F5F5F5;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 500;
        color: #0068C9;
    }

    .step-number {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        background: #0068C9;
        color: white;
        border-radius: 50%;
        font-weight: 600;
        font-size: 0.85rem;
    }

    .step-arrow {
        color: #0068C9;
        font-weight: bold;
        margin: 0 0.25rem;
    }

    @media (max-width: 768px) {
        .step-arrow {
            display: none;
        }
    }

    @media (prefers-color-scheme: dark) {
        .step {
            background: #3a3a3a;
        }
    }

    /* CONTROL PANEL */
    .control-panel {
        background: #ffffff;
        border: 1px solid #E0E0E0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }

    .control-panel-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #E0E0E0;
    }

    .control-panel-header h3 {
        margin: 0;
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a1a1a;
    }

    .control-panel-header .icon {
        font-size: 1.5rem;
    }

    @media (prefers-color-scheme: dark) {
        .control-panel {
            background: #262730;
            border-color: #41424b;
        }

        .control-panel-header {
            border-bottom-color: #41424b;
        }

        .control-panel-header h3 {
            color: #ffffff;
        }
    }

    /* STATS DISPLAY */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }

    .stat-box {
        background: linear-gradient(135deg, #E8F0FF 0%, #F0F4FF 100%);
        border: 1px solid #D4E4F7;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }

    .stat-box .value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0068C9;
        margin-bottom: 0.25rem;
    }

    .stat-box .label {
        font-size: 0.85rem;
        color: #666666;
        font-weight: 500;
    }

    @media (prefers-color-scheme: dark) {
        .stat-box {
            background: linear-gradient(135deg, #1a2a4a 0%, #1e2f50 100%);
            border-color: #2a4a6a;
        }

        .stat-box .label {
            color: #b0b0b0;
        }
    }

    /* BUTTONS */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        letter-spacing: 0.3px;
        transition: all 0.2s ease;
        border: none;
        padding: 0.6rem 1.25rem;
        height: auto;
    }

    .stButton > button[kind="primary"] {
        background-color: #0068C9;
        color: white;
    }

    .stButton > button[kind="primary"]:hover {
        background-color: #0053a6;
        box-shadow: 0 4px 12px rgba(0, 104, 201, 0.3);
        transform: translateY(-1px);
    }

    .stButton > button[kind="secondary"] {
        background-color: #F5F5F5;
        color: #1a1a1a;
        border: 1px solid #E0E0E0;
    }

    .stButton > button[kind="secondary"]:hover {
        background-color: #EEEEEE;
        border-color: #0068C9;
    }

    /* INPUTS & SELECTS */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 1px solid #E0E0E0;
        font-family: 'Inter', sans-serif;
        transition: all 0.2s ease;
    }

    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #0068C9;
        box-shadow: 0 0 0 3px rgba(0, 104, 201, 0.1);
    }

    /* TABS - Modern Design */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: transparent;
        border-bottom: 2px solid #E0E0E0;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0.75rem 1.5rem;
        border-radius: 0;
        border-bottom: 3px solid transparent;
        background: transparent;
        color: #666666;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #0068C9;
        background: #F5F5F5;
    }

    .stTabs [aria-selected="true"] {
        color: #0068C9;
        border-bottom-color: #0068C9;
        background: transparent;
    }

    @media (prefers-color-scheme: dark) {
        .stTabs [data-baseweb="tab-list"] {
            border-bottom-color: #41424b;
        }

        .stTabs [data-baseweb="tab"]:hover {
            background: #3a3a3a;
        }
    }

    /* ALERTS */
    .stSuccess {
        background-color: #F0FDF4;
        border-color: #10B981;
        border-radius: 8px;
    }

    .stWarning {
        background-color: #FFFBEB;
        border-color: #F59E0B;
        border-radius: 8px;
    }

    .stError {
        background-color: #FEF2F2;
        border-color: #EF4444;
        border-radius: 8px;
    }

    .stInfo {
        background-color: #E8F0FF;
        border-color: #0068C9;
        border-radius: 8px;
    }

    /* DIVIDER */
    .stDivider {
        border-color: #E0E0E0;
    }

    /* DATAFRAME */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }

    /* SIDEBAR */
    .st-emotion-cache-1r6zmc3 {
        background: linear-gradient(180deg, #ffffff 0%, #F9FAFB 100%);
    }

    @media (prefers-color-scheme: dark) {
        .st-emotion-cache-1r6zmc3 {
            background: linear-gradient(180deg, #262730 0%, #1E1E1E 100%);
        }
    }

    /* RESPONSIVE */
    @media (max-width: 768px) {
        .hero-banner {
            padding: 1.5rem;
        }

        .hero-banner h1 {
            font-size: 1.75rem;
        }

        .feature-card {
            padding: 1rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA CONSTANTS ---
STATE_VILLAGE_IDS = {
    "ANDAMAN_&_NICOBAR_ISLANDS": "1aikaQXqP9xtDhMcQFyUn8g9gGi0Tam0s",
    "ANDHRA_PRADESH": "1fkDuJI6oC0h8LQCvCh9elhKq0KbXQbTj",
    "ARUNACHAL_PRADESH": "1_Example_ID_Placeholder",
    "ASSAM": "1_Example_ID_Placeholder",
    "BIHAR": "14QA_fZiSPYFKy9CfvqL4Z-9v9FWaAWBC",
    "CHANDIGARH": "1cr9Px3o70pJTRSRcqTN1kS18AcTeksu_",
    "CHHATTISGARH": "1Kk3sUbMBysyDwVYTnBBGaqF9E9p7372c",
    "DELHI": "1UuiNX9cQvj3BZIhcojvEb6cZv3ic0NMy",
    "GOA": "1re0K0LUr1k9ZgqsKJoQpynLXtmFQQECs",
    "GUJARAT": "1_Example_ID_Placeholder",
    "HARYANA": "1Ab1ccMk-papacEOK74CST_nLFBbwRQia",
    "HIMACHAL_PRADESH": "1_Example_ID_Placeholder",
    "JAMMU_&_KASHMIR": "1_Example_ID_Placeholder",
    "JHARKHAND": "16w2g-ppENXpbAAbtG05bepQjVleijQCB",
    "KARNATAKA": "1daGp_O2RmMjjT8ATsaRX75XWNfWZaPsM",
    "KERALA": "1qva1qt4luInTg6tb_6vCKU7qKhbBvj1J",
    "LAKSHYADWEEP": "10vUXwZ8A_UNWaLAFvDZGfbi985_E8oxc",
    "MADHYA_PRADESH": "1WnwwFX8AtY4P9mDJq8Wd09nqEcIhOHk4",
    "MAHARASHTRA": "1NspjfpGqxNb1G6fJSmlGj82h5YTanULV",
    "MANIPUR": "1_Example_ID_Placeholder",
    "MEGHALAYA": "1_Example_ID_Placeholder",
    "MIZORAM": "1_Example_ID_Placeholder",
    "NAGALAND": "1_Example_ID_Placeholder",
    "ODISHA": "1_Example_ID_Placeholder",
    "PUDUCHERRY": "1_Example_ID_Placeholder",
    "PUNJAB": "1_Example_ID_Placeholder",
    "RAJASTHAN": "1_Example_ID_Placeholder",
    "SIKKIM": "1_Example_ID_Placeholder",
    "TAMIL_NADU": "1_Example_ID_Placeholder",
    "TELANGANA": "1_Example_ID_Placeholder",
    "TRIPURA": "1_Example_ID_Placeholder",
    "UTTAR_PRADESH": "1_Example_ID_Placeholder",
    "UTTARAKHAND": "1ydyLvZ3yiOWW9ltfYMlsKqBbnyLi0cu_",
    "WEST_BENGAL": "1euxg0fPGT5XcbLt0dP25U2M4fEZ-dkNs"
}

# --- 4. HELPER FUNCTIONS ---

@st.cache_data(show_spinner=False)
def load_file_from_url(url, is_gdrive=False):
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "downloaded_data.zip")

    try:
        if is_gdrive:
            gdown.download(url, zip_path, quiet=True, fuzzy=True)
        else:
            response = requests.get(url, stream=True)
            if response.status_code != 200:
                return None
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        return extract_and_read_first(zip_path, temp_dir)
    except Exception:
        return None

def extract_and_read_first(zip_path, temp_dir):
    try:
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith((".shp", ".geojson", ".kml", ".gpkg")):
                    return gpd.read_file(os.path.join(root, file))
        return None
    except Exception:
        return None

def clean_text_data(gdf):
    col_map = {
        'STATE_UT': 'STATE', 'State': 'STATE',
        'Name': 'District', 'Sub_dist': 'Subdistrict',
        'Vill_name': 'Village', 'Vill_name_': 'Village'
    }
    gdf.rename(columns=col_map, inplace=True)

    target_cols = ['District', 'STATE', 'Subdistrict', 'Village']
    for col in target_cols:
        if col in gdf.columns:
            if pd.api.types.is_string_dtype(gdf[col]) or pd.api.types.is_object_dtype(gdf[col]):
                gdf[col] = gdf[col].astype(str).str.replace('>', 'A').str.strip()
    return gdf

def convert_crs(gdf, target_epsg):
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf.to_crs(epsg=target_epsg)

def handle_export(gdf, output_format, file_prefix="export"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_dir = os.path.join(tmp_dir, "output")
        os.makedirs(out_dir, exist_ok=True)

        def make_zip(source_dir):
            zip_buffer = BytesIO()
            with ZipFile(zip_buffer, 'w') as zip_file:
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zip_file.write(file_path, os.path.relpath(file_path, source_dir))
            zip_buffer.seek(0)
            return zip_buffer

        try:
            file_ext, mime_type, final_data = "", "", None

            if "Shapefile" in output_format:
                gdf.to_file(os.path.join(out_dir, f"{file_prefix}.shp"), driver="ESRI Shapefile", encoding='utf-8')
                final_data = make_zip(out_dir)
                file_ext, mime_type = ".zip", "application/zip"

            elif "GeoJSON" in output_format:
                path = os.path.join(out_dir, f"{file_prefix}.geojson")
                gdf.to_file(path, driver="GeoJSON")
                with open(path, "rb") as f: final_data = BytesIO(f.read())
                file_ext, mime_type = ".geojson", "application/json"

            elif "KML" in output_format:
                path = os.path.join(out_dir, f"{file_prefix}.kml")
                gdf.to_file(path, driver="KML")
                with open(path, "rb") as f: final_data = BytesIO(f.read())
                file_ext, mime_type = ".kml", "application/vnd.google-earth.kml+xml"

            elif "GeoPackage" in output_format:
                path = os.path.join(out_dir, f"{file_prefix}.gpkg")
                gdf.to_file(path, driver="GPKG")
                with open(path, "rb") as f: final_data = BytesIO(f.read())
                file_ext, mime_type = ".gpkg", "application/x-sqlite3"

            return final_data, file_ext, mime_type
        except Exception as e:
            st.error(f"Export failed: {str(e)}")
            return None, None, None

# --- 5. HOME PAGE ---

def view_home():
    # Hero Section
    st.markdown("""
    <div class="hero-banner">
        <h1>🌍 GeoFormatX Ultimate</h1>
        <p>Advanced Geospatial Data Processing & Format Conversion Platform</p>
    </div>
    """, unsafe_allow_html=True)

    # Workflow Steps
    st.markdown("""
    <div class="workflow-steps">
        <div class="step"><span class="step-number">1</span> Upload/Download</div>
        <div class="step-arrow">→</div>
        <div class="step"><span class="step-number">2</span> Process</div>
        <div class="step-arrow">→</div>
        <div class="step"><span class="step-number">3</span> Export</div>
    </div>
    """, unsafe_allow_html=True)

    # Feature Cards
    st.write("")
    col1, col2, col3 = st.columns(3, gap="medium")

    with col1:
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">📥</span>
            <h3>Admin Downloader</h3>
            <p>Download official Indian administrative boundaries at district, subdistrict, and village level from verified sources.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Explore →", key="home_btn_1", use_container_width=True):
            st.session_state.current_tab = "downloader"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">🔄</span>
            <h3>Format Converter</h3>
            <p>Convert between Shapefile, GeoJSON, KML, GeoPackage with CRS transformation and batch processing support.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Convert →", key="home_btn_2", use_container_width=True):
            st.session_state.current_tab = "converter"
            st.rerun()

    with col3:
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">🧮</span>
            <h3>Vector Calculator</h3>
            <p>Perform geoprocessing operations: buffer, dissolve, centroids, simplify, and spatial analysis tools.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Calculate →", key="home_btn_3", use_container_width=True):
            st.session_state.current_tab = "calculator"
            st.rerun()

    # Additional Info
    st.divider()

    col_info1, col_info2 = st.columns(2, gap="medium")

    with col_info1:
        st.markdown("""
        #### 🚀 Quick Start
        1. **Admin Downloader** - Fetch state & district boundaries
        2. **Format Converter** - Convert any vector format
        3. **Vector Calculator** - Perform spatial analysis

        All tools support multiple output formats and CRS transformations.
        """)

    with col_info2:
        st.markdown("""
        #### ⚡ Supported Formats
        - **Input**: Shapefile, GeoJSON, KML, GeoPackage, CSV, Excel
        - **Output**: Shapefile, GeoJSON, KML, GeoPackage
        - **CRS**: Any EPSG code supported

        Learn more about geospatial formats and coordinate systems.
        """)

# --- 6. MODULES ---

def view_admin_downloader():
    st.title("📥 Admin Boundary Repository")
    st.markdown("Download official administrative boundaries for India")

    col_config, col_preview = st.columns([1.2, 1.5], gap="large")

    with col_config:
        # Control Panel
        st.markdown("""
        <div class="control-panel">
            <div class="control-panel-header">
                <span class="icon">⚙️</span>
                <h3>Configuration</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)

        source_type = st.pills(
            "Granularity",
            ["🏛️ Districts", "🏘️ Subdistricts", "🛖 Villages", "🗺️ States"],
            default="🏛️ Districts",
            selection_mode="single"
        )

        gdf = None
        selected_feature = None
        filename = "export"

        try:
            if "Districts" in source_type:
                with st.spinner("⏳ Loading Districts..."):
                    gdf = load_file_from_url('https://drive.google.com/uc?id=1tMyiUheQBcwwPwZQla67PwC5-AqenTmv', True)
            elif "Subdistricts" in source_type:
                with st.spinner("⏳ Loading Subdistricts..."):
                    gdf = load_file_from_url('https://drive.google.com/uc?id=18lMyt2j3Xjz_Qk_2Kzppr8EVlVDx_yOv', True)
            elif "States" in source_type:
                with st.spinner("⏳ Loading States..."):
                    gdf = load_file_from_url("https://raw.githubusercontent.com/nitesh4004/GeoFormatX/main/STATE_BOUNDARY.zip", False)
            elif "Villages" in source_type:
                available_states = sorted(list(STATE_VILLAGE_IDS.keys()))
                target_state_key = st.selectbox("Select State", available_states)
                file_id = STATE_VILLAGE_IDS.get(target_state_key)
                if file_id and "Placeholder" not in file_id:
                    with st.spinner(f"⏳ Downloading {target_state_key} Villages..."):
                        gdf = load_file_from_url(f"https://drive.google.com/uc?id={file_id}", True)
                else:
                    st.warning("⚠️ Data for this state is currently unavailable.")
        except Exception:
            st.error("❌ Connection error. Please try again.")

        if gdf is not None:
            gdf = clean_text_data(gdf)

            st.divider()

            st.markdown("""
            <div class="control-panel">
                <div class="control-panel-header">
                    <span class="icon">🔍</span>
                    <h3>Filter & Select</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)

            def get_sorted_unique(df, col):
                return sorted(df[col].astype(str).unique()) if col in df.columns else []

            if 'STATE' in gdf.columns:
                states = get_sorted_unique(gdf, 'STATE')
                sel_state = st.selectbox("Select State", states)

                if "Villages" in source_type and 'District' in gdf.columns:
                    state_gdf = gdf[gdf['STATE'] == sel_state]
                    sel_district = st.selectbox("Select District", get_sorted_unique(state_gdf, 'District'))
                    dist_gdf = state_gdf[state_gdf['District'] == sel_district]

                    if 'Subdistrict' in dist_gdf.columns:
                        sel_subdistrict = st.selectbox("Select Subdistrict", get_sorted_unique(dist_gdf, 'Subdistrict'))
                        subdist_gdf = dist_gdf[dist_gdf['Subdistrict'] == sel_subdistrict]
                        selected_feature = subdist_gdf
                        filename = f"{sel_subdistrict}_Villages"
                    else:
                        selected_feature = dist_gdf
                        filename = f"{sel_district}_Villages"

                elif "Districts" in source_type:
                    state_gdf = gdf[gdf['STATE'] == sel_state]
                    sel_dist = st.selectbox("Select District", get_sorted_unique(state_gdf, 'District'))
                    selected_feature = state_gdf[state_gdf['District'] == sel_dist]
                    filename = f"{sel_dist}_{sel_state}"

                elif "Subdistricts" in source_type:
                    state_gdf = gdf[gdf['STATE'] == sel_state]
                    sel_district = st.selectbox("Select District", get_sorted_unique(state_gdf, 'District'))
                    dist_gdf = state_gdf[state_gdf['District'] == sel_district]
                    sel_sub = st.selectbox("Select Subdistrict", get_sorted_unique(dist_gdf, 'Subdistrict'))
                    selected_feature = dist_gdf[dist_gdf['Subdistrict'] == sel_sub]
                    filename = f"{sel_sub}_{sel_district}"

                else:
                    selected_feature = gdf[gdf['STATE'] == sel_state]
                    filename = f"{sel_state}_Boundary"

            st.divider()

            st.markdown("""
            <div class="control-panel">
                <div class="control-panel-header">
                    <span class="icon">💾</span>
                    <h3>Export</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)

            out_fmt = st.selectbox("Output Format", ["ESRI Shapefile (.zip)", "GeoJSON", "KML", "GeoPackage"])

            if st.button("🚀 Download Data", type="primary", use_container_width=True):
                if selected_feature is not None and not selected_feature.empty:
                    with st.spinner("📦 Packaging..."):
                        data, ext, mime = handle_export(selected_feature, out_fmt, filename)
                        if data:
                            st.download_button(
                                f"⬇️ Save {filename}{ext}",
                                data,
                                f"{filename}{ext}",
                                mime,
                                use_container_width=True
                            )

    with col_preview:
        st.markdown("""
        <div class="control-panel">
            <div class="control-panel-header">
                <span class="icon">🗺️</span>
                <h3>Preview</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if selected_feature is not None and not selected_feature.empty:
            # Stats
            st.markdown("""
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="value">""" + str(len(selected_feature)) + """</div>
                    <div class="label">Features</div>
                </div>
                <div class="stat-box">
                    <div class="value">""" + str(selected_feature.geom_type.unique()[0]) + """</div>
                    <div class="label">Geometry</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            try:
                map_data = selected_feature.to_crs(epsg=4326)
                if len(map_data) > 1000:
                    st.warning("⚠️ Large dataset. Showing 1,000 features.")
                    st.map(map_data.sample(1000))
                else:
                    st.map(map_data)
            except Exception:
                st.warning("📊 Visualization unavailable.")
        else:
            st.info("👈 Select a region to preview")

def view_data_converter():
    st.title("🔄 Universal Data Converter")
    st.markdown("Convert vector data between multiple formats with CRS transformation")

    st.markdown("""
    <div class="control-panel">
        <div class="control-panel-header">
            <span class="icon">📂</span>
            <h3>Step 1: Upload File</h3>
        </div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['zip', 'shp', 'geojson', 'kml', 'gpkg', 'csv', 'xlsx'],
        label_visibility="collapsed"
    )

    if uploaded_file:
        gdf = None
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            try:
                if file_path.endswith('.zip'):
                    gdf = extract_and_read_first(file_path, tmp_dir)
                elif file_path.endswith(('.csv', '.xlsx')):
                    df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
                    st.warning("📊 Tabular data detected. Define geometry:")
                    c1, c2, c3 = st.columns(3)
                    mode = c1.radio("Type", ["Lat/Lon", "WKT"], label_visibility="collapsed")
                    if mode == "Lat/Lon":
                        x = c2.selectbox("X (Lon)", df.columns, label_visibility="collapsed")
                        y = c3.selectbox("Y (Lat)", df.columns, label_visibility="collapsed")
                        if st.button("✓ Create Geometry", type="primary"):
                            gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[x], df[y]), crs="EPSG:4326")
                    else:
                        wkt_c = c2.selectbox("WKT Column", df.columns, label_visibility="collapsed")
                        if st.button("✓ Parse WKT", type="primary"):
                            df['geometry'] = df[wkt_c].apply(wkt.loads)
                            gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
                else:
                    gdf = gpd.read_file(file_path)
            except Exception as e:
                st.error(f"❌ Read Error: {e}")

            if gdf is not None:
                st.success(f"✅ Loaded: {len(gdf)} features | CRS: {gdf.crs}")

                col_sets, col_map = st.columns([1, 1.2], gap="large")

                with col_sets:
                    st.markdown("""
                    <div class="control-panel">
                        <div class="control-panel-header">
                            <span class="icon">⚙️</span>
                            <h3>Step 2: Convert</h3>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    enable_crs = st.checkbox("🔄 Reproject Coordinates")
                    target_epsg = st.number_input("EPSG Code", value=4326, disabled=not enable_crs)
                    target_format = st.selectbox("Output Format", ["ESRI Shapefile (.zip)", "GeoJSON", "GeoPackage (.gpkg)", "KML"])

                    if enable_crs and st.button("Apply Projection", type="secondary"):
                        gdf = convert_crs(gdf, target_epsg)
                        st.success(f"✅ Reprojected to EPSG:{target_epsg}")

                    if st.button("🚀 Convert File", type="primary", use_container_width=True):
                        with st.spinner("⏳ Converting..."):
                            data, ext, mime = handle_export(gdf, target_format, "converted_data")
                            if data:
                                st.download_button(
                                    f"⬇️ Download {target_format.split(' ')[0]}",
                                    data,
                                    f"converted{ext}",
                                    mime,
                                    use_container_width=True
                                )

                with col_map:
                    st.markdown("""
                    <div class="control-panel">
                        <div class="control-panel-header">
                            <span class="icon">🗺️</span>
                            <h3>Preview</h3>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    try:
                        st.map(gdf.to_crs(4326) if gdf.crs else gdf)
                    except:
                        st.info("Visual preview not available for this geometry type.")

def view_vector_calculator():
    st.title("🧮 Vector Calculator")
    st.markdown("Advanced geoprocessing and spatial analysis tools")

    tab1, tab2, tab3 = st.tabs(["📂 Input Data", "⚙️ Processing", "💾 Results"])

    # TAB 1: INPUT
    with tab1:
        st.markdown("""
        <div class="control-panel">
            <div class="control-panel-header">
                <span class="icon">📤</span>
                <h3>Upload Vector Layer</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader("Choose a file", type=['zip', 'shp', 'geojson', 'kml', 'gpkg'], label_visibility="collapsed")

        input_gdf = None
        if uploaded_file:
            with tempfile.TemporaryDirectory() as tmp_dir:
                file_path = os.path.join(tmp_dir, uploaded_file.name)
                with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
                try:
                    if file_path.endswith('.zip'):
                        input_gdf = extract_and_read_first(file_path, tmp_dir)
                    else:
                        input_gdf = gpd.read_file(file_path)

                    if input_gdf is not None:
                        st.session_state['input_gdf'] = input_gdf
                        st.success(f"✅ Loaded: {len(input_gdf)} features | CRS: {input_gdf.crs}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        elif 'input_gdf' in st.session_state:
            input_gdf = st.session_state['input_gdf']
            st.info(f"📌 Using: {len(input_gdf)} features")

    # TAB 2: TOOLS
    with tab2:
        if 'input_gdf' in st.session_state:
            gdf = st.session_state['input_gdf']

            col_cat, col_tool = st.columns([1, 2], gap="large")

            with col_cat:
                st.markdown("""
                <div class="control-panel">
                    <div class="control-panel-header">
                        <span class="icon">🛠️</span>
                        <h3>Tools</h3>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                category = st.radio("Category", ["Geoprocessing", "Geometry", "Analysis", "Data Management"], label_visibility="collapsed")

                tool_options = []
                if category == "Geoprocessing":
                    tool_options = ["Buffer", "Convex Hull", "Dissolve"]
                elif category == "Geometry":
                    tool_options = ["Centroids", "Simplify", "Multipart to Singlepart"]
                elif category == "Analysis":
                    tool_options = ["Basic Statistics", "Bounding Box", "Mean Coordinate"]
                elif category == "Data Management":
                    tool_options = ["Reproject Layer", "Merge Layers"]

                tool = st.selectbox("Operation", tool_options, label_visibility="collapsed")

            with col_tool:
                st.markdown("""
                <div class="control-panel">
                    <div class="control-panel-header">
                        <span class="icon">⚡</span>
                        <h3>Parameters & Execute</h3>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                res_gdf = None

                try:
                    if tool == "Buffer":
                        dist = st.number_input("Distance (Layer Units)", value=0.01, format="%.6f")
                        st.caption("⚠️ For accurate results, use projected CRS (units in meters)")
                        if st.button("▶️ Run Buffer", type="primary", use_container_width=True):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.buffer(dist)

                    elif tool == "Convex Hull":
                        st.write("Smallest convex polygon enclosing all features")
                        if st.button("▶️ Run Convex Hull", type="primary", use_container_width=True):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.convex_hull

                    elif tool == "Dissolve":
                        col = st.selectbox("Field", ["All Features"] + list(gdf.columns), label_visibility="collapsed")
                        if st.button("▶️ Run Dissolve", type="primary", use_container_width=True):
                            if col == "All Features":
                                res_gdf = gdf.dissolve()
                            else:
                                res_gdf = gdf.dissolve(by=col)

                    elif tool == "Centroids":
                        if st.button("▶️ Calculate Centroids", type="primary", use_container_width=True):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.centroid

                    elif tool == "Simplify":
                        tol = st.number_input("Tolerance", value=0.001, format="%.6f")
                        if st.button("▶️ Run Simplify", type="primary", use_container_width=True):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.simplify(tol)

                    elif tool == "Multipart to Singlepart":
                        if st.button("▶️ Explode Features", type="primary", use_container_width=True):
                            res_gdf = gdf.explode(index_parts=True).reset_index(drop=True)

                    elif tool == "Basic Statistics":
                        if st.button("▶️ Calculate Stats", type="primary", use_container_width=True):
                            res_gdf = gdf.copy()
                            res_gdf['area'] = res_gdf.geometry.area
                            res_gdf['perimeter'] = res_gdf.geometry.length
                            st.dataframe(res_gdf[['area', 'perimeter']].describe(), use_container_width=True)

                    elif tool == "Bounding Box":
                        if st.button("▶️ Generate BBox", type="primary", use_container_width=True):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.envelope

                    elif tool == "Mean Coordinate":
                        if st.button("▶️ Calculate Mean", type="primary", use_container_width=True):
                            x = gdf.geometry.centroid.x.mean()
                            y = gdf.geometry.centroid.y.mean()
                            res_gdf = gpd.GeoDataFrame({'geometry': gpd.points_from_xy([x], [y])}, crs=gdf.crs)

                    elif tool == "Reproject Layer":
                        epsg = st.number_input("EPSG Code", value=3857, step=1)
                        if st.button("▶️ Reproject", type="primary", use_container_width=True):
                            res_gdf = gdf.to_crs(epsg=epsg)

                    elif tool == "Merge Layers":
                        st.info("ℹ️ Duplicates layer (merge multiple layers coming soon)")
                        if st.button("▶️ Merge", type="primary", use_container_width=True):
                            res_gdf = pd.concat([gdf, gdf])

                    if res_gdf is not None:
                        st.session_state['calc_result_gdf'] = res_gdf
                        st.session_state['calc_result_name'] = f"{tool}_Result"
                        st.success("✅ Complete! Go to Results tab")

                except Exception as e:
                    st.error(f"❌ Failed: {e}")
        else:
            st.info("👈 Upload data in the Input Data tab first")

    # TAB 3: EXPORT
    with tab3:
        if st.session_state['calc_result_gdf'] is not None:
            res_gdf = st.session_state['calc_result_gdf']
            res_name = st.session_state['calc_result_name']

            st.markdown(f"""
            <div class="control-panel">
                <div class="control-panel-header">
                    <span class="icon">📊</span>
                    <h3>{res_name}</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Map
            try:
                st.map(res_gdf.to_crs(4326) if res_gdf.crs else res_gdf)
            except:
                st.warning("⚠️ Cannot visualize this geometry")

            st.divider()

            # Export
            c_ex1, c_ex2 = st.columns([2, 1], gap="medium")
            with c_ex1:
                fmt = st.selectbox(
                    "Output Format",
                    ["ESRI Shapefile (.zip)", "GeoJSON", "KML", "GeoPackage"],
                    key="calc_export_fmt"
                )

            with c_ex2:
                data, ext, mime = handle_export(res_gdf, fmt, res_name)
                if data:
                    st.download_button(
                        label=f"⬇️ Download {fmt.split(' ')[0]}",
                        data=data,
                        file_name=f"{res_name}{ext}",
                        mime=mime,
                        use_container_width=True,
                        type="primary"
                    )
        else:
            st.info("👈 Process data in the Processing tab first")

# --- 7. MAIN APP ---

def main():
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "home"

    # Top Navigation
    st.markdown("""
    <div style="display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap;">
    """, unsafe_allow_html=True)

    nav_cols = st.columns([1, 1, 1, 1])

    with nav_cols[0]:
        if st.button("🏠 Home", use_container_width=True, type="secondary" if st.session_state.current_tab != "home" else "primary"):
            st.session_state.current_tab = "home"
            st.rerun()

    with nav_cols[1]:
        if st.button("📥 Downloader", use_container_width=True, type="secondary" if st.session_state.current_tab != "downloader" else "primary"):
            st.session_state.current_tab = "downloader"
            st.rerun()

    with nav_cols[2]:
        if st.button("🔄 Converter", use_container_width=True, type="secondary" if st.session_state.current_tab != "converter" else "primary"):
            st.session_state.current_tab = "converter"
            st.rerun()

    with nav_cols[3]:
        if st.button("🧮 Calculator", use_container_width=True, type="secondary" if st.session_state.current_tab != "calculator" else "primary"):
            st.session_state.current_tab = "calculator"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # Route to current page
    if st.session_state.current_tab == "home":
        view_home()
    elif st.session_state.current_tab == "downloader":
        view_admin_downloader()
    elif st.session_state.current_tab == "converter":
        view_data_converter()
    elif st.session_state.current_tab == "calculator":
        view_vector_calculator()

    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; padding: 1rem; color: #666; font-size: 0.9rem;">
        <p>🌍 GeoFormatX v5.0 | Advanced Geospatial Toolkit | <a href="#" style="color: #0068C9; text-decoration: none;">Learn More</a></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
