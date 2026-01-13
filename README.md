# SafeVision - Real-Time Smart CCTV Threat Detection System

SafeVision is an advanced AI-powered surveillance system designed to enhance security through real-time detection of potential threats. It integrates multiple detection models to identify intruders, weapons, and tampering attempts, distinguishing between authorized personnel and unknown entities.

## 🚀 Key Features

*   **Real-Time Person Detection:** accurately detects individuals within user-defined **Regions of Interest (ROI)** using YOLOv8, reducing false positives from pets or background motion.
*   **Weapon Detection:** Specialized custom-trained model to detect weapons such as **Handguns, Knives, Daggers, Axes, and Hammers** in real-time. This feature can be toggled on/off independently.
*   **Authorized Personnel Recognition:** Uses facial recognition to identify known individuals. Alerts are **suppressed** for authorized users (e.g., family members, staff), minimizing false alarms.
*   **Camera Tamper Detection:** Intelligent logic to detect if the camera view is blocked or covered (blinded). Includes a persistence timer to prevent flickering alerts.
*   **Automated Night Mode:** "Set and Forget" scheduling system that automatically arms the security system between **12:00 AM and 5:00 AM**.
*   **Smart Motion Filtering:** Differential motion analysis prevents alerts on static objects and reduces noise.
*   **Glassmorphism Dashboard:** A modern, responsive web interface for controlling the system, managing zones, and viewing live status updates.

## 🛠️ Technology Stack

*   **Backend:** Python, Flask
*   **Deep Learning:** YOLOv8 (Ultralytics), OpenCV, Face Recognition (dlib)
*   **Frontend:** HTML5, CSS3 (Glassmorphism), JavaScript (Vanilla)
*   **Processing:** Multi-threaded video processing pipeline

## 📦 Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/vanshbadjate07/SafeVision-Real-Time-Smart-CCTV-Threat-Detection-System.git
    cd SafeVision-Real-Time-Smart-CCTV-Threat-Detection-System
    ```

2.  **Install Dependencies**
    Ensure you have Python 3.9+ installed.
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: `dlib` may require CMake to be installed on your system)*

3.  **Setup Authorized Faces (Optional)**
    *   Create a folder `face_dataset/NameOfPerson`
    *   Add images of the person to this folder.
    *   The system will automatically learn these faces on next startup.

## 🚦 Usage

1.  **Run the Application**
    ```bash
    python main.py
    ```
2.  **Access the Dashboard**
    Open your browser and navigate to `http://127.0.0.1:5001`
3.  **Configure Security**
    *   **Add Zones:** Draw blue boxes on the camera feed to define monitoring areas.
    *   **Arm System:** Click "Start Away Mode" or "Enable Night Mode".
    *   **Enable Weapon Scan:** Toggle "Enable Weapon Detection" for high-threat monitoring.

## ⚠️ Disclaimer

This project is intended for educational and research purposes. While it aims for high accuracy, it should not be the sole reliance for critical safety applications.

---
**Developed by Vansh Badjate**
