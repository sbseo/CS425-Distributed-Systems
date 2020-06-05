import time, math
import socket, socketserver
from _thread import *
import threading 
from collections import defaultdict
import signal
import time
import sys
import random
import queue
import subprocess
import signal
import os
import time

# pack data to send
import pickle

from isis import *
from process import *
from message import *
from config import *

import copy

# alternative to sockets
from multiprocessing.connection import Listener
from multiprocessing.connection import Client

"""
    Globals
"""
NUM_NODES = None
OFFSET = None

HOST_RECV = ''
PORT_RECV = 3100

stop_threads = False

vmList = [vm1, vm2, vm3, vm4, vm5, vm6, vm7, vm8, vm9]
HOST_SEND = [vm1, vm2, vm3, vm4, vm5, vm6, vm7, vm8, vm9]
PORT_SEND = 3100

SPACING = 100 # defines the number of ports that each process takes
HB_SPACING = 50 # the number of ports we offset real ones from to use for HB

HEARTBEAT_SEND_DELAY = 0.5 # how often send a heartbeat
HEARTBEAT_OBSERVED = [] # doesnt need lock, only one writer. reader doesnt matter
HEARTBEAT_DEAD = [] # list of dead processes
K = 2 # scale factor


"""
    TOTAL ORDERING verification
"""
totalOrdering = [] # for total ordering verification
TO = []
TIMESTAMPS = [] # Aligned with TO

CONN_NUM = []

"""
    QUEUES FOR THE PROCESS TO SEND/RECEIVE
"""
SEND_QUEUE_LIST = []
RECEIVE_QUEUE = queue.Queue()

"""
    LOCKS
"""
# In Process()
HOLDBACK_LOCK = threading.Lock() #From RLock to Lock
DELIVERED_LOCK = threading.Lock()
RREP_DICT_LOCK = threading.Lock()
SEQ_LOCK = threading.Lock()
DICT_UPDATE_LOCK = threading.Lock()
BANDWIDTH_LOCK = threading.Lock()

TO_LOCK = threading.Lock()

# Global sending/receiveing queues
SEND_QUEUE_LIST_LOCK = threading.Lock()
# RECEIVE_LOCK = threading.Lock()

"""
    Bandwidth Checker
"""
BANDWIDTH_LIST = []
BANDWIDTH_TEMP_LIST = []

def bandwidth_checker():   
    while True:
        # print("am i running")
        with BANDWIDTH_LOCK:
            BANDWIDTH = 0
            for v in BANDWIDTH_TEMP_LIST:
                BANDWIDTH += v
            BANDWIDTH_LIST.append(BANDWIDTH)
            BANDWIDTH_TEMP_LIST.clear()
        # print(BANDWIDTH_LIST)
        time.sleep(1)
    return

# scheduler = BackgroundScheduler()
# job = scheduler.add_job(bandwidth_checker, 'interval', minutes=1)

"""
    Delay Checker with External Synchronization (NTP)
"""
# c = ntplib.NTPClient()
# response = c.request('0.north-america.pool.ntp.org')

"""
    Signal handler to deal with stupid process killing
    also we can use
        pkill --signal SIGINT python3
"""
def signal_handler(signal, frame):
        # close the socket here
        print("exiting")
        for i in TO:
            print(i)
        # for i in range(TO.qsize()):
        #     print(TO.get())

        '''
            Logger
        '''
        print('#################################')
        with DICT_UPDATE_LOCK:
            with open("("+ str(NUM_NODES) + ")" + "node" + str(OFFSET) + ".txt", "w") as fd:
                fd.write('################################# \n')
                for a in TO:
                    fd.write(str(a[0:2]) + " ")
                fd.write('\n')
                fd.write('\n')
                fd.write('BALANCES')
                print("BALANCES", end = '')
                for k, _ in list(p.accountDict.items()):
                    fd.write(" "+ str(k) + ":" + str(p.accountDict[k]) + " ")
                    print(" "+ str(k) + ":" + str(p.accountDict[k]), end = '')
                fd.write('\n')
                fd.write('\n')
                fd.write('BANDWIDTH: \n')
                for b in BANDWIDTH_LIST:
                    fd.write(str(b))
                    fd.write('\n')
                fd.write('\n')
                fd.write('\n')
                fd.write('TIMESTAMP: \n')
                for ts in TIMESTAMPS:
                    fd.write(str(ts))
                    fd.write('\n')
                # p.printAccs()
                fd.close()
        sys.exit(0)

