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
    page_title="GeoConvert Pro | Vector Data ETL",
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
    """Saves uploaded stream to a temporary file path."""
    try:
        file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None

def extract_zip(zip_path, extract_to):
    """Extracts zip and looks for spatial files."""
    with ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    # Heuristic: Find the largest .shp file or first .gpkg/.geojson
    spatial_files = []
    for ext in ['*.shp', '*.gpkg', '*.geojson', '*.kml', '*.json', '*.tab']:
        spatial_files.extend(glob.glob(os.path.join(extract_to, '**', ext), recursive=True))
    
    # Return the most likely main file (shapefile preferred in zips)
    shp_files = [f for f in spatial_files if f.endswith('.shp')]
    if shp_files:
        return shp_files[0]
    return spatial_files[0] if spatial_files else None

def make_zip(source_dir, output_filename):
    """Zips a directory for download (used for Shapefiles)."""
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zip_file:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(file_path, os.path.relpath(file_path, source_dir))
    zip_buffer.seek(0)
    return zip_buffer

def convert_crs(gdf, target_crs):
    """Reprojects GeoDataFrame."""
    if gdf.crs is None:
        st.warning("⚠️ Input data has no defined CRS. Assuming WGS84 (EPSG:4326).")
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf.to_crs(target_crs)

