#!/usr/bin/python3

import threading
from olts.intelbras.intelbras_g16 import Manager
import socket
from io import BlockingIOError
import signal
import os


# Connect to the server with `telnet $HOSTNAME 5000`.

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(False)
server.bind(('127.0.0.1', 2222))
server.listen(5)

connections = []

interrupt_read, interrupt_write = socket.socketpair()


def close_all(event):
    def wrap(signum, frame):
        event.set()
        try:
            server.shutdown(socket.SHUT_RDWR)
        except:
            pass
        for connection in connections:
            connection.close()
            interrupt_write.send(b'\0')
            interrupt_read.close()

        server.close()
        os._exit(0)
    return wrap

if __name__ == '__main__':
    event = threading.Event()
    signal.signal(signal.SIGHUP, close_all(event))
    #signal.signal(signal.SIGKILL, close_all(event))
    signal.signal(signal.SIGINT, close_all(event))
    while not event.is_set():
        try:
            connection, address = server.accept()
            emulador = Manager(connection, address)
            emulador.start()
            connections.append(emulador)
        except BlockingIOError:
            pass
        except OSError as e:
            if not event.is_set():
                raise e
