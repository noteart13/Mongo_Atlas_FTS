from fastapi import FastAPI, Query, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
import pymongo
from config import mongo_uri, API_KEY
import ast
import json
import os

# ==================== MONGODB CONNECTION ====================
try:
    print("Đang kết nối đến MongoDB...")
    conn = pymongo.MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,
        tlsAllowInvalidCertificates=True
    )
    conn.admin.command('ping')
    print("✅ Kết nối MongoDB thành công!")
    
    db = conn.get_database('sample_mflix')
    collection = db['movies']
    print(f"✅ Đã kết nối đến collection 'movies' với {collection.estimated_document_count()} documents")
    
    db_airbnb = conn.get_database('sample_airbnb')
    collection_airbnb = db_airbnb['listingsAndReviews']
    print(f"✅ Đã kết nối đến collection 'listingsAndReviews' với {collection_airbnb.estimated_document_count()} documents")
    
except Exception as e:
    print(f"❌ Lỗi kết nối MongoDB: {e}")
    raise

# ==================== FASTAPI APP ====================
app = FastAPI(
    title="MongoDB Atlas FTS API",
    description="MongoDB Full Text Search Demo with FastAPI - Protected by API Key",
    version="1.0.0",
)

port = int(os.getenv("PORT", "5011"))

print("\n" + "="*60)
print("✅ MongoDB Atlas FTS API started!")
print("="*60)
print(f"📚 Swagger UI: http://localhost:{port}/docs")
print(f"📖 ReDoc: http://localhost:{port}/redoc")
print(f"🔑 Default API Key: {API_KEY}")
print("="*60 + "\n")

# Mount static files
if os.path.exists("templates/static"):
    app.mount("/static", StaticFiles(directory="templates/static"), name="static")
elif os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ==================== SECURITY - API KEY ====================

# Định nghĩa API Key Header
api_key_header_scheme = APIKeyHeader(
    name="X-API-Key",
    scheme_name="API Key Authentication",
    description="Enter your API key",
    auto_error=True
)

def verify_api_key(api_key: str = Security(api_key_header_scheme)) -> str:
    """
    Xác thực API key từ header X-API-Key.
    Swagger UI sẽ tự động hiển thị nút Authorize khi dùng Security()
    """
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )
    return api_key

# ==================== MODELS ====================

class SearchResponse(BaseModel):
    """Response model cho search results"""
    docs: List[Any] = []
    count: int = 0
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

# ==================== PUBLIC ENDPOINTS ====================

@app.get("/", tags=["Public"])
def root():
    """Root endpoint - không cần API key"""
    return {
        "message": "MongoDB Atlas FTS API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "note": "API endpoints require X-API-Key header. Click 'Authorize' button in /docs to set it.",
        "default_key": API_KEY
    }

@app.get("/healthz", tags=["Public"], include_in_schema=False)
def healthz():
    """Health check endpoint"""
    return {"status": "ok"}

@app.get("/geonear", tags=["Public"], include_in_schema=False)
def geonear_page():
    """Serve Geo Near demo page"""
    if os.path.exists("templates/geonear.html"):
        return FileResponse("templates/geonear.html")
    raise HTTPException(status_code=404, detail="geonear.html not found")

# ==================== PROTECTED ENDPOINTS ====================

@app.get(
    "/api",
    tags=["Info"],
    summary="API Information",
    dependencies=[Security(verify_api_key)]
)
def api_info():
    """
    🔒 Protected Endpoint - Requires API Key
    
    Thông tin về API
    """
    return {
        "name": "MongoDB Atlas FTS API",
        "version": "1.0.0",
        "authentication": "API Key via X-API-Key header",
        "endpoints": {
            "search": "/api/search?query=...",
            "autocomplete": "/api/autocomplete?query=...",
            "geo_circle": "/api/geo/circle",
            "geo_box": "/api/geo/box",
            "geo_near": "/api/geo/near"
        }
    }