def handle_export(gdf, output_format, tmp_dir, file_prefix="export"):
    """
    Centralized export logic.
    Returns: (buffer, filepath, extension, mime_type)
    """
    out_dir = os.path.join(tmp_dir, "output_" + file_prefix)
    os.makedirs(out_dir, exist_ok=True)
    
    file_ext = ""
    mime_type = "application/octet-stream"
    final_buffer = None
    final_path = None

    try:
        if "Shapefile" in output_format:
            # Shapefile requires a folder, then zipping
            shp_path = os.path.join(out_dir, f"{file_prefix}.shp")
            # Truncate columns if needed for Shapefile limits
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

        elif "FlatGeobuf" in output_format:
            final_path = os.path.join(out_dir, f"{file_prefix}.fgb")
            gdf.to_file(final_path, driver="FlatGeobuf")
            file_ext = ".fgb"
            
        elif "CSV" in output_format:
            final_path = os.path.join(out_dir, f"{file_prefix}.csv")
            csv_gdf = gdf.copy()
            # Convert geometry to WKT for CSV
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
            type=['zip', 'shp', 'geojson', 'json', 'kml', 'gpkg', 'csv', 'xlsx', 'gpx', 'tab'],
            help="For Shapefiles, upload a .zip containing .shp, .shx, and .dbf"
        )

        st.header("2. Processing Settings")
        enable_reprojection = st.checkbox("Reproject Coordinates", value=False)
        target_epsg = st.number_input("Target EPSG Code (e.g., 3857)", min_value=1, value=4326, disabled=not enable_reprojection)

        st.header("3. Output Settings")
        output_format = st.selectbox(
            "Target Format",
            [
                "ESRI Shapefile (.zip)", 
                "GeoJSON", 
                "GeoPackage (.gpkg)", 
                "KML", 
                "GML", 
                "FlatGeobuf",
                "CSV (WKT)",
                "Excel (.xlsx)",
            ]
        )

    # 2. Main Processing Block
    if uploaded_file:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = save_uploaded_file(uploaded_file, tmp_dir)
            
            # --- Loading Logic ---
            try:
                gdf = None
                
                # A. Handling Zipped Shapefiles or regular Zips
                if file_path.endswith('.zip'):
                    extract_dir = os.path.join(tmp_dir, "extracted")
                    os.makedirs(extract_dir, exist_ok=True)
                    main_file = extract_zip(file_path, extract_dir)
                    if main_file:
                        gdf = gpd.read_file(main_file)
                        st.info(f"📂 Read inside zip: `{os.path.basename(main_file)}`")
                    else:
                        st.error("Could not find valid spatial data inside the ZIP.")
                
                # B. Handling Tabular Data (CSV/Excel) - RESTORED FEATURE
                elif file_path.endswith('.csv') or file_path.endswith('.xlsx'):
                    if file_path.endswith('.csv'):
                        df = pd.read_csv(file_path)
                    else:
                        df = pd.read_excel(file_path)
                    
                    st.write("### 🛠️ Tabular Data Configuration")
                    st.dataframe(df.head(3))
                    
                    col1, col2 = st.columns(2)
                    mode = col1.radio("Geometry Source", ["Lat/Lon Columns", "WKT Column"])
                    
                    if mode == "Lat/Lon Columns":
                        lon_col = col2.selectbox("Select Longitude (X)", df.columns, index=min(1, len(df.columns)-1))
                        lat_col = col2.selectbox("Select Latitude (Y)", df.columns, index=min(2, len(df.columns)-1))
                        if st.button("Create Geometry from XY"):
                            gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon_col], df[lat_col]), crs="EPSG:4326")
                    else:
                        wkt_col = col2.selectbox("Select WKT Column", df.columns)
                        if st.button("Parse WKT"):
                            try:
                                df['geometry'] = df[wkt_col].apply(wkt.loads)
                                gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
                            except Exception as e:
                                st.error(f"WKT Parse Error: {e}")

                # C. Handling Standard Vector Files
                else:
                    gdf = gpd.read_file(file_path)

                # --- Processing & Visualization ---
                if gdf is not None:
                    
                    # 1. Reprojection Logic
                    if enable_reprojection:
                        with st.spinner(f"Reprojecting to EPSG:{target_epsg}..."):
                            gdf = convert_crs(gdf, f"EPSG:{target_epsg}")
                            st.success(f"Reprojected to EPSG:{target_epsg}")

                    # 2. Metadata Display
                    st.divider()
                    col_info, col_map = st.columns([1, 2])
                    
                    with col_info:
                        st.subheader("📊 Metadata")
                        st.write(f"**CRS:** {gdf.crs}")
                        st.write(f"**Features:** {len(gdf)}")
                        st.write(f"**Geom:** {gdf.geom_type.unique()}")
                        with st.expander("View Attribute Table"):
                            st.dataframe(gdf.drop(columns='geometry').head(10))

                    with col_map:
                        st.subheader("🗺️ Preview")
                        try:
                            # Helper map_gdf to ensure we map in Lat/Lon
                            map_gdf = gdf.to_crs(epsg=4326) if gdf.crs else gdf
                            st.map(map_gdf)
                        except Exception as e:
                            st.warning("Could not render map preview.")

                    # ==========================================
                    # 📍 NEW FEATURE: SINGLE DISTRICT EXTRACTION
                    # ==========================================
                    
                    # Detect columns case-sensitively based on your request
                    has_district = 'District' in gdf.columns
                    has_state = 'STATE' in gdf.columns

                    if has_district and has_state:
                        st.write("---")
                        st.markdown("### 📍 District Extractor")
                        st.info("District boundary detected. Select a location to filter and download.")
                        
                        dc1, dc2, dc3 = st.columns(3)
                        
                        # 1. Select State
                        states_list = sorted(gdf['STATE'].astype(str).unique())
                        selected_state = dc1.selectbox("1. Select State", states_list)
                        
                        # 2. Select District (Filtered by State)
                        district_list = sorted(gdf[gdf['STATE'] == selected_state]['District'].astype(str).unique())
                        selected_district = dc2.selectbox("2. Select District", district_list)
                        
                        # 3. Download Button
                        with dc3:
                            st.write("3. Action")
                            if st.button(f"Extract & Download {selected_district}"):
                                # Create Subset
                                subset_gdf = gdf[
                                    (gdf['STATE'] == selected_state) & 
                                    (gdf['District'] == selected_district)
                                ]
                                
                                # Export Subset
                                f_buff, f_path, f_ext, f_mime = handle_export(
                                    subset_gdf, output_format, tmp_dir, file_prefix=f"{selected_district}_{selected_state}"
                                )
                                
                                # Show Download Button
                                if f_buff:
                                    st.download_button(
                                        label=f"📥 Download {selected_district}{f_ext}",
                                        data=f_buff,
                                        file_name=f"{selected_district}_{selected_state}{f_ext}",
                                        mime=f_mime
                                    )
                                elif f_path:
                                    with open(f_path, "rb") as f:
                                        st.download_button(
                                            label=f"📥 Download {selected_district}{f_ext}",
                                            data=f,
                                            file_name=f"{selected_district}_{selected_state}{f_ext}",
                                            mime=f_mime
                                        )
                    
                    # ==========================================
                    # 📤 GLOBAL DOWNLOAD (Standard Feature)
                    # ==========================================
                    st.write("---")
                    st.subheader("📥 Global Conversion Export")
                    if st.button(f"Convert Full Dataset to {output_format}"):
                        with st.spinner("Converting..."):
                            f_buff, f_path, f_ext, f_mime = handle_export(gdf, output_format, tmp_dir, file_prefix="converted_data")
                            
                            if f_buff:
                                st.download_button(
                                    label=f"Download Full {output_format}",
                                    data=f_buff,
                                    file_name=f"geoconvert_full{f_ext}",
                                    mime=f_mime
                                )
                            elif f_path:
                                with open(f_path, "rb") as f:
                                    st.download_button(
                                        label=f"Download Full {output_format}",
                                        data=f,
                                        file_name=f"geoconvert_full{f_ext}",
                                        mime=f_mime
                                    )
                            st.success("Conversion successful!")

            except Exception as e:
                st.error(f"Error loading file: {e}")

if __name__ == "__main__":
    main()
