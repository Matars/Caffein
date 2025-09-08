from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'projectvis_db')

try:
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    # Test the connection
    client.admin.command('ping')
    print("MongoDB connection successful!")
except Exception as e:
    print(f"MongoDB connection failed: {e}")
    db = None


@app.route('/api/hello', methods=['GET'])
def hello():
    """Hello world endpoint that returns a message from the database or default"""
    try:
        if db is not None:
            # Try to get message from database
            messages_collection = db.messages
            message_doc = messages_collection.find_one({'type': 'hello'})

            if message_doc:
                message = message_doc['content']
            else:
                # Insert default message if not exists
                default_message = {
                    'type': 'hello',
                    'content': 'Hello World from Flask backend with MongoDB!'
                }
                messages_collection.insert_one(default_message)
                message = default_message['content']
        else:
            message = 'Hello World from Flask backend (MongoDB not connected)'

        return jsonify({
            'message': message,
            'status': 'success',
            'database_connected': db is not None
        })
    except Exception as e:
        return jsonify({
            'message': 'Hello World from Flask backend (error occurred)',
            'status': 'error',
            'error': str(e),
            'database_connected': False
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'database_connected': db is not None
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
