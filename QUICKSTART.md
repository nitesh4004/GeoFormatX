# GeoFormatX Flask Web App - Quick Start Guide

## 🚀 LIVE DEPLOYMENT READY

Your full-featured Flask geospatial conversion web application is ready to deploy!

## What You Have

✅ **flask_app.py** - Complete Flask backend
- Vector format conversion (Shapefile, GeoJSON, KML, GPX → Shapefile, GeoJSON, KML, GeoPackage)
- Raster format handling (GeoTIFF, NetCDF, GeoGrid)
- Advanced CRS reprojection (100+ EPSG codes)
- RESTful API endpoints
- Secure file handling
- Error management

✅ **FLASK_DEPLOYMENT.md** - Complete documentation
- Installation instructions
- API endpoint reference
- 4 deployment platform guides
- Troubleshooting tips

✅ **Static Website** (GitHub Pages)
- Professional landing page at https://nitesh4004.github.io/GeoFormatX/

## Quick Local Setup (5 minutes)

```bash
# Clone and navigate
git clone https://github.com/nitesh4004/GeoFormatX.git
cd GeoFormatX

# Create environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install Flask Flask-CORS geoPandas rasterio numpy werkzeug

# Run app
python flask_app.py
```

Access at: **http://localhost:5000**

## Deploy to Production (Choose 1)

### 1️⃣ Railway (RECOMMENDED - Easiest)

```bash
# Visit https://railway.app
# 1. Sign up with GitHub
# 2. Click "New Project" → "Deploy from GitHub repo"
# 3. Select nitesh4004/GeoFormatX
# 4. Build: pip install -r requirements.txt
# 5. Start: gunicorn flask_app:app
# 6. Done! Get your URL
```

### 2️⃣ Heroku

```bash
heroku login
heroku create geoformatx-prod
git push heroku main
heroku open
```

### 3️⃣ PythonAnywhere

1. Sign up at https://www.pythonanywhere.com/
2. Upload repository files
3. Create virtual environment
4. Configure WSGI app
5. Reload web app

### 4️⃣ AWS EC2

```bash
ssh -i key.pem ubuntu@your-instance.com
sudo apt update
sudo apt install python3-pip gdal-bin libgdal-dev
git clone https://github.com/nitesh4004/GeoFormatX.git
cd GeoFormatX
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:5000 flask_app:app
```

## API Usage Examples

### Convert Shapefile to GeoJSON

```python
import requests

with open('data.shp', 'rb') as f:
    files = {'file': f}
    data = {'target_format': 'geojson'}
    response = requests.post('http://localhost:5000/api/convert', 
                            files=files, data=data)
    print(response.json())
```

### Reproject to WGS84

```python
with open('data.shp', 'rb') as f:
    files = {'file': f}
    data = {
        'target_format': 'shapefile',
        'target_crs': 'EPSG:4326'
    }
    response = requests.post('http://localhost:5000/api/convert', 
                            files=files, data=data)
```

### Get Supported Formats

```bash
curl http://localhost:5000/api/supported-formats
```

## Features Included

### Vector Support
- ✓ Shapefile
- ✓ GeoJSON
- ✓ KML
- ✓ GPX
- ✓ GeoPackage

### Raster Support
- ✓ GeoTIFF
- ✓ NetCDF
- ✓ GeoGrid

### Reprojection
- ✓ WGS84 (EPSG:4326)
- ✓ Web Mercator (EPSG:3857)
- ✓ UTM Zones
- ✓ And 100+ more EPSG codes

### Security
- ✓ Secure filename handling
- ✓ File type validation
- ✓ 500MB upload limit
- ✓ Error handling

## Next Steps

1. **Test locally** - Run python flask_app.py and test API
2. **Choose platform** - Pick one deployment option above
3. **Deploy** - Follow platform-specific instructions
4. **Share URL** - Your app will have a public URL!

## Troubleshooting

**GDAL Installation Issues?**

Linux:
```bash
sudo apt-get install gdal-bin libgdal-dev libgeos-dev
```

macOS:
```bash
brew install gdal geos
```

**Port already in use?**
```bash
python flask_app.py --port 8000
```

**Dependencies not installing?**
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## File Structure

```
GeoFormatX/
├── flask_app.py           ← Main application
├── requirements.txt       ← Dependencies
├── FLASK_DEPLOYMENT.md    ← Full documentation
├── QUICKSTART.md          ← This file
└── uploads/               ← Temp file storage
```

## Support & Documentation

- **Full Guide**: Read `FLASK_DEPLOYMENT.md`
- **GitHub**: https://github.com/nitesh4004/GeoFormatX
- **Issues**: https://github.com/nitesh4004/GeoFormatX/issues

---

**Status**: ✅ Production-Ready | Built with Python & Flask | 2025
