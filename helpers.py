from flask import render_template
from werkzeug.security import check_password_hash, generate_password_hash

def gen_hash(pw):
    pwhash = generate_password_hash(pw, method=f'pbkdf2:sha256:150000', salt_length=8)
    print(pwhash)
    return pwhash


def recollect_hash(pw, salt):
    return f"pbkdf2:sha256:150000${salt}${pw}"


def error(msg):
    return render_template("error.html", msg=msg)


def jsonify_book(book):
    return {
        "isbn":book[0],
        "title":book[1],
        "author":book[2],
        "year":book[3]
    }