"""
    sendHeartbeat
        Inputs:
            socket: The socket we send on
        Outputs:
            None
        Description:
            This funciton sends heartbeat messages every
            HEARTBEAT_SEND_DELAY
"""
def heartbeatSend(socket):
    while True:
        time.sleep(HEARTBEAT_SEND_DELAY)
        socket.send(b''.join([bytes(str(OFFSET), 'utf8'), b' HB\n']))

"""
    heartbeatDetect
        Inputs:
            None
        Outputs:
            None
        Description:
            This function detects whether we have a dead process
            in an infinite while loop.  If we have exceeded our
            K * observedDelay then we mark the process as dead.

            We do not actually need a lock in this case because
            this only reads.
"""
def heartbeatDetect():
    while True: 
        for i in range(len(HEARTBEAT_OBSERVED)):
            if time.time() - HEARTBEAT_OBSERVED[i] > K * HEARTBEAT_SEND_DELAY and HEARTBEAT_OBSERVED[i] != 0:
                if i not in HEARTBEAT_DEAD:
                    HEARTBEAT_DEAD.append(i)

"""
    heartbeatParse
        Inputs:
            data: This is the message we receive
        Outputs:
            None
        Description:
            Parse the message and update observed times
"""
def heartbeatParse(data):
    if data != None:
        splitted = data.decode().split()
        splitted[0] = int(splitted[0])
        if HEARTBEAT_OBSERVED[splitted[0]] == 0: 
            HEARTBEAT_OBSERVED[splitted[0]] = time.time()
        else:
            HEARTBEAT_OBSERVED[splitted[0]] = time.time()

"""
    heartbeatRecv
        Inputs:
            conn: From socket.accept()
            addr: From socket.accept()
        Outputs:
            None
        Description:
            This function receives all the heartbeat messages
"""
def heartbeatRecv(conn, addr):
    BUFFERSIZE = 1024
    data = None
    
    # Change ip address to name
    for i, ip in enumerate(vmList):
        if addr[0] == ip:
            vm = i
            break
        elif addr[0] == '127.0.0.1':
            # print("Using localhost")
            vm = i

    with conn:
        print('Connected by (HB) VM', vm)
        while True:
            heartbeatParse(data)
            data = conn.recv(BUFFERSIZE)
            if not data: break
    conn.close()

"""
    threadedRecv
        Inputs:
            conn: Returned from socket.accept
            addr: Returned from socket.accept
        Outputs:
            None
        Description:
            This is the thread that handles
            receiving messages from other processes
"""
def threadedRecv(conn, i):
    data = conn.recv()
    connNum = int(chr(data[0]))
    CONN_NUM[connNum] = i
    # print(connNum)
    with conn:
        # print("DEBUG threadedRecv cnt:", i, flush=True)
        while True:
            data = conn.recv()
            if not data: break
            
            with BANDWIDTH_LOCK:
                # Save bandwidth
                BANDWIDTH_TEMP_LIST.append(len(data))
                
            # print("DEBUG threadedRecv cnt:", i, flush=True)

            # recieve a message object and process it
            result = pickle.loads(data)
            
            # with DELIVERED_LOCK and HOLDBACK_LOCK and RREP_DICT_LOCK: # and ACCOUNT_DICT_LOCK and SEQ_LOCK:
            with RREP_DICT_LOCK and HOLDBACK_LOCK and DELIVERED_LOCK and DICT_UPDATE_LOCK and SEQ_LOCK:
                # with SEQ_LOCK:
                reply = p.recvWrapper(result)
                if reply != None:
                    if reply.isRRep:
                        with SEND_QUEUE_LIST_LOCK:
                            for j in range(NUM_NODES):
                                SEND_QUEUE_LIST[j].put(reply)
            
                        # # print("FFFF", reply.target, flush=True)
                        # off = -1
                        # for j in range(NUM_NODES):
                        #     if CONN_NUM[j] == reply.target:
                        #         off = j
                        #         break
                        # assert off != -1
                        # with SEND_QUEUE_LIST_LOCK:
                        #     SEND_QUEUE_LIST[j].put(reply)

"""
    threadedSend
        Inputs:
            socket: The socket we wish to send message out on
            TODO: MESSAGE
"""
def threadedSend(socket, i):
    socket.send(bytes(str(OFFSET), 'utf8'))

    while True: 
        if SEND_QUEUE_LIST[i].empty() == False:
            with SEND_QUEUE_LIST_LOCK:
                outMsg = SEND_QUEUE_LIST[i].get()
                if outMsg != None:
                    # print("DEBUG threadedSend:", "srep", outMsg.isSRep, "rrep", outMsg.isRRep, "target", outMsg.target, flush=True)
                    # if outMsg.isSRep:
                    #     print("D#E#B#U#G threadedSend:", "srep", outMsg.isSRep)
                    
                    socket.send(pickle.dumps(outMsg, protocol=4))
                # print("DEBUG threadedSend::::", i, outMsg.target, outMsg.isRRep, outMsg.isSRep, outMsg.amount, outMsg.targetAcc, outMsg.messageId[20:], flush=True)
    
    socket.close()

