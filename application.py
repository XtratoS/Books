#!/usr/bin/python3
import json
import os

import requests
from flask import Flask, redirect, render_template, request, session, url_for, jsonify
from tempfile import mkdtemp
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import gen_hash, error, recollect_hash, jsonify_book, json_error
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
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

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
        msg = request.args.get("msg")
        if msg:
            return render_template("login.html", msg=msg)
        return render_template("login.html")
    # POST
    username = request.form.get("username")
    password = request.form.get("password")
    query = db.execute("SELECT * FROM users WHERE username = :username", {"username":username}).fetchone()
    if not query:
        return render_template("login.html", msg="Invalid username or password")
    pwhash = recollect_hash(query[2], query[3])
    if not check_password_hash(pwhash, password):
        return render_template("login.html", msg="Invalid username or password")
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
        # get data from form
        search_string = request.form.get("search")
        substitutions = {"S": f"%{search_string}%"}
        search_options = request.form.getlist("search-option")
        # create the query dynamically
        query = "SELECT isbn, title, name, year FROM books JOIN authors ON books.author_id = authors.id WHERE"
        i = 0
        # force the 3 options if no options were selected
        default_options = ['isbn', 'title', 'name'] 
        if len(search_options) == 0:
            search_options = default_options
        for option in search_options:
            if option not in default_options:
                return error("Unexpected error")
            if "LIKE" in query:
                query += " OR"
            query += f" {option} ILIKE :S"
            i = i+1
        query += ';'
        # execute the query and fetch results
        search_res_proxy = db.execute(query, substitutions).fetchall()
        jsonified_results = [jsonify_book(book) for book in search_res_proxy]
        return render_template("search.html", search_string=search_string, results=jsonified_results, search_options=search_options)


@app.route("/api/<string:isbn>", methods=["GET"])
def api(isbn):
    # GET
    # Get book data from database
    book_queryres = db.execute("SELECT isbn, title, name, year FROM books JOIN authors ON books.author_id = authors.id WHERE isbn = :isbn",
        {"isbn":isbn}).fetchone()
    if not book_queryres:
        return json_error("Book not found", 404)
    book = jsonify_book(book_queryres)

    # Get book reviews from database
    reviews = db.execute("SELECT username, text, rating FROM reviews JOIN users ON reviews.user_id = users.id WHERE book_id = :isbn",
        {"isbn": isbn}).fetchall()
    
    # Get book average rating from database
    our_avg_float_queryres = db.execute("SELECT AVG(rating), COUNT(*) FROM reviews WHERE book_id = :isbn",
        {"isbn": isbn}).fetchone()
    
    # Check for None
    if not our_avg_float_queryres[0]:
        our_avg_float = 0
    else:
        our_avg_float = our_avg_float_queryres[0]
    
    # Get the count
    our_count = our_avg_float_queryres[1]
    
    # Format the average rating properly
    our_avg = "{0:.2f}".format(our_avg_float)

    # Get current time
    now = round(time())

    # Only use the api if there's no ratings for the book in the database or if it's been more than 1 minute since the last request
    if not ratings.get(isbn, False) or now - ratings.get(isbn, {'time':0})['time'] > 60:
        # Initiate the API request
        response = requests.get(f"https://www.goodreads.com/book/review_counts.json?isbns={isbn}")
        # Check the status code of the response, generate response if failture
        if response.status_code != 200:
            goodreads_book = {
                'average_rating':0,
                'work_ratings_count':0
            }
        else:
            goodreads_book = response.json()['books'][0]
        # Format the ratings
        ratings[isbn] = {
            'time': round(time()),
            'avg': goodreads_book['average_rating'],
            'count': goodreads_book['work_ratings_count']
        }
    
    # Reformat reviews
    reviews = [{"username":rev[0], "text":rev[1], "rating":rev[2]} for rev in reviews]

    # Reformat the data before returning the response
    data = {
        'isbn': book['isbn'],
        'title': book['title'],
        'author': book['author'],
        'rating': our_avg,
        'our_count': our_count,
        'goodreads_rating': ratings[book['isbn']]['avg'],
        'goodreads_count': ratings[book['isbn']]['count'],
        'reviews': reviews
    }
    print(data)
    return jsonify(data)


# Use own API and pass data to books.html view
@app.route("/books/<string:isbn>", methods=["GET"])
def books(isbn):
    api_response = requests.get(request.base_url.replace("books", "api"))
    if api_response.status_code != 200:
        return error("Book not found", api_response.status_code)
    data = api_response.json()
    return render_template("book.html", data=data)


# Add a review to a book
@app.route("/review/<string:isbn>", methods=["GET", "POST"])
def review(isbn):
    if session.get('user_id') is None:
        return redirect(url_for("login", msg="Please login to add a review"))
    # Double check that this book exists
    api_response = requests.get(request.base_url.replace("review", "api"))
    if api_response.status_code != 200:
        return error("Book not found", api_response.status_code)
    # Check if the user already has a review for this book
    rev_query = db.execute("SELECT COUNT(*) FROM reviews WHERE user_id = :user_id AND book_id = :isbn",
        {"user_id": session["user_id"], "isbn": isbn})
    res = rev_query.fetchone()
    if res != None and res[0] > 0:
        return render_template("review.html", data=data, msg="You have already reviewed this book")
    data = api_response.json()
    # GET
    if request.method == "GET":
        return render_template("review.html", data=data)
    # POST
    rating = request.form.get("rating")
    text = request.form.get("text")
    if not rating:
        return render_template("review.html", data=data, msg="Invalid Star Rating provided, please try again")
    db.execute("INSERT INTO reviews (user_id, book_id, text, rating) VALUES (:user_id, :book_id, :text, :rating)",
    {"user_id": session.get('user_id'), "book_id": isbn, "text": text, "rating": rating})
    return redirect(url_for("books", isbn=isbn))


# @app.route("/review", methods=["GET"])
# def review()