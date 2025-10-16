from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
import gradio as gr
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
from datetime import datetime
import uuid


load_dotenv(override=True)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Session storage for conversation history
sessions = {}

def push(text):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        }
    )


def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording {question}")
    return {"recorded": "ok"}

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            }
            ,
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_unknown_question_json}]


class Me:

    def __init__(self):
        self.openai = OpenAI()
        self.name = "Ed Donner"
        reader = PdfReader("me/linkedin.pdf")
        self.linkedin = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        with open("me/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()


    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results
    
    def system_prompt(self):
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
You are given a summary of {self.name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. "

        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt
    
    def chat(self, message, history):
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
            response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
            if response.choices[0].finish_reason=="tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(message)
                messages.extend(results)
            else:
                done = True
        return response.choices[0].message.content
    
    def chat_api(self, message, history=None):
        """API version of chat that handles history as a list of message objects"""
        if history is None:
            history = []
        
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
            response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
            if response.choices[0].finish_reason=="tool_calls":
                msg = response.choices[0].message
                tool_calls = msg.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(msg)
                messages.extend(results)
            else:
                done = True
        
        return {
            "response": response.choices[0].message.content,
            "updated_history": messages[1:]  # Exclude system prompt
        }


# Initialize the bot
me = Me()


# API Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Portfolio Bot API",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint
    Expected JSON body:
    {
        "message": "user message",
        "session_id": "optional-session-id",
        "history": [] // optional conversation history
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({"error": "Message is required"}), 400
        
        message = data['message']
        session_id = data.get('session_id', str(uuid.uuid4()))
        history = data.get('history', [])
        
        # Get or create session
        if session_id not in sessions:
            sessions[session_id] = {
                "created_at": datetime.now().isoformat(),
                "history": []
            }
        
        # Use provided history or session history
        if not history and session_id in sessions:
            history = sessions[session_id]['history']
        
        # Get response from bot
        result = me.chat_api(message, history)
        
        # Update session history
        sessions[session_id]['history'] = result['updated_history']
        sessions[session_id]['last_interaction'] = datetime.now().isoformat()
        
        return jsonify({
            "session_id": session_id,
            "message": result['response'],
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}", flush=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session history"""
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404
    
    return jsonify({
        "session_id": session_id,
        "history": sessions[session_id]['history'],
        "created_at": sessions[session_id]['created_at'],
        "last_interaction": sessions[session_id].get('last_interaction')
    })


@app.route('/api/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Clear session history"""
    if session_id in sessions:
        del sessions[session_id]
        return jsonify({"message": "Session deleted successfully"})
    return jsonify({"error": "Session not found"}), 404


@app.route('/api/info', methods=['GET'])
def get_info():
    """Get bot information"""
    return jsonify({
        "name": me.name,
        "description": f"AI-powered chatbot representing {me.name}",
        "capabilities": [
            "Answer questions about background and experience",
            "Capture lead information",
            "Record unanswered questions"
        ]
    })


def run_flask():
    """Run Flask API server"""
    port = int(os.getenv("API_PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


def run_gradio():
    """Run Gradio interface"""
    gr.ChatInterface(me.chat, type="messages").launch(server_port=7860)
    

if __name__ == "__main__":
    # Get mode from environment variable
    mode = os.getenv("MODE", "both").lower()
    
    if mode == "api":
        # Run only API
        print("Starting Portfolio Bot API only...", flush=True)
        run_flask()
    elif mode == "gradio":
        # Run only Gradio
        print("Starting Portfolio Bot Gradio interface only...", flush=True)
        run_gradio()
    else:
        # Run both (default)
        print("Starting Portfolio Bot with both API and Gradio interface...", flush=True)
        
        # Start Flask in a separate thread
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        # Run Gradio in main thread
        run_gradio()
    