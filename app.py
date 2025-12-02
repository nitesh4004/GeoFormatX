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

# --- 1. Configuration & Page Setup ---
st.set_page_config(
    page_title="geoformatx",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enable KML drivers
fiona.drvsupport.supported_drivers['KML'] = 'rw'
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'

# --- 2. Improved UI/UX (Theme Safe) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    div[data-testid="stButton"] > button[kind="primary"] {
        background-color: #0068C9;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: 0.2s;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: #0053a6;
        border: none;
    }
    
    .stTextInput > div > div > input {
        border-radius: 8px;
    }
    .stSelectbox > div > div > div {
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Configuration: Google Drive File IDs ---
STATE_VILLAGE_IDS = {
    "ANDAMAN_&_NICOBAR_ISLANDS": "1aikaQXqP9xtDhMcQFyUn8g9gGi0Tam0s",
    "ANDHRA_PRADESH": "1fkDuJI6oC0h8LQCvCh9elhKq0KbXQbTj",
    "BIHAR": "14QA_fZiSPYFKy9CfvqL4Z-9v9FWaAWBC",
    "CHANDIGARH": "1cr9Px3o70pJTRSRcqTN1kS18AcTeksu_",
    "CHHATTISGARH": "1Kk3sUbMBysyDwVYTnBBGaqF9E9p7372c",
    "DELHI": "1UuiNX9cQvj3BZIhcojvEb6cZv3ic0NMy",
    "GOA": "1re0K0LUr1k9ZgqsKJoQpynLXtmFQQECs",
    "HARYANA": "1Ab1ccMk-papacEOK74CST_nLFBbwRQia",
    "JHARKHAND": "16w2g-ppENXpbAAbtG05bepQjVleijQCB",
    "KARNATAKA": "1daGp_O2RmMjjT8ATsaRX75XWNfWZaPsM",
    "KERALA": "1qva1qt4luInTg6tb_6vCKU7qKhbBvj1J",
    "LAKSHYADWEEP": "10vUXwZ8A_UNWaLAFvDZGfbi985_E8oxc",
    "MADHYA_PRADESH": "1WnwwFX8AtY4P9mDJq8Wd09nqEcIhOHk4",
    "MAHARASHTRA": "1NspjfpGqxNb1G6fJSmlGj82h5YTanULV",
    "UTTARAKHAND": "1ydyLvZ3yiOWW9ltfYMlsKqBbnyLi0cu_",
    "WEST_BENGAL": "1euxg0fPGT5XcbLt0dP25U2M4fEZ-dkNs"
}

# --- 4. Helper Functions ---
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
                st.error(f"❌ Could not find file at: {url}")
                return None
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        return extract_and_read_first(zip_path, temp_dir)
    except Exception as e:
        st.error(f"Download Error: {e}")
        return None

def extract_and_read_first(zip_path, temp_dir):
    try:
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        shapefiles = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(".shp"):
                    shapefiles.append(os.path.join(root, file))
        
        if not shapefiles: return None
        return gpd.read_file(shapefiles[0], engine='fiona')
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
                gdf.to_file(os.path.join(out_dir, f"{file_prefix}.shp"), driver="ESRI Shapefile", encoding='utf-8', engine='fiona')
                final_data = make_zip(out_dir)
                file_ext, mime_type = ".zip", "application/zip"
                
            elif "GeoJSON" in output_format:
                path = os.path.join(out_dir, f"{file_prefix}.geojson")
                gdf.to_file(path, driver="GeoJSON", engine='fiona')
                with open(path, "rb") as f: final_data = BytesIO(f.read())
                file_ext, mime_type = ".geojson", "application/json"
            
            elif "KML" in output_format:
                path = os.path.join(out_dir, f"{file_prefix}.kml")
                gdf.to_file(path, driver="KML", engine='fiona')
                with open(path, "rb") as f: final_data = BytesIO(f.read())
                file_ext, mime_type = ".kml", "application/vnd.google-earth.kml+xml"
            
            elif "GeoPackage" in output_format:
                path = os.path.join(out_dir, f"{file_prefix}.gpkg")
                gdf.to_file(path, driver="GPKG", engine='fiona')
                with open(path, "rb") as f: final_data = BytesIO(f.read())
                file_ext, mime_type = ".gpkg", "application/x-sqlite3"

            return final_data, file_ext, mime_type
        except Exception as e:
            st.error(f"Export failed: {str(e)}")
            return None, None, None

# --- 5. Views ---

def view_admin_downloader():
    st.title("Admin Boundary Repository")
    st.markdown("Select an Indian administrative dataset, filter by region, and download.")
    
    col_config, col_preview = st.columns([1, 1.5], gap="medium")
    
    # --- Left Column: Configuration ---
    with col_config:
        with st.container(border=True):
            st.subheader("1. Select Source")
            # Using pills for cleaner look
            source_type = st.pills(
                "Dataset Level",
                ["🏛️ Districts", "🏘️ Subdistricts", "🛖 Villages", "🗺️ States"],
                default="🏛️ Districts",
                selection_mode="single"
            )
            
            gdf = None
            selected_feature = None
            filename = "export"
            
            # Data Loading
            try:
                if "Districts" in source_type:
                    with st.status("Fetching District Database...", expanded=False) as status:
                        gdf = load_file_from_url('https://drive.google.com/uc?id=1tMyiUheQBcwwPwZQla67PwC5-AqenTmv', is_gdrive=True)
                        status.update(label="Districts Loaded", state="complete")
                
                elif "Subdistricts" in source_type:
                    with st.status("Fetching Subdistrict Database...", expanded=False) as status:
                        gdf = load_file_from_url('https://drive.google.com/uc?id=18lMyt2j3Xjz_Qk_2Kzppr8EVlVDx_yOv', is_gdrive=True)
                        status.update(label="Subdistricts Loaded", state="complete")

                elif "States" in source_type:
                    with st.status("Fetching State Database...", expanded=False) as status:
                        gdf = load_file_from_url("https://raw.githubusercontent.com/nitesh4004/GeoFormatX/main/STATE_BOUNDARY.zip", is_gdrive=False)
                        status.update(label="States Loaded", state="complete")

                elif "Villages" in source_type:
                    st.info("ℹ️ Select a state to download its Village Map.")
                    available_states = sorted(list(STATE_VILLAGE_IDS.keys()))
                    target_state_key = st.selectbox("Select State", available_states)
                    
                    file_id = STATE_VILLAGE_IDS.get(target_state_key)
                    if file_id:
                        with st.status(f"Downloading {target_state_key}...", expanded=False) as status:
                            gdf = load_file_from_url(f"https://drive.google.com/uc?id={file_id}", is_gdrive=True)
                            status.update(label="Village Data Loaded", state="complete")
            except Exception as e:
                st.error("Connection Error.")
                st.stop()

        if gdf is None: st.stop()
        gdf = clean_text_data(gdf)
        
        with st.container(border=True):
            st.subheader("2. Filter Area")
            
            def get_sorted_unique(df, col):
                return sorted(df[col].astype(str).unique()) if col in df.columns else []

            if 'STATE' in gdf.columns:
                states = get_sorted_unique(gdf, 'STATE')
                sel_state = st.selectbox("Filter State", states, index=0)
                
                # Logic Chain
                if "Villages" in source_type and 'District' in gdf.columns:
                    state_gdf = gdf[gdf['STATE'] == sel_state]
                    sel_district = st.selectbox("Select District", get_sorted_unique(state_gdf, 'District'))
                    dist_gdf = state_gdf[state_gdf['District'] == sel_district]
                    
                    if 'Subdistrict' in dist_gdf.columns:
                        sel_subdistrict = st.selectbox("Select Subdistrict", get_sorted_unique(dist_gdf, 'Subdistrict'))
                        subdist_gdf = dist_gdf[dist_gdf['Subdistrict'] == sel_subdistrict]
                        
                        if 'Village' in subdist_gdf.columns:
                            mode = st.radio("Selection Mode", ["All Villages in Subdistrict", "Specific Village"])
                            if mode == "Specific Village":
                                sel_village = st.selectbox("Select Village", get_sorted_unique(subdist_gdf, 'Village'))
                                selected_feature = subdist_gdf[subdist_gdf['Village'] == sel_village]
                                filename = f"{sel_village}_{sel_subdistrict}_Village"
                            else:
                                selected_feature = subdist_gdf
                                filename = f"{sel_subdistrict}_Villages"
                        else:
                            selected_feature = subdist_gdf
                            filename = f"{sel_subdistrict}_Villages"
                    else:
                        selected_feature = dist_gdf
                        filename = f"{sel_district}_Villages"

                elif "Districts" in source_type:
                    state_gdf = gdf[gdf['STATE'] == sel_state]
                    sel_dist = st.selectbox("Select District", get_sorted_unique(state_gdf, 'District'))
                    selected_feature = state_gdf[state_gdf['District'] == sel_dist]
                    filename = f"{sel_dist}_{sel_state}" if not selected_feature.empty else "export"
                
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
            
            if st.button("🚀 Process & Download", type="primary"):
                 if selected_feature is not None and not selected_feature.empty:
                    with st.spinner("Packaging data..."):
                        data, ext, mime = handle_export(selected_feature, out_fmt, filename)
                        if data:
                            st.download_button(f"💾 Save {filename}{ext}", data, f"{filename}{ext}", mime)
                            st.toast("Download ready!", icon="✅")

    # --- Right Column: Preview ---
    with col_preview:
        with st.container(border=True):
            st.subheader("3. Map Preview")
            if selected_feature is not None and not selected_feature.empty:
                # Metrics
                m1, m2 = st.columns(2)
                m1.metric("Features Selected", len(selected_feature))
                m2.metric("Geometry Type", selected_feature.geom_type.unique()[0] if not selected_feature.empty else "N/A")
                
                # Map
                try:
                    map_data = selected_feature.to_crs(epsg=4326)
                    if len(map_data) > 1000:
                        st.warning("⚠️ Large dataset. Previewing 1000 features.")
                        st.map(map_data.sample(1000))
                    else:
                        st.map(map_data)
                except Exception:
                    st.warning("Map visualization unavailable.")
            else:
                st.info("Select a region on the left to visualize it here.")

def view_data_converter():
    st.title("Universal Data Converter")
    st.markdown("Upload your own vector data (Shapefile, CSV, KML) and convert it.")
    
    with st.container(border=True):
        uploaded_file = st.file_uploader(
            "Upload File", 
            type=['zip', 'shp', 'geojson', 'kml', 'gpkg', 'csv', 'xlsx'],
            help="For Shapefiles, upload a .zip containing .shp, .shx, and .dbf"
        )
    
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
                    gdf = gpd.read_file(file_path, engine='fiona')
            except Exception as e:
                st.error(f"Read Error: {e}")
            
            if gdf is not None:
                st.success("File uploaded successfully!")
                
                col_sets, col_map = st.columns([1, 1], gap="medium")
                
                with col_sets:
                    with st.container(border=True):
                        st.subheader("Conversion Settings")
                        enable_crs = st.checkbox("Reproject Coordinates")
                        target_epsg = st.number_input("Target EPSG", value=4326, disabled=not enable_crs)
                    
                        target_format = st.selectbox(
                            "Target Format", 
                            ["ESRI Shapefile (.zip)", "GeoJSON", "GeoPackage (.gpkg)", "KML"]
                        )
                        
                        if enable_crs:
                            gdf = convert_crs(gdf, target_epsg)
                            
                        if st.button("🔄 Convert File", type="primary"):
                            data, ext, mime = handle_export(gdf, target_format, "converted_data")
                            if data:
                                st.download_button("💾 Download Result", data, f"converted{ext}", mime)

                with col_map:
                    with st.container(border=True):
                        st.subheader("Preview")
                        try:
                            st.map(gdf.to_crs(4326) if gdf.crs else gdf)
                        except:
                            st.write("Visual preview not available.")

def view_vector_calculator():
    st.title("Vector Calculator")
    st.markdown("Perform vector analysis, geometry operations, and geoprocessing tasks.")
    
    # 1. Upload Section
    with st.container(border=True):
        st.subheader("1. Input Data")
        uploaded_file = st.file_uploader("Upload Vector Layer", type=['zip', 'shp', 'geojson', 'kml', 'gpkg'])
    
    gdf = None
    if uploaded_file:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, uploaded_file.name)
            with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
            
            try:
                if file_path.endswith('.zip'):
                    gdf = extract_and_read_first(file_path, tmp_dir)
                else:
                    gdf = gpd.read_file(file_path, engine='fiona')
            except Exception as e:
                st.error(f"Load Error: {e}")

    if gdf is not None:
        st.info(f"Loaded {len(gdf)} features. CRS: {gdf.crs}")
        
        # 2. Tool Selection Interface (QGIS Style)
        col_menu, col_wksp = st.columns([1, 2], gap="large")
        
        with col_menu:
            st.subheader("2. Toolbox")
            tool_category = st.radio(
                "Category",
                ["Geoprocessing Tools", "Geometry Tools", "Analysis Tools", "Data Management"]
            )
            
            tool = None
            
            if tool_category == "Geoprocessing Tools":
                tool = st.selectbox("Select Tool", ["Buffer", "Convex Hull", "Dissolve", "Difference (Clip)"])
            elif tool_category == "Geometry Tools":
                tool = st.selectbox("Select Tool", ["Centroids", "Simplify", "Multi to Singleparts", "Extract Vertices"])
            elif tool_category == "Analysis Tools":
                tool = st.selectbox("Select Tool", ["Basic Statistics", "Bounding Box (Envelope)", "Mean Coordinates"])
            elif tool_category == "Data Management":
                tool = st.selectbox("Select Tool", ["Reproject Layer", "Merge (Simulate)"])

        # 3. Workspace
        with col_wksp:
            st.subheader(f"3. Run: {tool}")
            result_gdf = None
            
            # --- TOOL LOGIC ---
            try:
                if tool == "Buffer":
                    dist = st.number_input("Buffer Distance (in layer CRS units)", value=0.01, format="%.6f")
                    st.caption("Note: If CRS is WGS84, distance is in degrees. For meters, reproject first.")
                    if st.button("Run Buffer", type="primary"):
                        result_gdf = gdf.copy()
                        result_gdf['geometry'] = result_gdf.geometry.buffer(dist)
                
                elif tool == "Convex Hull":
                    if st.button("Run Convex Hull", type="primary"):
                        result_gdf = gdf.copy()
                        result_gdf['geometry'] = result_gdf.geometry.convex_hull

                elif tool == "Dissolve":
                    dissolve_col = st.selectbox("Dissolve Field (Optional)", ["None (Dissolve All)"] + list(gdf.columns))
                    if st.button("Run Dissolve", type="primary"):
                        if dissolve_col == "None (Dissolve All)":
                            result_gdf = gdf.dissolve()
                        else:
                            result_gdf = gdf.dissolve(by=dissolve_col)
                
                elif tool == "Centroids":
                    if st.button("Extract Centroids", type="primary"):
                        result_gdf = gdf.copy()
                        result_gdf['geometry'] = result_gdf.geometry.centroid

                elif tool == "Simplify":
                    tol = st.number_input("Tolerance", value=0.001, format="%.6f")
                    if st.button("Run Simplify", type="primary"):
                        result_gdf = gdf.copy()
                        result_gdf['geometry'] = result_gdf.geometry.simplify(tol)
                
                elif tool == "Multi to Singleparts":
                    if st.button("Explode Multipart", type="primary"):
                        result_gdf = gdf.explode(index_parts=True).reset_index(drop=True)

                elif tool == "Basic Statistics":
                    st.write("Calculates Area and Perimeter for the layer.")
                    if st.button("Calculate Stats", type="primary"):
                        stats_gdf = gdf.copy()
                        stats_gdf['area'] = stats_gdf.geometry.area
                        stats_gdf['length'] = stats_gdf.geometry.length
                        st.dataframe(stats_gdf[['area', 'length']].describe())
                        result_gdf = stats_gdf # Allow download of attribute table

                elif tool == "Reproject Layer":
                    target = st.number_input("Target EPSG Code", value=3857, step=1)
                    if st.button("Reproject", type="primary"):
                        result_gdf = gdf.to_crs(epsg=target)
                        st.success(f"Reprojected to EPSG:{target}")

                elif tool == "Bounding Box (Envelope)":
                    if st.button("Get Envelope", type="primary"):
                        result_gdf = gdf.copy()
                        result_gdf['geometry'] = result_gdf.geometry.envelope

                # --- RESULT HANDLING ---
                if result_gdf is not None:
                    st.success("Operation Successful!")
                    
                    # Preview
                    with st.expander("Result Preview", expanded=True):
                        try:
                            viz_data = result_gdf.to_crs(4326) if result_gdf.crs else result_gdf
                            st.map(viz_data)
                        except:
                            st.write("Cannot map result (might be non-spatial geometry).")
                    
                    # Download
                    col_dl_fmt, col_dl_btn = st.columns(2)
                    fmt = col_dl_fmt.selectbox("Download Format", ["GeoJSON", "ESRI Shapefile (.zip)", "KML"], key="res_fmt")
                    
                    data, ext, mime = handle_export(result_gdf, fmt, "calculator_result")
                    if data:
                        col_dl_btn.download_button("💾 Download Result", data, f"result{ext}", mime)
            
            except Exception as e:
                st.error(f"Processing Error: {str(e)}")


def main():
    with st.sidebar:
        st.title("geoFormatX")
        st.markdown("### Menu")
        mode = st.radio(
            "Select Tool", 
            ["📥 Admin Downloader", "🔄 Converter", "🧮 Vector Calculator"]
        )
        st.divider()
        st.caption("v3.0 | Theme Aware")
        st.caption("Includes: Geoprocessing, Geometry, & Analysis Tools")

    if mode == "📥 Admin Downloader":
        view_admin_downloader()
    elif mode == "🔄 Converter":
        view_data_converter()
    elif mode == "🧮 Vector Calculator":
        view_vector_calculator()

if __name__ == "__main__":
    main()
