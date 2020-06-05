class Isis:
    '''
        proposeSeq
        Input:
            p: Receiving process
        Output:
            Proposed Sequence Num       
        Description:
            Receiving processes choose the maximum observed sequence number + 1
    '''
    counter = 0.0
    @staticmethod
    def proposeSeq(p):
        
        if p.proposedSeq is None:
            print("New Test: p.proposedSeq is None") 
        if p.agreedSeq is None:
            print("New Test: p.agreedSeq is None") 
        
        if p.proposedSeq is None or p.agreedSeq is None :
            print("p.proposeSeq is None. Proposing" + str("0.")+ str(p.pid))
            pNum = Isis.counter + (float(p.pid) * 0.1)
            p.proposedSeq = pNum
            p.agreedSeq = pNum
            Isis.counter += 1.0
            return pNum
        Isis.counter += 1.0
        p.proposedSeq += Isis.counter
        p.agreedSeq += Isis.counter
        return max(p.proposedSeq, p.agreedSeq) + Isis.counter

    '''
        chooseAgreedNum
        Inputs:
            arg1: Instance of Message class
            arg2: Instance of Message class
            *args: Instance of Message classes (3rd msg, 4th msg, ... 8th msg)
        Output:
            Agreed Number = maximum proposed number + 1  appended with process Num. eg) 3.1, 4.2 
        Description:
            Sender chooses agreed priority. Append process num at the end
    '''
    @staticmethod
    # def chooseAgreedNum(arg1, arg2, *args):
    #     max = arg1.proposedSeq
    #     minSource = arg1.source
    #     for msg in args:
    #         if msg.proposedSeq > max:
    #             max = msg.proposedSeq
    #             minSource = msg.source
    #         elif msg.proposedSeq == max:
    #             max = msg.proposedSeq
    #             if msg.source < minSource:
    #                 minSource = msg.source
    #     result = float(str(max) + "." + str(minSource))
    
    #     return result + 1
    def chooseAgreedNum(l):
        arg1 = l[0]
        max = arg1.proposedSeq
        for msg in l[1:]:
            if msg.proposedSeq > max:
                max = msg.proposedSeq

        return max + 1.0
    

    '''
    storeMsg
        Inputs: 
            p: Instance of process
            msg: instance of message
        Output:
            None
        Description:
            Store message in Queue(holdback) 
    '''
    @staticmethod
    def storeMsg(p, msg):
        num = float(str(msg.proposedSeq) + "." + str(msg.source))
        p.holdback.append((num, msg))

    @staticmethod
    def printHoldback(p):
        result = list()
        for m in p.holdback:
            result.append(str(m.proposedSeq) + " " + str(m.source) +" "+str(m.amount))
        print("My Process #: " + str(p.pid) + "\n" + str(result))
    
    '''
    reorderMessages
        Inputs: 
            p: Instance of process
            agreedMsg: agreedMsg
        Output:
            None
        Description:
            Upon receiving agreed priority, reorder messages
    '''
    # Not Used
    @staticmethod
    def reorderMessages(p, agreedMsg):
        if len(p.holdback) > 1:
            # Isis.printHoldback(p)
            tempHoldback = p.holdback
            sortedHoldback = []
            while tempHoldback:
                minimum = tempHoldback[0]  # arbitrary number in list 
                for x in tempHoldback: 
                    if x.proposedSeq == None:
                        """
                        """
                    elif minimum.proposedSeq == None:
                        """
                        """
                    elif x.proposedSeq < minimum.proposedSeq:
                        minimum = x
                sortedHoldback.append(minimum)
                tempHoldback.remove(minimum) 
            p.holdback = sortedHoldback

            for msg in p.holdback:
                if msg.messageId == agreedMsg.messageId:
                    msg.isDeliverable = True

    '''
    deliverableMsgs
        Inputs: 
            p: Instance of process
        Output:
            msgs: list of deliverable messages
        Description: 
            Return deliverable messages. They are already reordered by agreed priority
    '''
    @staticmethod
    def deliverableMsgs(p):
        msgs = list()
        for msg in p.holdback:
            if msg[1].isDeliverable is True:
                msgs.append(p.holdback.pop(0)) # Pop from the front of the list
                continue
            break
        return msgs
    
    