"""
Test script for Portfolio Bot API
Run this to test the API endpoints
"""

import requests
import json
import time

API_BASE = "http://localhost:5000/api"

def test_health():
    """Test health check endpoint"""
    print("Testing health check...")
    response = requests.get(f"{API_BASE}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    return response.status_code == 200

def test_chat(message, session_id=None):
    """Test chat endpoint"""
    print(f"Sending message: {message}")
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    
    response = requests.post(f"{API_BASE}/chat", json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}\n")
    return data

def test_get_session(session_id):
    """Test get session endpoint"""
    print(f"Getting session: {session_id}")
    response = requests.get(f"{API_BASE}/session/{session_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

def test_delete_session(session_id):
    """Test delete session endpoint"""
    print(f"Deleting session: {session_id}")
    response = requests.delete(f"{API_BASE}/session/{session_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

def test_info():
    """Test bot info endpoint"""
    print("Getting bot info...")
    response = requests.get(f"{API_BASE}/info")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

def run_full_test():
    """Run a full test of the API"""
    print("=" * 50)
    print("Portfolio Bot API Test")
    print("=" * 50 + "\n")
    
    # Test health
    if not test_health():
        print("Health check failed. Is the server running?")
        return
    
    time.sleep(1)
    
    # Test bot info
    test_info()
    time.sleep(1)
    
    # Test chat conversation
    print("Starting a conversation...\n")
    
    # First message
    result1 = test_chat("Hello! What is your background?")
    session_id = result1.get("session_id")
    time.sleep(2)
    
    # Second message in same session
    test_chat("What are your main skills?", session_id)
    time.sleep(2)
    
    # Third message in same session
    test_chat("Can you tell me about your experience?", session_id)
    time.sleep(2)
    
    # Get session history
    test_get_session(session_id)
    time.sleep(1)
    
    # Delete session
    test_delete_session(session_id)
    time.sleep(1)
    
    # Try to get deleted session (should fail)
    print("Trying to get deleted session (should fail)...")
    test_get_session(session_id)
    
    print("=" * 50)
    print("Test completed!")
    print("=" * 50)

if __name__ == "__main__":
    try:
        run_full_test()
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to API.")
        print("Make sure the server is running:")
        print("  python app.py")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
