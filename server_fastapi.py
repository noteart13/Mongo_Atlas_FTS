from fastapi import FastAPI, Query, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
import pymongo
from config import mongo_uri, API_KEY
import ast
import json

# Kết nối MongoDB
try:
    print("Đang kết nối đến MongoDB...")
    import ssl
    conn = pymongo.MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,
        tlsAllowInvalidCertificates=True
    )
    # Test the connection
    conn.admin.command('ping')
    print("Kết nối MongoDB thành công!")
    
    # Kết nối đến các collection
    db = conn.get_database('sample_mflix')
    collection = db['movies']
    print(f"Đã kết nối đến collection 'movies' với {collection.estimated_document_count()} documents")
    
    db_airbnb = conn.get_database('sample_airbnb')
    collection_airbnb = db_airbnb['listingsAndReviews']
    print(f"Đã kết nối đến collection 'listingsAndReviews' với {collection_airbnb.estimated_document_count()} documents")
    
except pymongo.errors.ServerSelectionTimeoutError as err:
    print(f"Lỗi kết nối MongoDB: {err}")
    print("Vui lòng kiểm tra kết nối mạng và thông tin kết nối trong file config.py")
    raise

except Exception as e:
    print(f"Lỗi không xác định: {e}")
    raise

# ==================== FASTAPI APP ====================

# Khởi tạo FastAPI app (không dùng lifespan)
app = FastAPI(
    title="MongoDB Atlas FTS API",
    description="MongoDB Full Text Search Demo with FastAPI",
    version="1.0.0",
    swagger_ui_parameters={"persistAuthorization": False}
)

print("✅ MongoDB Atlas FTS API started!")
print("📚 Swagger UI: http://localhost:5010/docs")
print("📖 ReDoc: http://localhost:5010/redoc")

# (removed duplicate FastAPI initialization)

# Mount static files (if exists)
import os
if os.path.exists("templates/static"):
    app.mount("/static", StaticFiles(directory="templates/static"), name="static")
elif os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ==================== SECURITY ====================

def verify_api_key(api_key: str = Header(default=None, alias="X-API-Key")):
    """Xác thực API key qua header `X-API-Key`."""
    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

