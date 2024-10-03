import sys

from pyroute2.remote import Server, Transport

Server(Transport(sys.stdin), Transport(sys.stdout))
