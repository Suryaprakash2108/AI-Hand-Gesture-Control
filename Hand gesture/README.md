# AI Hand Gesture Computer Control System

An advanced, real-time computer control application that allows you to operate your Windows laptop completely hands-free using simple hand gestures through your webcam!

The system is equipped with a high-fidelity **Skeletal Hand Landmark Tracking Engine (MediaPipe)** and a sleek, interactive **Dark Mode HUD Dashboard (CustomTkinter)**.

---

## Features

* **Virtual Trackpad Zone**: Translates localized hand movements into full-screen mouse navigation, eliminating hand fatigue.
* **Jitter-Free Cursor Control**: Incorporates an Exponential Moving Average (EMA) smoothing filter to absorb minor hand tremors.
* **Native Audio Control**: Integrates directly with Windows Core Audio APIs (`pycaw`) to let you slide and adjust volume in real-time.
* **Sustained Hold Gestures**: Recognizes continuous hand poses (like closing a Fist or holding a Palm open) to trigger play/pause or mute media.
* **Advanced Real-time HUD**: Displays neon-skeleton tracking, active gesture categories, frame rates (FPS), and system volume gauges.
* **On-the-fly Calibration**: Sliders to configure Pointer Speed, Cursor Stability, and Click Sensitivity.

---

## Quick Start Guide

Follow these three simple steps to start controlling your computer with hand gestures:

### Step 1: Open PowerShell in the Project Directory
Navigate to your project directory on your desktop:
```powershell
cd "c:\Users\surya\OneDrive\Desktop\Hand gesture"
```

### Step 2: Activate the Virtual Environment
Activate the isolated Python virtual environment:
```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 3: Run the Application
Boot up the dashboard and neural engine:
```powershell
python main.py
```

---

## How to Use the App

1. **Select Camera**: Use the dropdown in the sidebar if you have multiple cameras (default is Camera 0).
2. **Start Feed**: Click the bright blue **"START CAMERA FEED"** button. The camera view will boot up with a visual purple **Virtual Trackpad** box.
3. **Calibrate**:
   * Raise your hand in front of the camera. The neon-green skeleton should map overlay lines across your knuckles and fingers in real-time.
   * Toggle the **"ACTIVATE COMPUTER CONTROL"** switch to start sending gestures to the OS.
4. **Tune Parameters**:
   * **Pointer Speed**: Adjusts how fast the cursor covers your screen.
   * **Cursor Stability**: Higher percentages result in super-smooth, jitter-free cursor movements, while lower values are more responsive but sensitive to hand shakes.
   * **Click Sensitivity**: The distance threshold for pinch-to-click.

---

## Gesture Reference Dictionary

Keep your hand upright and face the webcam. The system detects gestures by analyzing the relative geometry between your finger tips and joints:

| Gesture Name | Hand Pose / Action | Screen Trigger |
| :--- | :--- | :--- |
| **Cursor Movement** | **1 Finger Open**: Only **Index finger OPEN**, all other fingers closed. Move your index tip within the purple boundary box. | Smoothly moves mouse cursor. |
| **Left Click** | **3 Fingers Open**: **Index + Middle + Ring fingers OPEN**, Pinky closed. | Triggers Left Click immediately. |
| **Drag & Drop** | **3 Fingers Open & Held**: **Index + Middle + Ring fingers OPEN** and held still for more than 0.5 seconds. | Holds left click down for dragging. Close middle & ring fingers back to Navigation to drop. |
| **Right Click** | **4 Fingers Open**: **Index + Middle + Ring + Pinky fingers OPEN**, Thumb closed (tucked). | Triggers Right Click. |
| **Scroll Mode** | **2 Fingers Open**: **Index + Middle fingers OPEN**, Ring + Pinky closed. Move hand Up/Down. | Scrolls browser pages or documents Up/Down. |
| **Volume Control** | **L-Shape**: **Thumb + Index OPEN**, others closed. Vary the distance between thumb and index tips. | Scales Windows master volume in real-time (0% to 100%). |
| **Play/Pause Media** | **5 Fingers Open**: **Full Open Palm (all 5 fingers open)**. Hold still for 1 second. | Presses the System Play/Pause key once. |
| **Mute / Unmute** | **Fist**: **All 5 fingers CLOSED**. Hold still for 1 second. | Presses the System Mute key. |

---

## Troubleshooting

* **Mouse cursor jumps to corner and freezes**:
  This occurs if PyAutoGUI triggers its default safety fail-safe mechanism when you drag the cursor to a physical edge of your screen. We have safely disabled PyAutoGUI's failsafe within the engine to ensure seamless tracking.
* **No webcam feed displays**:
  Verify that your webcam is not currently being used by another application (e.g. Zoom, Teams, Discord). Select a different index (e.g., "Camera 1") from the dropdown if you are using an external USB webcam.
* **Click triggers too easily or not easily enough**:
  Use the **Click Sensitivity** slider. If it clicks when you don't want to, decrease the slider. If it's hard to trigger a click, increase the slider.
