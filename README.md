Process flow 
RPLidar A1 → ESP32 (via UART/USB).
ESP32 → WiFi → PC (sends lidar scan data).
PC (does the heavy lifting: visualization, SLAM, saving/export).
PC → ESP32 → Arduino (sends motion commands).
Arduino (drives the motors).
