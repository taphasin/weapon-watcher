from flask import Flask, Response
import time
import cv2
import paho.mqtt.client as paho
from paho import mqtt


app = Flask(__name__)

xyz = str([[1, 2, 3], [1, 2, 3], [1, 2, 3]])

def on_connect(client, userdata, flags, rc, properties=None):
    print("CONNACK received with code %s." % rc)

#def on_subscribe(client, userdata, mid, granted_qos, properties=None):
#    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_message(client, userdata, msg):
    global xyz
    xyz = str(msg.payload.decode())
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

def generate():
    rtsp_url = "rtsp://admin:Admin.1234@192.168.1.64:554/Streaming/Channels/102"
    cap = None

    def open_capture():
        c = cv2.VideoCapture(rtsp_url)
        return c if c.isOpened() else None

    cap = open_capture()

    while True:
        if cap is None or not cap.isOpened():
            cap = open_capture()
            if cap is None:
                time.sleep(1.0)
                continue

        ok, frame = cap.read()
        if not ok or frame is None:
            # Try to reopen on read failure
            try:
                cap.release()
            except Exception:
                pass
            cap = None
            time.sleep(0.2)
            continue

        # Overlay latest MQTT metadata text on the frame
        text = str(xyz)
        cv2.putText(
            frame,
            text,
            (50, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            continue
        frame_bytes = encoded.tobytes()
        yield (b"--frame\r\n" + b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

@app.get("/stream")
def stream():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")



client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv5)
client.on_connect = on_connect
client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
client.username_pw_set("hivemq.webclient.1757927568300", "r$i.g1>23O5TMdLAcp:H")
client.connect("fd2249eedb6c43fdbf9e9d318ab38fe4.s1.eu.hivemq.cloud", 8883)

#client.on_subscribe = on_subscribe
client.on_message = on_message

client.loop_start()
client.publish("test/", payload="hot", qos=1)
client.subscribe("#", qos=1)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)


