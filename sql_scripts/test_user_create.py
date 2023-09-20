import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tabledef import *

engine = create_engine('sqlite:///../user_data.db', echo=True)

# create a Session
Session = sessionmaker(bind=engine)
session = Session()

with open('../test_csv_files/Crunch_test.csv', 'r') as file:
    csv_data = file.read()
user = User(username="test",password="password", csv_content=csv_data)
session.add(user)

# commit the record the database
session.commit()

session.commit()