import os
import subprocess
import argparse
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from userialsync.debounce import debounce
import time

parser = argparse.ArgumentParser()
parser.add_argument('--port', help='Serial port', type=str, required=True)
parser.add_argument('--baud', help='Serial baud', type=str, required=True)
args = parser.parse_args()
print(args.port)

root_ampy_cmd = f'ampy --port {args.port}'
if args.baud is not None:
    root_ampy_cmd += f' --baud {args.baud}'

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



@debounce(1)
def ampy_operation(src_path, operation):
    session_name = args.port.split('/')[2]  # ttyS8 / ttyS9 exc.
    ampy_cmd = f'{root_ampy_cmd} {operation} {src_path}'
    # Kill any running sessions
    os.system(f'screen -S {session_name} -X quit')
    print(ampy_cmd)
    if os.system(ampy_cmd) != 0:
        return
    print(session_name, args.port, args.baud)
    os.system(f'screen -dmS {session_name} {args.port} {args.baud}')
    # restart micropython machine
    os.system(f'screen -S {session_name} -X stuff "^C^D"')
    os.system(f'screen -r {session_name}')


class EventHandler(LoggingEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        else:
            if event.src_path == f'{os.getcwd()}/boot.py' or \
                    event.src_path == f'{os.getcwd()}/main.py':
                operation = file_op.get(event.event_type, None)
                if operation is not None:
                    print(event.event_type, event.src_path)
                    ampy_operation(event.src_path, operation)
                else:
                    print('file operation {event_type} not supported')


def main():
    path = os.getcwd()
    print('monitoring project dir: ', path)
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    session_name = args.port.split('/')[2]  # ttyS8 / ttyS9 exc.
    print('starting serial connect to: ', args.port)
    time.sleep(2)
    process = subprocess.run(['screen', '-S', session_name, args.port, args.baud], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, universal_newlines=True)
    print(process.stdout, process.stderr)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
