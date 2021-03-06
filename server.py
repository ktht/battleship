import time, pika, threading, game, common, Queue, logging, sys
from db import db
from argparse import ArgumentParser

# Global constants ------------------------------------------------------------
___DEFAULT_SERVER_NAME = 'Server'
___NAME = 'Battheships Game Server'
___VER = '0.0.0.1'
start_t = 0
client_watchdog_timeout = 10
is_running             = True
game_not_started       = True
game_not_finished      = True
player_has_hit         = False
entered_correct_coords = False
stop_loop              = False

# Synchronization primitives --------------------------------------------------
queue = Queue.Queue()
cv = threading.Condition()
l_adduser = threading.Lock()

# Private methods -------------------------------------------------------------
def __info():
    return '%s version %s' % (___NAME, ___VER)

# Parsing arguments -----------------------------------------------------------
parser = ArgumentParser(description=__info(),
                        version=___VER)
parser.add_argument('-s', '--serv', type=str, \
                    help='Server name, ' \
                         'defaults to %s' % ___DEFAULT_SERVER_NAME, \
                    default=___DEFAULT_SERVER_NAME)
args = parser.parse_args()
SERVER_NAME = (args.serv)

# Game-specific variables -----------------------------------------------------
board = []
inactive_clients = []

# Indirect communication channels ---------------------------------------------
announc_con = pika.BlockingConnection(
    pika.ConnectionParameters(
        virtual_host = common.vhost,
        host = common.host,
        port = common.port,
        heartbeat_interval=common.hb_interval,
        credentials = pika.PlainCredentials(
            username = common.mquser,
            password = common.mqpwd,
        ),
    )
)
bcast_con = pika.BlockingConnection(
    pika.ConnectionParameters(
        virtual_host = common.vhost,
        host = common.host,
        port = common.port,
        heartbeat_interval=common.hb_interval,
        credentials = pika.PlainCredentials(
            username = common.mquser,
            password = common.mqpwd,
        ),
    )
)
rpc_con = pika.BlockingConnection(
    pika.ConnectionParameters(
        virtual_host = common.vhost,
        host = common.host,
        port = common.port,
        heartbeat_interval=common.hb_interval,
        credentials = pika.PlainCredentials(
            username = common.mquser,
            password = common.mqpwd,
        ),
    )
)
watchdog_con = pika.BlockingConnection(
    pika.ConnectionParameters(
        virtual_host = common.vhost,
        host = common.host,
        port = common.port,
        heartbeat_interval=common.hb_interval,
        credentials = pika.PlainCredentials(
            username = common.mquser,
            password = common.mqpwd,
        ),
    )
)

announc_ch  = announc_con.channel()
bcast_ch    = bcast_con.channel()
rpc_ch      = rpc_con.channel()
watchdog_ch = watchdog_con.channel()

bcast_ch.exchange_declare(
    exchange = SERVER_NAME,
    type     = 'fanout'
)
announc_ch.exchange_declare(
    exchange  = 'announcements',
    type      = 'fanout',
    arguments = { 'x-message-ttl' : 5000 }
)
rpc_ch.queue_declare(queue = '{server_name}_rpc_queue'.format(server_name=SERVER_NAME))

class TimedSet(set):
    '''Set class with timed autoremoving of elements
    Code taken from: http://stackoverflow.com/a/16137224

    Needed for maintaining available clients list
    '''
    def __init__(self):
        self.__table = {}

    def add(self, item, timeout = 7):
        self.__table[item] = time.time() + timeout
        set.add(self, item)

    def __contains__(self, item):
        return time.time() < self.__table.get(item)

    def __iter__(self):
        for item in set.__iter__(self):
            if time.time() < self.__table.get(item):
                yield item

def send_announcements():
    ''' Sends server information to "announcements" exchange for players to see. '''
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
        logging.debug('Sent {announce_it}th announcement'.format(announce_it = i))

def send_broadcasts():
    ''' Broadcasts game info to all subscribed players. '''
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

def client_watchdog():
    ''' Receives keepalive messages from players. '''
    watchdog_ch.exchange_declare(
        exchange = 'keepalive',
        type     = 'direct',
    )
    result     = watchdog_ch.queue_declare(exclusive = True)
    queue_name = result.method.queue

    watchdog_ch.queue_bind(
        exchange    = 'keepalive',
        queue       = queue_name,
        routing_key = '{server_name}_watchdog'.format(server_name = SERVER_NAME),
    )
    watchdog_ch.basic_consume(
        watchdog_callback,
        queue  = queue_name,
        no_ack = True,
    )

    global start_t
    start_t = time.time()
    watchdog_ch.start_consuming()

