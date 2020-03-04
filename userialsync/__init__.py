import os
import subprocess
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from userialsync.debounce import debounce
import time
from pathlib import Path
import argparse
import ast


def dir_map(string):
    return ast.literal_eval(string)


# File to monitor TODO: make as an arg / default
file_names = ['boot.py', 'main.py']


# Paths = context path + filename
# paths = []

# Map a source dir (local fs) to destination dir (upy fs)
# directory_maps = [['public', 'www']]
# directory_maps but using full path name for src
# path_maps = []


# print(str(dir_path))
# path_maps.append([f'{root_dir}/{directory_map[0]}', directory_map[1]])

class Main:
    def __init__(self, args, session_name):
        self.session_name = session_name
        self.root_path = str(Path.cwd())
        self.port = args.port
        self.baud = args.baud
        self.root_ampy_cmd = f'ampy --port {self.port}'
        if args.baud is not None:
            self.root_ampy_cmd += f' --baud {self.baud}'
        if args.dir_map is not None:
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
        time.sleep(10)

    # Turn file names to monitor into full paths using exe context
    @staticmethod
    def file_names_to_paths(self):
        for file_name in file_names:
            return f'{self.path}/{file_name}'

    # def get_dir_paths(self, path):
    #     for path in paths:
    #         if path.is_dir():
    #             return self.get_dir_paths(path)
    #         else:
    #             return path

    def directory_map_to_paths_map(self, directory_map):
        results = []
        for directory in directory_map:
            results.append([f'{self.root_path}/{directory[0]}', directory[1]])
        return results

    def is_dir_map(self, src_path):
        return any(src_path.find(path_map[0]) != -1 for path_map in self.paths_map)

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

    # def is_sync_path(self, event):
    #     if event.is_directory:
    #         return
    #     else:
    #         if event.src_path == f'{os.getcwd()}/boot.py' or \
    #                 event.src_path == f'{os.getcwd()}/main.py' or \
    #                 any(path_map[0].find(event.src_path) != -1 for path_map in self.paths_map):
    #             operation = self.file_ops.get(event.event_type, None)
    #             if operation is not None:
    #                 print(event.event_type, event.src_path)
    #                 self.ampy_operation(event.src_path, operation)
    #             else:
    #                 print('file operation {event_type} not supported')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', help='Serial port', type=str, required=True)
    parser.add_argument('--baud', help='Serial baud', type=str, required=True)
    # List of Lists [[*source_dir*, *dest_dir*]]that is used a a directory map to sync
    # a local folder (and sub files/folders) to a micropython folder
    # Example: ... --dir_map '[["public", "www"], '["libs", "modules"]']
    # In this example the local project 'public' folder will sync to the 'www' folder on the micro python
    # as well, the 'libs' folder will sync to the 'modules' folder
    parser.add_argument('--dir_map', type=dir_map, required=False)
    args = parser.parse_args()
    session_name = args.port.split('/')[2]  # ttyS8 / ttyS9 exc.
    userialsync = Main(args, session_name)

    class EventHandler(LoggingEventHandler):
        def on_any_event(self, event):
            print(event.event_type, event.src_path)
            print(userialsync.is_dir_map(event.src_path))

            if event.is_directory:
                return
            else:
                if event.src_path == f'{os.getcwd()}/boot.py' or \
                        event.src_path == f'{os.getcwd()}/main.py':
                    # Determine ampy operation to perform

                    operation = userialsync.file_ops.get(event.event_type, None)
                    if operation is not None:
                        userialsync.ampy_operation(event.src_path, operation)
                    else:
                        print(f'file operation {event.event_type} not supported')

    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, userialsync.root_path, recursive=True)
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
