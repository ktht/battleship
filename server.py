import time, itertools, random, pika, threading, game, common, db, Queue
import numpy as np

# Global constants ------------------------------------------------------------
SERVER_NAME = 'Server'

is_running = True
game_not_started = True
queue = Queue.Queue()
cv = threading.Condition()

announc_con = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
bcast_con = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
rpc_con = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
announc_ch = announc_con.channel()
bcast_ch = bcast_con.channel()
rpc_ch = rpc_con.channel()

bcast_ch.exchange_declare(exchange=SERVER_NAME,
                         type='fanout')
announc_ch.exchange_declare(exchange='announcements',
                         type='fanout', arguments={'x-message-ttl' : 5000})
rpc_ch.queue_declare(queue='rpc_queue')

def send_announcements():
    i = 0
    while is_running:
        i +=1
        time.sleep(5)
        msg = SERVER_NAME+':'+str(len(game.players))
        announc_ch.basic_publish(exchange='announcements',
                              routing_key='',
                              body=msg)

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
        bcast_ch.basic_publish(exchange=SERVER_NAME,
                            routing_key='',
                            body=msg)


def request_new_id(u_name, pwd):
    print("New player connecting!")
    for p in game.players: # Checks if this username has already logged on
        if p.get_name() == u_name:
            return common.CTRL_ERR_LOGGED_IN
    if db_instance.auth_user(u_name, pwd) == 0:  # If authentication was succesful
        return game.create_player(u_name)
    elif db_instance.add_user(u_name, pwd) == 0: # If succesfully created a new player
        return game.create_player(u_name)
    else:
        return common.CTRL_ERR_DB # Username is taken or entered password is wrong

def start_game(player_id):
    for player in game.players:
        if int(player.get_id()) == int(player_id) and player.get_admin():
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
        response = common.marshal(board_array.tostring(),board_shape[0],board_shape[1])
        #print(np.fromstring(f, dtype=int).reshape(board_shape))


    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id= \
                                                         props.correlation_id),
                     body=str(response))
    ch.basic_ack(delivery_tag=method.delivery_tag)


def game_session():

    rpc_ch.basic_qos(prefetch_count=1)
    rpc_ch.basic_consume(on_request, queue='rpc_queue')
    print(" [x] Awaiting RPC requests")
    rpc_ch.start_consuming()


if __name__ == '__main__':
    db_instance = db.db(common.DATABASE_FILE_NAME)
    game = game.BattleShips()

    print('New game created!')

    threads = []
    t1 = threading.Thread(target=game_session, name='Game_session_RPC')
    t2 = threading.Thread(target=send_announcements, name='Server_announcements')
    t3 = threading.Thread(target=send_broadcasts, name='Server_broadcasts')
    threads.extend((t1, t2, t3))

    #t.setDaemon(True)
    #t2.setDaemon(True)
    t1.start()
    t2.start()
    t3.start()

    while game_not_started:
        if len(game.players) != 0: # Not worth sending it, when no clients are connected
            for player in game.players:
                if player.get_admin():
                    name = player.get_name()
                    break
                else: name = 'None'
            cv.acquire()
            queue.put(common.marshal(common.CTRL_BRDCAST_MSG,"Game not started yet, "+
                                     str(len(game.players))+" client(s) connected, "+
                                     str(name)+" has rights to start the game."))
            cv.notify_all()
            cv.release()
            time.sleep(5)


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

