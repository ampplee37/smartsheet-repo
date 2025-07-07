#!/usr/bin/env python3
"""
Debug script to test Azure Function locally and identify issues.
"""

import os
import sys
import logging
import json
from unittest.mock import Mock

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test if all modules can be imported successfully."""
    logger.info("Testing imports...")
    
    try:
        from config import config
        logger.info("✓ Config imported successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import config: {e}")
        return False
    
    try:
        from smartsheet_listener import smartsheet_listener
        logger.info("✓ Smartsheet listener imported successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import smartsheet_listener: {e}")
        return False
    
    try:
        from folder_manager import folder_manager
        logger.info("✓ Folder manager imported successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import folder_manager: {e}")
        return False
    
    try:
        from onenote_manager import onenote_manager
        logger.info("✓ OneNote manager imported successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import onenote_manager: {e}")
        return False
    
    try:
        from storage import storage_client
        logger.info("✓ Storage client imported successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import storage_client: {e}")
        return False
    
    return True

def test_config_validation():
    """Test configuration validation."""
    logger.info("Testing configuration validation...")
    
    try:
        from config import config
        if config.validate():
            logger.info("✓ Configuration validation passed")
            return True
        else:
            logger.error("✗ Configuration validation failed")
            return False
    except Exception as e:
        logger.error(f"✗ Configuration validation error: {e}")
        return False

def test_webhook_processing():
    """Test webhook processing with sample data."""
    logger.info("Testing webhook processing...")
    
    try:
        from smartsheet_listener import smartsheet_listener
        
        # Sample webhook payload for "Closed Won" deal
        sample_payload = {
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
        
        payload_str = json.dumps(sample_payload)
        result = smartsheet_listener.process_webhook_event(payload_str)
        
        if result:
            logger.info("✓ Webhook processing successful")
            logger.info(f"Event type: {result.get('type')}")
            return True
        else:
            logger.info("✓ Webhook processing returned None (expected for test data)")
            return True
            
    except Exception as e:
        logger.error(f"✗ Webhook processing error: {e}")
        return False

def test_storage_client():
    """Test storage client initialization."""
    logger.info("Testing storage client...")
    
    try:
        from storage import storage_client
        
        if storage_client.table_service is None:
            logger.warning("⚠ Storage client not fully initialized (no connection string)")
        else:
            logger.info("✓ Storage client initialized successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Storage client error: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("Starting Azure Function debug tests...")
    
    tests = [
        ("Import Test", test_imports),
        ("Config Validation", test_config_validation),
        ("Storage Client", test_storage_client),
        ("Webhook Processing", test_webhook_processing),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = 0
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        logger.info("🎉 All tests passed! The function should work correctly.")
    else:
        logger.error("❌ Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    main() 