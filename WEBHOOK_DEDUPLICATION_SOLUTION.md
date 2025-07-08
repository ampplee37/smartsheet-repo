# Webhook Deduplication Solution

## Problem
The Smartsheet webhook was firing repeatedly even when no changes were made to the sheet, causing:
- Multiple OneNote pages to be created under the same section
- Unnecessary processing and resource usage
- Potential data inconsistencies

## Root Causes
1. **Smartsheet Webhook Behavior**: Smartsheet webhooks can fire multiple times for the same event
2. **No Deduplication**: The system had no mechanism to prevent processing the same webhook multiple times
3. **Missing Change Detection**: The system wasn't properly checking if the row data had actually changed meaningfully

## Solution Overview

### 1. Webhook Deduplication
Implemented a two-tier deduplication system:

#### Azure Storage (Primary)
- Uses Azure Table Storage to track processed webhooks
- Persistent across function restarts
- Configurable TTL (Time-To-Live) for webhook records
- Table: `WebhookDeduplication`

#### In-Memory Cache (Fallback)
- Local cache for when Azure Storage is unavailable
- 5-minute TTL for webhook records
- Prevents duplicates within the same function instance

### 2. Change Detection
Added logic to check if row changes are meaningful:
- Only processes rows with "Closed Won" sales stage
- Validates required project data (Opportunity ID, Project Category)
- Prevents processing of irrelevant changes

### 3. Early Return Logic
Enhanced the webhook processing to return early when:
- Webhook is a duplicate
- Row changes are not meaningful
- Required data is missing

## Implementation Details

### Storage Manager (`src/storage.py`)
```python
class StorageManager:
    def is_webhook_processed(self, webhook_signature: str, ttl_minutes: int = 30) -> bool
    def mark_webhook_processed(self, webhook_signature: str) -> bool
    def cleanup_expired_webhooks(self, ttl_minutes: int = 60) -> int
```

### Smartsheet Listener (`src/smartsheet_listener.py`)
```python
class SmartsheetListener:
    def _is_duplicate_webhook(self, webhook_data: Dict[str, Any]) -> bool
    def _has_row_actually_changed(self, row_data: Dict[str, Any]) -> bool
```

### Webhook Signature
Unique identifier created from:
- `webhook_id`
- `nonce`
- `timestamp`

Format: `{webhook_id}_{nonce}_{timestamp}`

## Configuration

### Environment Variables
```bash
# Azure Storage (for persistent deduplication)
STORAGE_CONNECTION_STRING=your_azure_storage_connection_string

# Smartsheet
SMTSHEET_TOKEN=your_smartsheet_token
SMTSHEET_ID=your_smartsheet_id
```

### TTL Settings
- **Storage TTL**: 30 minutes (configurable)
- **Memory TTL**: 5 minutes (configurable)
- **Cleanup TTL**: 60 minutes (for expired record cleanup)

## Testing

### Test Scripts
1. **`test_webhook_deduplication.py`**: Tests deduplication with multiple identical webhooks
2. **`test_current_webhook_behavior.py`**: Analyzes current webhook behavior

### Expected Behavior
- **First webhook**: Processed normally
- **Subsequent identical webhooks**: Detected as duplicates and skipped
- **Log messages**: Clear indication of deduplication working

## Monitoring

### Log Messages to Watch For
```
INFO: Webhook {signature} marked as processed
WARNING: Duplicate webhook detected in storage: {signature}
WARNING: Duplicate webhook detected in memory: {signature}
INFO: Row has not changed meaningfully, skipping processing
```

### Azure Table Storage
Monitor the `WebhookDeduplication` table for:
- Number of processed webhooks
- Expired records (should be cleaned up automatically)
- Storage usage

## Deployment Steps

1. **Update Code**: Deploy the updated `smartsheet_listener.py` and `storage.py`
2. **Configure Storage**: Ensure `STORAGE_CONNECTION_STRING` is set
3. **Test**: Run the test scripts to verify deduplication
4. **Monitor**: Watch logs for deduplication messages
5. **Cleanup**: Monitor and clean up expired webhook records

## Troubleshooting

### Common Issues

1. **Storage Not Available**
   - System falls back to in-memory cache
   - Check `STORAGE_CONNECTION_STRING` configuration
   - Verify Azure Storage permissions

2. **Webhooks Still Processing**
   - Check if webhook signature is unique
   - Verify TTL settings are appropriate
   - Check logs for deduplication messages

3. **False Positives**
   - Adjust TTL settings if needed
   - Review change detection logic
   - Check column IDs for sales stage and project data

### Debug Commands
```bash
# Test deduplication
python test_webhook_deduplication.py

# Analyze current behavior
python test_current_webhook_behavior.py

# Check Azure Function logs
func azure functionapp logstream your-function-app-name
```

## Benefits

1. **Prevents Duplicate Processing**: Eliminates multiple OneNote page creation
2. **Reduces Resource Usage**: Avoids unnecessary API calls and processing
3. **Improves Reliability**: Consistent behavior across function restarts
4. **Better Monitoring**: Clear logging of webhook processing status
5. **Configurable**: Adjustable TTL and storage options

## Future Enhancements

1. **Metrics**: Add webhook processing metrics and alerts
2. **Advanced Filtering**: More sophisticated change detection
3. **Webhook Validation**: Enhanced webhook signature validation
4. **Performance Optimization**: Batch processing for multiple webhooks 