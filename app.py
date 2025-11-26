import streamlit as st
import geopandas as gpd
import pandas as pd
import fiona
import os
import tempfile
import gdown
import requests
import zipfile
from zipfile import ZipFile
from io import BytesIO
from shapely import wkt

# --- 1. Configuration & Page Setup ---
st.set_page_config(
    page_title="GeoConvert Pro",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enable KML drivers
fiona.drvsupport.supported_drivers['KML'] = 'rw'
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'

# --- 2. Custom UI Styling ---
st.markdown("""
    <style>
    /* Main container styling */
    .main { background-color: #FAFAFA; }
    
    /* Header styling */
    h1 { color: #2C3E50; font-family: 'Helvetica Neue', sans-serif; }
    h3 { color: #34495E; }
    
    /* Custom Box styling */
    .css-1r6slb0 { border: 1px solid #E0E0E0; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    
    /* Button Styling */
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 600; }
    
    /* Success/Info box styling */
    .stAlert { border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Configuration: State Village File IDs ---
# ⚠️ IMPORTANT: Replace the empty strings "" with the actual Google Drive File IDs 
# from your "Village of india" folder for each state zip file.
# To get an ID: Right-click file in Drive -> Share -> Copy Link -> The ID is the part like '1tMyiU...'
STATE_VILLAGE_IDS = {
    "ANDHRA_PRADESH": "",
    "BIHAR": "",
    "CHANDIGARH": "",
    "CHHATTISGARH": "",
    "DELHI": "",
    "GOA": "",
    "HARYANA": "",
    "JHARKHAND": "",
    "KARNATAKA": "",
    "KERALA": "",
    "LAKSHYADWEEP": "",
    "MADHYA_PRADESH": "", 
    "MAHARASHTRA": "", 
    "UTTARAKHAND": "",  
    "WEST_BENGAL": "", 
    # Add other states here as they appear in your folder...
}

# --- 4. Helper Functions (Cached) ---

@st.cache_data(show_spinner=False)
def load_single_file_from_drive(file_id):
    """Downloads a single dataset from Google Drive using File ID."""
    if not file_id:
        return None
        
    url = f'https://drive.google.com/uc?id={file_id}'
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "drive_data.zip")
    try:
        gdown.download(url, zip_path, quiet=True, fuzzy=True)
        return extract_and_read_first(zip_path, temp_dir)
    except Exception as e:
        st.error(f"Download failed: {e}")
        return None

@st.cache_data(show_spinner=False)
def load_github_data(url):
    """Downloads State Boundary from GitHub."""
    raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "github_data.zip")
    try:
        response = requests.get(raw_url)
        response.raise_for_status()
        with open(zip_path, "wb") as f:
            f.write(response.content)
        return extract_and_read_first(zip_path, temp_dir)
    except Exception as e:
        return None

def extract_and_read_first(zip_path, temp_dir):
    """Extracts zip and reads the FIRST shapefile found."""
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
    """Fixes encoding issues and standardizes columns."""
    # Standardize column names for consistency
    col_map = {
        'STATE_UT': 'STATE',
        'State': 'STATE',
        'Name': 'District',  # Often used in District files
        'Sub_dist': 'Subdistrict',
        'Vill_name': 'Village',
        'Vill_name_': 'Village' # Sometimes appearing with underscore
    }
    gdf.rename(columns=col_map, inplace=True)
    
    # Clean text artifacts
    target_cols = ['District', 'STATE', 'Subdistrict', 'Village']
    for col in target_cols:
        if col in gdf.columns:
            if pd.api.types.is_string_dtype(gdf[col]) or pd.api.types.is_object_dtype(gdf[col]):
                # Remove encoding artifacts like '>'
                gdf[col] = gdf[col].astype(str).str.replace('>', 'A').str.strip()
    return gdf

def convert_crs(gdf, target_epsg):
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf.to_crs(epsg=target_epsg)

def make_zip(source_dir):
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zip_file:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(file_path, os.path.relpath(file_path, source_dir))
    zip_buffer.seek(0)
    return zip_buffer

def handle_export(gdf, output_format, file_prefix="export"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_dir = os.path.join(tmp_dir, "output")
        os.makedirs(out_dir, exist_ok=True)
        
        file_ext = ""
        mime_type = "application/octet-stream"
        final_data = None
        
        try:
            if "Shapefile" in output_format:
                gdf.to_file(os.path.join(out_dir, f"{file_prefix}.shp"), driver="ESRI Shapefile", encoding='utf-8', engine='fiona')
                final_data = make_zip(out_dir)
                file_ext, mime_type = ".zip", "application/zip"
                
            elif "GeoJSON" in output_format:
                path = os.path.join(out_dir, f"{file_prefix}.geojson")
                gdf.to_file(path, driver="GeoJSON", engine='fiona')
                with open(path, "rb") as f: final_data = BytesIO(f.read())
                file_ext, mime_type = ".geojson", "application/json"
                
            elif "GeoPackage" in output_format:
                path = os.path.join(out_dir, f"{file_prefix}.gpkg")
                gdf.to_file(path, driver="GPKG", engine='fiona')
                with open(path, "rb") as f: final_data = BytesIO(f.read())
                file_ext, mime_type = ".gpkg", "application/x-sqlite3"
                
            elif "KML" in output_format:
                path = os.path.join(out_dir, f"{file_prefix}.kml")
                gdf.to_file(path, driver="KML", engine='fiona')
                with open(path, "rb") as f: final_data = BytesIO(f.read())
                file_ext, mime_type = ".kml", "application/vnd.google-earth.kml+xml"
            
            elif "CSV" in output_format:
                path = os.path.join(out_dir, f"{file_prefix}.csv")
                csv_gdf = gdf.copy()
                csv_gdf['geometry'] = csv_gdf.geometry.to_wkt()
                csv_gdf.to_csv(path, index=False)
                with open(path, "rb") as f: final_data = BytesIO(f.read())
                file_ext, mime_type = ".csv", "text/csv"
                
            elif "Excel" in output_format:
                path = os.path.join(out_dir, f"{file_prefix}.xlsx")
                excel_gdf = gdf.copy()
                excel_gdf['geometry'] = excel_gdf.geometry.astype(str)
                excel_gdf.to_excel(path, index=False)
                with open(path, "rb") as f: final_data = BytesIO(f.read())
                file_ext, mime_type = ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                
            return final_data, file_ext, mime_type
            
        except Exception as e:
            st.error(f"Export failed: {str(e)}")
            return None, None, None

# --- 5. Workflow Views ---

def view_admin_downloader():
    st.title("📥 Admin Boundary Downloader")
    st.markdown("Select an Indian administrative dataset, filter by region, and download.")
    
    col_config, col_preview = st.columns([1, 2], gap="large")
    
    with col_config:
        st.subheader("1. Select Source")
        source_type = st.radio(
            "Dataset Level",
            [
                "🏛️ Districts (Detailed)", 
                "🏘️ Subdistricts (Tehsil/Taluk)", 
                "🛖 Villages (Gram Panchayat)",
                "🗺️ States (Boundaries Only)"
            ]
        )
        
        gdf = None
        selected_feature = None
        filename = "export"
        
        # --- DISTRICTS ---
        if "Districts" in source_type:
            with st.spinner("Fetching District Database..."):
                gdf = load_single_file_from_drive('1tMyiUheQBcwwPwZQla67PwC5-AqenTmv')
        
        # --- SUBDISTRICTS ---
        elif "Subdistricts" in source_type:
            with st.spinner("Fetching Subdistrict Database..."):
                gdf = load_single_file_from_drive('18lMyt2j3Xjz_Qk_2Kzppr8EVlVDx_yOv')
        
        # --- STATES ---
        elif "States" in source_type:
            with st.spinner("Fetching State Database..."):
                gdf = load_github_data("https://github.com/nitesh4004/GeoFormatX/blob/main/STATE_BOUNDARY.zip")
        
        # --- VILLAGES (NEW FEATURE) ---
        elif "Villages" in source_type:
            st.info("ℹ️ Village data is heavy. Please select a state to download its specific database.")
            
            # 1. State Selection for File Loading
            available_states = list(STATE_VILLAGE_IDS.keys())
            target_state_key = st.selectbox("Select State for Village Data", available_states)
            
            file_id = STATE_VILLAGE_IDS.get(target_state_key)
            
            if not file_id:
                st.warning(f"⚠️ No File ID configured for {target_state_key}. Please update the `STATE_VILLAGE_IDS` dictionary in the code.")
                st.stop()
            
            with st.spinner(f"Downloading Village Map for {target_state_key}... (This may take time)"):
                gdf = load_single_file_from_drive(file_id)
                if gdf is None:
                    st.error("Failed to load village data. Check if the File ID is correct and public.")
                    st.stop()

        # --- DATA PROCESSING & FILTERING ---
        if gdf is None: st.stop()
        
        # Normalize and Clean
        gdf = clean_text_data(gdf) # Renames 'STATE_UT'->'STATE', 'Sub_dist'->'Subdistrict', 'Vill_name'->'Village'
        
        st.divider()
        st.subheader("2. Filter Area")
        
        # Helper to get unique sorted values safely
        def get_sorted_unique(df, col):
            return sorted(df[col].astype(str).unique()) if col in df.columns else []

        if 'STATE' in gdf.columns:
            # If we already selected state in "Villages" mode, we might auto-select or just filter
            states = get_sorted_unique(gdf, 'STATE')
            
            # Logic: If only one state exists (Village mode), default to it.
            index = 0
            if "Villages" in source_type and len(states) > 0:
                # Try to match the selected key (e.g. UTTARAKHAND) to the data content
                pass 
                
            sel_state = st.selectbox("Filter State", states, index=0)
            
            # --- FILTERING LOGIC ---
            
            # 1. Villages (Deepest Hierarchy)
            if "Villages" in source_type and 'District' in gdf.columns:
                state_gdf = gdf[gdf['STATE'] == sel_state]
                
                districts = get_sorted_unique(state_gdf, 'District')
                sel_district = st.selectbox("Select District", districts)
                
                dist_gdf = state_gdf[state_gdf['District'] == sel_district]
                
                if 'Subdistrict' in dist_gdf.columns:
                    subdistricts = get_sorted_unique(dist_gdf, 'Subdistrict')
                    sel_subdistrict = st.selectbox("Select Subdistrict (Tehsil)", subdistricts)
                    
                    subdist_gdf = dist_gdf[dist_gdf['Subdistrict'] == sel_subdistrict]
                    
                    if 'Village' in subdist_gdf.columns:
                        villages = get_sorted_unique(subdist_gdf, 'Village')
                        # Option to download whole subdistrict or specific village
                        filter_mode = st.radio("Selection Mode", ["All Villages in Subdistrict", "Specific Village"])
                        
                        if filter_mode == "Specific Village":
                            sel_village = st.selectbox("Select Village", villages)
                            selected_feature = subdist_gdf[subdist_gdf['Village'] == sel_village]
                            filename = f"{sel_village}_{sel_subdistrict}_Village"
                        else:
                            selected_feature = subdist_gdf
                            filename = f"{sel_subdistrict}_All_Villages"
                    else:
                        selected_feature = subdist_gdf
                        filename = f"{sel_subdistrict}_Villages"
                else:
                    selected_feature = dist_gdf
                    filename = f"{sel_district}_Villages"

            # 2. Districts / Subdistricts Logic (Existing)
            elif "Districts" in source_type and 'District' in gdf.columns:
                districts = get_sorted_unique(gdf[gdf['STATE'] == sel_state], 'District')
                sel_district = st.selectbox("Select District", districts)
                selected_feature = gdf[(gdf['STATE'] == sel_state) & (gdf['District'] == sel_district)]
                filename = f"{sel_district}_{sel_state}"
            
            elif "Subdistricts" in source_type and 'District' in gdf.columns and 'Subdistrict' in gdf.columns:
                state_gdf = gdf[gdf['STATE'] == sel_state]
                districts = get_sorted_unique(state_gdf, 'District')
                sel_district = st.selectbox("Select District", districts)
                
                dist_gdf = state_gdf[state_gdf['District'] == sel_district]
                subdistricts = get_sorted_unique(dist_gdf, 'Subdistrict')
                sel_subdistrict = st.selectbox("Select Subdistrict", subdistricts)
                
                selected_feature = dist_gdf[dist_gdf['Subdistrict'] == sel_subdistrict]
                filename = f"{sel_subdistrict}_{sel_district}_Subdistrict"
                
            else:
                selected_feature = gdf[gdf['STATE'] == sel_state]
                filename = f"{sel_state}_Boundary"

        # --- EXPORT SECTION (Common) ---
        st.divider()
        st.subheader("3. Export")
        out_fmt = st.selectbox("Format", ["ESRI Shapefile (.zip)", "GeoJSON", "KML", "GeoPackage (.gpkg)"])
        
        if st.button("🚀 Process & Prepare Download", type="primary"):
            if selected_feature is not None:
                with st.spinner("Processing geometry..."):
                    data, ext, mime = handle_export(selected_feature, out_fmt, filename)
                if data:
                    st.download_button(
                        label=f"💾 Download {filename}{ext}",
                        data=data,
                        file_name=f"{filename}{ext}",
                        mime=mime
                    )
            else:
                st.warning("Please make a selection first.")

    with col_preview:
        st.subheader("🗺️ Live Preview")
        if selected_feature is not None and not selected_feature.empty:
            # Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Selected Features", len(selected_feature))
            m2.metric("CRS", str(selected_feature.crs.name if selected_feature.crs else "N/A"))
            m3.metric("Geometry", selected_feature.geom_type.iloc[0])
            
            # Map
            try:
                # Convert to WGS84 for mapping
                map_data = selected_feature.to_crs(epsg=4326)
                
                # Intelligent Downsampling for Preview
                count = len(map_data)
                if count > 2000:
                    st.warning(f"⚠️ Dataset too large ({count} features). Displaying 1000 random samples for performance.")
                    st.map(map_data.sample(1000))
                else:
                    st.map(map_data)
                
                with st.expander("View Attribute Data", expanded=True):
                    st.dataframe(selected_feature.drop(columns='geometry').head(10))
            except Exception as e:
                st.warning(f"Map preview unavailable: {e}")
        else:
            st.info("Select a Region to generate a preview.")

def view_data_converter():
    st.title("🔄 Universal Data Converter")
    st.markdown("Upload your own vector data (Shapefile, CSV, KML, etc.) and convert it.")
    
    uploaded_file = st.file_uploader(
        "Drag and drop your file here", 
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
                if file_path.endswith('.zip'):
                    gdf = extract_and_read_first(file_path, tmp_dir)
                elif file_path.endswith(('.csv', '.xlsx')):
                    df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
                    st.warning("⚠️ Tabular data detected. Please specify geometry columns.")
                    c1, c2, c3 = st.columns(3)
                    mode = c1.radio("Geo Type", ["Lat/Lon", "WKT"])
                    if mode == "Lat/Lon":
                        x = c2.selectbox("Longitude", df.columns)
                        y = c3.selectbox("Latitude", df.columns)
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
                st.error(f"Error reading file: {e}")
            
            if gdf is not None:
                st.success("✅ File uploaded successfully!")
                
                col_sets, col_map = st.columns([1, 1], gap="medium")
                
                with col_sets:
                    st.subheader("⚙️ Conversion Settings")
                    with st.expander("🌐 CRS Reprojection (Optional)", expanded=True):
                        enable_crs = st.checkbox("Reproject Coordinates")
                        target_epsg = st.number_input("Target EPSG", value=4326, disabled=not enable_crs)
                    
                    target_format = st.selectbox(
                        "Target Format", 
                        ["ESRI Shapefile (.zip)", "GeoJSON", "GeoPackage (.gpkg)", "KML", "CSV (WKT)", "Excel (.xlsx)"]
                    )
                    
                    if enable_crs:
                        gdf = convert_crs(gdf, target_epsg)
                        
                    if st.button("🔄 Convert File", type="primary"):
                        data, ext, mime = handle_export(gdf, target_format, "converted_data")
                        if data:
                            st.download_button("💾 Download Result", data, f"converted{ext}", mime)

                with col_map:
                    st.subheader("👀 Preview")
                    try:
                        st.map(gdf.to_crs(4326) if gdf.crs else gdf)
                    except:
                        st.write("Visual preview not available.")

# --- 6. Main Navigation Controller ---

def main():
    st.sidebar.title("🌍 GeoConvert Pro")
    st.sidebar.markdown("---")
    
    mode = st.sidebar.radio(
        "Select Mode:",
        ["📥 Admin Boundary Downloader", "🔄 Universal Data Converter"],
        captions=["Get India Districts/States/Villages", "Format conversion tool"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info(
        "**Supported Formats:**\n"
        "- Shapefile (zipped)\n"
        "- GeoJSON, KML, GPKG\n"
        "- CSV/Excel (Lat/Lon or WKT)"
    )

    if mode == "📥 Admin Boundary Downloader":
        view_admin_downloader()
    else:
        view_data_converter()

if __name__ == "__main__":
    main()
