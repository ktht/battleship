import logging, functools, os, string, sys

# Connection parameters -----------------------------
host = 'localhost'
port = 5672
mquser = 'guest'
mqpwd  = 'guest'

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
CTRL_SIGNAL_PL_TURN = int(50)
CTRL_HIT_TIMEOUT    = int(70)
CTRL_ERR_HIT        = int(80)
DATABASE_FILE_NAME  = "users.db"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def marshal(*args):
    strings = map(lambda x: str(x), args)
    return ':'.join(strings)

def unmarshal(*args):
    return args[0].split(':')

def marshal_decorator(func):
    @functools.wraps(func)
    def decorated(self, *args):
        return unmarshal(func(self, marshal(*args)))
    return decorated

def print_board(board, board2):
    counter = 0
    print('      ' + ' '.join('%-3s' % i for i in range(1, board.shape[1] + 1))+' '*10),  # Column numbering
    print('      ' + ' '.join('%-3s' % i for i in range(1, board.shape[1] + 1)))
    print('   ' + '-' * 4 * board.shape[1]+' '*12),  # Line between board and colum  numbers
    print('   ' + '-' * 4 * board.shape[1])
    second_board = zip(string.ascii_uppercase[:board2.shape[0]],board2)
    for row_label, row in zip(string.ascii_uppercase[:board.shape[0]],board):  # Board with row numbering
        print '%-3s|  %s' % (row_label, ' '.join('%-3s' % i for i in row))+' '*10,
        print '%-3s|  %s' % (second_board[counter][0], ' '.join('%-3s' % i for i in second_board[counter][1]))
        counter += 1

def synchronized(lock_name):
    def wrapper(func):
        @functools.wraps(func)
        def decorator(self, *args, **kwargs):
            logging.debug("Acquiring lock: %s" % lock_name)
            lock = getattr(self, lock_name)
            with lock:
                result = func(self, *args, **kwargs)
            logging.debug("Released lock: %s" % lock_name)
            return result
        return decorator
    return wrapper

def synchronized_g(lock):
    def wrapper(func):
        @functools.wraps(func)
        def decorator(*args, **kw):
            lock.acquire()
            try:
                return func(*args, **kw)
            finally:
                lock.release()
        return decorator
    return wrapper

import sys

def query_yes_no(question, default = "yes"):
    '''Ask a yes/no question via raw_input() and return their answer.
    :param question: string, presented to the user
    :param default:  string, presumed answer
    :return: True, if the answer is ,,yes'' or similar,
             False otherwise

    Taken from: http://stackoverflow.com/a/3041990
    '''
    valid = {
        "yes": True,
        "y"  : True,
        "ye" : True,
        "no" : False,
        "n"  : False
    }
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")