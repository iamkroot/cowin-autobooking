"""
Flask application with a single endpoint /cowinOtp to receive a OTP code from the user
"""
from flask import Flask, request, Response
from flask_cors import CORS
import re
from queue import Queue
from gevent.pywsgi import WSGIServer

from __init__ import DEBUG, config, logging

otp_queue = Queue()
app = Flask(__name__)
CORS(app)

AUTH_KEY = config["server"]["auth_key"]


@app.route("/cowinOtp", methods=["POST"])
def handleOtpMsg():
    """Extract 6 digits from message using regex"""
    json = request.json
    if json is None:
        return Response(
            response="This endpoint only supports JSON requests",
            status=400,
            mimetype="text/plain",
        )
    msg = json.get("msgBody", "")
    auth = json.get("authKey")  # a bit of authetication
    if auth != AUTH_KEY:
        return Response(status=403)
    pattern = re.compile(r"\d{6}")
    if match := pattern.search(msg):
        otp = match.group(0)
        logging.info(f"Got otp from endpoint: {otp}.")
        otp_queue.put(otp)
        return Response(status=200)
    else:
        return Response(status=400)


def run_app():
    if DEBUG:
        app.run(host="0.0.0.0", port=5000, debug=True)
    else:
        http_server = WSGIServer(('localhost', 5000), app)
        http_server.serve_forever()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
