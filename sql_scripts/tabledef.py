from sqlalchemy import *
from sqlalchemy import create_engine, ForeignKey
from sqlalchemy import Column, Date, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref

engine = create_engine('sqlite:///../user_data.db', echo=True)
Base = declarative_base()

########################################################################
class User(Base):
  """"""
  __tablename__ = "users"

  username = Column(String, primary_key=True)
  password = Column(String)
  csv_content = Column(Text)

#----------------------------------------------------------------------
def __init__(self, username, password, csv_content):
  """"""
  self.username = username
  self.password = password
  self.csv_content = csv_content

# create tables
Base.metadata.create_all(engine)