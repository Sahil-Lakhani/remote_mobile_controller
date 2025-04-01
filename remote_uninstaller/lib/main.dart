import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:installed_apps/installed_apps.dart';
import 'package:installed_apps/app_info.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  _MyAppState createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  late WebSocketChannel channel;
  String statusMessage = "Connecting to server...";
  String deviceId = "Unknown Device";
  bool isConnected = false;
  List<AppInfo> installedApps = [];

  @override
  void initState() {
    super.initState();
    requestPermissions();
  }

  Future<void> requestPermissions() async {
    // Request necessary permissions for app uninstallation
    await [
      Permission.phone,
      Permission.storage,
      Permission.requestInstallPackages,
    ].request();

    fetchDeviceInfo();
  }

  Future<void> fetchDeviceInfo() async {
    // Fetch device info
    final deviceInfo = DeviceInfoPlugin();
    final androidInfo = await deviceInfo.androidInfo;

    setState(() {
      deviceId = androidInfo.id; // Store unique device ID
    });

    // Get installed apps
    await getInstalledApps();

    // Connect to the server
    connectToServer();
  }

  Future<void> getInstalledApps() async {
    try {
      // Get all installed apps (including system apps)
      List<AppInfo> apps = await InstalledApps.getInstalledApps(true, true);
      setState(() {
        installedApps = apps;
      });
      print("Found ${apps.length} installed apps");
    } catch (e) {
      print("Error getting installed apps: $e");
    }
  }

  void connectToServer() {
    try {
      channel = WebSocketChannel.connect(
        Uri.parse('ws://192.168.1.5:8000/ws'),
      );

      // Set connection message
      setState(() {
        statusMessage = "Hello Master, you're connected to the mainframe!";
        isConnected = true;
      });

      // Extract just the package names and app names
      List<Map<String, String>> appsData = installedApps
          .map((app) => {
                'package_name': app.packageName,
                'app_name': app.name ?? 'Unknown',
              })
          .toList();

      // Send device info and installed apps list
      final dataToSend = {
        'device_id': deviceId,
        'installed_apps': appsData,
      };

      channel.sink.add(jsonEncode(dataToSend));
      print("Sent ${appsData.length} app details to server");

      // Listen for commands from server
      channel.stream.listen(
        (message) {
          print("Received from server: $message");

          // Check if it's an uninstall command
          if (message.toString().startsWith("uninstall:")) {
            // Extract package name to uninstall
            String packageName =
                message.toString().split("uninstall:")[1].trim();
            uninstallApp(packageName);
          } else {
            setState(() {
              statusMessage = "Received command: $message";
            });
          }
        },
        onDone: () {
          setState(() {
            statusMessage = "Connection lost. Please restart the app.";
            isConnected = false;
          });
        },
        onError: (error) {
          setState(() {
            statusMessage = "Connection error: $error";
            isConnected = false;
          });
        },
      );
    } catch (e) {
      setState(() {
        statusMessage = "Failed to connect: $e";
      });
    }
  }

  Future<void> uninstallApp(String packageName) async {
    try {
      setState(() {
        statusMessage = "Attempting to uninstall $packageName...";
      });

bool? result = await InstalledApps.uninstallApp(packageName);
      String response;
      if (result == true) {
        response = "Successfully uninstalled $packageName";
      } else {
        response = "Failed to uninstall $packageName";
      }

      channel.sink.add(response);

      setState(() {
        statusMessage = response;
      });

      if (result == true ) {
        await getInstalledApps();

        List<Map<String, String>> updatedAppsData = installedApps
            .map((app) => {
                  'package_name': app.packageName,
                  'app_name': app.name ?? 'Unknown',
                })
            .toList();

        final updateData = {
          'device_id': deviceId,
          'action': 'apps_updated',
          'installed_apps': updatedAppsData,
        };

        channel.sink.add(jsonEncode(updateData));
      }
    } catch (e) {
      String errorMsg = "Error uninstalling app: $e";
      channel.sink.add(errorMsg);
      setState(() {
        statusMessage = errorMsg;
      });
    }
  }

  @override
  void dispose() {
    if (isConnected) {
      channel.sink.close();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        appBar: AppBar(title: const Text("Remote App Manager")),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  statusMessage,
                  style: TextStyle(
                    fontSize: 18.0,
                    color: isConnected ? Colors.green : Colors.red,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 20),
                Text(
                  "Device ID: $deviceId",
                  style: const TextStyle(fontSize: 14.0),
                ),
                const SizedBox(height: 10),
                Text(
                  "Monitoring ${installedApps.length} installed apps",
                  style: const TextStyle(fontSize: 14.0),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
