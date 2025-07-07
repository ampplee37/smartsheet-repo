# Operations Runbook

This runbook provides operational procedures for the BVC Smartsheet-SharePoint Automation system.

## Table of Contents

1. [System Overview](#system-overview)
2. [Monitoring](#monitoring)
3. [Troubleshooting](#troubleshooting)
4. [Maintenance](#maintenance)
5. [Emergency Procedures](#emergency-procedures)
6. [Upcoming Features](#upcoming-features)

## System Overview

### Architecture Components

- **Azure Function**: Main processing engine
- **Azure Storage Tables**: Project metadata (BVCSSProjects) and template mapping (TemplateMapping)
- **Microsoft Graph API**: SharePoint/OneNote operations
- **Smartsheet Webhook**: Event source
- **Application Insights**: Monitoring and logging
- **Microsoft Teams**: "Opportunities" team channel (coming soon)

### Data Flow

1. Smartsheet row updated → Project Type column change or Sales Stage → "Closed Won"
2. Webhook triggers Azure Function
3. Function extracts Project Type and other project data
4. Function queries BVCSSProjects for project metadata (SiteID, DriveID, JobFolderID, ParentFolderID, ProjectName, etc.)
5. Function uses ProjectType to query TemplateMapping for folder structure
6. Function creates/copies SharePoint folders using DriveID, JobFolderID, etc.
7. Function creates OneNote notebook in ParentFolderID if it doesn't exist, or adds a section if it does (using ProjectName)
8. Function creates OneNote page with structured table containing project data
9. Function logs results
10. **Future**: Function posts to Microsoft Teams "Opportunities" channel

### Current Features

#### ✅ Implemented
- SharePoint folder structure creation from templates
- OneNote notebook creation with " - Public" naming convention
- OneNote section and page creation with project data tables
- Retry logic for OneNote section creation (handles 403 provisioning delays)
- Comprehensive error handling and logging
- Health check endpoint

#### 🚧 Upcoming
- Microsoft Teams integration for "Opportunities" team channel
- Rich message formatting for Teams posts
- Automatic team notifications

## Monitoring

### Key Metrics

#### Azure Function
- **Execution Count**: Number of function invocations
- **Success Rate**: Percentage of successful executions
- **Duration**: Average execution time
- **Errors**: Number of failed executions

#### Storage
- **Table Operations**: Read/write operations on BVCSSProjects and TemplateMapping
- **Storage Usage**: Table storage consumption

#### Graph API
- **API Calls**: Number of Graph API requests
- **Error Rate**: Failed API calls percentage
- **Throttling**: Rate limit violations
- **403 Errors**: OneNote provisioning delays (automatically retried)

#### OneNote Operations
- **Notebook Creation**: Success/failure rates
- **Section Creation**: Success/failure rates with retry attempts
- **Page Creation**: Success/failure rates

### Monitoring Tools

#### Application Insights
```bash
# Access Application Insights
az monitor app-insights component show \
  --app bvc-automation-insights \
  --resource-group bvc-automation-rg
```

#### Function Logs
```bash
# View real-time logs
az webapp log tail \
  --name bvc-automation-function \
  --resource-group bvc-automation-rg

# Download logs
az webapp log download \
  --name bvc-automation-function \
  --resource-group bvc-automation-rg
```

#### Health Check
```bash
# Test function health
curl https://bvc-automation-function.azurewebsites.net/api/health
```

### Alerts Setup

#### Critical Alerts
- Function execution failures > 5 in 5 minutes
- Storage connection failures
- Graph API authentication errors
- Webhook validation failures
- OneNote creation failures > 3 in 5 minutes

#### Warning Alerts
- Function execution time > 30 seconds
- Template copy operation timeouts
- Missing project or template mappings
- 403 errors on OneNote operations (retry attempts)

## Troubleshooting

### Common Issues and Solutions

#### 1. Function Execution Failures

**Symptoms:**
- High error rate in Application Insights
- Failed webhook deliveries
- No folder/notebook creation

**Diagnosis:**
```bash
# Check function logs
az webapp log tail --name bvc-automation-function --resource-group bvc-automation-rg

# Check Application Insights
# Go to Azure Portal → Application Insights → Failures

# Test health endpoint
curl https://bvc-automation-function.azurewebsites.net/api/health
```

**Common Causes:**
- Invalid Azure AD credentials
- Missing environment variables
- Storage connection issues
- Graph API permission problems
- Missing or incorrect project metadata in BVCSSProjects
- Invalid bot refresh token for OneNote operations

**Solutions:**
1. Verify environment variables (especially bot authentication)
2. Check Azure AD app permissions
3. Validate storage connection string
4. Review Graph API permissions
5. Ensure BVCSSProjects and TemplateMapping tables are populated and correct
6. Refresh bot authentication tokens if expired

#### 2. OneNote Creation Failures

**Symptoms:**
- Notebooks not created
- Section creation errors
- Permission denied errors
- 403 errors

**Diagnosis:**
```bash
# Check OneNote permissions
# Verify ParentFolderID and SiteID in BVCSSProjects
# Review Graph API logs for 403 errors
```

**Solutions:**
1. Verify SharePoint site and parent folder IDs in BVCSSProjects
2. Check OneNote permissions
3. Ensure site has OneNote enabled
4. Review Graph API scopes
5. **403 Errors**: System automatically retries with exponential backoff
6. Check bot authentication (refresh token may be expired)

#### 3. Template Copy Failures

**Symptoms:**
- Folders not created in SharePoint
- Copy operation timeouts
- "Template not found" errors

**Diagnosis:**
```bash
# Check template mappings
python scripts/setup_template_mapping.py

# Check project metadata in BVCSSProjects
python setup_azure_table.py

# Verify SharePoint folder IDs
# Use Graph API to validate folder existence
```

**Solutions:**
1. Update template folder IDs in TemplateMapping
2. Update project metadata in BVCSSProjects
3. Verify SharePoint folder permissions
4. Check Graph API quota limits
5. Retry failed operations

#### 4. Webhook Issues

**Symptoms:**
- No function invocations
- 401/403 errors from Smartsheet
- Missing webhook events

**Diagnosis:**
```bash
# Test webhook endpoint
curl -X POST https://bvc-automation-function.azurewebsites.net/api/main \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Check function key
az functionapp function keys list \
  --name bvc-automation-function \
  --resource-group bvc-automation-rg \
  --function-name main
```

**Solutions:**
1. Verify webhook URL and function key
2. Check Smartsheet webhook configuration
3. Validate webhook signature
4. Test webhook manually

### Debugging Procedures

#### 1. Enable Detailed Logging

```bash
# Set log level to DEBUG
az functionapp config appsettings set \
  --name bvc-automation-function \
  --resource-group bvc-automation-rg \
  --settings WEBSITE_RUN_FROM_PACKAGE=1
```

#### 2. Test Individual Components

```bash
# Test configuration
curl https://bvc-automation-function.azurewebsites.net/api/health

# Test storage connection
python -c "
from src.storage import storage_client
print(storage_client.list_categories())
"

# Test Graph API
python -c "
from src.graph_client import graph_client
print(graph_client.get_access_token())
"

# Test OneNote operations
python -c "
from src.onenote_manager import OneNoteManager
onm = OneNoteManager()
print('OneNote manager initialized successfully')
"
```

#### 3. Manual Webhook Testing

```json
{
  "eventType": "ROW_UPDATED",
  "objectId": 123456789,
  "row": {
    "id": 987654321,
    "rowNumber": 1,
    "cells": [
      {
        "columnId": "project_type_column_id",
        "value": "Consulting Retainer"
      },
      {
        "columnId": "project_name_column_id",
        "value": "Test Project"
      },
      {
        "columnId": "sales_stage_column_id",
        "value": "Closed Won"
      }
    ]
  }
}
```

#### 4. OneNote Troubleshooting

**Check Notebook Naming:**
- All notebooks should be named `<Customer> - Public`
- Verify customer name extraction from Smartsheet data

**Check Retry Logic:**
- 403 errors are automatically retried with exponential backoff
- Monitor logs for retry attempts
- Check `MAX_RETRIES` and `RETRY_DELAY` in config

**Verify Bot Authentication:**
```bash
# Check bot refresh token
python -c "
from src.graph_client import graph_client
try:
    token = graph_client.get_delegated_access_token()
    print('Bot authentication successful')
except Exception as e:
    print(f'Bot authentication failed: {e}')
"
```

## Maintenance

### Regular Maintenance Tasks

#### Weekly
- Review Application Insights metrics
- Check error rates and performance
- Verify project and template mappings are current
- Review Azure AD app registration status
- Check OneNote operation success rates

#### Monthly
- Rotate Azure AD client secrets
- Update dependencies and security patches
- Review and clean up old logs
- Validate backup procedures
- Refresh bot authentication tokens if needed

#### Quarterly
- Review and update template folders and project metadata
- Audit Graph API usage and quotas
- Update documentation
- Conduct disaster recovery testing
- Review Teams integration requirements (when implemented)

### Backup Procedures

#### Project and Template Mappings
```bash
# Export project and template data
python -c "
from src.storage import storage_client
import json

categories = storage_client.list_categories()
data = {}
for category in categories:
    templates = storage_client.get_templates(category)
    data[category] = [{'name': t.row_key, 'id': t.template_folder_id} for t in templates]

with open('template_backup.json', 'w') as f:
    json.dump(data, f, indent=2)
"

# Export BVCSSProjects table (custom script required)
```

#### Configuration
```bash
# Export application settings
az functionapp config appsettings list \
  --name bvc-automation-function \
  --resource-group bvc-automation-rg \
  --output json > app_settings_backup.json
```

### Update Procedures

#### Code Updates
1. Test changes in development environment
2. Run full test suite
3. Deploy to staging environment
4. Validate functionality
5. Deploy to production
6. Monitor for issues

#### Configuration Updates
1. Update environment variables
2. Restart function app
3. Verify health check
4. Test webhook functionality

## Emergency Procedures

### System Outage Response

#### 1. Immediate Actions
1. Check Azure Function status
2. Verify storage account connectivity
3. Test webhook endpoint
4. Review recent logs for errors
5. Check OneNote operation status

#### 2. Communication
1. Notify stakeholders of outage
2. Provide status updates
3. Estimate recovery time
4. Document incident details

#### 3. Recovery Steps
1. Identify root cause
2. Apply fixes
3. Test functionality
4. Monitor for stability
5. Document lessons learned

### Data Recovery

#### Project and Template Mapping Recovery
```bash
# Restore from backup
python -c "
from src.storage import storage_client
import json

with open('template_backup.json', 'r') as f:
    data = json.load(f)

for category, templates in data.items():
    for template in templates:
        storage_client.add_template(
            category=category,
            template_name=template['name'],
            template_folder_id=template['id']
        )
"

# Restore BVCSSProjects table (custom script required)
```

#### Configuration Recovery
```bash
# Restore application settings
az functionapp config appsettings set \
  --name bvc-automation-function \
  --resource-group bvc-automation-rg \
  --settings @app_settings_backup.json
```

### Rollback Procedures

#### Function App Rollback
```bash
# Deploy previous version
func azure functionapp publish bvc-automation-function --force

# Or use Azure Portal to rollback to previous deployment
```

#### Configuration Rollback
```bash
# Restore previous settings
az functionapp config appsettings set \
  --name bvc-automation-function \
  --resource-group bvc-automation-rg \
  --settings @previous_settings.json
```

## Upcoming Features

### Microsoft Teams Integration

The system is being extended to include Microsoft Teams integration for the "Opportunities" team.

#### Planned Features
1. **Automatic Team Posts**: Post project information to the "Opportunities" channel
2. **Rich Message Formatting**: Include project details in formatted messages
3. **Team Notifications**: Automatic notifications to team members
4. **Same Data Source**: Use the same project data as OneNote pages

#### Required Setup
1. **Permissions**: Ensure app has `ChannelMessage.Send`, `Team.ReadBasic.All`
2. **Team Configuration**: Verify "Opportunities" team exists and is accessible
3. **Channel Setup**: Identify the target channel for posts
4. **Message Templates**: Design message formatting for project information

#### Implementation Notes
- Integration will follow the same retry patterns as OneNote operations
- Messages will include the same project data as OneNote page tables
- System will handle Teams API rate limits and errors
- Posts will be made after successful OneNote page creation

#### Monitoring Considerations
- Track Teams API call success rates
- Monitor message posting failures
- Alert on Teams integration errors
- Include Teams metrics in health checks

## Contact Information

### On-Call Team
- **Primary**: [Primary Contact]
- **Secondary**: [Secondary Contact]
- **Escalation**: [Escalation Contact]

### External Contacts
- **Azure Support**: [Azure Support Contact]
- **Smartsheet Support**: [Smartsheet Support Contact]
- **Microsoft Graph Support**: [Graph API Support]
- **Microsoft Teams Support**: [Teams API Support]

### Escalation Matrix
1. **Level 1**: On-call engineer (0-2 hours)
2. **Level 2**: Senior engineer (2-4 hours)
3. **Level 3**: System architect (4-8 hours)
4. **Level 4**: Management (8+ hours) 