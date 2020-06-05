import time, threading, socket, sys, socketserver, signal
import config
from sysin import SystemInput
from message import * 
import random
import config as g

# The size of our recv buffers
BUFFERSIZE = 10
# The number of targets we wish to gossip transactions to
NUM_RAND_TARGETS = 1

# NOTE: This is not needed beccause the service
# can always introduce more nodes to us
# number of nodes we can receive gossip messages from
# NUM_GOSSIP_RECEIVERS = 1

# we put our gossip receive handler thread at myPort + offset
GOSSIP_RECV_HANDLER_PORT_OFFSET = 1

# we store our unsent gossip messages here
# TODO: Remove the second part of the tuple in the message
gossipMsgs = []
gossiplock = threading.Lock()

# the list of nodes that have introduced to us
introduceList = []
introduceListLock = threading.Lock()

# we store the list of IPs we have connected here
IP = []
IPLock = threading.Lock()

# list of transaction messages that we have recieved so far
receivedTrans = []
receivedTranslock = threading.Lock()

class myThread(threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.lock = threading.RLock()
        # gossiplock = threading.Lock()
        self.command, self.myIp, self.myName, self.myPort = [None] * 4
        # self.func_on_introduction = self.introducedNodesHandler
        self.targetNum, self.targetIp, self.targetPort = [None] * 3

        # is this the first message we are receiving from the server?
        self.firstMessage = True
        # the previous incomplete message buffer
        self.prevMessage = ""

        # TODO: PROBABLY NEED TO GLOBAL THESE
        # TODO: these are not t.join()ed yet
        # threads that we are using to send gossip
        self.gossipSendThreads = []
        # threads that we are using to receive gossip
        self.gossipRecvThreads = []

        # add yourself as an IP you can access
        with IPLock:
            IP.append(self.myIp)

    """
        config
        Inputs:
            command:
            myIp: Our IP
            myName: Our code name
            myPort: Our base port number
        Outputs:
        Description:
            Updates the variables of our myThread structure
    """
    def config(self, command, myIp, myName, myPort):
        self.command, self.myIp, self.myName, self.myPort = command, myIp, myName, myPort

    def run(self):
        if self.name == "service":
            self.serviceThread()
        elif self.name == "gossiprecvhandler":
            self.gossipRecvHandler()
        elif self.name == "gossipsendhandler":
            self.gossipSendHandler()
        elif self.name == "bwhandler":
            self.bwHandler()
        else:
            print("myThread.run: invalid thread type")
    
    """
        serialDecode
        Inputs:
            data: Input from recv call
        Outputs:
            retmsgs: A list of decoded messages or None
                if the buffer has yet to contain a complete
                message
        Description:
            This function can decode messages that are sent
            incompletely.  It relies on new line to determine
            the end of a message.  After processing it will
            return a list of messages that it was able to decode
            from the new buffer and previously stored buffer
    """
    def serialDecode(self, firstMessage, prevMessage, data):
        # handle the first message which we know must begin
        # from the beginning of data
        if firstMessage == True:
            firstMessage = False
            idx = data.find("\n")
            # current data buffer does not contain one whole message
            # return None
            if idx == -1:
                # print("Did not parse whole message")
                prevMessage += data
                return firstMessage, prevMessage, None
            # otherwise we have at least one full message 
            else:
                # messages to return
                retmsgs = []
                retmsgs.append(data[:idx])
                prevMessage = data[idx + 1:]
                # try to find more messages
                while True:
                    idx = prevMessage.find("\n")
                    if idx == -1:
                        break
                    retmsgs.append(prevMessage[:idx])
                    prevMessage = prevMessage[idx + 1:]
                return firstMessage, prevMessage, retmsgs
        # we need to begin building a message from the end of the
        # last complete one
        else:
            idx = data.find("\n")
            # we have not hit the end of a message yet
            if idx == -1:
                prevMessage += data
                return firstMessage, prevMessage, None
            # we have hit the end of a message
            else:
                retmsgs = []
                retmsgs.append(prevMessage + data[:idx])
                prevMessage = data[idx + 1:]
                # try to find more messages
                while True:
                    idx = prevMessage.find("\n")
                    if idx == -1:
                        break
                    retmsgs.append(prevMessage[:idx])
                    prevMessage = prevMessage[idx + 1:]
                return firstMessage, prevMessage, retmsgs
            
        return firstMessage, prevMessage, None
    
    """
        serviceThread
        Inputs:
        Outputs:
        Description:
            This is our thread which receives messages from
            the service.  It will update introduceList to let
            our gossip send thread to know who to connect to,
            gossip message list to know who to send gossiped messages
            to, and finally update messages it has received from
            the service.
    """
    def serviceThread(self):
        print("Starting " + self.name)
        # Connect to Service.py
        with socket.create_connection((config.SERVICE_HOST, config.SERVICE_PORT)) as sock:
            s = self.command + " " + str(self.myName) + " " + self.myIp + " " + str(int(self.myPort) + GOSSIP_RECV_HANDLER_PORT_OFFSET)
            sock.send(s.encode())
            print("Press Enter to continue") # sock.send('\n'.encode())
            for line in sys.stdin:  
                sock.send(line.encode())  
                break
            
            firstMessage = True
            prevMessage = ""
            
            while True:
                data = sock.recv(BUFFERSIZE).decode()
                # Save bandwidth
                with config.BW_LOCK:
                    config.BW_STACK += len(data)
                
                """ Uncomment below to see received data """
                # print(data)

                firstMessage, prevMessage, retmsgs = self.serialDecode(firstMessage, prevMessage, data)
                if retmsgs != None:
                    for msg in retmsgs:
                        print("serviceThread:", msg)
                        if msg.split()[0] == "INTRODUCE":
                            with introduceListLock:
                                introduceList.append(msg)
                                # print("serviceThread appending: ", msg, introduceList)

                        elif msg.split()[0] == "TRANSACTION":
                            # print("serviceThread: Updating gossipMsgs")
                            with gossiplock:
                                gossipMsgs.append((msg+"\n", []))
                            with receivedTranslock:
                                receivedTrans.append(msg)
                                
                            self.arrivedTimeRecorder(msg)
                            tranmsg = Message(msg.split()[0:6])
                            print("serviceThread: len(gossipMsgs) =", len(gossipMsgs))

                        elif msg.split()[0] == "DIE":
                            # Send system kill sign
                            SystemInput.kill_handler()            
                        else:
                            print("####################")
                            print("serviceThread: GOT AN INCORRECT MESSAGE TYPE")
                            print(retmsgs)
                            print("####################")

                # When connection is lost, it stops receiving data
                if data is "": break 

                # Let main thread know that there are new connections!
                # if msg1.command == "INTRODUCE": self.trigger_on_introduction(msg1)
                
            print("Service Connection End")
            sock.close()
            # Send system kill sign
            SystemInput.kill_handler()            
             

    """
        gossipRecv
        Inputs:
            sock: The socket
            addr: The addr information (IP, port)
        Outputs:
        Description:
            This function is a thread which will
            receive gossiped messages from other nodes
    """
    def gossipRecv(self, sock, addr):
        firstMessage = True
        prevMessage = ""
        while True:
            data = sock.recv(BUFFERSIZE).decode()
            # Save bandwidth
            with config.BW_LOCK:
                config.BW_STACK += len(data)

            firstMessage, prevMessage, retmsgs = self.serialDecode(firstMessage, prevMessage, data)
            if retmsgs != None:
                # print("############")
                # print("RETMSGS: ", retmsgs)
                # print("############")

                # TODO: the problem right now is that the check for if message is not in the
                # TODO: list seems bad
                with receivedTranslock and gossiplock:
                    for msg in retmsgs:
                        # also we need to check if we have received this
                        # message already if we have already received this
                        # message do nothing.  otherwise we need to add
                        # it to the list of messages we need to also gossip
                            if not(msg in receivedTrans):
                                print("gossipRecv from", addr[0], ":", msg)
                                                # make sure that we do not have a connection yet
                                if msg.split()[0] == "INSTANCEID":
                                    splitted = msg.split()
                                    with IPLock:
                                        if addr not in IP:
                                            if False: #addr[0] == self.myIp:
                                                # also create an introduce message to send back our own gossips
                                                i = "INTRODUCE -1 " + "localhost" + " " + str(int(g.BASEPORT) + \
                                                    2 * (int(splitted[1]) - 1) + 1)
                                            else:
                                                # also create an introduce message to send back our own gossips
                                                i = "INTRODUCE -1 " + addr[0] + " " + str(int(g.BASEPORT) + \
                                                    2 * (int(splitted[1]) - 1) + 1)
                                            # add new ip connected to
                                            IP.append(addr)

                                            with introduceListLock:
                                                introduceList.append(i)
                                    continue
                                # NOTE: Due to the changes in gossipSend there
                                # is no more reason to check length of the second argument
                                # this is because each gossipSend now checks its local index
                                # to determine what messages its sent to its peer
                                gossipMsgs.append((msg+"\n", []))
                                receivedTrans.append(msg)
                                print("gossipRecv no dup: ", len(receivedTrans) == len(set(receivedTrans)))

                                # # if there does not exists a tuple in the gossipMsgs
                                # # where the first element (msg) is equivalent to
                                # # the gossip received then we add it to the list of
                                # # messages we also need to gossip
                                # if len(list(filter(lambda x: x[0] == msg+"\n", gossipMsgs))) == 0:
                                #     gossipMsgs.append((msg+"\n", []))
                                # receivedTrans.append(msg)
                                # print("gossipRecv check dup: ", len(receivedTrans) == len(set(receivedTrans)))

                                # NOTE: Saves time when message arrived 
                                self.arrivedTimeRecorder(msg)
        
        return 0

    """
        gossipRecvHandler
        Inputs:
        Outputs:
        DescriptioN:
            This function will listen for connections from
            other nodes.  THen accept the connection, spawn
            gossip receive threads, and finally tell gossip
            send handler to connect back.
    """
    def gossipRecvHandler(self):
        print("gossipRecvHandler: begin")
        # create an INET, STREAMing socket
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # bind the socket to a public host, and a well-known port
        serversocket.bind((socket.gethostbyname(socket.gethostname()), int(self.myPort) + GOSSIP_RECV_HANDLER_PORT_OFFSET))
        # print("gossipRecvHandler:", serversocket)
        # become a server socket
        serversocket.listen(5)

        while True:
            # accept a connection and start a new socket 
            conn, addr = serversocket.accept()
            # print("############################")
            # print("gossipRecvHandler conn:", conn)
            # print("gossipRecvHandler addr:", addr)
            # print("############################")
            # print("gossipRecvHandler:", conn, addr)
            t = threading.Thread(target=self.gossipRecv, args=(conn, addr, ))
            self.gossipRecvThreads.append(t)
            t.start()

            # make sure that we do not have a connection yet
            # with IPLock:
            #     if addr not in IP:
            #         if addr[0] == self.myIp:
            #             # also create an introduce message to send back our own gossips
            #             i = "INTRODUCE -1 " + "localhost" + " " + str(int(self.myPort) + 1)
            #         else:
            #             # also create an introduce message to send back our own gossips
            #             i = "INTRODUCE -1 " + addr[0] + " " + str(int(self.myPort) + 1)
            #         # add new ip connected to
            #         IP.append(addr)

            #         with introduceListLock:
            #             introduceList.append(i)

    """
        gossipSend
        Inputs:
            intro: An introduction message
        Outputs:
        Description:
            This function creates a socket to connect to our gossip recv
            handler on another node.  Then using that socket send out
            messages that we need to gossip out
    """
    def gossipSend(self, intro):
        splitted = intro.split()
        name, ip, port = splitted[1], splitted[2], splitted[3] 
        # print("gossipSend intro:", splitted)
        sock = socket.create_connection((ip, int(port)))

        # NOTE: Major change here commented out code represents old version
        # The problem is as follows.
        #   - Because we are sending to a specific number of random targes
        #   it is possible that you do not send a gossip message to a new node
        #   but rather to the node that this message originated from or another node
        #   that has this message.
        #       - therefore it is possible that the message gets dumped and ignored.
        #
        # To solve this problem, we only send gossip messages if the current thread
        # has not sent it to yet. In this vein, each gossipSend thread needs to keep
        # a local version of the gossipMsgs global variable. On every iteration it must...
        #   1. Check if there are new messages it needs to gossip
        #   2. If there are new messages to gossip, send them
        #   3. update its local list with the sent gossip messages
        #
        # This ensures that for a specific message we will only send a gossip message
        # once to all connected nodes.  We also must make sure to never clear the global
        # gossip list.  Because if a new node connects to us in the mean time we need to
        # ensure that it can get all previous histories of the gossips

        localGossipMsgs = []
        prevIndexToGossipMsgs = 0

        # send our first message. this contains the instance id.
        # this tells us what port to connect to as we are now spacing instances our 
        # from our base port.
        instance = "INSTANCEID " + str(g.INSTANCEID) + "\n"
        sock.send(instance.encode())

        while True:
            with gossiplock:
                # there are new messages to gossip
                if len(gossipMsgs) > prevIndexToGossipMsgs:
                    # print("gossipSend:", ip, len(gossipMsgs), prevIndexToGossipMsgs)
                    # copy over new messages
                    localGossipMsgs = gossipMsgs[prevIndexToGossipMsgs : len(gossipMsgs)]
                    # update our local gossip index so we know where to
                    # begin sending from next time
                    prevIndexToGossipMsgs = len(gossipMsgs)
                    # proceed to send all the messages that we have in our localGossipMsgs
                    for msg in localGossipMsgs:
                        try:
                            # print("gossipSend to:", ip, msg)
                            sock.send(msg[0].encode())
                        except:
                            # Connection Lost
                            print("Connection Lost to ", ip + ":" + port)
                            break
                    # clear all the messages we have sent
                    localGossipMsgs = []

        # # introduce yourself to the gossip receiver
        # # s = self.command + " " + str(self.myName) + " " + self.myIp + " " + self.myPort + "\n"
        # # print("sendGossip:", s)
        # # sock.send(s.encode())
        # while True:
        #     with gossiplock:
        #         if len(gossipMsgs) > 0:
        #             # print("gossipSend:", gossipMsgs)
        #             if sock not in gossipMsgs[0][1]:
        #                 # print("Sending gossip: ", gossipMsgs[0][0])
        #                 try:
        #                     sock.send(gossipMsgs[0][0].encode())
        #                 except:
        #                     # Connection Lost
        #                     print("Connection Lost to ", ip + ":" + port)
        #                     break

        #                 if len(gossipMsgs[0][1]) + 1 > NUM_RAND_TARGETS:
        #                     gossipMsgs.pop(0)
        #                 else:
        #                     gossipMsgs[0][1].append(sock)
    """
        gossipSendHandler
        Inputs:
        Outputs:
        Description:
            This is the gossip send handler.  It will check for
            introudce messages and connect to them.
    """
    def gossipSendHandler(self):
        print("gossipSendHandler: begin")
        while True:
            # sleep a random amount of time
            time.sleep(random.random())

            with introduceListLock:
                # if we know that we can connect to some gossiop receiver
                if len(introduceList) > 0:
                    for intro in introduceList:
                        print("gossipSendHandler: ", introduceList)
                        # start a new gossipSend thread
                        t = threading.Thread(target=self.gossipSend, args=(intro, ))
                        self.gossipSendThreads.append(t)
                        t.start()
                    introduceList.clear()
    
    """
        bwHandler
        Inputs:
        Outputs:
        Description:
            This is bandwidth handler. It records bandwidth every second.
    """
    def bwHandler(self):
        print("bwHandler: begin")
        while True:
            # It runs every 1 second
            time.sleep(1)
            with config.BW_LOCK:
                # Record bandwidth
                config.BW.append(config.BW_STACK)
                # Clear bandwidth
                config.BW_STACK = 0 
    
    """
        arrivedTimeRecorder
        Inputs: msg
        Outputs:
        Description:
            Records time when message arrived
    """
    def arrivedTimeRecorder(self, msg):
        txTime = time.time() 
        txId = msg.split()[2]
        config.MSG_ARRIVED_TIME.update({txId : txTime})