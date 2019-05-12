#comments
# 1 CHANGED Post a new comment on an article
# 2 CHANGED Delete an individual comment
# 3 Retrieve the number of comments on a given article
# 4 Retrieve the n most recent comments on a URL

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
#1  update an article that has same author and timestamp
#UUID = 724794aa-3310-4624-82a1-4e9347764318
@app.route("/article/<string:articleId>/comment", methods=['POST'])
def comment(articleId):
    session = cassandra.connect()
    session.set_keyspace("db")
    username = None
    comment = request.form.get('comment')
    #authorArt = request.form.get('author')
    articleId = uuid.UUID(articleId)
    if (request.authorization):
        username = request.authorization.username
    createdArt = session.execute("SELECT createdArt FROM Blog WHERE articleId = %s ", (articleId,))
    authorArt = session.execute("SELECT username FROM Blog WHERE articleId = %s ", (articleId,))
    if(createdArt and authorArt):
        createdArt = createdArt[0].createdart
        authorArt = authorArt[0].username
        if(username is not None):
            insertComment = (username, comment, authorArt, createdArt)
        else:
            insertComment = ('anonymous coward', comment, authorArt, createdArt)
            #cant update on just the secondary index so have to supply primary index of username/author
        session.execute('''UPDATE Blog SET comments = comments + [{'username': %s, 'comment': %s}] WHERE username = %s AND createdArt = %s''', insertComment)
        r = session.execute("SELECT comments, title FROM Blog WHERE articleId = %s", (articleId,))
        commentsR = str(r[0].comments)
        return jsonify({'articleId' : articleId, 'comments' : commentsR}), 201
    else:
        return jsonify('articleId was not found'), 404

#2
@app.route("/article/<string:articleId>/comment", methods=['DELETE'])
def deleteComment(articleId):
    session = cassandra.connect()
    session.set_keyspace("db")
    comment = request.form.get('comment')
    #authorArt = request.form.get('author')
    articleId = uuid.UUID(articleId)
    if (request.authorization):
        username = request.authorization.username
        password = request.authorization.password
    else:
        return jsonify('Unauthorized request'), 401
    createdArt = session.execute("SELECT createdArt FROM Blog WHERE articleId = %s ", (articleId,))
    authorArt = session.execute("SELECT username FROM Blog WHERE articleId = %s ", (articleId,))
    if(createdArt and authorArt):
        createdArt = createdArt[0].createdart
        authorArt = authorArt[0].username
        #PAY SPECIAL ATTENTION TO THIS QUERY AND THE CHECK BELOW comments is for when authorArt is given wrong
        #comments[0].comments is for when authorArt has an article with no comments
        comments = session.execute("SELECT comments FROM Blog WHERE username = %s AND createdArt = %s", (authorArt, createdArt))
        if(comments and comments[0].comments):
            comments = comments[0].comments

            authorComments = [x for x in comments if x['username'] == username]
            authorComment = [x for x in authorComments if x['comment'] == comment]

            if(authorComment):
                authorComment = authorComment[0]['username']

                session.execute("UPDATE Blog SET comments = comments - [{'username': %s, 'comment': %s}] WHERE username = %s AND createdArt = %s", (username, comment, authorArt, createdArt))
                return jsonify('comment deleted'), 200
            else:
                return jsonify('you are not authorized to delete this comment or your comment does not exist'), 401
        else:
            return jsonify('no comments for the articleId and author given'), 404
    else:
        return jsonify('articleId was not found'), 404

#3
@app.route("/article/<string:articleId>/comments", methods=['GET'])
def getNumOfComments(articleId):
    session = cassandra.connect()
    session.set_keyspace("db")
    #authorArt = request.form.get('author')
    articleId = uuid.UUID(articleId)
    createdArt = session.execute("SELECT createdArt FROM Blog WHERE articleId = %s ", (articleId,))
    authorArt = session.execute("SELECT username FROM Blog WHERE articleId = %s ", (articleId,))
    if(createdArt and authorArt):
        createdArt = createdArt[0].createdart
        authorArt = authorArt[0].username
        comments = session.execute("SELECT comments FROM Blog WHERE username = %s AND createdArt = %s", (authorArt, createdArt))
        if(comments and comments[0].comments):
            comments = comments[0].comments
            return jsonify(len(comments)), 200
        else:
            return jsonify('no comments for the articleId and author given'), 404
    else:
        return jsonify('articleId was not found'), 404

#4
@app.route("/article/<string:articleId>/comments/<int:n>", methods=['GET'])
def getNComments(articleId, n):
    session = cassandra.connect()
    session.set_keyspace("db")
    articleId = uuid.UUID(articleId)
    createdArt = session.execute("SELECT createdArt FROM Blog WHERE articleId = %s ", (articleId,))
    authorArt = session.execute("SELECT username FROM Blog WHERE articleId = %s ", (articleId,))
    if(createdArt and authorArt):
        createdArt = createdArt[0].createdart
        authorArt = authorArt[0].username
        comments = session.execute("SELECT json comments FROM Blog WHERE username = %s AND createdArt = %s", (authorArt, createdArt))
        if(comments and comments[0].json):
            comments = comments[0].json
            jsonR = json.loads(comments)
            jsonR = jsonR['comments']
            length = len(jsonR)
            if(length >= n):
                jsonR = jsonR[length-n:]
                return jsonify(jsonR), 200
            else:
                return jsonify(jsonR), 200
        else:
            return jsonify('no comments for the articleId and author given'), 404
    else:
        return jsonify('articleId was not found'), 404




if(__name__ == '__main__'):
    app.run(debug=True)
