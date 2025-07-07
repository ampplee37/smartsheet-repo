#!/usr/bin/env python3
"""
Test script for delegated authentication and OneNote operations.
"""

import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from graph_client import graph_client
from config import config

# Load environment variables
load_dotenv()

def test_delegated_authentication():
    """Test delegated authentication."""
    print("🔐 Testing Delegated Authentication...")
    
    try:
        # Test getting a delegated access token
        token = graph_client.get_delegated_access_token()
        print(f"✅ Successfully obtained delegated access token: {token[:50]}...")
        
        # Test a simple Graph API call with delegated auth
        response = graph_client.graph_request_delegated("GET", "/me")
        print(f"✅ Delegated auth test successful - User: {response.get('displayName', 'Unknown')}")
        
        return True
    except Exception as e:
        print(f"❌ Delegated authentication failed: {e}")
        return False

def test_onenote_operations():
    """Test OneNote operations with delegated auth."""
    print("\n📓 Testing OneNote Operations with Delegated Auth...")
    
    try:
        # Test getting user notebooks
        notebooks = graph_client.get_user_notebooks_delegated()
        print(f"✅ Found {len(notebooks.get('value', []))} OneNote notebooks with delegated auth")
        
        # Test creating a notebook (if needed)
        test_notebook_name = "Test Notebook - Delegated Auth"
        notebook = graph_client.create_notebook_delegated(test_notebook_name)
        notebook_id = notebook.get('id')
        print(f"✅ Created test notebook: {test_notebook_name}")
        
        # Test creating a section
        test_section_name = "Test Section"
        section = graph_client.create_notebook_section_delegated(notebook_id, test_section_name)
        print(f"✅ Created test section: {test_section_name}")
        
        return True
    except Exception as e:
        print(f"❌ OneNote operations failed: {e}")
        return False

def test_site_onenote_operations():
    """Test site-specific OneNote operations."""
    print("\n🏢 Testing Site OneNote Operations...")
    
    try:
        # Use the site ID from your config
        site_id = config.SHAREPOINT_SITE_ID
        print(f"Testing with site ID: {site_id}")
        
        # Test getting site notebooks
        notebooks = graph_client.get_site_notebooks(site_id)
        print(f"✅ Found {len(notebooks.get('value', []))} notebooks in site")
        
        return True
    except Exception as e:
        print(f"❌ Site OneNote operations failed: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Testing Delegated Authentication for OneNote")
    print("=" * 50)
    
    # Check configuration
    if not config.validate():
        print("❌ Configuration validation failed")
        return 1
    
    print("✅ Configuration validated")
    
    # Test delegated authentication
    if not test_delegated_authentication():
        return 1
    
    # Test OneNote operations
    if not test_onenote_operations():
        return 1
    
    # Test site OneNote operations
    if not test_site_onenote_operations():
        return 1
    
    print("\n🎉 All tests passed! Delegated authentication is working correctly.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
