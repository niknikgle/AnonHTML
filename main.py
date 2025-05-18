from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
    flash,
)
from datetime import datetime
import json
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import requests

app = Flask(__name__)

load_dotenv()

DATA_FILE = "forum_data.json"
UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

RECAPTCHA_SECRET = os.getenv("RECAPTCHA_SECRET")

app.secret_key = os.getenv("FLASK_SECRET_KEY", "a‑hard‑to‑guess‑value")


app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Create the uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def verify_recaptcha(response_token, remote_ip=None):
    """Send verification request to Google."""
    payload = {
        "secret": RECAPTCHA_SECRET,
        "response": response_token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    r = requests.post("https://www.google.com/recaptcha/api/siteverify", data=payload)
    result = r.json()
    return result.get("success", False)


@app.route("/")
def index():
    threads = load_data()

    def latest_activity(thread):
        if thread["replies"]:
            # Get the latest reply timestamp
            return max(reply["timestamp"] for reply in thread["replies"])
        else:
            # No replies; use the thread's own timestamp
            return thread["timestamp"]

    # Sort threads by latest activity in descending order
    threads.sort(key=latest_activity, reverse=True)

    # Add formatted timestamps to each thread
    for thread in threads:
        thread["created_at"] = datetime.fromisoformat(thread["timestamp"]).strftime(
            "%b %d, %Y %I:%M %p"
        )
        if thread["replies"]:
            latest_reply = max(thread["replies"], key=lambda r: r["timestamp"])
            thread["last_reply"] = datetime.fromisoformat(
                latest_reply["timestamp"]
            ).strftime("%b %d, %Y %I:%M %p")
        else:
            thread["last_reply"] = None

    recaptcha_site_key = os.getenv("RECAPTCHA_PUBLIC")

    return render_template(
        "index.html", threads=threads, recaptcha_site_key=recaptcha_site_key
    )


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
    recaptcha_response = request.form.get("g-recaptcha-response")

    if not recaptcha_response or not verify_recaptcha(
        recaptcha_response, request.remote_addr
    ):
        flash("CAPTCHA verification failed. Please try again.", "error")
        return redirect("/")

    threads.append(thread)
    save_data(threads)
    return redirect(f"{url_for('index')}#thread-{new_id}")


@app.route("/reply/<int:thread_id>", methods=["POST"])
def reply(thread_id):
    threads = load_data()
    for thread in threads:
        if thread["id"] == thread_id:
            # Base reply data
            reply = {
                "nickname": request.form.get("nickname", "Anon"),
                "content": request.form["content"],
                "timestamp": datetime.now().isoformat(),
                "image_url": None,
            }

            # Handle file upload
            file = request.files.get("image")
            if file and allowed_file(file.filename):
                filename = secure_filename(
                    f"{thread_id}_{int(datetime.now().timestamp())}_{file.filename}"
                )
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)
                # URL that the template can use
                reply["image_url"] = url_for("uploaded_file", filename=filename)

            thread["replies"].append(reply)
            save_data(threads)
            reply_index = len(thread["replies"]) - 1
            return redirect(
                url_for(
                    "view_thread", thread_id=thread_id, _anchor=f"reply-{reply_index}"
                )
            )
    return "Thread not found", 404


# Serve uploaded files
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.template_filter("datetimeformat")
def datetimeformat(value, fmt="%B %d, %Y %I:%M %p"):
    from datetime import datetime

    dt = datetime.fromisoformat(value)
    return dt.strftime(fmt)


if __name__ == "__main__":
    app.run(debug=True)
