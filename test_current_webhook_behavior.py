#!/usr/bin/env python3
"""
Test script to analyze current webhook behavior and identify why it's triggering repeatedly.
"""

import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import requests

def main():
    """Test current webhook behavior to understand the repeated triggers."""
    load_dotenv()
    
    # Get current timestamp
    current_time = datetime.utcnow().isoformat() + "Z"
    
    # Create a webhook payload with current timestamp
    webhook_payload = {
        "nonce": f"test-{int(time.time())}",
        "timestamp": current_time,
        "webhookId": 1783090705131396,
        "scope": "sheet",
        "scopeObjectId": int(os.getenv("SMTSHEET_ID", "123456789")),
        "events": [
            {
                "objectType": "row",
                "eventType": "updated",
                "id": 123456789,
                "userId": 7140110736091012,
                "timestamp": current_time
            }
        ]
    }
    
    local_function_url = "http://localhost:7071/api/main"
    headers = {"Content-Type": "application/json"}
    
    print("=== Testing Current Webhook Behavior ===")
    print(f"Current time: {current_time}")
    print(f"Webhook signature: {webhook_payload['webhookId']}_{webhook_payload['nonce']}_{webhook_payload['timestamp']}")
    print()
    
    # Send webhook and analyze response
    print("--- Sending Webhook ---")
    print(f"Sending POST to {local_function_url} ...")
    
    try:
        response = requests.post(
            local_function_url, 
            headers=headers, 
            data=json.dumps(webhook_payload),
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"Response JSON: {json.dumps(response_data, indent=2)}")
            except:
                print("Response is not JSON")
        else:
            print(f"Error response: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")
    
    print()
    print("=== Analysis ===")
    print("Check the Azure Function logs to see:")
    print("1. If the webhook is being processed")
    print("2. If deduplication is working")
    print("3. What specific data is being extracted")
    print("4. Whether the row data indicates actual changes")
    print()
    print("Common issues:")
    print("- Webhook firing without actual row changes")
    print("- Missing deduplication logic")
    print("- Row data not indicating 'Closed Won' status")
    print("- Function not returning early after processing")


if __name__ == "__main__":
    main() 