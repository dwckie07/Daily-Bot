import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "BOT IS WORKING"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()
