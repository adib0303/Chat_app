#!/usr/bin/env python3
"""
Simple test to verify the JSON protocol is working correctly.
This test simulates the send/receive protocol to identify any issues.
"""

import json
import io

def send_json_to_buffer(obj):
    """Simulate sending JSON to a buffer"""
    data = json.dumps(obj).encode('utf-8')
    length = f'{len(data):08d}'.encode('utf-8')
    return length + data

def recv_json_from_buffer(buffer):
    """Simulate receiving JSON from a buffer"""
    # Read 8 bytes for length
    length_bytes = buffer.read(8)
    if len(length_bytes) != 8:
        raise ConnectionError(f'Expected 8 bytes for length, got {len(length_bytes)}')
    
    try:
        length_str = length_bytes.decode('utf-8')
        print(f"DEBUG: Received length bytes: {repr(length_bytes)}, decoded: {repr(length_str)}")
        
        if len(length_str) != 8:
            raise ValueError(f"Length must be exactly 8 characters, got {len(length_str)}: {repr(length_str)}")
        
        if not length_str.isdigit():
            raise ValueError(f"Invalid length format (not all digits): {repr(length_str)}")
            
        length = int(length_str)
        if length < 0 or length > 1000000:
            raise ValueError(f"Invalid message length: {length}")
            
    except (UnicodeDecodeError, ValueError) as e:
        raise ConnectionError(f'Invalid message length received: {repr(length_bytes)} - {e}')
    
    # Read the data
    data = buffer.read(length)
    if len(data) != length:
        raise ConnectionError(f'Expected {length} bytes of data, got {len(data)}')
    
    try:
        return json.loads(data.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ConnectionError(f'Invalid JSON data received: {repr(data)} - {e}')

def test_protocol():
    """Test the protocol with various message types"""
    test_messages = [
        {'type': 'TEST', 'message': 'Hello'},
        {'type': 'PRIVATE_MESSAGE', 'to': 'user1', 'from': 'user2', 'msg': 'Test message'},
        {'type': 'GROUP_MESSAGE', 'group_name': 'test_group', 'from': 'user1', 'msg': 'Group test'},
        {'type': 'FRIEND_REQUEST', 'from': 'user1', 'to': 'user2'},
        {'type': 'LIST_RESPONSE', 'users': ['user1', 'user2', 'user3']},
    ]
    
    print("Testing JSON protocol...")
    
    for i, msg in enumerate(test_messages):
        print(f"\nTest {i+1}: {msg['type']}")
        try:
            # Simulate sending
            buffer_data = send_json_to_buffer(msg)
            print(f"  Sent: {len(buffer_data)} bytes")
            
            # Create a buffer to simulate network data
            buffer = io.BytesIO(buffer_data)
            
            # Simulate receiving
            received_msg = recv_json_from_buffer(buffer)
            print(f"  Received: {received_msg}")
            
            # Verify integrity
            if received_msg == msg:
                print("  ✅ SUCCESS: Message matches")
            else:
                print("  ❌ FAILURE: Message doesn't match")
                print(f"     Expected: {msg}")
                print(f"     Got:      {received_msg}")
                
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            
    print("\nProtocol test completed!")

if __name__ == "__main__":
    test_protocol()
