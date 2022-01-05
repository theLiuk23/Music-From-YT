from configparser import ConfigParser
import subprocess as s
import os
import platform
import threading
from discord import player
import sys
import os
import signal


def read_ini(config, option : str):
    config.read('variables.ini')
    return config.get('variables', option)


def write_ini(config, option : str, value : str):
    config.read('variables.ini')
    config.set('variables', option, value)
    configfile = open('variables.ini', 'w')
    config.write(configfile)
    configfile.close()


def close_original_script():
    pid = read_ini(ConfigParser(), 'pid')
    if pid == 'null': # pid is null because the bot has just been ran -->no need to reload it
        return
    # kills main.py
    if platform.system() == 'Linux':
        os.system(f'pkill -f main.py')
    elif platform.system() == 'Windows':
        os.system(f'taskkill /F /PID {int(pid)}', shell=True)
    else:
        print('Platform not supported.')


# ctrl + c handler
def signal_handler(signal=None, frame=None):
    print('hanling!')
    # resets pid to null
    write_ini(ConfigParser(), 'pid', 'null')
    sys.exit(0)


def main():
    close_original_script()
    # re-runs main.py
    os.system('python3 main.py')
    sys.exit(0)


thread = threading.Thread(target=main).run()


# TODO: not running if threading is running (?)
# thread = threading.Thread(target=signal.signal, args=(signal.SIGINT, signal_handler)).run()
signal.signal(signal.SIGINT, signal_handler)
signal.pause()