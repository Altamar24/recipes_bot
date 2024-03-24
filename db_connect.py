from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


engine = create_engine('sqlite:///bot.db')
db = scoped_session(sessionmaker(bind=engine))
