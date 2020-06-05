from apscheduler.schedulers.background import BackgroundScheduler
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
import ntplib 
import time

# pack data to send
import pickle

from isis import *
from process import *
from message import *

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

# NOTE: FOR LOCAL TESTING
vm1, vm2, vm3, vm4, vm5, vm6, vm7, vm8, vm9 = 'localhost', 'localhost', 'localhost', 'localhost', 'localhost', 'localhost', 'localhost', 'localhost', 'localhost'
vmList = [vm1, vm2, vm3, vm4, vm5, vm6, vm7, vm8, vm9]

# NOTE: FOR ONLINE USE
# vm1, vm2, vm3, vm4, vm5, vm6, vm7, vm8, vm9 = '172.22.94.48', '172.22.156.49', '172.22.158.49', '172.22.94.49', '172.22.156.50', '172.22.158.50', '172.22.94.50', '172.22.156.51', '172.22.158.51'
# vmList = [vm1, vm2, vm3, vm4, vm5, vm6, vm7, vm8, vm9]

HOST_SEND = [vm1, vm2, vm3, vm4, vm5, vm6, vm7, vm8, vm9]
PORT_SEND = 3100

SPACING = 100 # defines the number of ports that each process takes
HB_SPACING = 50 # the number of ports we offset real ones from to use for HB

HEARTBEAT_SEND_DELAY = 0.5 # how often send a heartbeat
HEARTBEAT_OBSERVED = [] # Observed timestamps
HEARTBEAT_OBSERVED_OLD = []
HEARTBEAT_RTT = [] # RTTs
HEARTBEAT_MSG_COUNTER = [] # number of heartbeat messages we've had
HEARTBEAT_DEAD = [] # list of dead processes

K = 10 # scale factor


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
NUM_OTHER_PROC_LOCK = threading.Lock()

TO_LOCK = threading.Lock()

# Global sending/receiveing queues
SEND_QUEUE_LIST_LOCK = threading.Lock()
# RECEIVE_LOCK = threading.Lock()

# Heartbeat locks
HEARTBEAT_DEAD_LOCK = threading.Lock()
HEARTBEAT_MSG_COUNTER_LOCK = threading.Lock()
HEARTBEAT_OBSERVED_LOCK = threading.Lock()
HEARTBEAT_RTT_LOCK = threading.Lock()

"""
    Bandwidth Checker
"""
BANDWIDTH = None
BANDWIDTH_LIST = []
BANDWIDTH_TEMP_LIST = []

def bandwidth_checker():   
    BANDWIDTH = 0
    for v in BANDWIDTH_TEMP_LIST:
        BANDWIDTH += v
    BANDWIDTH_LIST.append(BANDWIDTH)
    BANDWIDTH_TEMP_LIST.clear()
    return

scheduler = BackgroundScheduler()
job = scheduler.add_job(bandwidth_checker, 'interval', minutes=1)

"""
    Delay Checker with External Synchronization (NTP)
"""
c = ntplib.NTPClient()
response = c.request('0.north-america.pool.ntp.org')

"""
    Signal handler to deal with stupid process killing
    also we can use
        pkill --signal SIGINT python3
"""
def signal_handler(signal, frame):
        # close the socket here
        # print("exiting")
        # for i in TO:
        #     print(i)
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
                    fd.write(str(a) + "\n")
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
                p.printAccs()
                fd.close()
        sys.exit(0)

