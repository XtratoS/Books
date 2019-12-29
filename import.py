from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from csv import reader
import json
import os

def main():
    # load the configuration file
    try:
        with open("config.json", mode='r') as config_file:
            config = json.load(config_file)
            os.environ["DATABASE_URL"] = config["DATABASE_URL"]
    except:
        print("Couldn't open file config.json")
        return 1

    # Set up database
    engine = create_engine(os.getenv("DATABASE_URL"))
    db = scoped_session(sessionmaker(bind=engine))

    # read the file and add the data to the memory
    data = []
    try:
        with open("books.csv") as csvfile:
            csv_reader = reader(csvfile, delimiter=",")
            for line in csv_reader:
                data.append(line)
    except:
        print("Couldn't open file books.csv")
        return 1
    data.pop(0)
    authors = set([datum[2] for datum in data])
    lauth = len(authors)
    l = len(data)
    c = 0
    # construct queries to add authors to database from memory
    for author in authors:
        db.execute("INSERT INTO authors (name) VALUES (:name)", {"name":author})
        if c % 15 == 0:
            print("Adding Authors: " + "{0:.2f}".format(c / lauth * 100) + "%", end="\r")
        c += 1
    print("Adding Authors: 100.00%")
    db.commit()
    c = 0
    for datum in data:
        name = datum[2]
        auth_id = db.execute("SELECT id FROM authors WHERE name = :name", {"name":name}).fetchone()[0]
        db.execute("INSERT INTO books (isbn, title, author_id, year) VALUES (:isbn, :title, :author_id, :year)", {"isbn":datum[0], "title":datum[1], "author_id":auth_id, "year":datum[3]})
        if c % 15 == 0:
            print("Adding Books: " + "{0:.2f}".format(c / l * 100) + "%", end="\r")
        c += 1
    db.commit()
    print("Adding Books: 100.00%")
if __name__ == "__main__":
    main()