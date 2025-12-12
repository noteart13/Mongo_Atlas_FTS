# Setup GitHub Actions CI/CD with Docker Hub

## Step 1: Add Docker Hub Credentials to GitHub Secrets

1. Go to GitHub repository: https://github.com/noteart13/Mongo_Atlas_FTS
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add:

### Secret 1: DOCKER_USERNAME
- **Name:** `DOCKER_USERNAME`
- **Value:** `noteart13`

### Secret 2: DOCKER_PASSWORD
- **Name:** `DOCKER_PASSWORD`  
- **Value:** Your Docker Hub **Personal Access Token** (NOT your password!)

**How to create Docker Hub Personal Access Token:**
1. Go to https://hub.docker.com/settings/security
2. Click "New Access Token"
3. Give it a name (e.g., "github-actions")
4. Select "Read, Write, Delete" permissions
5. Copy the token and paste in GitHub Secret

### Secret 3: GCP_SA_KEY (Optional - only if you want K8s auto-update)
- **Name:** `GCP_SA_KEY`
- **Value:** Your GCP service account JSON key (if available)

*Note: If you don't have GCP_SA_KEY, the workflow will still build and push to Docker Hub. You'll just need to manually update K8s deployment.*

## Step 2: How the Workflow Works

When you **push to main branch**:
1. ✅ Docker image builds automatically
2. ✅ Image tags: `noteart13/mongodb-fts-api:latest` + commit SHA
3. ✅ Pushed to Docker Hub automatically
4. ✅ K8s deployment auto-updates (if GCP_SA_KEY available)

## Step 3: Manual Kubernetes Update (if no auto-deploy)

If you don't have GCP credentials, manually update K8s after Docker build:

```bash
# Pull latest image from Docker Hub
kubectl set image deployment/mongodb-fts-api \
  fastapi-app=noteart13/mongodb-fts-api:latest \
  -n mongodb-fts --record

# Check rollout status
kubectl rollout status deployment/mongodb-fts-api -n mongodb-fts
```

## Step 4: View Workflow Status

After pushing to main:
1. Go to GitHub repository
2. Click **Actions** tab
3. See your workflow running in real-time
4. Check Docker Hub: https://hub.docker.com/r/noteart13/mongodb-fts-api

## Step 5: Verify Deployment

Check if pods are running with new image:

```bash
kubectl describe pod -n mongodb-fts
kubectl logs -n mongodb-fts deployment/mongodb-fts-api
```

## Troubleshooting

**Workflow fails with "authentication failed":**
- Check Docker credentials in GitHub Secrets
- Verify Docker Hub Personal Access Token is valid
- Go to https://hub.docker.com/settings/security to regenerate token if needed

**K8s doesn't update:**
- Confirm GCP_SA_KEY is valid and has proper permissions
- Or manually run: `kubectl rollout restart deployment/mongodb-fts-api -n mongodb-fts`

**Image doesn't pull on K8s:**
- Make sure deployment.yaml has `imagePullPolicy: Always`
- Check: `kubectl get pods -n mongodb-fts` for ImagePullBackOff errors
