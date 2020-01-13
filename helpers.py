from flask import render_template, make_response, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from time import time

def gen_hash(pw):
    pwhash = generate_password_hash(pw, method=f'pbkdf2:sha256:150000', salt_length=8)
    print(pwhash)
    return pwhash


def recollect_hash(pw, salt):
    return f"pbkdf2:sha256:150000${salt}${pw}"


def json_error(msg, code):
    return make_response(jsonify(msg), code)


def error(msg, code):
    return render_template("error.html", msg=msg), code if code else 200


def jsonify_book(book):
    return {
        "isbn": book[0],
        "title": book[1],
        "author": book[2],
        "year": book[3],
        "our_rating": book[4] if book[4] is not None else "Unrated"
    }