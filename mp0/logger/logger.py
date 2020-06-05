class Node:
    """
        __init__
        Inputs:
            None
        Outputs:
            None
        Description:
            This constructor assigns a default value of -1 to nodeId
            and also assigns and emtpy array of data
    """
    def __init__(self):
        self.nodeId = -1
        self.data = []
        # this tells split how many times to split using space
        self.tupleElements = 1
    
    """
        assignNode
        Inputs:
            nodeIdIn: Input node ID number
        Outputs:
            None
        Description:
            This assigns a nodeId to this instance of node
    """
    def assignNode(self, nodeIdIn):
        self.nodeId = nodeIdIn

    """
        addData
        Inputs:
            stringIn: The string of input data
        Outputs:
            None
        Description:
            This adds data into our data array
            Our data has format
                time data1 data2 data3
            The number of elements in our tuple is determined
            by self.tupleElements
    """
    def addData(self, stringIn):
        """
        Example input data:

        1579666871.892629 58f7eb5b7d25906471ff1e1b8847c891f5b275aecd71451a8c040fe0fd2011a0

        Format:
        time data
        """
        if len(self.data) == 0:
            print(stringIn[2:-3].split(' ', maxsplit=self.tupleElements)[0] + " - node" + str(self.nodeId) + " connected")
            #self.data.append(stringIn[2:-3].split(' ', maxsplit=self.tupleElements)[2:-1])
            self.data.append(stringIn[2:-3].split(' ', maxsplit=self.tupleElements))
            self.data[-1].append(time.time())
            self.data[-1].append(len(stringIn))
        else:
            self.data.append(stringIn[2:-3].split(' ', maxsplit=self.tupleElements))
            self.data[-1].append(time.time())
            self.data[-1].append(len(stringIn))
            # TODO: This should be parametrized to accomodat the number of data ele
            print(self.data[-1][0] + " node" + str(self.nodeId) + " " + self.data[-1][1])

# TODO: Cluster needs to have a way to assert that no dup nodes
class Cluster:
    def __init__(self):
        self.nodeDictByAddress = defaultdict(int)  # Dictionary without error
        # self.nodeDict = {}
    
    def addNodeByAddress(self, addr, idNum):
        self.nodeDictByAddress[addr] = idNum    # Assign unique node number to each ip address

    # def addNode(self, nodeIdIn):
    #     assert(nodeIdIn not in self.nodeDict)
    #     if nodeIdIn not in self.nodeDict:
    #         self.nodeDict[nodeIdIn] = "Connected"
    #     else:
    #         print("Node already exists")

import socket
from _thread import *
import threading 
from collections import defaultdict
import signal
import sys
import time

def signal_handler(signal, frame):
        # close the socket here
        print("exiting")
        sys.exit(0)

def threaded(conn, addr, nodeId):
    BUFFERSIZE = 1024
    node = Node()
    node.nodeId = nodeId

    with conn:
        print('Connected by', addr)     
        while True:
            data = conn.recv(BUFFERSIZE)
            if not data: break
            node.addData(repr(data))
        conn.close()
    print("Node " + str(nodeId) + " has terminated.  Dumping logs to node" + str(nodeId) + ".txt.")

    # Dump node data to file output
    with open("node" + str(nodeId) + ".txt", "a") as fd:
        for entry in node.data:
            for ele in entry:
                fd.write(str(ele) + " ")
            fd.write('\n')
        fd.close()
    print("Node " + str(nodeId) + " dumping has finished.")
    return
    

def main(numNodes):
    HOST = ''
    PORT = 1234
    uniqueNum = 0
    cluster = Cluster()
    threads = []

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(1)

        while uniqueNum < numNodes:
            conn, addr = s.accept()
            addr = addr[0] # Use only ip address. addr originally is ('172.22.158.49', 54914)  

            if cluster.nodeDictByAddress.get(addr) is None:
                uniqueNum += 1 
                cluster.addNodeByAddress(addr, uniqueNum)      
                nodeId = uniqueNum
            else:
                nodeId = cluster.nodeDictByAddress.get(addr)
            # start_new_thread(threaded, (conn, addr, nodeId, )) 
            t = threading.Thread(target=threaded, args=(conn, addr, nodeId, ))
            t.start()
            threads.append(t)
    return uniqueNum

# def graph(numNodes):

"""
    MAIN LOOP
"""
# Input into main as the number of nodes we wish tro log
if len(sys.argv) > 1:
    numNodes = int(sys.argv[1])
else:
    print("Enter one argument specifying the number of nodes you wish to log.")

signal.signal(signal.SIGINT, signal_handler)
unique = main(numNodes)

while True:
    if threading.active_count() == 1:
        break
    else:
        time.sleep(2)

print("Done logging ", numNodes, " nodes.")

"""
# Echo server program
import socket

HOST = ''                # Symbolic name meaning all available interfaces
PORT = 1234              # Arbitrary non-privileged port
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    conn, addr = s.accept()
    with conn:
        print('Connected by', addr)
        while True:
            data = conn.recv(1024)
            if not data: break
            conn.sendall(data)
"""
