#!/usr/bin/env python3
"""
Test script to debug webhook processing and cell event handling.
"""

import json
import logging
from datetime import datetime, timezone
from src.smartsheet_listener import smartsheet_listener

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_webhook_processing():
    """Test webhook processing with a sample payload."""
    
    # Sample webhook payload based on the logs
    sample_payload = {
        "webhookId": 8105950432257924,
        "nonce": "test-nonce-" + str(int(datetime.now(timezone.utc).timestamp())),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scopeObjectId": 123456789,  # Replace with actual sheet ID
        "events": [
            {
                "objectType": "cell",
                "eventType": "updated",
                "rowId": 987654321,  # Replace with actual row ID
                "columnId": 593432251944836,  # Sales Stage column
                "value": "Closed Won"
            }
        ]
    }
    
    payload_str = json.dumps(sample_payload)
    
    logger.info("Testing webhook processing...")
    logger.info(f"Sample payload: {payload_str}")
    
    # Process the webhook
    result = smartsheet_listener.process_webhook_event(payload_str)
    
    logger.info(f"Processing result: {result}")
    
    if result:
        logger.info(f"Event type: {result.get('type')}")
        logger.info(f"Project info: {result.get('project_info', {})}")
    else:
        logger.warning("No result returned from webhook processing")

if __name__ == "__main__":
    test_webhook_processing() 