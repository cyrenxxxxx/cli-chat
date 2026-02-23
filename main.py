import requests
import time
import os
import sys
import signal
import select

SERVER_URL = 'https://server_url.com'

exit_flag = False
current_mode = "public"
current_room_id = "lobby"
current_room_name = "Public Chat"
last_display_time = 0
refresh_interval = 3

def signal_handler(sig, frame):
    global exit_flag
    print("\n\033[93mExiting... Goodbye!\033[0m")
    exit_flag = True
    sys.exit(0)

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
                    print(f"\033[91m✗ {error_msg}\033[0m")
                    return False, 'error'
            except Exception as e:
                print(f"\033[91m✗ Invalid server response\033[0m")
                return False, 'error'
        else:
            print(f"\033[91m✗ Server error: {response.status_code}\033[0m")
            return False, 'error'
    except requests.exceptions.Timeout:
        print(f"\033[91m✗ Connection timeout\033[0m")
        return False, 'error'
    except Exception as e:
        print(f"\033[91m✗ Connection error: {str(e)}\033[0m")
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
                print(f"\033[91m✗ {error_msg}\033[0m")
                return False, None, error_msg
        else:
            error_msg = f"Server error: {response.status_code}"
            print(f"\033[91m✗ {error_msg}\033[0m")
            return False, None, error_msg
    except requests.exceptions.Timeout:
        error_msg = "Connection timeout"
        print(f"\033[91m✗ {error_msg}\033[0m")
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"\033[91m✗ {error_msg}\033[0m")
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
                    print(f"\033[93m⚠️ {error_msg}\033[0m")
                return []
            return data
        else:
            return []
    except requests.exceptions.Timeout:
        print(f"\033[91m✗ Connection timeout\033[0m")
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
                    print(f"\033[93m⚠️ {error_msg}\033[0m")
                return []
            return data
        else:
            return []
    except requests.exceptions.Timeout:
        print(f"\033[91m✗ Connection timeout\033[0m")
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
                    print(f"\033[92m✓ Welcome {username}!\033[0m")
                    time.sleep(1)
                    return username
                else:
                    error_msg = data.get('message', 'Login failed')
                    if 'maintenance' in error_msg.lower():
                        print(f"\033[93m⚠️ {error_msg}\033[0m")
                    else:
                        print(f"\033[91m✗ {error_msg}\033[0m")
                    return None
            else:
                print(f"\033[91m✗ Server error: {response.status_code}\033[0m")
                return None
                
        except requests.exceptions.Timeout:
            print(f"\033[91m✗ Connection timeout\033[0m")
            return None
        except Exception as e:
            print(f"\033[91m✗ Connection failed: {str(e)}\033[0m")
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
                    print("\033[92m✓ Signup successful! Please login.\033[0m")
                    time.sleep(1)
                else:
                    error_msg = data.get('message', 'Signup failed')
                    if 'maintenance' in error_msg.lower():
                        print(f"\033[93m⚠️ {error_msg}\033[0m")
                    else:
                        print(f"\033[91m✗ {error_msg}\033[0m")
            else:
                print(f"\033[91m✗ Server error: {response.status_code}\033[0m")
        except requests.exceptions.Timeout:
            print(f"\033[91m✗ Connection timeout\033[0m")
        except Exception as e:
            print(f"\033[91m✗ Connection failed: {str(e)}\033[0m")
        return None

