import streamlit as st
import geopandas as gpd
import pandas as pd
import fiona
import os
import tempfile
import gdown  # For Google Drive
import requests  # For GitHub
from zipfile import ZipFile
from io import BytesIO
import glob
from shapely import wkt

# --- 1. Configuration & Drivers ---
st.set_page_config(
    page_title="GeoConvert Pro | India Portal",
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
def load_drive_data(file_id):
    """Downloads District Database from Google Drive using gdown."""
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
    """Downloads State Boundary from GitHub (Raw)."""
    # Convert 'blob' to 'raw' if necessary
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
        st.error(f"Failed to load GitHub data: {e}")
        return None

def extract_and_read(zip_path, temp_dir):
    """Helper to unzip and read the first shapefile found."""
    if not os.path.exists(zip_path) or os.path.getsize(zip_path) == 0:
        return None

    with ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
        
    spatial_files = []
    for ext in ['*.shp']:
        spatial_files.extend(glob.glob(os.path.join(temp_dir, '**', ext), recursive=True))
        
    if spatial_files:
        return gpd.read_file(spatial_files[0])
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

def extract_zip_uploaded(zip_path, extract_to):
    with ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    spatial_files = []
    for ext in ['*.shp', '*.gpkg', '*.geojson', '*.kml', '*.json', '*.tab']:
        spatial_files.extend(glob.glob(os.path.join(extract_to, '**', ext), recursive=True))
    
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
    st.title("🌍 GeoConvert Pro | India Portal")
    st.markdown("### Universal Vector Data Converter & Extractor")

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("1. Data Source")
        data_source = st.radio(
            "Select Source",
            [
                "🇮🇳 District Database (Default)", 
                "🗺️ State Boundary (GitHub)",
                "📂 Upload Custom File"
            ]
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
    if data_source == "🇮🇳 District Database (Default)":
        with st.spinner("Connecting to District Database (via gdown)..."):
            # District ID from previous context
            gdf = load_drive_data('1tMyiUheQBcwwPwZQla67PwC5-AqenTmv')
            if gdf is not None:
                st.success(f"✅ Loaded {len(gdf)} Districts")

    elif data_source == "🗺️ State Boundary (GitHub)":
        with st.spinner("Connecting to State Repository (via GitHub)..."):
            # Direct GitHub URL provided by user
            state_url = "https://github.com/nitesh4004/GeoFormatX/blob/main/STATE_BOUNDARY.zip"
            gdf = load_github_data(state_url)
            if gdf is not None:
                st.success(f"✅ Loaded {len(gdf)} States")

    elif uploaded_file:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = save_uploaded_file(uploaded_file, tmp_dir)
            if file_path.endswith('.zip'):
                extract_dir = os.path.join(tmp_dir, "extracted")
                os.makedirs(extract_dir, exist_ok=True)
                main_file = extract_zip_uploaded(file_path, extract_dir)
                if main_file:
                    gdf = gpd.read_file(main_file)
                    st.info(f"📂 Read: {os.path.basename(main_file)}")
            # ... (Existing CSV/Excel logic can remain here if needed) ...
            elif file_path.endswith(('.csv', '.xlsx')):
                df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
                st.write("### 🛠️ Tabular Configuration")
                st.dataframe(df.head(3))
                col1, col2 = st.columns(2)
                mode = col1.radio("Geometry Type", ["Lat/Lon Columns", "WKT Column"])
                if mode == "Lat/Lon Columns":
                    lon_col = col2.selectbox("Longitude (X)", df.columns)
                    lat_col = col2.selectbox("Latitude (Y)", df.columns)
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
            else:
                gdf = gpd.read_file(file_path)

    # B. Data Processing & Visualization
    if gdf is not None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            
            # 1. Auto-Clean Text
            gdf, cleaned = clean_text_data(gdf)
            
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
                # Show first 5 columns to help user verify data
                st.write(f"**Attributes:** {list(gdf.columns[:5])}") 

            with col_map:
                st.subheader("🗺️ Preview")
                try:
                    map_gdf = gdf.to_crs(epsg=4326) if gdf.crs else gdf
                    st.map(map_gdf)
                except:
                    st.write("Map preview unavailable.")

            # ==========================================
            # 📍 FEATURE: SMART DATA EXTRACTOR
            # ==========================================
            st.write("---")
            st.markdown("### 📍 Location Extractor")
            
            # Identify Column Structure
            has_district = 'District' in gdf.columns
            has_state = 'STATE' in gdf.columns

            # Layout Columns
            dc1, dc2, dc3 = st.columns(3)
            selected_feature = None
            filename_suffix = ""

            # LOGIC 1: State + District Data
            if has_state and has_district:
                states_list = sorted(gdf['STATE'].astype(str).unique())
                selected_state = dc1.selectbox("1. Select State", states_list)
                
                districts_list = sorted(gdf[gdf['STATE'] == selected_state]['District'].astype(str).unique())
                selected_district = dc2.selectbox("2. Select District", districts_list)
                
                selected_feature = gdf[
                    (gdf['STATE'] == selected_state) & 
                    (gdf['District'] == selected_district)
                ]
                filename_suffix = f"{selected_district}_{selected_state}"
            
            # LOGIC 2: State Boundary Data Only
            elif has_state and not has_district:
                states_list = sorted(gdf['STATE'].astype(str).unique())
                selected_state = dc1.selectbox("1. Select State to Extract", states_list)
                
                dc2.info("ℹ️ State-level dataset detected. District selection disabled.")
                
                selected_feature = gdf[gdf['STATE'] == selected_state]
                filename_suffix = f"{selected_state}_Boundary"

            # LOGIC 3: Unknown Custom Data
            else:
                st.warning("Could not detect standard 'STATE' or 'District' columns for auto-extraction.")

            # DOWNLOAD ACTION
            if selected_feature is not None:
                with dc3:
                    st.write(f"3. Export ({output_format})")
                    if st.button(f"Generate File"):
                        f_buff, f_path, f_ext, f_mime = handle_export(
                            selected_feature, output_format, tmp_dir, 
                            file_prefix=filename_suffix
                        )
                        
                        if f_buff:
                            st.download_button(f"📥 Download {filename_suffix}", f_buff, f"{filename_suffix}{f_ext}", mime=f_mime)
                        elif f_path:
                            with open(f_path, "rb") as f:
                                st.download_button(f"📥 Download {filename_suffix}", f, f"{filename_suffix}{f_ext}", mime=f_mime)

            # Global Download
            st.write("---")
            with st.expander("Advanced: Convert & Download Full Dataset"):
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
