# Azure Function Deployment Guide

## Overview
This guide helps you deploy and troubleshoot the BVC Smartsheet-SharePoint Automation Azure Function.

## Pre-deployment Checklist

### 1. Environment Variables
Ensure these environment variables are set in your Azure Function App:

**Required:**
- `BVC_ONENOTE_INGEST_BOT_ID` - Bot application ID
- `BVC_ONENOTE_INGEST_BOT_KEY` - Bot client secret
- `BVC_BOT_REFRESH_TOKEN` - Bot refresh token
- `BVC_BOT_CLIENT_SECRET` - Bot client secret
- `SMTSHEET_TOKEN` - Smartsheet API token

**Optional:**
- `STORAGE_CONNECTION_STRING` - Azure Storage connection string
- `FUNCTION_KEY` - Function key for webhook validation
- `TENANT_ID` - Azure AD tenant ID
- `CLIENT_ID` - Azure AD client ID
- `CLIENT_SECRET` - Azure AD client secret

### 2. Dependencies
All required dependencies are listed in `requirements.txt`:
- azure-functions==1.17.0
- azure-data-tables==12.4.4
- azure-identity==1.15.0
- msal==1.25.0
- smartsheet-python-sdk>=3.0.0
- python-dotenv==1.0.0
- tenacity>=8.0.0

## Deployment Steps

### 1. Deploy to Azure Functions
```bash
# Using Azure CLI
az functionapp deployment source config-zip \
  --resource-group <your-resource-group> \
  --name <your-function-app-name> \
  --src <path-to-zip-file>

# Or using VS Code Azure Functions extension
# Right-click on the function folder and select "Deploy to Function App"
```

### 2. Set Environment Variables
In Azure Portal:
1. Go to your Function App
2. Navigate to Configuration > Application settings
3. Add each environment variable from the checklist above

### 3. Test the Function
```bash
# Test health check endpoint
curl -X GET "https://<your-function-app>.azurewebsites.net/api/main?code=<function-key>"

# Test with sample webhook payload
curl -X POST "https://<your-function-app>.azurewebsites.net/api/main?code=<function-key>" \
  -H "Content-Type: application/json" \
  -d '{"eventType":"ROW_UPDATED","objectId":123456789,"row":{"id":987654321,"cells":[{"columnId":"593432251944836","value":"Closed Won"},{"columnId":"3408182019051396","value":"TEST_PROJECT_001"},{"columnId":"5878702367002500","value":"Complex Design Build"}]}}'
```

## Troubleshooting

### 1. Function Fails to Start
**Symptoms:** Function shows "Failed" status in logs

**Solutions:**
- Check environment variables are set correctly
- Verify all dependencies are installed
- Check function logs for import errors

**Debug Steps:**
```bash
# Run the debug script locally
python test_azure_function_debug.py
```

### 2. Import Errors
**Common Issues:**
- Missing dependencies
- Incorrect import paths
- Missing environment variables

**Solutions:**
- Ensure all packages in `requirements.txt` are installed
- Check that environment variables are set
- Verify import statements in code

### 3. Configuration Validation Fails
**Symptoms:** "Configuration validation failed" in logs

**Solutions:**
- Verify all required environment variables are set
- Check that values are correct (no extra spaces, quotes, etc.)
- Ensure Azure AD app permissions are configured

### 4. Storage Client Issues
**Symptoms:** "Table service not initialized" warnings

**Solutions:**
- Set `STORAGE_CONNECTION_STRING` environment variable
- Verify Azure Storage account exists and is accessible
- Check table permissions

### 5. Smartsheet Client Issues
**Symptoms:** "Smartsheet client not initialized" warnings

**Solutions:**
- Verify `SMTSHEET_TOKEN` is set correctly
- Check Smartsheet API permissions
- Ensure webhook is configured properly

## Monitoring and Logs

### 1. View Function Logs
In Azure Portal:
1. Go to your Function App
2. Navigate to Functions > main > Monitor
3. View recent executions and logs

### 2. Application Insights
If enabled, view detailed telemetry:
1. Go to Application Insights resource
2. Navigate to Logs
3. Query for function executions

### 3. Health Check Endpoint
Use the health check endpoint to verify function status:
```
GET https://<your-function-app>.azurewebsites.net/api/main?code=<function-key>
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-06T23:43:14Z",
  "components": {
    "configuration": "OK",
    "storage_client": "OK",
    "smartsheet_client": "OK"
  },
  "environment": {
    "python_version": "3.9.x",
    "azure_functions_version": "1.17.0"
  }
}
```

## Common Error Messages

### "Missing required configuration"
- Check that all required environment variables are set
- Verify no typos in variable names
- Ensure values are not empty

### "Failed to initialize table client"
- Set `STORAGE_CONNECTION_STRING` environment variable
- Verify Azure Storage account permissions

### "Smartsheet client not initialized"
- Set `SMTSHEET_TOKEN` environment variable
- Verify token is valid and has required permissions

### "Webhook signature validation failed"
- Set `FUNCTION_KEY` environment variable
- Verify webhook is configured with correct secret

## Support

If you continue to experience issues:
1. Run the debug script: `python test_azure_function_debug.py`
2. Check function logs in Azure Portal
3. Verify all environment variables are set correctly
4. Test with the health check endpoint
5. Review the troubleshooting steps above 