def get_messages():
    try:
        response = requests.get(SERVER_URL + '?action=messages', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and data.get('status') == 'error':
                error_msg = data.get('message', 'System error')
                if 'maintenance' in error_msg.lower():
                    print(f"\033[93m⚠️ {error_msg}\033[0m")
                return []
            return data
        else:
            print(f"\033[91m✗ Error fetching messages: {response.status_code}\033[0m")
            return []
    except requests.exceptions.Timeout:
        print(f"\033[91m✗ Connection timeout\033[0m")
        return []
    except Exception as e:
        print(f"\033[91m✗ Connection error: {str(e)}\033[0m")
        return []

def display_public_chat(username, messages, show_prompt=True):
    global current_room_name
    
    # SMOOTH CLEAR - NO BLINK
    sys.stdout.write("\033[2J\033[H")
    
    print("\033[94m" + "="*50 + "\033[0m")
    print(f"\033[93mPUBLIC CHAT - {current_room_name}\033[0m")
    print("\033[90mType '/private' for Private Messages | '/create' to create room\033[0m")
    print("\033[90mType '/list' to view your rooms | '!exit' to exit\033[0m")
    print("\033[94m" + "="*50 + "\033[0m\n")
    
    if not messages:
        print("\033[90mNo public messages yet. Start the conversation!\033[0m")
    else:
        for message in messages:
            timestamp = time.strftime('%H:%M', time.localtime(message.get('timestamp', 0)))
            if message['sender'] == username:
                print(f"\033[92m[{timestamp}] You: \033[0m{message['message']}")
            elif message['sender'] == 'Administrator':
                print(f"\033[93m[{timestamp}] {message['sender']}: \033[0m{message['message']}")
            else:
                print(f"\033[94m[{timestamp}] {message['sender']}: \033[0m{message['message']}")
    
    if show_prompt:
        print("\n\033[93mYou: \033[0m", end='', flush=True)

def display_private_chat(username, private_messages, show_prompt=True):
    # SMOOTH CLEAR - NO BLINK
    sys.stdout.write("\033[2J\033[H")
    
    print("\033[95m" + "="*50 + "\033[0m")
    print("\033[93mPRIVATE MESSAGES\033[0m")
    print("\033[90mType '/public' for Public Chat | '/create' to create room\033[0m")
    print("\033[90mType '/list' to view your rooms | '!exit' to exit\033[0m")
    print("\033[95m" + "="*50 + "\033[0m\n")
    
    if not private_messages:
        print("\033[90mNo private messages yet.\033[0m")
        print("\033[90mUse @username to send a private message\033[0m")
    else:
        sorted_pms = sorted(private_messages, key=lambda x: x.get('timestamp', 0), reverse=True)
        
        for pm in sorted_pms[:20]:
            timestamp = time.strftime('%H:%M', time.localtime(pm.get('timestamp', 0)))
            
            if pm['sender'] == username:
                print(f"\033[92m[{timestamp}] To {pm['receiver']}: \033[0m{pm['message']}")
            else:
                print(f"\033[95m[{timestamp}] From {pm['sender']}: \033[0m{pm['message']}")
    
    if show_prompt:
        print("\n\033[93mYou: \033[0m", end='', flush=True)

def display_room_chat(username, room_messages, room_info, show_prompt=True):
    global current_room_id, current_room_name
    
    # SMOOTH CLEAR - NO BLINK
    sys.stdout.write("\033[2J\033[H")
    
    print("\033[96m" + "="*50 + "\033[0m")
    
    if room_info:
        room_creation_time = time.strftime('%Y-%m-%d %H:%M', time.localtime(room_info.get('created_at', 0)))
        print(f"\033[93mROOM: {room_info.get('name', 'Unknown Room')}\033[0m")
        print(f"\033[90mID: {current_room_id} | Created: {room_creation_time} by {room_info.get('creator', 'Unknown')}\033[0m")
        print(f"\033[90mUsers in room: {len(room_info.get('users', []))}\033[0m")
    else:
        print(f"\033[93mROOM: {current_room_name}\033[0m")
        print(f"\033[90mID: {current_room_id}\033[0m")
    
    print("\033[90mType '/leave' to leave room | '/public' for Public Chat\033[0m")
    print("\033[90mType '/list' to view your rooms | '!exit' to exit\033[0m")
    print("\033[96m" + "="*50 + "\033[0m\n")
    
    if not room_messages:
        print("\033[90mNo messages in this room yet. Start the conversation!\033[0m")
    else:
        for message in room_messages:
            timestamp = time.strftime('%H:%M', time.localtime(message.get('timestamp', 0)))
            if message['sender'] == username:
                print(f"\033[92m[{timestamp}] You: \033[0m{message['message']}")
            else:
                print(f"\033[96m[{timestamp}] {message['sender']}: \033[0m{message['message']}")
    
    if show_prompt:
        print("\n\033[93mYou: \033[0m", end='', flush=True)
    
    return True

def display_rooms_list(username):
    # SMOOTH CLEAR - NO BLINK
    sys.stdout.write("\033[2J\033[H")
    
    print("\033[93m" + "="*50 + "\033[0m")
    print("\033[93mYOUR JOINED ROOMS\033[0m")
    print("\033[90mSelect room number to join | [0] Back to Public Chat\033[0m")
    print("\033[93m" + "="*50 + "\033[0m\n")
    
    user_rooms = get_user_rooms(username)
    
    if not user_rooms:
        print("\033[90mYou haven't joined any rooms yet.\033[0m")
        print("\033[90mUse '/create' to make a room or '/join [ID]' to join one.\033[0m")
        print("\n\033[93mPress Enter to continue...\033[0m", end='', flush=True)
        input()
        return False, None
    
    print("\033[94mROOMS YOU'VE JOINED:\033[0m")
    print("\033[90m" + "-"*50 + "\033[0m")
    
    for i, room in enumerate(user_rooms, 1):
        room_id = room.get('id', 'Unknown')
        room_name = room.get('name', f'Room {room_id}')
        joined_time = time.strftime('%Y-%m-%d %H:%M', time.localtime(room.get('joined_at', 0)))
        print(f"\033[92m[{i}]\033[0m {room_name} \033[90m(ID: {room_id})\033[0m")
    
    print("\033[90m" + "-"*50 + "\033[0m")
    print("\033[92m[0]\033[0m \033[90mBack to Public Chat\033[0m")
    print()
    
    while True:
        try:
            selection = input("\033[93mEnter room number: \033[0m").strip()
            
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
                print(f"\033[91mInvalid selection. Choose 0-{len(user_rooms)}\033[0m")
                
        except ValueError:
            print("\033[91mPlease enter a valid number\033[0m")
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
                print(f"\n\033[93m⚠️ {data.get('message')}\033[0m")
                print("\033[90mPlease try again later.\033[0m")
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
                        print(f"\n\033[91mRoom {current_room_id} has been deleted by admin!\033[0m")
                        print("\033[90mReturning to public chat...\033[0m")
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
                    print(f"\033[92m✓ Switched to PUBLIC CHAT\033[0m")
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
                    print(f"\033[92m✓ Switched to PRIVATE MESSAGES\033[0m")
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
                            print(f"\033[90mYou're already in this room\033[0m")
                            time.sleep(1)
                            display_room_chat(username, room_messages, room_info, show_prompt=True)
                        else:
                            print(f"\033[90mJoining {room_name}...\033[0m")
                            success, join_data = join_room(room_id, username)
                            
                            if success:
                                print(f"\033[92m✓ Joined room successfully!\033[0m")
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
                                print(f"\033[91m✗ Failed to join room: {join_data.get('message', 'Unknown error')}\033[0m")
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
                    print("\n\033[93mEnter room name: \033[0m", end='', flush=True)
                    room_name = ""
                    while not room_name.strip():
                        room_name = input()
                    
                    print(f"\033[90mCreating room '{room_name}'...\033[0m")
                    success, room_id, msg = create_room(room_name, username)
                    
                    if success:
                        print(f"\033[92m✓ Room created! ID: {room_id}\033[0m")
                        print(f"\033[90mShare this ID with others: {room_id}\033[0m")
                        
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
                        print(f"\033[91m✗ Failed to create room: {msg}\033[0m")
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
                        print("\n\033[93mEnter room ID to join: \033[0m", end='', flush=True)
                        room_id = input().strip().upper()
                    else:
                        room_id = parts[1].strip().upper()
                    
                    if not room_id:
                        print("\033[91m✗ Room ID cannot be empty\033[0m")
                        time.sleep(1)
                        continue
                    
                    print(f"\033[90mJoining room {room_id}...\033[0m")
                    success, join_data = join_room(room_id, username)
                    
                    if success:
                        print(f"\033[92m✓ Joined room successfully!\033[0m")
                        
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
                        print(f"\033[91m✗ Failed to join room: {join_data.get('message', 'Unknown error')}\033[0m")
                        time.sleep(2)
                        if current_mode == "public":
                            display_public_chat(username, messages, show_prompt=True)
                        elif current_mode == "private":
                            display_private_chat(username, private_messages, show_prompt=True)
                        else:
                            display_room_chat(username, room_messages, room_info, show_prompt=True)
                    continue
                
                elif command == 'leave_room' and current_mode == "room":
                    print(f"\033[90mLeaving room {current_room_id}...\033[0m")
                    success, msg = leave_room(current_room_id, username)
                    
                    if success:
                        print(f"\033[92m✓ Left room successfully\033[0m")
                        
                        time.sleep(1)
                        
                        current_mode = "public"
                        current_room_id = "lobby"
                        current_room_name = "Public Chat"
                        
                        messages = get_messages()
                        display_public_chat(username, messages, show_prompt=True)
                        last_message_count = len(messages)
                        last_display_time = time.time()
                    else:
                        print(f"\033[91m✗ Failed to leave room: {msg}\033[0m")
                        time.sleep(2)
                        display_room_chat(username, room_messages, room_info, show_prompt=True)
                    continue
                
                if message.lower() == '!exit':
                    print("\033[93mGoodbye!\033[0m")
                    break
                
                if message.strip():
                    success, msg_type = send_message(username, message, current_room_id)
                    if success:
                        sys.stdout.write("\033[F\033[K")
                        
                        if message.startswith('@'):
                            print(f"\033[92m✓ Private message sent\033[0m")
                        elif current_mode == "room":
                            print(f"\033[92m✓ Room message sent\033[0m")
                        else:
                            print(f"\033[92m✓ Message sent\033[0m")
                        
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
                        else:  # ROOM MODE - 1 REQUEST ONLY NOW!
                            # GET ROOM MESSAGES ONLY - NO GET ROOM INFO
                            room_messages = get_room_messages(current_room_id)
                            display_room_chat(username, room_messages, room_info, show_prompt=True)
                            last_room_message_count = len(room_messages)
                        # ════════════════════════════════════════════════════════════
                        
                        last_display_time = time.time()
                    else:
                        if msg_type == 'room_deleted':
                            print("\033[91m✗ Room has been deleted by admin\033[0m")
                            time.sleep(2)
                            current_mode = "public"
                            current_room_id = "lobby"
                            current_room_name = "Public Chat"
                            messages = get_messages()
                            display_public_chat(username, messages, show_prompt=True)
                            last_message_count = len(messages)
                            last_display_time = time.time()
                        else:
                            print("\033[91m✗ Failed to send message\033[0m")
            
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n\033[93mExiting... Goodbye!\033[0m")
    except Exception as e:
        print(f"\n\033[91mError: {e}\033[0m")
    finally:
        print("\033[0m")

def main():
    global exit_flag
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        username = None
        while not username and not exit_flag:
            try:
                username = login_or_signup()
            except KeyboardInterrupt:
                print("\n\033[93mExiting... Goodbye!\033[0m")
                exit_flag = True
                break
        
        if username and not exit_flag:
            start_chat(username)
            
    except KeyboardInterrupt:
        print("\n\033[93mExiting... Goodbye!\033[0m")
    except Exception as e:
        print(f"\033[91mError: {e}\033[0m")
    finally:
        print("\033[0m")

if __name__ == "__main__":
    main()
