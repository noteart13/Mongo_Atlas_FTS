"""
Script để kiểm tra API key configuration và test authentication
"""
import os
import sys
from config import API_KEY, mongo_uri
import requests
from urllib.parse import urljoin

def check_api_key_config():
    """Kiểm tra cấu hình API key"""
    print("=" * 60)
    print("🔍 KIỂM TRA API KEY CONFIGURATION")
    print("=" * 60)
    
    # 1. Kiểm tra API key từ config
    print(f"\n1. API Key từ config.py:")
    print(f"   - API Key: {API_KEY[:10]}...{API_KEY[-4:] if len(API_KEY) > 14 else '****'}")
    print(f"   - Độ dài: {len(API_KEY)} ký tự")
    
    if API_KEY == "dev-secret-key":
        print("   ⚠️  WARNING: Đang dùng default key (không an toàn cho production)")
    else:
        print("   ✅ Đã set custom API key")
    
    # 2. Kiểm tra environment variable
    print(f"\n2. Environment Variable:")
    env_key = os.getenv("API_KEY")
    if env_key:
        print(f"   ✅ API_KEY env var tồn tại: {env_key[:10]}...{env_key[-4:] if len(env_key) > 14 else '****'}")
    else:
        print("   ❌ API_KEY env var không tồn tại (đang dùng default)")
    
    # 3. Kiểm tra file .env
    print(f"\n3. File .env:")
    if os.path.exists(".env"):
        print("   ✅ File .env tồn tại")
        with open(".env", "r") as f:
            content = f.read()
            if "API_KEY" in content:
                print("   ✅ Có API_KEY trong .env")
            else:
                print("   ⚠️  Không có API_KEY trong .env")
    else:
        print("   ❌ File .env không tồn tại")
    
    # 4. Kiểm tra MongoDB connection
    print(f"\n4. MongoDB Connection:")
    try:
        import pymongo
        client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("   ✅ Kết nối MongoDB thành công")
    except Exception as e:
        print(f"   ❌ Lỗi kết nối MongoDB: {e}")
    
    print("\n" + "=" * 60)

def test_api_endpoints(base_url="http://localhost:5011"):
    """Test API endpoints với và không có API key"""
    print("\n" + "=" * 60)
    print("🧪 TEST API ENDPOINTS")
    print("=" * 60)
    
    # Test 1: Root endpoint (không cần API key)
    print("\n1. Test root endpoint (không cần API key):")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Thành công: {data.get('message', 'N/A')}")
            print(f"   API key configured: {data.get('api_key_configured', 'N/A')}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Không thể kết nối đến server. Đảm bảo server đang chạy!")
        print(f"   Chạy: python server_fastapi.py")
        return
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
        return
    
    # Test 2: Protected endpoint KHÔNG có API key
    print("\n2. Test protected endpoint (KHÔNG có API key):")
    try:
        response = requests.get(f"{base_url}/api/search?query=test", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 403:
            print("   ✅ Đúng: API từ chối request không có key")
        else:
            print(f"   ⚠️  Unexpected status: {response.status_code}")
            print(f"   Response: {response.text[:100]}")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
    
    # Test 3: Protected endpoint VỚI API key SAI
    print("\n3. Test protected endpoint (API key SAI):")
    try:
        headers = {"X-API-Key": "wrong-key-12345"}
        response = requests.get(f"{base_url}/api/search?query=test", headers=headers, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 403:
            print("   ✅ Đúng: API từ chối key sai")
        else:
            print(f"   ⚠️  Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
    
    # Test 4: Protected endpoint VỚI API key ĐÚNG
    print("\n4. Test protected endpoint (API key ĐÚNG):")
    try:
        headers = {"X-API-Key": API_KEY}
        response = requests.get(f"{base_url}/api/search?query=godfather", headers=headers, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            count = data.get('count', 0)
            print(f"   ✅ Thành công! Tìm thấy {count} kết quả")
        else:
            print(f"   ❌ Lỗi: Status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
    
    # Test 5: Health check
    print("\n5. Test health check endpoint:")
    try:
        response = requests.get(f"{base_url}/healthz", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Server đang hoạt động")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
    
    print("\n" + "=" * 60)

def main():
    """Main function"""
    check_api_key_config()
    
    # Hỏi có muốn test API không
    print("\nBạn có muốn test API endpoints không? (y/n): ", end="")
    try:
        choice = input().strip().lower()
        if choice == 'y':
            base_url = os.getenv("API_BASE_URL", "http://localhost:5011")
            print(f"\nĐang test API tại: {base_url}")
            print("(Đảm bảo server đang chạy: python server_fastapi.py)")
            test_api_endpoints(base_url)
        else:
            print("\nBỏ qua test API endpoints.")
    except KeyboardInterrupt:
        print("\n\nĐã hủy.")
        sys.exit(0)

if __name__ == "__main__":
    main()

