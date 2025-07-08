#!/usr/bin/env python3
"""
Test script for webhook processing with cell update events.
"""

import os
import sys
import json
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from smartsheet_listener import smartsheet_listener

# Load environment variables
load_dotenv()


def test_cell_update_webhook():
    """Test processing a cell update webhook for Sales Stage change."""
    print("\n🧪 Testing Cell Update Webhook Processing...")
    print("-" * 50)
    
    # Simulate the webhook payload from the logs
    webhook_payload = {
        "nonce": "dc732c34-6e32-410a-9bab-9de795e19626",
        "timestamp": "2025-07-08T17:03:33.038+00:00",
        "webhookId": 8105950432257924,
        "scope": "sheet",
        "scopeObjectId": 7060115601444740,
        "events": [
            {
                "objectType": "cell",
                "eventType": "updated",
                "rowId": 1979416990846852,
                "columnId": "593432251944836",  # Sales Stage column
                "userId": 7140110736091012,
                "timestamp": "2025-07-08T17:02:32.000+00:00"
            }
        ]
    }
    
    payload_str = json.dumps(webhook_payload)
    
    print(f"Webhook payload: {json.dumps(webhook_payload, indent=2)}")
    
    try:
        # Test the webhook processing
        result = smartsheet_listener.process_webhook_event(payload_str)
        
        if result:
            print(f"✅ Webhook processing successful!")
            print(f"Result type: {result.get('type')}")
            print(f"Project ID: {result.get('project_info', {}).get('project_id')}")
            print(f"Project Type: {result.get('project_info', {}).get('project_type')}")
            return True
        else:
            print("❌ Webhook processing returned None")
            return False
            
    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_extract_row_data():
    """Test the extract_row_data method specifically."""
    print("\n🔍 Testing extract_row_data Method...")
    print("-" * 50)
    
    # Simulate webhook data
    webhook_data = {
        "nonce": "test-nonce",
        "timestamp": "2025-07-08T17:03:33.038+00:00",
        "webhookId": 8105950432257924,
        "scope": "sheet",
        "scopeObjectId": 7060115601444740,
        "events": [
            {
                "objectType": "cell",
                "eventType": "updated",
                "rowId": 1979416990846852,
                "columnId": "593432251944836",  # Sales Stage column
                "userId": 7140110736091012,
                "timestamp": "2025-07-08T17:02:32.000+00:00"
            }
        ]
    }
    
    try:
        # Test extract_row_data
        row_data = smartsheet_listener.extract_row_data(webhook_data)
        
        if row_data:
            print(f"✅ extract_row_data successful!")
            print(f"Row ID: {row_data.get('row_id')}")
            print(f"Sheet ID: {row_data.get('sheet_id')}")
            print(f"Event type: {row_data.get('event_type')}")
            return True
        else:
            print("❌ extract_row_data returned None")
            return False
            
    except Exception as e:
        print(f"❌ Error in extract_row_data: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("🧪 Webhook Processing Test Suite")
    print("=" * 50)
    
    tests = [
        ("extract_row_data", test_extract_row_data),
        ("Cell Update Webhook", test_cell_update_webhook),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except KeyboardInterrupt:
            print("\n⚠️  Test interrupted by user")
            break
        except Exception as e:
            print(f"❌ Unexpected error in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Webhook processing is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")


if __name__ == "__main__":
    main() 