from flask import Flask, render_template, request, jsonify, send_file
import os
import json
from werkzeug.utils import secure_filename
import geopandas as gpd
import rasterio
from rasterio.warp import calculate_default_transform, reproject
from rasterio.io import MemoryFile
import numpy as np
from pathlib import Path

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'shp', 'geojson', 'kml', 'gpx', 'grd', 'tif', 'tiff', 'nc'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/convert', methods=['POST'])
def convert_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': f'File type not allowed. Allowed: {app.config["ALLOWED_EXTENSIONS"]}'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        file_ext = filename.rsplit('.', 1)[1].lower()
        target_format = request.form.get('target_format', 'geojson')
        
        # Vector format conversion
        if file_ext in ['shp', 'geojson', 'kml', 'gpx']:
            gdf = gpd.read_file(filepath)
            
            # Handle reprojection
            target_crs = request.form.get('target_crs')
            if target_crs and gdf.crs:
                gdf = gdf.to_crs(target_crs)
            
            # Convert to target format
            if target_format == 'geojson':
                output_path = filepath.replace(file_ext, 'geojson')
                gdf.to_file(output_path, driver='GeoJSON')
            elif target_format == 'shapefile':
                output_path = filepath.replace(file_ext, 'shp')
                gdf.to_file(output_path, driver='ESRI Shapefile')
            elif target_format == 'kml':
                output_path = filepath.replace(file_ext, 'kml')
                gdf.to_file(output_path, driver='KML')
            elif target_format == 'gpkg':
                output_path = filepath.replace(file_ext, 'gpkg')
                gdf.to_file(output_path, driver='GPKG')
            
            return jsonify({
                'success': True,
                'message': f'Converted to {target_format}',
                'output': os.path.basename(output_path),
                'features': len(gdf),
                'crs': str(gdf.crs)
            })
        
        # Raster format conversion (GeoTIFF)
        elif file_ext in ['tif', 'tiff', 'grd']:
            with rasterio.open(filepath) as src:
                if target_format == 'geotiff':
                    output_path = filepath.replace(file_ext, 'tif')
                    with rasterio.open(
                        output_path, 'w',
                        driver='GTiff',
                        height=src.height,
                        width=src.width,
                        count=src.count,
                        dtype=src.dtypes[0],
                        crs=src.crs,
                        transform=src.transform,
                    ) as dst:
                        dst.write(src.read())
                    
                    return jsonify({
                        'success': True,
                        'message': 'Converted to GeoTIFF',
                        'output': os.path.basename(output_path),
                        'shape': (src.height, src.width),
                        'crs': str(src.crs)
                    })
        
        return jsonify({'error': 'Conversion not supported for this format'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<filename>')
def download_file(filename):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/supported-formats')
def supported_formats():
    return jsonify({
        'vector_formats': ['Shapefile', 'GeoJSON', 'KML', 'GPX', 'GeoPackage'],
        'raster_formats': ['GeoTIFF', 'NetCDF', 'GeoGrid'],
        'projections': [
            {'code': 'EPSG:4326', 'name': 'WGS84'},
            {'code': 'EPSG:3857', 'name': 'Web Mercator'},
            {'code': 'EPSG:2154', 'name': 'Lambert 93 (France)'},
            {'code': 'EPSG:31256', 'name': 'MGI Austria'},
            {'code': 'EPSG:32633', 'name': 'UTM Zone 33N'}
        ]
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
