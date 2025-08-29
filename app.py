from flask import Flask, render_template, request, jsonify, session
import os
import requests
from datetime import timedelta
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(hours=1)

# Use your API key (in production, use environment variables)
OPENROUTER_API_KEY = "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"

# OpenRouter endpoint and headers
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}

# Initialize conversation history in session
def init_chat_history():
    if 'chat_history' not in session:
        session['chat_history'] = [
            {"role": "system", "content": "You are a helpful and friendly AI assistant that knows the current date and time. When asked about time or date, provide accurate information based on the server's current time. Today's date is " + 
             get_current_date() + " and the current time is " + get_current_time() + "."}
        ]

def get_current_time():
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")

def get_current_date():
    from datetime import datetime
    return datetime.now().strftime("%B %d, %Y")

def is_time_date_question(user_input):
    time_date_keywords = [
        'time', 'date', 'day', 'today', 'tomorrow', 'yesterday', 
        'week', 'month', 'year', 'clock', 'calendar', 'schedule',
        'hour', 'minute', 'second', 'what time', 'what date', 'what day',
        'current time', 'current date', 'what is the time', 'what is the date',
        'time now', 'date today', 'day today', 'now'
    ]
    
    return any(keyword in user_input.lower() for keyword in time_date_keywords)

def chatbot_response(user_input):
    # Initialize chat history if not exists
    init_chat_history()
    
    # Add user message to history
    session['chat_history'].append({"role": "user", "content": user_input})
    
    # For time/date questions, add current time/date to context
    if is_time_date_question(user_input):
        # Update system message with current time/date
        session['chat_history'][0] = {"role": "system", "content": 
            "You are a helpful and friendly AI assistant that knows the current date and time. " +
            "When asked about time or date, provide accurate information based on the server's current time. " +
            f"Today's date is {get_current_date()} and the current time is {get_current_time()}."}
    
    # ChatGPT-like payload
    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": session['chat_history']
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        bot_reply = data['choices'][0]['message']['content'].strip()
        
        # Add bot response to history
        session['chat_history'].append({"role": "assistant", "content": bot_reply})
        
        # Limit history to prevent session from getting too large
        if len(session['chat_history']) > 20:  # Keep last 10 exchanges
            session['chat_history'] = session['chat_history'][-20:]
            
        session.modified = True
        return bot_reply
        
    except requests.exceptions.Timeout:
        return "Sorry, the request timed out. Please try again."
    except requests.exceptions.RequestException as e:
        print("API Error:", e)
        return "Sorry, I'm having trouble connecting to the service right now."
    except Exception as e:
        print("Unexpected Error:", e)
        return "Sorry, something went wrong. Please try again later."

@app.route('/')
def index():
    # Initialize chat history on first visit
    init_chat_history()
    return render_template('index.html')

@app.route('/get', methods=['POST'])
def get_bot_response():
    try:
        user_message = request.json.get("message")
        if not user_message or not user_message.strip():
            return jsonify({"reply": "Please enter a message."})
            
        bot_reply = chatbot_response(user_message)
        return jsonify({"reply": bot_reply})
    except Exception as e:
        print("Error in get_bot_response:", e)
        return jsonify({"reply": "An error occurred processing your request."})

@app.route('/clear', methods=['POST'])
def clear_chat():
    # Clear the chat history
    session.pop('chat_history', None)
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)