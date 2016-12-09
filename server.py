import time, pika, threading, game, common, Queue, logging, sys
from db import db

# Global constants ------------------------------------------------------------
SERVER_NAME = 'Server'

# Synchronization primitives --------------------------------------------------
is_running       = True
game_not_started = True
queue = Queue.Queue()
cv = threading.Condition()
l_adduser = threading.Lock()

# Indirect communication channels ---------------------------------------------
announc_con = pika.BlockingConnection(
    pika.ConnectionParameters(host = 'localhost')
)
bcast_con = pika.BlockingConnection(
    pika.ConnectionParameters(host = 'localhost')
)
rpc_con = pika.BlockingConnection(
    pika.ConnectionParameters(host = 'localhost')
)
announc_ch = announc_con.channel()
bcast_ch   = bcast_con.channel()
rpc_ch     = rpc_con.channel()

bcast_ch.exchange_declare(
    exchange = SERVER_NAME,
    type     = 'fanout'
)
announc_ch.exchange_declare(
    exchange  = 'announcements',
    type      = 'fanout',
    arguments = { 'x-message-ttl' : 5000 }
)
rpc_ch.queue_declare(queue='rpc_queue')

def send_announcements():
    i = 0
    while is_running:
        i +=1
        time.sleep(5)
        msg =  "{server_name}:{nof_players}".format(
            server_name = SERVER_NAME,
            nof_players = game.get_nof_players()
        )
        announc_ch.basic_publish(
            exchange    = 'announcements',
            routing_key = '',
            body        = msg
        )

def send_broadcasts():
    while is_running:
        cv.acquire()
        if queue.qsize() == 0:
            cv.wait()
        try:
            msg = queue.get(0)
        except Queue.Empty:
            pass
        cv.release()
        bcast_ch.basic_publish(
            exchange    = SERVER_NAME,
            routing_key = '',
            body        = msg
        )

@common.synchronized_g(l_adduser)
def request_new_id(u_name, pwd):
    '''Adds or creates a new user if it doesn't exist in the DB
    :param u_name: string, user name
    :param pwd:    string, password
    :return:       int, user ID (a number less than 10), or an error code (> 10)

    TODO: reconsider the return values
    '''
    logging.info("New player '%s' connected!" % u_name)

    # Checks if this username has already logged on
    if game.user_exists(u_name):
        logging.debug("User '%s' tried to log in second time" % u_name)
        return common.CTRL_ERR_LOGGED_IN

    # First try to authenticate
    valid_user = False
    auth_result = db_instance.auth_user(u_name, pwd)
    if auth_result == db_instance.ERR_USER_NOT_EXIST:
        # Note that external lock ensures that another user isn't being added to the DB in b/w
        logging.debug("User '%s' doesn't exist, creating a new one" % u_name)
        if db_instance.add_user(u_name, pwd) == db_instance.OK:
            # Create a new user if doesn't exist, and say the user is auth'ed
            logging.debug("User '%s' added to the DB" % u_name)
            valid_user = True
    elif auth_result == db_instance.OK:
        logging.debug("User '%s' authenticated successfully" % u_name)
        valid_user = True

    # i.e. if authentication was succesful or a new user was added
    if valid_user:
        player_id, retcode = game.create_player(u_name)
        logging.debug("A new player '%s' was added to the game" % u_name)
        if retcode == common.CTRL_OK:
            return player_id

    else:
        return common.CTRL_ERR_DB # Username is taken or entered password is wrong

def start_game(player_id):
    for player in game.players:
        if int(player.get_id()) == int(player_id) and player.is_admin():
            global board
            board = game.create_board()  # Creates and populates the board after admin starts the game
            game.populate_board(board)
            cv.acquire()
            queue.put(common.marshal(common.CTRL_START_GAME, common.CTRL_ALL_PLAYERS))
            cv.notify_all()
            cv.release()
            global game_not_started
            game_not_started = False # Stops server from sending broadcasts
            return common.CTRL_OK
    return common.CTRL_NOT_ADMIN

def on_request(ch, method, props, body):
    request = common.unmarshal(body)
    CTRL_CODE = int(request[0])

    if CTRL_CODE == common.CTRL_REQ_ID:
        response = request_new_id(request[1], request[2])
    elif CTRL_CODE == common.CTRL_START_GAME:
        response = start_game(request[1])
    elif CTRL_CODE == common.CTRL_REQ_BOARD:
        board_array = board.get_board()  # Array needed to send board to client
        board_shape = board_array.shape
        response = common.marshal(board_array.tostring(), board_shape[0], board_shape[1])
        #print(np.fromstring(f, dtype=int).reshape(board_shape))

    ch.basic_publish(
        exchange    = '',
        routing_key = props.reply_to,
        properties  = pika.BasicProperties(correlation_id = props.correlation_id),
        body        = str(response)
    )
    ch.basic_ack(delivery_tag = method.delivery_tag)


def game_session():

    rpc_ch.basic_qos(prefetch_count = 1)
    rpc_ch.basic_consume(on_request, queue = 'rpc_queue')
    try:
        logging.info("Awaiting RPC requests")
        rpc_ch.start_consuming()
    except KeyboardInterrupt:
        logging.info("Stopped waiting for RPC requests")
        rpc_ch.stop_consuming()

if __name__ == '__main__':
    logging.basicConfig(
        level  = logging.DEBUG,
        format = '[%(asctime)s] [%(threadName)s] [%(module)s:%(funcName)s:%(lineno)d] [%(levelname)s] -- %(message)s',
        stream = sys.stdout
    )

    db_instance = db(common.DATABASE_FILE_NAME)
    game = game.BattleShips()

    logging.info('A new game created!')

    thread_game_session         = threading.Thread(target = game_session,       name = 'Game_session_RPC')
    thread_server_announcements = threading.Thread(target = send_announcements, name = 'Server_announcements')
    thread_server_broadcast     = threading.Thread(target = send_broadcasts,    name = 'Server_broadcasts')
    threads = [thread_game_session, thread_server_announcements, thread_server_broadcast]
    for t in threads:
        t.setDaemon(True)
        t.start()
        logging.debug("Started thread '%s'" % t.getName())

    try:
        while game_not_started:
            logging.debug("Entered loop")
            game.cv_create_player.acquire()
            if game.get_nof_players() == 0: # Not worth sending it, when no clients are connected
                logging.debug("Waiting a player to join")
                game.cv_create_player.wait(timeout = 5)
            game.cv_create_player.release()
            if game.get_nof_players() == 0: continue

            cv.acquire()
            queue.put(common.marshal(
                common.CTRL_BRDCAST_MSG,
                "Game not started yet, {nof_clients} client(s) connected, {admin} has rights to start the game.".format(
                    nof_clients = game.get_nof_players(),
                    admin       = game.get_admin()
                )))
            cv.notify_all()
            cv.release()
    except KeyboardInterrupt:
        is_running = False
        logging.debug("Bye bye")
    logging.debug("Exiting initial loop")

    #board = game.create_board()

    #game.populate_board(board)
    #board.print_board()

    #t.join()

    #board_array = board.get_board() # Stuff for sending the board to client
    #board_shape = board_array.shape
    #f = board_array.tostring()
    #print(np.fromstring(f, dtype=int).reshape(board_shape))
    # system('cls' if name == 'nt' else 'clear')

    #print(board_array.shape)
    #board.print_board()
