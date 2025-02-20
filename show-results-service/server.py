import logging
from flask import Flask, request, jsonify
import requests
from flask_pymongo import PyMongo
from functools import wraps

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# MongoDB setup
app.config["MONGO_URI"] = "mongodb://mongo:27017/gpa_analytics_db"
mongo = PyMongo(app)

# Auth service URL
AUTH_SERVICE_URL = "http://auth:5000/verify"

# Middleware to verify JWT token with auth service
def verify_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            logging.error("Authorization header is missing!")
            return jsonify({"message": "Token is missing!"}), 403
        
        logging.debug(f"Received Authorization header: {auth_header}")

        if not auth_header.startswith("Bearer "):
            logging.error("Authorization header does not start with 'Bearer '")
            return jsonify({"message": "Token is invalid!"}), 403

        token = auth_header.split(" ")[1]  # Extract token after 'Bearer '
        
        logging.debug(f"Extracted token: {token}")

        # Verify token with auth service
        response = requests.post(AUTH_SERVICE_URL, headers={"Authorization": f"Bearer {token}"})
        logging.debug(f"Auth service response status: {response.status_code}")
        logging.debug(f"Auth service response body: {response.text}")

        if response.status_code != 200:
            logging.error("Auth service rejected the token!")
            return jsonify({"message": "Invalid token!"}), 403

        request.user = response.json()  # Attach user information to the request
        logging.debug(f"Decoded token payload: {request.user}")

        return f(*args, **kwargs)

    return decorated_function

# Create a route to fetch GPA statistics for the authenticated user
@app.route('/gpa-statistics', methods=['GET'])
@verify_token
def gpa_statistics():
    student_id = request.user.get('userId')
    
    logging.debug(f"Fetching GPA statistics for student_id: {student_id}")

    result = mongo.db.analytics.find_one(
    {"student_id": {"$in": [student_id, str(student_id)]}},
    sort=[('_id', -1)]
)

    if not result:
        logging.error(f"No GPA statistics found for student_id: {student_id}")
        return jsonify({"message": "GPA statistics not found"}), 404

    logging.debug(f"Retrieved GPA statistics: {result}")

    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)
