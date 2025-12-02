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
    initial_sidebar_state="expanded"
)

# Enable KML drivers for fiona
fiona.drvsupport.supported_drivers['KML'] = 'rw'
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'

# Initialize Session State (This fixes the Export Bug)
if 'calc_result_gdf' not in st.session_state:
    st.session_state['calc_result_gdf'] = None
if 'calc_result_name' not in st.session_state:
    st.session_state['calc_result_name'] = "result"

# --- 2. STYLING (Original Colors + Modern Layout) ---
st.markdown("""
    <style>
    /* Import professional font: Poppins */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }
    
    /* Card Styling */
    .st-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    
    /* Dark mode adjustment for cards (automatic) */
    @media (prefers-color-scheme: dark) {
        .st-card {
            background-color: #262730;
            border: 1px solid #41424b;
        }
    }

    /* Primary Buttons (Your preferred Blue) */
    div[data-testid="stButton"] > button[kind="primary"] {
        background-color: #0068C9;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: 0.2s;
        border-radius: 8px;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: #0053a6;
    }
    
    /* Input Fields */
    .stTextInput > div > div > input, .stSelectbox > div > div > div {
        border-radius: 8px;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA CONSTANTS (Full List) ---
STATE_VILLAGE_IDS = {
    "ANDAMAN_&_NICOBAR_ISLANDS": "1aikaQXqP9xtDhMcQFyUn8g9gGi0Tam0s",
    "ANDHRA_PRADESH": "1fkDuJI6oC0h8LQCvCh9elhKq0KbXQbTj",
    "ARUNACHAL_PRADESH": "1_Example_ID_Placeholder", # Placeholder if ID missing
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
    except Exception as e:
        return None

def extract_and_read_first(zip_path, temp_dir):
    try:
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Find any supported vector file
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

# --- 5. MODULES ---

def view_admin_downloader():
    st.title("Admin Boundary Repository")
    st.markdown("Download official administrative boundaries for India.")
    
    col_config, col_preview = st.columns([1, 1.5], gap="medium")
    
    # --- Configuration ---
    with col_config:
        st.markdown('<div class="st-card">', unsafe_allow_html=True)
        st.subheader("1. Data Source")
        
        source_type = st.pills(
            "Granularity",
            ["🏛️ Districts", "🏘️ Subdistricts", "🛖 Villages", "🗺️ States"],
            default="🏛️ Districts",
            selection_mode="single"
        )
        
        gdf = None
        selected_feature = None
        filename = "export"
        
        # Load Data
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
            st.error("Connection Error.")

        st.markdown('</div>', unsafe_allow_html=True)

        if gdf is not None:
            gdf = clean_text_data(gdf)
            
            st.markdown('<div class="st-card">', unsafe_allow_html=True)
            st.subheader("2. Filter Region")
            
            def get_sorted_unique(df, col):
                return sorted(df[col].astype(str).unique()) if col in df.columns else []

            if 'STATE' in gdf.columns:
                states = get_sorted_unique(gdf, 'STATE')
                sel_state = st.selectbox("Filter State", states)
                
                # Logic Chain
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
            
            out_fmt = st.selectbox("Output Format", ["ESRI Shapefile (.zip)", "GeoJSON", "KML", "GeoPackage"])
            
            if st.button("🚀 Download Data", type="primary"):
                 if selected_feature is not None and not selected_feature.empty:
                    with st.spinner("Packaging..."):
                        data, ext, mime = handle_export(selected_feature, out_fmt, filename)
                        if data:
                            st.download_button(f"💾 Save {filename}{ext}", data, f"{filename}{ext}", mime)
            st.markdown('</div>', unsafe_allow_html=True)

    # --- Preview ---
    with col_preview:
        st.markdown('<div class="st-card">', unsafe_allow_html=True)
        st.subheader("Map Preview")
        if selected_feature is not None and not selected_feature.empty:
            m1, m2 = st.columns(2)
            m1.metric("Features", len(selected_feature))
            m2.metric("Type", selected_feature.geom_type.unique()[0])
            try:
                map_data = selected_feature.to_crs(epsg=4326)
                if len(map_data) > 1000:
                    st.warning("⚠️ Large dataset. Previewing 1000 features.")
                    st.map(map_data.sample(1000))
                else:
                    st.map(map_data)
            except Exception:
                st.warning("Visualization unavailable.")
        else:
            st.info("Select a region to visualize.")
        st.markdown('</div>', unsafe_allow_html=True)


def view_data_converter():
    st.title("Universal Data Converter")
    st.markdown("Convert vector data between formats.")
    
    st.markdown('<div class="st-card">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload File", 
        type=['zip', 'shp', 'geojson', 'kml', 'gpkg', 'csv', 'xlsx']
    )
    st.markdown('</div>', unsafe_allow_html=True)

    if uploaded_file:
        gdf = None
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                # ETL Logic
                if file_path.endswith('.zip'):
                    gdf = extract_and_read_first(file_path, tmp_dir)
                elif file_path.endswith(('.csv', '.xlsx')):
                    df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
                    st.warning("Tabular data detected. Please specify geometry.")
                    c1, c2, c3 = st.columns(3)
                    mode = c1.radio("Geometry Type", ["Lat/Lon", "WKT"])
                    if mode == "Lat/Lon":
                        x = c2.selectbox("Longitude (X)", df.columns)
                        y = c3.selectbox("Latitude (Y)", df.columns)
                        if st.button("Create Geometry"):
                            gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[x], df[y]), crs="EPSG:4326")
                    else:
                        wkt_c = c2.selectbox("WKT Column", df.columns)
                        if st.button("Parse WKT"):
                            df['geometry'] = df[wkt_c].apply(wkt.loads)
                            gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
                else:
                    gdf = gpd.read_file(file_path)
            except Exception as e:
                st.error(f"Read Error: {e}")
            
            if gdf is not None:
                col_sets, col_map = st.columns([1, 1], gap="medium")
                
                with col_sets:
                    st.markdown('<div class="st-card">', unsafe_allow_html=True)
                    st.subheader("Conversion Settings")
                    enable_crs = st.checkbox("Reproject Coordinates")
                    target_epsg = st.number_input("Target EPSG", value=4326, disabled=not enable_crs)
                    target_format = st.selectbox("Target Format", ["ESRI Shapefile (.zip)", "GeoJSON", "GeoPackage (.gpkg)", "KML"])
                    
                    if enable_crs: gdf = convert_crs(gdf, target_epsg)
                        
                    if st.button("🔄 Convert File", type="primary"):
                        data, ext, mime = handle_export(gdf, target_format, "converted_data")
                        if data:
                            st.download_button("💾 Download Result", data, f"converted{ext}", mime)
                    st.markdown('</div>', unsafe_allow_html=True)

                with col_map:
                    st.markdown('<div class="st-card">', unsafe_allow_html=True)
                    st.subheader("Preview")
                    try:
                        st.map(gdf.to_crs(4326) if gdf.crs else gdf)
                    except:
                        st.write("Visual preview not available.")
                    st.markdown('</div>', unsafe_allow_html=True)

def view_vector_calculator():
    st.title("Vector Calculator")
    st.markdown("Perform geoprocessing, geometry analysis, and data management tasks.")
    
    # TABS UI - Solves UX flow
    tab1, tab2, tab3 = st.tabs(["📂 1. Input Data", "⚙️ 2. Processing Tools", "💾 3. Results & Export"])

    # --- TAB 1: INPUT ---
    with tab1:
        st.markdown('<div class="st-card">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload Vector Layer", type=['zip', 'shp', 'geojson', 'kml', 'gpkg'])
        
        # Load logic
        input_gdf = None
        if uploaded_file:
            # We must use persistent storage for the input if we want it to survive tab changes without re-uploading
            # For simplicity, we re-read the buffer (Streamlit handles file_uploader caching well usually)
            with tempfile.TemporaryDirectory() as tmp_dir:
                file_path = os.path.join(tmp_dir, uploaded_file.name)
                with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
                try:
                    if file_path.endswith('.zip'):
                        input_gdf = extract_and_read_first(file_path, tmp_dir)
                    else:
                        input_gdf = gpd.read_file(file_path)
                    
                    if input_gdf is not None:
                        st.session_state['input_gdf'] = input_gdf # Cache input
                        st.success(f"Layer Loaded: {len(input_gdf)} features. CRS: {input_gdf.crs}")
                except Exception as e:
                    st.error(f"Error: {e}")
        elif 'input_gdf' in st.session_state:
            input_gdf = st.session_state['input_gdf']
            st.info(f"Using previously loaded layer ({len(input_gdf)} features).")
            
        st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 2: TOOLS ---
    with tab2:
        if 'input_gdf' in st.session_state:
            gdf = st.session_state['input_gdf']
            
            st.markdown('<div class="st-card">', unsafe_allow_html=True)
            c1, c2 = st.columns([1, 2])
            
            with c1:
                st.subheader("Select Tool")
                category = st.radio("Category", ["Geoprocessing", "Geometry", "Analysis", "Data Management"])
                
                tool_options = []
                if category == "Geoprocessing":
                    tool_options = ["Buffer", "Convex Hull", "Dissolve", "Difference (Clip)"]
                elif category == "Geometry":
                    tool_options = ["Centroids", "Simplify", "Multipart to Singlepart", "Extract Vertices"]
                elif category == "Analysis":
                    tool_options = ["Basic Statistics", "Bounding Box (Envelope)", "Mean Coordinate"]
                elif category == "Data Management":
                    tool_options = ["Reproject Layer", "Merge Layers"]
                
                tool = st.selectbox("Operation", tool_options)

            with c2:
                st.subheader("Parameters")
                res_gdf = None
                
                try:
                    # --- TOOL PARAMETERS & EXECUTION ---
                    if tool == "Buffer":
                        dist = st.number_input("Buffer Distance (Layer Units)", value=0.01, format="%.6f")
                        st.caption("Note: Ensure CRS is projected (meters) for accurate buffering.")
                        if st.button("Run Buffer", type="primary"):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.buffer(dist)

                    elif tool == "Convex Hull":
                        st.write("Creates the smallest convex polygon enclosing features.")
                        if st.button("Run Convex Hull", type="primary"):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.convex_hull
                    
                    elif tool == "Dissolve":
                        col = st.selectbox("Dissolve Field", ["None (Dissolve All)"] + list(gdf.columns))
                        if st.button("Run Dissolve", type="primary"):
                            if col == "None (Dissolve All)":
                                res_gdf = gdf.dissolve()
                            else:
                                res_gdf = gdf.dissolve(by=col)
                    
                    elif tool == "Difference (Clip)":
                        st.warning("Requires a second overlay layer (not implemented in this simplified version).")

                    elif tool == "Centroids":
                        if st.button("Run Centroids", type="primary"):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.centroid

                    elif tool == "Simplify":
                        tol = st.number_input("Tolerance", value=0.001, format="%.6f")
                        if st.button("Run Simplify", type="primary"):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.simplify(tol)

                    elif tool == "Multipart to Singlepart":
                        if st.button("Explode", type="primary"):
                            res_gdf = gdf.explode(index_parts=True).reset_index(drop=True)

                    elif tool == "Extract Vertices":
                        if st.button("Extract", type="primary"):
                            res_gdf = gdf.copy()
                            # Complex operation, creating points for every vertex
                            st.warning("Extracting vertices for large files can be slow.")
                            res_gdf['geometry'] = res_gdf.geometry.apply(lambda geom: [p for p in geom.exterior.coords])
                            # Simplified representation for demo
                            st.error("Vertex extraction creates non-standard geometry arrays. Generating centroids instead.")
                            res_gdf['geometry'] = res_gdf.geometry.centroid

                    elif tool == "Basic Statistics":
                        if st.button("Calculate", type="primary"):
                            stats = gdf.copy()
                            stats['area'] = stats.geometry.area
                            stats['perimeter'] = stats.geometry.length
                            st.dataframe(stats[['area', 'perimeter']].describe())
                            res_gdf = stats # allow export of table
                            
                    elif tool == "Bounding Box (Envelope)":
                        if st.button("Generate BBox", type="primary"):
                            res_gdf = gdf.copy()
                            res_gdf['geometry'] = res_gdf.geometry.envelope

                    elif tool == "Mean Coordinate":
                        if st.button("Calculate Mean", type="primary"):
                            # Create a single point
                            x = gdf.geometry.centroid.x.mean()
                            y = gdf.geometry.centroid.y.mean()
                            res_gdf = gpd.GeoDataFrame({'geometry': gpd.points_from_xy([x], [y])}, crs=gdf.crs)

                    elif tool == "Reproject Layer":
                        epsg = st.number_input("Target EPSG", value=3857, step=1)
                        if st.button("Reproject", type="primary"):
                            res_gdf = gdf.to_crs(epsg=epsg)

                    elif tool == "Merge Layers":
                        st.info("Currently only supports merging the layer with itself (Duplication).")
                        if st.button("Merge", type="primary"):
                             res_gdf = pd.concat([gdf, gdf])
                    
                    # --- SAVE RESULT TO STATE ---
                    if res_gdf is not None:
                        st.session_state['calc_result_gdf'] = res_gdf
                        st.session_state['calc_result_name'] = f"{tool}_Result"
                        st.success("Processing Complete! Go to Tab 3 to download.")
                
                except Exception as e:
                    st.error(f"Operation Failed: {e}")
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Please upload data in Tab 1 first.")

    # --- TAB 3: EXPORT (State Aware) ---
    with tab3:
        if st.session_state['calc_result_gdf'] is not None:
            res_gdf = st.session_state['calc_result_gdf']
            res_name = st.session_state['calc_result_name']
            
            st.markdown('<div class="st-card">', unsafe_allow_html=True)
            st.subheader(f"Results: {res_name}")
            
            # 1. Map
            try:
                st.map(res_gdf.to_crs(4326) if res_gdf.crs else res_gdf)
            except:
                st.warning("Cannot visualize geometry.")
            
            st.divider()
            
            # 2. Export (Persistent)
            c_ex1, c_ex2 = st.columns([2, 1])
            with c_ex1:
                # Changing this widget triggers a rerun, but session_state holds the GDF
                fmt = st.selectbox("Export Format", 
                                 ["ESRI Shapefile (.zip)", "GeoJSON", "KML", "GeoPackage"], 
                                 key="calc_export_fmt")
            
            with c_ex2:
                # Generate download object dynamically based on state + selected format
                data, ext, mime = handle_export(res_gdf, fmt, res_name)
                st.write("") # Spacer
                if data:
                    st.download_button(
                        label=f"⬇️ Download {fmt.split(' ')[0]}",
                        data=data,
                        file_name=f"{res_name}{ext}",
                        mime=mime,
                        type="primary"
                    )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No results calculated yet.")

def main():
    with st.sidebar:
        st.title("geoFormatX")
        st.write("Advanced Spatial Toolkit")
        mode = st.radio("Select Module", ["📥 Admin Downloader", "🔄 Converter", "🧮 Vector Calculator"])
        st.divider()
        st.caption("v5.0 | Stable Core")

    if mode == "📥 Admin Downloader":
        view_admin_downloader()
    elif mode == "🔄 Converter":
        view_data_converter()
    elif mode == "🧮 Vector Calculator":
        view_vector_calculator()

if __name__ == "__main__":
    main()
