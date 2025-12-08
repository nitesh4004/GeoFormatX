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
import folium
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="GeoFormatX Pro",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enable KML drivers
fiona.drvsupport.supported_drivers['KML'] = 'rw'
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'

# Session State Initialization
keys = ['main_gdf', 'secondary_gdf', 'calc_result_gdf', 'calc_result_name', 'river_gdf']
for k in keys:
    if k not in st.session_state:
        st.session_state[k] = None

# --- 2. DUAL-MODE ADAPTIVE STYLING ---
st.markdown("""
    <style>
    /* 1. FIX CLIPPING & SPACING */
    .block-container {
        padding-top: 2.5rem !important; /* Increased to prevent top text clipping */
        padding-bottom: 1rem;
    }
    
    /* 2. SIDEBAR TITLE (APP NAME) - INCREASE SIZE */
    [data-testid="stSidebar"] h1 {
        font-size: 3rem !important; /* Much larger */
        font-weight: 800 !important;
        background: -webkit-linear-gradient(45deg, #0068C9, #00E5FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-top: 1rem !important;
        margin-bottom: 1rem !important;
    }

    /* 3. CONTENT HEADERS (e.g., "Administrative Boundaries") - REDUCE SIZE */
    h2 {
        font-size: 1.5rem !important; /* Reduced size */
        font-weight: 600 !important;
        padding-top: 10px !important; /* Extra padding to stop black line clipping */
        margin-bottom: 0.5rem !important;
        line-height: 1.4 !important; /* Better line spacing */
    }

    /* ADAPTIVE METRIC CARDS */
    div[data-testid="stMetric"] {
        background-color: var(--secondary-background-color); 
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #0068C9;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        color: var(--text-color);
    }

    /* MAP BORDER */
    iframe {
        border-radius: 8px;
        border: 1px solid rgba(128, 128, 128, 0.2); 
    }
    
    /* CUSTOM TOAST */
    div[data-testid="stToast"] {
        background-color: var(--secondary-background-color);
        color: var(--text-color);
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
            if response.status_code != 200: return None
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
    if gdf.crs is None: gdf.set_crs(epsg=4326, inplace=True)
    return gdf.to_crs(epsg=target_epsg)

def render_map(gdf_list, height=600):
    """
    Renders interactive Folium map with Google Hybrid tiles.
    gdf_list: list of tuples (gdf, layer_name, color)
    """
    if not gdf_list or gdf_list[0][0] is None:
        # Default view of India
        m = folium.Map(location=[20.5937, 78.9629], zoom_start=4, tiles=None)
    else:
        # Center map on first layer
        first_gdf = gdf_list[0][0]
        if first_gdf.crs != "EPSG:4326": 
            first_gdf = first_gdf.to_crs(epsg=4326)
        
        bounds = first_gdf.total_bounds
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles=None)

    # Add Google Hybrid Layer (Satellite + Roads/Labels)
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', # lyrs=y for Hybrid
        attr='Google',
        name='Google Hybrid',
        overlay=False,
        control=True
    ).add_to(m)

    # Add Layers
    for gdf, name, color in gdf_list:
        if gdf is not None:
            if gdf.crs != "EPSG:4326": gdf = gdf.to_crs(epsg=4326)
            
            tooltip_cols = list(gdf.columns[:3]) if len(gdf.columns) > 0 else None
            
            folium.GeoJson(
                gdf,
                name=name,
                style_function=lambda x, color=color: {
                    'fillColor': color, 
                    'color': color, 
                    'weight': 2, 
                    'fillOpacity': 0.5 
                },
                tooltip=folium.GeoJsonTooltip(fields=tooltip_cols) if tooltip_cols else None
            ).add_to(m)

    folium.LayerControl().add_to(m)
    return st_folium(m, height=height, use_container_width=True)

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

# --- 5. MAIN APP ---

def main():
    # --- NAVIGATION SIDEBAR ---
    with st.sidebar:
        st.title("GeoFormatX") # Now targets h1 in sidebar with larger font
        st.caption("Professional Geospatial Suite v5.0")
        
        # Transparent background for container to adapt to sidebar color
        selected = option_menu(
            menu_title=None,
            options=["Admin Data", "Rivers", "Converter", "Vector Calculator"],
            icons=["building", "water", "arrow-repeat", "calculator"],
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "orange", "font-size": "18px"}, 
                "nav-link": {"font-size": "15px", "text-align": "left", "margin":"0px", "--hover-color": "var(--secondary-background-color)"},
                "nav-link-selected": {"background-color": "#0068C9", "color": "white"},
            }
        )
        st.divider()
        st.markdown("**User Guide**")
        st.info("💡 Map set to Google Hybrid (Satellite + Labels).")

    # --- 1. ADMIN DOWNLOADER MODULE ---
    if selected == "Admin Data":
        st.markdown("## 🏛️ Administrative Boundaries") # H2 - Reduced size via CSS
        
        col_ctrl, col_map = st.columns([1, 2.5], gap="medium")
        
        with col_ctrl:
            with st.container(border=True):
                st.subheader("1. Select Source")
                source_type = st.selectbox("Granularity", ["Districts", "Subdistricts", "Villages", "States"])
                
                # Dynamic Logic for Village States
                target_state_key = None
                if source_type == "Villages":
                    available_states = sorted(list(STATE_VILLAGE_IDS.keys()))
                    target_state_key = st.selectbox("Select State", available_states)

                if st.button("Load Data Source", type="primary", use_container_width=True):
                    with st.spinner("Fetching dataset..."):
                        gdf = None
                        if source_type == "Districts":
                            gdf = load_file_from_url('https://drive.google.com/uc?id=1tMyiUheQBcwwPwZQla67PwC5-AqenTmv', True)
                        elif source_type == "Subdistricts":
                            gdf = load_file_from_url('https://drive.google.com/uc?id=18lMyt2j3Xjz_Qk_2Kzppr8EVlVDx_yOv', True)
                        elif source_type == "States":
                            gdf = load_file_from_url("https://raw.githubusercontent.com/nitesh4004/GeoFormatX/main/STATE_BOUNDARY.zip", False)
                        elif source_type == "Villages" and target_state_key:
                             file_id = STATE_VILLAGE_IDS.get(target_state_key)
                             if "Placeholder" not in file_id:
                                 gdf = load_file_from_url(f"https://drive.google.com/uc?id={file_id}", True)
                             else:
                                 st.error("State data unavailable.")
                        
                        if gdf is not None:
                            st.session_state['main_gdf'] = clean_text_data(gdf)
                            st.toast("Dataset loaded successfully!", icon="✅")
                        else:
                            st.error("Failed to load data.")

            # Filtering & Export
            if st.session_state['main_gdf'] is not None:
                gdf = st.session_state['main_gdf']
                with st.container(border=True):
                    st.subheader("2. Filter Region")
                    
                    final_selection = gdf
                    filename = "export"
                    
                    if 'STATE' in gdf.columns:
                        states = sorted(gdf['STATE'].astype(str).unique())
                        sel_state = st.selectbox("State", states)
                        final_selection = gdf[gdf['STATE'] == sel_state]
                        filename = sel_state
                        
                        if 'District' in gdf.columns:
                            dists = sorted(final_selection['District'].astype(str).unique())
                            sel_dist = st.selectbox("District", ["All"] + dists)
                            if sel_dist != "All":
                                final_selection = final_selection[final_selection['District'] == sel_dist]
                                filename = f"{sel_dist}_{sel_state}"
                                
                                if 'Subdistrict' in gdf.columns:
                                    subs = sorted(final_selection['Subdistrict'].astype(str).unique())
                                    sel_sub = st.selectbox("Subdistrict", ["All"] + subs)
                                    if sel_sub != "All":
                                        final_selection = final_selection[final_selection['Subdistrict'] == sel_sub]
                                        filename = f"{sel_sub}_{sel_dist}"

                    st.markdown(f"**Selected Features:** `{len(final_selection)}`")
                    
                    st.subheader("3. Export")
                    fmt = st.selectbox("Format", ["ESRI Shapefile (.zip)", "GeoJSON", "KML", "GeoPackage"])
                    if st.button("Download Selection", use_container_width=True):
                        d, e, m = handle_export(final_selection, fmt, filename)
                        if d: st.download_button("Save File", d, f"{filename}{e}", m, use_container_width=True)
                        
        with col_map:
            current_data = locals().get('final_selection', st.session_state['main_gdf'])
            # Use Bright Blue (#3388ff) which contrasts well against Hybrid Map
            render_map([(current_data, "Admin Boundary", "#3388ff")])
            
            if current_data is not None:
                with st.expander("📊 View Attribute Table"):
                    st.dataframe(current_data.drop(columns='geometry'), use_container_width=True)


    # --- 2. RIVER DOWNLOADER MODULE ---
    elif selected == "Rivers":
        st.markdown("## 🌊 River Network Analysis")
        col_ctrl, col_map = st.columns([1, 2.5], gap="medium")
        
        with col_ctrl:
            with st.container(border=True):
                st.subheader("Selection Panel")
                river_url = "https://github.com/nitesh4004/GeoFormatX/raw/main/Rivers.zip"
                
                if 'river_gdf' not in st.session_state or st.session_state['river_gdf'] is None:
                    if st.button("Load River Database", type="primary"):
                        with st.spinner("Downloading River Database..."):
                            st.session_state['river_gdf'] = load_file_from_url(river_url, False)
                
                gdf = st.session_state['river_gdf']
                selected_river = None
                
                if gdf is not None:
                    basins = sorted(gdf['ba_name'].dropna().unique())
                    sel_basin = st.selectbox("1. Select Basin", basins)
                    
                    basin_gdf = gdf[gdf['ba_name'] == sel_basin]
                    rivers = sorted(basin_gdf['rivname'].dropna().unique())
                    sel_river = st.selectbox("2. Select River", rivers)
                    
                    selected_river = basin_gdf[basin_gdf['rivname'] == sel_river]
                    
                    # Metrics
                    l = float(selected_river['shape_Leng'].sum())
                    st.metric("Total Length", f"{l:.2f}", delta="Map Units")
                    st.metric("Segments", len(selected_river))
                    
                    st.divider()
                    st.subheader("Download")
                    fmt = st.selectbox("Format", ["ESRI Shapefile (.zip)", "GeoJSON", "KML", "GeoPackage"])
                    if st.button("Download River Data", use_container_width=True):
                        fname = f"{sel_river}_{sel_basin}".replace(" ","_")
                        d, e, m = handle_export(selected_river, fmt, fname)
                        if d: st.download_button("Save File", d, f"{fname}{e}", m, use_container_width=True)
                else:
                    st.info("Click 'Load River Database' to begin.")
        
        with col_map:
            # Use Cyan (#00E5FF) for Rivers to pop against Satellite background
            render_map([(selected_river, "River Flow", "#00E5FF")])


    # --- 3. FORMAT CONVERTER MODULE ---
    elif selected == "Converter":
        st.markdown("## 🔄 Universal Format Converter")
        
        # File Upload Section
        with st.container(border=True):
            uploaded_file = st.file_uploader("Upload File (Zip, SHP, KML, GPKG, CSV, XLSX)", type=['zip', 'shp', 'geojson', 'kml', 'gpkg', 'csv', 'xlsx'])
        
        gdf = None
        if uploaded_file:
            with tempfile.TemporaryDirectory() as tmp_dir:
                file_path = os.path.join(tmp_dir, uploaded_file.name)
                with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
                
                try:
                    if file_path.endswith('.zip'):
                        gdf = extract_and_read_first(file_path, tmp_dir)
                    elif file_path.endswith(('.csv', '.xlsx')):
                        df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
                        st.warning("Tabular data detected. Please define geometry.")
                        c1, c2, c3, c4 = st.columns(4)
                        mode = c1.radio("Mode", ["Lat/Lon", "WKT"])
                        if mode == "Lat/Lon":
                            x = c2.selectbox("Longitude Col", df.columns)
                            y = c3.selectbox("Latitude Col", df.columns)
                            if c4.button("Create Points"):
                                gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[x], df[y]), crs="EPSG:4326")
                        else:
                            wkt_col = c2.selectbox("WKT Column", df.columns)
                            if c4.button("Parse WKT"):
                                df['geometry'] = df[wkt_col].apply(wkt.loads)
                                gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
                    else:
                        gdf = gpd.read_file(file_path)
                except Exception as e:
                    st.error(f"Error reading file: {e}")

        if gdf is not None:
            col_ctrl, col_map = st.columns([1, 2], gap="medium")
            
            with col_ctrl:
                with st.container(border=True):
                    st.subheader("Conversion Settings")
                    st.info(f"Loaded: {len(gdf)} features | CRS: {gdf.crs}")
                    
                    target_crs = st.number_input("Target EPSG (e.g., 4326, 3857)", value=4326)
                    if st.button("Apply Reprojection"):
                        gdf = convert_crs(gdf, target_crs)
                        st.toast(f"Reprojected to EPSG:{target_crs}", icon="🔄")
                    
                    st.divider()
                    target_fmt = st.selectbox("Output Format", ["GeoJSON", "ESRI Shapefile (.zip)", "KML", "GeoPackage"])
                    
                    if st.button("Convert & Download", type="primary", use_container_width=True):
                        d, e, m = handle_export(gdf, target_fmt, "converted_data")
                        if d: st.download_button("Download Result", d, f"converted{e}", m, use_container_width=True)
            
            with col_map:
                # Use Red (#FF4B4B) - visible on hybrid
                render_map([(gdf, "Converted Data", "#FF4B4B")])

    # --- 4. VECTOR CALCULATOR MODULE (FULL FEATURES) ---
    elif selected == "Vector Calculator":
        st.markdown("## 🧮 Vector Operations")
        
        col_ctrl, col_map = st.columns([1.2, 2.5], gap="large")
        
        with col_ctrl:
            # 1. INPUTS
            with st.expander("📂 1. Data Layers (Input)", expanded=True):
                f1 = st.file_uploader("Layer A (Primary)", type=['zip', 'geojson', 'kml', 'gpkg'], key="f1")
                f2 = st.file_uploader("Layer B (Overlay/Secondary)", type=['zip', 'geojson', 'kml', 'gpkg'], key="f2")
                
                if f1:
                    with tempfile.TemporaryDirectory() as td:
                        p = os.path.join(td, f1.name); 
                        with open(p,"wb") as f: f.write(f1.getbuffer())
                        st.session_state['main_gdf'] = extract_and_read_first(p, td) if p.endswith('.zip') else gpd.read_file(p)
                
                if f2:
                    with tempfile.TemporaryDirectory() as td:
                        p = os.path.join(td, f2.name); 
                        with open(p,"wb") as f: f.write(f2.getbuffer())
                        st.session_state['secondary_gdf'] = extract_and_read_first(p, td) if p.endswith('.zip') else gpd.read_file(p)

            # 2. TOOLS
            with st.expander("🛠️ 2. Operations", expanded=True):
                category = st.selectbox("Category", ["Geoprocessing", "Geometry", "Analysis", "Overlay Operations", "Data Management"])
                
                tool_options = []
                if category == "Geoprocessing": tool_options = ["Buffer", "Convex Hull", "Dissolve"]
                elif category == "Geometry": tool_options = ["Centroids", "Simplify", "Explode", "Fix Geometries"]
                elif category == "Analysis": tool_options = ["Statistics", "Bounding Box", "Mean Coordinate"]
                elif category == "Overlay Operations": tool_options = ["Intersection", "Difference", "Union", "Spatial Join"]
                elif category == "Data Management": tool_options = ["Reproject", "Merge"]
                
                tool = st.selectbox("Tool", tool_options)
                
                # Dynamic Params
                params = {}
                if tool == "Buffer": params['dist'] = st.number_input("Distance (Map Units)", value=0.01, format="%.4f")
                elif tool == "Simplify": params['tol'] = st.number_input("Tolerance", value=0.001, format="%.4f")
                elif tool == "Dissolve" and st.session_state['main_gdf'] is not None:
                     cols = ["All"] + list(st.session_state['main_gdf'].columns)
                     params['col'] = st.selectbox("Dissolve Field", cols)
                elif tool == "Spatial Join": params['op'] = st.selectbox("Predicate", ["intersects", "contains", "within"])
                elif tool == "Reproject": params['epsg'] = st.number_input("Target EPSG", value=3857)

                if st.button("Run Operation", type="primary", use_container_width=True):
                    gdf = st.session_state['main_gdf']
                    sec_gdf = st.session_state['secondary_gdf']
                    res_gdf = None
                    
                    if gdf is None:
                        st.error("Layer A is required!")
                    else:
                        try:
                            # EXECUTION LOGIC
                            if tool == "Buffer": 
                                res_gdf = gdf.copy(); res_gdf['geometry'] = res_gdf.buffer(params['dist'])
                            elif tool == "Convex Hull": 
                                res_gdf = gdf.copy(); res_gdf['geometry'] = res_gdf.convex_hull
                            elif tool == "Dissolve": 
                                res_gdf = gdf.dissolve() if params['col'] == "All" else gdf.dissolve(by=params['col'])
                            elif tool == "Centroids": 
                                res_gdf = gdf.copy(); res_gdf['geometry'] = res_gdf.centroid
                            elif tool == "Simplify": 
                                res_gdf = gdf.copy(); res_gdf['geometry'] = res_gdf.simplify(params['tol'])
                            elif tool == "Explode": 
                                res_gdf = gdf.explode(index_parts=True).reset_index(drop=True)
                            elif tool == "Fix Geometries": 
                                res_gdf = gdf.copy(); res_gdf['geometry'] = res_gdf.buffer(0)
                            elif tool == "Bounding Box": 
                                res_gdf = gdf.copy(); res_gdf['geometry'] = res_gdf.envelope
                            elif tool == "Reproject": 
                                res_gdf = gdf.to_crs(epsg=params['epsg'])
                            elif tool == "Mean Coordinate":
                                x = gdf.geometry.centroid.x.mean(); y = gdf.geometry.centroid.y.mean()
                                res_gdf = gpd.GeoDataFrame({'geometry': gpd.points_from_xy([x], [y])}, crs=gdf.crs)
                            elif tool == "Statistics":
                                st.info(f"Area: {gdf.area.sum()} | Length: {gdf.length.sum()}")
                                res_gdf = gdf # No geometry change
                            
                            # Dual Layer Ops
                            elif tool in ["Intersection", "Difference", "Union", "Spatial Join", "Merge"]:
                                if sec_gdf is None: st.error("Layer B required for this tool.");
                                else:
                                    if gdf.crs != sec_gdf.crs: sec_gdf = sec_gdf.to_crs(gdf.crs)
                                    if tool == "Intersection": res_gdf = gpd.overlay(gdf, sec_gdf, how='intersection')
                                    elif tool == "Difference": res_gdf = gpd.overlay(gdf, sec_gdf, how='difference')
                                    elif tool == "Union": res_gdf = gpd.overlay(gdf, sec_gdf, how='union')
                                    elif tool == "Merge": res_gdf = pd.concat([gdf, sec_gdf])
                                    elif tool == "Spatial Join": res_gdf = gpd.sjoin(gdf, sec_gdf, how="inner", predicate=params['op'])
                            
                            if res_gdf is not None:
                                st.session_state['calc_result_gdf'] = res_gdf
                                st.toast(f"Operation {tool} Successful!", icon="🚀")
                                
                        except Exception as e:
                            st.error(f"Processing Error: {e}")

        with col_map:
            # Optimized Colors for Hybrid Map Visibility
            layers = []
            if st.session_state['main_gdf'] is not None: layers.append((st.session_state['main_gdf'], "Layer A", "#FFA500")) # Orange
            if st.session_state['secondary_gdf'] is not None: layers.append((st.session_state['secondary_gdf'], "Layer B", "#00E5FF")) # Cyan
            if st.session_state['calc_result_gdf'] is not None: layers.append((st.session_state['calc_result_gdf'], "Result", "#39FF14")) # Neon Green
            
            render_map(layers, height=600)
            
            # Result Download
            if st.session_state['calc_result_gdf'] is not None:
                with st.container(border=True):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                         out_fmt = st.selectbox("Export Result As", ["GeoJSON", "ESRI Shapefile (.zip)", "KML", "GeoPackage"])
                    with c2:
                         st.write("") # Spacer
                         st.write("") 
                         d, e, m = handle_export(st.session_state['calc_result_gdf'], out_fmt, "analysis_result")
                         if d: st.download_button("Download Result", d, f"result{e}", m, use_container_width=True, type="primary")

if __name__ == "__main__":
    main()
