import uvicorn
from fastapi import FastAPI, WebSocket
import json
import asyncio
from typing import Dict, List

app = FastAPI()
connected_devices = {}
device_apps = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected")
    
    try:
        # Receive device data and app list from the client
        data = await websocket.receive_text()
        device_info = json.loads(data)
        device_id = device_info.get("device_id")
        
        # Store installed apps information
        installed_apps = device_info.get("installed_apps", [])
        device_apps[device_id] = installed_apps
        
        # Store the websocket connection
        connected_devices[device_id] = websocket
        
        # Log connection and app count
        print(f"Device {device_id} connected")
        print(f"Received {len(installed_apps)} installed apps from device {device_id}")
        
        # Send back a confirmation message to the client
        await websocket.send_text(f"Device {device_id} connected")
        
        # Main command loop
        while True:
            print("\n==== Device Management ====")
            print(f"Connected device: {device_id}")
            print("1. List installed apps")
            print("2. Uninstall an app")
            print("3. Search for an app")
            print("4. Send custom command")
            print("5. Exit")
            
            choice = input("\nEnter your choice (1-5): ")
            
            if choice == "1":
                # List all installed apps
                print(f"\nInstalled Apps on device {device_id}:")
                print(f"{'#':<4} {'App Name':<40} {'Package Name':<50}")
                print("-" * 94)
                
                for i, app in enumerate(device_apps[device_id]):
                    app_name = app.get('app_name', 'Unknown')
                    package_name = app.get('package_name', 'Unknown')
                    print(f"{i+1:<4} {app_name[:38]:<40} {package_name[:48]:<50}")
            
            elif choice == "2":
                # Uninstall an app by number
                print("\nSelect an app to uninstall:")
                for i, app in enumerate(device_apps[device_id][:20]):  # Show first 20 only
                    print(f"{i+1}. {app.get('app_name')} ({app.get('package_name')})")
                
                if len(device_apps[device_id]) > 20:
                    print("... and more. Use search option to find specific apps.")
                
                app_index = input("\nEnter app number or 'c' to cancel: ")
                
                if app_index.lower() == 'c':
                    continue
                
                try:
                    app_index = int(app_index) - 1
                    if 0 <= app_index < len(device_apps[device_id]):
                        package_name = device_apps[device_id][app_index].get('package_name')
                        app_name = device_apps[device_id][app_index].get('app_name')
                        
                        confirm = input(f"Confirm uninstall of {app_name} ({package_name})? (y/n): ")
                        if confirm.lower() == 'y':
                            print(f"Sending uninstall command for {package_name}...")
                            # Send uninstall command
                            await websocket.send_text(f"uninstall:{package_name}")
                            # Wait for response
                            response = await websocket.receive_text()
                            print(f"Response: {response}")
                    else:
                        print("Invalid app selection")
                except ValueError:
                    print("Invalid input")
            
            elif choice == "3":
                # Search for an app
                search_term = input("\nEnter search term: ").lower()
                matches = []
                
                print(f"\nSearch results for '{search_term}':")
                print(f"{'#':<4} {'App Name':<40} {'Package Name':<50}")
                print("-" * 94)
                
                for i, app in enumerate(device_apps[device_id]):
                    app_name = app.get('app_name', '').lower()
                    package_name = app.get('package_name', '').lower()
                    
                    if search_term in app_name or search_term in package_name:
                        matches.append(app)
                        print(f"{len(matches):<4} {app.get('app_name')[:38]:<40} {app.get('package_name')[:48]:<50}")
                
                if matches:
                    app_index = input("\nEnter app number to uninstall or 'c' to cancel: ")
                    
                    if app_index.lower() == 'c':
                        continue
                    
                    try:
                        app_index = int(app_index) - 1
                        if 0 <= app_index < len(matches):
                            package_name = matches[app_index].get('package_name')
                            app_name = matches[app_index].get('app_name')
                            
                            confirm = input(f"Confirm uninstall of {app_name} ({package_name})? (y/n): ")
                            if confirm.lower() == 'y':
                                print(f"Sending uninstall command for {package_name}...")
                                # Send uninstall command
                                await websocket.send_text(f"uninstall:{package_name}")
                                # Wait for response
                                response = await websocket.receive_text()
                                print(f"Response: {response}")
                                
                                # Check if it's a JSON response with updated app list
                                try:
                                    update_data = json.loads(response)
                                    if 'action' in update_data and update_data['action'] == 'apps_updated':
                                        device_apps[device_id] = update_data.get('installed_apps', [])
                                        print(f"Updated app list received - now {len(device_apps[device_id])} apps")
                                except:
                                    # Not a JSON response, just a regular message
                                    pass
                        else:
                            print("Invalid app selection")
                    except ValueError:
                        print("Invalid input")
                else:
                    print("No matches found")
            
            elif choice == "4":
                # Send custom command
                command = input(f"\nEnter custom command for {device_id}: ")
                await websocket.send_text(command)
                response = await websocket.receive_text()
                print(f"Response: {response}")
            
            elif choice == "5":
                print("Exiting...")
                break
            
            else:
                print("Invalid choice")
    
    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        if 'device_id' in locals() and device_id in connected_devices:
            del connected_devices[device_id]
            if device_id in device_apps:
                del device_apps[device_id]
            print(f"Device {device_id} disconnected")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)