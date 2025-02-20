import pymysql
import pymongo
import time
from pymongo import MongoClient
from flask import Flask, request, jsonify

app = Flask(__name__)

# MySQL connection configuration
mysql_config = {
    'host': 'mysql',
    'user': 'root',
    'password': 'root',
    'database': 'student_db'
}

# Function to create a connection with retry mechanism
def connect_with_retry():
    connection = None
    while connection is None:
        try:
            connection = pymysql.connect(**mysql_config)
            print('Connected to MySQL')
        except pymysql.MySQLError as err:
            print(f'Error connecting to MySQL: {err}')
            time.sleep(5)  # Retry after 5 seconds
    return connection

# Create a MySQL connection
mysql_connection = connect_with_retry()

# MongoDB connection
try:
    mongo_client = MongoClient("mongodb://mongo:27017")
    db = mongo_client.gpa_analytics_db
    gpas_collection = db.gpas
    analytics_collection = db.analytics
    print('Connected to MongoDB')
except pymongo.errors.ConnectionError as err:
    print(f'Error connecting to MongoDB: {err}')
    mongo_client = None

# Function to get grades and credit_hours from MySQL
def get_grades_and_credit_hours(student_id):
    conn = pymysql.connect(**mysql_config)
    cursor = conn.cursor()
    query = "SELECT grade, credit_hours FROM grades WHERE student_id = %s"
    cursor.execute(query, (student_id,))
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

# Function to calculate GPA
def calculate_gpa(grades_and_credit_hours):
    total_grades = 0
    total_credit_hours = 0
    for grade, credit_hours in grades_and_credit_hours:
        total_grades += grade * credit_hours
        total_credit_hours += credit_hours
    if total_credit_hours == 0:
        return 0  # Avoid division by zero if no credit hours
    return total_grades / total_credit_hours

# Function to calculate min, max, and avg grade for a specific student
def calculate_student_grade_statistics(student_id):
    grades_and_credit_hours = get_grades_and_credit_hours(student_id)
    grades = [grade for grade, _ in grades_and_credit_hours]

    if len(grades) == 0:
        return None  # No grades to calculate statistics

    min_grade = min(grades)
    max_grade = max(grades)
    avg_grade = sum(grades) / len(grades)

    return {
        'min_grade': min_grade,
        'max_grade': max_grade,
        'avg_grade': round(avg_grade, 2)
    }

# Route to calculate and return GPA statistics for a student
@app.route('/calculate_gpa', methods=['GET'])
def calculate_and_store_gpa():
    student_id = request.args.get('student_id')

    if not student_id:
        return jsonify({'error': 'Student ID is required'}), 400

    # Get grades and credit_hours from MySQL
    grades_and_credit_hours = get_grades_and_credit_hours(student_id)

    if not grades_and_credit_hours:
        return jsonify({'error': 'No grades found for this student'}), 404

    # Calculate GPA
    gpa = calculate_gpa(grades_and_credit_hours)

    # Insert GPA into MongoDB for the student
    gpas_collection.insert_one({
        'student_id': student_id,
        'gpa': gpa
    })

    # Calculate GPA statistics for this student
    grade_stats = calculate_student_grade_statistics(student_id)

    # Insert GPA statistics into MongoDB
    analytics_collection.insert_one({
        'student_id': student_id,
        'min_grade': grade_stats['min_grade'],
        'max_grade': grade_stats['max_grade'],
        'avg_grade': grade_stats['avg_grade']
    })

    # Return the calculated GPA and statistics as a response
    return jsonify({
        'student_id': student_id,
        'gpa': gpa
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)

