import uuid, hashlib, sqlite3, logging

class db(object):
    '''Class for handling SQL DB
    The db object must be created first before it can be used, e.g.

        db_instance = db()
        # use db_instance object

    The supported methods include:
        - add_user()  -- adds a new user to the DB by providing a username and a password
        - auth_user() -- authenticates the user by providing a username and a password

    TODO:
        - add tests
        - accommodate it for RPC
    '''

    __PEPPER = 'PEPPER'

    __TABLE        = 'users'
    __COL_USERNAME = 'username'
    __COL_SALT     = 'salt'
    __COL_HASH     = 'hash'

    __OK                  = int(0x00)
    __ERR_DB_NOT_READY    = int(0x01 << 0)
    __ERR_USER_EXISTS     = int(0x01 << 1)
    __ERR_USER_NOT_EXIST  = int(0x01 << 2)
    __ERR_AUTH            = int(0x01 << 3)
    __ERR_SQL             = int(0x01 << 4)
    __ERR_UNKNOWN         = int(0x01 << 5)

    class error(Exception):
        pass

    def __init__(self, path):
        '''Initializes the database and creates a table which stores usernames and passwords,
           unless it's not existing already
        :param path: path to the database file
        '''
        self.path        = path
        self.pepper      = db.__PEPPER
        self.initialized = False

        con = None
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            cur.execute('CREATE TABLE IF NOT EXISTS {table_name}' \
                        '({col_username} TEXT PRIMARY KEY,'       \
                        ' {col_salt} TEXT,'                       \
                        ' {col_hash} TEXT)'.format(
                table_name   = db.__TABLE,
                col_username = db.__COL_USERNAME,
                col_salt     = db.__COL_SALT,
                col_hash     = db.__COL_HASH,
            ))
            self.initialized = True
        except sqlite3.Error as err:
            logging.error("SQL error: %s" % err)
        except BaseException as err:
            logging.error("Unknown error: %s" % err)
        finally:
            if con:
                con.close()

    def add_user(self, username, password):
        '''Adds a new user to the DB
        :param username: New username
        :param password: Password for the user
        :return: OK    if new user was added to the DB
                 ERR_* if there was an error
        '''
        if not self.initialized:
            return db.__ERR_DB_NOT_READY

        ret_code = db.__OK
        con = None
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()

            # first let's check if the username is already in the db
            cur.execute('SELECT * FROM {table_name} WHERE {col_username}=?'.format(
                    table_name   = db.__TABLE,
                    col_username = db.__COL_USERNAME,
                ),
                (username,)
            )
            rows = cur.fetchall()
            if rows:
                ret_code = db.__ERR_USER_EXISTS
                raise db.error("Username already exists in the DB")

            # now we're ready to create hash & salt for the guy
            salt = uuid.uuid4().hex
            hashed_password = hashlib.sha512(password + salt + self.pepper).hexdigest()

            cur.executemany('INSERT INTO {table_name} VALUES(?, ?, ?)'.format(table_name = db.__TABLE),
                            [(username, salt, hashed_password,),])
            con.commit()
        except sqlite3.Error as err:
            logging.error("SQL error: %s" % err)
            ret_code = db.__ERR_SQL
        except db.error as err:
            logging.error("DB error: %s" % err)
        except BaseException as err:
            logging.debug("Unknown error: %s" % err)
            ret_code = db.__ERR_UNKNOWN
        finally:
            if con:
                con.close()
        return ret_code

    def auth_user(self, username, password):
        '''Authenticates the user
        :param username: Username
        :param password: Password of the user
        :return: OK,    if authentication succeeded
                 ERR_*, if there was an error
        '''
        if not self.initialized:
            return db.__ERR_DB_NOT_READY

        ret_code = db.__OK
        con = None
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()

            # first let's check if the username is even in the db
            cur.execute('SELECT * FROM {table_name} WHERE {col_username}=?'.format(
                table_name   = db.__TABLE,
                col_username = db.__COL_USERNAME,
            ), (username,))
            rows = cur.fetchall()
            if not rows:
                ret_code = db.__ERR_USER_NOT_EXIST
                raise db.error("The user does not exist")

            # check if the provided password is valid
            _, salt, pwh = rows[0]
            hash_test = hashlib.sha512(password + salt + self.pepper).hexdigest()
            if hash_test != pwh:
                ret_code = db.__ERR_AUTH
                raise db.error("User authentication error")
        except sqlite3.Error as err:
            logging.error("SQL error: %s" % err)
            ret_code = db.__ERR_SQL
        except db.error as err:
            logging.error("DB error: %s" % err)
        except BaseException as err:
            logging.error("Unknown error: %s" % err)
            ret_code = db.__ERR_UNKNOWN
        finally:
            if con:
                con.close()
        return ret_code