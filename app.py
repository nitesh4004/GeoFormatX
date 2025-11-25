import streamlit as st
import os
import tempfile
import shutil
import zipfile
import glob
from datetime import datetime
import json

import geopandas as gpd
import pandas as pd
import rioxarray as rxr
import xarray as xr
from shapely.geometry import Point
import ee
import geemap.foliumap as geemap
from pyproj import CRS

# --- Configuration & State Management ---
st.set_page_config(
    page_title="GeoSpatial ETL Hub",
    layout="wide",
    page_icon="🌍"
)

if 'history' not in st.session_state:
    st.session_state['history'] = []

# --- Backend Processing Functions (The "Logic" Layer) ---

def save_uploaded_file(uploaded_file):
    """
    Persists uploaded bytes to a temporary directory.
    Handles unzipping for Shapefiles (which require .shp, .shx, .dbf).
    """
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, uploaded_file.name)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Handle Shapefile Zips
    if uploaded_file.name.lower().endswith(".zip"):
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Search for the .shp file recursively
        shp_files = [f for f in glob.glob(os.path.join(temp_dir, "**/*.shp"), recursive=True)]
        if shp_files:
            return shp_files[0] # Return the first shapefile found
        else:
            raise FileNotFoundError("No .shp file found in the uploaded zip.")
            
    return file_path

def process_vector(file_path, target_crs=None, output_format=None, lat_col=None, lon_col=None):
    """
    Loads, reprojects, and converts vector data using GeoPandas + Pyogrio.
    """
    # 1. Load Data
    if file_path.lower().endswith('.csv'):
        df = pd.read_csv(file_path)
        if lat_col and lon_col:
            gdf = gpd.GeoDataFrame(
                df, 
                geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
                crs="EPSG:4326"
            )
        else:
            return None, "CSV requires Lat/Lon selection."
    else:
        # Engine='pyogrio' is significantly faster for large datasets
        gdf = gpd.read_file(file_path, engine="pyogrio")

    # 2. Reproject
    if target_crs and gdf.crs:
        # Normalize CRS input (handle string vs EPSG int)
        try:
            target_crs_obj = CRS.from_user_input(target_crs)
            if gdf.crs != target_crs_obj:
                gdf = gdf.to_crs(target_crs_obj)
        except Exception as e:
            return None, f"CRS Error: {str(e)}"

    # 3. Export (if format requested)
    output_path = None
    mime_type = "application/octet-stream"
    
    if output_format:
        tmp_out_dir = tempfile.mkdtemp()
        
        # Driver mapping
        drivers = {
            'geojson': ('GeoJSON', '.geojson', 'application/json'),
            'gpkg': ('GPKG', '.gpkg', 'application/x-sqlite3'),
            'shp': ('ESRI Shapefile', '.shp', 'application/zip'),
            'dxf': ('DXF', '.dxf', 'application/dxf'),
        }
        
        driver, ext, mime = drivers.get(output_format, ('GeoJSON', '.geojson', 'application/json'))
        mime_type = mime
        
        out_name = f"export{ext}"
        out_full_path = os.path.join(tmp_out_dir, out_name)
        
        if output_format == 'shp':
            # Shapefiles are multi-file; write to folder then zip
            shp_dir = os.path.join(tmp_out_dir, "shapefile_export")
            os.makedirs(shp_dir, exist_ok=True)
            gdf.to_file(os.path.join(shp_dir, out_name), driver=driver)
            
            # Zip the directory
            shutil.make_archive(os.path.join(tmp_out_dir, "export"), 'zip', shp_dir)
            output_path = os.path.join(tmp_out_dir, "export.zip")
        else:
            gdf.to_file(out_full_path, driver=driver)
            output_path = out_full_path

    return gdf, output_path, mime_type

def process_raster(file_path, target_crs=None, output_format=None):
    """
    Loads, reprojects, and converts raster data using Rioxarray/Rasterio.
    """
    # 1. Load Raster (masked=True hides nodata values)
    xds = rxr.open_rasterio(file_path, masked=True)
    
    # 2. Reproject
    if target_crs:
        try:
            # Rioxarray handles the warping math
            xds = xds.rio.reproject(target_crs)
        except Exception as e:
            st.error(f"Reprojection Error: {e}")

    # 3. Export
    output_path = None
    mime_type = "image/tiff"
    
    if output_format:
        tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format}")
        output_path = tmp_out.name
        tmp_out.close()
        
        if output_format == 'tif':
            xds.rio.to_raster(output_path)
        elif output_format == 'png':
            # Simplified PNG export (visual only, loses georeference usually unless worldfile included)
            # For strict GIS use, we usually stick to GeoTIFF/COG
            xds.rio.to_raster(output_path, driver="PNG")
            mime_type = "image/png"
            
    return xds, output_path, mime_type

