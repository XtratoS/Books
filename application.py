import json
import os

import requests
from flask import Flask, redirect, render_template, request, session, url_for
from flask_login import login_required, LoginManager
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import gen_hash, error, recollect_hash


app = Flask(__name__)

# load the configuration file
with open("config.json") as config_file:
    config = json.load(config_file)
    os.environ["DATABASE_URL"] = config["DATABASE_URL"]
    os.environ["GOODREADS"] = config["API_KEY"]

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
    if session.get("user_id") == None:
        # not logged in
        return "Please Login"
    # logged in
    return "Logged in as " + session.get("username")


@app.route("/login", methods=["GET", "POST"])
def login():
    # GET
    if request.method == "GET":
        return render_template("login.html")
    # POST
    username = request.form.get("username")
    password = request.form.get("password")
    query = db.execute("SELECT * FROM users WHERE username = :username", {"username":username}).fetchone()
    if not query:
        return error("Invalid Username/Password")
    pwhash = recollect_hash(query[2], query[3])
    print(pwhash)
    if not check_password_hash(pwhash, password):
        return error("INVALID")
    session["user_id"] = query[0]
    session["username"] = query[1]
    return redirect(url_for("index"))


@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    #Check if user is logged in
    if session.get("user_id") is not None:
        return redirect(url_for("index"))
    #GET
    if request.method == "GET":
        return render_template("register.html")
    #POST
    username = request.form.get("username")
    password = request.form.get("password")
    if not username or not password:
        return "Error"
    fullhash = gen_hash(password)
    print(fullhash)
    hasarray = fullhash.split(":")[2].split('$')
    salt = hasarray[1]
    pwhash = hasarray[2]
    db.execute("INSERT INTO users (username, password, salt) VALUES (:username, :password, :salt)", {"username":username, "password":pwhash, "salt":salt})
    db.commit()
    return redirect(url_for("index"))