# ==================== OPENAPI (Swagger Authorize) ====================

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes["ApiKeyAuth"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "Nhập API key để gọi các endpoint"
    }

    # Áp dụng yêu cầu bảo mật cho tất cả các operations
    openapi_schema["security"] = [{"ApiKeyAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ==================== MODELS ====================

class SearchResponse(BaseModel):
    docs: List[Any] = []
    count: int = 0
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

# ==================== PAGES (serve HTML) ====================

# Serve the Geo Near demo page directly (static HTML)
@app.get("/geonear", include_in_schema=False)
def geonear_page():
    if os.path.exists("templates/geonear.html"):
        return FileResponse("templates/geonear.html")
    raise HTTPException(status_code=404, detail="geonear.html not found")

# ==================== SEARCH ENDPOINTS ====================

@app.get("/api/search", response_model=SearchResponse, tags=["Search"], dependencies=[Depends(verify_api_key)])
def search(query: str = Query(..., description="Search query string")):
    """
    Tìm kiếm phim theo query string
    
    Ví dụ: `/api/search?query=italian`
    """
    if not query or len(query.strip()) == 0:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        import os
        # Sử dụng đường dẫn tuyệt đối đến file query
        query_path = os.path.join(os.path.dirname(__file__), 'mongodb-atlas-fts-main', 'queries', 'query19.json')
        print(f"Đang đọc file query từ: {query_path}")
        
        with open(query_path, "r", encoding='utf-8') as f:
            agg_query = f.read().replace("!!queryParameter!!", query)
        
        agg_pipeline = ast.literal_eval(agg_query)
        docs = list(collection.aggregate(agg_pipeline))
        
        return SearchResponse(docs=docs, count=len(docs))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# ==================== AUTOCOMPLETE ENDPOINTS ====================

@app.get("/api/autocomplete", response_model=List[dict], tags=["Autocomplete"], dependencies=[Depends(verify_api_key)])
def autocomplete(query: str = Query(..., description="Autocomplete query (min 3 chars)")):
    """
    Gợi ý tiêu đề phim
    
    Ví dụ: `/api/autocomplete?query=sca`
    """
    if not query or len(query) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters")
    
    try:
        agg_pipeline = [
            { 
                "$search": {
                    "index": "title_autocomplete",
                    "autocomplete": {
                        "path": "title",
                        "query": query,
                        "fuzzy": {"maxEdits": 1, "maxExpansions": 100}
                    }
                }
            },
            {"$project": {"title": 1, "_id": 0, "year": 1, "fullplot": 1}},
            {"$limit": 15}
        ]
        
        return list(collection.aggregate(agg_pipeline))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Autocomplete failed: {str(e)}")

# ==================== GEOSPATIAL ENDPOINTS ====================

@app.get("/api/geo/circle", response_model=SearchResponse, tags=["Geospatial"], dependencies=[Depends(verify_api_key)])
def geo_circle(
    radius: int = Query(..., description="Radius in meters"),
    latitude: float = Query(..., description="Center latitude"),
    longtitude: float = Query(..., description="Center longitude")
):
    """
    Tìm kiếm trong vòng tròn
    
    Ví dụ: `/api/geo/circle?radius=5000&latitude=41.3851&longtitude=2.1734`
    """
    try:
        with open("queries/query30.json", "r", encoding='utf-8') as f:
            json_agg_query = json.loads(f.read())
        
        json_agg_query[0]['$search']['geoWithin']['circle']['radius'] = radius
        json_agg_query[0]['$search']['geoWithin']['circle']['center']['coordinates'] = [longtitude, latitude]
        
        docs = list(collection_airbnb.aggregate(json_agg_query))
        return SearchResponse(docs=docs, count=len(docs))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geo search failed: {str(e)}")

@app.get("/api/geo/box", response_model=SearchResponse, tags=["Geospatial"], dependencies=[Depends(verify_api_key)])
def geo_box(
    lat_min: float = Query(..., description="Minimum latitude"),
    lon_min: float = Query(..., description="Minimum longitude"),
    lat_max: float = Query(..., description="Maximum latitude"),
    lon_max: float = Query(..., description="Maximum longitude")
):
    """
    Tìm kiếm trong hình chữ nhật (Box)
    
    Ví dụ: `/api/geo/box?lat_min=41.3&lon_min=2.1&lat_max=41.4&lon_max=2.2`
    """
    try:
        with open("queries/query31.json", "r", encoding='utf-8') as f:
            json_agg_query = json.loads(f.read())
        
        json_agg_query[0]['$search']['geoWithin']['box']['bottomLeft']['coordinates'] = [lon_min, lat_min]
        json_agg_query[0]['$search']['geoWithin']['box']['topRight']['coordinates'] = [lon_max, lat_max]
        
        docs = list(collection_airbnb.aggregate(json_agg_query))
        return SearchResponse(docs=docs, count=len(docs))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geo search failed: {str(e)}")

@app.get("/api/geo/near", response_model=SearchResponse, tags=["Geospatial"], dependencies=[Depends(verify_api_key)])
def geo_near(
    latitude: float = Query(..., description="Latitude"),
    longtitude: float = Query(..., description="Longitude"),
    max_distance: int = Query(5000, description="Maximum distance in meters"),
    property_type: str = Query("Apartment", description="Property type"),
    keyword: Optional[str] = Query(None, description="Optional keyword to boost description matches")
):
    """
    Tìm kiếm property gần nhất (sử dụng MongoDB geospatial query)
    
    Ví dụ: `/api/geo/near?latitude=41.3851&longtitude=2.1734&property_type=Apartment&max_distance=5000`
    """
    try:
        # Dựng pipeline từ mẫu query34.json
        with open("queries/query34.json", "r", encoding='utf-8') as f:
            json_agg_query = json.loads(f.read())

        # Thiết lập near origin và pivot (sử dụng max_distance)
        json_agg_query[0]['$search']['compound']['should'][0]['near']['origin']['coordinates'] = [longtitude, latitude]
        json_agg_query[0]['$search']['compound']['should'][0]['near']['pivot'] = max_distance

        # Bắt buộc khớp theo property_type
        json_agg_query[0]['$search']['compound']['must']['text']['query'] = property_type

        # Nếu có keyword thì tăng điểm theo mô tả; nếu không thì bỏ phần should thứ hai
        if keyword and keyword.strip():
            json_agg_query[0]['$search']['compound']['should'][1]['text']['query'] = keyword
        else:
            json_agg_query[0]['$search']['compound']['should'] = [
                json_agg_query[0]['$search']['compound']['should'][0]
            ]

        docs = list(collection_airbnb.aggregate(json_agg_query))
        return SearchResponse(docs=docs, count=len(docs))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geo near failed: {str(e)}")


# ==================== API INFO ====================

@app.get("/api", tags=["Info"], dependencies=[Depends(verify_api_key)])
def api_info():
    """Thông tin API"""
    return {
        "name": "MongoDB Atlas FTS API",
        "version": "1.0.0",
        "description": "FastAPI for MongoDB Full Text Search",
        "endpoints": {
            "search": "/api/search?query=...",
            "autocomplete": "/api/autocomplete?query=...",
            "geo_circle": "/api/geo/circle?radius=...&latitude=...&longtitude=...",
            "geo_box": "/api/geo/box?lat_min=...&lon_min=...&lat_max=...&lon_max=...",
            "geo_near": "/api/geo/near?latitude=...&longtitude=..."
        },
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server_fastapi:app", host="0.0.0.0", port=5010, reload=True)
