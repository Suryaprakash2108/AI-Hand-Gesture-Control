import tkinter as tk
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import threading
import time
from gesture_engine import GestureEngine

# Set modern high-tech visual theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class GestureControlGUI(ctk.CTk):
    def __init__(self, engine: GestureEngine):
        super().__init__()
        
        self.engine = engine
        
        # Window configuration
        self.title("Neural Gesture Control Panel")
        self.geometry("1020x680")
        self.resizable(True, True)
        self.configure(fg_color="#0D0E15") # Dark deep-space background
        
        # Set protocol for graceful closing
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # State tracking
        self.camera_running = False
        
        # Initialize layout
        self.setup_layout()
        
        # Begin checking for new video frames from engine
        self.update_gui_loop()

    def setup_layout(self):
        # Configure root grid weights for dynamic resizing
        self.grid_columnconfigure(0, weight=0) # Sidebar column stays fixed width
        self.grid_columnconfigure(1, weight=1) # Main area expands horizontally
        self.grid_rowconfigure(0, weight=1)    # Full height expansion
        
        # ----------------- SIDEBAR FRAME (LEFT) -----------------
        self.sidebar_frame = ctk.CTkFrame(
            self, 
            width=280, 
            corner_radius=0, 
            fg_color="#121420", # Deep navy dark
            border_color="#1F2235",
            border_width=1
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar_frame.grid_propagate(False)
        
        # Application Brand Header
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="NEURAL GESTURE", 
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#00FFC2" # Neon Cyan/Mint
        )
        self.logo_label.pack(padx=20, pady=(30, 5))
        
        self.sub_logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="SYSTEM CONTROL HUD v1.0", 
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#636E72"
        )
        self.sub_logo_label.pack(padx=20, pady=(0, 20))
        
        # Divider Line
        self.divider = ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="#1F2235")
        self.divider.pack(fill="x", padx=20, pady=10)
        
        # Camera Feed Control Section
        self.camera_ctrl_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="DEVICE CONFIGURATION", 
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#A4B0BE"
        )
        self.camera_ctrl_label.pack(anchor="w", padx=25, pady=(10, 5))
        
        self.camera_select = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["Camera 0", "Camera 1", "Camera 2"],
            command=self.on_camera_select,
            fg_color="#1F2235",
            button_color="#2E314E",
            button_hover_color="#3E4268",
            dropdown_fg_color="#121420",
            dropdown_text_color="#E4E7EB"
        )
        self.camera_select.pack(fill="x", padx=25, pady=10)
        
        self.btn_camera_toggle = ctk.CTkButton(
            self.sidebar_frame,
            text="START CAMERA FEED",
            command=self.toggle_camera,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#00A8FF", # Bright electric blue
            hover_color="#0088CC",
            text_color="#0D0E15",
            height=40
        )
        self.btn_camera_toggle.pack(fill="x", padx=25, pady=10)
        
        # System Control Engine Toggle
        self.switch_gesture_control = ctk.CTkSwitch(
            self.sidebar_frame,
            text="ACTIVATE COMPUTER CONTROL",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#00FFC2",
            progress_color="#00FFC2",
            command=self.toggle_gesture_control,
            state="disabled" # Starts disabled until camera is on
        )
        self.switch_gesture_control.pack(anchor="w", padx=25, pady=25)
        
        # Divider Line
        self.divider2 = ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="#1F2235")
        self.divider2.pack(fill="x", padx=20, pady=10)
        
        # Real-time HUD Telemetry Readouts
        self.hud_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="SYSTEM TELEMETRY HUD", 
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#A4B0BE"
        )
        self.hud_label.pack(anchor="w", padx=25, pady=(10, 5))
        
        # 1. Active Gesture Info Box
        self.info_gesture_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#090A10", height=45)
        self.info_gesture_frame.pack(fill="x", padx=25, pady=6)
        self.info_gesture_frame.pack_propagate(False)
        self.lbl_hud_gesture_title = ctk.CTkLabel(self.info_gesture_frame, text="ACTIVE GESTURE", font=ctk.CTkFont(size=9, weight="bold"), text_color="#57606F")
        self.lbl_hud_gesture_title.pack(anchor="w", padx=10, pady=(4, 0))
        self.lbl_hud_gesture_value = ctk.CTkLabel(self.info_gesture_frame, text="SYSTEM INACTIVE", font=ctk.CTkFont(size=13, weight="bold"), text_color="#DCDDE1")
        self.lbl_hud_gesture_value.pack(anchor="w", padx=10, pady=(0, 4))
        
        # 2. Hand State telemetry
        self.info_hand_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#090A10", height=45)
        self.info_hand_frame.pack(fill="x", padx=25, pady=6)
        self.info_hand_frame.pack_propagate(False)
        self.lbl_hud_hand_title = ctk.CTkLabel(self.info_hand_frame, text="HAND DETECTED STATE", font=ctk.CTkFont(size=9, weight="bold"), text_color="#57606F")
        self.lbl_hud_hand_title.pack(anchor="w", padx=10, pady=(4, 0))
        self.lbl_hud_hand_value = ctk.CTkLabel(self.info_hand_frame, text="NO SIGNAL", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ED4C67")
        self.lbl_hud_hand_value.pack(anchor="w", padx=10, pady=(0, 4))

        # 3. CPU FPS Metric
        self.info_fps_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#090A10", height=45)
        self.info_fps_frame.pack(fill="x", padx=25, pady=6)
        self.info_fps_frame.pack_propagate(False)
        self.lbl_hud_fps_title = ctk.CTkLabel(self.info_fps_frame, text="ENGINE FRAME RATE", font=ctk.CTkFont(size=9, weight="bold"), text_color="#57606F")
        self.lbl_hud_fps_title.pack(anchor="w", padx=10, pady=(4, 0))
        self.lbl_hud_fps_value = ctk.CTkLabel(self.info_fps_frame, text="0 FPS", font=ctk.CTkFont(size=12, weight="bold"), text_color="#DCDDE1")
        self.lbl_hud_fps_value.pack(anchor="w", padx=10, pady=(0, 4))
        
        # ----------------- MAIN VIEWPORT FRAME (RIGHT) -----------------
        self.main_frame = ctk.CTkFrame(self, fg_color="#0D0E15", corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # Configure main frame grid weights
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1) # Camera frame expands vertically
        self.main_frame.grid_rowconfigure(1, weight=0) # Calibration frame stays fixed height
        
        # Camera Feed Canvas Bounding Box
        self.camera_outer_frame = ctk.CTkFrame(
            self.main_frame, 
            width=644, 
            height=484, 
            fg_color="#121420", 
            border_color="#1F2235", 
            border_width=2
        )
        self.camera_outer_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 15))
        self.camera_outer_frame.grid_propagate(False)
        
        self.camera_view = ctk.CTkLabel(
            self.camera_outer_frame, 
            text="NEURAL GESTURE CORE CAMERA DISCONNECTED\n\nClick 'START CAMERA FEED' to initialize.", 
            font=ctk.CTkFont(family="Courier", size=13, weight="bold"),
            text_color="#57606F"
        )
        self.camera_view.place(relx=0.5, rely=0.5, anchor="center")
        
        # ----------------- SETTINGS & CALIBRATION (BOTTOM PANEL) -----------------
        self.control_panel_frame = ctk.CTkFrame(
            self.main_frame, 
            width=644, 
            height=130, 
            fg_color="#121420",
            border_color="#1F2235",
            border_width=1
        )
        self.control_panel_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.control_panel_frame.grid_propagate(False)
        
        # Grid inside Calibration panel (3 sliders side by side)
        self.control_panel_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Slider 1: Cursor Pointer Speed
        self.s1_frame = ctk.CTkFrame(self.control_panel_frame, fg_color="transparent")
        self.s1_frame.grid(row=0, column=0, padx=15, pady=10, sticky="nsew")
        self.lbl_speed_val = ctk.CTkLabel(self.s1_frame, text="Pointer Speed: 1.8x", font=ctk.CTkFont(size=11, weight="bold"), text_color="#A4B0BE")
        self.lbl_speed_val.pack(anchor="w", pady=(0, 5))
        self.slider_speed = ctk.CTkSlider(
            self.s1_frame, 
            from_=1.0, 
            to=5.0, 
            command=self.on_speed_slider,
            progress_color="#00A8FF",
            button_color="#00A8FF",
            button_hover_color="#0088CC"
        )
        self.slider_speed.set(1.8)
        self.slider_speed.pack(fill="x")
        
        # Slider 2: Cursor Stability (EMA Smoothing Factor)
        self.s2_frame = ctk.CTkFrame(self.control_panel_frame, fg_color="transparent")
        self.s2_frame.grid(row=0, column=1, padx=15, pady=10, sticky="nsew")
        self.lbl_stability_val = ctk.CTkLabel(self.s2_frame, text="Cursor Stability: 75%", font=ctk.CTkFont(size=11, weight="bold"), text_color="#A4B0BE")
        self.lbl_stability_val.pack(anchor="w", pady=(0, 5))
        self.slider_stability = ctk.CTkSlider(
            self.s2_frame, 
            from_=1, 
            to=100, 
            command=self.on_stability_slider,
            progress_color="#00FFC2",
            button_color="#00FFC2",
            button_hover_color="#00CC9C"
        )
        self.slider_stability.set(75) # maps to alpha 0.25
        self.slider_stability.pack(fill="x")
        
        # Slider 3: Click Sensitivity (Pinch Threshold)
        self.s3_frame = ctk.CTkFrame(self.control_panel_frame, fg_color="transparent")
        self.s3_frame.grid(row=0, column=2, padx=15, pady=10, sticky="nsew")
        self.lbl_click_val = ctk.CTkLabel(self.s3_frame, text="Click Sensitivity: 28px", font=ctk.CTkFont(size=11, weight="bold"), text_color="#A4B0BE")
        self.lbl_click_val.pack(anchor="w", pady=(0, 5))
        self.slider_click = ctk.CTkSlider(
            self.s3_frame, 
            from_=15, 
            to=60, 
            command=self.on_click_slider,
            progress_color="#ED4C67",
            button_color="#ED4C67",
            button_hover_color="#B53B52"
        )
        self.slider_click.set(28)
        self.slider_click.pack(fill="x")
        
        # Volume Status Bar at the bottom of the Calibration panel
        self.volume_bar_frame = ctk.CTkFrame(self.control_panel_frame, fg_color="transparent")
        self.volume_bar_frame.grid(row=1, column=0, columnspan=3, padx=15, pady=(5, 10), sticky="ew")
        
        self.lbl_vol_title = ctk.CTkLabel(self.volume_bar_frame, text="WINDOWS SYSTEM VOLUME SCALAR", font=ctk.CTkFont(size=10, weight="bold"), text_color="#636E72")
        self.lbl_vol_title.pack(side="left", padx=(0, 10))
        
        self.vol_progress = ctk.CTkProgressBar(
            self.volume_bar_frame, 
            progress_color="#00FFC2", 
            fg_color="#090A10", 
            height=8
        )
        self.vol_progress.pack(side="left", fill="x", expand=True, padx=5)
        self.vol_progress.set(self.engine.get_volume() / 100.0)

    # ----------------- EVENT CALLBACKS & HANDLERS -----------------
    
    def toggle_camera(self):
        if not self.camera_running:
            # Start camera
            self.btn_camera_toggle.configure(text="INITIALIZING CAMERA...", state="disabled", fg_color="#F1C40F")
            
            # Start engine backend thread
            self.engine.start()
            
            # Give OpenCV half a second to bind
            self.after(500, self._finalize_camera_start)
        else:
            # Stop camera
            self.switch_gesture_control.deselect()
            self.switch_gesture_control.configure(state="disabled")
            self.engine.stop()
            self.camera_running = False
            self.btn_camera_toggle.configure(text="START CAMERA FEED", fg_color="#00A8FF", state="normal")
            self.camera_view.configure(image="", text="NEURAL GESTURE CORE CAMERA DISCONNECTED\n\nClick 'START CAMERA FEED' to initialize.")
            self.lbl_hud_gesture_value.configure(text="SYSTEM INACTIVE", text_color="#DCDDE1")
            self.lbl_hud_hand_value.configure(text="NO SIGNAL", text_color="#ED4C67")
            self.lbl_hud_fps_value.configure(text="0 FPS")

    def _finalize_camera_start(self):
        self.camera_running = True
        self.btn_camera_toggle.configure(text="STOP CAMERA FEED", fg_color="#EA2027", state="normal") # Red color
        self.switch_gesture_control.configure(state="normal")
        self.camera_view.configure(text="")

    def toggle_gesture_control(self):
        is_active = self.switch_gesture_control.get() == 1
        self.engine.update_settings(active=is_active)
        if is_active:
            self.switch_gesture_control.configure(text_color="#00FFC2")
        else:
            self.switch_gesture_control.configure(text_color="#636E72")

    def on_camera_select(self, option):
        # Extract integer camera index from string e.g., "Camera 0" -> 0
        idx = int(option.split(" ")[-1])
        self.engine.update_settings(camera_index=idx)

    def on_speed_slider(self, val):
        self.lbl_speed_val.configure(text=f"Pointer Speed: {val:.1f}x")
        self.engine.update_settings(pointer_speed=val)

    def on_stability_slider(self, val):
        stability = int(val)
        self.lbl_stability_val.configure(text=f"Cursor Stability: {stability}%")
        
        # Stability is the inverse of the smoothing factor (alpha)
        # stability = 100 -> alpha = 0.05 (most stable/smooth, slightly laggy)
        # stability = 1 -> alpha = 1.00 (raw, very fast, jittery)
        # Formula: alpha = 1.0 - (stability - 1) / 99 * 0.95
        alpha = 1.0 - ((stability - 1) / 99.0) * 0.95
        self.engine.update_settings(alpha=alpha)

    def on_click_slider(self, val):
        pixels = int(val)
        self.lbl_click_val.configure(text=f"Click Sensitivity: {pixels}px")
        self.engine.update_settings(click_threshold=float(pixels))

    # ----------------- GUI TELEMETRY UPDATE LOOP -----------------
    
    def update_gui_loop(self):
        """Standard Tkinter after() poll loop to consume data from background thread."""
        if self.camera_running:
            # Thread-safe read of frame and state variables
            frame, stats = self.engine.get_latest_frame_and_stats()
            
            if frame is not None:
                try:
                    # Convert OpenCV BGR to RGB and then to PIL Image
                    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(rgb_image)
                    
                    # Get actual dimensions of the camera bounding box
                    # Subtract 4 to account for border_width=2 on both sides
                    outer_w = self.camera_outer_frame.winfo_width() - 4
                    outer_h = self.camera_outer_frame.winfo_height() - 4
                    
                    h_frame, w_frame = frame.shape[:2]
                    aspect_ratio = w_frame / h_frame
                    
                    if outer_w < 10 or outer_h < 10:
                        new_w, new_h = 640, 480
                    else:
                        # Scale to fit while maintaining aspect ratio
                        if outer_w / outer_h > aspect_ratio:
                            new_h = outer_h
                            new_w = int(outer_h * aspect_ratio)
                        else:
                            new_w = outer_w
                            new_h = int(outer_w / aspect_ratio)
                    
                    # Display inside camera viewport using CustomTkinter's native scaling-aware CTkImage
                    ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(new_w, new_h))
                    self.camera_view.configure(image=ctk_img)
                    self.camera_view.ctk_img = ctk_img # prevent GC
                except Exception as e:
                    print(f"Frame render error: {e}")
            
            # Update HUD status panels
            gesture = stats["gesture"]
            hand_detected = stats["hand_detected"]
            fps = stats["fps"]
            vol_pct = stats["volume_level"]
            
            # 1. Update Gesture Telemetry
            self.lbl_hud_gesture_value.configure(text=gesture)
            if gesture in ["LEFT CLICK", "RIGHT CLICK", "DRAGGING"]:
                self.lbl_hud_gesture_value.configure(text_color="#00FFC2") # Teal
            elif gesture == "VOLUME CONTROL":
                self.lbl_hud_gesture_value.configure(text_color="#F1C40F") # Yellow
            elif gesture == "SCROLL MODE":
                self.lbl_hud_gesture_value.configure(text_color="#00A8FF") # Blue
            elif "TRIGGERED" in gesture:
                self.lbl_hud_gesture_value.configure(text_color="#9B59B6") # Purple
            else:
                self.lbl_hud_gesture_value.configure(text_color="#DCDDE1") # Grayish-white
                
            # 2. Update Hand Detected Indicator
            if hand_detected:
                self.lbl_hud_hand_value.configure(text="SIGNAL RESOLVED", text_color="#00FFC2")
            else:
                self.lbl_hud_hand_value.configure(text="NO SIGNAL", text_color="#ED4C67")
                
            # 3. Update FPS Readout
            self.lbl_hud_fps_value.configure(text=f"{fps} FPS")
            
            # 4. Update Volume Master Progress Bar
            self.vol_progress.set(vol_pct / 100.0)
            
        # Re-queue update check every 15ms (approx 60 ticks per second)
        self.after(15, self.update_gui_loop)

    def on_closing(self):
        """Graces closed all threads and processes upon window closing."""
        print("Closing application...")
        self.engine.stop()
        self.destroy()
