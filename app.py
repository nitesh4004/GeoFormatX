import os
import geopandas as gpd
import pandas as pd

# 1. Setup the base directory path
# Make sure this path is correct for your machine
base_dir = r"E:\Download\INDIAN-SHAPEFILES-master\INDIAN-SHAPEFILES-master\STATES"

all_dataframes = []

print("Starting to load state files...")

# 2. Loop through every folder in the STATES directory
for state_folder in os.listdir(base_dir):
    state_path = os.path.join(base_dir, state_folder)
    
    # Check if it is actually a folder
    if os.path.isdir(state_path):
        
        # 3. EXCLUDE MAHARASHTRA
        # We convert to upper case to ensure we match 'Maharashtra', 'MAHARASHTRA', etc.
        if "MAHARASHTRA" in state_folder.upper():
            print(f"Skipping {state_folder} as requested.")
            continue
        
        # 4. Find the village GeoJSON file
        # Based on your screenshot, the pattern is: STATES\STATE_NAME\STATE_NAME_VILLAGES.geojson
        expected_filename = f"{state_folder}_VILLAGES.geojson"
        file_full_path = os.path.join(state_path, expected_filename)
        
        # Check if the file actually exists before trying to read it
        if os.path.exists(file_full_path):
            try:
                print(f"Loading data for: {state_folder}...")
                gdf = gpd.read_file(file_full_path)
                
                # Optional: Add a column for the state name if it's not already there
                gdf['source_state'] = state_folder
                
                all_dataframes.append(gdf)
                
            except Exception as e:
                print(f"Could not read file for {state_folder}. Error: {e}")
        else:
            # Fallback: If the naming isn't exact, look for ANY .geojson inside the folder
            print(f"Standard file not found for {state_folder}, searching folder...")
            found_backup = False
            for f in os.listdir(state_path):
                if f.endswith(".geojson") and "VILLAGE" in f.upper():
                    backup_path = os.path.join(state_path, f)
                    try:
                        print(f"Found backup file: {f}")
                        gdf = gpd.read_file(backup_path)
                        gdf['source_state'] = state_folder
                        all_dataframes.append(gdf)
                        found_backup = True
                        break
                    except Exception as e:
                        print(f"Error reading backup file {f}: {e}")
            
            if not found_backup:
                print(f"No suitable village data found in {state_folder}")

# 5. Merge all the loaded states into one big GeoDataFrame
if all_dataframes:
    print("Combining all states into one dataset...")
    final_gdf = pd.concat(all_dataframes, ignore_index=True)
    
    print("Success! Final dataset loaded.")
    print(final_gdf.head())
    print(f"Total rows: {len(final_gdf)}")
else:
    print("No data was loaded. Please check your folder path.")

# 6. (Optional) Save the combined file so you don't have to reload next time
# final_gdf.to_file("All_States_Villages_Except_MH.geojson", driver='GeoJSON')
