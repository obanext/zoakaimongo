from flask import Flask, request, jsonify, render_template, url_for
import openai
import json
import requests
import aiohttp
import asyncio
import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from dotenv import load_dotenv

# Laad de omgevingsvariabelen
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
openai_api_key = os.environ.get('OPENAI_API_KEY')
typesense_api_key = os.environ.get('TYPESENSE_API_KEY')
typesense_api_url = os.environ.get('TYPESENSE_API_URL')
mongodb_uri = os.environ.get('MONGODB_URI')

openai.api_key = openai_api_key

client = MongoClient(mongodb_uri, server_api=ServerApi('1'))
db = client['nexi']
interactions_collection = db['interactions']
messages_collection = db['messages']

assistant_id_1 = 'asst_ejPRaNkIhjPpNHDHCnoI5zKY'
assistant_id_2 = 'asst_mQ8PhYHrTbEvLjfH8bVXPisQ'
assistant_id_3 = 'asst_NLL8P78p9kUuiq08vzoRQ7tn'

class CustomEventHandler(openai.AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.response_text = ""

    def on_text_created(self, text) -> None:
        self.response_text = ""

    def on_text_delta(self, delta, snapshot):
        self.response_text += delta.value

    def on_tool_call_created(self, tool_call):
        pass

    def on_tool_call_delta(self, delta, snapshot):
        pass

def call_assistant(assistant_id, user_input, thread_id=None):
    try:
        if thread_id is None:
            start_time = datetime.utcnow()
            thread = openai.beta.threads.create()
            thread_id = thread.id
            end_time = datetime.utcnow()
            print(f"Thread creation time: {(end_time - start_time).total_seconds()} seconds")
        else:
            start_time = datetime.utcnow()
            openai.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_input
            )
            end_time = datetime.utcnow()
            print(f"Message creation time: {(end_time - start_time).total_seconds()} seconds")

        event_handler = CustomEventHandler()

        start_time = datetime.utcnow()
        with openai.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()
        end_time = datetime.utcnow()
        print(f"Assistant call time: {(end_time - start_time).total_seconds()} seconds")

        return event_handler.response_text, thread_id
    except openai.error.OpenAIError as e:
        return str(e), thread_id
    except Exception as e:
        return str(e), thread_id

def extract_search_query(response):
    search_marker = "SEARCH_QUERY:"
    if search_marker in response:
        start_index = response.find(search_marker) + len(search_marker)
        search_query = response[start_index:].strip()
        return search_query
    return None

def extract_comparison_query(response):
    comparison_marker = "VERGELIJKINGS_QUERY:"
    if comparison_marker in response:
        start_index = response.find(comparison_marker) + len(comparison_marker)
        comparison_query = response[start_index:].strip()
        return comparison_query
    return None

def parse_assistant_message(content):
    try:
        parsed_content = json.loads(content)
        return {
            "q": parsed_content.get("q", ""),
            "query_by": parsed_content.get("query_by", ""),
            "collection": parsed_content.get("collection", ""),
            "vector_query": parsed_content.get("vector_query", ""),
            "filter_by": parsed_content.get("filter_by", "")
        }
    except json.JSONDecodeError:
        return None

def perform_typesense_search(params):
    headers = {
        'Content-Type': 'application/json',
        'X-TYPESENSE-API-KEY': typesense_api_key,
    }
    body = {
        "searches": [{
            "q": params["q"],
            "query_by": params["query_by"],
            "collection": params["collection"],
            "prefix": "false",
            "vector_query": params["vector_query"],
            "include_fields": "titel,ppn",
            "per_page": 15,
            "filter_by": params["filter_by"]
        }]
    }

    response = requests.post(typesense_api_url, headers=headers, json=body)
    
    if response.status_code == 200:
        search_results = response.json()
        results = [
            {
                "ppn": hit["document"]["ppn"],
                "titel": hit["document"]["titel"]
            } for hit in search_results["results"][0]["hits"]
        ]

        simplified_results = {"results": results}
        return simplified_results
    else:
        return {"error": response.status_code, "message": response.text}

def log_interaction(thread_id, user_id, assistant_id, interaction_type):
    interaction = {
        "thread_id": thread_id,
        "user_id": user_id,
        "assistant_id": assistant_id,
        "interaction_type": interaction_type,
        "created_at": datetime.utcnow()
    }
    interaction_id = interactions_collection.insert_one(interaction).inserted_id
    return interaction_id

def log_message(interaction_id, sender, message):
    message_doc = {
        "interaction_id": interaction_id,
        "sender": sender,
        "message": message,
        "created_at": datetime.utcnow()
    }
    messages_collection.insert_one(message_doc)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_thread', methods=['POST'])
def start_thread():
    try:
        thread = openai.beta.threads.create()
        return jsonify({'thread_id': thread.id})
    except openai.error
