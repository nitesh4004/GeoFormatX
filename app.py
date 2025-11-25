import streamlit as st
import geopandas as gpd
import pandas as pd
import fiona
import os
import shutil
import tempfile
from zipfile import ZipFile
from io import BytesIO
import glob
from shapely import wkt

# --- Configuration & Drivers ---
st.set_page_config(
    page_title="GeoConvert Pro | District Extractor",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enable KML/KMZ drivers for Fiona
fiona.drvsupport.supported_drivers['KML'] = 'rw'
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'

# --- CSS Styling ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #4CAF50; color: white; }
    .stDownloadButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #008CBA; color: white; }
    .stSuccess { padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---

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
    """Fixes specific encoding issues found in the user's dataset (e.g. '>' -> 'A')."""
    cleaned = False
    target_cols = ['District', 'STATE', 'district', 'state']
    
    for col in target_cols:
        if col in gdf.columns:
            # Check if column has string data
            if pd.api.types.is_string_dtype(gdf[col]) or pd.api.types.is_object_dtype(gdf[col]):
                # Only apply fix if we detect the specific issue to avoid over-cleaning
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

# --- Main App Logic ---

def main():
    st.title("🌍 GeoConvert Pro")
    st.markdown("### Universal Vector Data Converter & ETL Tool")

    # 1. Sidebar: Controls
    with st.sidebar:
        st.header("1. Input Data")
        uploaded_file = st.file_uploader(
            "Upload geospatial file", 
            type=['zip', 'shp', 'geojson', 'kml', 'gpkg', 'csv', 'xlsx'],
            help="Upload your DISTRICT_BOUNDARY.zip here"
        )

        st.header("2. Processing Settings")
        enable_reprojection = st.checkbox("Reproject Coordinates", value=False)
        target_epsg = st.number_input("Target EPSG Code", min_value=1, value=4326, disabled=not enable_reprojection)

        st.header("3. Output Settings")
        output_format = st.selectbox(
            "Target Format",
            ["ESRI Shapefile (.zip)", "GeoJSON", "GeoPackage (.gpkg)", "KML", "CSV (WKT)", "Excel (.xlsx)"]
        )

    # 2. Main Processing Block
    if uploaded_file:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = save_uploaded_file(uploaded_file, tmp_dir)
            
            try:
                gdf = None
                
                # Load Logic
                if file_path.endswith('.zip'):
                    extract_dir = os.path.join(tmp_dir, "extracted")
                    os.makedirs(extract_dir, exist_ok=True)
                    main_file = extract_zip(file_path, extract_dir)
                    if main_file:
                        gdf = gpd.read_file(main_file)
                        st.info(f"📂 Loaded: `{os.path.basename(main_file)}`")
                    else:
                        st.error("No spatial file found in zip.")
                
                elif file_path.endswith(('.csv', '.xlsx')):
                    df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
                    st.write("### Tabular Data Setup")
                    st.dataframe(df.head(3))
                    col1, col2 = st.columns(2)
                    if col1.checkbox("Has Lat/Lon Columns?", value=True):
                        lon = col2.selectbox("Longitude", df.columns)
                        lat = col2.selectbox("Latitude", df.columns)
                        if st.button("Create Geometry"):
                            gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon], df[lat]), crs="EPSG:4326")
                
                else:
                    gdf = gpd.read_file(file_path)

                # --- Processing ---
                if gdf is not None:
                    
                    # 1. Auto-Clean Text Data (Fixing GUJAR>T -> GUJARAT)
                    gdf, cleaned = clean_text_data(gdf)
                    if cleaned:
                        st.success("✨ Automatically fixed character encoding issues (replaced '>' with 'A') in District/State names.")

                    # 2. Reprojection
                    if enable_reprojection:
                        gdf = convert_crs(gdf, f"EPSG:{target_epsg}")

                    # 3. Metadata & Map
                    st.divider()
                    col_info, col_map = st.columns([1, 2])
                    with col_info:
                        st.subheader("📊 Metadata")
                        st.write(f"**CRS:** {gdf.crs}")
                        st.write(f"**Features:** {len(gdf)}")
                        with st.expander("View Table"):
                            st.dataframe(gdf.drop(columns='geometry').head(5))
                    with col_map:
                        st.subheader("🗺️ Preview")
                        try:
                            st.map(gdf.to_crs(epsg=4326) if gdf.crs else gdf)
                        except:
                            st.write("Map preview unavailable.")

                    # ==========================================
                    # 📍 FEATURE: DISTRICT EXTRACTOR
                    # ==========================================
                    
                    if 'District' in gdf.columns and 'STATE' in gdf.columns:
                        st.write("---")
                        st.markdown("### 📍 District Extractor")
                        st.info("Select a State and District to extract and download individually.")
                        
                        dc1, dc2, dc3 = st.columns(3)
                        
                        # Sort and unique values
                        states = sorted(gdf['STATE'].astype(str).unique())
                        selected_state = dc1.selectbox("1. Select State", states)
                        
                        districts = sorted(gdf[gdf['STATE'] == selected_state]['District'].astype(str).unique())
                        selected_district = dc2.selectbox("2. Select District", districts)
                        
                        # Filter Data
                        subset_gdf = gdf[
                            (gdf['STATE'] == selected_state) & 
                            (gdf['District'] == selected_district)
                        ]
                        
                        with dc3:
                            st.write("3. Download")
                            f_buff, f_path, f_ext, f_mime = handle_export(
                                subset_gdf, output_format, tmp_dir, 
                                file_prefix=f"{selected_district}_{selected_state}"
                            )
                            
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
                    if st.button(f"Convert & Download Full Dataset ({output_format})"):
                        f_buff, f_path, f_ext, f_mime = handle_export(gdf, output_format, tmp_dir, file_prefix="full_dataset")
                        
                        if f_buff:
                            st.download_button("Download File", f_buff, f"converted_full{f_ext}", mime=f_mime)
                        elif f_path:
                            with open(f_path, "rb") as f:
                                st.download_button("Download File", f, f"converted_full{f_ext}", mime=f_mime)

            except Exception as e:
                st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
