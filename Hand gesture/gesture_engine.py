import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math
import time
import threading
from screeninfo import get_monitors
from smoothing import EMAFilter

# Try importing pycaw for Windows volume control
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False

# PyAutoGUI configuration to prevent freezing and enable rapid execution
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.001

class GestureEngine:
    def __init__(self, callback=None):
        self.callback = callback
        
        # Engine state controls
        self.is_running = False
        self.is_gesture_control_active = False
        self.camera_index = 0
        
        # Adjustable parameters (can be configured via GUI)
        self.pointer_speed = 1.8
        self.click_threshold = 28.0  # in pixels
        self.scroll_speed = 5
        
        # Coordinate smoothing
        self.ema_filter = EMAFilter(alpha=0.25)
        
        # Window & Screen metrics
        self.frame_width = 640
        self.frame_height = 480
        
        try:
            primary_monitor = get_monitors()[0]
            self.screen_width = primary_monitor.width
            self.screen_height = primary_monitor.height
        except Exception:
            self.screen_width, self.screen_height = pyautogui.size()
            
        # Virtual Trackpad Zone (centered rectangle in the 640x480 camera view)
        # Coordinates: [x_min, y_min, x_max, y_max]
        self.trackpad_w = 320
        self.trackpad_h = 240
        self.trackpad_x1 = (self.frame_width - self.trackpad_w) // 2
        self.trackpad_y1 = (self.frame_height - self.trackpad_h) // 2 - 20 # slight upward offset for comfort
        self.trackpad_x2 = self.trackpad_x1 + self.trackpad_w
        self.trackpad_y2 = self.trackpad_y1 + self.trackpad_h
        
        # Windows Master Volume Controller
        self.volume_controller = None
        self.init_volume_control()
        
        # Gesture tracking and execution states
        self.left_click_held = False
        self.right_click_held = False
        self.drag_start_time = None
        self.is_dragging = False
        self.prev_scroll_y = None
        
        # Timing controls for gesture rate limiting (Play/Pause, Mute)
        self.last_action_time = 0
        self.action_cooldown = 2.0  # seconds
        self.gesture_hold_start = None
        self.held_gesture_name = None
        
        # Thread handles
        self.thread = None
        self.cap = None
        
        # Shared thread-safe state variables (read by GUI)
        self.latest_frame = None
        self.status_data = {
            "fps": 0,
            "gesture": "STOPPED",
            "coords": (0, 0),
            "click_dist": 0.0,
            "volume_level": 0,
            "hand_detected": False
        }
        self.lock = threading.Lock()

    def init_volume_control(self):
        """Initializes Pycaw Windows Master Volume endpoint interface."""
        if not PYCAW_AVAILABLE:
            print("Pycaw is not available. Volume control will be disabled.")
            return
        try:
            devices = AudioUtilities.GetSpeakers()
            self.volume_controller = devices.EndpointVolume
            print("Successfully initialized system volume control (Pycaw).")
        except Exception as e:
            print(f"Error initializing system volume: {e}")
            self.volume_controller = None

    def set_volume(self, percent):
        """Sets master volume level (0.0 to 1.0) on Windows."""
        if not self.volume_controller:
            return
        try:
            # Map 0-100 percentage to 0.0-1.0 float scalar
            val = max(0.0, min(1.0, percent / 100.0))
            self.volume_controller.SetMasterVolumeLevelScalar(val, None)
        except Exception as e:
            print(f"Failed to set volume: {e}")

    def get_volume(self):
        """Gets current master volume level as integer percentage (0-100)."""
        if not self.volume_controller:
            return 0
        try:
            val = self.volume_controller.GetMasterVolumeLevelScalar()
            return int(val * 100)
        except Exception:
            return 0

    def start(self):
        """Starts the background gesture recognition engine thread."""
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stops the engine and releases video resources."""
        self.is_running = False
        self.is_gesture_control_active = False
        if self.thread:
            self.thread.join(timeout=1.0)
        self._release_camera()

    def update_settings(self, active=None, pointer_speed=None, alpha=None, click_threshold=None, camera_index=None):
        """Thread-safe update of engine parameters from the GUI."""
        with self.lock:
            if active is not None:
                self.is_gesture_control_active = active
                if not active:
                    self.ema_filter.reset()
                    self._reset_click_states()
            if pointer_speed is not None:
                self.pointer_speed = pointer_speed
            if alpha is not None:
                self.ema_filter.set_alpha(alpha)
            if click_threshold is not None:
                self.click_threshold = click_threshold
            if camera_index is not None and camera_index != self.camera_index:
                # If running, we need to hot-swap cameras safely
                self.camera_index = camera_index
                if self.is_running:
                    # Signal thread to recreate the VideoCapture
                    threading.Thread(target=self._reconnect_camera, daemon=True).start()

    def _reset_click_states(self):
        """Releases any active clicks and resets tracking variables."""
        if self.left_click_held or self.is_dragging:
            pyautogui.mouseUp()
        if self.right_click_held:
            pyautogui.mouseUp(button='right')
        self.left_click_held = False
        self.right_click_held = False
        self.is_dragging = False
        self.drag_start_time = None
        self.prev_scroll_y = None
        self.gesture_hold_start = None
        self.held_gesture_name = None

    def _reconnect_camera(self):
        """Handles hot-swapping webcam sources safely."""
        with self.lock:
            self._release_camera()
            self.cap = cv2.VideoCapture(self.camera_index)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)

    def _release_camera(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    def _calculate_distance(self, p1, p2):
        """Returns Euclidean distance between two 2D pixel coordinates."""
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def _run_loop(self):
        # Initialize MediaPipe Hands API
        mp_hands = mp.solutions.hands
        mp_draw = mp.solutions.drawing_utils
        
        # Stylized neon drawing configurations
        landmark_style = mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3)
        connection_style = mp_draw.DrawingSpec(color=(0, 255, 100), thickness=2)
        
        hands = mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        
        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        
        prev_time = time.time()
        
        while self.is_running:
            success = False
            frame = None
            
            if self.cap and self.cap.isOpened():
                success, frame = self.cap.read()
                
            if not success or frame is None:
                # Wait a bit and try to reconnect
                time.sleep(0.03)
                continue
                
            # 1. Flip frame horizontally to mimic mirror reflection for intuitive gesture mapping
            frame = cv2.flip(frame, 1)
            
            # Convert to RGB for MediaPipe processing
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)
            
            # Local iteration status metadata
            current_gesture = "NAVIGATION" if self.is_gesture_control_active else "MONITORING"
            hand_detected = False
            index_x, index_y = 0, 0
            click_dist = 0.0
            volume_level = self.get_volume()
            
            # Draw Virtual Trackpad boundaries on screen
            cv2.rectangle(
                frame, 
                (self.trackpad_x1, self.trackpad_y1), 
                (self.trackpad_x2, self.trackpad_y2), 
                (255, 0, 150), 
                2, 
                lineType=cv2.LINE_AA
            )
            # Add neon backdrop glow to trackpad label
            cv2.putText(
                frame, "VIRTUAL TRACKPAD", 
                (self.trackpad_x1 + 5, self.trackpad_y1 - 8), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 150), 1, cv2.LINE_AA
            )
            
            if results.multi_hand_landmarks:
                hand_detected = True
                hand_landmarks = results.multi_hand_landmarks[0]
                
                # Convert normalized landmarks to absolute pixel coordinates
                h, w, _ = frame.shape
                lm_points = []
                for lm in hand_landmarks.landmark:
                    lm_points.append((int(lm.x * w), int(lm.y * h)))
                
                # Render beautifully designed custom neural skeletal tracking
                mp_draw.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    landmark_style, connection_style
                )
                
                # Landmark references:
                # 0: Wrist, 4: Thumb Tip, 8: Index Tip, 12: Middle Tip, 16: Ring Tip, 20: Pinky Tip
                # 2: Thumb MCP, 6: Index PIP, 10: Middle PIP, 14: Ring PIP, 18: Pinky PIP
                wrist = lm_points[0]
                thumb_tip = lm_points[4]
                index_tip = lm_points[8]
                middle_tip = lm_points[12]
                ring_tip = lm_points[16]
                pinky_tip = lm_points[20]
                
                # 2. Extract relative distance-based finger open states (orientation independent)
                # A finger is OPEN if its tip is further from the wrist than its PIP joint.
                is_index_open = self._calculate_distance(wrist, index_tip) > self._calculate_distance(wrist, lm_points[6])
                is_middle_open = self._calculate_distance(wrist, middle_tip) > self._calculate_distance(wrist, lm_points[10])
                is_ring_open = self._calculate_distance(wrist, ring_tip) > self._calculate_distance(wrist, lm_points[14])
                is_pinky_open = self._calculate_distance(wrist, pinky_tip) > self._calculate_distance(wrist, lm_points[18])
                
                # Thumb is open if its tip is further from Pinky MCP (17) than Thumb MCP (2) is.
                is_thumb_open = self._calculate_distance(thumb_tip, lm_points[17]) > self._calculate_distance(lm_points[2], lm_points[17]) * 1.25
                
                # Store coordinates of index tip for overlay drawing
                index_x, index_y = index_tip[0], index_tip[1]
                
                # Distances for clicks
                index_thumb_dist = self._calculate_distance(index_tip, thumb_tip)
                middle_thumb_dist = self._calculate_distance(middle_tip, thumb_tip)
                click_dist = index_thumb_dist
                
                # Core gesture recognition engine
                if self.is_gesture_control_active:
                    now = time.time()
                    
                    # A. Play/Pause (5 Fingers Open) - Sustained hold gesture
                    if is_index_open and is_middle_open and is_ring_open and is_pinky_open and is_thumb_open:
                        current_gesture = "PLAY / PAUSE (HOLD)"
                        cv2.putText(frame, "HOLD OPEN PALM...", (index_x + 15, index_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1, cv2.LINE_AA)
                        
                        if self.held_gesture_name != "PLAY_PAUSE" or self.gesture_hold_start is None:
                            self.held_gesture_name = "PLAY_PAUSE"
                            self.gesture_hold_start = now
                        elif now - self.gesture_hold_start >= 1.0: # Hold for 1 second
                            if now - self.last_action_time >= self.action_cooldown:
                                pyautogui.press('playpause')
                                self.last_action_time = now
                                current_gesture = "TRIGGERED: PLAY/PAUSE"
                                self.ema_filter.reset()
                    
                    # B. Mute/Unmute (Fist - All fingers closed) - Sustained hold gesture
                    elif not is_index_open and not is_middle_open and not is_ring_open and not is_pinky_open and not is_thumb_open:
                        current_gesture = "MUTE (HOLD)"
                        cv2.putText(frame, "HOLD FIST...", (wrist[0] - 30, wrist[1] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
                        
                        if self.held_gesture_name != "MUTE" or self.gesture_hold_start is None:
                            self.held_gesture_name = "MUTE"
                            self.gesture_hold_start = now
                        elif now - self.gesture_hold_start >= 1.0:
                            if now - self.last_action_time >= self.action_cooldown:
                                pyautogui.press('volumemute')
                                self.last_action_time = now
                                current_gesture = "TRIGGERED: MUTE"
                    
                    # C. Volume Control (L-Shape: Index + Thumb Open, others closed)
                    elif is_thumb_open and is_index_open and not is_middle_open and not is_ring_open and not is_pinky_open:
                        current_gesture = "VOLUME CONTROL"
                        # Visual feedback - draw L-shape measurement line
                        cv2.line(frame, thumb_tip, index_tip, (0, 255, 255), 2, lineType=cv2.LINE_AA)
                        cv2.circle(frame, thumb_tip, 6, (0, 255, 255), -1)
                        cv2.circle(frame, index_tip, 6, (0, 255, 255), -1)
                        
                        # Map pixel distance to Volume percentage
                        # typically range is 30px (0%) to 160px (100%)
                        d = index_thumb_dist
                        min_d, max_d = 30.0, 160.0
                        vol_pct = int(((d - min_d) / (max_d - min_d)) * 100)
                        vol_pct = max(0, min(100, vol_pct))
                        
                        self.set_volume(vol_pct)
                        volume_level = vol_pct
                        
                        # Draw visual volume percentage indicator on HUD
                        cv2.putText(
                            frame, f"VOL: {vol_pct}%", 
                            (int((thumb_tip[0] + index_tip[0])/2) + 10, int((thumb_tip[1] + index_tip[1])/2)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2, cv2.LINE_AA
                        )
                        self.held_gesture_name = None
                        self.gesture_hold_start = None
                        
                    # D. Scroll Mode (Index + Middle Open and Close Together)
                    elif is_index_open and is_middle_open and not is_ring_open and not is_pinky_open:
                        current_gesture = "SCROLL MODE"
                        
                        # Draw connecting line between scroll fingers
                        cv2.line(frame, index_tip, middle_tip, (255, 100, 0), 2, cv2.LINE_AA)
                        
                        mid_y = (index_tip[1] + middle_tip[1]) // 2
                        if self.prev_scroll_y is not None:
                            dy = mid_y - self.prev_scroll_y
                            scroll_thresh = 4 # small movements filter
                            
                            if abs(dy) > scroll_thresh:
                                # OpenCV y decreases as hand goes UP, so:
                                # if dy > 0 (hand went down), scroll down (-scroll_speed)
                                # if dy < 0 (hand went up), scroll up (+scroll_speed)
                                amt = -int(np.sign(dy) * self.scroll_speed)
                                pyautogui.scroll(amt)
                        
                        self.prev_scroll_y = mid_y
                        self.held_gesture_name = None
                        self.gesture_hold_start = None
                        self.ema_filter.reset()
                        
                    # E. Left Click, Right Click, Dragging or Cursor Movement (Default)
                    else:
                        self.prev_scroll_y = None
                        self.held_gesture_name = None
                        self.gesture_hold_start = None
                        
                        # 1. 4-Finger Right Click (Index, Middle, Ring, Pinky open, Thumb closed)
                        if is_index_open and is_middle_open and is_ring_open and is_pinky_open and not is_thumb_open:
                            # Visual feedback highlights on fingertips
                            cv2.circle(frame, index_tip, 8, (0, 0, 255), -1)
                            cv2.circle(frame, middle_tip, 8, (0, 0, 255), -1)
                            cv2.circle(frame, ring_tip, 8, (0, 0, 255), -1)
                            cv2.circle(frame, pinky_tip, 8, (0, 0, 255), -1)
                            
                            if not self.right_click_held:
                                pyautogui.rightClick()
                                self.right_click_held = True
                                current_gesture = "RIGHT CLICK"
                                
                        # 2. 3-Finger Left Click / Drag & Drop (Index, Middle, Ring open, Pinky closed)
                        elif is_index_open and is_middle_open and is_ring_open and not is_pinky_open:
                            # Visual feedback highlights on fingertips
                            cv2.circle(frame, index_tip, 8, (0, 255, 0), -1)
                            cv2.circle(frame, middle_tip, 8, (0, 255, 0), -1)
                            cv2.circle(frame, ring_tip, 8, (0, 255, 0), -1)
                            
                            if not self.left_click_held:
                                self.left_click_held = True
                                self.drag_start_time = now
                                pyautogui.click() # single click instantly
                                current_gesture = "LEFT CLICK"
                            elif now - self.drag_start_time > 0.5 and not self.is_dragging:
                                # sustained 3-finger open pose = Drag & Drop active
                                self.is_dragging = True
                                pyautogui.mouseDown()
                                current_gesture = "DRAGGING"
                                
                            if self.is_dragging:
                                current_gesture = "DRAGGING"
                                cv2.putText(frame, "DRAG ACTIVE", (index_x + 15, index_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
                                
                        else:
                            # Release click and drag states when fingers close or return to navigation
                            if self.left_click_held:
                                if self.is_dragging:
                                    pyautogui.mouseUp()
                                    self.is_dragging = False
                                    current_gesture = "DRAG RELEASED"
                                self.left_click_held = False
                                self.drag_start_time = None
                                
                            if self.right_click_held:
                                self.right_click_held = False
                                
                            current_gesture = "CURSOR MOVEMENT"
                            
                        # Move mouse cursor in Left Click, Right Click, or default Cursor Movement state
                        # We map the index finger tip position from the Virtual Trackpad box
                        # to the screen width and height.
                        ix, iy = index_tip[0], index_tip[1]
                        
                        # Normalize index coordinates inside Virtual Trackpad box
                        nx = (ix - self.trackpad_x1) / self.trackpad_w
                        ny = (iy - self.trackpad_y1) / self.trackpad_h
                        
                        # Clip boundary bounds
                        nx = max(0.0, min(1.0, nx))
                        ny = max(0.0, min(1.0, ny))
                        
                        # Multiply by speed multiplier for sensitivity
                        nx_scaled = 0.5 + (nx - 0.5) * self.pointer_speed
                        ny_scaled = 0.5 + (ny - 0.5) * self.pointer_speed
                        nx_scaled = max(0.0, min(1.0, nx_scaled))
                        ny_scaled = max(0.0, min(1.0, ny_scaled))
                        
                        # Calculate screen coordinates
                        screen_x = int(nx_scaled * self.screen_width)
                        screen_y = int(ny_scaled * self.screen_height)
                        
                        # Apply coordinate smoothing filter (EMA)
                        smoothed_x, smoothed_y = self.ema_filter.update(screen_x, screen_y)
                        
                        # Trigger system mouse cursor move
                        pyautogui.moveTo(smoothed_x, smoothed_y)
                        
                        # Draw visual trackpad cursor inside OpenCV frame for calibration
                        cv2.circle(frame, (ix, iy), 6, (0, 255, 0), 2)
                        cv2.putText(
                            frame, f"CURSOR: ({smoothed_x}, {smoothed_y})", 
                            (ix + 15, iy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA
                        )
            else:
                # Release keys if hand leaves camera field
                self._reset_click_states()
                self.ema_filter.reset()
                current_gesture = "NO HAND DETECTED"
            
            # FPS Calculation
            curr_time = time.time()
            fps = int(1.0 / (curr_time - prev_time))
            prev_time = curr_time
            
            # Store results thread-safely
            with self.lock:
                self.latest_frame = frame.copy()
                self.status_data = {
                    "fps": fps,
                    "gesture": current_gesture if self.is_gesture_control_active else "MONITORING (PAUSED)",
                    "coords": (index_x, index_y),
                    "click_dist": round(click_dist, 1),
                    "volume_level": volume_level,
                    "hand_detected": hand_detected
                }
                
            # Invoke callback if set to alert GUI thread that a new frame is ready
            if self.callback:
                self.callback()
                
            # Frame pacing rate limiting (approx 30-40 FPS to conserve CPU)
            time.sleep(0.015)
            
        hands.close()
        self._release_camera()

    def get_latest_frame_and_stats(self):
        """Thread-safe acquisition of the latest processed frame and HUD metadata."""
        with self.lock:
            if self.latest_frame is None:
                return None, self.status_data
            return self.latest_frame.copy(), self.status_data.copy()
