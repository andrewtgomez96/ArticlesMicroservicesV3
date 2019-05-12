#user
#1 create a new user
#2 delete an existing user
#3 update existing user's password

from init_db import init_db
from flask import Flask, current_app, request, jsonify
import click
import json
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

# basic auth subclass checks database
def checkAuth(username, password):
    session = cassandra.connect()
    session.set_keyspace("db")
    pw_hash = session.execute("SELECT password FROM User WHERE username = %s", (username,))
    if(pw_hash and bcrypt.check_password_hash(pw_hash[0].password, password) == True):
        return True
    else:
        return False

bcrypt = Bcrypt(app) #added
BasicAuth(app)
cassandra = CassandraCluster()
app.config['CASSANDRA_NODES'] = ['172.17.0.2']  # can be a string or list of nodes


#1 create a new user
@app.route("/user/new", methods=['POST'])
def newUser():
    session = cassandra.connect()
    session.set_keyspace("db")
    username = request.form.get('username')
    password = request.form.get('password')
    #hash password
    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    insertUser = (username, pw_hash)
    session.execute("INSERT INTO User (username, password) VALUES (%s, %s)", insertUser)
    #cur.execute("INSERT INTO User (userName, password) VALUES (?, ?)", (insertUser))
    #db.connection.commit()
    return jsonify({'Successfully created user' : username}), 201

#2 auth route endpoint for all microservices on Nginx
@app.route("/user/auth", methods=['GET'])
def authUser():
    #cur = db.connection.cursor()
    if (request.authorization):
        username = request.authorization.username
        password = request.authorization.password
    else:
        return jsonify('Unauthorized response'), 401
    #authenticate
    if(checkAuth(username, password) == True):
        return jsonify('Successful authentication'), 200
    #invalid credentials, return 409
    else:
        return jsonify('Credentials not found'), 409

#2 delete existing user
@app.route("/user", methods=['DELETE'])
def deleteUser():
    session = cassandra.connect()
    session.set_keyspace("db")
    if (request.authorization):
        username = request.authorization.username
        password = request.authorization.password
    else:
        return jsonify('Unauthorized response'), 401
    #authenticate
    if(checkAuth(username, password) == True):
        #delete user
        session.execute("DELETE FROM User WHERE username = %s", (username,))
        return jsonify('Successfully deleted user'), 200
    #invalid credentials, return 409
    else:
        return jsonify('Credentials not found'), 409

#3 change existing user's password upsert instead of update
@app.route("/user/edit", methods=['PATCH'])
def editUser():
    session = cassandra.connect()
    session.set_keyspace("db")
    newPassword = request.form.get('password')
    if (request.authorization):
        username = request.authorization.username
        password = request.authorization.password
    else:
        return jsonify('Unauthorized response'), 401
    #authenticate
    if(checkAuth(username, password) == True):
        #set new password
        pw_hash = bcrypt.generate_password_hash(newPassword).decode('utf-8')
        insertUser = (username, pw_hash)
        session.execute("INSERT INTO User (username, password) VALUES (%s, %s)", insertUser)
        return jsonify('Successfully updated user password'), 200
    else:
        return jsonify('Credentials not found'), 409

if(__name__ == '__main__'):
    app.run(debug=True)
