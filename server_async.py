from __future__ import print_function

import asyncore
import os
import collections
import logging
import socket
import re
import threading
import sys
import time


MAX_MESSAGE_LENGTH = 1024
THREADS = []
HOST = None
ALIVE = True

# prep file data for file transfer
def file_to_data(file_path):
    with open(file_path, 'r') as myfile:
        data=myfile.read().replace('\n', '')
    return data

# ********** OUTGOING PACKET PROTOCOLS **********
# (Prefix) (Parameters)
# MSG     | [message text]
# CMD     | [command prompt}]
# FTREQ   | [filename, filesize]
# BEG     | [filename, number of fragments]
# DATA    | [filename, sequence id, data]
# END     | [filename, number of sent fragments]
# ***********************************************

# ********** INCOMING PACKET PROTOCOLS **********
# (Prefix) (Parameters)
# ACC     | [filename, max data per fragment]
# FACK    | [filename]
# ***********************************************


class Packet(object):
    def __init__(self, prefix, params=[], *args):
        self.prefix = prefix
        self.params = params

    def __str__(self):
        msg_form = ']||['
        msg_form += self.prefix
        msg_form += ']||['
        for x in range(0,len(self.params)):
            msg_form += str(self.params[x])
            msg_form += ']||['
        return msg_form


# remote client socket
class RemoteClient(asyncore.dispatcher):

    def __init__(self, host, socket, address):
        asyncore.dispatcher.__init__(self, socket)
        self.host = host
        self.outbox = collections.deque()

    def say(self, message):
        self.outbox.append(message)

    def handle_read(self):
        client_message = self.recv(MAX_MESSAGE_LENGTH)
        self.host.broadcast_message(client_message)

    def handle_write(self):
        if not self.outbox:
            return
        packet = self.outbox.popleft()
        # check if transfer
        if packet.startswith('||'):
            if len(packet) > MAX_MESSAGE_LENGTH:
                raise ValueError('Message too long')
            else:
                self.send(packet)
            groups = packet.split('||')
            filename = str(groups[len(groups) - 2])
            f = open(filename, 'rb')
            # FILE TRANSFER
            stream = f.read(MAX_MESSAGE_LENGTH)
            logging.info(groups)
            while (stream):
                self.send(stream)
                # print('Sent ',repr(stream))
                stream = f.read(MAX_MESSAGE_LENGTH)
            f.close()
        else:
            if len(packet) > MAX_MESSAGE_LENGTH:
                raise ValueError('Message too long')
            self.send(packet)

# host
class Host(asyncore.dispatcher):

    log = logging.getLogger('Host')

    def __init__(self, address):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(address)
        self.listen(1)
        self.remote_clients = []

    # list slave nodes
    def print_clients(self):
        client_list_str = ""
        for node in self.remote_clients:
            client_list_str += str(node)
            client_list_str += ', '
        return client_list_str

    # called upon new connection
    def handle_accept(self):
        socket, addr = self.accept() # For the remote client.
        self.log.info('Accepted client at %s', addr)
        self.remote_clients.append(RemoteClient(self, socket, addr))

    # called upon incoming data
    def handle_read(self):
        self.log.info('Received message: %s', self.read())

    # broadcast a message/command to all client nodes
    def broadcast_message(self, message):
        packet = Packet('MSG',[message])
        self.log.info('Broadcasting message: %s', packet)
        for remote_client in self.remote_clients:
            remote_client.say(packet)

    def broadcast_command(self, command):
        packet = Packet('CMD',[command])
        self.log.info('Broadcasting command: %s', packet)
        for remote_client in self.remote_clients:
            remote_client.say(packet)

    # file transfer (in progress)
    def transfer(self, recipient, file_path):
        logging.info('transfer not ready! no thanks!')
    #    self.remote_clients[0].say(packet)

# command and control
def manual_commands(host):
    global HOST
    if host == None:
        logging.info("HOST not set :/")
    else:
        # control loop
        while True:
            cmd = str(raw_input(">>"))
            logging.info(cmd)
            # enter help to view available commands
            if cmd == 'help':
                logging.info("broadcast <message>")
                logging.info("cmdall <prompt>")
                #logging.info("transfer <recipient> <file_path>")
                logging.info("clients")
                logging.info("quit")
            # enter broadcast <messsage> to send a message to all clients
            if re.match(r'^broadcast [\w. ]+$', cmd) is not None:
                message = str(re.match(r'^(broadcast) (.+)$', cmd).group(2))
                host.broadcast_message(message)
            # enter cmdall <prompt> to send a command to be run on all clients
            if re.match(r'^cmdall [\w.\-\\+\- ]+$', cmd) is not None:
                prompt += str(re.match(r'^(cmdall) (.+)$', cmd).group(2))
                host.broadcast_command(prompt)
            # TRANSFER NOT READY
            if 'transfer' in cmd:
                groups = cmd.split(' ')
                recipient = groups[1]
                file_path = groups[2]
                #host.transfer(recipient, file_path)
            # enter clients to view list of client nodes
            if cmd == 'clients':
                logging.info("Clients: " + host.print_clients())
            # enter quit to end server
            if cmd == 'quit':
                logging.info("manual control loop broken, exit with ^C")
                os._exit(1)
                ALIVE = False
                return

# asynch setup
def core_service():
    global HOST
    logging.basicConfig(level=logging.INFO)
    # set host address to machine's IP and use port 1337
    host_addr = (socket.gethostbyname(socket.gethostname()), 1337)
    host = Host(host_addr)
    HOST = host
    logging.info('Creating host' + str(host.getsockname()))
    logging.info('Looping')
    asyncore.loop()

if __name__ == '__main__':
    # start asynch loop thread
    t1 = threading.Thread(target=core_service)
    THREADS.append(t1)
    t1.start()
    time.sleep(3)

    # start command and control thread
    t2 = threading.Thread(target=manual_commands, kwargs={'host': HOST})
    THREADS.append(t2)
    t2.start()

    # attempt at killing all threads
    while True:
        if ALIVE == False:
            os._exit(1)