@app.get(
    "/api/search",
    response_model=SearchResponse,
    tags=["Search"],
    summary="Search Movies",
    dependencies=[Security(verify_api_key)]
)
def search(query: str = Query(..., description="Search query", min_length=1)):
    """
    🔒 Protected Endpoint - Requires API Key
    
    Tìm kiếm phim theo từ khóa
    
    **Example:** `/api/search?query=godfather`
    """
    try:
        query_path = os.path.join(os.path.dirname(__file__), 'queries', 'query19.json')
        
        with open(query_path, "r", encoding='utf-8') as f:
            agg_query = f.read().replace("!!queryParameter!!", query)
        
        agg_pipeline = ast.literal_eval(agg_query)
        docs = list(collection.aggregate(agg_pipeline))
        
        return SearchResponse(docs=docs, count=len(docs))
    
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Query template not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get(
    "/api/autocomplete",
    response_model=List[dict],
    tags=["Autocomplete"],
    summary="Autocomplete Movie Titles",
    dependencies=[Security(verify_api_key)]
)
def autocomplete(query: str = Query(..., description="Search query (min 3 chars)", min_length=3)):
    """
    🔒 Protected Endpoint - Requires API Key
    
    Tự động hoàn thành tiêu đề phim
    
    **Example:** `/api/autocomplete?query=god`
    """
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

@app.get(
    "/api/geo/circle",
    response_model=SearchResponse,
    tags=["Geospatial"],
    summary="Search Within Circle",
    dependencies=[Security(verify_api_key)]
)
def geo_circle(
    radius: int = Query(..., description="Radius in meters", gt=0),
    latitude: float = Query(..., description="Center latitude", ge=-90, le=90),
    longtitude: float = Query(..., description="Center longitude", ge=-180, le=180)
):
    """
    🔒 Protected Endpoint - Requires API Key
    
    Tìm kiếm trong vòng tròn
    
    **Example:** `/api/geo/circle?radius=5000&latitude=41.3851&longtitude=2.1734`
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

@app.get(
    "/api/geo/box",
    response_model=SearchResponse,
    tags=["Geospatial"],
    summary="Search Within Box",
    dependencies=[Security(verify_api_key)]
)
def geo_box(
    lat_min: float = Query(..., description="Min latitude", ge=-90, le=90),
    lon_min: float = Query(..., description="Min longitude", ge=-180, le=180),
    lat_max: float = Query(..., description="Max latitude", ge=-90, le=90),
    lon_max: float = Query(..., description="Max longitude", ge=-180, le=180)
):
    """
    🔒 Protected Endpoint - Requires API Key
    
    Tìm kiếm trong hình chữ nhật
    
    **Example:** `/api/geo/box?lat_min=41.3&lon_min=2.1&lat_max=41.4&lon_max=2.2`
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

@app.get(
    "/api/geo/near",
    response_model=SearchResponse,
    tags=["Geospatial"],
    summary="Search Near Point",
    dependencies=[Security(verify_api_key)]
)
def geo_near(
    latitude: float = Query(..., description="Latitude", ge=-90, le=90),
    longtitude: float = Query(..., description="Longitude", ge=-180, le=180),
    max_distance: int = Query(5000, description="Max distance (meters)", gt=0),
    property_type: str = Query("Apartment", description="Property type"),
    keyword: Optional[str] = Query(None, description="Keyword for description")
):
    """
    🔒 Protected Endpoint - Requires API Key
    
    Tìm kiếm gần điểm chỉ định
    
    **Example:** `/api/geo/near?latitude=41.3851&longtitude=2.1734`
    """
    try:
        with open("queries/query34.json", "r", encoding='utf-8') as f:
            json_agg_query = json.loads(f.read())

        json_agg_query[0]['$search']['compound']['should'][0]['near']['origin']['coordinates'] = [longtitude, latitude]
        json_agg_query[0]['$search']['compound']['should'][0]['near']['pivot'] = max_distance
        json_agg_query[0]['$search']['compound']['must']['text']['query'] = property_type

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

# ==================== LEGACY ENDPOINTS (Flask compatibility) ====================

@app.get("/search", include_in_schema=False)
def search_legacy(
    query: str = Query(None),
    api_key: str = Security(api_key_header_scheme)
):
    """Legacy endpoint - requires API key"""
    if not query:
        raise HTTPException(status_code=400, detail="Query required")
    return search(query=query)

@app.get("/autocomplete", include_in_schema=False)
def autocomplete_legacy(
    query: str = Query(None),
    api_key: str = Security(api_key_header_scheme)
):
    """Legacy endpoint - requires API key"""
    if not query:
        raise HTTPException(status_code=400, detail="Query required")
    return autocomplete(query=query)

# ==================== RUN SERVER ====================

if __name__ == "__main__":
    import uvicorn
    reload = os.getenv("RELOAD", "false").lower() == "true"
    uvicorn.run(
        "server_fastapi:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
        log_level="info"
    )
