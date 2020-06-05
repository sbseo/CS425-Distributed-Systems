from message import *
from account import *
from isis import *
from collections import defaultdict
import hashlib

# import rpyc

import sys
import threading

class Process():
    """
        __init__
        Inputs:
            None
        Outputs:
            None
        Description:
            pid: Process ID
            numProc: The number of other processes
            proposedSeq: Proposed sequence number
            agreedSeq: Agreed sequence number
            holdback: Queue of holdback messages
            delivered: Queue of delivered messages
            accountDict: The dictionary of accounts (use this due to speed over list)
            socketsDict: Keeps a dictionary of all the sockets that we need
            selfMessageRepDict: Keeps track of all the messages that it sent and the
                number of receiver replies it got per message
    """
    counter = 0 # Helpful for proposing Seq Num

    def __init__(self):
        self.pid = None
        self.numOtherProc = None
        self.proposedSeq = None
        self.agreedSeq = None
        self.holdback = []
        self.delivered = []
        self.accountDict = defaultdict(int) # {}
        self.socketsDict = {}
        self.selfMessageRepDict = {}
    """
        assignPid
        Inputs:
            pidIn: The input pid
        Outputs:
            None
        Description:
            This function assigns the pid to a process
    """
    def assignPid(self, pidIn):
        self.pid = pidIn

    """
        assignNumOtherProc
    """
    def assignNumOtherProc(self, num):
        self.numOtherProc = num

    """
        createNewMessage
            Inputs:
                self:
                pidIn:
                msgContent: content of message
            Outputs:
                Msg(): This is not used fo ranything
                    wwe are actually send the string from
                    standard in
            Description:
                This process creates a new mew message
                and adds it to the back of the holdback queue.
                It also adds the message to the dictionary to keep
                track of the number of receiver replies it got
    """
    def createNewMessage(self, msgContent):
        m = hashlib.sha256()
        m.update(str.encode(msgContent))
    
        # print("createNewMessage: ", msgContent)

        splitted = msgContent.split(" ")
        if splitted[0] == "DEPOSIT":
            # print("createNewMessage: DEPOSIT detected")
            newMsg = Message()
            # print("What is PID here: ", self.pid)
            newMsg.preprocess(self.pid, msgContent)
            # print("What is my pSeq (Before Assigned):", newMsg.proposedSeq)
            newMsg.assignSeq(Isis.proposeSeq(self))
            # print("What is my pSeq (After Assigned):", newMsg.proposedSeq)
    

            # Debugging..... March 7
            # check if account exists if it does update
            # if splitted[1] in self.accountDict:
            self.accountDict[splitted[1]] += 0
                # self.accountDict[splitted[1]] += float(splitted[2])
            # else:
                # self.accountDict.update({splitted[1] : float(splitted[2])})
            
            # update holdback
            # print("DEBUG createnewmessage", newMsg.proposedSeq, self.pid)
            self.holdback.append(newMsg)
            assert newMsg.messageId not in self.selfMessageRepDict
            self.selfMessageRepDict.update({newMsg.messageId : []})

            return newMsg

        # [TRANSFER, a, ->, b, 10] 
        # TODO: Send to the other processes
        elif splitted[0] == "TRANSFER":
            # print("createNewMessage: TRANSFER detected")
            newMsg = Message()
            newMsg.preprocess(self.pid, msgContent)

            # NOTE: We do not need to assign a sequence number here
            # the receivers of this message will reply with theirs
            # then we finalize suing our own value before we multicast SRep

            # check if source account is in dictionary
            # if not fail out
            
            if splitted[1] in self.accountDict:
                # does not set accoutn balance will not zero out
                if  self.accountDict[splitted[1]] - float(splitted[4]) >= 0:
                    # check if target account in dict. If not, add it to dictionary
                    pass
                    # self.accountDict[splitted[3]] += 0
                    
                    # if splitted[3] in self.accountDict:
                    #     self.accountDict[splitted[1]] -= float(splitted[4])
                    #     self.accountDict[splitted[3]] += float(splitted[4])
                    
                    # if the account is not in dict
                    # and the amount is positive create acc
                    # NOTE: Do we care if the amount is > 0?
                    # elif splitted[4] not in self.accountDict and float(splitted[4]) > 0:
                    #     self.accountDict[splitted[1]] -= float(splitted[4])
                    #     self.accountDict.update({splitted[3]: float(splitted[4])})
                # else fail out since acc balance < 0
                else:
                    return None
            # fail out
            else:
                return None


            # update holdback
            # self.holdback.append(newMsg)
            # newMsg.proposedSeq = Isis.proposeSeq(self)
            newMsg.assignSeq(Isis.proposeSeq(self))
            self.holdback.append(newMsg)
            
            # Isis.storeMsg(self, newMsg)
            assert newMsg.messageId not in self.selfMessageRepDict
            self.selfMessageRepDict.update({newMsg.messageId : []})

            return newMsg
        else:
            print("sendMessage: Invalid message type input")
            return None
    
    """
        createReceiverReply
            Inputs:
                msg: Message() from a process
            Outputs:
                rrep: ReceiverReply() object representing a receiver reply
            Description:
                This function creates a receiver reply to a message
                and returns it.
    """
    def createReceiverReply(self, msg):
        # create receiver reply
        rrep = ReceiverReply()
        # assign the source of the receiver reply
        rrep.assignSource(self.pid)
        # assign the sequence number
        rrep.assignSeq(Isis.proposeSeq(self))
        # assign the message id
        rrep.assignMessageId(msg.messageId)
        # assign the target of the message (original sender of Message())
        rrep.assignTarget(msg.source)

        assert msg.isDeliverable == False
        
        return rrep

    """
        createSenderReply
            Inputs:
                mid: Message ID we are createing SRep for
            Outputs:
                srep: SenderReply
            Description:
                This function creates a sender reply
                assigns the maximum seq number to it
                and returns it.  Moreover it assigns a
                final seq number to the relevant message and
                deliverable.  If it is deliverable deliver it.
                This is called within recvReceiverReply.
    """
    def createSenderReply(self, mid, numother):
        srep = SenderReply()
        srep.assignSource(self.pid)
        srep.assignMessageId(mid)

        assert mid in self.selfMessageRepDict
        # print(len(self.selfMessageRepDict[mid]), numother)
        # assert len(self.selfMessageRepDict[mid]) == numother
        
        srep.assignSeq(Isis.chooseAgreedNum(self.selfMessageRepDict[mid]))

        # sender now needs ot mark this message as deliverable
        for i in range(len(self.holdback)):
            if self.holdback[i].messageId == mid:
                self.holdback[i].proposedSeq = Isis.chooseAgreedNum(self.selfMessageRepDict[mid])
                self.holdback[i].isDeliverable = True
                break

        return srep

    """
        recvMessage
            Description: Receive a new message and add it to the end
                of our holdback queue
    """
    def recvMessage(self, msg):
        for message in self.holdback:
            # print("self.holdback in recvMessage")
            # print(self.holdback)
            if message.messageId == msg.messageId:
                # print("Message already exists in holdback.")
                return 0
        for message in self.delivered:
            if message.messageId == msg.messageId:
                # print("Message is already delivered.")
                return 0
        self.holdback.append(msg)
        
        if msg.sourceAcc != None and \
                msg.sourceAcc not in self.accountDict.keys():
            self.accountDict.update({msg.sourceAcc : 0})
        if msg.targetAcc != None and \
                msg.targetAcc not in self.accountDict.keys():
            self.accountDict.update({msg.targetAcc : 0})
        
        return 1

    """
        recvReceiverReply
            Description: Appends a new sequence number into the dictionary
    """
    def recvReceiverReply(self, rrep):
        assert rrep.isRRep == True
        mid = rrep.messageId
        # print("DEBUG: recvReceiverReply RRep mid:", mid, "Repdict:", self.selfMessageRepDict)
        if mid in self.selfMessageRepDict:
            assert mid in self.selfMessageRepDict
            self.selfMessageRepDict[mid].append(rrep)


    """
        recvSenderReply
            Description: Given a sender reply we update the message
                in our holdback queue with the final sequence number
                and mark it as deliverable
    """
    def recvSenderReply(self, srep):
        assert srep.isSRep == True
        mid = srep.messageId
        
        # mark deliverable
        # TODO: Not sure if this works
        for i, message in enumerate(self.holdback):
            if message.messageId == mid:
                self.holdback[i].isDeliverable = True
                # print("recvSenderReply")
                self.holdback[i].proposedSeq = srep.proposedSeq
                # if message.type == "DEPOSIT":
                #     self.accountDict[message.targetAcc] += message.amount
                # elif message.type == "TRANSFER":
                #     self.accountDict[message.sourceAcc] -= message.amount
                #     self.accountDict[message.targetAcc] += message.amount

    """
        recvWrapper
        Inputs:
            msg: The input message
        Outputs:
            Message(): If we receive a message of type message
                return a Message object. Otherwise return none
        Description: This function determines which type of message
            has been received and appropiately calls the correct function
    """
    def recvWrapper(self, msg):
        # invalid message input
        # such as an invalid transfer which makes the balance neg
        if msg == None:
            return None
        elif msg.isRRep:
            # print("DEBUG recvWrapper: Received RRep")
            self.recvReceiverReply(msg)
            return None
        elif msg.isSRep:
            # print("DEBUG recvWrapper: Received SRep")
            self.recvSenderReply(msg)
            return None
        else:
            # print("DEBUG recvWrapper: Received Msg")
            isNewMsg = self.recvMessage(msg)
            # print("DEBUG recvWrapper: Received Msg, creating receiver reply")
            if isNewMsg:
                return self.createReceiverReply(msg)
    """
        printMessage
    """
    def printMessage(self, msg):
        if msg.type == "DEPOSIT":
            print("printMessage: DEPOSIT " + msg.targetAcc + " " + str(msg.amount))
        elif msg.type == "TRANSFER":
            print("printMessage: TRANSFER " + msg.sourceAcc + " -> " + msg.targetAcc + " " + str(msg.amount))
        else:
            print("DEBUG printMessage: unknown message type")
        
    """
        printAccs
    """
    def printAccs(self):
        # print("DDDDDDDDDDDDDDDDDDDDDDD", self.accountDict.keys())
        print("BALANCES", end = '')
        for k, _ in list(self.accountDict.items()):
            print(" "+ str(k) + ":" + str(self.accountDict[k]), end = '')
        print()
            

    """
        sort
        Inputs:
            None
        Outputs:
            None
        Description:
            This function sorts messages in a queue
    """