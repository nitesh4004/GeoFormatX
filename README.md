# 🚄 **GeoFormatX** – Geospatial ETL & Format Conversion Platform

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Cloud-Native](https://img.shields.io/badge/Cloud--Native-Serverless-orange)](#)
[![Geospatial](https://img.shields.io/badge/Geospatial-Format%20Conversion-brightgreen)](#)

---

## 📋 **Overview**

**GeoFormatX** is a cloud-based geospatial conversion and transformation platform designed to streamline complex GIS data format handling. It automates vector format conversion, raster reprojection, and coordinate system transformations while maintaining spatial accuracy and metadata integrity.

### 🎯 **Core Value Proposition**

Eliminate manual GIS format conversion workflows. GeoFormatX handles shapefile, GeoJSON, KML, GeoTIFF, and raster reprojection with API-first architecture for production pipelines.

---

## ✨ **Key Features**

### **🌾 Ground Truth (GT) App Export Converter**

- **App Export Support**: Merges `fields.geojson` boundaries and `fields.csv` survey questionnaires exported from field survey apps.
- **FIELD ID Ordering**: Automatically sorts field placemarks sequentially by `FIELD ID` (e.g. `FLD-01ZzlUn7`, `FLD-344pLqRb`, `FLD-7W25Tqu1`).
- **Placemark Naming**: Custom placemark naming (`FIELD ID - Farmer Name`).
- **HTML Popup Cards**: Unpacks survey response pairs (Crop, Variety, Stage, Health, Sowing Date, Harvest Date, Irrigation, Soil Type, Area in Acres/SqM, Remarks) into clean styled HTML table popups for Google Earth and QGIS.
- **Dual Export**: Exports formatted `.kml` and cleaned `.csv` with centroid coordinates and acreage calculations.

### **📄 Vector Format Support**

- **Input Formats**: Shapefile, GeoJSON, GeoPackage, KML/KMZ, GML, PostGIS
- **Output Formats**: Shapefile, GeoJSON, GeoPackage, KML/KMZ, CSV with geometry
- **Batch Processing**: Process thousands of features asynchronously
- **Geometry Validation**: Automatic topology checking and repair
- **Attribute Mapping**: Flexible field transformation and aliasing

### **📈 Raster Format Support**

- **Input Formats**: GeoTIFF, HDF5, NetCDF, ERDAS IMG, COG
- **Output Formats**: GeoTIFF (Cloud-Optimized), COG, NetCDF, HDF5
- **Reprojection**: EPSG database with automatic CRS detection
- **Resampling Methods**: Nearest, bilinear, cubic, lanczos
- **Compression**: Lossless (LZW, Deflate) and lossy (JPEG, WebP)

### **🌐 Coordinate System Transformations**

- **Datum Shifts**: Nadcon5, ntv2 grid transformations
- **Multi-Step Projections**: Complex transformations via intermediate systems
- **Accuracy Validation**: Sub-meter accuracy assurance
- **Custom CRS Definition**: User-defined coordinate systems

### **📊 Data Quality**

- **Validation Reports**: Comprehensive error detection and logging
- **Duplicate Removal**: Feature deduplication algorithms
- **Boundary Simplification**: Douglas-Peucker, Visvalingam algorithms
- **Metadata Preservation**: GDAL metadata and ISO standards compliance

### **🚄 ETL Automation**

- **REST API**: Programmatic access to conversion workflows
- **Batch Jobs**: Cron-schedulable asynchronous processing
- **Webhooks**: Event-driven notifications on completion
- **Cloud Storage**: S3, Google Cloud Storage, Azure Blob integration

---

## 🚀 **Quick Start**

### **Prerequisites**

- Python 3.9+
- GDAL/GEOS libraries
- AWS account (for cloud deployment) or Docker

### **Installation**

```bash
# Clone repository
git clone https://github.com/nitesh4004/GeoFormatX.git
cd GeoFormatX

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start API server
uvicorn main:app --reload
```

### **API / Streamlit Usage**

```python
# Convert GeoJSON to KML
import geopandas as gpd

gdf = gpd.read_file('input_data.geojson')
# GeoFormatX automatically reprojects to EPSG:4326 for KML compatibility
gdf.to_file('output_data.kml', driver='KML')
```

```bash
# Launch GeoFormatX Interactive Web UI
streamlit run app.py
```

---

## 📂 **Project Structure**

```
GeoFormatX/
├── main.py                    # FastAPI application
├── requirements.txt          # Python dependencies
├── converters/              # Format-specific handlers
├── utils/                  # GDAL utilities, CRS handling
├── tests/                  # Unit and integration tests
└── docker/                 # Docker configurations
```

---

## 📋 **Supported Transformations**

### **Vector Transformations**

| From | To | Status |
|------|-------|--------|
| Shapefile | GeoJSON | ✅ |
| GeoJSON | KML | ✅ |
| GeoPackage | Shapefile | ✅ |
| PostGIS | GeoJSON | ✅ |
| CSV (with geom) | Shapefile | ✅ |
| KML | GeoPackage | ✅ |

### **Raster Transformations**

| Input | Output | Reprojection | Resampling |
|-------|--------|--------------|------------|
| GeoTIFF | COG | ✅ | ✅ |
| Landsat HDF5 | GeoTIFF | ✅ | ✅ |
| NetCDF | GeoTIFF | ✅ | ✅ |
| ERDAS IMG | GeoTIFF | ✅ | ✅ |

---

## 💡 **Use Cases**

1. **GIS Data Migration**
   - Legacy format conversion (SHP → GeoJSON)
   - Database migrations (PostGIS exports)
   - Multi-source data integration

2. **Satellite Data Processing**
   - Landsat/Sentinel GeoTIFF standardization
   - Cloud-optimized raster generation
   - Batch reprojection pipelines

3. **OpenData Integration**
   - Web services consumption (WFS, WMS)
   - Format standardization for data catalogs
   - Automated data updates

4. **Web Mapping Pipelines**
   - Vector-to-GeoJSON for web apps
   - Raster tiling for basemaps
   - Attribute filtering and simplification

---

## 📊 **Technical Stack**

| Component | Technology | Purpose |
|-----------|-----------|----------|
| **API** | FastAPI | High-performance Python web framework |
| **Geospatial** | GDAL/OGR | Vector/raster I/O |
| **Geometry** | Shapely, GEOS | Geometry operations |
| **Data Handling** | GeoPandas, Pandas | Spatial dataframes |
| **Cloud** | AWS Lambda, S3 | Serverless execution |
| **Queue** | Celery, Redis | Asynchronous task processing |
| **Containerization** | Docker | Consistent deployments |

---

## 🤝 **Contributing**

Contributions welcome! To contribute:

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-format`
3. Commit changes: `git commit -m "Add format support"`
4. Push to branch: `git push origin feature/new-format`
5. Open Pull Request

### **Development Guidelines**
- Add format handlers to `converters/` directory
- Include unit tests for new converters
- Update documentation with new format

---

## 📜 **License**

MIT License – See LICENSE file for details.

---

## 📬 **Contact & Support**

**Author:** Nitesh Kumar  
**Role:** Geospatial Data Scientist  
**Email:** nitesh.gulzar@gmail.com  
**GitHub:** [@nitesh4004](https://github.com/nitesh4004)  

### **Support Channels**

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/nitesh4004/GeoFormatX/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/nitesh4004/GeoFormatX/discussions)
- 📧 **Email**: For enterprise support or custom format handlers

---

## 🎯 **Roadmap**

- [ ] Web UI for drag-and-drop conversion
- [ ] GraphQL API support
- [ ] Custom projection definitions
- [ ] Streaming large file processing
- [ ] Validation rule engine
- [ ] Multi-threading optimization

---

## 📚 **References**

- [GDAL/OGR Documentation](https://gdal.org/)
- [EPSG Geodetic Parameter Registry](https://epsg.org/)
- [RFC 7946 - GeoJSON](https://tools.ietf.org/html/rfc7946)
- [Cloud Optimized GeoTIFF](https://www.cogeo.org/)

---

**Made with 🚄 by Nitesh Kumar | GIS Engineer @ SWANSAT OPC Pvt. Ltd**
