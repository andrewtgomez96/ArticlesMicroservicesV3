from flask import Flask, request, jsonify
#import sqlite3
import datetime
from rfeed import *
import requests
from httpcache import CachingHTTPAdapter
from httpcache import HTTPCache

#Create the flask app
app = Flask(__name__)

#Max Number of articles the RSS feed will return
COUNT = 10

#RSS MicroService to fetch the 10 most recent articles
@app.route("/articles/rss")
def rss():
    s = requests.Session()
    s.mount("http://localhost/articles" + str(COUNT), CachingHTTPAdapter(COUNT))
    cache = HTTPCache()
    
    #List that will hold articles
    items = []

    #access the articles microservice
    link = "http://localhost/articles/" + str(COUNT)
    rArticles = requests.get(link)

    #Check if got an 'OK' status to conntinue
    if rArticles.status_code == 200:
        print("Connection Establish")

    #Retrive atricles metadata from articles microserice
    link = "http://localhost/articles/" + str(COUNT)
    rInfoArticles = requests.get(link)

    #Check if established connection
    if rInfoArticles.status_code == 200:
        print('Establish Connection')
        data=rInfoArticles.json
        for i in range(len(data)):
            #add body with comments underneath
            content = data[i]["body"] + "\n\n"
            content += data[i]["comments"]
            item = Item(
                    title = data[i]["title"],
                    link = "http://localhost/articles" + str(data[i]["title"]),
                    description = content,
                    author = data[i]["username"],
                    pubDate=data[i]["created"]
                    )
            items.append(item)

    #The format of an Item object given by rfeed
    item = Item(
            title = "New Article",
            link = "example.com/articles/2",
            description = "Sample Article",
            author = "EM",
            pubDate = datetime.datetime.now())

    items.append(item)

    #Title of the RSS feed given by rfeee
    feed = Feed(
            title = "Articles RSS Feed",
            link = "http://localhost/Article",
            description = "A summary feed for the 10 most recent articles",
            language = "en-US",
            lastBuildDate = datetime.datetime.now(),
            items = items)
    cache.store(rInfoArticles )

    return feed.rss()
