from flask import Flask, request, render_template, send_from_directory, jsonify, Response
import datetime
import pandas as pd
import os
import json
import time

app = Flask(__name__)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

# Declare global variables
anticipated_attendees = {}
checked_in_list = []
not_scheduled_list = []
interview_check_in_list = []

# Ensure the uploads directory and file exist and have the correct permissions
uploads_dir = 'uploads'
excel_file_path = os.path.join(uploads_dir, 'expected_attendees.xlsx')

if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)

if not os.path.exists(excel_file_path):
    raise FileNotFoundError(f"{excel_file_path} does not exist. Please ensure the file is present.")

# Check file permissions
if not os.access(excel_file_path, os.R_OK):
    raise PermissionError(f"Read permission denied for {excel_file_path}")

# Load anticipated attendees from the Excel file
def load_attendees_from_excel(file_path):
    global anticipated_attendees
    df = pd.read_excel(file_path, parse_dates=['Date'])
    attendees = {}
    for _, row in df.iterrows():
        date = row['Date'].strftime('%m/%d/%Y')  # Assuming the date is in month/day/year format
        time = row['Time']  # Assuming time is already in hour:minute AM/PM format as a string
        if isinstance(time, datetime.time):
            time = time.strftime('%I:%M %p')  # Format time as hour:minute AM/PM
        name = row['Name']
        if date not in attendees:
            attendees[date] = {}
        if time not in attendees[date]:
            attendees[date][time] = []
        attendees[date][time].append(name)
    anticipated_attendees = attendees

# Load the attendees
load_attendees_from_excel(excel_file_path)

# Print anticipated attendees for debugging
print("Anticipated Attendees:")
print(anticipated_attendees)

latest_data = None

def generate_recruiter_list_updates():
    global latest_data
    while True:
        time.sleep(1)
        if latest_data:
            yield f"data: {json.dumps(latest_data)}\n\n"

@app.route('/recruiter_list_updates')
def recruiter_list_updates():
    return Response(generate_recruiter_list_updates(), mimetype='text/event-stream')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check_in', methods=['GET', 'POST'])
def check_in():
    global latest_data
    check_in_type = request.args.get('type')

    if request.method == 'GET':
        if check_in_type == 'interview':
            return render_template('interview_check_in.html')
        elif check_in_type == 'orientation':
            return render_template('orientation_check_in.html')

    elif request.method == 'POST':
        name = request.form['name'].strip()
        current_date = datetime.datetime.now().strftime('%m/%d/%Y')
        current_time = datetime.datetime.now().strftime('%I:%M %p')

        response_message = ''
        found = False

        if check_in_type == 'interview':
            interview_check_in_list.append({'name': name, 'time': current_time})
            response_message = 'You have been checked in. Please have a seat and wait for the recruiter to come get you. Thank you for your patience.'

        elif check_in_type == 'orientation':
            for date, times in anticipated_attendees.items():
                for time_window, attendees in times.items():
                    if name in attendees:
                        scheduled_time = datetime.datetime.strptime(f"{date} {time_window}", '%m/%d/%Y %I:%M %p')
                        if date == current_date:
                            if scheduled_time < datetime.datetime.now():
                                response_message = f'You are late. Your orientation was scheduled for {scheduled_time.strftime("%I:%M %p")}.'
                                checked_in_list.append({'name': name, 'time': current_time, 'scheduled_time': scheduled_time.strftime("%I:%M %p"), 'late': True})
                            elif scheduled_time > datetime.datetime.now() + datetime.timedelta(hours=1):
                                response_message = f'You are early! You are scheduled for {scheduled_time.strftime("%I:%M %p")}.'
                            else:
                                checked_in_list.append({'name': name, 'time': current_time, 'scheduled_time': scheduled_time.strftime("%I:%M %p"), 'late': False})
                                response_message = 'Have a seat. Our recruiter will be with you soon.'
                        elif scheduled_time > datetime.datetime.now():
                            response_message = f'You are early! You are scheduled for {scheduled_time.strftime("%m/%d/%Y %I:%M %p")}.'
                        else:
                            response_message = f'You are late. Your orientation was scheduled for {scheduled_time.strftime("%m/%d/%Y %I:%M %p")}.'
                        found = True
                        break
                if found:
                    break

            if not found:
                response_message = 'You are not on the list.'
                not_scheduled_list.append({'name': name, 'time': current_time})

        # Update latest data for SSE
        latest_data = {
            'checked_in_list': checked_in_list,
            'not_scheduled_list': not_scheduled_list,
            'interview_check_in_list': interview_check_in_list
        }

        return render_template('response.html', message=response_message)

@app.route('/recruiter_list')
def recruiter_list():
    return render_template('recruiter_list.html', checked_in_list=checked_in_list, not_scheduled_list=not_scheduled_list, interview_check_in_list=interview_check_in_list)

@app.route('/qr')
def qr():
    return send_from_directory('static', 'check_in_qr.png')

if __name__ == '__main__':
    # Run the application on all interfaces (0.0.0.0) and on port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)
