"""Some console related functions"""

from common.constants import bcolors
from objects import glob


def printServerStartHeader(asciiArt):
    """
    Print server start header with optional ascii art

    asciiArt -- if True, will print ascii art too
    """

    if asciiArt:
        printColored(" (                 (     ", bcolors.YELLOW)
        printColored(" )\\ )        *   ) )\\ )  ", bcolors.YELLOW)
        printColored("(()/(  (   ` )  /((()/(  ", bcolors.YELLOW)
        printColored(" /(_)) )\\   ( )(_))/(_)) ", bcolors.YELLOW)
        printColored("(_))  ((_) (_(_())(_))   ", bcolors.YELLOW)
        printColored("| |   | __||_   _|/ __|  ", bcolors.GREEN)
        printColored("| |__ | _|   | |  \\__ \\  ", bcolors.GREEN)
        printColored("|____||___|  |_|  |___/  \n", bcolors.GREEN)

    printColored("> Welcome to the Latest Essential Tatoe Server v{}".format(glob.VERSION), bcolors.GREEN)
    printColored("> Made by the Ripple and Akatsuki teams", bcolors.GREEN)
    printColored("> {}https://github.com/osuAkatsuki/lets".format(bcolors.UNDERLINE), bcolors.GREEN)
    printColored("> Press CTRL+C to exit\n", bcolors.GREEN)


def printNoNl(string):
    """
    Print string without new line at the end

    string -- string to print
    """

    print(string, end="")


def printColored(string, color):
    """
    Print colored string

    string -- string to print
    color -- see bcolors.py
    """

    print(f"{color}{string}{bcolors.ENDC}")
    return

def printError():
    """Print error text FOR LOADING"""

    printColored("Error", bcolors.RED)


def printDone():
    """Print error text FOR LOADING"""

    printColored("Done", bcolors.GREEN)


def printWarning():
    """Print error text FOR LOADING"""

    printColored("Warning", bcolors.YELLOW)

def printGetScoresMessage(message):
    printColored(f"[get_scores] {message}", bcolors.PINK)

def printSubmitModularMessage(message):
    printColored(f"[submit_modular] {message}", bcolors.YELLOW)

def printBanchoConnectMessage(message):
    printColored(f"[bancho_connect] {message}", bcolors.YELLOW)

def printGetReplayMessage(message):
    printColored(f"[get_replay] {message}", bcolors.PINK)

def printMapsMessage(message):
    printColored(f"[maps] {message}", bcolors.PINK)

def printRippMessage(message):
    printColored(f"[ripp] {message}", bcolors.GREEN)

# def printRippoppaiMessage(message):
# 	printColored("[rippoppai] {}", bcolors.GREEN)

def printWifiPianoMessage(message):
    printColored(f"[wifipiano] {message}", bcolors.GREEN)

def printDebugMessage(message):
    printColored(f"[debug] {message}", bcolors.BLUE)

def printScreenshotsMessage(message):
    printColored(f"[screenshots] {message}", bcolors.YELLOW)

def printApiMessage(module, message):
    printColored(f"[{module}] {message}", bcolors.GREEN)
