import time, itertools, random, pika, threading, game
import numpy as np

is_running = True

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

channel.exchange_declare(exchange='server1_bcast',
                         type='fanout')
channel.exchange_declare(exchange='announcements',
                         type='fanout', arguments={'x-message-ttl' : 900})
channel.queue_declare(queue='rpc_queue')

def send_announcements():
    while is_running:
        time.sleep(1)
        channel.basic_publish(exchange='announcements',
                              routing_key='',
                              body="Sending server announcements!")


def send_broadcasts():
    while is_running:
        time.sleep(1)
        channel.basic_publish(exchange='server1_bcast',
                            routing_key='',
                            body="Sending server broadcast!")


def on_request(ch, method, props, body):
    n = int(body)

    if n == 1:
        # game.create_player('Peeter')
        # print(game.players[0].get_admin())
        print('Yay, it worked!!!')

    print("Body is: (%s)" % n)
    response = 125

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id= \
                                                         props.correlation_id),
                     body=str(response))
    ch.basic_ack(delivery_tag=method.delivery_tag)


def game_session():
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(on_request, queue='rpc_queue')
    print(" [x] Awaiting RPC requests")
    channel.start_consuming()




if __name__ == '__main__':
    game = game.BattleShips()

    print('New game created!')
    #channel.basic_qos(prefetch_count=1)
    #channel.basic_consume(on_request, queue='rpc_queue')

    #print(" [x] Awaiting RPC requests")
    #channel.start_consuming()

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


    #game.create_player('Karl')
    #game.create_player('Pepe')
    #game.create_player('Mohammad')
    #game.create_player('Pepe')
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

