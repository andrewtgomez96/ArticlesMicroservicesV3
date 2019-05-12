
def init_db(cassandra):
    session = cassandra.connect()

    cql = '''DROP KEYSPACE db'''
    r = session.execute(cql)
    cql = '''CREATE KEYSPACE db
            WITH replication = {
            'class': 'SimpleStrategy',
            'replication_factor' : 1};'''
    r = session.execute(cql)
    session.set_keyspace("db")
    cql = '''CREATE TABLE User(
                username text PRIMARY KEY,
                password text);'''
    r = session.execute(cql)
    #possibly make primarykey(username, createdArt)
    cql = '''CREATE TABLE Blog(
                articleId uuid,
                username text,
                title text,
                body text,
                createdArt timestamp,
                tags set<text>,
                comments list<frozen<map<text,text>>>,
                PRIMARY KEY(username, createdArt)
                )WITH CLUSTERING ORDER BY (createdArt DESC);
                '''
    r = session.execute(cql)
    #timestampo for actual now toTimestamp(now())
    ps = '''BEGIN BATCH
            INSERT INTO Blog(articleId, username, title, body, createdArt, tags, comments)
            VALUES(uuid(), 'andoop', 'article1', 'this is a cool article', '2014-09-19 11:35:20', {'me', 'cooltag'},
                [
                    {
                        'username': 'andoop2',
                        'comment': 'this is a dumb comment'
                    }
                ]);
            INSERT INTO User(username, password) VALUES('andoop', 'password');
            INSERT INTO User(username, password) VALUES('andoop2', 'password2');
            INSERT INTO User(username, password) VALUES('andoop3', 'password3');
            APPLY BATCH''';
    session.execute(ps);
    cql = '''CREATE INDEX ON Blog (title);'''
    session.execute(cql)
    cql = '''CREATE INDEX ON Blog (articleId);'''
    session.execute(cql)
    #cql = '''CREATE INDEX ON Blog (tags);'''
    #session.execute(cql)
    #cql = '''CREATE INDEX ON Blog (comments);'''
    #session.execute(cql)
    cql = "SELECT * FROM Blog"
    r = session.execute(cql)
    return(r[0])
