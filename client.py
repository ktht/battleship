import pika, os, logging, sys, uuid, threading, time
logging.basicConfig()

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

connection2 = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel2 = connection2.channel()

global_bool = False

def listen_public_announcements():
    channel.exchange_declare(exchange='announcements',
                             type='fanout')
    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange='announcements',
                       queue=queue_name)
    channel.basic_consume(serv_announc_callback,
                          queue=queue_name,
                          no_ack=True)
    print(' [*] Announcements started listening. To exit press CTRL+C')
    channel.start_consuming()


def listen_server_bcasts():
    channel2.exchange_declare(exchange='server1_bcast',
                             type='fanout')

    result2 = channel2.queue_declare(exclusive=True)
    queue_name2 = result2.method.queue

    channel2.queue_bind(exchange='server1_bcast',
                       queue=queue_name2)
    channel2.basic_consume(callback,
                          queue=queue_name2,
                          no_ack=True)
    print(' [*] Broadcasts started listening. To exit press CTRL+C')
    channel2.start_consuming()


def serv_announc_callback(ch, method, properties, body):
    print(" [x] %r" % body)


def callback(ch, method, properties, body):
    global global_bool
    global_bool = True
    print(" [x] %r" % body)


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
    rpc_client = RpcClient()
    print("Testing rpc!")
    response = rpc_client.call(1)
    print("Got a response: %r" % response)


if __name__ == '__main__':
    threads = []
    t1 = threading.Thread(target=listen_server_bcasts, name='Listen_Server_Bcasts')
    t2 = threading.Thread(target=do_rpc, name='RPC_Handling')
    t3 = threading.Thread(target=listen_public_announcements, name='Listen_Public_Announc')
    threads.extend((t1, t2, t3))
    #t.setDaemon(True)
    t1.start()
    t3.start()

    while not global_bool:
        time.sleep(0.2)

    print('Got bool!')

    #t2.start()
    #t3.join()



























