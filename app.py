from flask import Flask, flash, render_template, request, session, send_file, redirect
import os
from sqlalchemy.orm import sessionmaker
from db_tabledef import *
from db_user_create import *
import csv
import tempfile
import datetime

import logging
from azure.loganalytics import LogAnalyticsDataClient
from azure.identity import DefaultAzureCredential
from azure.loganalytics.models import LogItem

engine = create_engine('sqlite:///user_data.db', echo=True)
app = Flask(__name__)
app.secret_key = os.urandom(12)

@app.route('/')
def home():
  if not session.get('logged_in'):
    return render_template('login.html')
  else:
    if session.get('admin'):
      Session = sessionmaker(bind=engine)
      s = Session()
      users = s.query(User).all()

      user_data = []
      for user in users:
          num_rows = len(user.csv_content.split('\n')) - 1
          
          user_data.append({
              'username': user.username,
              'password': user.password,
              'num_rows_in_csv': num_rows,
              'is_admin': user.is_admin
          })
      s.close()

      return render_template('admin_tool.html',login_user=session["user"], users=user_data)
    else:
      return render_template('tool.html',login_user=session["user"], headers=[], matching_rows=0, preview_rows=[])

@app.route('/login', methods=['POST'])
def do_login():
  session["csv_temp_filename"] = None
  session["user"] = str(request.form['username'])
  session["pwd"] = str(request.form['password'])

  Session = sessionmaker(bind=engine)
  s = Session()
  query = s.query(User).filter(User.username.in_([session["user"]]), User.password.in_([session["pwd"]]) )
  result = query.first()
  if result:
    session['logged_in'] = True
    if s.query(User.is_admin).filter_by(username=session["user"]).first().is_admin:
      session['admin'] = True
    else:
      session['admin'] = False
  else:
    flash('Incorrect Username or Password')
  return redirect('/')

@app.route("/export")
def export():
  if session["csv_temp_filename"] != None:
    return send_file(session["csv_temp_filename"], as_attachment=True, download_name="QUERY_" + session["datetime"] + ".csv", mimetype="text/csv")
  return redirect('/')

@app.route("/upload", methods=["GET", "POST"])
def upload():
  if request.method == "POST":

    file = request.files.get("file")
    file_content = file.read().decode('utf-8')
    
    # check if file loaded successfully or not
    if file_content:
        Session = sessionmaker(bind=engine)
        s = Session()

        query_csv_data = s.query(User.csv_content).filter_by(username=session["user"]).first().csv_content
        
        csv1_reader = csv.reader(query_csv_data.splitlines())
        data1 = list(csv1_reader)

        csv2_reader = csv.reader(file_content.splitlines())
        data2 = list(csv2_reader)

        join_fields_combinations = [
          # ["FIRSTNAME", "LASTNAME", "ADDRESS", "ADDRESS2", "CITY", "STATE", "ZIP"],
          # ["FIRSTNAME", "LASTNAME"],
          ["ADDRESS", "ADDRESS2", "CITY", "STATE", "ZIP"],
          ["EMAIL"]
        ]

        matching_rows = []
        encountered_rows = set()  # Set to store encountered row tuples

        for join_fields in join_fields_combinations:
          # Check if all join fields are present in both CSV headers
          if all(field in data1[0] and field in data2[0] for field in join_fields):
            # Create a dictionary for data1, indexed by the join fields
            header1 = data1[0]
            data1_dict = {tuple(row1[header1.index(field)].strip().lower() for field in join_fields): row1 for row1 in data1[1:]}

            # Iterate through data2 and check for matches
            for row2 in data2[1:]:
              join_key = tuple(row2[data2[0].index(field)].strip().lower() for field in join_fields)
              if join_key in data1_dict:
                # Check if the normalized row data is unique before adding it
                row_tuple = tuple(row2)
                if row_tuple not in encountered_rows:
                  matching_rows.append(row_tuple)
                  encountered_rows.add(row_tuple)
          else:
            print(f"Ignoring join fields {join_fields} because one or more are missing in the CSV headers.")
        
        timestamp = datetime.datetime.now()
        timestamp_str = str(timestamp).replace(' ', '_')[:-7]
        log_entry = f"Query executed at {timestamp_str}, Records Uploaded: {len(data2) - 1}, Matches Found: {len(matching_rows)}, User: {session['user']}\n"
        session["datetime"] = timestamp_str.replace(':', '-')
        app.logger.info(log_entry)


        if matching_rows:
          with tempfile.NamedTemporaryFile(delete=False, mode='w', newline='\n') as temp_file:
            csv_writer = csv.writer(temp_file)
            csv_writer.writerows(matching_rows)
          session["csv_temp_filename"] = temp_file.name

        headers = data2[0] if matching_rows else []

        preview_rows = matching_rows[:50]

        return render_template('tool.html', login_user = session["user"], headers=headers, matching_rows=len(matching_rows), preview_rows=preview_rows)

    else:
        session["csv_temp_filename"] = None
        return redirect('/')
    
  session["csv_temp_filename"] = None
  return redirect('/')

