import streamlit as st
import geopandas as gpd
import pandas as pd
import fiona
import os
import tempfile
import gdown
import requests
from zipfile import ZipFile, BadZipFile
from io import BytesIO
import json
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
keys = ['main_gdf', 'secondary_gdf', 'calc_result_gdf', 'calc_result_name', 'river_gdf', 'postal_gdf', 'parliament_gdf']
for k in keys:
    if k not in st.session_state:
        st.session_state[k] = None

# --- 2. COMPACT & CLEAN STYLING (FIXED CLIPPING) ---
st.markdown("""
    <style>
    /* 1. FIX CLIPPING: Increase padding-top so text doesn't hide behind the top bar */
    .block-container {
        padding-top: 3.5rem !important; 
        padding-bottom: 1rem !important;
        max-width: 95% !important;
    }
    
    /* 2. SIDEBAR TITLE (Large & Colorful) */
    [data-testid="stSidebar"] h1 {
        font-size: 2.5rem !important; 
        font-weight: 800 !important;
        background: -webkit-linear-gradient(45deg, #0068C9, #00E5FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem !important;
        margin-top: 0.5rem !important;
        line-height: 1.2 !important;
    }

    /* 3. SECTION HEADERS */
    h2 {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        margin-top: 0rem !important; 
        margin-bottom: 0.5rem !important;
        border-bottom: 1px solid rgba(128,128,128,0.2);
        padding-bottom: 5px;
        line-height: 1.5 !important;
    }

    /* 4. METRIC CARDS (Compact) */
    div[data-testid="stMetric"] {
        background-color: var(--secondary-background-color); 
        padding: 10px 15px;
        border-radius: 6px;
        border-left: 4px solid #0068C9;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        color: var(--text-color);
    }
    
    /* 5. REDUCE VERTICAL GAPS */
    div[data-testid="column"] {
        gap: 0.5rem;
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
    file_path = os.path.join(temp_dir, "downloaded_data") 
    
    try:
        if is_gdrive:
            # Fixed: Removed the 'fuzzy' keyword argument which is unsupported in newer gdown versions
            gdown.download(url, file_path, quiet=True)
        else:
            response = requests.get(url, stream=True)
            if response.status_code != 200: return None
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        if is_zip(file_path):
            return extract_and_read_first(file_path, temp_dir)
        else:
            try:
                return gpd.read_file(file_path)
            except Exception:
                os.rename(file_path, file_path + ".geojson")
                return gpd.read_file(file_path + ".geojson")

    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def is_zip(file_path):
    try:
        with ZipFile(file_path, 'r') as zip_ref:
            return True
    except BadZipFile:
        return False

def extract_and_read_first(zip_path, temp_dir):
    try:
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith((".shp", ".geojson", ".kml", ".gpkg", ".json")):
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

def is_null_val(x):
    if x is None: return True
    if isinstance(x, float) and pd.isna(x): return True
    return False

def sanitize_gdf_for_display_and_export(gdf):
    """
    Sanitizes GeoDataFrame attributes so non-JSON-serializable objects 
    (e.g., pd.Timestamp, datetime, pd.Period, dicts, lists) are converted to 
    strings before Folium map rendering or format export.
    """
    if gdf is None or gdf.empty:
        return gdf
    
    gdf_clean = gdf.copy()
    for col in gdf_clean.columns:
        if col == 'geometry':
            continue
        
        # Numeric & boolean types are natively JSON serializable
        if pd.api.types.is_numeric_dtype(gdf_clean[col]) or pd.api.types.is_bool_dtype(gdf_clean[col]):
            continue
            
        gdf_clean[col] = gdf_clean[col].apply(
            lambda x: "" if is_null_val(x)
            else x if type(x) in (str, int, float, bool)
            else json.dumps(x) if isinstance(x, (dict, list, tuple, set))
            else x.isoformat() if hasattr(x, 'isoformat') and callable(x.isoformat)
            else str(x)
        )
            
    return gdf_clean

def render_map(gdf_list, height=550, show_geometries=False):
    """
    Renders interactive Folium map with RED OUTLINE ONLY (No Fill).
    """
    m = folium.Map(location=[20.5937, 78.9629], zoom_start=4, tiles=None)

    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
        attr='Google',
        name='Google Hybrid',
        overlay=False,
        control=True
    ).add_to(m)

    if show_geometries and gdf_list and gdf_list[0][0] is not None:
        try:
            first_gdf = gdf_list[0][0]
            if first_gdf.crs != "EPSG:4326":
                display_gdf = first_gdf.to_crs(epsg=4326)
            else:
                display_gdf = first_gdf
            
            bounds = display_gdf.total_bounds
            m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
            
            # Note: We are ignoring the 'color' passed in gdf_list to enforce Red Outline
            for gdf, name, _ in gdf_list:
                if gdf is not None and not gdf.empty:
                    if gdf.crs != "EPSG:4326": 
                        gdf_display = gdf.to_crs(epsg=4326)
                    else:
                        gdf_display = gdf
                    
                    # Sanitize non-JSON-serializable attributes (pd.Timestamp, etc.) for Folium map
                    gdf_display = sanitize_gdf_for_display_and_export(gdf_display)
                    
                    tooltip_cols = list(gdf_display.columns[:4]) if len(gdf_display.columns) > 0 else None
                    if tooltip_cols and 'geometry' in tooltip_cols:
                        tooltip_cols.remove('geometry')
                    
                    folium.GeoJson(
                        gdf_display,
                        name=name,
                        style_function=lambda x: {
                            'fillColor': 'transparent', # No fill color
                            'color': 'red',             # Red outline
                            'weight': 2,                # Outline thickness
                            'fillOpacity': 0            # Ensure transparency
                        },
                        tooltip=folium.GeoJsonTooltip(fields=tooltip_cols) if tooltip_cols else None
                    ).add_to(m)
        except Exception as e:
            st.error(f"Error rendering map: {e}")

    folium.LayerControl().add_to(m)
    return st_folium(m, height=height, use_container_width=True)

def handle_export(gdf, output_format, file_prefix="export", name_col=None, desc_col=None):
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
                export_gdf = gdf.copy()
                
                # KML strictly requires EPSG:4326 (WGS84)
                if export_gdf.crs is None:
                    export_gdf.set_crs(epsg=4326, inplace=True)
                elif str(export_gdf.crs).upper() != "EPSG:4326":
                    try:
                        export_gdf = export_gdf.to_crs(epsg=4326)
                    except Exception:
                        pass

                # Assign Name & Description fields if provided
                if name_col and name_col in export_gdf.columns and name_col != "Name":
                    export_gdf["Name"] = export_gdf[name_col].astype(str)
                if desc_col and desc_col in export_gdf.columns and desc_col != "Description":
                    export_gdf["Description"] = export_gdf[desc_col].astype(str)

                # Clean non-primitive columns (Timestamps, dates, objects) to prevent GDAL/Fiona XML serialization crashes
                export_gdf = sanitize_gdf_for_display_and_export(export_gdf)

                try:
                    export_gdf.to_file(path, driver="KML")
                except Exception:
                    try:
                        export_gdf.to_file(path, driver="LIBKML")
                    except Exception:
                        export_gdf.to_file(path, driver="KML", engine="fiona")

                with open(path, "rb") as f: final_data = BytesIO(f.read())
                file_ext, mime_type = ".kml", "application/vnd.google-earth.kml+xml"
            elif "GeoPackage" in output_format:
                path = os.path.join(out_dir, f"{file_prefix}.gpkg")
                gdf.to_file(path, driver="GPKG")
                with open(path, "rb") as f: final_data = BytesIO(f.read())
                file_ext, mime_type = ".gpkg", "application/x-sqlite3"
            elif "WKT" in output_format:
                path = os.path.join(out_dir, f"{file_prefix}.csv")
                gdf.to_csv(path, index=False)
                with open(path, "rb") as f: final_data = BytesIO(f.read())
                file_ext, mime_type = ".csv", "text/csv"

            return final_data, file_ext, mime_type
        except Exception as e:
            st.error(f"Export failed: {str(e)}")
            return None, None, None

# --- 5. MAIN APP ---

def main():
    # --- NAVIGATION SIDEBAR ---
    with st.sidebar:
        st.image("https://github.com/nitesh4004/GeoFormatX/raw/main/docs/logo.png", use_container_width=True)
        st.caption("Devoloped by Nitesh Kumar")
        
        selected = option_menu(
            menu_title=None,
            options=["Admin Data", "Postal Codes", "Parliament Boundaries", "Rivers", "GT Conversion", "GeoJSON to KML", "Converter", "Vector Calculator"],
            icons=["building", "mailbox", "bank", "water", "patch-check", "file-earmark-code", "arrow-repeat", "calculator"],
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
        st.info("💡 Map set to Google Hybrid.")

    # --- 1. ADMIN DOWNLOADER MODULE ---
    if selected == "Admin Data":
        st.markdown("## 🏛️ Administrative Boundaries") 
        
        col_ctrl, col_map = st.columns([1, 2.5], gap="medium")
        
        with col_ctrl:
            with st.container(border=True):
                st.subheader("1. Select Source")
                source_type = st.selectbox("Granularity", ["Districts", "Subdistricts", "Villages", "States"])
                
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

            if st.session_state['main_gdf'] is not None:
                gdf = st.session_state['main_gdf']
                with st.container(border=True):
                    st.subheader("2. Filter Region")
                    
                    final_selection = gdf
                    parent_level_selection = gdf 
                    
                    filename = "export"
                    is_specific_village_selected = False
                    
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
                                        
                                        parent_level_selection = final_selection

                                        if 'Village' in gdf.columns:
                                            vills = sorted(final_selection['Village'].astype(str).unique())
                                            sel_vill = st.selectbox("Village", ["All"] + vills)
                                            if sel_vill != "All":
                                                final_selection = final_selection[final_selection['Village'] == sel_vill]
                                                filename = f"{sel_vill}_{sel_sub}"
                                                is_specific_village_selected = True

                    st.markdown(f"**Selected Features:** `{len(final_selection)}`")
                    
                    st.subheader("3. Export")
                    
                    export_gdf = final_selection
                    export_filename = filename

                    if is_specific_village_selected:
                        st.markdown("Download Options:")
                        download_scope = st.radio(
                            "Select Data Range:", 
                            ["Selected Village Only", "Entire Subdistrict"],
                            index=0
                        )
                        if download_scope == "Entire Subdistrict":
                            export_gdf = parent_level_selection
                            export_filename = f"{sel_sub}_Entire_Subdistrict"
                            st.caption(f"Will download all {len(export_gdf)} villages in {sel_sub}.")

                    fmt = st.selectbox("Format", ["ESRI Shapefile (.zip)", "GeoJSON", "KML", "GeoPackage", "WKT (CSV)"])
                    if st.button("Download Selection", use_container_width=True):
                        d, e, m = handle_export(export_gdf, fmt, export_filename)
                        if d: st.download_button("Save File", d, f"{export_filename}{e}", m, use_container_width=True)
                        
        with col_map:
            current_data = locals().get('final_selection', st.session_state['main_gdf'])
            
            st.markdown("### Map View")
            col_toggle, col_dummy = st.columns([1, 2])
            show_map = col_toggle.toggle("Show Geometry on Map", value=False, help="Enable this to render geometries.")
            
            render_map([(current_data, "Admin Boundary", "#3388ff")], height=550, show_geometries=show_map)
            
            if current_data is not None:
                with st.expander("📊 View Attribute Table"):
                    st.dataframe(current_data.drop(columns='geometry'), use_container_width=True)

    # --- 2. POSTAL CODES MODULE (DIRECT SEARCH ONLY) ---
    elif selected == "Postal Codes":
        st.markdown("## 📮 Postal Code Boundaries")
        
        col_ctrl, col_map = st.columns([1, 2.5], gap="medium")
        
        with col_ctrl:
            with st.container(border=True):
                st.subheader("1. Data Source")
                postal_id = "1RpFUgIGi_KGCYiCnk2X5BMHs4ZeV-OLg"
                
                if st.session_state['postal_gdf'] is None:
                    if st.button("Load Postal Boundaries", type="primary", use_container_width=True):
                        with st.spinner("Downloading Postal Data..."):
                            gdf = load_file_from_url(f"https://drive.google.com/uc?id={postal_id}", is_gdrive=True)
                            if gdf is not None:
                                st.session_state['postal_gdf'] = gdf
                                st.toast("Postal Data Loaded!", icon="📮")
                            else:
                                st.error("Failed to load Postal Data.")
                else:
                    st.success("Postal Data Loaded.")
                    if st.button("Reload Data"):
                        st.session_state['postal_gdf'] = None
                        st.rerun()

            if st.session_state['postal_gdf'] is not None:
                pgdf = st.session_state['postal_gdf']
                filtered_pgdf = pgdf
                
                sel_pin = "All"
                
                with st.container(border=True):
                    st.subheader("2. Filter Location")
                    
                    all_pincodes = sorted(pgdf['Pincode'].dropna().astype(str).unique())
                    sel_pin = st.selectbox("Search Pincode", ["All"] + all_pincodes)
                    
                    if sel_pin != "All":
                        filtered_pgdf = filtered_pgdf[filtered_pgdf['Pincode'].astype(str) == str(sel_pin)]

                    st.markdown(f"**Found:** `{len(filtered_pgdf)}` postal boundaries")

                    st.divider()
                    st.subheader("3. Download")
                    fmt = st.selectbox("Format", ["ESRI Shapefile (.zip)", "GeoJSON", "KML", "GeoPackage", "WKT (CSV)"], key="postal_fmt")
                    
                    fname = "Postal_Export"
                    if sel_pin != "All":
                        fname = f"Pincode_{sel_pin}"
                    
                    if st.button("Download Data", use_container_width=True):
                        d, e, m = handle_export(filtered_pgdf, fmt, fname)
                        if d: st.download_button("Save File", d, f"{fname}{e}", m, use_container_width=True)

        with col_map:
            current_postal = locals().get('filtered_pgdf', st.session_state['postal_gdf'])
            st.markdown("### Map View")
            show_postal_map = st.toggle("Show Geometry on Map", value=True)
            render_map([(current_postal, "Postal Boundaries", "#FF5733")], height=550, show_geometries=show_postal_map)
            
            if current_postal is not None:
                with st.expander("📊 View Attribute Table"):
                    st.dataframe(current_postal.drop(columns='geometry', errors='ignore'), use_container_width=True)

    # --- 3. PARLIAMENT BOUNDARIES MODULE (NEW) ---
    elif selected == "Parliament Boundaries":
        st.markdown("## 🏛️ Parliament Boundaries (Lok Sabha)")
        
        col_ctrl, col_map = st.columns([1, 2.5], gap="medium")
        
        with col_ctrl:
            with st.container(border=True):
                st.subheader("1. Data Source")
                parl_id = "1gNT2PIVMP2nxK_9CKmwzPp__TBDlozXs"
                
                if st.session_state['parliament_gdf'] is None:
                    if st.button("Load Parliament Data", type="primary", use_container_width=True):
                        with st.spinner("Downloading Parliament Boundaries..."):
                            gdf = load_file_from_url(f"https://drive.google.com/uc?id={parl_id}", is_gdrive=True)
                            if gdf is not None:
                                st.session_state['parliament_gdf'] = gdf
                                st.toast("Parliament Data Loaded!", icon="🏛️")
                            else:
                                st.error("Failed to load Data.")
                else:
                    st.success("Parliament Data Loaded.")
                    if st.button("Reload Data", key="reload_parl"):
                        st.session_state['parliament_gdf'] = None
                        st.rerun()

            if st.session_state['parliament_gdf'] is not None:
                df = st.session_state['parliament_gdf']
                filtered_df = df
                
                sel_state = "All"
                sel_pc = "All"
                sel_code = "All"
                sel_res = "All"
                
                with st.container(border=True):
                    st.subheader("2. Filter Constituency")
                    
                    states = sorted(df['ST_NAME'].dropna().astype(str).unique())
                    sel_state = st.selectbox("Select State (ST_NAME)", ["All"] + states)
                    
                    if sel_state != "All":
                        filtered_df = filtered_df[filtered_df['ST_NAME'] == sel_state]
                    
                    res_types = sorted(filtered_df['Res'].dropna().astype(str).unique())
                    sel_res = st.selectbox("Reservation Status", ["All"] + res_types)
                    
                    if sel_res != "All":
                        filtered_df = filtered_df[filtered_df['Res'] == sel_res]

                    pc_names = sorted(filtered_df['PC_NAME'].dropna().astype(str).unique())
                    sel_pc = st.selectbox("Select Constituency (PC_NAME)", ["All"] + pc_names)
                    
                    if sel_pc != "All":
                        filtered_df = filtered_df[filtered_df['PC_NAME'] == sel_pc]
                        
                    pc_codes = sorted(filtered_df['PC_CODE'].dropna().astype(str).unique())
                    sel_code = st.selectbox("Select PC Code", ["All"] + pc_codes)
                    
                    if sel_code != "All":
                        filtered_df = filtered_df[filtered_df['PC_CODE'].astype(str) == str(sel_code)]
                        
                    st.markdown(f"**Found:** `{len(filtered_df)}` constituencies")
                    
                    st.divider()
                    st.subheader("3. Download")
                    fmt = st.selectbox("Format", ["ESRI Shapefile (.zip)", "GeoJSON", "KML", "GeoPackage", "WKT (CSV)"], key="parl_fmt")
                    
                    fname = "Parliament_Export"
                    if sel_pc != "All": fname = f"{sel_pc}_Constituency"
                    elif sel_state != "All": fname = f"{sel_state}_Parliament_Boundaries"
                    
                    if st.button("Download Data", key="dl_parl", use_container_width=True):
                        d, e, m = handle_export(filtered_df, fmt, fname)
                        if d: st.download_button("Save File", d, f"{fname}{e}", m, use_container_width=True)

        with col_map:
            current_parl = locals().get('filtered_df', st.session_state['parliament_gdf'])
            st.markdown("### Map View")
            show_parl_map = st.toggle("Show Geometry on Map", value=True, key="parl_map_toggle")
            render_map([(current_parl, "Parliament Boundaries", "#9b59b6")], height=550, show_geometries=show_parl_map)
            
            if current_parl is not None:
                with st.expander("📊 View Attribute Table"):
                    st.dataframe(current_parl.drop(columns='geometry', errors='ignore'), use_container_width=True)

    # --- 4. RIVER DOWNLOADER MODULE ---
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
                    
                    l = float(selected_river['shape_Leng'].sum())
                    st.metric("Total Length", f"{l:.2f}", delta="Map Units")
                    st.metric("Segments", len(selected_river))
                    
                    st.divider()
                    st.subheader("Download")
                    fmt = st.selectbox("Format", ["ESRI Shapefile (.zip)", "GeoJSON", "KML", "GeoPackage", "WKT (CSV)"])
                    if st.button("Download River Data", use_container_width=True):
                        fname = f"{sel_river}_{sel_basin}".replace(" ","_")
                        d, e, m = handle_export(selected_river, fmt, fname)
                        if d: st.download_button("Save File", d, f"{fname}{e}", m, use_container_width=True)
                else:
                    st.info("Click 'Load River Database' to begin.")
        
def render_gt_conversion_module():
    st.markdown("## 🌾 GT App Export Converter (GeoJSON + CSV ➔ KML & CSV)")
    st.caption("Specialized converter for Ground Truth app exports (`fields_export_...` containing `fields.geojson` and `fields.csv`). Merges boundaries with survey responses, orders features sequentially by FIELD ID, and exports formatted KML & clean CSV.")
    
    merged_gdf = None
    csv_df = None
    
    col_input, col_preset = st.columns([2, 1])
    with col_input:
        input_mode = st.radio("Upload Method", ["Upload Zip Export Package", "Upload GeoJSON & CSV Separately"], horizontal=True, key="gt_input_mode")
        
        if input_mode == "Upload Zip Export Package":
            zip_file = st.file_uploader("Upload App Export Zip (`fields_export_...zip`)", type=['zip'], key="gt_zip_uploader")
            if zip_file:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    zpath = os.path.join(tmp_dir, zip_file.name)
                    with open(zpath, "wb") as f: f.write(zip_file.getbuffer())
                    with ZipFile(zpath, 'r') as zip_ref:
                        zip_ref.extractall(tmp_dir)
                    
                    g_file, c_file = None, None
                    for root, dirs, files in os.walk(tmp_dir):
                        for file in files:
                            if file.endswith('.geojson') or (file.endswith('.json') and 'field' in file.lower()):
                                g_file = os.path.join(root, file)
                            elif file.endswith('.csv') and 'field' in file.lower():
                                c_file = os.path.join(root, file)
                    
                    if g_file:
                        gt_raw = gpd.read_file(g_file)
                        gt_csv = pd.read_csv(c_file) if c_file else None
                        if gt_csv is not None and 'Field ID' in gt_csv.columns and 'field_id' in gt_raw.columns:
                            merged_gdf = gt_raw.merge(gt_csv, left_on='field_id', right_on='Field ID', how='left', suffixes=('', '_csv'))
                            csv_df = gt_csv
                        else:
                            merged_gdf = gt_raw
                            csv_df = gt_csv
        else:
            c1, c2 = st.columns(2)
            up_g = c1.file_uploader("Upload fields.geojson", type=['geojson', 'json'], key="gt_g_up")
            up_c = c2.file_uploader("Upload fields.csv", type=['csv'], key="gt_c_up")
            if up_g:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    gpath = os.path.join(tmp_dir, up_g.name)
                    with open(gpath, "wb") as f: f.write(up_g.getbuffer())
                    gt_raw = gpd.read_file(gpath)
                    gt_csv = None
                    if up_c:
                        cpath = os.path.join(tmp_dir, up_c.name)
                        with open(cpath, "wb") as f: f.write(up_c.getbuffer())
                        gt_csv = pd.read_csv(cpath)
                    
                    if gt_csv is not None and 'Field ID' in gt_csv.columns and 'field_id' in gt_raw.columns:
                        merged_gdf = gt_raw.merge(gt_csv, left_on='field_id', right_on='Field ID', how='left', suffixes=('', '_csv'))
                        csv_df = gt_csv
                    else:
                        merged_gdf = gt_raw
                        csv_df = gt_csv

    with col_preset:
        st.write("")
        st.write("")
        downloads_export_dir = os.path.join("C:", os.sep, "Users", "nites", "Downloads", "fields_export_2026-08-05")
        if os.path.exists(downloads_export_dir):
            if st.button("📁 Quick Load local `fields_export_2026-08-05`", type="primary", use_container_width=True):
                try:
                    g_path = os.path.join(downloads_export_dir, "fields.geojson")
                    c_path = os.path.join(downloads_export_dir, "fields.csv")
                    gt_raw = gpd.read_file(g_path)
                    gt_csv = pd.read_csv(c_path)
                    merged_gdf = gt_raw.merge(gt_csv, left_on='field_id', right_on='Field ID', how='left', suffixes=('', '_csv'))
                    csv_df = gt_csv
                    st.toast("Loaded fields_export_2026-08-05 (GeoJSON + CSV)!", icon="🎉")
                except Exception as ex:
                    st.error(f"Failed to load export package: {ex}")

    if merged_gdf is not None and not merged_gdf.empty:
        col_ctrl, col_map = st.columns([1, 2], gap="medium")
        
        with col_ctrl:
            with st.container(border=True):
                st.subheader("1. Export Package Summary")
                st.success(f"Total Fields: `{len(merged_gdf)}` | CRS: `{merged_gdf.crs or 'EPSG:4326'}`")
                
                st.subheader("2. KML Ordering & Placemark Naming")
                
                sort_by = st.selectbox(
                    "Sort Order (KML & CSV)",
                    ["FIELD ID (field_id A-Z)", "Farmer Name A-Z", "Village A-Z", "Keep Original Order"],
                    index=0,
                    key="gt_app_sort"
                )
                
                name_fmt = st.selectbox(
                    "Placemark Title Format",
                    [
                        "FIELD ID - Farmer Name (e.g. FLD-Zrrxxg1C - Prakash)",
                        "FIELD ID Only (e.g. FLD-Zrrxxg1C)",
                        "FIELD ID - Current Crop",
                        "FIELD ID (Village)"
                    ],
                    index=0,
                    key="gt_app_name_fmt"
                )
                
                out_base_name = st.text_input("Output File Name Base", value="fields_export_formatted", key="gt_app_outname")
                
                st.divider()
                st.subheader("3. Convert & Export")
                
                # Perform processing
                proc_gdf = merged_gdf.copy()
                
                # Sort order
                if "FIELD ID" in sort_by:
                    sort_col = 'field_id' if 'field_id' in proc_gdf.columns else ('Field ID' if 'Field ID' in proc_gdf.columns else None)
                    if sort_col: proc_gdf = proc_gdf.sort_values(by=sort_col).reset_index(drop=True)
                elif "Farmer Name" in sort_by:
                    sort_col = 'Farmer name' if 'Farmer name' in proc_gdf.columns else ('farmer_name' if 'farmer_name' in proc_gdf.columns else None)
                    if sort_col: proc_gdf = proc_gdf.sort_values(by=sort_col).reset_index(drop=True)
                elif "Village" in sort_by:
                    sort_col = 'Village' if 'Village' in proc_gdf.columns else ('village' if 'village' in proc_gdf.columns else None)
                    if sort_col: proc_gdf = proc_gdf.sort_values(by=sort_col).reset_index(drop=True)
                    
                names = []
                descriptions = []
                
                for idx, r in proc_gdf.iterrows():
                    fid = str(r.get('field_id', r.get('Field ID', f'FLD-{idx+1}')))
                    farmer = str(r.get('Farmer name', r.get('farmer_name', '')))
                    if farmer == 'nan': farmer = ''
                    crop = str(r.get('Current crop', r.get('crop', '')))
                    if crop == 'nan': crop = ''
                    village = str(r.get('Village', r.get('village', '')))
                    if village == 'nan': village = ''
                    
                    if "FIELD ID - Farmer Name" in name_fmt:
                        p_name = f"{fid} - {farmer}" if farmer else fid
                    elif "FIELD ID Only" in name_fmt:
                        p_name = fid
                    elif "FIELD ID - Current Crop" in name_fmt:
                        p_name = f"{fid} - {crop}" if crop else fid
                    elif "FIELD ID (Village)" in name_fmt:
                        p_name = f"{fid} ({village})" if village else fid
                    else:
                        p_name = fid
                    names.append(p_name)
                    
                    # HTML Popup Card
                    html_rows = []
                    html_rows.append(f"<tr><th style='background:#0068C9; color:white; padding:6px; text-align:left;'>FIELD ID</th><td style='padding:6px;'><b>{fid}</b></td></tr>")
                    if farmer:
                        html_rows.append(f"<tr><th style='background:#f8f9fa; padding:5px; text-align:left;'>Farmer Name</th><td style='padding:5px;'><b>{farmer}</b></td></tr>")
                    if crop:
                        html_rows.append(f"<tr><th style='background:#f8f9fa; padding:5px; text-align:left;'>Current Crop</th><td style='padding:5px;'><b>{crop}</b></td></tr>")
                    if village:
                        html_rows.append(f"<tr><th style='background:#f8f9fa; padding:5px; text-align:left;'>Village</th><td style='padding:5px;'>{village}</td></tr>")
                        
                    sqm = r.get('total_area_sqmt', None)
                    if pd.notna(sqm):
                        try:
                            sqm_v = float(sqm)
                            acres_v = sqm_v / 4046.85642
                            html_rows.append(f"<tr><th style='background:#f8f9fa; padding:5px; text-align:left;'>Total Area</th><td style='padding:5px;'>{sqm_v:,.1f} sq.m ({acres_v:.2f} acres)</td></tr>")
                        except: pass
                        
                    for label, col_key in [
                        ("Phone Number", "Contact number"), ("Crop Variety", "Crop variety"),
                        ("Crop Stage", "Crop growth stage"), ("Crop Health", "Crop health / condition"),
                        ("Sowing Date", "Sowing / transplanting date / Plantation date"),
                        ("Expected Harvest Date", "Expected Harvest Date"), ("Soil Type", "Soil Type"),
                        ("Irrigation Type", "Irrigation type"), ("Irrigation Source", "Irrigation Source"),
                        ("Previous Season Crop", "Previous season crop"), ("Previous Season Yield", "Previous season yield"),
                        ("Yield Unit", "Yield unit"), ("Survey Date", "Survey date"),
                        ("Officer / Surveyor", "User Name"), ("Remarks", "Remarks")
                    ]:
                        val = r.get(col_key, '')
                        if pd.notna(val) and str(val).strip() != '' and str(val) != 'nan':
                            html_rows.append(f"<tr><th style='background:#f8f9fa; padding:5px; text-align:left;'>{label}</th><td style='padding:5px;'>{val}</td></tr>")
                            
                    desc_card = "<table border='1' style='border-collapse:collapse; width:100%; font-family:Arial,sans-serif; font-size:12px;'>" + "".join(html_rows) + "</table>"
                    descriptions.append(desc_card)
                    
                proc_gdf['Name'] = names
                proc_gdf['Description'] = descriptions
                
                # Create KML data
                kml_export_gdf = proc_gdf[['Name', 'Description', 'geometry']]
                d_kml, e_kml, m_kml = handle_export(kml_export_gdf, "KML", out_base_name, name_col='Name', desc_col='Description')
                
                # Create CSV data
                csv_export_df = csv_df.copy() if csv_df is not None else proc_gdf.drop(columns=['geometry', 'Name', 'Description'], errors='ignore')
                if 'Field ID' in csv_export_df.columns:
                    csv_export_df = csv_export_df.sort_values(by='Field ID').reset_index(drop=True)
                elif 'field_id' in csv_export_df.columns:
                    csv_export_df = csv_export_df.sort_values(by='field_id').reset_index(drop=True)
                    
                if 'geometry' in proc_gdf.columns and not proc_gdf.empty:
                    try:
                        area_series = proc_gdf['total_area_sqmt'] if 'total_area_sqmt' in proc_gdf.columns else proc_gdf.area
                        csv_export_df['total_area_acres'] = (area_series.astype(float) / 4046.85642).round(2)
                        csv_export_df['centroid_lat'] = proc_gdf.geometry.centroid.y.round(6)
                        csv_export_df['centroid_lon'] = proc_gdf.geometry.centroid.x.round(6)
                    except: pass
                    
                csv_bytes = csv_export_df.to_csv(index=False).encode('utf-8')
                
                # Buttons
                c_dl1, c_dl2 = st.columns(2)
                if d_kml:
                    c_dl1.download_button(
                        label="📥 Download Formatted KML (.kml)",
                        data=d_kml,
                        file_name=f"{out_base_name}{e_kml}",
                        mime=m_kml,
                        use_container_width=True,
                        type="primary",
                        key="gt_app_kml_dl"
                    )
                c_dl2.download_button(
                    label="📊 Download Formatted CSV (.csv)",
                    data=csv_bytes,
                    file_name=f"{out_base_name}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="gt_app_csv_dl"
                )

        with col_map:
            st.markdown("### GT Map Preview")
            show_gt_map = st.toggle("Show Geometry on Map", value=True, key="gt_app_map_toggle")
            
            disp_gdf = proc_gdf if 'proc_gdf' in locals() else merged_gdf
            disp_gdf = sanitize_gdf_for_display_and_export(disp_gdf)
            render_map([(disp_gdf, "GT Fields", "#00E5FF")], height=520, show_geometries=show_gt_map)
            
            with st.expander("📊 View Merged Attribute Table"):
                st.dataframe(disp_gdf.drop(columns='geometry', errors='ignore'), use_container_width=True)

def render_geojson_to_kml_module():
    st.markdown("## 🌐 GeoJSON to KML Converter")
    st.caption("Quickly convert GeoJSON / JSON files or raw GeoJSON code to Google Earth KML (.kml) format.")
    
    g2k_gdf = None
    input_source = st.radio("Input Source", ["Upload GeoJSON / JSON File", "Paste GeoJSON Code"], horizontal=True, key="g2k_source")
    
    if input_source == "Upload GeoJSON / JSON File":
        geojson_file = st.file_uploader("Upload .geojson or .json file", type=['geojson', 'json', 'zip'], key="g2k_file")
        if geojson_file:
            with tempfile.TemporaryDirectory() as tmp_dir:
                file_path = os.path.join(tmp_dir, geojson_file.name)
                with open(file_path, "wb") as f:
                    f.write(geojson_file.getbuffer())
                try:
                    if file_path.endswith('.zip'):
                        g2k_gdf = extract_and_read_first(file_path, tmp_dir)
                    else:
                        g2k_gdf = gpd.read_file(file_path)
                except Exception as ex:
                    st.error(f"Failed to read GeoJSON file: {ex}")
    else:
        raw_json = st.text_area("Paste GeoJSON text content below:", height=180, placeholder='{"type": "FeatureCollection", "features": [...]}', key="g2k_text")
        if raw_json.strip():
            try:
                g2k_gdf = gpd.read_file(raw_json)
            except Exception as ex:
                st.error(f"Failed to parse GeoJSON text: {ex}")

    if g2k_gdf is not None and not g2k_gdf.empty:
        g2k_gdf = sanitize_gdf_for_display_and_export(g2k_gdf)
        col_ctrl, col_map = st.columns([1, 2], gap="medium")
        
        with col_ctrl:
            with st.container(border=True):
                st.subheader("1. GeoJSON Summary")
                st.success(f"Features: `{len(g2k_gdf)}` | CRS: `{g2k_gdf.crs or 'EPSG:4326 (Assumed)'}`")
                geom_types = ", ".join(list(g2k_gdf.geometry.type.unique()))
                st.caption(f"Geometry Types: {geom_types}")
                
                st.subheader("2. KML Placemark Options")
                non_geom_cols = ["None"] + list(g2k_gdf.columns.drop('geometry', errors='ignore'))
                
                default_name = "None"
                for candidate in ["name", "Name", "NAME", "title", "Title"]:
                    if candidate in g2k_gdf.columns:
                        default_name = candidate
                        break
                
                sel_name_col = st.selectbox("Placemark Name Field", non_geom_cols, index=non_geom_cols.index(default_name) if default_name in non_geom_cols else 0, key="g2k_name_col")
                
                default_desc = "None"
                for candidate in ["description", "Description", "DESC", "desc", "summary"]:
                    if candidate in g2k_gdf.columns:
                        default_desc = candidate
                        break
                
                sel_desc_col = st.selectbox("Placemark Description Field", non_geom_cols, index=non_geom_cols.index(default_desc) if default_desc in non_geom_cols else 0, key="g2k_desc_col")
                
                out_prefix = st.text_input("Output File Name", value="converted_from_geojson", key="g2k_prefix")
                
                st.divider()
                if st.button("🚀 Convert to KML", type="primary", use_container_width=True, key="g2k_btn"):
                    name_param = None if sel_name_col == "None" else sel_name_col
                    desc_param = None if sel_desc_col == "None" else sel_desc_col
                    d, e, m = handle_export(g2k_gdf, "KML", out_prefix, name_col=name_param, desc_col=desc_param)
                    if d:
                        st.toast("GeoJSON to KML conversion successful!", icon="🎉")
                        st.download_button(
                            label="📥 Download KML File",
                            data=d,
                            file_name=f"{out_prefix}{e}",
                            mime=m,
                            use_container_width=True,
                            type="primary",
                            key="g2k_dl"
                        )
        
        with col_map:
            st.markdown("### Map Preview")
            show_g2k_map = st.toggle("Show Geometry on Map", value=True, key="g2k_map_toggle")
            render_map([(g2k_gdf, "GeoJSON Features", "#FF5733")], height=520, show_geometries=show_g2k_map)
            
            with st.expander("📊 View GeoJSON Attribute Table"):
                st.dataframe(g2k_gdf.drop(columns='geometry', errors='ignore'), use_container_width=True)

# --- 5. MAIN APP ---
def main():
    # --- NAVIGATION SIDEBAR ---
    with st.sidebar:
        st.image("https://github.com/nitesh4004/GeoFormatX/raw/main/docs/logo.png", use_container_width=True)
        st.caption("Devoloped by Nitesh Kumar")
        
        selected = option_menu(
            menu_title=None,
            options=["Admin Data", "Postal Codes", "Parliament Boundaries", "Rivers", "GeoJSON to KML", "Converter", "Vector Calculator"],
            icons=["building", "mailbox", "bank", "water", "file-earmark-code", "arrow-repeat", "calculator"],
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
        st.info("💡 Map set to Google Hybrid.")

    # --- 1. ADMIN DOWNLOADER MODULE ---
    if selected == "Admin Data":
        st.markdown("## 🏛️ Administrative Boundaries") 
        # ...
    elif selected == "Postal Codes":
        pass # preserved below

    # --- 5. GT CONVERSION MODULE ---
    elif selected == "GT Conversion":
        render_gt_conversion_module()

    # --- 6. GEOJSON TO KML MODULE ---
    elif selected == "GeoJSON to KML":
        render_geojson_to_kml_module()

    # --- 6. FORMAT CONVERTER MODULE ---
    elif selected == "Converter":
        st.markdown("## 🔄 Geospatial Format Converter")
        
        tab_g2k, tab_univ = st.tabs(["🌐 GeoJSON ➔ KML Converter", "🔄 Universal Format Converter"])
        
        with tab_g2k:
            render_geojson_to_kml_module()

        with tab_univ:
            st.markdown("### 🔄 Universal Geospatial Converter")
            with st.container(border=True):
                uploaded_file = st.file_uploader("Upload File (Zip, SHP, GeoJSON, JSON, KML, GPKG, CSV, XLSX)", type=['zip', 'shp', 'geojson', 'json', 'kml', 'gpkg', 'csv', 'xlsx'], key="univ_uploader")
            
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
                        target_fmt = st.selectbox("Output Format", ["GeoJSON", "ESRI Shapefile (.zip)", "KML", "GeoPackage", "WKT (CSV)"])
                        
                        if st.button("Convert & Download", type="primary", use_container_width=True):
                            d, e, m = handle_export(gdf, target_fmt, "converted_data")
                            if d: st.download_button("Download Result", d, f"converted{e}", m, use_container_width=True)
                
                with col_map:
                    show_conv_map = st.toggle("Show Geometry on Map", value=True, key="univ_map_toggle")
                    render_map([(gdf, "Converted Data", "#FF4B4B")], height=550, show_geometries=show_conv_map)

    # --- 6. VECTOR CALCULATOR MODULE ---
    elif selected == "Vector Calculator":
        st.markdown("## 🧮 Vector Operations")
        
        col_ctrl, col_map = st.columns([1.2, 2.5], gap="large")
        
        with col_ctrl:
            with st.expander("📂 1. Data Layers (Input)", expanded=True):
                f1 = st.file_uploader("Layer A (Primary)", type=['zip', 'geojson', 'json', 'kml', 'gpkg'], key="f1")
                f2 = st.file_uploader("Layer B (Overlay/Secondary)", type=['zip', 'geojson', 'json', 'kml', 'gpkg'], key="f2")
                
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

            with st.expander("🛠️ 2. Operations", expanded=True):
                category = st.selectbox("Category", ["Geoprocessing", "Geometry", "Analysis", "Overlay Operations", "Data Management"])
                
                tool_options = []
                if category == "Geoprocessing": tool_options = ["Buffer", "Convex Hull", "Dissolve"]
                elif category == "Geometry": tool_options = ["Centroids", "Simplify", "Explode", "Fix Geometries"]
                elif category == "Analysis": tool_options = ["Statistics", "Bounding Box", "Mean Coordinate"]
                elif category == "Overlay Operations": tool_options = ["Intersection", "Difference", "Union", "Spatial Join"]
                elif category == "Data Management": tool_options = ["Reproject", "Merge"]
                
                tool = st.selectbox("Tool", tool_options)
                
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
                                res_gdf = gdf 
                            elif tool in ["Intersection", "Difference", "Union", "Spatial Join", "Merge"]:
                                if sec_gdf is None: st.error("Layer B required.");
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
            layers = []
            if st.session_state['main_gdf'] is not None: layers.append((st.session_state['main_gdf'], "Layer A", "#FFA500"))
            if st.session_state['secondary_gdf'] is not None: layers.append((st.session_state['secondary_gdf'], "Layer B", "#00E5FF"))
            if st.session_state['calc_result_gdf'] is not None: layers.append((st.session_state['calc_result_gdf'], "Result", "#39FF14"))
            
            show_calc_map = st.toggle("Show Geometry on Map", value=True)
            render_map(layers, height=550, show_geometries=show_calc_map)
            
            if st.session_state['calc_result_gdf'] is not None:
                with st.container(border=True):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                         out_fmt = st.selectbox("Export Result As", ["GeoJSON", "ESRI Shapefile (.zip)", "KML", "GeoPackage", "WKT (CSV)"])
                    with c2:
                         st.write("") 
                         st.write("") 
                         d, e, m = handle_export(st.session_state['calc_result_gdf'], out_fmt, "analysis_result")
                         if d: st.download_button("Download Result", d, f"result{e}", m, use_container_width=True, type="primary")

if __name__ == "__main__":
    main()
