# uSerialSync
Sync micropython files on change over serial

## Dependecies
* Python 3
* [Watchdog](https://pypi.org/project/watchdog/) - python filesystem watcher
* [Ampy](https://learn.adafruit.com/micropython-basics-load-files-and-run-code/install-ampy) serial fs utility for micropython
* [screen](https://www.gnu.org/software/screen/manual/screen.html) - serial client

## Run
While currently in your project directory:
```
sudo pip3 install . --upgrade; userialsync --port /dev/ttys8 --baud 115200 --dir_map '[["public", "www"]]' 
```
uSerialSync will:
1. Create a `screen` session with the session name `ttyS*` 
2. Monitor the project directory for changes to `main.py` or `boot.py`
3. Destroy `screen` session
4. Upload modified file to the device connected to `ttyS*`
5. Create a new `screen` session
6. Restart the device connected to `ttyS*`
