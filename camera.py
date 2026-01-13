import datetime
import cv2
import threading
import time
import numpy as np
import uuid
import os
import face_recognition
from ultralytics import YOLO

class VideoCamera(object):
    def __init__(self):
        # Using 0 for the default camera.
        self.video = cv2.VideoCapture(0)
        if not self.video.isOpened():
            print("Warning: Could not open video device 0. Please check camera permissions.")
        self.lock = threading.Lock()
        
        # Global state
        self.rois = [] # List of dicts: {'id': str, 'name': str, 'rect': (x, y, w, h)}
        self.away_mode = False
        self.alarm_active = False
        self.dismissed_until = 0 # Timestamp until when alarm is dismissed
        
        # Tamper Detection State
        self.tamper_start_time = None
        self.tamper_active = False
        self.night_mode_enabled = False # New Feature
        
        # High Confidence Person Detection State
        self.person_detection_start_time = None
        self.last_person_seen_time = 0
        
        # Weapon Detection State
        self.weapon_active = False
        self.weapon_check_enabled = False # Default: OFF. User must enable it.
        self.weapon_detection_start_time = None
        self.last_weapon_seen_time = 0
        self.confirmed_weapon_boxes = []
        # Performance & Motion
        self.frame_count = 0
        self.last_detections = [] # [(rect, type)] type='person'
        self.average_frame = None # For motion detection
        
        # Models
        print("Loading Person Detection Model (YOLOv8 Small)...")
        # Upgraded to 's' model for better accuracy (less false positives like pillows)
        self.model_person = YOLO('yolov8s.pt')
        
        print("Loading Weapon Detection Model (Custom)...")
        # Custom model for Handgun, Knife, Dagger, Axe, Hammer
        self.model_weapon = YOLO('my_final_weapon_model.pt')
        
        # --- Face Recognition Setup ---
        self.known_face_encodings = []
        self.known_face_names = []
        self.load_known_faces()
        
 


    def load_known_faces(self):
        """Load known faces from face_dataset folder."""
        print("Loading Known Faces...")
        dataset_path = "face_dataset"
        if not os.path.exists(dataset_path):
            print(f"Warning: {dataset_path} not found.")
            return

        for person_name in os.listdir(dataset_path):
            person_dir = os.path.join(dataset_path, person_name)
            if not os.path.isdir(person_dir):
                continue
                
            for image_name in os.listdir(person_dir):
                if image_name.startswith('.'): continue
                image_path = os.path.join(person_dir, image_name)
                try:
                    image = face_recognition.load_image_file(image_path)
                    encodings = face_recognition.face_encodings(image)
                    if encodings:
                        self.known_face_encodings.append(encodings[0])
                        self.known_face_names.append(person_name)
                        print(f"Loaded: {person_name} ({image_name})")
                except Exception as e:
                    print(f"Error loading {image_path}: {e}")
        print(f"Total Known Faces: {len(self.known_face_names)}")

    def __del__(self):
        self.video.release()

    def add_roi(self, x, y, w, h, name="Zone"):
        """Add a new Region of Interest."""
        with self.lock:
            roi_id = str(uuid.uuid4())
            self.rois.append({
                'id': roi_id,
                'name': name,
                'rect': (int(x), int(y), int(w), int(h))
            })
            print(f"Added ROI: {name} {self.rois[-1]}")
            return roi_id

    def delete_roi(self, roi_id):
        """Delete an ROI by ID."""
        with self.lock:
            self.rois = [r for r in self.rois if r['id'] != roi_id]
            print(f"Deleted ROI: {roi_id}")

    def get_rois(self):
        with self.lock:
            return self.rois

    def toggle_away_mode(self, status):
        """Enable or disable Away Mode."""
        with self.lock:
            self.away_mode = status
            self.alarm_active = False
            self.weapon_active = False
            print(f"Away Mode: {self.away_mode}")

    def toggle_night_mode(self, status):
        """Enable or disable Night Mode (12 AM - 5 AM)."""
        with self.lock:
            self.night_mode_enabled = status
            print(f"Night Mode: {self.night_mode_enabled}")

    def toggle_weapon_detection(self, status):
        """Enable or disable Specific Weapon Detection."""
        with self.lock:
            self.weapon_check_enabled = status
            self.weapon_active = False # Reset alert if toggled off
            print(f"Weapon Detection Enabled: {self.weapon_check_enabled}")

    def dismiss_alert(self):
        with self.lock:
            self.alarm_active = False
            self.tamper_active = False
            self.weapon_active = False
            # Prevent re-triggering for 5 seconds
            self.dismissed_until = time.time() + 5

    def reset_alarm(self):
        with self.lock:
            self.alarm_active = False
            self.tamper_active = False

    def get_status(self):
        with self.lock:
            # Check if night mode is currently ACTIVE
            current_hour = datetime.datetime.now().hour
            is_night_time = 0 <= current_hour < 5
            night_mode_active = self.night_mode_enabled and is_night_time

            return {
                "away_mode": self.away_mode,
                "night_mode_enabled": self.night_mode_enabled,
                "night_mode_active": night_mode_active,
                "alarm_active": self.alarm_active,
                "tamper_active": self.tamper_active,
                "weapon_active": self.weapon_active,
                "weapon_check_enabled": self.weapon_check_enabled,
                "roi_count": len(self.rois)
            }

    def check_tampering(self, image):
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Calculate mean and standard deviation
        mean, std_dev = cv2.meanStdDev(gray)
        mean_val = mean[0][0]
        std_val = std_dev[0][0]
        
        # Thresholds: Strict Black Check
        # User requested "100% black", so we use a very low mean threshold (e.g., < 2)
        # We allow a tiny bit of noise (0-2) but mostly pitch black.
        is_tampered = mean_val < 2
        
        current_time = time.time()
        
        if is_tampered:
            if self.tamper_start_time is None:
                self.tamper_start_time = current_time
            elif current_time - self.tamper_start_time > 5: # 5 Seconds Persistence
                # Only activate if we haven't recently dismissed it
                if current_time > self.dismissed_until:
                    self.tamper_active = True
        else:
            self.tamper_start_time = None
            if not self.alarm_active and not self.weapon_active:
                if current_time > self.dismissed_until:
                     self.tamper_active = False

    def get_motion_mask(self, gray_frame):
        """Compute motion mask between current and average frame."""
        if self.average_frame is None:
            self.average_frame = gray_frame.copy().astype("float")
            return np.zeros_like(gray_frame)
        
        # Accumulate weighted average
        # Alpha 0.02 means background updates slowly (good for detecting static-ish people)
        # 0.5 was too fast (person became background instantly)
        cv2.accumulateWeighted(gray_frame, self.average_frame, 0.02)
        
        # Compute difference
        frame_diff = cv2.absdiff(gray_frame, cv2.convertScaleAbs(self.average_frame))
        
        # Threshold to get motion
        _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
        return thresh

    def is_box_moving(self, box_coords, motion_mask, threshold=0.01):
        """Check if a bounding box area has significant motion."""
        x1, y1, x2, y2 = box_coords
        h, w = motion_mask.shape
        
        # Clamp to image bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        if x2 <= x1 or y2 <= y1: return False
        
        roi_motion = motion_mask[y1:y2, x1:x2]
        motion_pixels = cv2.countNonZero(roi_motion)
        total_pixels = (x2 - x1) * (y2 - y1)
        
        if total_pixels == 0: return False
        
        ratio = motion_pixels / total_pixels
        return ratio > threshold

    def get_frame(self):
        success, image = self.video.read()
        if not success:
            return None

        # Always Mirror View
        image = cv2.flip(image, 1)
        
        # Prep for motion detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        motion_mask = self.get_motion_mask(gray)

        with self.lock:
            current_time = time.time()
            
            # Check Tampering (Always active 24/7)
            self.check_tampering(image)
            
            if self.tamper_active:
                 cv2.putText(image, "CAMERA TAMPERED!", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            
            # --- Detection Logic ---
            current_hour = datetime.datetime.now().hour
            is_night_time = 0 <= current_hour < 5
            
            # ROI Based Person Detection (Away/Night Only)
            should_detect_person = self.away_mode or (self.night_mode_enabled and is_night_time)
            
            # Frame Skipping (Process every 3rd frame)
            self.frame_count += 1
            if self.frame_count % 3 == 0:
                self.last_detections = [] # Clear previous detections

                # --- 1. WEAPON DETECTION (Global Scan - Independent of ROI/Person) ---
                # Check 1: User must have enabled it via UI button
                if self.weapon_check_enabled:
                    w_results = self.model_weapon(image, verbose=False, conf=0.60) # High confidence
                    weapon_seen_now = False
                    
                    for r in w_results:
                        boxes = r.boxes
                        for box in boxes:
                            # Trusting custom model classes (0-4: Handgun, Knife, Dagger, Axe, Hammer)
                            bx1, by1, bx2, by2 = map(int, box.xyxy[0].cpu().numpy())
                            self.confirmed_weapon_boxes.append((bx1, by1, bx2, by2))
                            weapon_seen_now = True

                    # Persistence for Weapons (1.0 Second)
                    if weapon_seen_now:
                        self.last_weapon_seen_time = current_time
                        if self.weapon_detection_start_time is None:
                            self.weapon_detection_start_time = current_time
                        
                        if current_time - self.weapon_detection_start_time >= 1.0:
                            # Respect dismissal
                            if current_time > self.dismissed_until:
                                self.weapon_active = True
                    else:
                        if current_time - self.last_weapon_seen_time > 0.5:
                            self.weapon_detection_start_time = None
                            if self.weapon_active and (current_time - self.last_weapon_seen_time > 5.0):
                                self.weapon_active = False
                else: 
                     # Explicitly reset state if feature is disabled
                     self.weapon_active = False
                     self.weapon_detection_start_time = None

                # --- 2. PERSON DETECTION (ROI Based & Armed Only) ---
                if should_detect_person:

                    # 2. Person Detection
                    person_seen_now = False
                    detected_in_any_zone = False
                    
                    for roi in self.rois:
                        rx, ry, rw, rh = roi['rect']
                        
                        # Clip ROI
                        h_img, w_img, _ = image.shape
                        rx = max(0, min(rx, w_img))
                        ry = max(0, min(ry, h_img))
                        rw = max(0, min(rw, w_img - rx))
                        rh = max(0, min(rh, h_img - ry))
                        
                        if rw > 0 and rh > 0:
                            roi_crop = image[ry:ry+rh, rx:rx+rw]
                            
                            # Run inference
                            # Increased confidence to 0.75 to reduce false positives
                            results = self.model_person(roi_crop, classes=[0], verbose=False, conf=0.75)
                            
                            for r in results:
                                boxes = r.boxes
                                for box in boxes:
                                    bx1, by1, bx2, by2 = box.xyxy[0].cpu().numpy()
                                    gx1 = int(bx1 + rx)
                                    gy1 = int(by1 + ry)
                                    gx2 = int(bx2 + rx)
                                    gy2 = int(by2 + ry)
                                    
                                    # --- MOTION CHECK ---
                                    # Only confirm if this box has movement
                                    if self.is_box_moving((gx1, gy1, gx2, gy2), motion_mask):
                                        # --- FACE RECOGNITION CHECK ---
                                        # Crop the face/person area for recognition
                                        person_crop = image[gy1:gy2, gx1:gx2]
                                        rgb_person = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
                                        
                                        # Find faces in the crop (using lighter HOG model or CNN)
                                        # We only verify if it's NOT a known person
                                        face_locations = face_recognition.face_locations(rgb_person)
                                        face_encodings = face_recognition.face_encodings(rgb_person, face_locations)
                                        
                                        is_known = False
                                        for face_encoding in face_encodings:
                                            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
                                            if True in matches:
                                                is_known = True
                                                print("Authorized Person Detected: Alert Supressed.")
                                                break
                                        
                                        if not is_known:
                                            person_seen_now = True
                                            self.last_detections.append((gx1, gy1, gx2, gy2))
                                        else:
                                            # Optional: Draw green box for known person?
                                            cv2.rectangle(image, (gx1, gy1), (gx2, gy2), (0, 255, 0), 2)
                                            cv2.putText(image, "AUTHORIZED", (gx1, gy1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                    # Persistence for Person (2 Seconds)
                    if person_seen_now:
                        self.last_person_seen_time = current_time
                        if self.person_detection_start_time is None:
                            self.person_detection_start_time = current_time
                        
                        if current_time - self.person_detection_start_time >= 0.0: # Immediate alert
                             detected_in_any_zone = True # Mark confirmed
                    else:
                         if current_time - self.last_person_seen_time > 0.5:
                             self.person_detection_start_time = None

                    if detected_in_any_zone:
                         if current_time > self.dismissed_until:
                            self.alarm_active = True
                else:
                    # Reset person timers if disarmed
                    self.person_detection_start_time = None
                    self.weapon_detection_start_time = None

            # --- Drawing & Alerts ---
            
            # Draw ROIs
            for roi in self.rois:
                rx, ry, rw, rh = roi['rect']
                cv2.rectangle(image, (rx, ry), (rx+rw, ry+rh), (255, 0, 0), 2)
                cv2.putText(image, roi['name'], (rx, ry-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

            # Draw Person Detections (Only if confirmed/active phase)
            # If alarm is active, we assume valid detection
            if self.alarm_active or (self.person_detection_start_time and (current_time - self.person_detection_start_time >= 0.0)):
                 for (gx1, gy1, gx2, gy2) in self.last_detections:
                        cv2.rectangle(image, (gx1, gy1), (gx2, gy2), (0, 0, 255), 2)
                        cv2.putText(image, "Confirmed Person", (gx1, gy1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                        
            # Alert Logic
            if self.weapon_active:
                cv2.putText(image, "CRITICAL: WEAPON DETECTED", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            elif self.alarm_active:
                alert_msg = "ALERT: PERSON CONFIRMED"
                if is_night_time and self.night_mode_enabled and not self.away_mode:
                        alert_msg = "NIGHT WATCH: INTRUDER"
                cv2.putText(image, alert_msg, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Encode frame
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()
