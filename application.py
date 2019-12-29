import json
import os

import requests
from flask import Flask, redirect, render_template, request, session, url_for
from flask_login import login_required, LoginManager
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import gen_hash, error, recollect_hash, jsonify_book
from time import time

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

# Temporary storage for data from api
ratings = {}

@app.route("/")
def index():
    return render_template("index.html")


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
    hasarray = fullhash.split(":")[2].split('$')
    salt = hasarray[1]
    pwhash = hasarray[2]
    db.execute("INSERT INTO users (username, password, salt) VALUES (:username, :password, :salt)", {"username":username, "password":pwhash, "salt":salt})
    db.commit()
    return redirect(url_for("index"))


@app.route("/search", methods=["GET", "POST"])
def search():
    # GET
    if request.method == "GET":
        return render_template("search.html")
    # POST
    else:
        search_string = request.form.get("search")
        search_res_proxy = db.execute("SELECT isbn, title, name, year FROM books JOIN authors ON books.author_id = authors.id WHERE isbn LIKE :S OR title LIKE :S OR authors.name LIKE :S;", {"S": f"%{search_string}%"}).fetchall()
        jsonified_results = [jsonify_book(book) for book in search_res_proxy]
        return render_template("search.html", search_string=search_string ,results=jsonified_results)


@app.route("/books/<string:isbn>", methods=["GET"])
def books(isbn):
    # GET
    book = jsonify_book(db.execute("SELECT isbn, title, name, year FROM books JOIN authors ON books.author_id = authors.id WHERE isbn = :isbn",
        {"isbn":isbn}).fetchone())
    reviews = db.execute("SELECT username, text, rating FROM reviews JOIN users ON reviews.user_id = users.id WHERE book_id = :isbn",
        {"isbn": isbn}).fetchall()
    our_avg_float = db.execute("SELECT AVG(rating) FROM reviews WHERE book_id = :isbn",
        {"isbn": isbn}).fetchone()[0] or 2.5
    our_avg = "{0:.2f}".format(our_avg_float)
    now = round(time())
    # Only use the api if there's no ratings for the book in the database or if it's been more than 1 minute since the last request
    if not ratings.get(isbn, False) or now - ratings.get(isbn, {'time':0})['time'] > 60:
        response = requests.get(f"https://www.goodreads.com/book/review_counts.json?isbns={isbn}")
        goodreads_book = response.json()['books'][0]
        if response.status_code != 200:
            return error("Unexpected error, book not found in goodread's library")
        ratings[isbn] = {
            'time': round(time()),
            'avg': goodreads_book['average_rating'],
            'count': goodreads_book['work_ratings_count']
        }
    data = {
        'isbn': book['isbn'],
        'title': book['title'],
        'author': book['author'],
        'rating': our_avg,
        'goodreads_rating': ratings[book['isbn']]['avg'],
        'goodreads_count': ratings[book['isbn']]['count'],
        'reviews': reviews
    }
    return render_template('book.html', data=data)