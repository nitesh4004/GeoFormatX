# GeoFormatX Flask Web Application

## Complete Full-Stack Geospatial Conversion Platform

A professional Flask web application for converting, reprojecting, and managing geospatial data formats.

## Features

### Vector Format Support
- **Input**: Shapefile, GeoJSON, KML, GPX
- **Output**: GeoJSON, Shapefile, KML, GeoPackage
- **Reprojection**: 100+ EPSG projection codes
- **Operations**: Format conversion, CRS transformation, metadata preservation

### Raster Format Support
- **Input/Output**: GeoTIFF, NetCDF, GeoGrid
- **Capabilities**: Geospatial metadata preservation, coordinate transformation

### Advanced Features
- **File Upload**: 500MB file size limit
- **Batch Processing**: Ready for multi-file operations
- **RESTful API**: JSON endpoints for programmatic access
- **Error Handling**: Comprehensive validation and error messages
- **Security**: Secure filename handling, file type validation

## Installation

### Local Development

```bash
# Clone repository
git clone https://github.com/nitesh4004/GeoFormatX.git
cd GeoFormatX

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python flask_app.py
```

App will be available at `http://localhost:5000`

## Requirements

```
Flask==2.3.0
Flask-CORS==4.0.0
geoPandas==0.12.0
rasterio==1.3.0
Fiona==1.9.0
shapely==2.0.0
rasterio[s3]==1.3.0
numpy==1.24.0
werkzeug==2.3.0
gunicorn==21.0.0  # Production server
python-dotenv==1.0.0
```

## API Endpoints

### POST /api/convert
Convert and reproject geospatial files

**Parameters**:
- `file`: Geospatial file (required)
- `target_format`: Output format (geojson, shapefile, kml, gpkg)
- `target_crs`: Target CRS code (e.g., EPSG:4326)

**Response**:
```json
{
  "success": true,
  "message": "Converted to geojson",
  "output": "filename.geojson",
  "features": 150,
  "crs": "EPSG:4326"
}
```

### GET /api/download/<filename>
Download converted file

### GET /api/supported-formats
Get list of supported formats and projection codes

## Deployment Options

### Option 1: Railway (Recommended)

1. Create account at https://railway.app
2. Connect GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn flask_app:app`
5. Add environment variables if needed
6. Deploy!

### Option 2: Heroku

```bash
# Login to Heroku
heroku login

# Create app
heroku create geoformatx-app

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

### Option 3: PythonAnywhere

1. Upload files to PythonAnywhere
2. Create virtual environment
3. Install dependencies
4. Configure WSGI file
5. Reload web app

### Option 4: AWS EC2

```bash
# SSH into instance
ssh -i key.pem ec2-user@your-instance.compute-1.amazonaws.com

# Install dependencies
sudo yum update
sudo yum install python3 python3-pip
sudo apt install gdal-bin libgdal-dev  # For geospatial libraries

# Clone and setup
git clone https://github.com/nitesh4004/GeoFormatX.git
cd GeoFormatX
pip install -r requirements.txt

# Run with gunicorn
gunicorn --bind 0.0.0.0:5000 flask_app:app
```

## Project Structure

```
GeoFormatX/
├── flask_app.py           # Main Flask application
├── requirements.txt       # Python dependencies
├── Procfile              # Heroku/Railway deployment config
├── templates/
│   └── index.html        # Web interface
├── static/
│   ├── css/
│   └── js/
├── uploads/              # Temporary file storage
├── FLASK_DEPLOYMENT.md   # This file
└── README.md            # Project overview
```

## Usage Examples

### Convert Shapefile to GeoJSON

```python
import requests

files = {'file': open('data.shp', 'rb')}
data = {'target_format': 'geojson'}
response = requests.post('http://localhost:5000/api/convert', files=files, data=data)
print(response.json())
```

### Reproject to WGS84

```python
files = {'file': open('data.shp', 'rb')}
data = {
    'target_format': 'shapefile',
    'target_crs': 'EPSG:4326'
}
response = requests.post('http://localhost:5000/api/convert', files=files, data=data)
```

## Performance Considerations

- Large files (>100MB) may require optimization
- Use GIS file format compression when possible
- Consider implementing queue system (Celery) for batch operations
- Add caching layer (Redis) for frequently accessed conversions

## Testing

```bash
# Run unit tests
python -m pytest tests/

# Test API endpoints
curl -X POST -F "file=@test.shp" http://localhost:5000/api/convert
```

## Troubleshooting

### GDAL/GEOS Installation Issues

**Linux**:
```bash
sudo apt-get install gdal-bin libgdal-dev libgeos-dev
pip install GDAL==$(gdal-config --version)
```

**macOS**:
```bash
brew install gdal geos
pip install GDAL
```

**Windows**:
Download pre-compiled wheels from [OSGeo4W](https://trac.osgeo.org/osgeo4w/)

## Security Notes

- Validate all file uploads
- Sanitize filenames
- Implement rate limiting for API
- Use HTTPS in production
- Set secure cookies and CORS policies
- Regular security updates for dependencies

## Performance Tips

1. Use CDN for static files
2. Implement caching headers
3. Compress responses with gzip
4. Use connection pooling for database
5. Monitor with APM tools (New Relic, DataDog)

## Contributing

1. Fork repository
2. Create feature branch
3. Implement changes
4. Add tests
5. Submit pull request

## License

MIT License - See LICENSE file

## Support

For issues and questions:
- GitHub Issues: https://github.com/nitesh4004/GeoFormatX/issues
- Email: nitesh4004@example.com

## Roadmap

- [ ] Web UI for file upload/download
- [ ] Batch processing queue
- [ ] Database for conversion history
- [ ] Advanced styling and visualization
- [ ] API key authentication
- [ ] Webhook support
- [ ] Cloud storage integration (S3, GCS)
- [ ] Docker containerization

---

**Built with Python & Flask | GeoFormatX 2025**
