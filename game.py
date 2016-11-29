import string
import numpy as np

# Global Constants  -------------------------------------------------------------------
BOARD_WIDTH = 10
BOARD_HEIGHT = 10

NO_SHIPS_MARK = 0
CARRIER_MARK = 5
BATTLESHIP_MARK = 4
CRUISER_MARK = 3
SUBMARINE_MARK = 6
DESTROYER_MARK = 2


ships = {"Carrier":[5,CARRIER_MARK],
         "Battleship":[4,BATTLESHIP_MARK],
         "Cruiser":[3,CRUISER_MARK],
         "Submarine":[3,SUBMARINE_MARK],
         "Destroyer":[2,DESTROYER_MARK]}

class BattleShips(object):
    players = []

    def __init__(self):
        #self.board = Board('0') # Board to print out
        self.create_player("Guy")

        firstpl = self.players[0]

        try:
            firstpl.board_ships.ship_placement(ships['Submarine'],1,1,'h')
            firstpl.board_ships.ship_placement(ships['Carrier'], 3, 4, 'v')
        except IndexError as err:
            print(err)

        firstpl.board_ships.print_board()

    def create_player(self, name):
        self.players.append(Player(name))


class Player(object):
    def __init__(self, name):
        self.name = name
        self.board_ships = Board(NO_SHIPS_MARK) # Board holding players personal ship locations
        self.board_myhits = Board(NO_SHIPS_MARK) # Board showing the hits made to other players

    # TODO: Save the name and check wether it is already taken

class Board(object):
    def __init__(self, mark):
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
        for row_label, row in zip(string.ascii_uppercase[:BOARD_HEIGHT], self.board): # Board with row numbering
            print '%-3s|  %s' % (row_label, ' '.join('%-3s' % i for i in row))

    def ship_placement(self, ship, row, column, v_or_h):
        if v_or_h == 'v':
            sublist = self.board[:,column-1][row-1:(row+ship[0]-1)]
            if not all(v == 0 for v in sublist): # Checks overlap with other ships
                raise IndexError('Multiple ships overlapping!')
            if len(sublist) >= ship[0]: # Checks if ship would go out of boundaries
                self.board[:, column - 1][row - 1:(row + ship[0] - 1)] = ship[1]
            else:
                raise IndexError('Ship placement out of board range!')

        else:
            sublist = self.board[row-1][column-1:(column+ship[0]-1)]
            if not all(v == 0 for v in sublist): # Checks overlap with other ships
                raise IndexError('Multiple ships overlapping!')
            if len(sublist) >= ship[0]: # Checks if ship would go out of boundaries
                self.board[row - 1][column - 1:(column + ship[0] - 1)] = ship[1]
            else:
                raise IndexError('Ship placement out of board range!')

    def hit_ship(self, row, column):
        value = self.board[row-1][column-1]
        if value < 9:
            if value != 0:
                self.score[value] += 1
            value += 10 # Adds 10 to the field value when it has been hit for the first time
            self.board[row - 1][column - 1] = value
        return value - 10 # Returns the unmodified field value


class Score(object):
    pass

game = BattleShips()