"""
    threadedAccept
        Inputs:
            q: Queue
            i: Port offset
        Outputs:
            None
        Description:
            This function creates a socket which we are able to
            listen for messages from.  The struct (conn, addr)
            is pushed to our queue as a return value
"""
def threadedAccept(q, i):
    got = False
    s = None
    while got == False:
        try:
            print("Accept failed ", )
            s = Listener((HOST_RECV, PORT_RECV + i))
            conn = s.accept()
            q.put(conn)
            got = True
        except Exception as e:
            print("Unable to bind socket", PORT_RECV + i, flush=True)
            time.sleep(random.random())
        finally:
            s.close()

"""
    # TODO: THIS NEEDS TO HANDLE MULTIPLE IP ADDR
    threadedConnect
        Inputs:
            q: Queue
            i: Port offset
        Outputs:
            None
        Description:
            This function creates a connection which we can send
            messages on to a different process
"""
def threadedConnect(q, i, IP):
    got = False
    while got == False:
        try:
            s = Client((HOST_SEND[IP], PORT_SEND + i))
            q.put(s)
            got = True
        except Exception as e:
            print("Failed to connect", PORT_SEND + i, flush=True)
            print(HOST_SEND[IP], flush=True)
            time.sleep(random.random())

"""
    stdInRead
        Inputs:
        Outpus:
        Description:
            This is a thread that reads from stdin and then
            puts the message at the head of the SEND_QUEUE
"""
def stdInRead(p):
    
    # Read only three transactions from generator. For debugging purpose
    i = 0
    while True:
        for line in sys.stdin:
            byte = str.encode(line)
            result = line
            # i+=1
            if result != '':
                # print("DEBUG stdInRead: ", result)
                # we need to lock the SENDER_QUEUE (put new msg) and 
                # the the process's rrep dict queue (create new entry)
                with HOLDBACK_LOCK and DICT_UPDATE_LOCK and RREP_DICT_LOCK and SEND_QUEUE_LIST_LOCK and SEQ_LOCK:
                    newMsg = p.createNewMessage(result)
                    for i in range(len(SEND_QUEUE_LIST)):
                        SEND_QUEUE_LIST[i].put(newMsg)
                    break

