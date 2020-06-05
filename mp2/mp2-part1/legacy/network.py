import time, threading, socket, sys, socketserver
import config
from sysin import SystemInput
from message import * 
from threadFunc import *

# The size of our recv buffers
BUFFERSIZE = 10
# The number of targets we wish to gossip transactions to
NUM_RAND_TARGETS = 1

gossipMsgs = []
gossiplock = threading.Lock()

"""
    NETWORK
        
        conn1(): connects with service.py
        conn2(): run server
        conn3(): connets with introduced nodes
        
        Description: 
            This thread connects to service.py and receives data
            The receiving data includes 
                INTRODUCE
                TRANSACTION
"""
class myThread(threading.Thread):
    def __init__(self, threadID, name, counter):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.counter = counter
        self.lock = threading.RLock()
        # gossiplock = threading.Lock()
        self.receivedTranslock = threading.Lock()
        self.command, self.myIp, self.myName, self.myPort = [None] * 4
        self.func_on_introduction = self.introducedNodesHandler
        self.targetNum, self.targetIp, self.targetPort = [None] * 3

        # is this the first message we are receiving from the server?
        self.firstMessage = True
        # the previous incomplete message buffer
        self.prevMessage = ""
        # list of transaction messages that we have recieved so far
        self.receivedTrans = []
        # backlog of transaction messages we need to gossip
        # gossipMsgs = []

    def config(self, command, myIp, myName, myPort):
        self.command, self.myIp, self.myName, self.myPort = command, myIp, myName, myPort
    
    def targetConfig(self, targetNum, targetIp, targetPort):
        self.targetNum, self.targetIp, self.targetPort = targetNum, targetIp, targetPort

    def run(self):
        if self.threadID == 1:
            self.conn1()
        elif self.threadID == 2:
            self.conn2()
        elif self.threadID >= 3:
            self.conn3()

    def serialDecode(self, data):
        # handle the first message which we know must begin
        # from the beginning of data
        if self.firstMessage == True:
            self.firstMessage = False
            idx = data.find("\n")
            # current data buffer does not contain one whole message
            # return None
            if idx == -1:
                # print("Did not parse whole message")
                self.prevMessage += data
                return None
            # otherwise we have at least one full message 
            else:
                # messages to return
                retmsgs = []
                retmsgs.append(data[:idx])
                self.prevMessage = data[idx + 1:]
                # try to find more messages
                while True:
                    idx = self.prevMessage.find("\n")
                    if idx == -1:
                        break
                    retmsgs.append(self.prevMessage[:idx])
                    self.prevMessage = self.prevMessage[idx + 1:]
                return retmsgs
        # we need to begin building a message from the end of the
        # last complete one
        else:
            idx = data.find("\n")
            # we have not hit the end of a message yet
            if idx == -1:
                self.prevMessage += data
                return None
            # we have hit the end of a message
            else:
                retmsgs = []
                retmsgs.append(self.prevMessage + data[:idx])
                self.prevMessage = data[idx + 1:]
                # try to find more messages
                while True:
                    idx = self.prevMessage.find("\n")
                    if idx == -1:
                        break
                    retmsgs.append(self.prevMessage[:idx])
                    self.prevMessage = self.prevMessage[idx + 1:]
                return retmsgs
            
        return None
    ''' connects with service.py '''
    def conn1(self):
        print("Starting " + self.name)
        # Connect to Service.py
        with socket.create_connection((config.SERVICE_HOST, config.SERVICE_PORT)) as sock:
            
            s = self.command + " " + str(self.myName) + " " + self.myIp + " " + self.myPort
            sock.send(s.encode())
            print("Press Enter to continue") # sock.send('\n'.encode())
            for line in sys.stdin:  
                sock.send(line.encode())  
                break
            
            while True:
                data = sock.recv(BUFFERSIZE).decode()
                """ Uncomment below to see received data """
                # print(data)

                retmsgs = self.serialDecode(data)
                if retmsgs != None:
                    for msg in retmsgs:
                        print(msg)
                        if msg.split()[0] == "INTRODUCE":
                            intromsg = Message(msg.split()[0:4])
                            self.trigger_on_introduction(intromsg)
                        elif msg.split()[0] == "TRANSACTION":
                            print("conn1: Updating gossipMsgs")
                            with gossiplock:
                                gossipMsgs.append((msg, []))
                            with self.receivedTranslock:
                                self.receivedTrans.append(msg)
                            tranmsg = Message(msg.split()[0:6])
                            print("conn1: ", len(gossipMsgs))

                # When connection is lost, it stops receiving data
                if data is "": break 

                # Let main thread know that there are new connections!
                # if msg1.command == "INTRODUCE": self.trigger_on_introduction(msg1)
                
            print("Service Connection End")
            sock.close()
            SystemInput.signal_handler # Send system kill sign
        print("Exiting " + self.name)


    '''run server'''
    def conn2(self):
        with socketserver.ThreadingTCPServer((self.myIp, int(self.myPort)), LoggerHandler) as server:
            
            print("Server Thread Running")
            # Add node itself to alive nodes list #
            s = "INTRO_CONNECT" + " " + self.myIp + " " + str(self.myName) + " " + self.myPort
            msg = Message(s.split())
            config.NODES.update({msg.nodeNum: msg})
            server.serve_forever()
            print("Server Closing")

    '''Connects with introduced clients and sends gossiped messages'''
    def sendGossip(self):
        sock = socket.create_connection((self.targetIp, self.targetPort))  
        # with socket.create_connection((self.targetIp, self.targetPort)) as sock:
        s = self.command + " " + str(self.myName) + " " + self.myIp + " " + self.myPort
        print("sendGossip:", s)
        sock.send(s.encode())
        
        while True:
            # print("BBBB", len(gossipMsgs))
            with gossiplock:
                if len(gossipMsgs) > 0:
                    # TODO: This currently only checks the beginning of the list
                    # TODO: This should check the whole list for all available gossip
                    if sock not in gossipMsgs[0][1]:
                        print("Sending gossip: ", gossipMsgs[0][0])
                        sock.send(gossipMsgs[0][0].encode())
                        # TODO: This should be > not ==
                        if len(gossipMsgs[0][1]) + 1 == NUM_RAND_TARGETS:
                            gossipMsgs.pop(0)
                        else:
                            gossipMsgs[0][1].append(sock)

    def recvGossip(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((socket.gethostname(), 8080))
        sock.listen()
        print("recvGossip:")
        while True:
            data = sock.recv(1024).decode()
            print("handle gossip: ", data)

        
    def conn3(self):
        print("Starting new thread. Name: " + self.name)
        
        self.lock.acquire()
        if len(config.NODES) > 0:
            self.lock.release()

            # try:
            sendgossip_t = threading.Thread(target=self.sendGossip, args=())
            recvgossip_t = threading.Thread(target=self.recvGossip, args=())

            sendgossip_t.start()
            recvgossip_t.start()
            sendgossip_t.join()
            recvgossip_t.join()
                    # print(gossipMsgs)

                    # print("A")
                    # data = sock.recv(1024).decode()
                    
                    # When connection is lost, it stops receiving data
                    # sock.send(s.encode())
                    # if data is "": break 
                    # print(data)                   
            # except:
            #     pass

            print("Connection to " + str(self.targetNum) +" End")
            
            # Need to drop it in alive node list
            drop_node_handler(self.targetNum)
            
            # sock.close()
        print("Exiting " + self.name)
    
    def trigger_on_introduction(self, msg):
        self.func_on_introduction(msg)

    def introducedNodesHandler(self, msg):
        # print("INTRODUCE event triggered by thread %s" % self.threadID)
        
        with self.lock:
            config.NODES.update({msg.nodeNum: msg})
            print("node" + str(msg.nodeNum) + " introduced. Connecting to.... node" + str(msg.nodeNum))
            print(config.NODES.keys())
            func_on_intro_thread(msg, self.myName, self.myIp, self.myPort)