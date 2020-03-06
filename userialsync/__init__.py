import os
import subprocess
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from userialsync.debounce import debounce
import time
from pathlib import Path
import argparse
import ast


# Convert --dir_map '[["public", "www"]]' to an array of strings
def args_dir_map(string):
    return ast.literal_eval(string)


class USerialSync:
    def __init__(self, args, session_name):
        self.session_name = session_name
        self.root_path = str(Path.cwd())
        self.port = args.port
        self.baud = args.baud
        self.root_ampy_cmd = f'ampy --port {self.port}'
        if args.baud is not None:
            self.root_ampy_cmd += f' --baud {self.baud}'
        args.dir_map.append(['main.py', None])
        args.dir_map.append(['boot.py', None])
        self.paths_map = self.directory_map_to_paths_map(args.dir_map)
        print(self.paths_map)

        self.file_ops = {
            'created': 'put',
            'modified': 'put',
            'deleted': 'rm',
        }
        self.dir_ops = {
            'created': 'mkdir',
            'modified': 'put',
            'deleted': 'rmdir'
        }

    # Iterate over each file/folder name and make it a full path
    # Example input: [['main.py', None],['public','www']]
    # Example output: [['/.../userialsync/main.py', None],['/.../userialsync/public','www']]
    def directory_map_to_paths_map(self, directory_map):
        results = []
        for directory in directory_map:
            results.append([f'{self.root_path}/{directory[0]}', directory[1]])
        return results

    # Determine if the filesystem event was related to a folder/file we are syncing
    # Return [src, dest] arr if found or None
    def is_dir_map(self, src_path):
        # return any((src_path.find(path_map[0]) != -1 for path_map in self.paths_map)
        for path_map in self.paths_map:
            if src_path.find(path_map[0]) != -1:
                return path_map

    @debounce(1)
    def ampy_operation(self, src_path, operation):
        session_name = self.port.split('/')[2]  # ttyS8 / ttyS9 exc.
        ampy_cmd = f'{self.root_ampy_cmd} {operation} {src_path}'
        # Kill any running sessions
        # os.system(f'screen -S {session_name} -X quit')
        print(ampy_cmd)
        # if os.system(ampy_cmd) != 0:
        #     return
        print(session_name, self.port, self.baud)
        # os.system(f'screen -dmS {session_name} {self.port} {self.baud}')
        # restart micropython machine
        # os.system(f'screen -S {session_name} -X stuff "^C^D"')
        # os.system(f'screen -r {session_name}')


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
    session_name = args.port.split('/')[2]  # ttyS8 / ttyS9 exc.
    u_serial_sync = USerialSync(args, session_name)

    class EventHandler(LoggingEventHandler):
        @staticmethod
        def on_any_event(event):
            dir_map = u_serial_sync.is_dir_map(event.src_path)
            if dir_map:
                print(event.event_type, event.src_path, dir_map)
                if event.is_directory:
                    return
                else:
                    # Determine ampy operation to perform
                    operation = u_serial_sync.file_ops.get(event.event_type, None)
                    if operation is not None:
                        u_serial_sync.ampy_operation(dir_map, operation)
                    else:
                        print(f'file operation {event.event_type} not supported')

    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, u_serial_sync.root_path, recursive=True)
    observer.start()
    # process = subprocess.run(['screen', '-S', session_name, args.port, args.baud], stdout=subprocess.PIPE,
    #                          stderr=subprocess.PIPE, universal_newlines=True)
    # print(process.stdout, process.stderr)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
