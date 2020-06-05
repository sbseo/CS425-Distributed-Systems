import time, threading, socket, sys, socketserver, signal
import config
from sysin import SystemInput
from message import * 
import random
import config as g
import hashlib as hl
from collections import OrderedDict
import account

# global account dictoinary
acc = account.Account()

# The size of our recv buffers
BUFFERSIZE = 1024
# The number of targets we wish to gossip transactions to
NUM_RAND_TARGETS = 1

# we put our gossip receive handler thread at myPort + offset
GOSSIP_RECV_HANDLER_PORT_OFFSET = 1

VERIFICATION_TIMEOUT = 10

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

# list of committed messages in our solved blocks
solvedBlocksTrans = []
solvedBlocksTransLock = threading.Lock()

# number of maximum messages per block
MAX_TX_PER_BLOCK = 2000

# number of blocks before we consider confirmed
CONFIRMED_BLOCK_OFFSET = 1000
BACKWARDS_COUNT = 10

# blockHeight
blockHeight = 0
blockHeightLock = threading.Lock()

# flag determining if we need to catch up
stopMining = False
stopMiningLock = threading.Lock()

# blocks to solve
# key: (hash, block height)
# value: block
toSolveBlocksDict = OrderedDict()
toSolveBlocksDictLock = threading.Lock()

# solved block
# key: (hash, blockheight)
# value: blocks
solvedBlocksDict = OrderedDict()
solvedBlocksDictLock = threading.Lock()

# blocks to verify
# key: (hash, blockheight)
# value: block
toVerifyBlocksDict = OrderedDict()
toVerifyBlocksDictLock = threading.Lock()
pendingVerifBlockDict = OrderedDict()
pendingVerifBlockDictLock = threading.Lock()

# block requests
# key: (ip,port)
# value: str(REQUESTBLOCK blockHeight)
blockRequestsDict = OrderedDict()
blockRequestsDictLock = threading.Lock()

# this stores the ip and port we are using to do requests
rebuilderThreadID = None
rebuilderThreadIDLock = threading.Lock()

# reply blocks
# key (ip, port)
# value: REQUESTEDBLOCK block
replyBlocksDict = OrderedDict()
replyBlocksDictLock = threading.Lock()

