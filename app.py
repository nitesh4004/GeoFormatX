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

# --- 3. Helper Functions (Cached) ---

@st.cache_data(show_spinner=False)
def load_drive_data(file_id):
    """Downloads Dataset from Google Drive."""
    url = f'https://drive.google.com/uc?id={file_id}'
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "drive_data.zip")
    try:
        gdown.download(url, zip_path, quiet=True, fuzzy=True)
        return extract_and_read(zip_path, temp_dir)
    except Exception as e:
        st.error(f"Failed to load Drive data: {e}")
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
        return extract_and_read(zip_path, temp_dir)
    except Exception as e:
        return None

def extract_and_read(zip_path, temp_dir):
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
    # Added Sub_dist and STATE_UT to targets based on your screenshot
    target_cols = ['District', 'STATE', 'district', 'state', 'Name', 'name', 'Sub_dist', 'STATE_UT']
    for col in target_cols:
        if col in gdf.columns:
            if pd.api.types.is_string_dtype(gdf[col]) or pd.api.types.is_object_dtype(gdf[col]):
                # Generic cleanup for encoding artifacts like '>'
                if gdf[col].astype(str).str.contains('>').any():
                    gdf[col] = gdf[col].astype(str).str.replace('>', 'A')
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

# --- 4. Workflow Views ---

def view_admin_downloader():
    st.title("📥 Admin Boundary Downloader")
    st.markdown("Select an Indian administrative dataset, filter by region, and download in your preferred format.")
    
    col_config, col_preview = st.columns([1, 2], gap="large")
    
    with col_config:
        st.subheader("1. Select Source")
        source_type = st.radio(
            "Dataset Level",
            [
                "🏛️ Districts (Detailed)", 
                "🏘️ Subdistricts (Tehsil/Taluk)", 
                "🗺️ States (Boundaries Only)"
            ],
            captions=[
                "District attributes & boundaries", 
                "Detailed Sub-District boundaries", 
                "State outlines only"
            ]
        )
        
        gdf = None
        # Logic to load data based on selection
        if "Districts" in source_type:
            with st.spinner("Fetching District Database..."):
                gdf = load_drive_data('1tMyiUheQBcwwPwZQla67PwC5-AqenTmv')
        
        elif "Subdistricts" in source_type:
            with st.spinner("Fetching Subdistrict Database..."):
                # New Drive ID for subdistricts
                gdf = load_drive_data('18lMyt2j3Xjz_Qk_2Kzppr8EVlVDx_yOv')
                
        else: # States
            with st.spinner("Fetching State Database..."):
                gdf = load_github_data("https://github.com/nitesh4004/GeoFormatX/blob/main/STATE_BOUNDARY.zip")
        
        if gdf is None:
            st.stop()
            
        # --- Normalization Block ---
        # Rename STATE_UT to STATE for consistency if present (based on screenshot)
        if 'STATE_UT' in gdf.columns:
            gdf.rename(columns={'STATE_UT': 'STATE'}, inplace=True)
            
        gdf = clean_text_data(gdf)
        
        st.divider()
        st.subheader("2. Filter Area")
        
        # Filtering Logic
        selected_feature = None
        filename = "export"
        
        if 'STATE' in gdf.columns:
            states = sorted(gdf['STATE'].astype(str).unique())
            sel_state = st.selectbox("Select State", states)
            
            # --- Logic for Districts ---
            if "Districts" in source_type and 'District' in gdf.columns:
                districts = sorted(gdf[gdf['STATE'] == sel_state]['District'].astype(str).unique())
                sel_district = st.selectbox("Select District", districts)
                selected_feature = gdf[(gdf['STATE'] == sel_state) & (gdf['District'] == sel_district)]
                filename = f"{sel_district}_{sel_state}"
            
            # --- Logic for Subdistricts (New) ---
            elif "Subdistricts" in source_type and 'District' in gdf.columns and 'Sub_dist' in gdf.columns:
                # First filter by State to get Districts
                state_gdf = gdf[gdf['STATE'] == sel_state]
                districts = sorted(state_gdf['District'].astype(str).unique())
                
                sel_district = st.selectbox("Select District", districts)
                
                # Then filter by District to get Subdistricts
                dist_gdf = state_gdf[state_gdf['District'] == sel_district]
                subdistricts = sorted(dist_gdf['Sub_dist'].astype(str).unique())
                
                sel_subdistrict = st.selectbox("Select Subdistrict", subdistricts)
                
                selected_feature = dist_gdf[dist_gdf['Sub_dist'] == sel_subdistrict]
                filename = f"{sel_subdistrict}_{sel_district}_Subdistrict"
                
            # --- Logic for States ---
            else:
                selected_feature = gdf[gdf['STATE'] == sel_state]
                filename = f"{sel_state}_Boundary"
        
        st.divider()
        st.subheader("3. Export")
        out_fmt = st.selectbox("Format", ["ESRI Shapefile (.zip)", "GeoJSON", "KML", "GeoPackage (.gpkg)"])
        
        if st.button("🚀 Process & Prepare Download", type="primary"):
            data, ext, mime = handle_export(selected_feature, out_fmt, filename)
            if data:
                st.download_button(
                    label=f"💾 Download {filename}{ext}",
                    data=data,
                    file_name=f"{filename}{ext}",
                    mime=mime
                )

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
                st.map(map_data)
                
                with st.expander("View Attribute Data"):
                    # Drop geometry to just show the table
                    st.dataframe(selected_feature.drop(columns='geometry').head())
            except Exception as e:
                st.warning("Map preview unavailable.")
        else:
            st.info("Select a Region to generate a preview.")

def view_data_converter():
    st.title("🔄 Universal Data Converter")
    st.markdown("Upload your own vector data (Shapefile, CSV, KML, etc.) and convert it to any format.")
    
    # 1. Upload Section
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
                
            # Reading Logic
            try:
                if file_path.endswith('.zip'):
                    gdf = extract_and_read(file_path, tmp_dir)
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
            
            # 2. Transformation & Download Section
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
                    st.write(f"**CRS:** {gdf.crs}")
                    st.write(f"**Rows:** {len(gdf)}")
                    try:
                        st.map(gdf.to_crs(4326) if gdf.crs else gdf)
                    except:
                        st.write("Visual preview not available.")

# --- 5. Main Navigation Controller ---

def main():
    # Sidebar Navigation styling
    st.sidebar.title("🌍 GeoConvert Pro")
    st.sidebar.markdown("---")
    
    # Simple Radio Button Navigation
    mode = st.sidebar.radio(
        "Select Mode:",
        ["📥 Admin Boundary Downloader", "🔄 Universal Data Converter"],
        captions=["Get India Districts/States", "Format conversion tool"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info(
        "**Supported Formats:**\n"
        "- Shapefile (zipped)\n"
        "- GeoJSON, KML, GPKG\n"
        "- CSV/Excel (Lat/Lon or WKT)"
    )

    # Route to Views
    if mode == "📥 Admin Boundary Downloader":
        view_admin_downloader()
    else:
        view_data_converter()

if __name__ == "__main__":
    main()
