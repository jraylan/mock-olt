#!/usr/bin/python3

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

def close_all(signum, frame):
    for connection in connections:
        connection.close()
        interrupt_write.send(b'\0')
        interrupt_read.close()

    server.close()
    os._exit(0)

if __name__ == '__main__':

    signal.signal(signal.SIGHUP, close_all)
    #signal.signal(signal.SIGKILL, close_all)
    signal.signal(signal.SIGINT, close_all)
    while True:
        try:
            connection, address = server.accept()
            emulador = Manager(connection, address)
            emulador.start()
            connections.append(emulador)
        except BlockingIOError:
            pass
