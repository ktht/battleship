import itertools, random, threading, common, logging
from string import ascii_uppercase
from collections import defaultdict
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
    '''Battleships game manager

    Used for creating and later accessing player objects and the game board.
    '''

    def __init__(self):
        '''Initializes Battleships game instance'''
        self.ships_l = {'5': 5, '4': 4, '3': 3, '2': 2, '6': 3}
        self.ships_tot = 17
        self.players = []
        self.cv_create_player = threading.Condition()

    def create_player(self, name):
        ''' Creates a player object
        :param name: name of the player object
        :return: Player_Id, OK  - if succeeded
                 -1, ERR_MAX_PL - if max number of player has been reached
        '''
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
        ''' Creates a new board object and populates it with every player ships

        Also creates a dict for every player, containing coordinates of players ships

        :return: populated board object
        '''
        global BOARD_HEIGHT, BOARD_WIDTH
        BOARD_HEIGHT = int(np.rint(np.sqrt(30*len(self.players))))
        BOARD_WIDTH = BOARD_HEIGHT + 1
        board =  Board(NO_SHIPS_MARK)
        for player in self.players:
            for ship in ships:
                board.bool = False
                while not board.bool:
                    board.ship_placement(ships[ship], player.id)
        for coord, board_val in np.ndenumerate(board.get_board()):
            if int(board_val) != 0: # If on those coords there is a ship
                pl_id = str(board_val)[0]
                self.players[int(pl_id)-1].ships_dict[str(board_val)[1:]].append(coord)
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

    def get_winner(self):
        return filter(lambda x: not x.get_lost(), self.players)

class Player(object):
    ''' Class containing players information '''
    newid = itertools.count().next
    def __init__(self, name):
        self.name = name
        self.id = Player.newid()+1 # Gives incremental new ID to every new player
        self.is_admin_b = True if self.id == 1 else False
        self.ships_dict = defaultdict(list) # Dictionary storing coordinates of every ship the player has
        self.ships_dmg = defaultdict(int) # Dict storing all the dmg player has got
        self.has_lost = False

    def is_admin(self):
        return self.is_admin_b

    def set_admin(self, bool):
        self.is_admin_b = bool

    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def set_lost(self):
        self.has_lost = True

    def get_lost(self):
        return self.has_lost

class Board(object):
    ''' Game board manager

    Used for creating, populating and later modifying the game board
    Board is created using numpy.
    '''
    def __init__(self, mark):
        self.bool = False # Boolean helping to populate the board with ships
        self.board = self.create_board(mark, BOARD_WIDTH, BOARD_HEIGHT)
        self.score = defaultdict(int)

    def create_board(self, mark, w, h):
        ''' Creates numpy array for the game board
        :param mark: character to be used for filling the board
        :param w: board width
        :param h: board height
        :return: board array
        '''
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
        ''' Used for placing the ships on the board

        It also checks if ship would go out of boundaries or if multiple ships would overlap

        :param ship: list containing ship id and size
        :param id: Id of the player whose ship is being placed
        '''
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
                return
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
        ''' Used for making hits to the ships on the board

        This function also checks if player would hit his own ship.
        After a coordinate has been hit, 100 is added to its value, so same hit would not be
        counted twice.

        :param row: row index of the hit
        :param column: column index of the hit
        :param id: Id of the player who made the hit
        :return: 0, 0         -- when hit was a miss or hit players own ship
                 1, player_id -- 1 and Id of the player who got hit
        '''
        value = self.board[row][column]
        if value > 100:
            if str(value-100).startswith(str(id)):
                return 0, 0
        elif str(value).startswith(str(id)):
            return 0, 0
        if value < 99:
            if value != 0:
                self.score[str(value)[0]] += 1
            value += 100 # Adds 100 to the field value when it has been hit for the first time
            self.board[row][column] = value
        if value-100 == 0:
            return 0, 0
        else: return 1, str(value-100)[0]
        #return value - 100 # Returns the unmodified field value

    def get_board(self):
        return self.board

    def get_value(self, x, y):
        return self.board[x][y]


if __name__ == '__main__':
    game = BattleShips()