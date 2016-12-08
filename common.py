from os import system, name
from string import ascii_uppercase


# Glboal constants ----------------------------------
CTRL_REQ_ID         = int(55)
CTRL_REQ_BOARD      = int(56)
CTRL_START_GAME     = int(57)
CTRL_HIT_SHIP       = int(58)
CTRL_ERR_MAX_PL     = int(59)
CTRL_ERR_DB         = int(60)
CTRL_ALL_PLAYERS    = int(61)
CTRL_NOT_ADMIN      = int(62)
CTRL_ERR_LOGGED_IN  = int(63)
CTRL_OK             = int(40)
CTRL_BRDCAST_MSG    = int(30)
DATABASE_FILE_NAME  = "users.db"

def clear_screen():
    system('cls' if name == 'nt' else 'clear')

def marshal(*args):
    strings = map(lambda x: str(x), args)
    return ':'.join(strings)

def unmarshal(*args):
    return args[0].split(':')

def print_board(board, width, height):
    print('      ' + ' '.join('%-3s' % i for i in range(1, width + 1)))  # Column numbering
    print('   ' + '-' * 4 * width)  # Line between board and colum  numbers
    for row_label, row in zip(ascii_uppercase[:height],board):  # Board with row numbering
        print '%-3s|  %s' % (row_label, ' '.join('%-3s' % i for i in row))