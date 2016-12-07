import pika, os, logging, sys, uuid, threading, time, Queue
from os import system, name
logging.basicConfig()

GAME_SERVER_NAME = 'Server'

global_bool = False
initialization_phase = True
is_alive = True
counter = 0
queue = Queue.Queue()
cv = threading.Condition()

def testing():
    connection.add_timeout(5, testing)
#    print('Timeout thingyu')

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
connection.add_timeout(5, testing)
channel = connection.channel()


connection2 = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel2 = connection2.channel()

def setup():
    channel.exchange_declare(exchange='announcements',
                             type='fanout')
    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange='announcements',
                       queue=queue_name)
    channel.basic_consume(public_announc_callback,
                          queue=queue_name,
                          no_ack=True)




class TimedSet(set): # http://stackoverflow.com/questions/16136979/set-class-with-timed-auto-remove-of-elements
    def __init__(self): # For maintaining available server list
        self.__table = {}
    def add(self, item, timeout=5):
        self.__table[item] = time.time() + timeout
        set.add(self, item)
    def __contains__(self, item):
        return time.time() < self.__table.get(item)
    def __iter__(self):
        for item in set.__iter__(self):
            if time.time() < self.__table.get(item):
                yield item


def listen_public_announcements():
    #while is_alive:
    #print(' [*] Announcements started listening. To exit press CTRL+C')
    print('Getting list of available servers, please wait...')
    print('If no servers are seen after 10 seconds, then no server is available.')
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    #channel.start_consuming()


def listen_server_bcasts():
    server_name = raw_input('\nEnter the name of the server you want to connect to: \n')


    # TODO check if this name matches any names in the set
    channel2.exchange_declare(exchange=server_name,
                              type='fanout')

    result2 = channel2.queue_declare(exclusive=True)
    queue_name2 = result2.method.queue

    channel2.queue_bind(exchange=server_name,
                        queue=queue_name2)
    channel2.basic_consume(server_bcasts_callback,
                           queue=queue_name2,
                           no_ack=True)
    system('cls' if name == 'nt' else 'clear')
    print(' [*] Broadcasts started listening. To exit press CTRL+C')

    try:
        channel2.start_consuming()
    except KeyboardInterrupt:
        channel2.stop_consuming()
    #channel2.start_consuming()


def public_announc_callback(ch, method, properties, body):
    t_set.add(body)
    global initialization_phase
    if initialization_phase:
        global counter
        counter += 1
        if counter >= 2:
            counter = 0
            initialization_phase = False
            system('cls' if name == 'nt' else 'clear')
            print('Available servers and number of clients connected:')
            for t in t_set:
                print(t)
            x = raw_input('\nWould you like to update the list? (y/n) \n')
            if x == 'y':
                print('Updating...')
                initialization_phase = True
            else:
                connection.close()

def server_bcasts_callback(ch, method, properties, body):
    cv.acquire()
    queue.put(body)
    cv.notify_all()
    cv.release()

    #print(" [x] %r" % body)


class RpcClient(object):
    def __init__(self):
        #self.connection = pika.BlockingConnection(pika.ConnectionParameters(
        #        host='localhost'))

        #self.channel = self.connection.channel()

        result = channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue

        channel.basic_consume(self.on_response, no_ack=True,
                                   queue=self.callback_queue)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, n):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        channel.basic_publish(exchange='',
                                   routing_key='rpc_queue',
                                   properties=pika.BasicProperties(
                                         reply_to = self.callback_queue,
                                         correlation_id = self.corr_id,
                                         ),
                                   body=str(n))
        while self.response is None:
            connection.process_data_events()
        return int(self.response)


def do_rpc():
    while is_alive:
        cv.acquire()
        if queue.qsize() == 0:
            cv.wait()
        try:
            msg = queue.get(0)
            print("This got put into the queue: " + str(msg))

        except Queue.Empty:
            pass
        cv.release()


#    while(is_alive):
#        cv.acquire()
#        if queue_send2srvr.qsize() == 0:
#            cv.wait()
    #response = rpc_client.call(1)
    #print("Got a response: %r" % response)


if __name__ == '__main__':
    rpc_client = RpcClient()
    t_set = TimedSet()
    setup()

    threads = []
    get_servers_list = threading.Thread(target=listen_public_announcements, name='Listen_Public_Announc')
    t1 = threading.Thread(target=listen_server_bcasts, name='Listen_Server_Bcasts')
    t2 = threading.Thread(target=do_rpc, name='RPC_Handling')

    threads.extend((t1, t2, get_servers_list))

    get_servers_list.setDaemon(True)
    get_servers_list.start()
    get_servers_list.join()

    t1.setDaemon(True)
    t2.setDaemon(True)
    t2.start()
    t1.start()
    while not global_bool:
        time.sleep(0.2)
    print('Exited while loop')
    t1.join()
    t2.join()

    #print('\n t3 started')


    #print('Got bool!')

    #t3.join()

    #is_alive = False

    #t2.start()
    #t3.join()

