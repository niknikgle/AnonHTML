from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import json
import os

app = Flask(__name__)

DATA_FILE = "forum_data.json"


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


@app.route("/")
def index():
    threads = load_data()
    return render_template("index.html", threads=threads)


@app.route("/thread/<int:thread_id>")
def view_thread(thread_id):
    threads = load_data()
    thread = next((t for t in threads if t["id"] == thread_id), None)
    if not thread:
        return "Thread not found", 404
    return render_template("thread.html", thread=thread)


@app.route("/new_thread", methods=["POST"])
def new_thread():
    threads = load_data()
    new_id = max([t["id"] for t in threads], default=0) + 1
    thread = {
        "id": new_id,
        "title": request.form["title"],
        "nickname": request.form.get("nickname", "Anon"),
        "content": request.form["content"],
        "timestamp": datetime.now().isoformat(),
        "replies": [],
    }
    threads.append(thread)
    save_data(threads)
    return redirect(url_for("index"))


@app.route("/reply/<int:thread_id>", methods=["POST"])
def reply(thread_id):
    threads = load_data()
    for thread in threads:
        if thread["id"] == thread_id:
            reply = {
                "nickname": request.form.get("nickname", "Anon"),
                "content": request.form["content"],
                "timestamp": datetime.now().isoformat(),
            }
            thread["replies"].append(reply)
            save_data(threads)
            return redirect(url_for("view_thread", thread_id=thread_id))
    return "Thread not found", 404


if __name__ == "__main__":
    app.run(debug=True)
