import uvicorn
from fastapi import FastAPI, WebSocket
import json
import asyncio
from typing import Dict, List, Optional

app = FastAPI()
connected_devices = {}
device_apps = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    device_id = None
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
            print("3. Exit")
            
            choice = input("\nEnter your choice (1-3): ")
            
            if choice == "1":
                # List all installed apps
                if not device_apps.get(device_id):
                    print("No apps found for this device")
                    continue
                    
                print(f"\nInstalled Apps on device {device_id}:")
                print(f"{'#':<4} {'App Name':<40} {'Package Name':<50}")
                print("-" * 94)
                
                for i, app in enumerate(device_apps[device_id]):
                    app_name = app.get('app_name', 'Unknown')
                    package_name = app.get('package_name', 'Unknown')
                    print(f"{i+1:<4} {app_name[:38]:<40} {package_name[:48]:<50}")
            
            elif choice == "2":
                # Uninstall an app
                if not device_apps.get(device_id):
                    print("No apps found for this device")
                    continue
                
                # Ask for search term to find the app
                search_term = input("\nEnter part of app name to search (or press Enter to see all): ").lower()
                
                matches = []
                for i, app in enumerate(device_apps[device_id]):
                    app_name = app.get('app_name', '').lower()
                    package_name = app.get('package_name', '').lower()
                    
                    if not search_term or search_term in app_name or search_term in package_name:
                        matches.append(app)
                
                if not matches:
                    print("No matching apps found")
                    continue
                
                # Show matching apps
                print(f"\nMatching Apps ({len(matches)}):")
                print(f"{'#':<4} {'App Name':<40} {'Package Name':<50}")
                print("-" * 94)
                
                for i, app in enumerate(matches):
                    app_name = app.get('app_name', 'Unknown')
                    package_name = app.get('package_name', 'Unknown')
                    print(f"{i+1:<4} {app_name[:38]:<40} {package_name[:48]:<50}")
                
                # Select app to uninstall
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
                            uninstall_command = f"uninstall:{package_name}"
                            await websocket.send_text(uninstall_command)
                            
                            # Wait for response
                            print("Waiting for uninstall response...")
                            response = await websocket.receive_text()
                            print(f"Response: {response}")
                            
                            # Remove the app from our local list if successful
                            if "Successfully uninstalled" in response:
                                device_apps[device_id] = [app for app in device_apps[device_id] 
                                                        if app.get('package_name') != package_name]
                                print(f"Updated local app list - now {len(device_apps[device_id])} apps")
                    else:
                        print("Invalid app selection")
                except ValueError:
                    print("Invalid input, please enter a number")
            
            elif choice == "3":
                print("Exiting management interface...")
                break
            
            else:
                print("Invalid choice, please try again")
    
    except Exception as e:
        print(f"Connection error: {str(e)}")
    finally:
        # Clean up when connection is closed
        if device_id and device_id in connected_devices:
            del connected_devices[device_id]
        if device_id and device_id in device_apps:
            del device_apps[device_id]
        print(f"Device {device_id} disconnected")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)