def watchdog_callback(ch, method, properties, body):
    # we expect client ID aka an integer here
    active_clients.add(int(body))
    logging.debug('Received watchdog message')

    global start_t
    global inactive_clients

    if time.time() - start_t > client_watchdog_timeout:
        start_t = time.time()
        # let's check how many clients are actually active
        #inactive_clients = [x for x in game.players if x.get_id() not in active_clients]

        active_client_ids = [x for x in active_clients]
        inactive_client_ids = list(set([x.get_id() for x in game.players]) - set(active_client_ids))
        inactive_clients = [x for x in game.players if x.get_id() in inactive_client_ids]

        #print 'game player IDs', [x.get_id() for x in game.players]
        #print 'active client IDs', active_client_ids
        #print 'inactive client IDs', inactive_client_ids

        if len(inactive_clients) > 0:
            logging.debug('{nof_players} player(s) have left the game: {player_list}'.format(
                nof_players = len(inactive_clients),
                player_list = ', '.join([x.get_name() for x in inactive_clients]),
            ))
        #TODO: do something with the list of inactive players

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
        global game_not_started
        player_id, retcode = game.create_player(u_name)
        logging.debug("A new player '%s' was added to the game" % u_name)
        if retcode == common.CTRL_OK:
            if not game_not_started: # When game has already started
                game.players[int(player_id) - 1].set_lost()
                return common.CTRL_GAME_STARTED
            return player_id

    else:
        return common.CTRL_ERR_DB # Username is taken or entered password is wrong

def check_win():
    ''' Checks if any player has lost and if there is final a winner '''
    counter = 0
    for key, value in board.score.iteritems():
        if int(value) == game.ships_tot:
            counter += 1
            if not game.players[int(key)-1].get_lost():
                game.players[int(key)-1].set_lost()
        if counter == len(game.players)-1:
            global game_not_finished
            game_not_finished = False

def start_game(player_id):
    ''' Creates the battleship game board and notifies all players to request
     newly created board.
    :param player_id: id of the player trying to start the game
    :return: OK if player is admin
             NOT_ADMIN if player is not admin
    '''
    for player in game.players:
        if int(player.get_id()) == int(player_id) and player.is_admin():
            global board
            board = game.create_and_populate_board()  # Creates and populates the board after admin starts the game
            cv.acquire()
            queue.put(common.marshal(common.CTRL_START_GAME, common.CTRL_ALL_PLAYERS))
            cv.notify_all()
            cv.release()
            global game_not_started
            game_not_started = False # Stops server from sending broadcasts
            return common.CTRL_OK
    return common.CTRL_NOT_ADMIN

def inform_other_clients(x, y, sufferer_id, bomber_id):
    ''' Sends info of the hit to other players with the name of bomber
    :param x: x-coordinate of the hit
    :param y: y-coordinate of the hit
    :param sufferer_id: id of the player who got hit
    :param bomber_id: id of the player who made the hit
    '''
    bomber_name = game.players[int(bomber_id)-1].get_name()
    cv.acquire()
    queue.put(common.marshal(common.CTRL_NOTIFY_HIT, sufferer_id, x, y, bomber_name))
    cv.notify_all()
    cv.release()

def inform_sunken_ship(pl_id, ship_id):
    '''Informs other players when a ship has been sunken
    :param pl_id: id of the player whose ship got sunken
    :param ship_id: id of the ships that has been sunken
    '''
    for index in game.players[int(pl_id)-1].ships_dict[str(ship_id)]:
        cv.acquire()
        queue.put(common.marshal(common.CTRL_SHIP_SUNKEN, index[0], index[1], pl_id))
        cv.notify_all()
        cv.release()

