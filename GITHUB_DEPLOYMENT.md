# GitHub Actions Deployment Guide

## Quick Setup Commands

### For Linux/Mac:
```bash
# Make the script executable
chmod +x deploy-to-github.sh

# Run the deployment script
./deploy-to-github.sh
```

### For Windows PowerShell:
```powershell
# Run the deployment script
.\deploy-to-github.ps1 -FunctionAppName "your-function-app-name" -ResourceGroup "your-resource-group"
```

## Manual Setup Steps

### 1. Initialize Git Repository
```bash
git init
git add .
git commit -m "Initial commit with Azure Function"
```

### 2. Create GitHub Repository
- Go to https://github.com/new
- Create a new repository
- Don't initialize with README (we already have files)

### 3. Connect Local Repository to GitHub
```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

### 4. Get Azure Function Publish Profile
```bash
# Using Azure CLI
az functionapp deployment list-publishing-profiles \
  --name YOUR_FUNCTION_APP_NAME \
  --resource-group YOUR_RESOURCE_GROUP \
  --xml
```

### 5. Set GitHub Secret
1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `AZURE_FUNCTIONAPP_PUBLISH_PROFILE`
5. Value: Paste the XML content from step 4

### 6. Update Workflow File
Edit `.github/workflows/deploy-azure-function.yml` and replace:
```yaml
AZURE_FUNCTIONAPP_NAME: your-function-app-name
```
with your actual function app name.

### 7. Set Environment Variables in Azure
In Azure Portal → Your Function App → Configuration → Application settings, add:
- `BVC_ONENOTE_INGEST_BOT_ID`
- `BVC_ONENOTE_INGEST_BOT_KEY`
- `BVC_BOT_REFRESH_TOKEN`
- `BVC_BOT_CLIENT_SECRET`
- `SMTSHEET_TOKEN`
- `STORAGE_CONNECTION_STRING` (optional)
- `FUNCTION_KEY` (optional)
- `TENANT_ID` (optional)
- `CLIENT_ID` (optional)
- `CLIENT_SECRET` (optional)

### 8. Test Deployment
```bash
# Make a small change
echo "# Test deployment" >> README.md
git add .
git commit -m "Test deployment"
git push
```

### 9. Monitor Deployment
- Go to your GitHub repository → Actions tab
- You should see the deployment workflow running
- Check the logs for any errors

## Troubleshooting

### Workflow Fails to Start
- Check that the workflow file is in `.github/workflows/`
- Verify the function app name is correct
- Ensure the publish profile secret is set

### Deployment Fails
- Check Azure Function App logs
- Verify environment variables are set
- Check GitHub Actions logs for specific errors

### Function Not Working After Deployment
- Run the health check: `GET /api/main?code=<function-key>`
- Check function logs in Azure Portal
- Verify all environment variables are set correctly

## Useful Commands

### Check Function Status
```bash
# Health check
curl -X GET "https://YOUR_FUNCTION_APP.azurewebsites.net/api/main?code=YOUR_FUNCTION_KEY"

# Test webhook
curl -X POST "https://YOUR_FUNCTION_APP.azurewebsites.net/api/main?code=YOUR_FUNCTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{"eventType":"ROW_UPDATED","objectId":123456789,"row":{"id":987654321,"cells":[{"columnId":"593432251944836","value":"Closed Won"}]}}'
```

### View Function Logs
```bash
# Using Azure CLI
az webapp log tail --name YOUR_FUNCTION_APP --resource-group YOUR_RESOURCE_GROUP
```

### Redeploy Manually
```bash
# Force push to trigger deployment
git commit --allow-empty -m "Force redeploy"
git push
``` 