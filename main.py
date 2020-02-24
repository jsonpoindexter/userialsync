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
if args.baud is not None: root_ampy_cmd += f'--baud { args.baud}' 

# dir
# created - mkdir
# modified - put
# deleted - rmdir

# file
# created - put
# modified - put
# deleted - rm

file_op = {
    'created': 'put',
    'modified': 'put',
    'deleted': 'rm',
}

class EventHandler(LoggingEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            print('is dir')
        else: 
            if event.src_path.find('boot.py') >= 0 or event.src_path.find('main.py') >= 0:
                operation = file_op.get(event.event_type, None)
                if operation is not None: 
                    ampy_cmd = f'{root_ampy_cmd} {operation} {event.src_path}'
                    print(ampy_cmd)
                    if os.system(ampy_cmd) != 0:
                        return

                    process = subprocess.run(['cu', f'-l {args.port}', f'-s {args.baud}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                    print(process.stdout)
                    print(process.stderr)
                else:
                    print('file operation {event_type} not supported')
            
       

if __name__ == "__main__":
    path = os.getcwd()
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()