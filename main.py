import requests
import time
import os
import sys
import signal
import select
import base64
import mimetypes
import math

SERVER_URL = 'https://franchiwebdesign.com/server/server.php'

exit_flag = False
current_mode = "public"
current_room_id = "lobby"
current_room_name = "Public Chat"
last_display_time = 0
refresh_interval = 3

# For file transfers
active_transfers = {}

# Color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
PURPLE = "\033[95m"
CYAN = "\033[96m"
RED = "\033[91m"
GRAY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"

def signal_handler(sig, frame):
    global exit_flag
    print(f"\n{YELLOW}Exiting... Goodbye!{RESET}")
    exit_flag = True
    sys.exit(0)

def format_file_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def check_room_deleted(room_id):
    try:
        response = requests.get(SERVER_URL + '?action=deleted_rooms', timeout=3)
        if response.status_code == 200:
            deleted_rooms = response.json()
            if isinstance(deleted_rooms, dict) and room_id in deleted_rooms:
                return True, deleted_rooms[room_id].get('deleted_at', time.time())
    except:
        pass
    
    try:
        response = requests.get(SERVER_URL + '?action=room_info&room_id=' + room_id, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'error':
                return True, time.time()
    except:
        pass
    
    return False, None

def send_message(sender, message, room_id=None):
    payload = {
        'action': 'send_message',
        'sender': sender,
        'message': message
    }
    
    if room_id and room_id != "lobby":
        payload['room_id'] = room_id
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(SERVER_URL, json=payload, headers=headers, timeout=5)

        if response.status_code == 200:
            try:
                response_data = response.json()
                if response_data.get('status') == 'success':
                    return True, response_data.get('type', 'public')
                else:
                    error_msg = response_data.get('message', 'Error sending message')
                    if 'Room has been deleted' in error_msg:
                        return False, 'room_deleted'
                    print(f"{RED}✗ {error_msg}{RESET}")
                    return False, 'error'
            except Exception as e:
                print(f"{RED}✗ Invalid server response{RESET}")
                return False, 'error'
        else:
            print(f"{RED}✗ Server error: {response.status_code}{RESET}")
            return False, 'error'
    except requests.exceptions.Timeout:
        print(f"{RED}✗ Connection timeout{RESET}")
        return False, 'error'
    except Exception as e:
        print(f"{RED}✗ Connection error: {str(e)}{RESET}")
        return False, 'error'

def get_user_rooms(username):
    try:
        response = requests.get(SERVER_URL + f'?action=user_rooms&username={username}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and data.get('status') == 'error':
                return []
            return data
        else:
            return []
    except:
        return []

def create_room(room_name, creator):
    payload = {
        'action': 'create_room',
        'room_name': room_name,
        'creator': creator
    }
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(SERVER_URL, json=payload, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return True, data.get('room_id'), data.get('message', 'Room created')
            else:
                error_msg = data.get('message', 'Failed to create room')
                print(f"{RED}✗ {error_msg}{RESET}")
                return False, None, error_msg
        else:
            error_msg = f"Server error: {response.status_code}"
            print(f"{RED}✗ {error_msg}{RESET}")
            return False, None, error_msg
    except requests.exceptions.Timeout:
        error_msg = "Connection timeout"
        print(f"{RED}✗ {error_msg}{RESET}")
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"{RED}✗ {error_msg}{RESET}")
        return False, None, error_msg

def join_room(room_id, username):
    payload = {
        'action': 'join_room',
        'room_id': room_id,
        'username': username
    }
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(SERVER_URL, json=payload, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return True, data
            else:
                error_msg = data.get('message', 'Failed to join room')
                if 'Room has been deleted' in error_msg:
                    return False, {'message': 'Room has been deleted by admin'}
                return False, {'message': error_msg}
        else:
            return False, {'message': f"Server error: {response.status_code}"}
    except requests.exceptions.Timeout:
        return False, {'message': "Connection timeout"}
    except Exception as e:
        return False, {'message': f"Error: {str(e)}"}

def leave_room(room_id, username):
    payload = {
        'action': 'leave_room',
        'room_id': room_id,
        'username': username
    }
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(SERVER_URL, json=payload, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return True, data.get('message', 'Left room')
            else:
                error_msg = data.get('message', 'Failed to leave room')
                return False, error_msg
        else:
            return False, f"Server error: {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Connection timeout"
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_room_info(room_id):
    try:
        response = requests.get(SERVER_URL + f'?action=room_info&room_id={room_id}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return True, data.get('room')
            else:
                error_msg = data.get('message', 'Room not found')
                return False, error_msg
        else:
            return False, f"Server error: {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Connection timeout"
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_room_messages(room_id):
    try:
        response = requests.get(SERVER_URL + f'?action=room_messages&room_id={room_id}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and data.get('status') == 'error':
                error_msg = data.get('message', 'System error')
                if 'maintenance' in error_msg.lower():
                    print(f"{YELLOW}⚠️ {error_msg}{RESET}")
                return []
            return data
        else:
            return []
    except requests.exceptions.Timeout:
        print(f"{RED}✗ Connection timeout{RESET}")
        return []
    except:
        return []

def get_private_messages(username):
    try:
        response = requests.get(SERVER_URL + f'?action=private_messages&user={username}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and data.get('status') == 'error':
                error_msg = data.get('message', 'System error')
                if 'maintenance' in error_msg.lower():
                    print(f"{YELLOW}⚠️ {error_msg}{RESET}")
                return []
            return data
        else:
            return []
    except requests.exceptions.Timeout:
        print(f"{RED}✗ Connection timeout{RESET}")
        return []
    except:
        return []

def login_or_signup():
    print("\n1. Login\n2. Signup")
    choice = input("Choose an option: ")
    
    if choice == '1':
        username = input("Enter username: ")
        password = input("Enter password: ")
        payload = {
            'action': 'login',
            'username': username,
            'password': password
        }
        
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(SERVER_URL, json=payload, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    print(f"{GREEN}✓ Welcome {username}!{RESET}")
                    time.sleep(1)
                    return username
                else:
                    error_msg = data.get('message', 'Login failed')
                    if 'maintenance' in error_msg.lower():
                        print(f"{YELLOW}⚠️ {error_msg}{RESET}")
                    else:
                        print(f"{RED}✗ {error_msg}{RESET}")
                    return None
            else:
                print(f"{RED}✗ Server error: {response.status_code}{RESET}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"{RED}✗ Connection timeout{RESET}")
            return None
        except Exception as e:
            print(f"{RED}✗ Connection failed: {str(e)}{RESET}")
            return None

    elif choice == '2':
        username = input("Enter username: ")
        password = input("Enter password: ")
        payload = {
            'action': 'signup',
            'username': username,
            'password': password
        }
        
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(SERVER_URL, json=payload, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    print(f"{GREEN}✓ Signup successful! Please login.{RESET}")
                    time.sleep(1)
                else:
                    error_msg = data.get('message', 'Signup failed')
                    if 'maintenance' in error_msg.lower():
                        print(f"{YELLOW}⚠️ {error_msg}{RESET}")
                    else:
                        print(f"{RED}✗ {error_msg}{RESET}")
            else:
                print(f"{RED}✗ Server error: {response.status_code}{RESET}")
        except requests.exceptions.Timeout:
            print(f"{RED}✗ Connection timeout{RESET}")
        except Exception as e:
            print(f"{RED}✗ Connection failed: {str(e)}{RESET}")
        return None

def get_messages():
    try:
        response = requests.get(SERVER_URL + '?action=messages', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and data.get('status') == 'error':
                error_msg = data.get('message', 'System error')
                if 'maintenance' in error_msg.lower():
                    print(f"{YELLOW}⚠️ {error_msg}{RESET}")
                return []
            return data
        else:
            print(f"{RED}✗ Error fetching messages: {response.status_code}{RESET}")
            return []
    except requests.exceptions.Timeout:
        print(f"{RED}✗ Connection timeout{RESET}")
        return []
    except Exception as e:
        print(f"{RED}✗ Connection error: {str(e)}{RESET}")
        return []

# ============================================
# FILE SHARING FUNCTIONS
# ============================================

def upload_file(sender, filepath, expire="24h", room_id=None, private_to=None):
    """Upload and share a file"""
    
    if not os.path.exists(filepath):
        print(f"{RED}✗ File not found: {filepath}{RESET}")
        return False
    
    # Check file size (max 100MB)
    file_size = os.path.getsize(filepath)
    if file_size > 100 * 1024 * 1024:
        print(f"{RED}✗ File too large. Max 100MB{RESET}")
        return False
    
    # Read file and encode to base64
    try:
        with open(filepath, 'rb') as f:
            file_content = f.read()
            file_b64 = base64.b64encode(file_content).decode('utf-8')
    except Exception as e:
        print(f"{RED}✗ Error reading file: {str(e)}{RESET}")
        return False
    
    filename = os.path.basename(filepath)
    
    # Show progress (simulated)
    print(f"{YELLOW}⬆️ Uploading {filename}...{RESET}")
    
    payload = {
        'action': 'upload_file',
        'sender': sender,
        'filename': filename,
        'filedata': file_b64,
        'filesize': file_size,
        'expire': expire
    }
    
    if room_id and room_id != "lobby":
        payload['room_id'] = room_id
    
    if private_to:
        payload['private_to'] = private_to
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(SERVER_URL, json=payload, headers=headers, timeout=30)  # Longer timeout for files
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                print(f"{GREEN}✓ File shared successfully! Code: {data.get('file_code')}{RESET}")
                return True
            else:
                print(f"{RED}✗ {data.get('message', 'Upload failed')}{RESET}")
                return False
        else:
            print(f"{RED}✗ Server error: {response.status_code}{RESET}")
            return False
    except requests.exceptions.Timeout:
        print(f"{RED}✗ Upload timeout{RESET}")
        return False
    except Exception as e:
        print(f"{RED}✗ Upload error: {str(e)}{RESET}")
        return False

def download_file(file_code, username):
    """Download a file by code"""
    
    print(f"{YELLOW}⬇️ Fetching file info...{RESET}")
    
    try:
        response = requests.get(SERVER_URL + f'?action=download_file&file_code={file_code}&username={username}', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'error':
                print(f"{RED}✗ {data.get('message', 'Download failed')}{RESET}")
                return False
            
            filename = data.get('filename', f"file_{file_code}")
            filesize = data.get('filesize', 0)
            filedata_b64 = data.get('filedata', '')
            
            # Decode
            file_content = base64.b64decode(filedata_b64)
            
            # Save to current directory
            save_path = os.path.join(os.getcwd(), filename)
            
            # If file exists, add number
            counter = 1
            original_filename = filename
            while os.path.exists(save_path):
                name, ext = os.path.splitext(original_filename)
                filename = f"{name}_{counter}{ext}"
                save_path = os.path.join(os.getcwd(), filename)
                counter += 1
            
            print(f"{YELLOW}⬇️ Downloading {filename} ({format_file_size(filesize)})...{RESET}")
            
            with open(save_path, 'wb') as f:
                f.write(file_content)
            
            print(f"{GREEN}✓ Downloaded to: {save_path}{RESET}")
            return True
            
        else:
            print(f"{RED}✗ Server error: {response.status_code}{RESET}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"{RED}✗ Download timeout{RESET}")
        return False
    except Exception as e:
        print(f"{RED}✗ Download error: {str(e)}{RESET}")
        return False

def list_files(username):
    """List all files user has access to"""
    
    try:
        response = requests.get(SERVER_URL + f'?action=list_files&username={username}', timeout=5)
        
        if response.status_code == 200:
            files = response.json()
            
            if not files:
                print(f"{GRAY}No files found.{RESET}")
                return
            
            print(f"\n{CYAN}════════════════════════════════════════════════════{RESET}")
            print(f"{YELLOW}SHARED FILES{RESET}")
            print(f"{CYAN}════════════════════════════════════════════════════{RESET}")
            
            current_time = time.time()
            
            for code, file in files.items():
                # Format expiration
                expires = file.get('expires')
                expire_text = ""
                if expires:
                    hours_left = round((expires - current_time) / 3600, 1)
                    if hours_left > 0:
                        expire_text = f" {GRAY}(expires in {hours_left}h){RESET}"
                    else:
                        expire_text = f" {RED}(expired){RESET}"
                
                # Format size
                size_text = format_file_size(file.get('size', 0))
                
                # Format time
                uploaded = time.strftime('%H:%M %m/%d', time.localtime(file.get('uploaded_at', 0)))
                
                # Who shared
                sender = file.get('sender', 'Unknown')
                
                # Location
                location = "Public"
                if file.get('room_id'):
                    location = f"Room: {file.get('room_id')}"
                elif file.get('private_to'):
                    location = f"Private to: {file.get('private_to')}"
                
                print(f"{GREEN}[{code}]{RESET} {file.get('original_filename', 'Unknown')}")
                print(f"  {GRAY}├─ Size: {size_text}{RESET}")
                print(f"  {GRAY}├─ From: {sender}{RESET}")
                print(f"  {GRAY}├─ Location: {location}{RESET}")
                print(f"  {GRAY}├─ Uploaded: {uploaded}{RESET}")
                print(f"  {GRAY}└─ Downloads: {file.get('downloads', 0)}{RESET}{expire_text}")
                print()
            
            print(f"{CYAN}════════════════════════════════════════════════════{RESET}")
            print(f"{GRAY}Use /get CODE to download a file{RESET}")
            
        else:
            print(f"{RED}✗ Failed to list files{RESET}")
            
    except Exception as e:
        print(f"{RED}✗ Error: {str(e)}{RESET}")

def unshare_file(file_code, username):
    """Delete a shared file"""
    
    payload = {
        'action': 'delete_file',
        'file_code': file_code,
        'username': username
    }
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(SERVER_URL, json=payload, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                print(f"{GREEN}✓ File deleted successfully{RESET}")
                return True
            else:
                print(f"{RED}✗ {data.get('message', 'Delete failed')}{RESET}")
                return False
        else:
            print(f"{RED}✗ Server error: {response.status_code}{RESET}")
            return False
    except Exception as e:
        print(f"{RED}✗ Error: {str(e)}{RESET}")
        return False

# ============================================
# NEW: HELP COMMAND FUNCTION
# ============================================

def show_help():
    """Display all available commands"""
    
    # Clear screen
    sys.stdout.write("\033[2J\033[H")
    
    print(f"{CYAN}╔════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║                    {YELLOW}AVAILABLE COMMANDS{RESET}{CYAN}                     ║{RESET}")
    print(f"{CYAN}╚════════════════════════════════════════════════════════════╝{RESET}\n")
    
    # BASIC NAVIGATION
    print(f"{YELLOW}━━━━━━━━━━━━━━━━━ BASIC NAVIGATION ━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{GREEN}/public{RESET}         - Switch to public chat")
    print(f"{GREEN}/private{RESET}        - Switch to private messages")
    print(f"{GREEN}!exit{RESET}           - Exit the chat application")
    print()
    
    # ROOM COMMANDS
    print(f"{YELLOW}━━━━━━━━━━━━━━━━━ ROOM MANAGEMENT ━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{GREEN}/create{RESET}         - Create a new room (you'll be asked for room name)")
    print(f"{GREEN}/join [ID]{RESET}      - Join a room by its 6-digit ID (e.g., /join ABC123)")
    print(f"{GREEN}/list{RESET}           - List all rooms you have joined")
    print(f"{GREEN}/leave{RESET}          - Leave the current room you're in")
    print()
    
    # PRIVATE MESSAGES
    print(f"{YELLOW}━━━━━━━━━━━━━━━━━ PRIVATE MESSAGES ━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{GREEN}@username{RESET}       - Send private message to a user")
    print(f"{GRAY}Example 1:{RESET} @john Kamusta ka na?")
    print(f"{GRAY}Example 2:{RESET} @john,@maria @jane Tara usap tayo")
    print(f"{GRAY}Note:{RESET} You can tag multiple users separated by commas")
    print()
    
    # FILE SHARING
    print(f"{YELLOW}━━━━━━━━━━━━━━━━━ FILE SHARING ━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{GREEN}/share [file]{RESET}   - Share a file (supports --expire option)")
    print(f"{GRAY}Examples:{RESET}")
    print(f"  {GRAY}•{RESET} /share photo.jpg")
    print(f"  {GRAY}•{RESET} /share video.mp4 --expire 2h")
    print(f"  {GRAY}•{RESET} /share @maria secret.pdf (private file)")
    print(f"{GREEN}/get [CODE]{RESET}     - Download a file using its 6-digit code")
    print(f"{GRAY}Example:{RESET} /get ABC123")
    print(f"{GREEN}/files{RESET}          - List all files you can access")
    print(f"{GREEN}/unshare [CODE]{RESET} - Delete/stop sharing your file")
    print(f"{GRAY}Example:{RESET} /unshare ABC123")
    print(f"{GRAY}Note:{RESET} Max file size: 100MB | Expiry: 1h-24h (default: 24h)")
    print()
    
    # OTHER COMMANDS
    print(f"{YELLOW}━━━━━━━━━━━━━━━━━ OTHER COMMANDS ━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{GREEN}/help{RESET} or {GREEN}/h{RESET} or {GREEN}/?{RESET} - Show this help screen")
    print()
    
    # SUMMARY TABLE
    print(f"{YELLOW}━━━━━━━━━━━━━━━━━ QUICK REFERENCE ━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{CYAN}Command                Description{RESET}")
    print(f"{GRAY}──────────────────────────────────────────────────{RESET}")
    print(f"{GREEN}/public                {GRAY}Switch to public chat{RESET}")
    print(f"{GREEN}/private               {GRAY}Switch to private messages{RESET}")
    print(f"{GREEN}/create                {GRAY}Create a new room{RESET}")
    print(f"{GREEN}/join ID               {GRAY}Join a room by ID{RESET}")
    print(f"{GREEN}/list                  {GRAY}List your rooms{RESET}")
    print(f"{GREEN}/leave                 {GRAY}Leave current room{RESET}")
    print(f"{GREEN}/share file             {GRAY}Share a file{RESET}")
    print(f"{GREEN}/get CODE              {GRAY}Download a file{RESET}")
    print(f"{GREEN}/files                 {GRAY}List shared files{RESET}")
    print(f"{GREEN}/unshare CODE          {GRAY}Delete shared file{RESET}")
    print(f"{GREEN}@user message          {GRAY}Send private message{RESET}")
    print(f"{GREEN}!exit                  {GRAY}Exit chat{RESET}")
    print(f"{GREEN}/help, /h, /?          {GRAY}Show this help{RESET}")
    
    print(f"\n{YELLOW}Press Enter to continue...{RESET}", end='', flush=True)
    input()
    
    # Clear screen after pressing Enter
    sys.stdout.write("\033[2J\033[H")

# ============================================
# DISPLAY FUNCTIONS (UPDATED WITH HELP COMMAND)
# ============================================

def display_public_chat(username, messages, show_prompt=True):
    global current_room_name
    
    # SMOOTH CLEAR - NO BLINK
    sys.stdout.write("\033[2J\033[H")
    
    print(f"{BLUE}="*50 + RESET)
    print(f"{YELLOW}PUBLIC CHAT - {current_room_name}{RESET}")
    print(f"{GRAY}Type '/private' for Private Messages | '/create' to create room{RESET}")
    print(f"{GRAY}Type '/share filename' to share file | '/files' to list files{RESET}")
    print(f"{GRAY}Type '/list' to view your rooms | '/help' for all commands{RESET}")
    print(f"{GRAY}Type '!exit' to exit{RESET}")
    print(f"{BLUE}="*50 + RESET + "\n")
    
    if not messages:
        print(f"{GRAY}No public messages yet. Start the conversation!{RESET}")
    else:
        for message in messages:
            timestamp = time.strftime('%H:%M', time.localtime(message.get('timestamp', 0)))
            if message['sender'] == username:
                print(f"{GREEN}[{timestamp}] You: {RESET}{message['message']}")
            elif message['sender'] == 'Administrator':
                print(f"{YELLOW}[{timestamp}] {message['sender']}: {RESET}{message['message']}")
            else:
                print(f"{BLUE}[{timestamp}] {message['sender']}: {RESET}{message['message']}")
    
    if show_prompt:
        print(f"\n{YELLOW}You: {RESET}", end='', flush=True)

def display_private_chat(username, private_messages, show_prompt=True):
    # SMOOTH CLEAR - NO BLINK
    sys.stdout.write("\033[2J\033[H")
    
    print(f"{PURPLE}="*50 + RESET)
    print(f"{YELLOW}PRIVATE MESSAGES{RESET}")
    print(f"{GRAY}Type '/public' for Public Chat | '/create' to create room{RESET}")
    print(f"{GRAY}Type '/share @user filename' to send private file{RESET}")
    print(f"{GRAY}Type '/list' to view your rooms | '/help' for all commands{RESET}")
    print(f"{GRAY}Type '!exit' to exit{RESET}")
    print(f"{PURPLE}="*50 + RESET + "\n")
    
    if not private_messages:
        print(f"{GRAY}No private messages yet.{RESET}")
        print(f"{GRAY}Use @username to send a private message{RESET}")
    else:
        sorted_pms = sorted(private_messages, key=lambda x: x.get('timestamp', 0), reverse=True)
        
        for pm in sorted_pms[:20]:
            timestamp = time.strftime('%H:%M', time.localtime(pm.get('timestamp', 0)))
            
            if pm['sender'] == username:
                print(f"{GREEN}[{timestamp}] To {pm['receiver']}: {RESET}{pm['message']}")
            else:
                print(f"{PURPLE}[{timestamp}] From {pm['sender']}: {RESET}{pm['message']}")
    
    if show_prompt:
        print(f"\n{YELLOW}You: {RESET}", end='', flush=True)

def display_room_chat(username, room_messages, room_info, show_prompt=True):
    global current_room_id, current_room_name
    
    # SMOOTH CLEAR - NO BLINK
    sys.stdout.write("\033[2J\033[H")
    
    print(f"{CYAN}="*50 + RESET)
    
    if room_info:
        room_creation_time = time.strftime('%Y-%m-%d %H:%M', time.localtime(room_info.get('created_at', 0)))
        print(f"{YELLOW}ROOM: {room_info.get('name', 'Unknown Room')}{RESET}")
        print(f"{GRAY}ID: {current_room_id} | Created: {room_creation_time} by {room_info.get('creator', 'Unknown')}{RESET}")
        print(f"{GRAY}Users in room: {len(room_info.get('users', []))}{RESET}")
    else:
        print(f"{YELLOW}ROOM: {current_room_name}{RESET}")
        print(f"{GRAY}ID: {current_room_id}{RESET}")
    
    print(f"{GRAY}Type '/leave' to leave room | '/public' for Public Chat{RESET}")
    print(f"{GRAY}Type '/share filename' to share file in room{RESET}")
    print(f"{GRAY}Type '/list' to view your rooms | '/help' for all commands{RESET}")
    print(f"{GRAY}Type '!exit' to exit{RESET}")
    print(f"{CYAN}="*50 + RESET + "\n")
    
    if not room_messages:
        print(f"{GRAY}No messages in this room yet. Start the conversation!{RESET}")
    else:
        for message in room_messages:
            timestamp = time.strftime('%H:%M', time.localtime(message.get('timestamp', 0)))
            if message['sender'] == username:
                print(f"{GREEN}[{timestamp}] You: {RESET}{message['message']}")
            else:
                print(f"{CYAN}[{timestamp}] {message['sender']}: {RESET}{message['message']}")
    
    if show_prompt:
        print(f"\n{YELLOW}You: {RESET}", end='', flush=True)
    
    return True

def display_rooms_list(username):
    # SMOOTH CLEAR - NO BLINK
    sys.stdout.write("\033[2J\033[H")
    
    print(f"{YELLOW}="*50 + RESET)
    print(f"{YELLOW}YOUR JOINED ROOMS{RESET}")
    print(f"{GRAY}Select room number to join | [0] Back to Public Chat{RESET}")
    print(f"{YELLOW}="*50 + RESET + "\n")
    
    user_rooms = get_user_rooms(username)
    
    if not user_rooms:
        print(f"{GRAY}You haven't joined any rooms yet.{RESET}")
        print(f"{GRAY}Use '/create' to make a room or '/join [ID]' to join one.{RESET}")
        print(f"\n{YELLOW}Press Enter to continue...{RESET}", end='', flush=True)
        input()
        return False, None
    
    print(f"{BLUE}ROOMS YOU'VE JOINED:{RESET}")
    print(f"{GRAY}" + "-"*50 + RESET)
    
    for i, room in enumerate(user_rooms, 1):
        room_id = room.get('id', 'Unknown')
        room_name = room.get('name', f'Room {room_id}')
        joined_time = time.strftime('%Y-%m-%d %H:%M', time.localtime(room.get('joined_at', 0)))
        print(f"{GREEN}[{i}]{RESET} {room_name} {GRAY}(ID: {room_id}){RESET}")
    
    print(f"{GRAY}" + "-"*50 + RESET)
    print(f"{GREEN}[0]{RESET} {GRAY}Back to Public Chat{RESET}")
    print()
    
    while True:
        try:
            selection = input(f"{YELLOW}Enter room number: {RESET}").strip()
            
            if not selection:
                continue
                
            if selection == '0':
                return False, None
            
            selection_num = int(selection)
            if 1 <= selection_num <= len(user_rooms):
                selected_room = user_rooms[selection_num - 1]
                selected_room_id = selected_room.get('id')
                selected_room_name = selected_room.get('name', f'Room {selected_room_id}')
                return True, (selected_room_id, selected_room_name)
            else:
                print(f"{RED}Invalid selection. Choose 0-{len(user_rooms)}{RESET}")
                
        except ValueError:
            print(f"{RED}Please enter a valid number{RESET}")
        except KeyboardInterrupt:
            raise

def check_command(message):
    message_lower = message.lower().strip()
    
    if message_lower == '/public':
        return 'switch_to_public'
    elif message_lower == '/private':
        return 'switch_to_private'
    elif message_lower == '/list':
        return 'list_rooms'
    elif message_lower.startswith('/create'):
        return 'create_room'
    elif message_lower.startswith('/join'):
        return 'join_room'
    elif message_lower == '/leave':
        return 'leave_room'
    elif message_lower.startswith('/share'):
        return 'share_file'
    elif message_lower.startswith('/get'):
        return 'get_file'
    elif message_lower == '/files':
        return 'list_files'
    elif message_lower.startswith('/unshare'):
        return 'unshare_file'
    elif message_lower in ['/help', '/h', '/?']:  # ADDED: Help command with shortcuts
        return 'show_help'
    else:
        return 'normal_message'

def get_input_with_timeout(timeout=0.1):
    try:
        if sys.stdin in select.select([sys.stdin], [], [], timeout)[0]:
            message = sys.stdin.readline().rstrip()
            return message
    except:
        pass
    return None

def start_chat(username):
    global exit_flag, current_mode, current_room_id, current_room_name, last_display_time
    
    try:
        test_response = requests.get(SERVER_URL + '?action=messages', timeout=5)
        if test_response.status_code == 200:
            data = test_response.json()
            if isinstance(data, dict) and data.get('status') == 'error' and 'maintenance' in data.get('message', '').lower():
                print(f"\n{YELLOW}⚠️ {data.get('message')}{RESET}")
                print(f"{GRAY}Please try again later.{RESET}")
                time.sleep(3)
                return
    except:
        pass
    
    last_message_count = 0
    last_pm_count = 0
    last_room_message_count = 0
    messages = []
    private_messages = []
    room_messages = []
    room_info = None
    
    signal.signal(signal.SIGINT, signal_handler)
    
    if current_mode == "public":
        messages = get_messages()
        display_public_chat(username, messages, show_prompt=True)
        last_message_count = len(messages)
    elif current_mode == "private":
        private_messages = get_private_messages(username)
        display_private_chat(username, private_messages, show_prompt=True)
        last_pm_count = len(private_messages)
    else:
        room_messages = get_room_messages(current_room_id)
        success, info = get_room_info(current_room_id)
        if success:
            room_info = info
            current_room_name = info.get('name', 'Unknown Room')
        display_room_chat(username, room_messages, room_info, show_prompt=True)
        last_room_message_count = len(room_messages)
    
    last_display_time = time.time()
    
    try:
        while not exit_flag:
            current_time = time.time()
            
            should_refresh = (current_time - last_display_time) >= refresh_interval
            
            if should_refresh:
                if current_mode == "public":
                    new_messages = get_messages()
                    current_count = len(new_messages)
                    
                    if current_count != last_message_count:
                        display_public_chat(username, new_messages, show_prompt=True)
                        messages = new_messages
                        last_message_count = current_count
                        last_display_time = current_time
                        
                elif current_mode == "private":
                    new_private_messages = get_private_messages(username)
                    current_pm_count = len(new_private_messages)
                    
                    if current_pm_count != last_pm_count:
                        display_private_chat(username, new_private_messages, show_prompt=True)
                        private_messages = new_private_messages
                        last_pm_count = current_pm_count
                        last_display_time = current_time
                        
                else:
                    is_deleted, _ = check_room_deleted(current_room_id)
                    if is_deleted:
                        print(f"\n{RED}Room {current_room_id} has been deleted by admin!{RESET}")
                        print(f"{GRAY}Returning to public chat...{RESET}")
                        time.sleep(2)
                        
                        current_mode = "public"
                        current_room_id = "lobby"
                        current_room_name = "Public Chat"
                        
                        messages = get_messages()
                        display_public_chat(username, messages, show_prompt=True)
                        last_message_count = len(messages)
                        last_display_time = time.time()
                        continue
                    
                    new_room_messages = get_room_messages(current_room_id)
                    current_room_msg_count = len(new_room_messages)
                    
                    if current_room_msg_count != last_room_message_count:
                        success, info = get_room_info(current_room_id)
                        if success:
                            room_info = info
                            current_room_name = info.get('name', 'Unknown Room')
                        display_room_chat(username, new_room_messages, room_info, show_prompt=True)
                        room_messages = new_room_messages
                        last_room_message_count = current_room_msg_count
                        last_display_time = current_time
            
            message = get_input_with_timeout(0.1)
            
            if message is not None and message != "":
                command = check_command(message)
                
                if command == 'switch_to_public':
                    current_mode = "public"
                    current_room_id = "lobby"
                    current_room_name = "Public Chat"
                    print(f"{GREEN}✓ Switched to PUBLIC CHAT{RESET}")
                    time.sleep(0.5)
                    messages = get_messages()
                    display_public_chat(username, messages, show_prompt=True)
                    last_message_count = len(messages)
                    last_display_time = time.time()
                    continue
                    
                elif command == 'switch_to_private':
                    current_mode = "private"
                    current_room_id = "lobby"
                    current_room_name = "Public Chat"
                    print(f"{GREEN}✓ Switched to PRIVATE MESSAGES{RESET}")
                    time.sleep(0.5)
                    private_messages = get_private_messages(username)
                    display_private_chat(username, private_messages, show_prompt=True)
                    last_pm_count = len(private_messages)
                    last_display_time = time.time()
                    continue
                
                elif command == 'list_rooms':
                    has_rooms, room_selection = display_rooms_list(username)
                    
                    if has_rooms and room_selection:
                        room_id, room_name = room_selection
                        
                        if current_mode == "room" and current_room_id == room_id:
                            print(f"{GRAY}You're already in this room{RESET}")
                            time.sleep(1)
                            display_room_chat(username, room_messages, room_info, show_prompt=True)
                        else:
                            print(f"{GRAY}Joining {room_name}...{RESET}")
                            success, join_data = join_room(room_id, username)
                            
                            if success:
                                print(f"{GREEN}✓ Joined room successfully!{RESET}")
                                time.sleep(1)
                                
                                current_mode = "room"
                                current_room_id = room_id
                                current_room_name = room_name
                                
                                success, info = get_room_info(room_id)
                                if success:
                                    room_info = info
                                    current_room_name = info.get('name', room_name)
                                else:
                                    current_room_name = room_name
                                
                                room_messages = get_room_messages(room_id)
                                display_room_chat(username, room_messages, room_info, show_prompt=True)
                                last_room_message_count = len(room_messages)
                                last_display_time = time.time()
                            else:
                                print(f"{RED}✗ Failed to join room: {join_data.get('message', 'Unknown error')}{RESET}")
                                time.sleep(2)
                                if current_mode == "public":
                                    display_public_chat(username, messages, show_prompt=True)
                                elif current_mode == "private":
                                    display_private_chat(username, private_messages, show_prompt=True)
                                else:
                                    display_room_chat(username, room_messages, room_info, show_prompt=True)
                    
                    elif not has_rooms:
                        if current_mode == "public":
                            messages = get_messages()
                            display_public_chat(username, messages, show_prompt=True)
                            last_message_count = len(messages)
                        elif current_mode == "private":
                            private_messages = get_private_messages(username)
                            display_private_chat(username, private_messages, show_prompt=True)
                            last_pm_count = len(private_messages)
                        else:
                            room_messages = get_room_messages(current_room_id)
                            display_room_chat(username, room_messages, room_info, show_prompt=True)
                            last_room_message_count = len(room_messages)
                        
                        last_display_time = time.time()
                    
                    continue
                
                elif command == 'create_room':
                    print(f"\n{YELLOW}Enter room name: {RESET}", end='', flush=True)
                    room_name = ""
                    while not room_name.strip():
                        room_name = input()
                    
                    print(f"{GRAY}Creating room '{room_name}'...{RESET}")
                    success, room_id, msg = create_room(room_name, username)
                    
                    if success:
                        print(f"{GREEN}✓ Room created! ID: {room_id}{RESET}")
                        print(f"{GRAY}Share this ID with others: {room_id}{RESET}")
                        
                        time.sleep(2)
                        
                        current_mode = "room"
                        current_room_id = room_id
                        current_room_name = room_name
                        
                        join_success, join_data = join_room(room_id, username)
                        if join_success:
                            room_info = join_data.get('room')
                            room_messages = get_room_messages(room_id)
                            display_room_chat(username, room_messages, room_info, show_prompt=True)
                            last_room_message_count = len(room_messages)
                            last_display_time = time.time()
                    else:
                        print(f"{RED}✗ Failed to create room: {msg}{RESET}")
                        time.sleep(2)
                        if current_mode == "public":
                            display_public_chat(username, messages, show_prompt=True)
                        elif current_mode == "private":
                            display_private_chat(username, private_messages, show_prompt=True)
                        else:
                            display_room_chat(username, room_messages, room_info, show_prompt=True)
                    continue
                
                elif command == 'join_room':
                    parts = message.split(' ', 1)
                    if len(parts) < 2:
                        print(f"\n{YELLOW}Enter room ID to join: {RESET}", end='', flush=True)
                        room_id = input().strip().upper()
                    else:
                        room_id = parts[1].strip().upper()
                    
                    if not room_id:
                        print(f"{RED}✗ Room ID cannot be empty{RESET}")
                        time.sleep(1)
                        continue
                    
                    print(f"{GRAY}Joining room {room_id}...{RESET}")
                    success, join_data = join_room(room_id, username)
                    
                    if success:
                        print(f"{GREEN}✓ Joined room successfully!{RESET}")
                        
                        success_info, info = get_room_info(room_id)
                        room_name = info.get('name', f"Room {room_id}") if success_info else f"Room {room_id}"
                        
                        time.sleep(1)
                        
                        current_mode = "room"
                        current_room_id = room_id
                        current_room_name = room_name
                        
                        if success_info:
                            room_info = info
                            current_room_name = info.get('name', room_name)
                        else:
                            current_room_name = room_name
                        
                        room_messages = get_room_messages(room_id)
                        display_room_chat(username, room_messages, room_info, show_prompt=True)
                        last_room_message_count = len(room_messages)
                        last_display_time = time.time()
                    else:
                        print(f"{RED}✗ Failed to join room: {join_data.get('message', 'Unknown error')}{RESET}")
                        time.sleep(2)
                        if current_mode == "public":
                            display_public_chat(username, messages, show_prompt=True)
                        elif current_mode == "private":
                            display_private_chat(username, private_messages, show_prompt=True)
                        else:
                            display_room_chat(username, room_messages, room_info, show_prompt=True)
                    continue
                
                elif command == 'leave_room' and current_mode == "room":
                    print(f"{GRAY}Leaving room {current_room_id}...{RESET}")
                    success, msg = leave_room(current_room_id, username)
                    
                    if success:
                        print(f"{GREEN}✓ Left room successfully{RESET}")
                        
                        time.sleep(1)
                        
                        current_mode = "public"
                        current_room_id = "lobby"
                        current_room_name = "Public Chat"
                        
                        messages = get_messages()
                        display_public_chat(username, messages, show_prompt=True)
                        last_message_count = len(messages)
                        last_display_time = time.time()
                    else:
                        print(f"{RED}✗ Failed to leave room: {msg}{RESET}")
                        time.sleep(2)
                        display_room_chat(username, room_messages, room_info, show_prompt=True)
                    continue
                
                # FILE SHARING COMMANDS
                elif command == 'share_file':
                    # Parse: /share filename or /share filename --expire 2h
                    parts = message.split(' ')
                    
                    if len(parts) < 2:
                        print(f"{RED}✗ Usage: /share filename [--expire 1h-24h]{RESET}")
                        print(f"{GRAY}Example: /share document.pdf{RESET}")
                        print(f"{GRAY}Example: /share photo.jpg --expire 2h{RESET}")
                        time.sleep(2)
                        continue
                    
                    # Check for --expire option
                    expire = "24h"
                    filename = ""
                    
                    i = 1
                    while i < len(parts):
                        if parts[i] == '--expire' and i + 1 < len(parts):
                            expire = parts[i + 1]
                            i += 2
                        else:
                            if filename:
                                filename += " " + parts[i]
                            else:
                                filename = parts[i]
                            i += 1
                    
                    if not filename:
                        print(f"{RED}✗ No filename specified{RESET}")
                        time.sleep(2)
                        continue
                    
                    # Handle @user for private file share
                    private_to = None
                    if current_mode == "private" or (filename.startswith('@') and ' ' in filename):
                        # Format: @username filename
                        if filename.startswith('@') and ' ' in filename:
                            parts2 = filename.split(' ', 1)
                            private_to = parts2[0][1:]  # Remove @
                            filename = parts2[1]
                    
                    # Check if in room
                    room_id = current_room_id if current_mode == "room" else None
                    
                    upload_file(username, filename, expire, room_id, private_to)
                    
                    # Refresh display
                    if current_mode == "public":
                        messages = get_messages()
                        display_public_chat(username, messages, show_prompt=True)
                    elif current_mode == "private":
                        private_messages = get_private_messages(username)
                        display_private_chat(username, private_messages, show_prompt=True)
                    else:
                        room_messages = get_room_messages(current_room_id)
                        display_room_chat(username, room_messages, room_info, show_prompt=True)
                    
                    continue
                
                elif command == 'get_file':
                    # Parse: /get CODE
                    parts = message.split(' ')
                    
                    if len(parts) < 2:
                        print(f"{RED}✗ Usage: /get FILECODE{RESET}")
                        print(f"{GRAY}Example: /get ABC123{RESET}")
                        time.sleep(2)
                        continue
                    
                    file_code = parts[1].strip().upper()
                    
                    download_file(file_code, username)
                    
                    time.sleep(2)
                    
                    # Refresh display
                    if current_mode == "public":
                        messages = get_messages()
                        display_public_chat(username, messages, show_prompt=True)
                    elif current_mode == "private":
                        private_messages = get_private_messages(username)
                        display_private_chat(username, private_messages, show_prompt=True)
                    else:
                        room_messages = get_room_messages(current_room_id)
                        display_room_chat(username, room_messages, room_info, show_prompt=True)
                    
                    continue
                
                elif command == 'list_files':
                    list_files(username)
                    
                    print(f"\n{YELLOW}Press Enter to continue...{RESET}", end='', flush=True)
                    input()
                    
                    # Refresh display
                    if current_mode == "public":
                        messages = get_messages()
                        display_public_chat(username, messages, show_prompt=True)
                    elif current_mode == "private":
                        private_messages = get_private_messages(username)
                        display_private_chat(username, private_messages, show_prompt=True)
                    else:
                        room_messages = get_room_messages(current_room_id)
                        display_room_chat(username, room_messages, room_info, show_prompt=True)
                    
                    continue
                
                elif command == 'unshare_file':
                    # Parse: /unshare CODE
                    parts = message.split(' ')
                    
                    if len(parts) < 2:
                        print(f"{RED}✗ Usage: /unshare FILECODE{RESET}")
                        print(f"{GRAY}Example: /unshare ABC123{RESET}")
                        time.sleep(2)
                        continue
                    
                    file_code = parts[1].strip().upper()
                    
                    unshare_file(file_code, username)
                    
                    time.sleep(2)
                    
                    # Refresh display
                    if current_mode == "public":
                        messages = get_messages()
                        display_public_chat(username, messages, show_prompt=True)
                    elif current_mode == "private":
                        private_messages = get_private_messages(username)
                        display_private_chat(username, private_messages, show_prompt=True)
                    else:
                        room_messages = get_room_messages(current_room_id)
                        display_room_chat(username, room_messages, room_info, show_prompt=True)
                    
                    continue
                
                # ADDED: Help command handler
                elif command == 'show_help':
                    show_help()
                    
                    # Refresh display after help
                    if current_mode == "public":
                        messages = get_messages()
                        display_public_chat(username, messages, show_prompt=True)
                        last_message_count = len(messages)
                    elif current_mode == "private":
                        private_messages = get_private_messages(username)
                        display_private_chat(username, private_messages, show_prompt=True)
                        last_pm_count = len(private_messages)
                    else:
                        room_messages = get_room_messages(current_room_id)
                        display_room_chat(username, room_messages, room_info, show_prompt=True)
                        last_room_message_count = len(room_messages)
                    
                    last_display_time = time.time()
                    continue
                
                if message.lower() == '!exit':
                    print(f"{YELLOW}Goodbye!{RESET}")
                    break
                
                if message.strip():
                    success, msg_type = send_message(username, message, current_room_id)
                    if success:
                        sys.stdout.write("\033[F\033[K")
                        
                        if message.startswith('@'):
                            print(f"{GREEN}✓ Private message sent{RESET}")
                        elif current_mode == "room":
                            print(f"{GREEN}✓ Room message sent{RESET}")
                        else:
                            print(f"{GREEN}✓ Message sent{RESET}")
                        
                        time.sleep(0.1)
                        
                        # Clear success message
                        sys.stdout.write("\033[F\033[K")
                        
                        if current_mode == "public":
                            messages = get_messages()
                            display_public_chat(username, messages, show_prompt=True)
                            last_message_count = len(messages)
                        elif current_mode == "private":
                            private_messages = get_private_messages(username)
                            display_private_chat(username, private_messages, show_prompt=True)
                            last_pm_count = len(private_messages)
                        else:
                            room_messages = get_room_messages(current_room_id)
                            display_room_chat(username, room_messages, room_info, show_prompt=True)
                            last_room_message_count = len(room_messages)
                        
                        last_display_time = time.time()
                    else:
                        if msg_type == 'room_deleted':
                            print(f"{RED}✗ Room has been deleted by admin{RESET}")
                            time.sleep(2)
                            current_mode = "public"
                            current_room_id = "lobby"
                            current_room_name = "Public Chat"
                            messages = get_messages()
                            display_public_chat(username, messages, show_prompt=True)
                            last_message_count = len(messages)
                            last_display_time = time.time()
                        else:
                            print(f"{RED}✗ Failed to send message{RESET}")
            
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Exiting... Goodbye!{RESET}")
    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
    finally:
        print(RESET)

def main():
    global exit_flag
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        username = None
        while not username and not exit_flag:
            try:
                username = login_or_signup()
            except KeyboardInterrupt:
                print(f"\n{YELLOW}Exiting... Goodbye!{RESET}")
                exit_flag = True
                break
        
        if username and not exit_flag:
            start_chat(username)
            
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Exiting... Goodbye!{RESET}")
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")
    finally:
        print(RESET)

if __name__ == "__main__":
    main()