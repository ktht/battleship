import pika, logging, uuid, threading, time, Queue, common, getpass, sys, select, string,  numpy as np

# Global constants -----------------------------------------------
GAME_SERVER_NAME = 'Server'

# Synchronization primitives -------------------------------------
global_bool = False
os_linux = True
initialization_phase = True
is_alive = True
queue = Queue.Queue()
cv = threading.Condition()
cv_init = threading.Condition()
start_t = 0
server_list_timeout = 6
client_name = ''

# Game-specific variables ----------------------------------------
available_servers  = []
player_ships_board = []
player_hits_board = []

# Indirect communication channels --------------------------------
server_list_con = pika.BlockingConnection(
    pika.ConnectionParameters(
        host = common.host,
        port = common.port,
        credentials = pika.PlainCredentials(
            username = common.mquser,
            password = common.mqpwd,
        ),
    )
)
server_bcasts_con = pika.BlockingConnection(
    pika.ConnectionParameters(
        host = common.host,
        port = common.port,
        credentials = pika.PlainCredentials(
            username = common.mquser,
            password = common.mqpwd,
        ),
    )
)
client_keepalive_con = pika.BlockingConnection(
    pika.ConnectionParameters(
        host = common.host,
        port = common.port,
        credentials = pika.PlainCredentials(
            username = common.mquser,
            password = common.mqpwd,
        ),
    )
)
server_list_ch      = server_list_con.channel()
server_bcasts_ch    = server_bcasts_con.channel()
client_keepalive_ch = client_keepalive_con.channel()

class TimedSet(set):
    '''Set class with timed autoremoving of elements
    Code taken from: http://stackoverflow.com/a/16137224

    Needed for maintaining available server list
    '''
    def __init__(self):
        self.__table = {}

    def add(self, item, timeout = 7):
        server_name, nof_clients = item.split(':')
        self.__table[server_name] = [nof_clients, time.time() + timeout]
        set.add(self, server_name)

    def __contains__(self, item):
        return time.time() < self.__table.get(item)[1]

    def __iter__(self):
        for item in set.__iter__(self):
            if time.time() < self.__table.get(item)[1]:
                yield (item, self.__table.get(item)[0])

def listen_public_announcements():
    server_list_ch.exchange_declare(
        exchange = 'announcements',
        type     = 'fanout'
    )
    result = server_list_ch.queue_declare(exclusive = True)
    queue_name = result.method.queue

    server_list_ch.queue_bind(
        exchange = 'announcements',
        queue    = queue_name
    )
    server_list_ch.basic_consume(
        public_announc_callback,
        queue  = queue_name,
        no_ack = True
    )

    global start_t
    global server_list_timeout
    print('Getting list of available servers, please wait...')
    print('If no servers are seen after %d seconds, then no server is available.' % server_list_timeout)
    start_t = time.time()
    server_list_ch.start_consuming()

def listen_server_bcasts():
    server_bcasts_ch.exchange_declare(
        exchange = GAME_SERVER_NAME,
        type     = 'fanout'
    )

    result2 = server_bcasts_ch.queue_declare(exclusive = True)
    queue_name2 = result2.method.queue

    server_bcasts_ch.queue_bind(
        exchange = GAME_SERVER_NAME,
        queue    = queue_name2
    )
    server_bcasts_ch.basic_consume(
        server_bcasts_callback,
        queue  = queue_name2,
        no_ack = True
    )
    server_bcasts_ch.start_consuming()

def send_keepalive():
    i = 0
    global global_bool
    global client_name
    global GAME_SERVER_NAME

    client_keepalive_ch.exchange_declare(
        exchange  = 'keepalive',
        type      = 'direct',
        arguments = { 'x-message-ttl': 5000 }
    )

    while not global_bool:
        i += 1
        time.sleep(5)
        msg = '{client_name}'.format(client_name = client_name)
        client_keepalive_ch.basic_publish(
            exchange    = 'keepalive',
            routing_key = '{server_name}_watchdog'.format(server_name = GAME_SERVER_NAME),
            body        = msg,
        )
        #logging.debug('Sent {keepalive_i}th keepalive message'.format(keepalive_i = i))
        print('Sent {keepalive_i}th keepalive message'.format(keepalive_i = i))

