import requests
import sys
import time
import os

# Set API URLs
PRIMARY_API_URL = "http://172.16.16.13:8585/att/api/transactionReport/export/"
BACKUP_API_URL = "http://213.210.196.115:8585/att/api/transactionReport/export/"

# Set connection timeout settings
CONNECT_TIMEOUT = 10  # Shorter timeout for testing
READ_TIMEOUT = 20     # Shorter timeout for testing

# Authentication credentials
USERNAME = os.environ.get("BIOTIME_USERNAME", "raghad")
PASSWORD = os.environ.get("BIOTIME_PASSWORD", "A1111111")  # Default password for testing

def test_connection(url, username, password):
    print(f"\n=== Testing connection to {url} ===")
    
    # First try a simple connection to the server without authentication
    try:
        # Extract base URL (e.g., http://172.16.16.13:8585/)
        base_url_parts = url.split("/att/")
        base_url = base_url_parts[0] + "/" if len(base_url_parts) > 1 else url
        
        print(f"Testing basic server connection to {base_url}...")
        ping_response = requests.get(base_url, timeout=CONNECT_TIMEOUT)
        print(f"Server is reachable! Status code: {ping_response.status_code}")
    except requests.exceptions.ConnectTimeout:
        print(f"ERROR: Connection timed out when trying to reach {base_url}")
        print("The server might be down or not accepting connections.")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"ERROR: Connection error when trying to reach {base_url}")
        print(f"Details: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error when testing server connection: {e}")
        
    # Now try to authenticate
    try:
        # Create authentication URL
        auth_url = url.replace('/transactionReport/export/', '/login')
        
        print(f"\nTrying to authenticate at {auth_url}")
        print(f"Username: {username}")
        print(f"Password: {'*' * len(password)}")
        
        # Authentication data
        auth_data = {
            'username': username,
            'password': password
        }
        
        # Try authentication
        auth_start_time = time.time()
        auth_response = requests.post(
            auth_url,
            json=auth_data,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
        auth_end_time = time.time()
        auth_time = auth_end_time - auth_start_time
        
        print(f"Authentication response received in {auth_time:.2f} seconds")
        print(f"Status code: {auth_response.status_code}")
        
        if auth_response.status_code == 200:
            print("Authentication successful!")
            print(f"Response content: {auth_response.text[:200]}...")  # Show first 200 chars
            
            # Extract token and test data endpoint
            try:
                token_data = auth_response.json()
                if 'token' in token_data:
                    token = token_data['token']
                    print(f"\nObtained token: {token[:10]}...")  # Show first 10 chars
                    
                    # Test data endpoint
                    headers = {
                        'Authorization': f'Token {token}',
                        'Content-Type': 'application/json',
                        'Accept': 'text/csv'
                    }
                    
                    # Use a small date range and specific department for testing
                    params = {
                        'dept_id': 10,  # Adjust this as needed
                        'start_time': '2025-04-20',  # Recent date
                        'end_time': '2025-04-26'     # Today's date
                    }
                    
                    print(f"\nTesting data endpoint: {url}")
                    print(f"With parameters: {params}")
                    
                    data_start_time = time.time()
                    data_response = requests.get(
                        url,
                        headers=headers,
                        params=params,
                        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT * 2)  # Longer timeout for data
                    )
                    data_end_time = time.time()
                    data_time = data_end_time - data_start_time
                    
                    print(f"Data response received in {data_time:.2f} seconds")
                    print(f"Status code: {data_response.status_code}")
                    
                    if data_response.status_code == 200:
                        print("Data retrieval successful!")
                        content_sample = data_response.text[:200].replace('\n', '\\n')  # Format for display
                        print(f"Response content sample: {content_sample}...")
                        
                        # Save sample to file for inspection
                        with open("api_response_sample.txt", "wb") as f:
                            f.write(data_response.content[:4000])  # First 4KB
                        print("Saved first 4KB of response to api_response_sample.txt")
                        
                        return True
                    else:
                        print(f"Data retrieval failed with status code {data_response.status_code}")
                        print(f"Response: {data_response.text}")
                else:
                    print("Authentication response did not contain a token")
            except Exception as e:
                print(f"ERROR processing authentication response: {e}")
        else:
            print(f"Authentication failed with status code {auth_response.status_code}")
            print(f"Response: {auth_response.text}")
    
    except requests.exceptions.ConnectTimeout:
        print(f"ERROR: Connection timed out when trying to authenticate to {auth_url}")
    except requests.exceptions.ReadTimeout:
        print(f"ERROR: Read timeout when trying to authenticate to {auth_url}")
    except requests.exceptions.ConnectionError as e:
        print(f"ERROR: Connection error when trying to authenticate: {e}")
    except Exception as e:
        print(f"ERROR: Unexpected error when testing authentication: {e}")
    
    return False

def main():
    print("BioTime API Connection Tester")
    print("============================")
    
    # Test primary URL
    print("\nTesting PRIMARY URL:")
    primary_success = test_connection(PRIMARY_API_URL, USERNAME, PASSWORD)
    
    if not primary_success:
        # Test backup URL only if primary fails
        print("\n\nTesting BACKUP URL:")
        backup_success = test_connection(BACKUP_API_URL, USERNAME, PASSWORD)
        
        if backup_success:
            print("\n✅ Backup URL connection SUCCESSFUL!")
        else:
            print("\n❌ Both primary and backup URL connections FAILED!")
    else:
        print("\n✅ Primary URL connection SUCCESSFUL!")
    
    # Network diagnostic information
    print("\n\nDiagnostic Information:")
    print("----------------------")
    try:
        import socket
        print(f"Local hostname: {socket.gethostname()}")
        print(f"Local IP: {socket.gethostbyname(socket.gethostname())}")
    except:
        print("Could not determine local network information")
    
    # Parse URLs to get server addresses
    for url in [PRIMARY_API_URL, BACKUP_API_URL]:
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            hostname = parsed.netloc.split(':')[0]
            print(f"\nTrying to resolve {hostname}:")
            try:
                ip = socket.gethostbyname(hostname)
                print(f"  → Resolved to IP: {ip}")
            except socket.gaierror:
                print(f"  → Could not resolve hostname: {hostname}")
                
            # Try ping
            print(f"Ping test to {hostname}:")
            import subprocess
            result = subprocess.run(['ping', '-n', '3', hostname], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE, 
                                    text=True)
            print("\n".join("  " + line for line in result.stdout.split('\n')[:10]))
        except Exception as e:
            print(f"Error during network diagnostics for {url}: {e}")

if __name__ == "__main__":
    # Allow command line arguments to override defaults
    if len(sys.argv) >= 3:
        USERNAME = sys.argv[1]
        PASSWORD = sys.argv[2]
        
    main()