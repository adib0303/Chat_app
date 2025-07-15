"""
Debug utilities for the chat application.
Use these functions to help diagnose communication issues.
"""

import socket
import json

def debug_recv_json(sock):
    """Debug version of recv_json with extensive logging"""
    print("[DEBUG] Starting recv_json...")
    
    length_bytes = b''
    while len(length_bytes) < 8:
        try:
            print(f"[DEBUG] Reading length bytes, currently have: {len(length_bytes)}/8")
            more = sock.recv(8 - len(length_bytes))
            if not more:
                print("[DEBUG] Socket closed while reading length")
                raise ConnectionError('Socket closed')
            length_bytes += more
            print(f"[DEBUG] Received {len(more)} bytes: {repr(more)}")
        except socket.timeout:
            print("[DEBUG] Socket timeout while reading length")
            raise ConnectionError('Socket timeout while reading length')
        except socket.error as e:
            print(f"[DEBUG] Socket error while reading length: {e}")
            raise ConnectionError(f'Socket error while reading length: {e}')
    
    print(f"[DEBUG] Complete length bytes: {repr(length_bytes)}")
    
    try:
        # Decode and convert to integer with error handling
        length_str = length_bytes.decode('utf-8')
        print(f"[DEBUG] Decoded length string: {repr(length_str)}")
        
        if len(length_str) != 8:
            print(f"[DEBUG] Length string wrong size: {len(length_str)} != 8")
            raise ValueError(f"Length must be exactly 8 characters, got {len(length_str)}: {repr(length_str)}")
        
        if not length_str.isdigit():
            print(f"[DEBUG] Length string not all digits: {repr(length_str)}")
            raise ValueError(f"Invalid length format (not all digits): {repr(length_str)}")
            
        length = int(length_str)
        print(f"[DEBUG] Parsed length: {length}")
        
        if length < 0 or length > 1000000:
            print(f"[DEBUG] Length out of range: {length}")
            raise ValueError(f"Invalid message length: {length}")
            
    except (UnicodeDecodeError, ValueError) as e:
        print(f"[DEBUG] Error parsing length: {e}")
        raise ConnectionError(f'Invalid message length received: {repr(length_bytes)} - {e}')
    
    print(f"[DEBUG] Now reading {length} bytes of data...")
    data = debug_recv_full(sock, length)
    
    try:
        json_data = json.loads(data.decode('utf-8'))
        print(f"[DEBUG] Successfully parsed JSON: {json_data}")
        return json_data
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"[DEBUG] Error parsing JSON: {e}")
        print(f"[DEBUG] Raw data: {repr(data)}")
        raise ConnectionError(f'Invalid JSON data received: {repr(data)} - {e}')

def debug_recv_full(sock, length):
    """Debug version of recv_full with extensive logging"""
    data = b''
    while len(data) < length:
        try:
            remaining = length - len(data)
            print(f"[DEBUG] Reading data, have {len(data)}/{length} bytes, need {remaining} more")
            more = sock.recv(remaining)
            if not more:
                print("[DEBUG] Socket closed while reading data")
                raise ConnectionError('Socket closed')
            data += more
            print(f"[DEBUG] Received {len(more)} bytes of data")
        except socket.timeout:
            print("[DEBUG] Socket timeout while reading data")
            raise ConnectionError('Socket timeout while reading data')
        except socket.error as e:
            print(f"[DEBUG] Socket error while reading data: {e}")
            raise ConnectionError(f'Socket error while reading data: {e}')
    
    print(f"[DEBUG] Complete data received: {len(data)} bytes")
    return data

def debug_send_json(sock, obj):
    """Debug version of send_json with extensive logging"""
    print(f"[DEBUG] Sending JSON: {obj}")
    
    data = json.dumps(obj).encode('utf-8')
    length = f'{len(data):08d}'.encode('utf-8')
    
    print(f"[DEBUG] Data length: {len(data)} bytes")
    print(f"[DEBUG] Length header: {repr(length)}")
    print(f"[DEBUG] Total sending: {len(length) + len(data)} bytes")
    
    try:
        sock.sendall(length + data)
        print(f"[DEBUG] Successfully sent message")
    except socket.error as e:
        print(f"[DEBUG] Error sending: {e}")
        raise

# Instructions for use:
"""
To use these debug functions, temporarily replace the normal functions in your code:

1. Replace recv_json with debug_recv_json
2. Replace send_json with debug_send_json

For example, in your listen_server method, change:
    message = recv_json(self.sock)
to:
    from debug_utils import debug_recv_json
    message = debug_recv_json(self.sock)

This will give you detailed logging to help identify where the protocol is failing.
"""