# if we are stopped mining we need to queue the requests
replyBlocksSet = set()
replyBlocksSetLock = threading.Lock()


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

        self.genesisBlock = True

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

    @staticmethod
    def reachbility(self):
        temp = list()
        for key in solvedBlocksDict.keys():
            for tx in self.getTxFromBlock(self.getBlockWOSolution(solvedBlocksDict[key])):
                print(tx[2])
                temp.append(tx[2])
        return temp
        

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
        genBlock
        Inputs:
            transLi: A list of transmissions to put into a block
        Outputs:
            block: A block
        Description:
            This function generates a block given a list of input transactions.
            The format of this block is as follows
                PREVHASH hash BLOCKHEIGHT blockHeight TRANSACTION __ TRANSACTION __ ... SOLUTION\n
            The solution will be added after we receive a SOLVED

    """
    def genBlock(self, transLi):
        """
            TODO: THIS CHECKING METHOD OF THE TRANSACTIONS IS FAULTY!!! WE CANNOT DO THIS
            TODO: UNTIL WE HAVE REACHED A DEPTH OF AT LEAST 6!!!
            TODO: MAYBE IT WOULD BE BETTER TO ADD A TEMP DICT AND A FINAL DICT?
        """
        # print("genBlock transLi:", transLi)`
        # print("genBlock solvedBlockTrans:", solvedBlocksTrans)`

        global blockHeight

        # contains the messages that have been able to be added to a block
        # therefore we remove them from our transmission block list
        toRemove = []

        if len(toSolveBlocksDict.keys()) > 0:
            for block in toSolveBlocksDict.values():
                blockToSolveTxs = self.getTxFromBlock(block)
                # print("genBlock toSolve txs:", blockToSolveTxs)
                for tx in blockToSolveTxs:
                    if tx in transLi:
                        if tx not in toRemove:
                            toRemove.append(tx)
        for msg in transLi:
            if msg in solvedBlocksTrans:
                if msg not in toRemove:
                    toRemove.append(msg)
        for msg in toRemove:
            transLi.remove(msg)
        # print("&^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        # print(solvedBlocksTrans)
        # print()
        # print()
        # print(solvedBlocksDict)
        # print()
        # print()
        # print(toRemove)
        # print()
        # print()
        # print(transLi)

        # print("*^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        transLi = list(set(transLi))
        # if we are genesis block the prev hash is "genesis "
        if self.genesisBlock == True:
            block = "PREVHASH 0 BLOCKHEIGHT " + str(blockHeight) + " "
            
            for idx in range(len(transLi)):
                msg =  transLi[idx].split()
                # the transaction is valid AKA does not zero account
                if acc.checkValidTransaction(int(msg[3]), int(msg[4]), int(msg[5])):
                    # add it to the block
                    # if it is the last transaction in our list, terminate with "\n"
                    # if idx == len(transLi) - 1:
                    #     block += transLi[idx]
                    # else:
                    #     block += transLi[idx] + " "
                    # acc.updateBalance(int(msg[3]), int(msg[4]), int(msg[5]))
                    # toRemove.append(transLi[idx])
                    
                    block += transLi[idx] + " "
                    acc.updateBalance(int(msg[3]), int(msg[4]), int(msg[5]))
                    toRemove.append(transLi[idx])
                else:
                    print("FAILED:", transLi[idx])
                    gossipMsgs.append(transLi[idx]+"\n")
            # if there were valid messages
            if block != "PREVHASH 0 BLOCKHEIGHT 0 ":
                block = block[:-1]
                # hash the whole block after converting to bytes
                h = hl.sha256(block.encode()).hexdigest()
                self.genesisBlock = False
                # update the block height
                # blockHeight += 1
                return block, h, toRemove
            else:
                # assert toRemove == []
                return None, None, toRemove
        # not a genesis block
        else:
            # grab the previous block and hash it
            flag = False
            prevkey = None
            for key in solvedBlocksDict.keys():
                if key[1] == blockHeight - 1:
                    flag = True
                    prevkey = key
            # print("FLAG", flag, prevkey)
            if flag:
                prevhash = hl.sha256(solvedBlocksDict[prevkey].encode()).hexdigest()
                block = "PREVHASH " + str(prevhash) + " BLOCKHEIGHT " + str(blockHeight) + " "

                for idx in range(len(transLi)):
                    msg =  transLi[idx].split()
                    # print("DSFDS", acc.checkValidTransaction(int(msg[3]), int(msg[4]), int(msg[5])), msg)
                    if acc.checkValidTransaction(int(msg[3]), int(msg[4]), int(msg[5])):
                        # if idx == len(transLi) - 1:
                        #     block += transLi[idx]
                        # else:
                        block += transLi[idx] + " "
                        acc.updateBalance(int(msg[3]), int(msg[4]), int(msg[5]))
                        toRemove.append(transLi[idx])
                    else:
                        print("FAILED:", transLi[idx])
                        gossipMsgs.append(transLi[idx]+"\n")
                    # else:
                    #     print("you cant get negative money")
                if block != "PREVHASH " + str(prevhash) + " BLOCKHEIGHT " + str(blockHeight) + " ":
                    block = block[:-1]
                    h = hl.sha256(block.encode()).hexdigest()
                    return block, h, toRemove
                else:
                    # assert toRemove == []
                    return None, None, toRemove
            else:
                return None, None, toRemove
    
    def getBlockPrevHash(self, block):
        return block.split()[1]
    def getBlockHeight(self, block):
        return block.split()[3]
    def getBlockSolution(self, block):
        return block.split()[-1]
    def getBlockWOSolution(self, block):
        return " ".join(block.split()[:-1])
    """
        getTxFromBlock
        Inputs:
            block: A block
        OUtputs:
            txs: A list of transactions which occur within a block
        Description:
            This returns a list of transactions from a block
    """
    def getTxFromBlock(self, block):
        global receivedTrans

        splitted = block.split()
        splitted = splitted[4:]
        splitted = " ".join(splitted)
        splitted = splitted.split("TRANSACTION ")
        rettx = []
        for tx in splitted:
            if tx != '':
                if tx[-1] == ' ':
                    rettx.append("TRANSACTION " + tx[:-1])
                else:
                    rettx.append("TRANSACTION " + tx)
        return rettx

    # def getTxFromBlock(self, block):
    #     splitted = block.split()
        
    #     # block always has the form PREVHASH ____ BLOCKHEIGHT ____ TRANS ... solution
    #     # therefore we are ble to ignore the first 4 items
    #     splitted = splitted[4:]
    #     txs = []
    #     currtx = ""
    #     cnt = 0 # this is a counter for the number of elements in the 
    #     buildingtx = False
    #     for ele in splitted:
    #         if cnt == 6:
    #             buildingtx = False
    #             cnt = 0
    #             txs.append(currtx)
    #             currtx = ""
    #         # new transaction detected
    #         if ele == "TRANSACTION" and cnt == 0:
    #             currtx += ele
    #             cnt += 1
    #             buildingtx = True
    #         elif cnt < 6 and buildingtx == True:
    #             currtx += " " + ele
    #             cnt += 1
    #     return txs
    def getBlockFromRequestedBlock(self, rb):
        return " ".join(rb.split()[1:])
    def getKeyViaHash(self, h, name):
        if name == "toSolveBlocksDict":
            for key in toSolveBlocksDict.keys():
                if key[0] == h:
                    return key
            return None
        return None
    def getKeyViaBlockHeight(self, bh, name):
        if name == "solvedBlocksDict":
            for key in solvedBlocksDict:
                if key[1] == bh:
                    return key
            return None
    def getBlockHeightFromRequestBlock(self, msg):
        return msg.split()[1]
    def moveVerifiedIntoSolved(self, todelverifkeys):
        global receivedTrans
        # returns the matching pair in a
        # [i for i in a.keys() for j in b.keys() if i[1] == j[1]]
        # print(solvedBlocksDict)
        # print(toVerifyBlocksDict)

        solvedkeydel = []
        for delKey in todelverifkeys:
            for solvedKey in solvedBlocksDict.keys():
                if delKey[1] == solvedKey[1]:
                    solvedTx = self.getTxFromBlock(self.getBlockWOSolution(solvedBlocksDict[solvedKey]))
                    verifTx = self.getTxFromBlock(self.getBlockWOSolution(toVerifyBlocksDict[delKey]))
                    # >>> x = [1,2,3]
                    # >>> y = [2,3,4]
                    # >>> [item for item in x if item not in y]
                    # [1]
                    print("###SOLVEDTX:", solvedTx)
                    print("####VERIFTX:", verifTx)
                    rtx = [tx for tx in solvedTx if tx not in verifTx]
                    print("####RTX:", verifTx)
                    for t in rtx:
                        receivedTrans.append(t)
                        gossipMsgs.append(t+"\n")
                        solvedBlocksTrans.remove(t)
                    solvedkeydel.append(solvedKey)
                # else:
                #     solvedTx = self.getTxFromBlock(self.getBlockWOSolution(solvedBlocksDict[solvedKey]))
                #     if solvedTx:
                #         print("SOLVEDTX", solvedTx)
                #         for tx in solvedTx:
                #             if tx in solvedBlocksTrans:
                #                 solvedBlocksTrans.remove(tx)
                #         solvedkeydel.append(solvedKey)
        for key in solvedkeydel:
            del solvedBlocksDict[key]
        for key in todelverifkeys:
            verifTx = self.getTxFromBlock(self.getBlockWOSolution(toVerifyBlocksDict[delKey]))
            for tx in verifTx:
                solvedBlocksTrans.append(tx)
            solvedBlocksDict.update({key : toVerifyBlocksDict[key]})
        for key in todelverifkeys:
            del toVerifyBlocksDict[key]   
        print("()()()())()()()()()", solvedBlocksDict)     
        print("()()()())()()()()()", toVerifyBlocksDict)     

        # solvedKeysWithOverlappingTransactions = set()
        # cnt = 0
        # for verifKey in todelverifkeys:
        #     verifyTxs = self.getTxFromBlock(self.getBlockWOSolution(toVerifyBlocksDict[verifKey]))
        #     for solvedKey in sorted(solvedBlocksDict.keys(), key=lambda x : x[1]):
        #         if cnt < CONFIRMED_BLOCK_OFFSET and solvedKey[1] < verifKey[1]:
        #             solvedTxs = self.getTxFromBlock(self.getBlockWOSolution(solvedBlocksDict[solvedKey]))
        #             """
        #                 TODO: THIS LOGIC IS INCORRECT WE DONT RESTORE TRANSACTIONS
        #                 NOTE: Not sure if this works
        #             """
        #             for tx in solvedTxs:
        #                 if tx not in verifyTxs:
        #                     if tx not in receivedTrans and tx not in solvedBlocksTrans:
        #                         print("if tx not in receivedTrans:", tx)
        #                         receivedTrans.append(tx)
        #                     gossipMsgs.append(tx+"\n")
        #                     solvedKeysWithOverlappingTransactions.add(solvedKey)
        #                     # break
        #             receivedTrans = list(set(receivedTrans))
        #             cnt += 1
        # # for key in solvedKeysWithOverlappingTransactions:
        # #     del solvedBlocksDict[key]
        # verifkeyssamebh = [kv for kv in todelverifkeys for ks in solvedBlocksDict.keys() if kv[1] == ks[1]]
        # solvedkeyssamebh = [ks for ks in solvedBlocksDict.keys() for kv in todelverifkeys if kv[1] == ks[1]]
        # # print("moveVerifiedIntoSolved SOLVED", solvedBlocksDict.items())

        # print("moveVerifiedIntoSolved", verifkeyssamebh, solvedkeyssamebh)
        # # if len(verifkeyssamebh) == 0 and len(solvedkeyssamebh) == 0:
        # #     print("AAAAAAAAAAAAAAAAAAAAAAAAAAAA")
        # #     for key in todelverifkeys:
        # #         solvedBlocksDict.update( {key : toVerifyBlocksDict[key]} )
        # #     for key in todelverifkeys:
        # #         del toVerifyBlocksDict[key]
        # # else:
        # for keySolved in solvedkeyssamebh:
        #     for keyVerif in verifkeyssamebh:
        #         if keyVerif[1] == keySolved[1]:
        #             verifBlockTx = self.getTxFromBlock(self.getBlockWOSolution(toVerifyBlocksDict[keyVerif]))
        #             solvedBlockTx = self.getTxFromBlock(self.getBlockWOSolution(solvedBlocksDict[keySolved]))
        #             for tx in solvedBlockTx:
        #                 if tx not in verifBlockTx:
        #                     if tx not in receivedTrans:
        #                         print("if tx not in receivedTrans:", receivedTrans)
        #                         receivedTrans.insert(0, tx)
        #     receivedTrans = list(set(receivedTrans))
        #     del solvedBlocksDict[keySolved]
        # for key in todelverifkeys:
        #     solvedBlocksDict.update( {key : toVerifyBlocksDict[key]} )
        # for key in todelverifkeys:
        #     del toVerifyBlocksDict[key]
    def undoBalance(self, todelverifkeys):
        if len(solvedBlocksDict.keys()) > 0:
            # with acc.accDictLock:
            #     print("(((((((((((((((((((((((((((((((")
            #     print(acc.accDict)
            #     print("(((((((((((((((((((((((((((((((")
            solvedkeyssamebh = [ks for ks in solvedBlocksDict.keys() for kv in todelverifkeys if kv[1] == ks[1]]
            for key in solvedkeyssamebh:
                txs = self.getTxFromBlock(self.getBlockWOSolution(solvedBlocksDict[key]))
                if len(txs) > 0:
                    for tx in txs:
                        splitted = tx.split()
                        source = int(splitted[3])
                        dest = int(splitted[4])
                        amount = int(splitted[5])
                        # TODO: do we need to check if we go negative?
                        acc.updateBalance(dest, source, -1 * amount)
            # with acc.accDictLock:
            #     print("(((((((((((((((((((((((((((((((")
            #     print(acc.accDict)
            #     print("(((((((((((((((((((((((((((((((")
        # for keys in solvedkeyssamebh:
        #     del solvedBlocksDict[key]
    def rebuildAccs(self):
        acc.resetBalances()
        for key in sorted(solvedBlocksDict.keys(), key=lambda x : x[1]):
            block = solvedBlocksDict[key]
            for tx in self.getTxFromBlock(self.getBlockWOSolution(block)):
                splitted = tx.split()
                # print("rebuildAccs:", tx)
                acc.updateBalance(int(splitted[3]), int(splitted[4]), int(splitted[5]))
    def checkIfContinueRequesting(self):
        print("checkIfContinueRequesting begin")
        global solvedBlocksDict
        keys = solvedBlocksDict.keys()
        print("###(*&^(*&^(*&^(*&^&")
        print(keys)
        print("###(*&^(*&^(*&^(*&^&")
        if len(keys) == 0:
            print("checkIfContinueRequesting: solvedBlocksDict currently empty!")
            return -1
        elif len(keys) == 1:
            print("checkIfContinueRequesting: solvedBlocksDict only one key:", keys)
            return int(self.getBlockHeight(solvedBlocksDict[list(keys)[0]])) - 1
        keys = sorted(keys, key=lambda x : x[1])
        # sortedDict = OrderedDict()
        # for key in keys:
        #     sortedDict.update( {key : solvedBlocksDict[key]} )
        for revidx in range(len(keys)-1, 0,-1):
            # print("$")
            # print(revidx, keys[revidx])
            # print(revidx-1, keys[revidx-1])
            # print("$")
            # higherBlock = self.getBlockWOSolution(solvedBlocksDict[keys[revidx]])
            higherBlock = solvedBlocksDict[keys[revidx]]
            # lowerBlock = self.getBlockWOSolution(solvedBlocksDict[keys[revidx - 1]])
            lowerBlock = solvedBlocksDict[keys[revidx - 1]]
            # print(lowerBlock.encode())
            # print(hl.sha256(lowerBlock.encode()).hexdigest())
            higherBlockPrevHash = self.getBlockPrevHash(higherBlock)
            lowerBlockHash = hl.sha256(lowerBlock.encode()).hexdigest()
            # print(lowerBlockHash, higherBlockPrevHash)
            # print(int(self.getBlockHeight(lowerBlock)), lowerBlockHash != higherBlockPrevHash)
            # print("$")
            if lowerBlockHash != higherBlockPrevHash:
                # print("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                # print(higherBlock)
                # print("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                # print(higherBlockPrevHash)
                # print("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                # print(lowerBlock)
                # print("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                # print(lowerBlockHash)
                # print("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                print("checkIfContinueRequesting end")
                return int(self.getBlockHeight(higherBlock)) - 1
        print(keys)
        minkey = keys[0]
        if minkey[1] != 0:
            return minkey[1] -1
        return None

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
        global blockHeight
        global stopMining
        global rebuilderThreadID
        global receivedTrans
        global gossipMsgs
        lastRequestedBlock = -1
        print("Starting " + self.name)

        beginVerification = -1
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
                        print("$$$$$$$$$$$$$$$$$$$$$$$", blockHeight, stopMining, msg)
                        # print("serviceThread:", msg)
                        if msg.split()[0] == "INTRODUCE":
                            with introduceListLock:
                                introduceList.append(msg)
                                # print("serviceThread appending: ", msg, introduceList)

                        elif msg.split()[0] == "TRANSACTION":
                            with receivedTranslock and gossiplock and solvedBlocksTransLock:
                                if msg not in receivedTrans and msg not in solvedBlocksTrans:
                                    # print("if msg not in receivedTrans and msg not in solvedBlocksTrans:", msg)
                                    # print("BEFORE")
                                    # print("GOSSIP:", gossipMsgs)
                                    # print()
                                    # print("RECEIVED:", receivedTrans)
                                    # print("BEFORE")
                                    gossipMsgs.append(msg+"\n")
                                    receivedTrans.append(msg)
                                    receivedTrans = list(set(receivedTrans))
                                    # print("AFTER")
                                    # print("GOSSIP:", gossipMsgs)
                                    # print()
                                    # print("RECEIVED:", receivedTrans)
                                    # print("AFTER")
                                    self.arrivedTimeRecorder(msg)    
                            
                            tranmsg = Message(msg.split()[0:6])

                        elif msg.split()[0] == "SOLVED":
                            self.blockSolvedTimeRecorder(tx)

                            with stopMiningLock and toSolveBlocksDictLock and solvedBlocksTransLock and gossiplock:
                                if stopMining == False:
                                    splitted = msg.split()
                                    splitted = splitted[1:]
                                    h = splitted[0]
                                    sol = splitted[1]
                                    k = self.getKeyViaHash(h, "toSolveBlocksDict")
                                    print("SOLVED key:", k, toSolveBlocksDict[k])
                                    for tx in self.getTxFromBlock(toSolveBlocksDict[k]):
                                        print("SOLVED TX:", tx)
                                        if tx not in solvedBlocksTrans:
                                            solvedBlocksTrans.append(tx)
                                        if (tx+"\n") in gossipMsgs:
                                            gossipMsgs.remove((tx+"\n"))
                                    # print("SOLVEDBLOCK TRANS:", solvedBlocksTrans)
                                    with solvedBlocksDictLock:
                                        solvedBlocksDict.update( {k : toSolveBlocksDict[k] + " " + sol} )
                                    del toSolveBlocksDict[k]
                                    gossipMsgs.append(solvedBlocksDict[k]+"\n")
                                else:
                                    splitted = msg.split()
                                    splitted = splitted[1:]
                                    h = splitted[0]
                                    sol = splitted[1]
                                    k = self.getKeyViaHash(h, "toSolveBlocksDict")
                                    txToRestore = self.getTxFromBlock(toSolveBlocksDict[k])
                                    with receivedTranslock:
                                        for tx in txToRestore:
                                            receivedTrans.append(tx)
                                            gossipMsgs.append(tx+"\n")
                                        receivedTrans = list(set(receivedTrans))
                                        # gossipMsgs = list(set(gossipMsgs))
                                    del toSolveBlocksDict[k]
                            # print(acc.accDict)

                        elif msg.split()[0] == "VERIFY" and msg.split()[1] == "OK":
                            with stopMiningLock:
                                if stopMining == True:
                                    with toVerifyBlocksDictLock and solvedBlocksDictLock and blockHeightLock and receivedTranslock and gossiplock and solvedBlocksTransLock:
                                        todelverifkeys = []
                                        # print("################")
                                        # print("TOVERIF", toVerifyBlocksDict)
                                        # print("################")
                                        for key in toVerifyBlocksDict.keys():
                                            if key[0] == msg.split()[2]:
                                                print("serviceThread verify ok:", toVerifyBlocksDict[key])
                                                todelverifkeys.append(key)
                                                break
                                        print("i was able to escape with key:", todelverifkeys)
                                        if len(todelverifkeys) > 0:
                                            if int(self.getBlockHeight(toVerifyBlocksDict[key])) > blockHeight:
                                                blockHeight = int(self.getBlockHeight(toVerifyBlocksDict[key]))
                                            # self.undoBalance(todelverifkeys)
                                            # print("################")
                                            # print("PREMOVESOLVED", solvedBlocksDict.keys())
                                            # print("##################")
                                            self.moveVerifiedIntoSolved(todelverifkeys)
                                            # print("################")
                                            # print("POSTMOVESOLVED", solvedBlocksDict.keys())
                                            # print("##################")
                                            try:
                                                nextreqbh = self.checkIfContinueRequesting()
                                            except:
                                                print("checkIfContinueRequesting failed")
                                            print("serviceThread nextreqbh:", nextreqbh, rebuilderThreadID)
                                            if nextreqbh != None and nextreqbh != -1:
                                                print("serviceThread requesting additional block: ", nextreqbh, lastRequestedBlock)
                                                if nextreqbh == lastRequestedBlock:
                                                    print("sericeThread resuming mining to try and retrieve a new block fromsomeone else")
                                                    # with blockRequestsDictLock:
                                                    #     req = "REQUESTBLOCK " + str(nextreqbh+1)
                                                    #     blockRequestsDict.update( {rebuilderThreadID : req} )
                                                    #     lastRequestedBlock = nextreqbh + 1
                                                    lastRequestedBlock = -1
                                                    stopMining = False
                                                else:
                                                    print("sericeThread requesting lower blockheight")
                                                    with blockRequestsDictLock:
                                                        req = "REQUESTBLOCK " + str(nextreqbh)
                                                        blockRequestsDict.update( {rebuilderThreadID : req} )
                                                        lastRequestedBlock = nextreqbh
                                            # elif nextreqbh != None and nextreqbh == -1:
                                            #     print("serviceThread requesting additional block: ", nextreqbh)
                                            #     with blockRequestsDictLock:
                                            #         req = "REQUESTBLOCK " + str(0)
                                            #         blockRequestsDict.update( {rebuilderThreadID : req} )
                                            else:
                                                print("serviceThread caught up!", msg)
                                                self.rebuildAccs()
                                                print("REBUILDACCS DICT:", solvedBlocksDict.items())
                                                # with :
                                                # print("serivceThread caught up solvedtrans:", solvedBlocksTrans)
                                                # print("serviceThread caught up receivedTrans:", receivedTrans)
                                                solvedBlocksTrans.clear()
                                                for block in solvedBlocksDict.values():
                                                    for tx in self.getTxFromBlock(self.getBlockWOSolution(block)):
                                                        solvedBlocksTrans.append(tx)
                                                receivedTrans = list(set(receivedTrans))
                                                for tx in solvedBlocksTrans:
                                                    if tx in receivedTrans:
                                                        receivedTrans.remove(tx)
                                                print("serivceThread caught up solvedtrans:", solvedBlocksTrans)
                                                print("serviceThread caught up receivedTrans:", receivedTrans)
                                                blockHeight += 1
                                                stopMining = False
                                                self.genesisBlock = False
                                                with rebuilderThreadIDLock:
                                                    rebuilderThreadID = None
                        
                        elif msg.split()[0] == "VERIFY" and msg.split()[1] == "FAIL":
                            print("serviceThread verification failed:", msg)                   
                            with stopMiningLock and toVerifyBlocksDictLock and rebuilderThreadIDLock:
                                todelverifkeys = []
                                for key in toVerifyBlocksDict.keys():
                                    if key[0] == msg.split()[2]:
                                        print("serviceThread verify false:", toVerifyBlocksDict[key])
                                        todelverifkeys.append(key)
                                        break
                                    
                                if len(todelverifkeys) > 0:
                                    for key in todelverifkeys:
                                        del toVerifyBlocksDict[key]
                                stopMining = False
                                rebuilderThreadID = None

                        elif msg.split()[0] == "DIE":
                            # Send system kill sign
                            SystemInput.kill_handler()            
                        else:
                            print("####################")
                            print("serviceThread: GOT AN INCORRECT MESSAGE TYPE")
                            print(retmsgs)
                            print("####################")
                    with stopMiningLock:
                        if stopMining == False:
                            with receivedTranslock and solvedBlocksTransLock and toSolveBlocksDictLock and solvedBlocksDictLock:
                                if len(receivedTrans) > 0 and random.randint(1,2) == 1:
                                    receivedTrans.sort(key = lambda x: x.split()[1]) 
                                    # print("CREATING BLOCK RECEIVEDTRANS:", receivedTrans)
                                    # print("CREATING BLOCK SOLVEDTRANS:", solvedBlocksTrans)
                                    # rnd = random.randint(1, MAX_TX_PER_BLOCK)
                                    rnd = min(len(receivedTrans), MAX_TX_PER_BLOCK)
                                    if True: # if rnd <= len(receivedTrans):
                                        print('service thread len(receivedTrans):', len(receivedTrans), rnd, MAX_TX_PER_BLOCK)
                                        msgsToAdd = random.sample(receivedTrans, rnd) # receivedTrans[:rnd] # random.sample(receivedTrans, rnd)
                                        with blockHeightLock:
                                            # with acc.accDictLock:
                                            #     print(")))))))))))))))))))))))))))))))")
                                            #     print(acc.accDict)
                                            #     print(")))))))))))))))))))))))))))))))")
                                            with gossiplock:
                                                block, h, toRemove = self.genBlock(msgsToAdd)
                                            if len(toRemove) > 0:
                                                # print("TOREMOVE:", toRemove)
                                                toRemove = list(set(toRemove))
                                                receivedTrans = list(set(receivedTrans))
                                                for m in toRemove:
                                                    receivedTrans.remove(m)
                                            print("$(*#&$")
                                            print(block, h)
                                            if block != None:
                                                blockTxs = self.getTxFromBlock(block)
                                                for tx in blockTxs:
                                                    if blockTxs.count(tx) > 1:
                                                        print()
                                                        print("DUPLICATE TRANSACTION IN GENBLOCK:", tx)
                                                        print()
                                            print("$(*#&$")
                                            with acc.accDictLock:
                                                print(")))))))))))))))))))))))))))))))")
                                                print(acc.accDict)
                                                print(")))))))))))))))))))))))))))))))")
                                            # print(block, h, toRemove)
                                            if h != None:
                                                newKey = (h, blockHeight)
                                                toSolveBlocksDict.update( {newKey : block} )
                                                blockHeight += 1
                                                sock.send( ("SOLVE " + h + "\n").encode() )
                    with toVerifyBlocksDictLock:
                        with stopMiningLock:
                            if stopMining == True:
                                if len(toVerifyBlocksDict.keys()) > 0:
                                    for key in toVerifyBlocksDict.keys():
                                        h = key[0]
                                        sol = self.getBlockSolution(toVerifyBlocksDict[key])
                                        sock.send( ("VERIFY " + h + " " + sol + "\n").encode())
                                    beginVerification = time.time()
                                print("time", time.time())
                                if time.time() - beginVerification > VERIFICATION_TIMEOUT:
                                    print("timeout", time.time(), beginVerification, time.time() - beginVerification)
                                    lastRequestedBlock = -1
                                    stopMining = False


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
        global blockHeight
        global stopMining
        global rebuilderThreadID
        global receivedTrans

        print("GOSSIPRECV SPAWN", sock,addr)

        detectInstance = False
        
        instancePort = None # NOTE: int
        ip = None # NOTE: String
        instance = None # NOTE: int
        while True:
            data = sock.recv(BUFFERSIZE).decode()
            # Save bandwidth
            with config.BW_LOCK:
                config.BW_STACK += len(data)

            firstMessage, prevMessage, retmsgs = self.serialDecode(firstMessage, prevMessage, data)
            # print("##################", ip, instancePort, stopMining, firstMessage, prevMessage, retmsgs)
            if retmsgs != None:
                # print("############")
                # print("RETMSGS: ", retmsgs)
                # print("############")

                # TODO: the problem right now is that the check for if message is not in the
                # TODO: list seems bad
                for msg in retmsgs:
                    # also we need to check if we have received this
                    # message already if we have already received this
                    # message do nothing.  otherwise we need to add
                    # it to the list of messages we need to also gossip
                    # print("#")
                    # print("gossipRecv from", addr[0], ":", msg)
                    # print("#")

                    # make sure that we do not have a connection yet
                    if msg.split()[0] == "INSTANCEID" and detectInstance == False:
                        splitted = msg.split()
                        with IPLock:
                            print("IP", IP)
                            instancePort = int(g.BASEPORT) + 2 * (int(splitted[1]) - 1) + 1
                            instance = int(splitted[1])
                            ip = addr[0]
                            if (addr[0], int(splitted[1])) not in IP:
                                print(addr, IP)
                                if False: #addr[0] == self.myIp:
                                    # also create an introduce message to send back our own gossips
                                    i = "INTRODUCE -1 " + "localhost" + " " + str(int(g.BASEPORT) + \
                                        2 * (int(splitted[1]) - 1) + 1)
                                else:
                                    # also create an introduce message to send back our own gossips
                                    i = "INTRODUCE -1 " + addr[0] + " " + str(int(g.BASEPORT) + \
                                        2 * (int(splitted[1]) - 1) + 1)
                                # add new ip connected to
                                IP.append((addr[0], int(splitted[1])))
                                
                                with introduceListLock:
                                    introduceList.append(i)
                                detectInstance = True
                                print("gossipRecv received INSTANCEID:", msg)
                            # else:
                            #     return
                        continue
                        
                    elif msg.split()[0] == "NODE":
                        if ip != None and instance != None:
                            with IPLock:
                                splitted = msg.split()
                                print("EEEEEEEEEEEEEEEE",splitted, g.INSTANCEID)
                                if splitted[1] != g.MYIP and g.INSTANCEID != int(splitted[2]):
                                    if (splitted[1], int(splitted[2])) not in IP:
                                        IP.append((splitted[1], int(splitted[2])))
                                        with introduceListLock:
                                            port =  str(int(g.BASEPORT) + 2 * (int(splitted[2]) - 1) + 1)
                                            print("NODE: ", "INTRODUCE -5 " + splitted[1] + " " + port)
                                            introduceList.append("INTRODUCE -5 " + splitted[1] + " " + port)

                    elif msg.split()[0] == "TRANSACTION":
                        with receivedTranslock and gossiplock and solvedBlocksTransLock:    
                            self.arrivedTimeRecorder(msg)
                            # if msg not in receivedTrans and msg not in solvedBlocksTrans:
                            if msg not in solvedBlocksTrans:
                                # print("FUCK ME:", solvedBlocksTrans)
                                if msg not in receivedTrans:
                                    # print("gossipRecv TRANSACTION NEW ONE:", msg)
                                    receivedTrans.append(msg)
                                    receivedTrans = list(set(receivedTrans))
                                    if msg not in gossipMsgs:
                                        gossipMsgs.append(msg+"\n")
                            

                    elif msg.split()[0] == "PREVHASH":
                        msgbh = int(self.getBlockHeight(msg))
                        self.blockArrivedTimeRecorder(msg)
                        with stopMiningLock:
                            if stopMining == False:
                                with blockHeightLock and rebuilderThreadIDLock:
                                    if msgbh > blockHeight:
                                        print("gossipRecv PREVHASH msgbh > blockheight:", msgbh, blockHeight)
                                        self.updateChainSplit()
                                        with toVerifyBlocksDictLock:
                                            h = hl.sha256(self.getBlockWOSolution(msg).encode()).hexdigest()
                                            newkey = (h, msgbh)
                                            toVerifyBlocksDict.update( {newkey : msg} )
                                            print("gossipRecv PREVHASH newkey msg:", newkey, msg)
                                        stopMining = True
                                        rebuilderThreadID = (ip,instancePort)
                                        print("gossipRecv rebuilderThreadID assign:", rebuilderThreadID)
                    
                    elif msg.split()[0] == "REQUESTBLOCK":
                        with stopMiningLock:
                            print("gossipRecv stopMining, REQUESTBLOCK:", stopMining, msg)
                            if stopMining == False:
                                with replyBlocksDictLock and solvedBlocksDictLock \
                                and replyBlocksDictLock:
                                    print("gossipRecv REQUESTBLOCK:", msg)
                                    bh = int(self.getBlockHeightFromRequestBlock(msg))
                                    rep = None
                                    key = self.getKeyViaBlockHeight(bh, "solvedBlocksDict")
                                    blockToSend = solvedBlocksDict[key]
                                    rep = "REQUESTEDBLOCK " + blockToSend # self.getBlockWOSolution(blockToSend)
                                    assert rep != None
                                    key = (ip, instancePort)
                                    print("gossipRecv REQUESTBLOCK reply:", key, rep)
                                    replyBlocksDict.update( {key : rep} )
                            else:
                                print("gossipRecv queueing request:", msg)
                                with replyBlocksSetLock:
                                    key = (ip, instancePort)
                                    replyBlocksSet.add((key, int(self.getBlockHeightFromRequestBlock(msg))))
                    
                    elif msg.split()[0] == "REQUESTEDBLOCK":
                        with stopMiningLock:
                            if stopMining == True:
                                with toVerifyBlocksDictLock:
                                    print("gossipRecv REQUESTEDBLOCK:", msg)
                                    blockSol = self.getBlockFromRequestedBlock(msg)
                                    # print("gossipRecv REQUESTEDBLOCK blocksol:", blockSol)
                                    block = self.getBlockWOSolution(blockSol)
                                    # print("gossipRecv REQUESTEDBLOCK block:", block)
                                    h = hl.sha256( block.encode() ).hexdigest()
                                    bh = int(self.getBlockHeight(block))
                                    key = (h, bh)
                                    self.blockArrivedTimeRecorder(msg)
                                    if key not in toVerifyBlocksDict.keys():
                                        toVerifyBlocksDict.update( {key : blockSol} )

                    # TODO: At the end of all the ifs check if we still need to keep requesting blocks

                    # NOTE: Due to the changes in gossipSend there
                    # is no more reason to check length of the second argument
                    # this is because each gossipSend now checks its local index
                    # to determine what messages its sent to its peer
                    # gossipMsgs.append((msg+"\n", []))

                    # NOTE: Saves time when message arrived 
                    # self.arrivedTimeRecorder(msg)
    
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
        serversocket.listen(15)

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

        ip = str(ip)
        port = int(port)

        global stopMining
        global IP

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
        
        time.sleep(2)

        localIP = []
        while True:
            # sock.send("THISSUCKS\n".encode())
            with IPLock:
                if len(localIP) != len(IP) and len(IP) > 0:
                    print("SSSSSSSSSSSSS", IP)
                    for node in IP:
                        if node != None:
                            try:
                                print("gossipSend:", ("NODE " + str(node[0]) + " " + str(node[1])))
                                sock.send(("NODE " + str(node[0]) + " " + str(node[1]) + "\n").encode())
                            except:
                                # print("Connection Lost to ", str(ip) + ":" + str(port))
                                sock.close()
                                sock = socket.create_connection((ip, int(port)))
                                sock.send(("NODE " + str(node[0]) + " " + str(node[1]) + "\n").encode())
                    localIP = IP
            with gossiplock:
                for msg in gossipMsgs:
                    try:
                        # print("gossipSend to:", ip, msg)
                        sock.send(msg.encode())
                    except:
                        # Connection Lost
                        print("Connection Lost to ", str(ip) + ":" + str(port))
                        sock.close()
                        sock = socket.create_connection((ip, int(port)))
                        instance = "INSTANCEID " + str(g.INSTANCEID) + "\n"
                        sock.send(instance.encode())
                        # break
                gossipMsgs.clear()

            with blockRequestsDictLock:
                todelkeys = []
                if len(blockRequestsDict.keys()) > 0:
                    for key in blockRequestsDict.keys():
                        if key[0] == ip and key[1] == port:
                            print("gossipSend blockRequestsDict:", blockRequestsDict)
                            sock.send( (blockRequestsDict[key] + "\n").encode() )
                            todelkeys.append(key)
                    for key in todelkeys:
                        del blockRequestsDict[key]
            with replyBlocksDictLock and stopMiningLock:
                if stopMining == False:
                    todelkeys = []
                    for key in replyBlocksDict.keys():
                        if key[0] == ip and key[1] == port:
                            print("gossipSend replyBlocksDict:", replyBlocksDict)
                            sock.send( (replyBlocksDict[key] + "\n").encode() )
                            todelkeys.append(key)
                    for key in todelkeys:
                        del replyBlocksDict[key]
            with replyBlocksSetLock and stopMiningLock:
                if stopMining == False:
                    todelreq = []
                    for req in replyBlocksSet:
                        key = req[0]
                        if key[0] == ip and key[1] == port:
                            bh = req[1]
                            key = self.getKeyViaBlockHeight(bh, "solvedBlocksDict")
                            blockToSend = solvedBlocksDict[key]
                            sock.send( ("REQUESTEDBLOCK " + blockToSend + "\n").encode() )
                            todelreq.append(req)
                    for req in todelreq:
                        replyBlocksSet.remove(req)

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
                        with IPLock:
                            if (intro.split()[2], (int(intro.split()[3]) - g.BASEPORT) // 2 + 1) not in IP:
                                IP.append((intro.split()[2], (int(intro.split()[3]) - g.BASEPORT) // 2 + 1))
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

    """
        blockSolvedTimeRecorder
        Inputs: msg
        Outputs:
        Description:
            Records time when block is solved
    """
    def blockSolvedTimeRecorder(self, msg):
        txTime = time.time() 
        txId = msg.split()[2]
        config.BLOCK_APPEAR_TIME.update({txId : txTime})

    """
        blockArrivedTimeRecorder
        Inputs: msg
        Outputs:
        Description:
            Records time when block message is arrived
    """
    def blockArrivedTimeRecorder(self, msg):
        txTime = time.time() 
        txId = msg.split()[1].split()[0]

        print(txId)
        config.BLOCK_ARRIVED_TIME.update({txId : txTime})
    

    """
        updateChainSplit
        Inputs: 
        Outputs:
        Description:
            Update chain split 
    """
    def updateChainSplit(self):
        config.NUM_CHAIN_SPLIT += 1

    def delay_logger(self):
        for tx in self.getTxFromBlock(self.getBlockWOSolution(solvedBlocksDict)):
            print(tx[2])