"""
    &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
"""
class blockingRecvThread(threading.Thread):
    def __init__(self, inConn, ini, offID):
        self._running_flag = False
        self.stop  = threading.Event()
        threading.Thread.__init__(self, target=self.bRecv, args=(inConn, ini, offID))

    def bRecv(self, conn, i, offID):
        try:
            data = conn.recv()
            connNum = int(chr(data[0]))
            CONN_NUM[connNum] = i
            # print(connNum)
            with conn:
                # print("DEBUG threadedRecv cnt:", i, flush=True)
                # print("DDDDDDDDDDDDDDDDDDDDDDDDD", self.stop)
                while not self.stop.wait(0.000000000001):
                    data = conn.recv()
                    if not data: break
                    
                    # Save bandwidth
                    BANDWIDTH_LIST.append(len(data))

                    # print("DEBUG threadedRecv cnt:", i, flush=True)

                    # recieve a message object and process it
                    result = pickle.loads(data)
                    
                    # with DELIVERED_LOCK and HOLDBACK_LOCK and RREP_DICT_LOCK: # and ACCOUNT_DICT_LOCK and SEQ_LOCK:
                    with RREP_DICT_LOCK and HOLDBACK_LOCK \
                        and DELIVERED_LOCK and DICT_UPDATE_LOCK and SEQ_LOCK and HEARTBEAT_DEAD_LOCK:
                        # with SEQ_LOCK:
                        if result.source not in HEARTBEAT_DEAD:
                            reply = p.recvWrapper(result)
                            if reply != None:
                                if reply.isRRep:
                                    # with SEND_QUEUE_LIST_LOCK:
                                    for j in range(NUM_NODES):
                                        SEND_QUEUE_LIST[j].put(reply)
        except EOFError:
            return
        finally:
            print("RECVKILL", offID, flush=True)
            self.stop.set()

    def terminate(self):
        print("TERMRECV")
        self.stop.set()
class blockingSendThread(threading.Thread):
    def __init__(self, inSock, ini, offID):
        self._running_flag = False
        self.stop  = threading.Event()
        threading.Thread.__init__(self, target=self.bSend, args=(inSock, ini, offID))


    def bSend(self, socket, i, offID):
        try:
            socket.send(bytes(str(OFFSET), 'utf8'))
            while not self.stop.wait(0.000000000001): 
                if SEND_QUEUE_LIST[i].empty() == False:
                    # with SEND_QUEUE_LIST_LOCK:
                    outMsg = SEND_QUEUE_LIST[i].get()
                    if outMsg != None:
                        # print("DEBUG threadedSend:", "srep", outMsg.isSRep, "rrep", outMsg.isRRep, "target", outMsg.target, flush=True)
                        # if outMsg.isSRep:
                        #     print("D#E#B#U#G threadedSend:", "srep", outMsg.isSRep)
                        
                        socket.send(pickle.dumps(outMsg, protocol=4))
                        # print("DEBUG threadedSend::::", i, outMsg.target, outMsg.isRRep, outMsg.isSRep, outMsg.amount, outMsg.targetAcc, outMsg.messageId[20:], flush=True)
        except BrokenPipeError:
            return
        finally:
            print("SENDKILL", offID, flush=True)
            # socket.close()
            # self.stop.set()

    def terminate(self):
        print("TERMSEND")
        self.stop.set()

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
def heartbeatDetect(recv_t_L, connOff, send_t_L, sockOff):
    # observedDelay = []
    # count = []
    # for i in range(len(HEARTBEAT_OBSERVED)):
    #     observedDelay[i] = 0
    #     count[i] = 1
    while True: 
        with HEARTBEAT_OBSERVED_LOCK and HEARTBEAT_RTT_LOCK:
            for i in range(len(HEARTBEAT_OBSERVED)):
                # print(HEARTBEAT_DEAD, i, time.time() - HEARTBEAT_OBSERVED[i], HEARTBEAT_RTT, HEARTBEAT_OBSERVED, HEARTBEAT_OBSERVED_OLD)
                # if time.time() - HEARTBEAT_OBSERVED[i] > K * HEARTBEAT_RTT[i] and HEARTBEAT_OBSERVED_OLD[i] != 0 and HEARTBEAT_RTT[i] != 0:
                if time.time() - HEARTBEAT_OBSERVED[i] > K * HEARTBEAT_RTT[i] and HEARTBEAT_OBSERVED_OLD[i] != 0 and HEARTBEAT_RTT[i] != 0:
                    with HEARTBEAT_DEAD_LOCK:
                        if i not in HEARTBEAT_DEAD:
                            HEARTBEAT_DEAD.append(i)
                            # determine which connection to close
                            for idx in range(len(connOff)):
                                # if connOff[idx] == i:
                                #     recv_t_L[idx].terminate()
                                #     print("recv HB KILL", idx, connOff, HEARTBEAT_DEAD, flush=True)
                            # for idx in range(len(sockOff)):
                                if sockOff[idx] == i:
                                    send_t_L[idx].terminate()
                                    print("send HB KILL", idx, sockOff, HEARTBEAT_DEAD, flush=True)

            # if time.time() - HEARTBEAT_OBSERVED[i] > K * HEARTBEAT_SEND_DELAY and HEARTBEAT_OBSERVED[i] != 0:
            #     with HEARTBEAT_DEAD_LOCK:
            #         if i not in HEARTBEAT_DEAD:
            #             HEARTBEAT_DEAD.append(i)
            #             # determine which connection to close
            #             for idx in range(len(connOff)):
            #                 if connOff[idx] == i:
            #                     recv_t_L[idx].terminate()
            #                     print("recv HB", idx, connOff, HEARTBEAT_DEAD, flush=True)
            #             for idx in range(len(sockOff)):
            #                 if sockOff[idx] == i:
            #                     send_t_L[idx].terminate()
            #                     print("send HB", idx, sockOff, HEARTBEAT_DEAD, flush=True)

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
        
        # assign the time when we receive a heartbeat from process i
        with HEARTBEAT_OBSERVED_LOCK and HEARTBEAT_RTT_LOCK:
            HEARTBEAT_OBSERVED_OLD[splitted[0]] = HEARTBEAT_OBSERVED[splitted[0]]
            HEARTBEAT_OBSERVED[splitted[0]] = time.time()
            # first time we assign equivalnce
            if HEARTBEAT_OBSERVED_OLD[splitted[0]] == 0:
                HEARTBEAT_RTT[splitted[0]] = 0 # HEARTBEAT_OBSERVED[splitted[0]] - HEARTBEAT_OBSERVED_OLD[splitted[0]]
            # not first time average
            else:
                HEARTBEAT_RTT[splitted[0]] += HEARTBEAT_OBSERVED[splitted[0]] - HEARTBEAT_OBSERVED_OLD[splitted[0]]
                HEARTBEAT_RTT[splitted[0]] /= 2

        # print("HB", splitted[0], HEARTBEAT_OBSERVED[splitted[0]], HEARTBEAT_OBSERVED_OLD[splitted[0]], HEARTBEAT_RTT[splitted[0]], HEARTBEAT_DEAD)
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
        print('Connected by (HB) VM', vm, flush=True)
        while True:
            heartbeatParse(data)
            data = conn.recv(BUFFERSIZE)
            if not data: break
    conn.close()

