import streamlit as st
import geopandas as gpd
import pandas as pd
import fiona
import os
import shutil
import tempfile
import gdown  # New dependency for robust Drive downloads
from zipfile import ZipFile
from io import BytesIO
import glob
from shapely import wkt

# --- 1. Configuration & Drivers ---
st.set_page_config(
    page_title="GeoConvert Pro | India District Portal",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enable KML/KMZ drivers for Fiona
fiona.drvsupport.supported_drivers['KML'] = 'rw'
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'

# --- 2. CSS Styling ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #4CAF50; color: white; }
    .stDownloadButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #008CBA; color: white; }
    .stSuccess, .stInfo { border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Helper Functions ---

@st.cache_data(show_spinner=False)
def load_default_data():
    """
    Downloads and caches the District Boundary from Google Drive using gdown.
    gdown handles large file warnings and tokens automatically.
    """
    # Your specific Google Drive File ID
    file_id = '1tMyiUheQBcwwPwZQla67PwC5-AqenTmv'
    # Construct the URL for gdown
    url = f'https://drive.google.com/uc?id={file_id}'
    
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "default_districts.zip")
    
    try:
        # Using gdown for robust download
        # quiet=True suppresses standard output logs
        gdown.download(url, zip_path, quiet=True, fuzzy=True)
        
        # Verify file exists and is not empty
        if not os.path.exists(zip_path) or os.path.getsize(zip_path) == 0:
            st.error("Download failed or file is empty.")
            return None

        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        spatial_files = []
        # Search for shapefiles recursively
        for ext in ['*.shp']:
            spatial_files.extend(glob.glob(os.path.join(temp_dir, '**', ext), recursive=True))
            
        if spatial_files:
            return gpd.read_file(spatial_files[0])
        else:
            st.error("Default database error: No Shapefile found in the downloaded archive.")
            return None
            
    except Exception as e:
        st.error(f"Failed to load default database: {e}")
        return None

def save_uploaded_file(uploaded_file, temp_dir):
    try:
        file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None

def extract_zip(zip_path, extract_to):
    with ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    spatial_files = []
    # Priority search for spatial formats
    for ext in ['*.shp', '*.gpkg', '*.geojson', '*.kml', '*.json', '*.tab']:
        spatial_files.extend(glob.glob(os.path.join(extract_to, '**', ext), recursive=True))
    
    # Prioritize Shapefile if multiple exist
    shp_files = [f for f in spatial_files if f.endswith('.shp')]
    if shp_files:
        return shp_files[0]
    return spatial_files[0] if spatial_files else None

def make_zip(source_dir, output_filename):
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zip_file:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(file_path, os.path.relpath(file_path, source_dir))
    zip_buffer.seek(0)
    return zip_buffer

def convert_crs(gdf, target_crs):
    """Reprojects the GeoDataFrame to the target coordinate reference system."""
    if gdf.crs is None:
        st.warning("⚠️ Input data has no defined CRS. Assuming WGS84 (EPSG:4326).")
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf.to_crs(target_crs)

def clean_text_data(gdf):
    """Auto-fixes encoding issues (e.g. GUJAR>T -> GUJARAT)."""
    cleaned = False
    target_cols = ['District', 'STATE', 'district', 'state', 'Name', 'name']
    for col in target_cols:
        if col in gdf.columns:
            if pd.api.types.is_string_dtype(gdf[col]) or pd.api.types.is_object_dtype(gdf[col]):
                if gdf[col].astype(str).str.contains('>').any():
                    gdf[col] = gdf[col].astype(str).str.replace('>', 'A')
                    cleaned = True
    return gdf, cleaned

def handle_export(gdf, output_format, tmp_dir, file_prefix="export"):
    out_dir = os.path.join(tmp_dir, "output_" + file_prefix)
    os.makedirs(out_dir, exist_ok=True)
    
    file_ext = ""
    mime_type = "application/octet-stream"
    final_buffer = None
    final_path = None

    try:
        if "Shapefile" in output_format:
            shp_path = os.path.join(out_dir, f"{file_prefix}.shp")
            gdf.to_file(shp_path, driver="ESRI Shapefile", encoding='utf-8')
            final_buffer = make_zip(out_dir, f"{file_prefix}.zip")
            file_ext = ".zip"
            mime_type = "application/zip"
            
        elif "GeoJSON" in output_format:
            final_path = os.path.join(out_dir, f"{file_prefix}.geojson")
            gdf.to_file(final_path, driver="GeoJSON")
            file_ext = ".geojson"
            mime_type = "application/json"
            
        elif "GeoPackage" in output_format:
            final_path = os.path.join(out_dir, f"{file_prefix}.gpkg")
            gdf.to_file(final_path, driver="GPKG")
            file_ext = ".gpkg"
            
        elif "KML" in output_format:
            final_path = os.path.join(out_dir, f"{file_prefix}.kml")
            gdf.to_file(final_path, driver="KML")
            file_ext = ".kml"
            mime_type = "application/vnd.google-earth.kml+xml"

        elif "CSV" in output_format:
            final_path = os.path.join(out_dir, f"{file_prefix}.csv")
            csv_gdf = gdf.copy()
            csv_gdf['geometry'] = csv_gdf.geometry.to_wkt()
            csv_gdf.to_csv(final_path, index=False)
            file_ext = ".csv"
            mime_type = "text/csv"
            
        elif "Excel" in output_format:
            final_path = os.path.join(out_dir, f"{file_prefix}.xlsx")
            excel_gdf = gdf.copy()
            excel_gdf['geometry'] = excel_gdf.geometry.astype(str)
            excel_gdf.to_excel(final_path, index=False)
            file_ext = ".xlsx"
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            
    except Exception as e:
        st.error(f"Export Error: {e}")
        return None, None, None, None

    return final_buffer, final_path, file_ext, mime_type

# --- 4. Main Application Logic ---

def main():
    st.title("🌍 GeoConvert Pro | India District Portal")
    st.markdown("### Universal Vector Data Converter & District Extractor")

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("1. Data Source")
        data_source = st.radio(
            "Select Source",
            ["🇮🇳 India District Database (Default)", "📂 Upload Custom File"]
        )
        
        uploaded_file = None
        if data_source == "📂 Upload Custom File":
            uploaded_file = st.file_uploader(
                "Upload File", 
                type=['zip', 'shp', 'geojson', 'kml', 'gpkg', 'csv', 'xlsx', 'tab']
            )

        st.header("2. Processing")
        enable_reprojection = st.checkbox("Reproject Coordinates", value=False)
        target_epsg = st.number_input("Target EPSG Code", min_value=1, value=4326, disabled=not enable_reprojection)

        st.header("3. Output Settings")
        output_format = st.selectbox(
            "Target Format",
            ["ESRI Shapefile (.zip)", "GeoJSON", "GeoPackage (.gpkg)", "KML", "CSV (WKT)", "Excel (.xlsx)"]
        )

    # --- MAIN CONTENT ---
    gdf = None
    
    # A. Data Loading Strategy
    if data_source == "🇮🇳 India District Database (Default)":
        with st.spinner("Connecting to District Database (via gdown)..."):
            gdf = load_default_data()
            if gdf is not None:
                st.success("✅ Connected to India District Database")

    elif uploaded_file:
        # Custom File Handling (Including Advanced CSV/Excel Logic)
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = save_uploaded_file(uploaded_file, tmp_dir)
            
            # Case 1: ZIP (Shapefile)
            if file_path.endswith('.zip'):
                extract_dir = os.path.join(tmp_dir, "extracted")
                os.makedirs(extract_dir, exist_ok=True)
                main_file = extract_zip(file_path, extract_dir)
                if main_file:
                    gdf = gpd.read_file(main_file)
                    st.info(f"📂 Read: {os.path.basename(main_file)}")
            
            # Case 2: Tabular (CSV/Excel)
            elif file_path.endswith(('.csv', '.xlsx')):
                df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
                st.write("### 🛠️ Tabular Configuration")
                st.dataframe(df.head(3))
                
                col1, col2 = st.columns(2)
                mode = col1.radio("Geometry Type", ["Lat/Lon Columns", "WKT Column"])
                
                if mode == "Lat/Lon Columns":
                    lon_col = col2.selectbox("Longitude (X)", df.columns, index=min(1, len(df.columns)-1))
                    lat_col = col2.selectbox("Latitude (Y)", df.columns, index=min(2, len(df.columns)-1))
                    if st.button("Create Geometry"):
                        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon_col], df[lat_col]), crs="EPSG:4326")
                else:
                    wkt_col = col2.selectbox("Select WKT Column", df.columns)
                    if st.button("Parse WKT"):
                        try:
                            df['geometry'] = df[wkt_col].apply(wkt.loads)
                            gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
                        except Exception as e:
                            st.error(f"WKT Error: {e}")
            
            # Case 3: Standard Vectors
            else:
                gdf = gpd.read_file(file_path)

    # B. Data Processing & Visualization
    if gdf is not None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            
            # 1. Auto-Clean Text (Fixing '>')
            gdf, cleaned = clean_text_data(gdf)
            if cleaned:
                st.info("✨ Auto-corrected text encoding issues (Replaced '>' with 'A').")

            # 2. Reprojection
            if enable_reprojection:
                gdf = convert_crs(gdf, f"EPSG:{target_epsg}")

            # 3. Metadata Display
            st.divider()
            col_info, col_map = st.columns([1, 2])
            with col_info:
                st.subheader("📊 Metadata")
                st.write(f"**Features:** {len(gdf)}")
                st.write(f"**CRS:** {gdf.crs}")
                st.write(f"**Geom:** {gdf.geom_type.unique()}")
                with st.expander("View Data Table"):
                    st.dataframe(gdf.drop(columns='geometry').head(10))

            with col_map:
                st.subheader("🗺️ Preview")
                try:
                    # Map always needs Lat/Lon
                    map_gdf = gdf.to_crs(epsg=4326) if gdf.crs else gdf
                    st.map(map_gdf)
                except:
                    st.write("Map preview unavailable.")

            # ==========================================
            # 📍 FEATURE: DISTRICT EXTRACTOR
            # ==========================================
            # Check for District/State columns (Case Sensitive)
            has_district = 'District' in gdf.columns
            has_state = 'STATE' in gdf.columns

            if has_district and has_state:
                st.write("---")
                st.markdown("### 📍 Select & Download District")
                st.info("Use the filters below to extract a single district.")
                
                dc1, dc2, dc3 = st.columns(3)
                
                # 1. Select State
                states_list = sorted(gdf['STATE'].astype(str).unique())
                selected_state = dc1.selectbox("1. Select State", states_list)
                
                # 2. Select District (Filtered by State)
                district_list = sorted(gdf[gdf['STATE'] == selected_state]['District'].astype(str).unique())
                selected_district = dc2.selectbox("2. Select District", district_list)
                
                # 3. Download Action
                with dc3:
                    st.write(f"3. Download ({output_format})")
                    if st.button(f"Generate {selected_district}"):
                        # Create Subset
                        subset_gdf = gdf[
                            (gdf['STATE'] == selected_state) & 
                            (gdf['District'] == selected_district)
                        ]
                        
                        # Export
                        f_buff, f_path, f_ext, f_mime = handle_export(
                            subset_gdf, output_format, tmp_dir, 
                            file_prefix=f"{selected_district}_{selected_state}"
                        )
                        
                        # Serve File
                        if f_buff:
                            st.download_button(
                                label=f"📥 Download {selected_district}",
                                data=f_buff,
                                file_name=f"{selected_district}{f_ext}",
                                mime=f_mime
                            )
                        elif f_path:
                            with open(f_path, "rb") as f:
                                st.download_button(
                                    label=f"📥 Download {selected_district}",
                                    data=f,
                                    file_name=f"{selected_district}{f_ext}",
                                    mime=f_mime
                                )

            # ==========================================
            # 📤 GLOBAL DOWNLOAD
            # ==========================================
            st.write("---")
            with st.expander("Advanced: Convert & Download Full Dataset"):
                st.write("Export the entire loaded dataset in the selected format.")
                if st.button("Process Full Dataset"):
                    with st.spinner("Processing..."):
                        f_buff, f_path, f_ext, f_mime = handle_export(gdf, output_format, tmp_dir, file_prefix="full_export")
                        
                        if f_buff:
                            st.download_button("Download Full File", f_buff, f"converted_full{f_ext}", mime=f_mime)
                        elif f_path:
                            with open(f_path, "rb") as f:
                                st.download_button("Download Full File", f, f"converted_full{f_ext}", mime=f_mime)

if __name__ == "__main__":
    main()
