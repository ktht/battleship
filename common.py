from os import system, name


# Glboal constants ----------------------------------
CTRL_REQ_ID         = int(55)
CTRL_REQ_BOARD      = int(56)
CTRL_START_GAME     = int(57)
CTRL_HIT_SHIP       = int(58)
CTRL_ERR_MAX_PL     = int(59)
CTRL_ERR_DB         = int(60)
DATABASE_FILE_NAME  = "users.db"

def clear_screen():
    system('cls' if name == 'nt' else 'clear')

def marshal(*args):
    strings = map(lambda x: str(x), args)
    return ':'.join(strings)

def unmarshal(*args):
    return args[0].split(':')