def on_request(ch, method, props, body):
    ''' Responds to rpc calls, (receives requests from players and responds to them)
    :param ch:
    :param method:
    :param props:
    :param body: body of the rpc call that a player has made
    '''
    request = common.unmarshal(body)
    CTRL_CODE = int(request[0])

    if CTRL_CODE == common.CTRL_REQ_ID:
        response = request_new_id(request[1], request[2])
    elif CTRL_CODE == common.CTRL_CHECK_ADMIN:
        if game.players[int(request[1])-1].is_admin():
            response = 1
        else: response = 0
    elif CTRL_CODE == common.CTRL_START_GAME:
        response = start_game(request[1])
    elif CTRL_CODE == common.CTRL_REQ_BOARD:
        board_array = board.get_board()  # Array needed to send board to a client
        board_shape = board_array.shape
        #time.sleep(0.2)
        board_str = board_array.tostring()
        response = common.marshal(board_str, board_shape[0], board_shape[1])
    elif CTRL_CODE == common.CTRL_HIT_SHIP:
        global entered_correct_coords, stop_loop, player_has_hit
        entered_correct_coords = False
        if int(request[2]) == common.CTRL_ERR_HIT or int(request[3]) == common.CTRL_ERR_HIT:
            response = common.CTRL_ERR_HIT
            stop_loop = True
        else:
            try:
                value = board.get_value(int(request[2]), int(request[3]))
                if int(value) < 100 and int(value) > 0:  # If that coordinate has not been hit before
                    pl_id = str(value)[0]
                    ship_id = str(value)[1]
                    if int(pl_id) != int(request[1]):  # If player did not hit his own ship
                        game.players[int(pl_id) - 1].ships_dmg[ship_id] += 1  # Records the hit
                        # If ship sunk
                        if int(game.players[int(pl_id) - 1].ships_dmg[ship_id]) == int(game.ships_l[ship_id]):
                            inform_sunken_ship(pl_id, ship_id)
                response, suffer_id = board.hit_ship(int(request[2]), int(request[3]), int(request[1]))
                entered_correct_coords = True
                check_win()
                if int(response) == 1: # In case someone got hit, let him know
                    inform_other_clients(request[2], request[3], suffer_id, request[1])
            except Exception as err:
                logging.info(err)
                response = common.CTRL_ERR_HIT
            player_has_hit = True

    ch.basic_publish(
        exchange    = '',
        routing_key = props.reply_to,
        properties  = pika.BasicProperties(correlation_id = props.correlation_id),
        body        = str(response)
    )
    ch.basic_ack(delivery_tag = method.delivery_tag)


def game_session():
    ''' Starts consuming rpc calls from all players. '''
    rpc_ch.basic_qos(prefetch_count = 1)
    rpc_ch.basic_consume(on_request, queue = '{server_name}_rpc_queue'.format(server_name=SERVER_NAME))
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

    active_clients = TimedSet()

    db_instance = db(common.DATABASE_FILE_NAME)
    game = game.BattleShips()

    logging.info('A new game created!')

    thread_game_session         = threading.Thread(target = game_session,       name = 'Game_session_RPC')
    thread_server_announcements = threading.Thread(target = send_announcements, name = 'Server_announcements')
    thread_server_broadcast     = threading.Thread(target = send_broadcasts,    name = 'Server_broadcasts')
    thread_client_watchdog      = threading.Thread(target = client_watchdog,    name = 'Client_watchdog')
    threads = [thread_game_session, thread_server_announcements, thread_server_broadcast, thread_client_watchdog]
    for t in threads:
        t.setDaemon(True)
        t.start()
        logging.debug("Started thread '%s'" % t.getName())

    try:
        while game_not_started: # Sends game info (n.o players connected and admin username to all who
            # are connected to the server.
            logging.debug("Entered loop")
            game.cv_create_player.acquire()
            if game.get_nof_players() == 0: # Not worth sending it, when no clients are connected
                logging.debug("Waiting a player to join")
                game.cv_create_player.wait(timeout = 5)
            game.cv_create_player.release()

            if game.get_nof_players() == 0:
                continue
            else:
                time.sleep(5)

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
        bcast_con.close()
        announc_con.close()
        rpc_con.close()
        watchdog_con.close()
        is_running = False
        game_not_finished = False
        logging.debug("Bye bye")
    logging.debug("Exiting initial loop")

    try:
        while game_not_finished: # Main game loop, where players are given turns to play
            for player in game.players:
                if player.get_lost() == False:
                    entered_correct_coords = False
                    while not entered_correct_coords:
                        stop_loop = False
                        cv.acquire()
                        queue.put(common.marshal(common.CTRL_SIGNAL_PL_TURN, player.get_id()))
                        cv.notify_all()
                        cv.release()
                        start = time.time()
                        while not player_has_hit and time.time()-start<30 and not stop_loop:
                            time.sleep(0.5)
                            if time.time()-start>30:
                                entered_correct_coords = True
                        player_has_hit = False
                        stop_loop = False
    except KeyboardInterrupt:
        is_running = False
        bcast_con.close()
        announc_con.close()
        rpc_con.close()
        watchdog_con.close()

    if is_running:
        winner = game.get_winner()
        logging.debug("Winner is {winner}!".format(winner=winner[0].get_name()))
        cv.acquire()
        queue.put(common.marshal(common.CTRL_GAME_FINISHED, winner[0].get_id(), winner[0].get_name()))
        cv.notify_all()
        cv.release()

    while is_running: # Keeps server running after game is finished
        time.sleep(0.5)