"""
    threadedIsis
        Inputs:
        Outputs:
        Description:
            This function implents the thread that performs all the isis actions
"""
def threadedIsis():
    # never clear holdback so we index it that way
    HOLDBACK_IDX = 0
    prevTime = time.time()
    while True:
        # check if there are any messages that are ready to send
        # an SRep

        with RREP_DICT_LOCK and SEQ_LOCK and HOLDBACK_LOCK:
            toDelKeys = []
            for key, _ in list(p.selfMessageRepDict.items()):
                if len(p.selfMessageRepDict[key]) >= NUM_NODES - 1:
                    # print("DEBUG threadedIsis: ready to send SRep", flush=True)
                    sRep = p.createSenderReply(p.selfMessageRepDict[key][0].messageId)
                    toDelKeys.append(key)
                    with SEND_QUEUE_LIST_LOCK:
                        for i in range(len(SEND_QUEUE_LIST)):
                            SEND_QUEUE_LIST[i].put(sRep)
                    # p.printAccs()
            for key in toDelKeys:
                del p.selfMessageRepDict[key]
        
        # reorder messages in holdback and check deliverability
        with HOLDBACK_LOCK:
            # TODO: DO WE NEED A DEEP COPY
            if len(p.holdback) > 0:
                holdbackCpy = p.holdback
                
                # for msg in holdbackCpy:
                    # print("DEBUG threadedIsis:", msg.isDeliverable)
                    # Isis.reorderMessages(p, msg)
                
                # Reorder Message 
                with SEQ_LOCK:
                    holdbackCpy = p.holdback
                    for i, m in enumerate(holdbackCpy):
                        if m.isDeliverable == True:
                            p.holdback.sort(key = lambda x: x.proposedSeq) 
                            # print("Deliverables index in holdback: ", i)
                            # Isis.printHoldback(p)
                            break
                
                # Now move to deliverables
                holdbackCpy = p.holdback
                # holdbackCpy2 = p.holdback
                # with DELIVERED_LOCK:
                # a = HOLDBACK_IDX
                # for i in range(a, len(holdbackCpy)):
                #     m = holdbackCpy[i]
                #     # print("DEBUG threadedIsis:", i, m.messageId[0:10], m.proposedSeq, m.isDeliverable, flush=True)
                #     if m.isDeliverable:
                #         TO.append(m.messageId)
                #         HOLDBACK_IDX += 1
                #     else:
                #         # print("DEBUG PASS")
                #         break

                toDelMsg = []
                for i in range(len(holdbackCpy)):
                    m = holdbackCpy[i]
                    # print("DEBUG threadedIsis:", i, m.messageId[0:10], m.proposedSeq, m.isDeliverable, flush=True)
                    if m.isDeliverable:
                        toDelMsg.append(m)
                        TO.append(m.messageId)
                        TIMESTAMPS.append(time.time() * 1000) # Save in milliseconds
                    else:
                        break
                p.holdback = list(set(p.holdback)-set(toDelMsg))
                
                # update accounts
                with DICT_UPDATE_LOCK:
                    for m in toDelMsg:
                        if m.type == "DEPOSIT":
                            p.accountDict[m.targetAcc] += m.amount
                        elif m.type == "TRANSFER":
                            if p.accountDict[m.sourceAcc] - m.amount < 0:
                                break
                            p.accountDict[m.sourceAcc] -= m.amount
                            p.accountDict[m.targetAcc] += m.amount

                
                
                # print("#######################################")
                # print totally ordered messages
                # for a in TO:
                #     print(a)
                
                """
                    Logger
                """
                with DICT_UPDATE_LOCK:
                    currTime = time.time()
                    if currTime - prevTime > 5.0:
                        print('#################################')
                        p.printAccs()
                        prevTime = currTime
                #     with open("("+ str(NUM_NODES) + ")" + "node" + str(OFFSET) + ".txt", "a") as fd:
                #         fd.write('################################# \n')
                #         for a in TO:
                #             fd.write(str(a[0:2]) + " ")
                #         fd.write('\n')
                #         fd.write('\n')
                #         fd.write('BALANCES')
                #         for k, _ in list(p.accountDict.items()):
                #             fd.write(" "+ str(k) + ":" + str(p.accountDict[k]) + " ")
                #         fd.write('\n')
                #         fd.close()
                # print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")

"""
    purgeDeadProcessMsg
        Description:
            When a process is detected to be dead,
            we purge all messages in our holdback queue
            relating to that process (sent by that process)
            Because we are only purging things in holdback queue
            these will only be message type (not RRep and SRep)
"""
def purgeDeadProcessMsg():
    while True:
        localLen = 0
        if len(HEARTBEAT_DEAD) > localLen:
            tempHoldback = []
            for i in range(len(p.holdback)):
                if p.holdback[i].pid not in HEARTBEAT_DEAD:
                    tempHoldback.append(p.holdback[i])
            # copy live messages back in
            p.holdback = tempHoldback

            # NOTE: We do not clear HEARTBEAT_DEAD because
            # messages from dead processes 

"""
    MAIN LOOP
"""
# Setup SIGINT signal handler
signal.signal(signal.SIGINT, signal_handler)

# Grab number of nodes
if len(sys.argv) == 3:
    NUM_NODES = int(sys.argv[1])
    OFFSET = int(sys.argv[2])
else:
    print("Please enter the number of nodes running on the system and the offset this VM is.")
    print("For example, this is VM number 3 (out of 8), this value is ZERO indexed")
    print("\n    python3 ____.py 8 2")

# Initialize the Process
p = Process()
p.assignPid(OFFSET)
# p.proposedSeq = random.randint(0,1000) # What is this
p.assignNumOtherProc(NUM_NODES - 1)

# allocate separate send queues for each process we need to send to
for i in range(NUM_NODES):
    SEND_QUEUE_LIST.append(queue.Queue())
    # allows us to check which maps to what
    CONN_NUM.append(-1)

# initialize the HEARTBEAT_OBSERVED list with NUM_NODES zeros
print("Initializing hearbeat oberseved delay")
for i in range(NUM_NODES):
    HEARTBEAT_OBSERVED.append(0)

qAcc = queue.Queue()
qConn = queue.Queue()
qAcc_HB = queue.Queue()
qConn_HB = queue.Queue()

print("Starting accept and connect")

RECV_PORT_OFFSETS = []

