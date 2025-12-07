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
import shapely

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="GeoFormatX Ultimate",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enable KML drivers
fiona.drvsupport.supported_drivers['KML'] = 'rw'
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'

# Session State Initialization
if 'calc_result_gdf' not in st.session_state:
    st.session_state['calc_result_gdf'] = None
if 'calc_result_name' not in st.session_state:
    st.session_state['calc_result_name'] = "result"
if 'input_gdf' not in st.session_state:
    st.session_state['input_gdf'] = None
if 'overlay_gdf' not in st.session_state:
    st.session_state['overlay_gdf'] = None

# --- 2. CLEAN MINIMALIST STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    code, pre {
        font-family: 'Space Mono', monospace;
    }

    /* === MINIMALIST CARD STYLING === */
    .minimal-card {
        background: #FFFFFF;
        border: none;
        border-left: 4px solid #0068C9;
        border-radius: 4px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        transition: all 0.2s ease;
    }

    .minimal-card:hover {
        box-shadow: 0 4px 12px rgba(0,104,201,0.15);
    }

    .minimal-card h2, .minimal-card h3 {
        margin-top: 0;
        color: #1a1a1a;
        font-weight: 600;
        letter-spacing: -0.3px;
    }

    .minimal-card p {
        color: #555555;
        line-height: 1.6;
        margin: 0.5rem 0;
    }
    
    .guideline-box {
        background-color: #f8f9fa;
        border-radius: 4px;
        padding: 1rem;
        font-size: 0.9rem;
        border: 1px solid #e9ecef;
        margin-bottom: 1rem;
    }
    
    .guideline-header {
        font-weight: 600;
        color: #0068C9;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    @media (prefers-color-scheme: dark) {
        .minimal-card {
            background: #1E1E1E;
            border-left-color: #0068C9;
        }
        .minimal-card h2, .minimal-card h3 {
            color: #FFFFFF;
        }
        .minimal-card p {
            color: #CCCCCC;
        }
        .guideline-box {
            background-color: #262730;
            border-color: #363945;
            color: #FAFAFA;
        }
    }

    /* === SECTION DIVIDER === */
    .section-break {
        height: 1px;
        background: linear-gradient(90deg, transparent, #0068C9, transparent);
        margin: 2rem 0;
        opacity: 0.3;
    }

    /* === SIDEBAR STYLING === */
    .sidebar-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #0068C9;
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
    }

    .sidebar-subtitle {
        font-size: 0.85rem;
        color: #999999;
        margin-bottom: 1.5rem;
        font-weight: 400;
    }

    .sidebar-section {
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid rgba(0,104,201,0.1);
    }

    .sidebar-section:last-child {
        border-bottom: none;
    }

    /* === BUTTON STYLING === */
    .stButton > button {
        background-color: #0068C9;
        color: white;
        border: none;
        border-radius: 4px;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
        transition: all 0.2s ease;
        letter-spacing: 0.2px;
    }

    .stButton > button:hover {
        background-color: #0053a6;
        box-shadow: 0 4px 12px rgba(0,104,201,0.25);
        transform: translateY(-1px);
    }

    /* === INPUT STYLING === */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stNumberInput > div > div > input {
        border: 1px solid #DDDDDD;
        border-radius: 4px;
        padding: 0.6rem 0.8rem;
        font-family: 'Outfit', sans-serif;
    }

    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #0068C9;
        box-shadow: 0 0 0 2px rgba(0,104,201,0.1);
    }

    /* === METRIC STYLING === */
    .metric-item {
        display: inline-block;
        padding: 0.75rem 1.5rem;
        background: #F5F7FA;
        border-radius: 4px;
        margin-right: 1rem;
        margin-bottom: 0.5rem;
        border-left: 3px solid #0068C9;
    }

    .metric-label {
        font-size: 0.8rem;
        color: #0068C9;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1a1a1a;
    }

    @media (prefers-color-scheme: dark) {
        .metric-item {
            background: #2a2a2a;
        }
        .metric-value {
            color: #FFFFFF;
        }
    }

    /* === TABS (Minimal) === */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 2px solid #EEEEEE;
    }

    .stTabs [data-baseweb="tab"] {
        border-bottom: 3px solid transparent;
        border-radius: 0;
        padding: 1rem 1.5rem;
        font-weight: 500;
        color: #999999;
    }

    .stTabs [aria-selected="true"] {
        border-bottom-color: #0068C9;
        color: #0068C9;
    }

    /* === ALERTS === */
    .stSuccess, .stWarning, .stError, .stInfo {
        border-radius: 4px;
        border-left: 4px solid;
    }

    .stSuccess {
        border-left-color: #10B981;
    }

    .stWarning {
        border-left-color: #F59E0B;
    }

    .stError {
        border-left-color: #EF4444;
    }

    .stInfo {
        border-left-color: #0068C9;
    }

    /* === EXPANDER === */
    .streamlit-expanderHeader {
        border-left: 3px solid #0068C9;
        padding-left: 0.75rem;
    }
    
    /* === COLUMNS PADDING === */
    [data-testid="column"] {
        padding: 0 0.5rem;
    }

    /* === HEADER STYLING === */
    h1 {
        color: #1a1a1a;
        border-bottom: 3px solid #0068C9;
        padding-bottom: 0.75rem;
    }

    @media (prefers-color-scheme: dark) {
        h1 {
            color: #FFFFFF;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA CONSTANTS (Complete) ---
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

def render_guideline(title, content):
    st.markdown(f"""
    <div class="guideline-box">
        <div class="guideline-header">💡 Guideline: {title}</div>
        {content}
    </div>
    """, unsafe_allow_html=True)

# --- 5. MODULES ---

def view_admin_downloader():
    st.title("📥 Administrative Boundaries Downloader")

    st.markdown("""
    <div class="minimal-card">
        <p>Download official administrative boundaries for India at multiple granularity levels. 
        Select your desired level, filter by state/district, and download in your preferred format.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📖 User Guide: How to use the Downloader"):
        st.markdown("""
        1.  **Select Granularity:** Choose between States, Districts, Subdistricts (Tehsils), or Villages.
        2.  **Filter Data:** Depending on the granularity, use the dropdown menus to narrow down the specific region you need.
        3.  **Choose Format:** Select a GIS format (Shapefile, GeoJSON, KML, or GeoPackage).
        4.  **Download:** Click the button to process and download the file.
        
        *Note: Village maps are large files and may take a moment to process.*
        """)

    col_left, col_right = st.columns([1.3, 1.7], gap="large")

    with col_left:
        st.markdown('<div class="minimal-card"><h3>Configuration</h3>', unsafe_allow_html=True)

        source_type = st.pills(
            "Data Granularity",
            ["🏛️ Districts", "🏘️ Subdistricts", "🛖 Villages", "🗺️ States"],
            default="🏛️ Districts",
            selection_mode="single"
        )

        st.markdown("</div>", unsafe_allow_html=True)

        gdf = None
        selected_feature = None
        filename = "export"

        try:
            if "Districts" in source_type:
                with st.spinner("Loading Districts..."):
                    gdf = load_file_from_url('https://drive.google.com/uc?id=1tMyiUheQBcwwPwZQla67PwC5-AqenTmv', True)
            elif "Subdistricts" in source_type:
                with st.spinner("Loading Subdistricts..."):
                    gdf = load_file_from_url('https://drive.google.com/uc?id=18lMyt2j3Xjz_Qk_2Kzppr8EVlVDx_yOv', True)
            elif "States" in source_type:
                with st.spinner("Loading States..."):
                    gdf = load_file_from_url("https://raw.githubusercontent.com/nitesh4004/GeoFormatX/main/STATE_BOUNDARY.zip", False)
            elif "Villages" in source_type:
                available_states = sorted(list(STATE_VILLAGE_IDS.keys()))
                target_state_key = st.selectbox("Select State", available_states)
                file_id = STATE_VILLAGE_IDS.get(target_state_key)
                if file_id and "Placeholder" not in file_id:
                    with st.spinner(f"Downloading {target_state_key} Village Map..."):
                        gdf = load_file_from_url(f"https://drive.google.com/uc?id={file_id}", True)
                else:
                    st.warning("Data for this state is currently offline.")
        except Exception:
            st.error("Connection error. Please try again.")

        if gdf is not None:
            gdf = clean_text_data(gdf)

            st.markdown('<div class="minimal-card"><h3>Filter Region</h3>', unsafe_allow_html=True)

            def get_sorted_unique(df, col):
                return sorted(df[col].astype(str).unique()) if col in df.columns else []

            if 'STATE' in gdf.columns:
                states = get_sorted_unique(gdf, 'STATE')
                sel_state = st.selectbox("State", states, label_visibility="collapsed")

                if "Villages" in source_type and 'District' in gdf.columns:
                    state_gdf = gdf[gdf['STATE'] == sel_state]
                    sel_district = st.selectbox("District", get_sorted_unique(state_gdf, 'District'), label_visibility="collapsed")
                    dist_gdf = state_gdf[state_gdf['District'] == sel_district]

                    if 'Subdistrict' in dist_gdf.columns:
                        sel_subdistrict = st.selectbox("Subdistrict", get_sorted_unique(dist_gdf, 'Subdistrict'), label_visibility="collapsed")
                        subdist_gdf = dist_gdf[dist_gdf['Subdistrict'] == sel_subdistrict]
                        selected_feature = subdist_gdf
                        filename = f"{sel_subdistrict}_Villages"
                    else:
                        selected_feature = dist_gdf
                        filename = f"{sel_district}_Villages"

                elif "Districts" in source_type:
                    state_gdf = gdf[gdf['STATE'] == sel_state]
                    sel_dist = st.selectbox("District", get_sorted_unique(state_gdf, 'District'), label_visibility="collapsed")
                    selected_feature = state_gdf[state_gdf['District'] == sel_dist]
                    filename = f"{sel_dist}_{sel_state}"

                elif "Subdistricts" in source_type:
                    state_gdf = gdf[gdf['STATE'] == sel_state]
                    sel_district = st.selectbox("District", get_sorted_unique(state_gdf, 'District'), label_visibility="collapsed")
                    dist_gdf = state_gdf[state_gdf['District'] == sel_district]
                    sel_sub = st.selectbox("Subdistrict", get_sorted_unique(dist_gdf, 'Subdistrict'), label_visibility="collapsed")
                    selected_feature = dist_gdf[dist_gdf['Subdistrict'] == sel_sub]
                    filename = f"{sel_sub}_{sel_district}"

                else:
                    selected_feature = gdf[gdf['STATE'] == sel_state]
                    filename = f"{sel_state}_Boundary"

            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="minimal-card"><h3>Export Settings</h3>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                out_fmt = st.selectbox("Format", ["ESRI Shapefile (.zip)", "GeoJSON", "KML", "GeoPackage"], label_visibility="collapsed")
            with col2:
                if st.button("Download", type="primary", use_container_width=True):
                    if selected_feature is not None and not selected_feature.empty:
                        with st.spinner("Packaging data..."):
                            data, ext, mime = handle_export(selected_feature, out_fmt, filename)
                            if data:
                                st.download_button(
                                    f"Save {filename}{ext}",
                                    data,
                                    f"{filename}{ext}",
                                    mime,
                                    use_container_width=True
                                )
            st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="minimal-card"><h3>Preview & Statistics</h3>', unsafe_allow_html=True)

        if selected_feature is not None and not selected_feature.empty:
            st.markdown(f"""
            <div class="metric-item">
                <div class="metric-label">Features</div>
                <div class="metric-value">{len(selected_feature)}</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Geometry Type</div>
                <div class="metric-value">{selected_feature.geom_type.unique()[0]}</div>
            </div>
            """, unsafe_allow_html=True)

            try:
                map_data = selected_feature.to_crs(epsg=4326)
                if len(map_data) > 1000:
                    st.info("Large dataset - showing 1000 features")
                    st.map(map_data.sample(1000))
                else:
                    st.map(map_data)
            except Exception:
                st.warning("Visualization unavailable")
        else:
            st.info("Select a region to preview")

        st.markdown("</div>", unsafe_allow_html=True)


def view_data_converter():
    st.title("🔄 Format Converter")

    st.markdown("""
    <div class="minimal-card">
        <p>Convert between different geospatial vector formats. Supports Shapefile, GeoJSON, KML, 
        and GeoPackage with optional CRS transformation.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📖 User Guide: How to convert data"):
        st.markdown("""
        1.  **Upload:** Drop a file (Zip containing Shapefile, GeoJSON, KML, CSV, or Excel).
        2.  **CSV/Excel Handling:** If uploading tabular data, you must specify which columns contain Latitude/Longitude or WKT (Well-Known Text) geometry.
        3.  **Coordinate Reference System (CRS):** You can optionally reproject the data to a new system (e.g., EPSG:3857 for web mapping).
        4.  **Convert:** Select the target format and download the result.
        """)

    st.markdown('<div class="minimal-card"><h3>Step 1: Upload File</h3>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Choose file",
        type=['zip', 'shp', 'geojson', 'kml', 'gpkg', 'csv', 'xlsx'],
        label_visibility="collapsed"
    )

    st.markdown("</div>", unsafe_allow_html=True)

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
                    st.warning("Tabular data detected - define geometry")
                    c1, c2, c3 = st.columns(3)
                    mode = c1.radio("Type", ["Lat/Lon", "WKT"], label_visibility="collapsed")
                    if mode == "Lat/Lon":
                        x = c2.selectbox("Lon", df.columns, label_visibility="collapsed", help="Select Longitude Column")
                        y = c3.selectbox("Lat", df.columns, label_visibility="collapsed", help="Select Latitude Column")
                        if st.button("Create Geometry", type="primary"):
                            gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[x], df[y]), crs="EPSG:4326")
                    else:
                        wkt_c = c2.selectbox("WKT Column", df.columns, label_visibility="collapsed")
                        if st.button("Parse WKT", type="primary"):
                            df['geometry'] = df[wkt_c].apply(wkt.loads)
                            gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
                else:
                    gdf = gpd.read_file(file_path)
            except Exception as e:
                st.error(f"Error: {e}")

            if gdf is not None:
                st.success(f"Loaded: {len(gdf)} features | CRS: {gdf.crs}")

                col_convert, col_preview = st.columns([1, 1.2], gap="large")

                with col_convert:
                    st.markdown('<div class="minimal-card"><h3>Step 2: Configure Conversion</h3>', unsafe_allow_html=True)

                    enable_crs = st.checkbox("Transform CRS (Reprojection)", help="Check this to change the coordinate system.")
                    target_epsg = st.number_input("EPSG Code", value=4326, disabled=not enable_crs, help="Enter the target EPSG code (e.g., 4326 for WGS84, 3857 for Web Mercator).")
                    target_format = st.selectbox("Output Format", ["ESRI Shapefile (.zip)", "GeoJSON", "GeoPackage (.gpkg)", "KML"], label_visibility="collapsed")

                    if enable_crs and st.button("Apply CRS Transform", type="secondary"):
                        gdf = convert_crs(gdf, target_epsg)
                        st.success(f"Reprojected to EPSG:{target_epsg}")

                    if st.button("Convert & Download", type="primary", use_container_width=True):
                        with st.spinner("Converting..."):
                            data, ext, mime = handle_export(gdf, target_format, "converted_data")
                            if data:
                                st.download_button(
                                    f"Save converted{ext}",
                                    data,
                                    f"converted{ext}",
                                    mime,
                                    use_container_width=True
                                )
                    st.markdown("</div>", unsafe_allow_html=True)

                with col_preview:
                    st.markdown('<div class="minimal-card"><h3>Preview</h3>', unsafe_allow_html=True)
                    try:
                        st.map(gdf.to_crs(4326) if gdf.crs else gdf)
                    except:
                        st.info("Visual preview not available")
                    st.markdown("</div>", unsafe_allow_html=True)

def view_vector_calculator():
    st.title("🧮 Vector Calculator")

    st.markdown("""
    <div class="minimal-card">
        <p>Perform advanced spatial analysis and geoprocessing operations. 
        Features include Overlay analysis, Spatial Joins, and Topology repairs.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("📖 User Guide: Vector Calculator"):
        st.markdown("""
        1.  **Input Data:** Upload your primary vector layer (Points, Lines, or Polygons).
        2.  **Processing Tools:** Select a category (Geoprocessing, Analysis, Overlay, etc.).
        3.  **Parameters:** Configure the specific tool (e.g., buffer distance in degrees).
        4.  **Results:** View the output on the map and export it in your desired format.
        
        *Tip: For Overlay and Spatial Join tools, you will need to upload a secondary layer.*
        """)

    tab1, tab2, tab3 = st.tabs(["1. Input Data", "2. Processing Tools", "3. Results"])

    with tab1:
        st.markdown('<div class="minimal-card"><h3>Primary Layer</h3>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload Primary Layer", type=['zip', 'shp', 'geojson', 'kml', 'gpkg'], label_visibility="collapsed", key="primary_up")

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
                        st.success(f"Primary Layer Loaded: {len(input_gdf)} features")
                except Exception as e:
                    st.error(f"Error: {e}")
        
        if st.session_state['input_gdf'] is not None:
             st.info(f"Active Primary Layer: {len(st.session_state['input_gdf'])} features")

        st.markdown("</div>", unsafe_allow_html=True)
        
        # Secondary Layer Uploader for Overlay/Join
        st.markdown('<div class="minimal-card"><h3>Secondary Layer (Optional)</h3>', unsafe_allow_html=True)
        st.caption("Required only for Overlay and Spatial Join operations.")
        uploaded_overlay = st.file_uploader("Upload Secondary Layer", type=['zip', 'shp', 'geojson', 'kml', 'gpkg'], label_visibility="collapsed", key="sec_up")
        
        if uploaded_overlay:
            with tempfile.TemporaryDirectory() as tmp_dir:
                file_path = os.path.join(tmp_dir, uploaded_overlay.name)
                with open(file_path, "wb") as f: f.write(uploaded_overlay.getbuffer())
                try:
                    if file_path.endswith('.zip'):
                        overlay_gdf = extract_and_read_first(file_path, tmp_dir)
                    else:
                        overlay_gdf = gpd.read_file(file_path)
                    
                    if overlay_gdf is not None:
                        st.session_state['overlay_gdf'] = overlay_gdf
                        st.success(f"Secondary Layer Loaded: {len(overlay_gdf)} features")
                except Exception as e:
                    st.error(f"Error loading secondary layer: {e}")

        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        if 'input_gdf' in st.session_state and st.session_state['input_gdf'] is not None:
            gdf = st.session_state['input_gdf']
            sec_gdf = st.session_state.get('overlay_gdf')

            col_tool, col_param = st.columns([1, 1.5], gap="large")

            with col_tool:
                st.markdown('<div class="minimal-card"><h3>Tool Selection</h3>', unsafe_allow_html=True)

                category = st.selectbox("Category", ["Geoprocessing", "Geometry", "Analysis", "Overlay Operations", "Data Management"], label_visibility="collapsed")

                tool_options = []
                if category == "Geoprocessing":
                    tool_options = ["Buffer", "Convex Hull", "Dissolve"]
                elif category == "Geometry":
                    tool_options = ["Centroids", "Simplify", "Explode", "Fix Geometries"]
                elif category == "Analysis":
                    tool_options = ["Statistics", "Bounding Box", "Mean Coordinate"]
                elif category == "Overlay Operations":
                    tool_options = ["Intersection", "Difference", "Union", "Spatial Join"]
                elif category == "Data Management":
                    tool_options = ["Reproject", "Merge"]

                tool = st.selectbox("Operation", tool_options, label_visibility="collapsed")
                st.markdown("</div>", unsafe_allow_html=True)

            with col_param:
                st.markdown('<div class="minimal-card"><h3>Parameters</h3>', unsafe_allow_html=True)

                res_gdf = None

                try:
                    # --- Geoprocessing ---
                    if tool == "Buffer":
                        render_guideline("Buffer", "Creates a polygon surrounding the geometry at a specified distance. Distance units depend on the CRS (e.g., degrees for WGS84, meters for UTM).")
                        dist = st.number_input("Distance (units)", value=0.01, format="%.6f")
                        if st.button("Execute Buffer", type="primary", use_container_width=True):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.buffer(dist)

                    elif tool == "Convex Hull":
                        render_guideline("Convex Hull", "Creates the smallest convex polygon that encloses all points in the geometry (like wrapping a rubber band around nails).")
                        if st.button("Execute Convex Hull", type="primary", use_container_width=True):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.convex_hull

                    elif tool == "Dissolve":
                        render_guideline("Dissolve", "Aggregates features based on a specific attribute. Similar to 'Group By' in SQL.")
                        col = st.selectbox("Field", ["All"] + list(gdf.columns), label_visibility="collapsed")
                        if st.button("Execute Dissolve", type="primary", use_container_width=True):
                            res_gdf = gdf.dissolve() if col == "All" else gdf.dissolve(by=col)

                    # --- Geometry ---
                    elif tool == "Centroids":
                        render_guideline("Centroids", "Converts polygons or lines into a single point representing the geometric center.")
                        if st.button("Calculate Centroids", type="primary", use_container_width=True):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.centroid

                    elif tool == "Simplify":
                        render_guideline("Simplify", "Reduces the number of vertices in a geometry while preserving its shape (Douglas-Peucker algorithm).")
                        tol = st.number_input("Tolerance", value=0.001, format="%.6f")
                        if st.button("Execute Simplify", type="primary", use_container_width=True):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.simplify(tol)
                            
                    elif tool == "Explode":
                        render_guideline("Explode", "Separates Multipart features (e.g., a set of islands stored as one row) into Singlepart features (one row per island).")
                        if st.button("Execute Explode", type="primary", use_container_width=True):
                            res_gdf = gdf.explode(index_parts=True).reset_index(drop=True)

                    elif tool == "Fix Geometries":
                        render_guideline("Fix Geometries", "Attempts to repair invalid geometries (e.g., self-intersections) by applying a zero-distance buffer.")
                        if st.button("Execute Repair", type="primary", use_container_width=True):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.buffer(0)

                    # --- Analysis ---
                    elif tool == "Statistics":
                        render_guideline("Statistics", "Calculates basic geometric properties like Area and Perimeter.")
                        if st.button("Calculate Stats", type="primary", use_container_width=True):
                            res_gdf = gdf.copy()
                            res_gdf['area'] = res_gdf.geometry.area
                            res_gdf['perimeter'] = res_gdf.geometry.length
                            st.dataframe(res_gdf[['area', 'perimeter']].describe(), use_container_width=True)

                    elif tool == "Bounding Box":
                        render_guideline("Bounding Box", "Creates a rectangular box representing the maximum extents of each feature.")
                        if st.button("Generate BBox", type="primary", use_container_width=True):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.envelope

                    elif tool == "Mean Coordinate":
                        render_guideline("Mean Coordinate", "Calculates the average X and Y center of all features combined.")
                        if st.button("Calculate Mean", type="primary", use_container_width=True):
                            x = gdf.geometry.centroid.x.mean()
                            y = gdf.geometry.centroid.y.mean()
                            res_gdf = gpd.GeoDataFrame({'geometry': gpd.points_from_xy([x], [y])}, crs=gdf.crs)

                    # --- Overlay Operations (Replaces Advanced GIS Tools) ---
                    elif tool in ["Intersection", "Difference", "Union", "Spatial Join"]:
                        if sec_gdf is None:
                            st.error("⚠️ Secondary Layer required for Overlay operations. Please upload it in the 'Input Data' tab.")
                        else:
                            # Ensure CRS match
                            if gdf.crs != sec_gdf.crs:
                                st.warning(f"CRS Mismatch detected. Reprojecting Secondary Layer to match Primary ({gdf.crs}).")
                                sec_gdf = sec_gdf.to_crs(gdf.crs)

                            if tool == "Intersection":
                                render_guideline("Intersection", "Returns the area common to both layers (AND operation).")
                                if st.button("Run Intersection", type="primary"):
                                    res_gdf = gpd.overlay(gdf, sec_gdf, how='intersection')
                            
                            elif tool == "Difference":
                                render_guideline("Difference", "Subtracts the Secondary Layer area from the Primary Layer (NOT operation).")
                                if st.button("Run Difference", type="primary"):
                                    res_gdf = gpd.overlay(gdf, sec_gdf, how='difference')
                                    
                            elif tool == "Union":
                                render_guideline("Union", "Combines all features from both layers (OR operation).")
                                if st.button("Run Union", type="primary"):
                                    res_gdf = gpd.overlay(gdf, sec_gdf, how='union')

                            elif tool == "Spatial Join":
                                render_guideline("Spatial Join", "Joins attributes from the Secondary Layer to the Primary Layer based on spatial location.")
                                op = st.selectbox("Join Predicate", ["intersects", "contains", "within"], index=0)
                                if st.button("Run Spatial Join", type="primary"):
                                    res_gdf = gpd.sjoin(gdf, sec_gdf, how="inner", predicate=op)

                    # --- Data Management ---
                    elif tool == "Reproject":
                        render_guideline("Reproject", "Transforms data to a new Coordinate Reference System (EPSG code).")
                        epsg = st.number_input("Target EPSG Code", value=3857)
                        if st.button("Execute Reproject", type="primary", use_container_width=True):
                            res_gdf = gdf.to_crs(epsg=epsg)

                    elif tool == "Merge":
                        render_guideline("Merge", "Duplicates the current layer and appends it to itself (demonstration of appending data).")
                        if st.button("Execute Merge", type="primary", use_container_width=True):
                            res_gdf = pd.concat([gdf, gdf])

                    if res_gdf is not None:
                        st.session_state['calc_result_gdf'] = res_gdf
                        st.session_state['calc_result_name'] = f"{tool}_Result"
                        st.success("Processing Complete! Go to 'Results' tab to download.")

                except Exception as e:
                    st.error(f"Processing Error: {e}")

                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Please upload a Primary Layer in the 'Input Data' tab first.")

    with tab3:
        if st.session_state['calc_result_gdf'] is not None:
            res_gdf = st.session_state['calc_result_gdf']
            res_name = st.session_state['calc_result_name']

            st.markdown(f'<div class="minimal-card"><h3>{res_name}</h3>', unsafe_allow_html=True)

            try:
                st.map(res_gdf.to_crs(4326) if res_gdf.crs else res_gdf)
            except:
                st.warning("Cannot visualize result (likely non-spatial or empty).")

            col1, col2 = st.columns(2)
            with col1:
                fmt = st.selectbox("Format", ["ESRI Shapefile (.zip)", "GeoJSON", "KML", "GeoPackage"], key="calc_fmt")
            with col2:
                data, ext, mime = handle_export(res_gdf, fmt, res_name)
                if data:
                    st.download_button(f"Download {fmt.split()[0]}", data, f"{res_name}{ext}", mime, use_container_width=True)

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("No results generated yet.")

def main():
    # Sidebar Navigation
    with st.sidebar:
        st.markdown('<p class="sidebar-title">🌍 GeoFormatX</p>', unsafe_allow_html=True)
        st.markdown('<p class="sidebar-subtitle">Advanced Geospatial Toolkit v5.0</p>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        mode = st.radio("Modules", 
                       ["📥 Admin Downloader", "🔄 Converter", "🧮 Vector Calculator"],
                       label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("**Quick Info**")
        st.caption("Convert, transform, and analyze geospatial vector data.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("**Supported Formats**")
        st.markdown("- Shapefile (SHP)")
        st.markdown("- GeoJSON")
        st.markdown("- KML")
        st.markdown("- GeoPackage (GPKG)")
        st.markdown("- CSV / Excel")
        st.markdown("</div>", unsafe_allow_html=True)

    # Main Content
    if mode == "📥 Admin Downloader":
        view_admin_downloader()
    elif mode == "🔄 Converter":
        view_data_converter()
    elif mode == "🧮 Vector Calculator":
        view_vector_calculator()

    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; font-size: 0.85rem; color: #999; margin-top: 2rem;">
        <p>GeoFormatX v5.0 | Geospatial Data Processing Platform</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
