from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_tabledef import *

def sqlite_user_upload(username, password, is_admin, csv_file_contents):
    engine = create_engine('sqlite:///user_data.db', echo=True)

    # create a Session
    Session = sessionmaker(bind=engine)
    session = Session()

    if is_admin:
        user = User(username=username, password=password, is_admin=True, csv_content="")
    else:
        user = User(username=username, password=password, is_admin=False, csv_content=csv_file_contents)


    session.add(user)

    # commit the record the database
    session.commit()

    session.commit()