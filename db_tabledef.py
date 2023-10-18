from sqlalchemy import *
from sqlalchemy import create_engine
from sqlalchemy import Column, String, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('sqlite:///../user_data.db', echo=True)
Base = declarative_base()

########################################################################
class User(Base):
  """"""
  __tablename__ = "users"

  username = Column(String, primary_key=True)
  password = Column(String)
  is_admin = Column(Boolean)
  csv_content = Column(Text)

#----------------------------------------------------------------------
def __init__(self, username, password, is_admin, csv_content):
  """"""
  self.username = username
  self.password = password
  self.is_admin = is_admin
  self.csv_content = csv_content

# create tables
Base.metadata.create_all(engine)