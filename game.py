import itertools, random, threading, common, logging
from string import ascii_uppercase
import numpy as np


# Global Constants  -------------------------------------------------------------------
BOARD_WIDTH  = 10
BOARD_HEIGHT = 10

NO_SHIPS_MARK   = 0
CARRIER_MARK    = 5
BATTLESHIP_MARK = 4
CRUISER_MARK    = 3
SUBMARINE_MARK  = 6
DESTROYER_MARK  = 2

ships = {
    "Carrier"    : [ 5, CARRIER_MARK    ],
    "Battleship" : [ 4, BATTLESHIP_MARK ],
    "Cruiser"    : [ 3, CRUISER_MARK    ],
    "Submarine"  : [ 3, SUBMARINE_MARK  ],
    "Destroyer"  : [ 2, DESTROYER_MARK  ]
}

class BattleShips(object):

    def __init__(self):
        self.players = []
        self.cv_create_player = threading.Condition()

    def create_player(self, name):
        if len(self.players) < 10:
            self.cv_create_player.acquire()
            self.new_player = Player(name)
            self.players.append(self.new_player)
            if len(self.players) == 1:
                self.cv_create_player.notify_all()
            self.cv_create_player.release()
        else:
            return -1, common.CTRL_ERR_MAX_PL
        return self.new_player.get_id(), common.CTRL_OK

    def create_and_populate_board(self):
        global BOARD_HEIGHT, BOARD_WIDTH
        BOARD_HEIGHT = int(np.rint(np.sqrt(40*len(self.players))))
        BOARD_WIDTH = BOARD_HEIGHT + 1
        board =  Board(NO_SHIPS_MARK)
        for player in self.players:
            for ship in ships:
                board.bool = False
                while not board.bool:
                    board.ship_placement(ships[ship], player.id)
        return board


    def user_exists(self, name):
        return any(map(lambda x: x.get_name() == name, self.players))

    def get_nof_players(self):
        return len(self.players)

    def get_admin(self):
        admins = filter(lambda x: x.is_admin(), self.players)
        if len(admins) == 1:
            return admins[0].get_name()
        if len(admins) > 1:
            logging.error("Multiple admins")
        return ''

class Player(object):
    newid = itertools.count().next
    def __init__(self, name):
        self.name = name
        self.id = Player.newid()+1 # Gives incremental new ID to every new player
        self.is_admin_b = True if self.id == 1 else False
        #self.board_ships = Board(NO_SHIPS_MARK) # Board holding players personal ship locations
        #self.board_myhits = Board(NO_SHIPS_MARK) # Board showing the hits made to other players

    def is_admin(self):
        return self.is_admin_b

    def set_admin(self, bool):
        self.is_admin_b = bool

    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

class Board(object):
    def __init__(self, mark):
        self.bool = False
        self.board = self.create_board(mark, BOARD_WIDTH, BOARD_HEIGHT)
        self.score = {
            CARRIER_MARK    : 0,
            BATTLESHIP_MARK : 0,
            CRUISER_MARK    : 0,
            SUBMARINE_MARK  : 0,
            DESTROYER_MARK  : 0
        }

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


    def hit_ship(self, row, column, id):
        value = self.board[row][column]
        if str(value).startswith(str(id)):
            return 0, 0
        if value < 99:
            value += 100 # Adds 10 to the field value when it has been hit for the first time
            self.board[row][column] = value
        if value-100 == 0:
            return 0, 0
        else: return 1, str(value-100)[0]
        #return value - 100 # Returns the unmodified field value

    def get_board(self):
        return self.board

class Score(object):
    pass

if __name__ == '__main__':
    game = BattleShips()