# --- UI Layout ---

def main():
    st.sidebar.title("🛠️ Geo-Toolbox")
    app_mode = st.sidebar.radio("Select Module", ["Vector Operations", "Raster Operations", "GEE Satellite Data"])

    st.markdown("## 🛰️ Geospatial Inspection & Conversion Hub")
    st.markdown("---")

    # --- VECTOR MODULE ---
    if app_mode == "Vector Operations":
        st.subheader("Vector ETL (Shapefile, GeoJSON, CSV, GPKG)")
        
        uploaded_file = st.file_uploader("Upload Vector File", type=['zip', 'geojson', 'gpkg', 'csv', 'kml'])
        
        if uploaded_file:
            with st.spinner("Uploading and analyzing..."):
                try:
                    local_path = save_uploaded_file(uploaded_file)
                    
                    # CSV Pre-check for Lat/Lon
                    lat_col, lon_col = None, None
                    if uploaded_file.name.endswith('.csv'):
                        df_preview = pd.read_csv(local_path, nrows=0) # Read header only
                        cols = df_preview.columns.tolist()
                        c1, c2 = st.columns(2)
                        lat_col = c1.selectbox("Latitude Column", cols)
                        lon_col = c2.selectbox("Longitude Column", cols)
                    
                    # Load Data
                    gdf, _, _ = process_vector(local_path, lat_col=lat_col, lon_col=lon_col)
                    
                    if gdf is not None:
                        # --- Layout: Inspection ---
                        c_info, c_map = st.columns([1, 2])
                        
                        with c_info:
                            st.markdown("### 📋 Metadata")
                            st.info(f"**CRS:** {gdf.crs}")
                            st.write(f"**Features:** {len(gdf)}")
                            st.write(f"**Geometry:** {gdf.geom_type.mode()[0] if not gdf.empty else 'N/A'}")
                            st.write("**Attribute Sample:**")
                            st.dataframe(gdf.drop(columns='geometry').head(3), hide_index=True)
                        
                        with c_map:
                            st.markdown("### 🗺️ Preview")
                            # Reproject for Web Map (Folium requires EPSG:4326)
                            m = geemap.Map()
                            
                            # Simplify geometry for performance if too large
                            map_gdf = gdf.to_crs("EPSG:4326")
                            if len(map_gdf) > 1000:
                                map_gdf = map_gdf.simplify(tolerance=0.001) # Approx 100m simplification
                                st.warning("Geometry simplified for web rendering.")
                                
                            m.add_data(map_gdf, layer_name="User Data")
                            m.centerObject(map_gdf)
                            m.to_streamlit(height=400)

                        # --- Layout: Transformation ---
                        st.markdown("### 🔄 Conversion & Reprojection")
                        col_crs, col_fmt, col_btn = st.columns([2, 1, 1])
                        
                        target_crs = col_crs.text_input("Target EPSG (e.g., EPSG:3857)", value="EPSG:4326")
                        out_format = col_fmt.selectbox("Format", ["geojson", "shp", "gpkg", "dxf"])
                        
                        if col_btn.button("Convert File"):
                            with st.spinner("Processing..."):
                                _, out_path, mime = process_vector(local_path, target_crs=target_crs, output_format=out_format, lat_col=lat_col, lon_col=lon_col)
                                
                                if out_path:
                                    with open(out_path, "rb") as f:
                                        st.download_button(
                                            "Download Converted File", 
                                            f, 
                                            file_name=f"processed_vector.{out_format.replace('shp','zip')}",
                                            mime=mime
                                        )
                                    st.success("Conversion successful.")
                                    
                except Exception as e:
                    st.error(f"Error processing file: {e}")


    # --- RASTER MODULE ---
    elif app_mode == "Raster Operations":
        st.subheader("Raster ETL (GeoTIFF, COG)")
        uploaded_raster = st.file_uploader("Upload GeoTIFF", type=['tif', 'tiff'])
        
        if uploaded_raster:
            local_path = save_uploaded_file(uploaded_raster)
            
            # Load
            xds, _, _ = process_raster(local_path)
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown("### 📋 Raster Metadata")
                st.write(f"**Dimensions:** {xds.rio.width} x {xds.rio.height}")
                st.write(f"**Bands:** {xds.rio.count}")
                st.write(f"**CRS:** {xds.rio.crs}")
                st.write(f"**Resolution:** {xds.rio.resolution()}")
                
            with c2:
                # Basic visualization of first band
                st.markdown("### 🖼️ Quick View (Band 1)")
                # Downsample for display speed
                xds_small = xds.isel(x=slice(0, None, 10), y=slice(0, None, 10))
                st.image(xds_small[0].values, caption="Band 1 (Resampled)", clamp=True, channels='GRAY')

            st.markdown("---")
            st.markdown("### 🔄 Reproject & Export")
            
            rc1, rc2, rc3 = st.columns([2, 1, 1])
            target_crs_r = rc1.text_input("Target CRS (EPSG)", "EPSG:3857")
            r_fmt = rc2.selectbox("Format", ["tif", "png"])
            
            if rc3.button("Process Raster"):
                _, out_p, r_mime = process_raster(local_path, target_crs=target_crs_r, output_format=r_fmt)
                if out_p:
                    with open(out_p, "rb") as f:
                        st.download_button("Download Raster", f, file_name=f"processed_raster.{r_fmt}", mime=r_mime)


    # --- GEE MODULE ---
    elif app_mode == "GEE Satellite Data":
        st.subheader("Google Earth Engine Export")
        
        # Authentication Check
        try:
            ee.Initialize()
        except Exception as e:
            st.error("GEE Authentication failed. Please run `earthengine authenticate` locally or set GOOGLE_APPLICATION_CREDENTIALS.")
            st.stop()
            
        st.markdown("Define Area of Interest (AoI) and Date Range for Sentinel-2 MSI data.")
        
        # Inputs
        c_date, c_loc = st.columns(2)
        start_date = c_date.date_input("Start Date", pd.to_datetime("2023-01-01"))
        end_date = c_date.date_input("End Date", pd.to_datetime("2023-01-30"))
        
        coords = c_loc.text_input("Lat, Lon (Center Point)", "28.6139, 77.2090") # Delhi default
        try:
            lat, lon = map(float, coords.split(','))
        except:
            lat, lon = 28.6139, 77.2090
            
        roi = ee.Geometry.Point([lon, lat]).buffer(5000) # 5km buffer
        
        # Generate Composite
        if st.button("Generate Sentinel-2 Composite"):
            with st.spinner("Querying Google Earth Engine..."):
                # S2_SR_HARMONIZED: Sentinel-2 Surface Reflectance
                # Filtering logic: Date -> Bounds -> Cloud Cover
                s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")\
                    .filterBounds(roi)\
                    .filterDate(str(start_date), str(end_date))\
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))\
                    .median()\
                    .clip(roi)
                
                # Visualization parameters (False Color Infrared: NIR, Red, Green)
                vis_params = {'min': 0, 'max': 3000, 'bands': ['B8', 'B4', 'B3']}
                
                # Render Map
                m = geemap.Map()
                m.centerObject(roi, 12)
                m.addLayer(s2, vis_params, "Sentinel-2 (NIR/Red/Green)")
                m.addLayer(roi, {'color': 'red'}, "AOI")
                
                # Store in session state for export
                st.session_state['gee_asset'] = s2
                st.session_state['gee_roi'] = roi
                
                m.to_streamlit(height=500)
                
        # Export Logic
        if 'gee_asset' in st.session_state:
            st.markdown("### Export Data")
            if st.button("Export Image to Drive"):
                # Note: This creates a task in the user's GEE account
                task = ee.batch.Export.image.toDrive(
                    image=st.session_state['gee_asset'],
                    description=f'S2_Export_{datetime.now().strftime("%Y%m%d")}',
                    folder='Streamlit_Exports',
                    region=st.session_state['gee_roi'],
                    scale=10, # Sentinel-2 10m resolution
                    crs='EPSG:4326',
                    maxPixels=1e9
                )
                task.start()
                st.success(f"Export Task Started! ID: {task.id}. Check your Code Editor/Task Manager.")

if __name__ == "__main__":
    main()