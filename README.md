# CS50's Web Programming with Python and JavaScript, Project 1, Books

---

## Introduction:
This is my first project in [CS50 Web](https://courses.edx.org/courses/course-v1:HarvardX+CS50W+Web/course/).

---

## What is this?
This is the very project required in the course ( the second if you count project 0 ),
In this project data is fetched from goodreads, aswell as from our own database, created in heroku, this data is then viewed to the user on requst,
Users are allowed to search our database for movies by isbn, book title or author's name, aswell as add reviews to each book.
The data viewed when searching a book comes from both sources mentioned previously - our database and goodreads' -.

## Folders:
### templates/ *(Views)*:
This contains the templates which view the data to the user as instructed via **application.py**, these files are written in html, javascript and jinja2 templating language.
### static/
Contains static files such as images and css files.
## Individual files:
### application.py *(Controller)*:
This is the entry point to our program that contains the python code that runs our program.
### helpers.py:
Contains some helping functions that assist the **application.py** in doing its job.
### books.csv:
This file contains a comma-separated-list of books that are in our database.
### config-example.json:
This file contains an example of how a **config.json** file should be, in order for the application to work it's required to insert the required keys in to their placeholders and rename this file to **config.json**.
### Database.db:
This file contains the layout of the database, could be used to create the database, then we can use **import.py** to import the database entries from books.csv.
### import.py:
This file imports the books and authors from the **books.csv** file to the database.
### requirements.txt:
Contains a list of required libraries to be installed in order for this application to work properly.