def threadedHBAccept(q, i):
    got = False
    s = None
    while got == False:
        try:
            # print("ACC",PORT_RECV + OFFSET * (NUM_NODES - 1) + i)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((HOST_RECV, PORT_RECV + i))
            s.listen(1)
            conn, addr = s.accept()
            q.put(conn) 
            q.put(addr)
            got = True
        except Exception as e:
            print("Unable to bind socket", PORT_RECV + i)
            time.sleep(random.random())
        finally:
            s.close()
def threadedHBConnect(q, i):
    got = False
    while got == False:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST_SEND[OFFSET], PORT_SEND + i))
            # s.sendall(bytes(str(15), 'utf8'))
            # s.close()
            q.put(s)
            got = True
        except Exception as e:
            print("Failed to connect HB", PORT_SEND + i)
            time.sleep(random.random())

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
            
            # Save bandwidth
            BANDWIDTH_LIST.append(len(data))

            # print("DEBUG threadedRecv cnt:", i, flush=True)

            # recieve a message object and process it
            result = pickle.loads(data)
            
            # with DELIVERED_LOCK and HOLDBACK_LOCK and RREP_DICT_LOCK: # and ACCOUNT_DICT_LOCK and SEQ_LOCK:
            with RREP_DICT_LOCK and HOLDBACK_LOCK and DELIVERED_LOCK and DICT_UPDATE_LOCK and SEQ_LOCK:
                # with SEQ_LOCK:
                reply = p.recvWrapper(result)
                if reply != None:
                    if reply.isRRep:
                        # with SEND_QUEUE_LIST_LOCK and HEARTBEAT_DEAD_LOCK:
                        for j in range(NUM_NODES - len(HEARTBEAT_DEAD)):
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
            # with SEND_QUEUE_LIST_LOCK:
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
def threadedAccept(q, i, num):
    got = False
    s = None
    while got == False:
        try:
            print("Accept failed ", )
            s = Listener((HOST_RECV, PORT_RECV + i))
            conn = s.accept()
            q.put(conn)
            q.put(num)
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
            q.put(IP)
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
                # with HOLDBACK_LOCK and DICT_UPDATE_LOCK and RREP_DICT_LOCK and SEND_QUEUE_LIST_LOCK and SEQ_LOCK:
                with HOLDBACK_LOCK and DICT_UPDATE_LOCK and RREP_DICT_LOCK and SEQ_LOCK:
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
    count = 0
    while True:
        # check if there are any messages that are ready to send
        # an SRep

        with RREP_DICT_LOCK and SEQ_LOCK and HOLDBACK_LOCK and HEARTBEAT_DEAD_LOCK and NUM_OTHER_PROC_LOCK:
            p.assignNumOtherProc(NUM_NODES - 1 - len(HEARTBEAT_DEAD))

            # remove rreps
            # for key, _ in list(p.selfMessageRepDict.items()):
            #     values = p.selfMessageRepDict[key]
            #     tempValues = []
            #     for v in values:
            #         if v.source not in HEARTBEAT_DEAD:
            #             tempValues.append(v)
            #     p.selfMessageRepDict.update({key : tempValues})
                # print(p.selfMessageRepDict[key])

            toDelKeys = []
            for key, _ in list(p.selfMessageRepDict.items()):
                commit = True
                if len(p.selfMessageRepDict[key]) == NUM_NODES - 1 - len(HEARTBEAT_DEAD):
                    for value in p.selfMessageRepDict[key]:
                        if value.source in HEARTBEAT_DEAD:
                            commit = False
                            toDelKeys.append(key)
                            # TO.append("AAAAAAAAAAAAAAAAAAAAAAAAA")
                    # print("DEBUG threadedIsis: ready to send SRep", flush=True)
                    if commit == True:
                        sRep = p.createSenderReply(p.selfMessageRepDict[key][0].messageId, NUM_NODES - 1 - len(HEARTBEAT_DEAD))
                        toDelKeys.append(key)
                        # with SEND_QUEUE_LIST_LOCK:
                        for i in range(len(SEND_QUEUE_LIST)):
                            SEND_QUEUE_LIST[i].put(sRep)
                    # p.printAccs()
            for key in toDelKeys:
                del p.selfMessageRepDict[key]
        

            
            if len(p.holdback) > 0:
                toDelMsg = []
                holdbackCpy = p.holdback
                for i in range(len(holdbackCpy)):
                    m = holdbackCpy[i]
                    # delete messages in holdback that are sourced from dead proc
                    if m.source in HEARTBEAT_DEAD:
                        toDelMsg.append(m)
                    else:
                        break
                p.holdback = list(set(p.holdback)-set(toDelMsg))
                
                holdbackCpy = p.holdback                
                # Reorder Message 
                with SEQ_LOCK:
                    holdbackCpy = p.holdback
                    unsort = p.holdback
                    sort = []
                    lowest = unsort[0]
                    i = 0
                    # for i, m in enumerate(holdbackCpy):
                        # p.holdback = sorted(p.holdback, key = lambda x: x.proposedSeq) 
                        # if m.isDeliverable == True:
                        #     while len(unsort) > 0:
                        #         if unsort[i].proposedSeq < lowest.proposedSeq:
                        #             lowest = unsort[i]
                        #         i += 1
                        #         if i == len(unsort):
                        #             sort.append(lowest)
                        #             unsort.remove(lowest)
                        #             if unsort:
                        #                 lowest = unsort[0]
                        #             i = 0
                    p.holdback.sort(key = lambda x: x.proposedSeq) 
                
                # Now move to deliverables
                holdbackCpy = p.holdback
                toDelMsg = []
                for i in range(len(holdbackCpy)):
                    m = holdbackCpy[i]
                    # print("DEBUG threadedIsis:", i, m.messageId[0:10], m.proposedSeq, m.isDeliverable, flush=True)
                    if m.isDeliverable:
                        toDelMsg.append(m)
                        TO.append((m.source,m.messageId))
                        TIMESTAMPS.append(time.time())
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
                    if count % 100 == 0:
                        print(len(p.holdback), len(TO), print(HEARTBEAT_DEAD), count)
                        # p.printAccs()
                        # for i in TO:
                        #     print(i)
                    count += 1
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
    HEARTBEAT_OBSERVED_OLD.append(0)
    HEARTBEAT_MSG_COUNTER.append(0)
    HEARTBEAT_RTT.append(0)

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
    accept_t = threading.Thread(target=threadedAccept, args=(qAcc, SPACING * OFFSET + i, i))
    accept_t_L.append(accept_t)
    accept_t.start()
 
    # ports to receive heartbeats on
    RECV_PORT_OFFSETS.append(SPACING * OFFSET + i + HB_SPACING)
    accept_t = threading.Thread(target=threadedHBAccept, args=(qAcc_HB, SPACING * OFFSET + i + HB_SPACING))
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
        connect_t = threading.Thread(target=threadedHBConnect, args=(qConn_HB, conn_port + HB_SPACING))
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
connOffsets = []
addr = []
sock = []
sockOffsets = []
for i in range(NUM_NODES - 1):
    print("A")
    conn.append(qAcc.get())
    connOffsets.append(qAcc.get())
    # addr.append(qAcc.get())
    sock.append(qConn.get())
    sockOffsets.append(qConn.get())
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
for i in range(NUM_NODES - 1):
    print("C")
    conn_HB.append(qAcc_HB.get())
    addr_HB.append(qAcc_HB.get())
    sock_HB.append(qConn_HB.get())
