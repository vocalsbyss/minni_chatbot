from flask import Flask, render_template, request, jsonify, session
import os
import requests
from datetime import timedelta, datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(hours=1)

# 🔑 Replace with your OpenRouter API key
OPENROUTER_API_KEY = "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"

# OpenRouter API endpoint
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}


# ---------------- Utilities ---------------- #
def get_current_time():
    return datetime.now().strftime("%H:%M:%S")

def get_current_date():
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

def init_chat_history():
    if 'chat_history' not in session:
        session['chat_history'] = [
            {
                "role": "system",
                "content": (
                    "You are a helpful and friendly AI assistant. "
                    f"Today's date is {get_current_date()} and the current time is {get_current_time()}."
                )
            }
        ]


# ---------------- Chatbot Logic ---------------- #
def chatbot_response(user_input):
    init_chat_history()
    session['chat_history'].append({"role": "user", "content": user_input})

    # Update system prompt if user asks about date/time
    if is_time_date_question(user_input):
        session['chat_history'][0] = {
            "role": "system",
            "content": (
                "You are a helpful and friendly AI assistant that knows the current date and time. "
                f"Today's date is {get_current_date()} and the current time is {get_current_time()}."
            )
        }

    payload = {
        "model": "openai/gpt-3.5-turbo",  # ✅ You can change to any model from OpenRouter (e.g., anthropic/claude-3.5-sonnet, openai/gpt-4o-mini)
        "messages": session['chat_history']
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        bot_reply = data['choices'][0]['message']['content'].strip()
        session['chat_history'].append({"role": "assistant", "content": bot_reply})

        # Keep history short
        if len(session['chat_history']) > 20:
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


# ---------------- Routes ---------------- #
@app.route('/')
def index():
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
    session.pop('chat_history', None)
    return jsonify({"status": "success"})


if __name__ == '__main__':
    app.run(debug=True)
