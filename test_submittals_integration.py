#!/usr/bin/env python3
"""
Test script for Submittals folder integration.
Tests the functionality to find Submittals folders and update Smartsheet with URLs.
"""

import os
import sys
from typing import Dict, Any
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from folder_manager import folder_manager
from smartsheet_updater import smartsheet_updater
from graph_client import graph_client

# Load environment variables
load_dotenv()


def test_find_submittals_folder():
    """Test finding a Submittals folder in a SharePoint location."""
    print("\n🔍 Testing Submittals Folder Finding...")
    print("-" * 40)
    
    # You'll need to provide actual values for testing
    drive_id = input("Enter SharePoint Drive ID: ").strip()
    parent_folder_id = input("Enter Parent Folder ID: ").strip()
    
    if not drive_id or not parent_folder_id:
        print("❌ Missing required parameters")
        return False
    
    try:
        # Test finding the Submittals folder
        submittals_folder = folder_manager.find_submittals_folder(drive_id, parent_folder_id)
        
        if submittals_folder:
            print(f"✅ Found Submittals folder: {submittals_folder.get('name')}")
            print(f"   ID: {submittals_folder.get('id')}")
            return True
        else:
            print("❌ No Submittals folder found")
            return False
            
    except Exception as e:
        print(f"❌ Error finding Submittals folder: {e}")
        return False


def test_get_submittals_folder_url():
    """Test getting the web URL for a Submittals folder."""
    print("\n🌐 Testing Submittals Folder URL Generation...")
    print("-" * 40)
    
    # You'll need to provide actual values for testing
    drive_id = input("Enter SharePoint Drive ID: ").strip()
    parent_folder_id = input("Enter Parent Folder ID: ").strip()
    
    if not drive_id or not parent_folder_id:
        print("❌ Missing required parameters")
        return False
    
    try:
        # Test getting the Submittals folder URL
        submittals_url = folder_manager.get_submittals_folder_url(drive_id, parent_folder_id)
        
        if submittals_url:
            print(f"✅ Got Submittals folder URL: {submittals_url}")
            return True
        else:
            print("❌ Could not get Submittals folder URL")
            return False
            
    except Exception as e:
        print(f"❌ Error getting Submittals folder URL: {e}")
        return False


def test_smartsheet_update():
    """Test updating Smartsheet with Submittals folder URL."""
    print("\n📊 Testing Smartsheet Update...")
    print("-" * 40)
    
    # You'll need to provide actual values for testing
    sheet_id = input("Enter Smartsheet Sheet ID: ").strip()
    row_id = input("Enter Smartsheet Row ID: ").strip()
    project_name = input("Enter Project Name: ").strip()
    folder_url = input("Enter Folder URL: ").strip()
    
    if not all([sheet_id, row_id, project_name, folder_url]):
        print("❌ Missing required parameters")
        return False
    
    try:
        # Test updating Smartsheet
        success = smartsheet_updater.update_submittals_folder_link(
            sheet_id=int(sheet_id),
            row_id=int(row_id),
            project_name=project_name,
            folder_url=folder_url
        )
        
        if success:
            print("✅ Successfully updated Smartsheet with Submittals folder URL")
            return True
        else:
            print("❌ Failed to update Smartsheet")
            return False
            
    except Exception as e:
        print(f"❌ Error updating Smartsheet: {e}")
        return False


def test_graph_api_sharing():
    """Test Graph API folder sharing functionality."""
    print("\n🔗 Testing Graph API Folder Sharing...")
    print("-" * 40)
    
    # You'll need to provide actual values for testing
    drive_id = input("Enter SharePoint Drive ID: ").strip()
    item_id = input("Enter Folder Item ID: ").strip()
    
    if not drive_id or not item_id:
        print("❌ Missing required parameters")
        return False
    
    try:
        # Test creating a sharing link
        share_response = graph_client.share_folder_with_anyone_link(drive_id, item_id)
        
        if share_response and 'link' in share_response:
            web_url = share_response['link'].get('webUrl')
            if web_url:
                print(f"✅ Created sharing link: {web_url}")
                return True
            else:
                print("❌ No web URL in sharing response")
                return False
        else:
            print("❌ Failed to create sharing link")
            return False
            
    except Exception as e:
        print(f"❌ Error creating sharing link: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Submittals Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Graph API Sharing", test_graph_api_sharing),
        ("Find Submittals Folder", test_find_submittals_folder),
        ("Get Submittals Folder URL", test_get_submittals_folder_url),
        ("Smartsheet Update", test_smartsheet_update),
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
        print("🎉 All tests passed! Submittals integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")


if __name__ == "__main__":
    main() 