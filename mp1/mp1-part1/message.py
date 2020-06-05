import hashlib

class Message:
    """
        __init__
        Inputs:
            None
        Outputs:
            None
        Description:
            source: A process that sends request eg) 1, 2, 3, .... 8
            target: A process that receives a message (only used for RRep) so we dont need to multicast
            messageId: A message id
            proposedSeq: The sequence number that the source is proposing eg) 1, 2, 3, 4, ... 
            type: "DEPOSIT" or "TRANSFER"
            sourceAcc: The source account not used in DEPOSIT
            targetAcc: The target account of a transaction
            amount: Amount to be transfered/deposited
            isDeliverable: Is this deliverable message when at front of priority queue?
            isRRep: True if a message is a receiver reply
            isSRep: True if a message is a sender reply
            counter: Counter for msg created in the same process 
            DEPOSIT yxpqg 75, TRANSFER yxpqg -> wqkby 13
    """
    counter = 0

    def __init__(self):
        self.source = None
        self.target = None # only used for RRep
        self.messageId = None
        self.proposedSeq = None
        self.type = None
        self.sourceAcc = None
        self.targetAcc = None
        self.amount = None
        self.isDeliverable = False
        self.isRRep = False
        self.isSRep = False
        Message.counter += 1

    """
        Preprocessing
        Inputs:
            pId: process id
            msgContent: Message content from stdio
    """
    def preprocess(self, pId, msgContent):
        self.source = pId
        # self.messageId = str(pId) + '-' + str(Message.counter)
        m = hashlib.sha256()
        m.update(str.encode(msgContent + str(Message.counter) + str(pId)))
        self.messageId = m.digest()

        # eg) TRANSFER n -> g 18
        # => ['TRANSFER', 'n', '->', 'g', '18']
        for i, word in enumerate(msgContent.split()):
            if i == 0:
                if word == 'DEPOSIT':
                    self.type = 'DEPOSIT'    
                elif word == 'TRANSFER':
                    self.type = 'TRANSFER'
            if i == 1:
                if self.type == 'DEPOSIT':
                    self.targetAcc = word
                elif self.type == 'TRANSFER':
                    self.sourceAcc = word
            if i == 2:
                if self.type == 'DEPOSIT':
                    self.amount = float(word)
            if i== 3:
                if self.type == 'TRANSFER':
                    self.targetAcc = word
            if i== 4:
                if self.type == 'TRANSFER':
                    self.amount = float(word)
        
    """
        assignSource
        Inputs:
            sourceIdIn: Input source Id Number eg) p1, p2, p3, p4, ...
        Outputs:
            None
        Description:
            This assigns a sourceId to this instance of message. Tells whom the sender is. 
    """
    def assignSource(self, sourceIdIn):
        self.source = sourceIdIn

    def assignTarget(self, targetIdIn):
        self.target = targetIdIn
        
    """
        assignMessageId
        Inputs:
            msgIdIn: Assign unique ids to identify receiver's reply. eg) p1-01, p1-02, ...
        Outputs:
            None
        Description:
            This assigns a msgId to this instance of message
    """
    def assignMessageId(self, msgIdIn):
        self.messageId = msgIdIn

    """
        assignSeq
        Inputs:
            proposedSeq: propose sequence number. eg) 1, 2, 3, 4 ...
        Outputs:
            None
        Description:
            This assigns proposed sequence number to this instance of message
    """
    def assignSeq(self, proposedSeqIn):
        self.proposedSeq = proposedSeqIn

    """
        assignType
    """
    def assignType(self, typeIn):
        if typeIn == "DEPOSIT" or typeIn == "TRANSFER":
            self.type = typeIn
        else:
            print("assignType: WRONG TYPE")
    
    """
        assignSouceAcc
    """
    def assignSourceAcc(self, sourceAccIn):
        self.sourceAcc = sourceAccIn
    
    """
        assignTargetAcc
    """
    def assignTargetAcc(self, targetAccIn):
        self.targetAcc = targetAccIn
    
    """
        assignAmount
    """
    def assignAmount(self, amountIn):
        self.amount = amountIn


class ReceiverReply(Message):
    """
        __init__
        Inputs:
            source
            proposedSeq
            content
            messageId: Assign unique ids to identify receiver's reply. eg) p1-01-rr, p1-02-rr, ...
        Outputs:
            None
        Description:
            Inherits properties and methods from Class message
            This constructor assigns a default value of None to messageId

    """
    def __init__(self):
        super().__init__()
        self.isRRep = True
        # self.messageId = None

class SenderReply(Message):
    """
        __init__
        Inputs:
            source
            proposedSeq
            content
            messageId: Assign unique ids to identify receiver's reply. eg) p1-01-sr, p1-02-sr, ...
        Outputs:
            None
        Description:
            Inherits properties and methods from Class message
            This constructor assigns a default value of None to messageId
    """
    def __init__(self):
        super().__init__()
        self.isSRep = True
        # self.messageId = None