def public_announc_callback(ch, method, properties, body):
    t_set.add(body)

    global start_t
    global server_list_timeout
    global initialization_phase
    global available_servers

    if time.time() - start_t > server_list_timeout:
        start_t = time.time()
        if initialization_phase:
            common.clear_screen()
            print('Available servers and number of clients connected:')
        for t in t_set:
            if initialization_phase:
                print("{server_name}: {nof_clients} client(s)".format(
                    server_name = t[0],
                    nof_clients = t[1]
                ))
            available_servers.append(t[0])
        if initialization_phase:
            if common.query_yes_no("Would you like to update the list?", default = "no"):
                print('Updating...')
                return
            elif len(available_servers) > 0:
                initialization_phase = False
                cv_init.acquire()
                cv_init.notify_all()
                cv_init.release()

                # we must close the connection, see https://github.com/pika/pika/issues/698
                server_list_con.close()

def process_board(board, height, width):
    game_board = np.fromstring(board, dtype=int).reshape(height, width)
    game_board = game_board.astype(str)
    for index, x in np.ndenumerate(game_board):
        if not x.startswith(str(player_id)):
            game_board[index] = '.'
        else: game_board[index] = x[1:]
    return game_board

def get_coords():
    if os_linux:
        print "Enter the coords you want to hit! (ex a2) You have 25 seconds!:"
        i, o, e = select.select([sys.stdin], [], [], 25)
        if (i):
            coords =  sys.stdin.readline().strip()
        else: coords = None
    if coords == None:
        return common.CTRL_HIT_TIMEOUT, common.CTRL_HIT_TIMEOUT
    try:
        x = int(string.lowercase.index(coords[0].lower()))
        y = int(str(coords)[1:])-1
    except Exception:
        return common.CTRL_ERR_HIT, common.CTRL_ERR_HIT
    return x, y


def server_bcasts_callback(ch, method, properties, body):
    msg = common.unmarshal(body)
    CTRL_CODE = int(msg[0])
    if CTRL_CODE == common.CTRL_BRDCAST_MSG:
        print(msg[1])
    elif CTRL_CODE == common.CTRL_START_GAME:
        board = rpc_client.call_mum(common.CTRL_REQ_BOARD)
        global player_ships_board, player_hits_board
        player_ships_board = process_board(board[0], int(board[1]) ,int(board[2]))
        player_hits_board = np.full((int(board[1]), int(board[2])), '-', dtype=str)
        common.print_board(player_ships_board, player_hits_board)
    elif CTRL_CODE == common.CTRL_SIGNAL_PL_TURN:
        if int(msg[1]) == player_id:
            x, y = get_coords()
            if x != common.CTRL_HIT_TIMEOUT and y != common.CTRL_HIT_TIMEOUT: # In case of timeout not worth doing RPC
                hit = int(rpc_client.call_mum(common.CTRL_HIT_SHIP, player_id, x, y)[0])
                if int(hit) == common.CTRL_ERR_HIT:
                    print('Entered coordinates were invalid.')
                else:
                    if int(hit) == 0:
                        player_hits_board[x][y] = 'O'
                    else: player_hits_board[x][y] = 'X'
            common.clear_screen()
            common.print_board(player_ships_board, player_hits_board)
    elif CTRL_CODE == common.CTRL_NOTIFY_HIT:
        if int(msg[1]) == player_id: # Id of player who got hit
                player_ships_board[int(msg[2])][int(msg[3])] = '*'
                common.clear_screen()
                common.print_board(player_ships_board, player_hits_board)
                print('Oh noes, you\'ve been hit by {bomber}!'.format(bomber=str(msg[4])))

    else:
        cv.acquire()
        queue.put(body)
        cv.notify_all()
        cv.release()

