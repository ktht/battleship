import time, itertools, random, pika
from os import system, name
from string import ascii_uppercase
import numpy as np

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))

channel = connection.channel()

channel.queue_declare(queue='rpc_queue')

# Global Constants  -------------------------------------------------------------------
BOARD_WIDTH = 10
BOARD_HEIGHT = 10

NO_SHIPS_MARK = 0
CARRIER_MARK = 5
BATTLESHIP_MARK = 4
CRUISER_MARK = 3
SUBMARINE_MARK = 6
DESTROYER_MARK = 2

ships = {"Carrier": [5, CARRIER_MARK],
             "Battleship": [4, BATTLESHIP_MARK],
             "Cruiser": [3, CRUISER_MARK],
             "Submarine": [3, SUBMARINE_MARK],
             "Destroyer": [2, DESTROYER_MARK]}

class BattleShips(object):
    players = []

    def __init__(self):
        print('Yellow!')


        #self.board = Board('0') # Board to print out
        #self.create_player("Guy")
        #self.main_board = self.create_board(NO_SHIPS_MARK)
        #firstpl = self.players[0]

        #self.populate_board()

        #self.main_board.print_board()
        #try:
        #    firstpl.board_ships.ship_placement(ships['Submarine'],1,1,'h')
        #    firstpl.board_ships.ship_placement(ships['Carrier'], 9, 9, 'v')

        #self.main_board.ship_placement(ships['Carrier'], firstpl.id)

        #except IndexError as err:
        #    print(err)

        #for ship, val1 in ships_dict.iteritems():
        #    print(ship, val1)
        #f = array.tostring()
        #np.fromstring(f, dtype=int).reshape(4,4)

        #system('cls' if name == 'nt' else 'clear')


    def create_player(self, name):
        if len(self.players) < 10:
            self.players.append(Player(name))
        else:
            print("Maximum number of players exceeded!")

    def create_board(self):
        global BOARD_HEIGHT, BOARD_WIDTH
        BOARD_HEIGHT = int(np.rint(np.sqrt(40*len(self.players))))
        BOARD_WIDTH = BOARD_HEIGHT + 1
        return Board(NO_SHIPS_MARK)

    def populate_board(self, board):
        for player in self.players:
            for ship in ships:
                board.bool = False
                while not board.bool:
                    board.ship_placement(ships[ship], player.id)



class Player(object):
    newid = itertools.count().next
    def __init__(self, name):
        self.name = name
        self.id = Player.newid()+1 # Gives incremental new ID to every new player
        if self.id == 1:
            self.is_admin = True
        else:
            self.is_admin = False
        #self.board_ships = Board(NO_SHIPS_MARK) # Board holding players personal ship locations
        #self.board_myhits = Board(NO_SHIPS_MARK) # Board showing the hits made to other players

    def get_admin(self):
        return self.is_admin

    def set_admin(self, bool):
        self.is_admin = bool


    # TODO: Save the name and check wether it is already taken

class Board(object):
    def __init__(self, mark):
        self.bool = False
        self.board = self.create_board(mark, BOARD_WIDTH, BOARD_HEIGHT)
        self.score = {CARRIER_MARK:0,BATTLESHIP_MARK:0,CRUISER_MARK:0,SUBMARINE_MARK:0,DESTROYER_MARK:0}

    def create_board(self, mark, w, h):
        if type(mark) is str:
            board = np.full((h, w), mark, dtype=str)
        else:
            board = np.full((h, w), mark, dtype=int)
        return board

    def print_board(self):
        print('      '+' '.join('%-3s' % i for i in range(1, BOARD_WIDTH + 1))) # Column numbering
        print('   '+'-'*4*BOARD_WIDTH) # Line between board and colum  numbers
        for row_label, row in zip(ascii_uppercase[:BOARD_HEIGHT], self.board): # Board with row numbering
            print '%-3s|  %s' % (row_label, ' '.join('%-3s' % i for i in row))

    def ship_placement(self, ship, id):
        v_or_h = random.randint(0,1)
        row = random.randint(1, BOARD_HEIGHT)
        column = random.randint(1, BOARD_WIDTH)
        if v_or_h == 1:
            sublist = self.board[:,column-1][row-1:(row+ship[0]-1)]
            if not all(v == 0 for v in sublist): # Checks overlap with other ships
                self.bool = False
                return
            if len(sublist) >= ship[0]: # Checks if ship would go out of boundaries
                self.board[:, column - 1][row - 1:(row + ship[0] - 1)] = ship[1]+10*id
                self.bool = True
            else:
                return False
        else:
            sublist = self.board[row-1][column-1:(column+ship[0]-1)]
            if not all(v == 0 for v in sublist): # Checks overlap with other ships
                self.bool = False
                return
            if len(sublist) >= ship[0]: # Checks if ship would go out of boundaries
                self.board[row - 1][column - 1:(column + ship[0] - 1)] = ship[1]+10*id
                self.bool = True
            else:
                self.bool = False


    def hit_ship(self, row, column):
        value = self.board[row-1][column-1]
        if value < 99:
            #if value != 0:
                #self.score[value] += 100
            value += 100 # Adds 10 to the field value when it has been hit for the first time
            self.board[row - 1][column - 1] = value
        return value - 100 # Returns the unmodified field value

    def get_board(self):
        return self.board

class Score(object):
    pass


def on_request(ch, method, props, body):
    n = int(body)

    if n == 1:
        game.create_player('Peeter')
        print(game.players[0].get_admin())


    print("Body is: (%s)" % n)
    response = 125

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=str(response))
    ch.basic_ack(delivery_tag = method.delivery_tag)


if __name__ == '__main__':
    game = BattleShips()

    print('New game created!')
    #channel.basic_qos(prefetch_count=1)
    #channel.basic_consume(on_request, queue='rpc_queue')

    print(" [x] Awaiting RPC requests")
    #channel.start_consuming()

    game.create_player('Karl')
    game.create_player('Pepe')
    game.create_player('Mohammad')
    game.create_player('Pepe')
    board = game.create_board()

    game.populate_board(board)
    board.print_board()

    #board_array = board.get_board() # Stuff for sending the board to client
    #board_shape = board_array.shape
    #f = board_array.tostring()
    #print(np.fromstring(f, dtype=int).reshape(board_shape))

    #print(board_array.shape)
    #board.print_board()