print("D")

print("Begining to receive and send data")

recv_t_L = []
send_t_L = []
recv_t_HB_L = []
send_t_HB_L = []

for i in range(NUM_NODES):
    if i < OFFSET:
        # recv_t = threading.Thread(target=threadedRecv, args=(conn[i], i))
        recv_t = blockingRecvThread(conn[i], i, connOffsets[i])
        recv_t_L.append(recv_t)
    elif i > OFFSET:
        # recv_t = threading.Thread(target=threadedRecv, args=(conn[i - 1], i))
        recv_t = blockingRecvThread(conn[i - 1], i, connOffsets[i - 1])
        recv_t_L.append(recv_t)

for i in range(NUM_NODES):
    if i < OFFSET:
        # send_t = threading.Thread(target=threadedSend, args=(sock[i], i))
        send_t = blockingSendThread(sock[i], i, sockOffsets[i])
        send_t_L.append(send_t)
    elif i > OFFSET:
        # send_t = threading.Thread(target=threadedSend, args=(sock[i - 1], i))
        send_t = blockingSendThread(sock[i - 1], i, sockOffsets[i - 1])
        send_t_L.append(send_t)
for t in recv_t_L:
    t.start()
for t in send_t_L:
    t.start()

for i in range(NUM_NODES - 1):
    recv_t = threading.Thread(target=heartbeatRecv, args=(conn_HB[i], addr_HB[i]))
    recv_t_HB_L.append(recv_t)
    send_t = threading.Thread(target=heartbeatSend, args=(sock_HB[i], ))
    send_t_HB_L.append(send_t)
    recv_t.start()
    send_t.start()    
# setup heartbeat thread
hb_t = threading.Thread(target=heartbeatDetect, args=(recv_t_L, connOffsets, send_t_L, sockOffsets))
hb_t.start()

# Initialize thread that reads from standard in
stdInRead_t = threading.Thread(target=stdInRead, args=(p, ))
stdInRead_t.start()

# setup Isis protocol thread
isis_t = threadedIsis()
isis_t.start()

# Run Every 1 Second to Check Bandwidth
scheduler.start()

# serial.write('\x03')


# for thread in recv_t_L:
#     thread.join()
# for thread in send_t_L:
#     thread.join()
for thread in recv_t_HB_L:
    thread.join()
for thread in send_t_HB_L:
    thread.join()    

# Thread can still be alive at this point. Do another join without a timeout 
# to verify thread shutdown.
# t.join()

# hb_t.join()
stdInRead_t.join()
isis_t.join()

print("Finished sending and receiveing data")


    