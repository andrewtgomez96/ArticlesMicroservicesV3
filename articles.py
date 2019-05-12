#article
#1 posting a new article
#2 retrieve an existing article
#3 edit an existing article (update TIMESTAMP)
#4 delete an existing article
#5 retrieve contents of n most recent getArticles
#6 retrieve metadata for an article

from init_db import init_db
from flask import Flask, current_app, request, jsonify
import click
import json
import uuid
from flask.cli import with_appcontext
from flask_cassandra import CassandraCluster
from flask_bcrypt import Bcrypt #added
from flask_basicauth import BasicAuth #added

app = Flask(__name__)
'''
if you run 'flask init-db-command' it will drop the current database and reinitialize it from
the scheme.sql file which resets the db, inserting 3 rows in each table
'''
@app.cli.command()
@with_appcontext
def init_db_command():
    click.echo('clearing the existing data and creating a new KEYSPACE with two column families')
    r = init_db(cassandra)
    click.echo('Initialized the database Blog column family with: \n' + str(r))

cassandra = CassandraCluster()
app.config['CASSANDRA_NODES'] = ['172.17.0.2']  # can be a string or list of nodes

# 1 function for posting single article
@app.route("/article/new", methods=['POST'])
def newArticle():
    session = cassandra.connect()
    session.set_keyspace("db")
    if (request.authorization):
        username = request.authorization.username
        password = request.authorization.password
        title = request.form.get('title')
        body = request.form.get('body')
        tags = request.form.get('tags')
        if(username and password and title and body and tags):
            tags = tags.split(",")
            tags = set(tags)
            insertArticle = (username, title, body, tags)
            session.execute("INSERT INTO Blog (articleId, username, title, body, createdArt, tags) VALUES (uuid(), %s, %s, %s, toTimestamp(now()), %s)", insertArticle)
            artId = session.execute("SELECT articleId FROM Blog WHERE username = %s ORDER BY createdArt desc LIMIT 1", (username,))
            artId = artId[0][0]
            return jsonify({'articleId' : artId}), 201
        else:
            return jsonify('Please input all of the url and form data required in the documentation'), 404
    else:
        return jsonify('Unauthorized response'), 401

#2 retrieve existing article
@app.route("/article/<string:articleId>", methods=['GET'])
def getArticle(articleId):
    session = cassandra.connect()
    session.set_keyspace("db")
    articleId = uuid.UUID(articleId)
    #check if articleId exists in DB
    r = session.execute("SELECT json * FROM Blog WHERE articleId = %s ", (articleId,))
    if(r):
        jsonR = r[0].json
        article = json.loads(jsonR)
        #article = article['tags']
        return jsonify(article), 200
    else:
        return jsonify('Article Not found'), 404

#3 edit existing article
@app.route("/article/<string:articleId>", methods=['PATCH'])
def editArticle(articleId):
    session = cassandra.connect()
    session.set_keyspace("db")
    articleId = uuid.UUID(articleId)
    if (request.authorization):
        username = request.authorization.username
        password = request.authorization.password
        title = request.form.get('title')
        body = request.form.get('body')
        tags = request.form.get('tags')
        if(username and password and title and body and tags):
            tags = tags.split(",")
            tags = set(tags)
            #check if articleId exists in DB
            createdArt = session.execute("SELECT createdArt FROM Blog WHERE articleId = %s ", (articleId,))
            authorArt = session.execute("SELECT username FROM Blog WHERE articleId = %s ", (articleId,))
            if(createdArt and authorArt):
                createdArt = createdArt[0].createdart
                authorArt = authorArt[0].username
                if(authorArt == username):
                    insertArticle = (articleId, username, title, body, createdArt, tags)
                    session.execute("INSERT INTO Blog (articleId, username, title, body, createdArt, tags) VALUES (%s, %s, %s, %s, %s, %s)", insertArticle)
                    r = session.execute("SELECT json * FROM Blog WHERE articleId = %s ", (articleId,))
                    jsonR = r[0].json
                    article = json.loads(jsonR)
                    return jsonify(article), 200
                else:
                    return jsonify('You are not authorized to edit this article'), 401
            else:
                return jsonify('articleId was not found'), 404

        else:
            return jsonify('Please input all of the url and form data required in the documentation'), 404
    else:
        return jsonify('Unauthorized response'), 401

#4  delete and existing article
@app.route("/article/<int:articleId>", methods=['DELETE']) #allow both GET and POST requests
def deleteArticle(articleId):
    cur = db.connection.cursor()
    if (request.authorization):
        username = request.authorization.username
        password = request.authorization.password
    else:
        return ('Unauthorized response'), 401
    #check if articleId exists in DB
    #authenticate
    if(checkAuth(username, password) == True):
        cur.execute("SELECT title, body FROM Article WHERE artId = ? ", (articleId,))
        returnObject = cur.fetchone()
        if(returnObject):
            #Delete article
            cur.execute("DELETE FROM article WHERE artID = ?", (articleId,))
            db.connection.commit()
            return jsonify({'Successfully deleted article' : articleId}), 200
        else:
            jsonify('Article Not found'), 404
    else:
        return jsonify('Credentials not found'), 409

#5 retrieve contents of n most recent articles
@app.route("/articles/<int:n>", methods=['GET'])
def getArticles(n):
    session = cassandra.connect()
    session.set_keyspace("db")
    #Retrieve n most recent articles
    r = session.execute("SELECT title, body FROM Blog LIMIT %s", (n,))
    jsonR = []
    i = 0
    for row in r:
        jsonR.append({
            'title': row.title,
            'body': row.body
        })
        i=i+1
    return jsonify(jsonR), 200

#6 retrieve meta data of n most recent articles
@app.route("/articles/info/<int:n>", methods=['GET'])
def getMetaArticles(n):
    session = cassandra.connect()
    session.set_keyspace("db")
    #Retrieve n most recent articles
    r = session.execute("SELECT title, body, username, createdArt FROM Blog LIMIT %s", (n,))
    jsonR = []
    i = 0
    for row in r:
        print(row)
        jsonR.append({
            'title': row.title,
            'body': row.body,
            'username': row.username,
            'createdArt': row.createdart
        })
        i=i+1
    return jsonify(jsonR), 200



if(__name__ == '__main__'):
    app.run(debug=True)
