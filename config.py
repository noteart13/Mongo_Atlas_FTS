from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

# Load .env so API_KEY (and others) can come from env file
load_dotenv()

mongo_uri = os.getenv("MONGODB_URI")
if not mongo_uri:
    user = os.getenv("MONGO_USER")
    password = os.getenv("MONGO_PASSWORD")
    host = os.getenv("MONGO_HOST")
    if user and password and host:
        mongo_uri = f"mongodb+srv://{quote_plus(user)}:{quote_plus(password)}@{host}/?retryWrites=true&w=majority"
    else:
        raise RuntimeError(
            "Missing MONGODB_URI. Set it in environment or provide MONGO_USER, MONGO_PASSWORD, and MONGO_HOST."
        )

# API key dùng để xác thực request vào FastAPI
# Nên cấu hình qua biến môi trường `API_KEY`; giá trị mặc định chỉ dùng cho phát triển
API_KEY = os.getenv("API_KEY", "dev-secret-key")