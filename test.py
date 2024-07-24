import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# Manually load environment variables from .env file
with open('.env') as f:
    for line in f:
        if line.strip():
            key, value = line.strip().split('=', 1)
            os.environ[key] = value

# Get MongoDB URI from environment variables
mongodb_uri = os.environ.get('MONGODB_URI')

# Create a new client and connect to the server
client = MongoClient(mongodb_uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