class RpcClient(object):
    def __init__(self):
        self.rpc_con = pika.BlockingConnection(
            pika.ConnectionParameters(
                host = common.host,
                port = common.port,
                credentials = pika.PlainCredentials(
                    username = common.mquser,
                    password = common.mqpwd,
                ),
            )
        )
        self.rpc_ch         = self.rpc_con.channel()
        self.rpc_result     = self.rpc_ch.queue_declare(exclusive=True)
        self.callback_queue = self.rpc_result.method.queue

        self.rpc_ch.basic_consume(
            self.on_response,
            no_ack = True,
            queue  = self.callback_queue
        )

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, n):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.rpc_ch.basic_publish(
            exchange    = '',
            routing_key = 'rpc_queue',
            properties  = pika.BasicProperties(
                reply_to       = self.callback_queue,
                correlation_id = self.corr_id,
            ),
            body        = str(n)
        )
        while self.response is None:
            self.rpc_con.process_data_events()
        return self.response

    @common.marshal_decorator
    def call_mum(self, *args):
        return self.call(*args)

def authenticate():
    global available_servers, GAME_SERVER_NAME
    boolean = True
    while boolean:
        try:
            server_name = raw_input('Enter the name of the server you want to connect to: ')
        except KeyboardInterrupt:
            print("Bye bye")
            sys.exit(1)
        if server_name in available_servers:
            boolean = False
            del available_servers[:]
            break
        else:
            print("Incorrect server name")

    GAME_SERVER_NAME = server_name
    common.clear_screen()

    print('Connected to {game_server_name}'.format(game_server_name = GAME_SERVER_NAME))
    while not boolean:
        try:
            u_name = raw_input("Enter your username: ")
            #pwd    = getpass.getpass("Enter your password: ")
            pwd = raw_input("Enter your password: ")
            #player_id = int(rpc_client.call(common.marshal(common.CTRL_REQ_ID, u_name,pwd)))
        except KeyboardInterrupt:
            print("Bye bye")
            sys.exit(1)
        player_id = int(rpc_client.call_mum(common.CTRL_REQ_ID, u_name, pwd)[0])
        if player_id == common.CTRL_ERR_DB:
            print('This username is taken or you entered a wrong password, please try again.')
        elif player_id == common.CTRL_ERR_MAX_PL:
            print('Sorry, maximum number of players has been exceeded.')
        elif player_id == common.CTRL_ERR_LOGGED_IN:
            print('Sorry but this user is already logged in.')
        else:
            boolean = True
            common.clear_screen()

    global client_name
    client_name = u_name

    keepalive_thread = threading.Thread(
        target = send_keepalive,
        name   = 'Client_keepalive'
    )
    keepalive_thread.setDaemon(True)
    keepalive_thread.start()

    return u_name, player_id


if __name__ == '__main__':

    logging.basicConfig(
        level  = logging.CRITICAL,
        format = '[%(asctime)s] [%(threadName)s] [%(module)s:%(funcName)s:%(lineno)d] [%(levelname)s] -- %(message)s',
        stream = sys.stdout
    )

    rpc_client = RpcClient()
    t_set = TimedSet()

    game_board = []
    get_servers_list_th = threading.Thread(
        target = listen_public_announcements,
        name   = 'Listen_Public_Announc'
    )
    listen_server_bcasts_th = threading.Thread(
        target = listen_server_bcasts,
        name   = 'Listen_Server_Bcasts'
    )

    threads = [listen_server_bcasts_th, get_servers_list_th]
    for t in threads:
        t.setDaemon(True)

    cv_init.acquire()
    get_servers_list_th.start()
    try:
        while True:
            if initialization_phase:
                cv_init.wait(timeout = 10)
            else:
                break
    except KeyboardInterrupt:
        print "Bye bye"
        sys.exit(1)
    cv_init.release()

    u_name, player_id = authenticate()
    print('Hello, {username}! You have connected succesfully!'.format(username = u_name))

    listen_server_bcasts_th.start()

    try:
        if player_id == 1:  # Admin has player id 1
            game_not_started = True
            while game_not_started:
                if common.query_yes_no("Do you want to start the game?"):
                    #rpc_client.call(common.marshal(common.CTRL_START_GAME, player_id))
                    rpc_client.call_mum(common.CTRL_START_GAME, player_id)
                    game_not_started = False
    except KeyboardInterrupt:
        print("Bye bye")
        sys.exit(1)

    while not global_bool:
        time.sleep(0.2)

    listen_server_bcasts_th.join()
