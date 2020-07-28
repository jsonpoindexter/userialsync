import os
import subprocess
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from userialsync.debounce import debounce
import time
from pathlib import Path
import argparse
import ast


# Tests:
# Create root dir_map directory: pass
# Create sub dir_map directory: *pass
#   *passes when running on linux and sub creating directories in linux, not when creating files in windows and running in linux
# Create file in dir_map directory: pass


# Convert --dir_map '[["public", "www"]]' to an array of strings
def args_dir_map(string):
    return ast.literal_eval(string)

class USerialSync:
    def __init__(self, args):
        self.session_name = args.port.split('/')[2]  # ttyS8 / ttyS9 exc.
        self.root_path = str(Path.cwd())
        self.slash = '/' if (self.root_path.find('/') != -1) else '\\'
        self.port = args.port
        self.baud = args.baud
        self.root_ampy_cmd = f'ampy --port {self.port}'
        if args.baud is not None:
            self.root_ampy_cmd += f' --baud {self.baud}'
        self.paths_map = args.dir_map if args.dir_map else []
        self.paths_map.append(['main.py', None])
        self.paths_map.append(['boot.py', None])
        print(self.paths_map)
        self.file_ops = {
            'created': 'put',  # src/dest
            'modified': 'put',  # src/dest
            'deleted': 'rm',  # dest
        }
        self.dir_ops = {
            'created': 'mkdir',  # dest
            'modified': 'put',  # src/dest
            'deleted': 'rmdir'  # src/dest
        }

    # Determine if the filesystem event was related to a folder/file we are syncing
    # Return [src, dest] arr if found or None
    def is_dir_map(self, src_path):
        # return any((src_path.find(path_map[0]) != -1 for path_map in self.paths_map)
        for path_map in self.paths_map:
            full_path_map = f'{self.root_path}{self.slash}{path_map[0]}'
            print(full_path_map)
            if src_path.find(full_path_map) != -1:
                if src_path == full_path_map:
                    return path_map
                else:
                    return [src_path.replace(f'{self.root_path}{self.slash}', ''),
                            f'{path_map[1]}{src_path.replace(full_path_map, "")}']

    @debounce(1)
    def ampy_operation(self, dir_map, operation):
        src_path = ''
        dest_path = ''
        if operation == 'mkdir' or operation == 'rm':
            src_path = dir_map[0] if dir_map[1] is None else dir_map[1]
        else:
            src_path = dir_map[0]
            dest_path = dir_map[1]
        ampy_cmd = f'{self.root_ampy_cmd} {operation} {src_path} {dest_path if dest_path is not None else ""}'
        # Kill any running sessions
        os.system(f'screen -S {self.session_name} -X quit')
        print(ampy_cmd)
        if os.system(ampy_cmd) != 0:
            return
        print(self.session_name, self.port, self.baud)
        os.system(f'screen -dmS {self.session_name} {self.port} {self.baud}')
        # restart micropython machine
        os.system(f'screen -S {self.session_name} -X stuff "^C^D"')
        os.system(f'screen -r {self.session_name}')
        print('')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', help='Serial port', type=str, required=True)
    parser.add_argument('--baud', help='Serial baud', type=str, required=True)
    # List of Lists [[*source_dir*, *dest_dir*]]that is used a a directory map to sync
    # a local folder (and sub files/folders) to a micropython folder
    # Example: ... --dir_map '[["public", "www"], '["libs", "modules"]']
    # In this example the local project 'public' folder will sync to the 'www' folder on the micro python
    # as well, the 'libs' folder will sync to the 'modules' folder
    parser.add_argument('--dir_map', type=args_dir_map, required=False)
    args = parser.parse_args()
    u_serial_sync = USerialSync(args)

    class EventHandler(LoggingEventHandler):
        @staticmethod
        def on_any_event(event):
            # Ignore files ending in ~ bc generally its a temp file from another proghram
            if event.src_path[len(event.src_path) - 1] == '~':
                return
            dir_map = u_serial_sync.is_dir_map(event.src_path)
            if dir_map and (event.is_directory and event.event_type != 'modified' or event.is_directory is not True):
                print(f'\033[1;33;40m{event.event_type} {event.src_path} {event.is_directory} {dir_map}')
                # Determine ampy operation to perform
                operation = u_serial_sync.file_ops.get(event.event_type, None)
                if operation is not None:
                    u_serial_sync.ampy_operation(dir_map, operation)
                else:
                    print(f'file operation {event.event_type} not supported')
            else:
                print('')

    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, u_serial_sync.root_path, recursive=True)
    observer.start()
    process = subprocess.run(['screen', '-S', args.port.split('/')[2], args.port, args.baud], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, universal_newlines=True)
    print(process.stdout, process.stderr)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
