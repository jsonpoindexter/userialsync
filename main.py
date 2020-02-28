# 1. Take in args:
#   - root path [string]
#   - serial port [string]
#   - serial baud [number]
#   - watch files [ [string]] - auto main.py/boot.py
# 2. connect via serial (serialcomm)
# 3. On created/updated/deleted: 
#   - disconnect serial connection
#   - use ampy to run fs operation
#   - connect via serial
#   - restart device? 

import os
import subprocess
import argparse, sys
import time
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler

parser = argparse.ArgumentParser()
parser.add_argument('--port', help='Serial port')
parser.add_argument('--baud', help='Serial baud')
args = parser.parse_args()
print(args.port)

root_ampy_cmd = f'ampy --port {args.port}'
if args.baud is not None: root_ampy_cmd += f' --baud { args.baud}' 

# dir 
# created - mkdir
# modified - put
# deleted - rmdir

# file
# created - put
# modified - put
# deleted - rm 

from threading import Timer
import time

file_op = {
    'created': 'put',
    'modified': 'put',
    'deleted': 'rm',
}


def debounce(wait):
    """ Decorator that will postpone a functions
        execution until after wait seconds
        have elapsed since the last time it was invoked. """
    def decorator(fn):
        def debounced(*args, **kwargs):
            def call_it():
                fn(*args, **kwargs)
            try:
                debounced.t.cancel()
            except(AttributeError):
                pass
            debounced.t = Timer(wait, call_it)
            debounced.t.start()
        return debounced
    return decorator

@debounce(1)
def ampy_operation(src_path, operation):
    sessionName = args.port.split('/')[2] # ttyS8 / ttyS9 exc.
    ampy_cmd = f'{root_ampy_cmd} {operation} {src_path}'
    # Kill any running sessions
    os.system(f'screen -S {sessionName} -X quit')
    print(ampy_cmd)
    if os.system(ampy_cmd) != 0: 
        return
    print(sessionName, args.port, args.baud)
    os.system(f'screen -dmS {sessionName} {args.port} {args.baud}')
    # restart micropython machine
    os.system(f'screen -S {sessionName} -X stuff "^Cimport machine^Mmachine.reset()^M"')
    os.system(f'screen -r {sessionName}')
   

class EventHandler(LoggingEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            print('is dir')
        else: 
            if event.src_path.find('boot.py') >= 0 or event.src_path.find('main.py') >= 0:
                operation = file_op.get(event.event_type, None)
                if operation is not None:
                    print(event.event_type, event.src_path)
                    ampy_operation(event.src_path, operation)
                else:
                    print('file operation {event_type} not supported')
            
       

if __name__ == "__main__":
    path = os.getcwd()
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    sessionName = args.port.split('/')[2] # ttyS8 / ttyS9 exc.
    print('connecting to serial')
    process = subprocess.run(['screen', '-S', sessionName, args.port, args.baud], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)  
    print(process.stdout, process.stderr)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()