accept_t_L = []
accept_t_HB_L = []
connect_t_L = []
connect_t_HB_L = []
for i in range(NUM_NODES - 1):
    # ports to receive messages on
    RECV_PORT_OFFSETS.append(SPACING * OFFSET + i)
    accept_t = threading.Thread(target=threadedAccept, args=(qAcc, SPACING * OFFSET + i))
    accept_t_L.append(accept_t)
    accept_t.start()
    
    # ports to receive heartbeats on
    RECV_PORT_OFFSETS.append(SPACING * OFFSET + i + HB_SPACING)
    accept_t = threading.Thread(target=threadedAccept, args=(qAcc_HB, SPACING * OFFSET + i + HB_SPACING))
    accept_t_HB_L.append(accept_t)
    accept_t.start()

# loop over each process we need to connect to
for i in range(NUM_NODES):
    if i == OFFSET:
        continue
    elif i < OFFSET:
        conn_port = i * SPACING + OFFSET - 1
    else:
        conn_port = i * SPACING + OFFSET
    if conn_port not in RECV_PORT_OFFSETS:
        # message ports
        connect_t = threading.Thread(target=threadedConnect, args=(qConn, conn_port, i))
        connect_t_L.append(connect_t)
        connect_t.start()

        # heartbeat ports
        connect_t = threading.Thread(target=threadedConnect, args=(qConn_HB, conn_port + HB_SPACING, i))
        connect_t_HB_L.append(connect_t)
        connect_t.start()

for thread in connect_t_L:
    thread.join()
for thread in accept_t_L:
    thread.join()
time.sleep(1)
time.sleep(1)

print("Done accepting and connecting")

# print(connect_t_HB_L)

# create lists
conn = []
addr = []
sock = []
for i in range(NUM_NODES - 1):
    print("A")
    conn.append(qAcc.get())
    # addr.append(qAcc.get())
    sock.append(qConn.get())
print("B")

# print("########")
# print(conn)
# print("########")
# print(addr)
# print("########")
# print(sock[0].getpeername()[1])
# print("########")

conn_HB = []
addr_HB = []
sock_HB = []
# for i in range(NUM_NODES - 1):
#     print("C")
#     conn_HB.append(qAcc_HB.get())
#     addr_HB.append(qAcc_HB.get())
#     sock_HB.append(qConn_HB.get())
print("D")

print("Begining to receive and send data")

# Run Every 1 Second to Check Bandwidth
bandwidth_t = threading.Thread(target=bandwidth_checker, args=())
bandwidth_t.start()

recv_t_L = []
send_t_L = []
recv_t_HB_L = []
send_t_HB_L = []

for i in range(NUM_NODES):
    if i < OFFSET:
        recv_t = threading.Thread(target=threadedRecv, args=(conn[i], i))
        recv_t_L.append(recv_t)
    elif i > OFFSET:
        recv_t = threading.Thread(target=threadedRecv, args=(conn[i - 1], i))
        recv_t_L.append(recv_t)

for i in range(NUM_NODES):
    if i < OFFSET:
        send_t = threading.Thread(target=threadedSend, args=(sock[i], i))
        send_t_L.append(send_t)
    elif i > OFFSET:
        send_t = threading.Thread(target=threadedSend, args=(sock[i - 1], i))
        send_t_L.append(send_t)
for t in recv_t_L:
    t.start()
for t in send_t_L:
    t.start()

# for i in range(NUM_NODES - 1):
#     # recv_t = threading.Thread(target=threadedRecv, args=(conn[i], addr[i]))
#     # recv_t_L.append(recv_t)
#     # send_t = threading.Thread(target=threadedSend, args=(sock[i], ))
#     # send_t_L.append(send_t)
#     # recv_t.start()
#     # send_t.start()

#     recv_t = threading.Thread(target=heartbeatRecv, args=(conn_HB[i], addr_HB[i]))
#     recv_t_HB_L.append(recv_t)
#     send_t = threading.Thread(target=heartbeatSend, args=(sock_HB[i], ))
#     send_t_HB_L.append(send_t)
#     recv_t.start()
#     send_t.start()

# setup heartbeat thread
# hb_t = threading.Thread(target=heartbeatDetect, args=())
# hb_t.start()

# Initialize thread that reads from standard in
stdInRead_t = threading.Thread(target=stdInRead, args=(p, ))
stdInRead_t.start()

# setup Isis protocol thread
isis_t = threadedIsis()
isis_t.start()


# serial.write('\x03')


# for thread in recv_t_L:
#     thread.join()
# for thread in send_t_L:
#     thread.join()
# for thread in recv_t_HB_L:
#     thread.join()
# for thread in send_t_HB_L:
#     thread.join()
# 
# 
#     

# Thread can still be alive at this point. Do another join without a timeout 
# to verify thread shutdown.
# t.join()

# hb_t.join()
stdInRead_t.join()
isis_t.join()

print("Finished sending and receiveing data")


    