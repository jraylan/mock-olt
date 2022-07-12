
import socket
from threading import Thread


class ExitClient(Exception):
    pass

class Emulador(Thread):

    def __init__(self, connection, address):
        super().__init__()
        self.address = address
        self.connection = connection
        self.connection.setblocking(True)

    def request(self, message, secure=False):
        self.send(message)
        return self.receve_data()

    def send(self, message):
        if isinstance(message, str):
            message = message.expandtabs().encode()
        else:
            message = message.decode().expandtabs().encode()
        self.connection.send(message)
        print(f'sent: {message}')

    def sendLine(self, message):
        self.send(message)
        self.connection.send(b'\n')

    def receve_data(self):
        data = self.connection.recv(2048).decode(errors='ignore')
        print('Received:', data)
        return data

    def close(self):
        self.__running = False
        self.connection.close()
    
    @property
    def running(self):
        return self.__running

    def run(self):
        self.__running = True
        logged_in = False

        while self.running:
            try:
                if not logged_in:
                    logged_in = self.__login__()
                if logged_in:
                    for d in self.receve_data().split('\n'):
                        self.receive(d)

            except BlockingIOError:
                pass
            except ExitClient:
                return self.close()
            
