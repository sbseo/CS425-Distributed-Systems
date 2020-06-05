import socket
from _thread import *
import threading 
from collections import defaultdict
import signal
import time
import sys
import random
import queue

"""
	Globals
"""
HOST_RECV = ''
PORT_RECV = 1301
HOST_SEND = 'localhost'
PORT_SEND = 1302
BUFFER = []

def signal_handler(signal, frame):
        # close the socket here
        print("exiting")
        sys.exit(0)

def threadedRecv(conn, addr):
	BUFFERSIZE = 1024
	with conn:
		print('Connected by', addr)
		while True:
			data = conn.recv(BUFFERSIZE)
			if not data: break
			# BUFFER = repr(data)
			print(repr(data))
	conn.close()

def threadedSend(socket):
	i = 0
	while i < 10:
		socket.sendall(b''.join([bytes(str(1), 'utf8'), b' # ', bytes(str(i), 'utf8')]))
		i = i + 1
		time.sleep(random.random())
	
	socket.close()


def threadedAccept(q, ):
	got = False
	s = None
	while got == False:
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.bind((HOST_RECV, PORT_RECV))
			s.listen(1)
			conn, addr = s.accept()
			q.put(conn)
			q.put(addr)
			got = True
		except Exception as e:
			print("Unable to bind socket")
			time.sleep(random.random())
		finally:
			s.close()

def threadedConnect(q, ):
	got = False
	while got == False:
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect((HOST_SEND, PORT_SEND))
			# s.sendall(bytes(str(15), 'utf8'))
			# s.close()
			q.put(s)
			got = True
		except Exception as e:
			print("Failed to connect")
			time.sleep(random.random())

"""
	Receive and send
"""
signal.signal(signal.SIGINT, signal_handler)

qAcc = queue.Queue()
qConn = queue.Queue()

print("Starting accept and connect")

accept_t = threading.Thread(target=threadedAccept, args=(qAcc, ))
accept_t.start()

connect_t = threading.Thread(target=threadedConnect, args=(qConn, ))
connect_t.start()

accept_t.join()
connect_t.join()

print("Done accepting and connecting")
conn = qAcc.get()
addr = qAcc.get()
sock = qConn.get()

print("Begining to receive and send data")

recv_t = threading.Thread(target=threadedRecv, args=(conn, addr))
send_t = threading.Thread(target=threadedSend, args=(sock, ))

recv_t.start()
send_t.start()

recv_t.join()
send_t.join()

print("Done recv")

	