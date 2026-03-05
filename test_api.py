"""
Simple API Test Script
Run this to test if the backend is working properly.
"""

import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Check ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_register():
    """Test user registration"""
    print("\n=== Testing Registration ===")
    data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    }
    try:
        response = requests.post(f"{BASE_URL}/register", json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code in [200, 201, 400]  # 400 if user exists
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_login():
    """Test user login"""
    print("\n=== Testing Login ===")
    data = {
        "email": "serge.wiseabijuru5@gmail.com",
        "password": "2008@abanaBEZA"
    }
    try:
        response = requests.post(f"{BASE_URL}/login", json=data)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {result}")
        
        if result.get('success'):
            token = result.get('data', {}).get('token')
            print(f"Login successful! Token: {token}")
            return token
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_leaderboard():
    """Test leaderboard"""
    print("\n=== Testing Leaderboard ===")
    try:
        response = requests.get(f"{BASE_URL}/leaderboard?limit=10")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_admin_stats():
    """Test admin stats"""
    print("\n=== Testing Admin Stats ===")
    # First login as admin
    login_data = {
        "email": "serge.wiseabijuru5@gmail.com",
        "password": "2008@abanaBEZA"
    }
    try:
        login_response = requests.post(f"{BASE_URL}/login", json=login_data)
        if login_response.json().get('success'):
            token = login_response.json().get('data', {}).get('token')
            headers = {'Authorization': f'Bearer {token}'}
            
            response = requests.get(f"{BASE_URL}/admin/stats", headers=headers)
            print(f"Status: {response.status_code}")
            result = response.json()
            print(f"Response: {result}")
            
            if result.get('success'):
                api_keys = result.get('data', {}).get('api_keys', {})
                print(f"API Keys Configured: {api_keys.get('configured', 0)}")
                return True
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("FIFA Stats API Test")
    print("=" * 50)
    
    # Test endpoints
    health_ok = test_health()
    register_ok = test_register()
    leaderboard_ok = test_leaderboard()
    admin_ok = test_admin_stats()
    
    print("\n" + "=" * 50)
    print("TEST RESULTS")
    print("=" * 50)
    print(f"Health Check: {'✓ PASS' if health_ok else '✗ FAIL'}")
    print(f"Registration: {'✓ PASS' if register_ok else '✗ FAIL'}")
    print(f"Leaderboard: {'✓ PASS' if leaderboard_ok else '✗ FAIL'}")
    print(f"Admin Stats: {'✓ PASS' if admin_ok else '✗ FAIL'}")
    print("=" * 50)
    
    if health_ok and leaderboard_ok and admin_ok:
        print("\n✓ Backend is working correctly!")
    else:
        print("\n✗ Some tests failed. Check if backend is running.")

