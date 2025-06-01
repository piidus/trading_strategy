# my sql connection
import sqlalchemy
from sqlalchemy import create_engine
import os
from datetime import datetime, timedelta
from .environ_parser import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST

# from dotenv import load_dotenv
# load_dotenv()


engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_NAME}')

def get_engine():
    try:
        engine.connect()
    # except:
    #     engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_NAME}')
    except Exception as e:
        print(f"Error connecting to the database: {e}")  # Print the error message (e)
        print(f"DB_NAME: {DB_NAME}, DB_USER: {DB_USER}, DB_PASSWORD: {DB_PASSWORD}, DB_HOST: {DB_HOST}")
    return engine

if __name__ == "__main__":
    print(get_engine())

