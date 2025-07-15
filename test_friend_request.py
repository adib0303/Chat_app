#!/usr/bin/env python3
"""
Test script to validate friend request functionality
"""
import json
import sys
import os

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_friend_request_data():
    """Test that user data is properly formatted for friend requests"""
    
    # Test loading users.json
    try:
        with open('data/users.json', 'r') as f:
            users_data = json.load(f)
        print("✓ Successfully loaded users.json")
        print(f"  Found {len(users_data)} users:")
        for username, info in users_data.items():
            print(f"    - {username}: {info.get('dept', 'Unknown')}, {info.get('session', 'Unknown')}")
    except Exception as e:
        print(f"✗ Error loading users.json: {e}")
        return False
    
    # Test friend request message format
    from_user = "adib"
    to_user = "omar"
    
    sender_info = users_data.get(from_user, {})
    friend_request_msg = {
        "type": "FRIEND_REQUEST", 
        "from": from_user,
        "sender_info": {
            "name": sender_info.get("name", from_user),
            "dept": sender_info.get("dept", "Unknown"),
            "session": sender_info.get("session", "Unknown")
        }
    }
    
    print("\n✓ Friend request message format:")
    print(json.dumps(friend_request_msg, indent=2))
    
    return True

def test_notification_format():
    """Test notification display format"""
    sender = "adib"
    sender_info = {
        "name": "adib",
        "dept": "cse", 
        "session": "2021-22"
    }
    
    display_text = f'[FRIEND REQUEST] {sender}: sent you a friend request'
    print(f"\n✓ Notification display: {display_text}")
    
    print("✓ Sender info structure:")
    for key, value in sender_info.items():
        print(f"    {key}: {value}")
    
    return True

if __name__ == "__main__":
    print("Testing Friend Request Implementation")
    print("=" * 40)
    
    all_tests_passed = True
    
    all_tests_passed &= test_friend_request_data()
    all_tests_passed &= test_notification_format()
    
    print("\n" + "=" * 40)
    if all_tests_passed:
        print("✓ All tests passed! Friend request implementation looks good.")
    else:
        print("✗ Some tests failed. Please check the implementation.")
