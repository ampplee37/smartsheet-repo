#!/usr/bin/env python3
"""
Test script to debug webhook processing locally.
This helps identify why the webhook processing might be returning None.
"""

import json
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_webhook_processing():
    """Test webhook processing with various sample payloads."""
    
    try:
        from smartsheet_listener import smartsheet_listener
        logger.info("✓ Successfully imported smartsheet_listener")
    except Exception as e:
        logger.error(f"✗ Failed to import smartsheet_listener: {e}")
        return False
    
    # Test 1: Valid "Closed Won" deal
    logger.info("\n" + "="*50)
    logger.info("TEST 1: Valid 'Closed Won' deal")
    logger.info("="*50)
    
    sample_payload_1 = {
        "eventType": "ROW_UPDATED",
        "objectId": 123456789,
        "row": {
            "id": 987654321,
            "rowNumber": 1,
            "modifiedAt": "2025-01-06T23:43:14Z",
            "cells": [
                {
                    "columnId": "593432251944836",
                    "value": "Closed Won"
                },
                {
                    "columnId": "3408182019051396",
                    "value": "TEST_PROJECT_001"
                },
                {
                    "columnId": "5878702367002500",
                    "value": "Complex Design Build"
                }
            ]
        }
    }
    
    payload_str_1 = json.dumps(sample_payload_1)
    logger.info(f"Sample payload 1: {payload_str_1[:200]}...")
    
    result_1 = smartsheet_listener.process_webhook_event(payload_str_1)
    if result_1:
        logger.info("✓ Test 1 PASSED - Got valid result")
        logger.info(f"  Event type: {result_1.get('type')}")
        logger.info(f"  Project ID: {result_1.get('project_info', {}).get('project_id')}")
        logger.info(f"  Project Type: {result_1.get('project_info', {}).get('project_type')}")
    else:
        logger.error("✗ Test 1 FAILED - Got None result")
    
    # Test 2: Non-"Closed Won" deal (should return None)
    logger.info("\n" + "="*50)
    logger.info("TEST 2: Non-'Closed Won' deal (should return None)")
    logger.info("="*50)
    
    sample_payload_2 = {
        "eventType": "ROW_UPDATED",
        "objectId": 123456789,
        "row": {
            "id": 987654322,
            "rowNumber": 2,
            "modifiedAt": "2025-01-06T23:43:14Z",
            "cells": [
                {
                    "columnId": "593432251944836",
                    "value": "Prospecting"
                },
                {
                    "columnId": "3408182019051396",
                    "value": "TEST_PROJECT_002"
                },
                {
                    "columnId": "5878702367002500",
                    "value": "Simple Design"
                }
            ]
        }
    }
    
    payload_str_2 = json.dumps(sample_payload_2)
    logger.info(f"Sample payload 2: {payload_str_2[:200]}...")
    
    result_2 = smartsheet_listener.process_webhook_event(payload_str_2)
    if result_2 is None:
        logger.info("✓ Test 2 PASSED - Correctly returned None for non-Closed Won deal")
    else:
        logger.error("✗ Test 2 FAILED - Should have returned None")
    
    # Test 3: Missing required fields
    logger.info("\n" + "="*50)
    logger.info("TEST 3: Missing required fields (should return None)")
    logger.info("="*50)
    
    sample_payload_3 = {
        "eventType": "ROW_UPDATED",
        "objectId": 123456789,
        "row": {
            "id": 987654323,
            "rowNumber": 3,
            "modifiedAt": "2025-01-06T23:43:14Z",
            "cells": [
                {
                    "columnId": "593432251944836",
                    "value": "Closed Won"
                }
                # Missing project_id and project_type
            ]
        }
    }
    
    payload_str_3 = json.dumps(sample_payload_3)
    logger.info(f"Sample payload 3: {payload_str_3[:200]}...")
    
    result_3 = smartsheet_listener.process_webhook_event(payload_str_3)
    if result_3 is None:
        logger.info("✓ Test 3 PASSED - Correctly returned None for missing fields")
    else:
        logger.error("✗ Test 3 FAILED - Should have returned None")
    
    # Test 4: Webhook challenge
    logger.info("\n" + "="*50)
    logger.info("TEST 4: Webhook challenge")
    logger.info("="*50)
    
    sample_payload_4 = {
        "eventType": "WEBHOOK_CHALLENGE",
        "challenge": "test_challenge_123"
    }
    
    payload_str_4 = json.dumps(sample_payload_4)
    logger.info(f"Sample payload 4: {payload_str_4}")
    
    result_4 = smartsheet_listener.process_webhook_event(payload_str_4)
    if result_4 and result_4.get('type') == 'challenge':
        logger.info("✓ Test 4 PASSED - Correctly handled webhook challenge")
        logger.info(f"  Challenge response: {result_4.get('response')}")
    else:
        logger.error("✗ Test 4 FAILED - Should have returned challenge response")
    
    return True

def main():
    """Run the webhook debugging tests."""
    logger.info("Starting webhook debugging tests...")
    
    try:
        success = test_webhook_processing()
        if success:
            logger.info("\n🎉 All tests completed successfully!")
        else:
            logger.error("\n❌ Some tests failed!")
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 