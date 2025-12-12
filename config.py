from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

# Load .env so API_KEY (and others) can come from env file
load_dotenv()

mongo_uri = os.getenv("MONGODB_URI")
if not mongo_uri:
    raise RuntimeError(
        "Missing MONGODB_URI. Please set it in environment or .env using your MongoDB Atlas connection string."
    )

# API key dùng để xác thực request vào FastAPI
# Nên cấu hình qua biến môi trường `API_KEY`; giá trị mặc định chỉ dùng cho phát triển
API_KEY = os.getenv("API_KEY", "dev-secret-key")