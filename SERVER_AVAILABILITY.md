# Server Availability và Các Trường Hợp Ảnh Hưởng

## ✅ Server KHÔNG bị ảnh hưởng khi:

### 1. Tắt máy tính của bạn
- **Không ảnh hưởng** vì server chạy trên Google Cloud Platform (GKE), không phải trên máy local
- Server vẫn chạy 24/7 trên cloud

### 2. Đóng terminal/command prompt
- **Không ảnh hưởng** - Server đã được deploy lên K8s, không phụ thuộc vào terminal local

### 3. Tắt WiFi/Internet trên máy bạn
- **Không ảnh hưởng** - Chỉ bạn không truy cập được, server vẫn chạy bình thường

### 4. Restart máy tính của bạn
- **Không ảnh hưởng** - Server chạy độc lập trên cloud

### 5. Xóa code trên máy local
- **Không ảnh hưởng** - Code đã được build thành Docker image và push lên Artifact Registry
- Server chạy từ image trên cloud, không phụ thuộc vào code local

## ❌ Server BỊ ẢNH HƯỞNG khi:

### 1. Xóa Pod/Deployment trên Kubernetes
```bash
# Các lệnh này sẽ DỪNG server:
kubectl delete deployment mongodb-atlas-fts-api
kubectl delete -f k8s/
kubectl delete pod <pod-name>
```

### 2. Xóa Kubernetes Cluster
- Nếu xóa GKE cluster → Server sẽ mất hoàn toàn

### 3. Xóa Secret MongoDB
```bash
# Lệnh này sẽ làm server crash:
kubectl delete secret mongodb-secret
```

### 4. Hết quota/credit GCP
- Nếu hết free tier hoặc không thanh toán → GCP có thể tạm dừng services

### 5. Lỗi trong code (nếu update image mới)
- Nếu push image mới có bug → Pod sẽ crash và restart liên tục

### 6. MongoDB Atlas có vấn đề
- Nếu MongoDB Atlas down hoặc block IP → Server không thể kết nối database

### 7. Xóa Docker Image trên Artifact Registry
- Nếu xóa image → K8s không thể pull image mới khi pod restart

### 8. Thay đổi cấu hình K8s sai
- Nếu sửa deployment.yaml sai → Pod không thể start

## 🔄 Server TỰ ĐỘNG KHÔI PHỤC khi:

### 1. Pod crash
- Kubernetes tự động restart pod nếu crash
- Có thể restart tối đa theo cấu hình

### 2. Node (máy chủ) bị lỗi
- GKE tự động chuyển pod sang node khác
- Pod sẽ được tạo lại trên node mới

### 3. Image pull failed tạm thời
- K8s sẽ retry pull image

## 📊 Kiểm tra trạng thái server:

```bash
# Xem pods
kubectl get pods

# Xem deployment
kubectl get deployment mongodb-atlas-fts-api

# Xem service và External IP
kubectl get svc mongodb-atlas-fts-api

# Xem logs
kubectl logs -l app=mongodb-atlas-fts-api -f

# Xem events
kubectl get events --sort-by='.lastTimestamp'
```

## 🛡️ Đảm bảo Server luôn chạy:

### 1. Không xóa deployment
```bash
# ĐỪNG chạy lệnh này trừ khi muốn dừng server:
# kubectl delete deployment mongodb-atlas-fts-api
```

### 2. Giữ Secret MongoDB
```bash
# ĐỪNG xóa secret:
# kubectl delete secret mongodb-secret
```

### 3. Monitor logs định kỳ
```bash
# Kiểm tra server có chạy tốt không
kubectl logs -l app=mongodb-atlas-fts-api --tail=50
```

### 4. Kiểm tra GCP billing
- Đảm bảo có credit/quota đủ để chạy GKE cluster

## 📝 Tóm tắt:

| Hành động | Ảnh hưởng |
|-----------|-----------|
| Tắt máy tính của bạn | ❌ Không ảnh hưởng |
| Đóng terminal | ❌ Không ảnh hưởng |
| Xóa code local | ❌ Không ảnh hưởng |
| Xóa deployment | ✅ **DỪNG server** |
| Xóa secret | ✅ **Server crash** |
| Xóa cluster | ✅ **Mất server** |
| Hết GCP credit | ✅ **Có thể dừng** |
| MongoDB Atlas down | ✅ **Server không hoạt động** |

## 💡 Lưu ý:

- Server hiện tại đang chạy trên **GKE Autopilot** (managed Kubernetes)
- Pod sẽ tự động restart nếu crash
- External IP: `35.193.64.92` (có thể thay đổi nếu xóa service)
- Server chạy 24/7 miễn là GKE cluster còn hoạt động