@app.route('/user_upload', methods=['POST'])
def user_upload():
  is_admin = request.form.get('yesNoRadio') == 'True'
  new_username = str(request.form['new_username'])
  new_password = str(request.form['new_password'])

  file = request.files.get('new_file')
  if file:
    if not file.filename.endswith('.csv'):
      flash('Please attach a .csv file for non-admin user')
      return redirect('/')
    
    file_content = file.read().decode('utf-8')

  else:
    file_content = None

  Session = sessionmaker(bind=engine)
  s = Session()
  existing_user = s.query(User).filter_by(username=new_username).first()

  if ' ' in new_username:
    flash('Username cannot contain spaces')
  elif ' ' in new_password:
    flash('Password cannot contain spaces')
  elif len(new_username) < 5:
    flash('Username must have 5 or more characters')
  elif existing_user:
    flash('Username already in use. Please choose a different username.')
  elif len(new_password) < 8:
    flash('Password must have 8 or more characters')
  elif not file_content and not is_admin:
    flash('Please attach a CSV file for non-admin user')
  else:
    if is_admin:
      sqlite_user_upload(new_username, new_password, 1, "")
    else:
      sqlite_user_upload(new_username, new_password, 0, file_content)
    flash('User created successfully', 'success')
  return redirect('/')

@app.route('/user_delete', methods=['POST'])
def user_delete():
    username = request.form.get('username')
    
    Session = sessionmaker(bind=engine)
    s = Session()
    user_to_delete = s.query(User).filter_by(username=username).first()
    
    if user_to_delete:
        s.delete(user_to_delete)
        s.commit()
        flash(f'User {username} has been deleted', 'success')
    else:
        flash(f'User {username} not found', 'error')
    
    s.close()
    return redirect('/')
  

@app.route("/logout")
def logout():
  session['logged_in'] = False
  session["csv_temp_filename"] = None
  return redirect('/')

def setup_logging():
   # Initialize the log analytics data client
   credential = DefaultAzureCredential()
   client = LogAnalyticsDataClient(credential)

   # Set the workspace ID and instrumentation key
   workspace_id = os.environ.get('YOUR_WORKSPACE_ID')
   instrumentation_key = os.environ.get('YOUR_INSTRUMENTATION_KEY')

   logger = logging.getLogger("azure")
   logger.setLevel(logging.INFO)

   # Define a custom log handler
   class LogAnalyticsHandler(logging.Handler):
       def emit(self, record):
           message = self.format(record)
           log_item = LogItem(message=message)
           client.post_log(workspace_id, os.environ.get('YOUR_LOG_TYPE'), log_item)

   log_handler = LogAnalyticsHandler()
   logger.addHandler(log_handler)

if __name__ == "__main__":
  setup_logging()

  app.run(debug=True,host='0.0.0.0', port=4000)