import os
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_PATH')

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
API_SESSION = os.getenv('API_SESSION')

def env_parser(name):
    if name == 'DB_NAME':
        return DB_NAME
    elif name == 'DB_USER':
        return DB_USER
    elif name == 'DB_PASSWORD':
        return DB_PASSWORD
    elif name == 'DB_HOST':
        return DB_HOST
    elif name == 'API_KEY':
        return API_KEY
    elif name == 'API_SECRET':
        return API_SECRET
    elif name == 'API_SESSION':
        return API_SESSION
    