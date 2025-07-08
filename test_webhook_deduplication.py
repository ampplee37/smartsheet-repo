#!/usr/bin/env python3
"""
Test script for webhook deduplication functionality.
This script simulates multiple webhook calls to verify deduplication is working.
"""

import os
import json
import time
from dotenv import load_dotenv
import requests

def main():
    """Test webhook deduplication by sending multiple identical webhooks."""
    load_dotenv()
    
    # Test webhook payload (same as the one that was causing issues)
    webhook_payload = {
        "nonce": "test-dedup-123",
        "timestamp": "2025-01-27T15:17:54.826+00:00",
        "webhookId": 1783090705131396,
        "scope": "sheet",
        "scopeObjectId": int(os.getenv("SMTSHEET_ID", "123456789")),
        "events": [
            {
                "objectType": "row",
                "eventType": "updated",
                "id": 123456789,
                "userId": 7140110736091012,
                "timestamp": "2025-01-27T15:16:54.000+00:00"
            }
        ]
    }
    
    local_function_url = "http://localhost:7071/api/main"
    headers = {"Content-Type": "application/json"}
    
    print("=== Testing Webhook Deduplication ===")
    print(f"Webhook signature: {webhook_payload['webhookId']}_{webhook_payload['nonce']}_{webhook_payload['timestamp']}")
    print()
    
    # Send the same webhook multiple times
    for i in range(5):
        print(f"--- Attempt {i+1} ---")
        print(f"Sending POST to {local_function_url} ...")
        
        try:
            response = requests.post(
                local_function_url, 
                headers=headers, 
                data=json.dumps(webhook_payload),
                timeout=30
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text[:500]}...")  # Truncate long responses
            
            if response.status_code == 200:
                response_data = response.json()
                if "duplicate" in response.text.lower() or "already processed" in response.text.lower():
                    print("✅ Deduplication working: Webhook was detected as duplicate")
                else:
                    print("⚠️  Webhook processed (may be first time or deduplication not working)")
            else:
                print(f"❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
        
        print()
        
        # Wait a bit between requests
        if i < 4:  # Don't wait after the last request
            print("Waiting 2 seconds before next attempt...")
            time.sleep(2)
    
    print("=== Test Complete ===")
    print("Expected behavior:")
    print("- First webhook: Should be processed normally")
    print("- Subsequent webhooks: Should be detected as duplicates and skipped")
    print("- Check the function logs to see deduplication messages")


if __name__ == "__main__":
    main() 