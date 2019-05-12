#tag
# 1 Add an article with a new tag
# 2 Add another tag to the article and # 3 Add a tag to an article that doesn’t exist
# 4 Delete one or more of the tags from the article
# 5 List all articles with the new tag NOT DONEEEEE
# 6 Retrieve the tags for an individual URL
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

#1
@app.route("/article/tag/<string:tag>", methods=['POST'])
def addArtTag(tag):
    session = cassandra.connect()
    session.set_keyspace("db")
    if (request.authorization):
        username = request.authorization.username
        password = request.authorization.password
        title = request.form.get('title')
        body = request.form.get('body')
        tags = {tag}
        if(username and password and title and body and tag):
            insertArticle = (username, title, body, tags)
            session.execute("INSERT INTO Blog (articleId, username, title, body, createdArt, tags) VALUES (uuid(), %s, %s, %s, toTimestamp(now()), %s)", insertArticle)
            artId = session.execute("SELECT articleId FROM Blog WHERE username = %s ORDER BY createdArt desc LIMIT 1", (username,))
            artId = artId[0][0]
            return jsonify({'articleId' : artId, 'tag' : tag}), 201
        else:
            return jsonify('Please input all of the url and form data required in the documentation'), 404
    else:
        return jsonify('Unauthorized response'), 401


#2 and 3
#@app.route("/article/<int:articleId>/tag/<string:tag>", methods=['PUT'])
@app.route("/article/<string:articleId>/tag/<string:tag>", methods=['PUT'])
def addTag(articleId, tag):
    session = cassandra.connect()
    session.set_keyspace("db")
    username = None
    articleId = uuid.UUID(articleId)
    if (request.authorization):
        username = request.authorization.username
        createdArt = session.execute("SELECT createdArt FROM Blog WHERE articleId = %s ", (articleId,))
        authorArt = session.execute("SELECT username FROM Blog WHERE articleId = %s ", (articleId,))
        if(createdArt and authorArt):
            createdArt = createdArt[0].createdart
            authorArt = authorArt[0].username
            if(username == authorArt):
                insertTag = (tag, authorArt, createdArt)
                    #cant update on just the secondary index so have to supply primary index of username/author
                session.execute('''UPDATE Blog SET tags = tags + {%s} WHERE username = %s AND createdArt = %s''', insertTag)
                r = session.execute("SELECT json tags FROM Blog WHERE articleId = %s", (articleId,))
                jsonR = r[0].json
                tags = json.loads(jsonR)
                tags = tags['tags']
                return jsonify({'articleId' : articleId, 'tags' : tags}), 201
            else:
                return jsonify('you are not authorized to alter this article'), 401
        else:
            return jsonify('articleId was not found'), 404
    else:
        return jsonify('Unauthorized response'), 401

#6
@app.route("/article/<string:articleId>/tags", methods=['GET'])
def getTags(articleId):
    session = cassandra.connect()
    session.set_keyspace("db")
    articleId = uuid.UUID(articleId)
    createdArt = session.execute("SELECT createdArt FROM Blog WHERE articleId = %s ", (articleId,))
    if(createdArt):
        createdArt = createdArt[0].createdart
        r = session.execute("SELECT json tags FROM Blog WHERE articleId = %s", (articleId,))
        jsonR = r[0].json
        tags = json.loads(jsonR)
        tags = tags['tags']
        return jsonify({'tags' : tags}), 200
    else:
        return jsonify('articleId was not found'), 404

#4
@app.route("/article/<string:articleId>/tag", methods=['DELETE'])
def deleteTags(articleId):
    session = cassandra.connect()
    session.set_keyspace("db")
    articleId = uuid.UUID(articleId)
    if (request.authorization):
        username = request.authorization.username
        password = request.authorization.password
    else:
        return jsonify('Unauthorized response'), 401
    returnTags = {}
    #array holding one or more tags to delete
    tags = request.form.get('tags')
    tags = tags.split(",")
    tags = set(tags)
    #check if articleId exists in DB
    createdArt = session.execute("SELECT createdArt FROM Blog WHERE articleId = %s ", (articleId,))
    authorArt = session.execute("SELECT username FROM Blog WHERE articleId = %s ", (articleId,))
    if(createdArt and authorArt):
        createdArt = createdArt[0].createdart
        authorArt = authorArt[0].username
        if(authorArt == username):
            print(tags)
            session.execute("UPDATE Blog SET tags = tags - %s WHERE username = %s AND createdArt = %s", (tags, authorArt, createdArt))
            r = session.execute("SELECT json tags FROM Blog WHERE articleId = %s", (articleId,))
            jsonR = r[0].json
            tags = json.loads(jsonR)
            tags = tags['tags']
            return jsonify({'articleId': articleId, 'tags' : tags}), 200
        else:
            return jsonify('You are not authorized to delete this tag'), 401
    else:
        return jsonify('articleId was not found'), 404

#5 STILL DIDNT DO
@app.route("/articles/tag/<string:tag>", methods=['GET'])
def getArticles(tag):
    session = cassandra.connect()
    session.set_keyspace("db")
    r = session.execute("SELECT json * FROM Blog WHERE tags CONTAINS %s ", (tag,))
    if(r):
        jsonR = r[0].json
        ids = json.loads(jsonR)
        ids = ids['articleId']
        return jsonify({'articleId' : ids}), 200
    else:
        return jsonify({'no articles matched your tag'}), 404




if(__name__ == '__main__'):
    app.run(debug=True)
