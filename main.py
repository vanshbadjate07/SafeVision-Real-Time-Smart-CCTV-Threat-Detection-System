from flask import Flask, render_template, Response, request, jsonify
from camera import VideoCamera
import time

app = Flask(__name__)
camera = VideoCamera()

@app.route('/')
def index():
    return render_template('index.html')

def gen(camera):
    while True:
        frame = camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
        else:
            time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    return Response(gen(camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/set_roi', methods=['POST'])
def set_roi():
    data = request.json
    try:
        x = data['x']
        y = data['y']
        w = data['w']
        h = data['h']
        name = data.get('name', 'Zone')
        roi_id = camera.add_roi(x, y, w, h, name)
        return jsonify({"success": True, "id": roi_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/delete_roi', methods=['POST'])
def delete_roi():
    data = request.json
    try:
        roi_id = data['id']
        camera.delete_roi(roi_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/get_rois', methods=['GET'])
def get_rois():
    return jsonify(camera.get_rois())

@app.route('/api/toggle_away', methods=['POST'])
def toggle_away():
    data = request.json
    status = data.get('status', False)
    camera.toggle_away_mode(status)
    return jsonify({"success": True, "status": camera.away_mode})

@app.route('/api/toggle_night_mode', methods=['POST'])
def toggle_night_mode():
    data = request.json
    status = data.get('status', False)
    camera.toggle_night_mode(status)
    return jsonify({"success": True, "status": camera.night_mode_enabled})

@app.route('/api/toggle_weapon_detection', methods=['POST'])
def toggle_weapon_detection():
    data = request.json
    status = data.get('status', False)
    camera.toggle_weapon_detection(status)
    return jsonify({"success": True, "status": camera.weapon_check_enabled})

@app.route('/api/dismiss_alert', methods=['POST'])
def dismiss_alert():
    camera.dismiss_alert()
    return jsonify({"success": True})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(camera.get_status())

@app.route('/api/trigger_call', methods=['POST'])
def trigger_call():
    # Simulate calling police
    print("----------- CALLING POLICE (SIMULATED) -----------")
    print("DIALING 112...")
    print("CONNECTED.")
    print("--------------------------------------------------")
    
    # We can also reset the alarm here if desired, or let the user manually stop it.
    camera.reset_alarm()
    return jsonify({"success": True, "message": "Police have been notified (Simulated)"})

if __name__ == '__main__':
    # Using port 5001 to avoid conflict with AirPlay Receiver on macOS (port 5000)
    app.run(host='0.0.0.0', port=5001, debug=True)
