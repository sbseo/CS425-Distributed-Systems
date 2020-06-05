import Pyro4
import socket
import threading
import sys
import config

SERV_NAME = None

COORDINATOR_URI = config.COORDINATOR_URI

Pyro4.config.SERIALIZER = 'marshal'

@Pyro4.expose
@Pyro4.behavior(instance_mode="single")
class Server(object):
    def __init__(self):
        self.finalDict = {}
        self.finalDictLock = threading.Lock()
        self.tentativeDicts = {}
        self.tentativeDictsLock = threading.Lock()
        self.coordinator = Pyro4.Proxy(COORDINATOR_URI)
        # keep track of the clients so we know who to send 
        # an abort message to
        self.clients = set()
    
    def Begin(self, ip, inst, tid, uri):
        self.tentativeDicts.update({(ip, inst, tid) : {}})
        self.clients.add((ip, inst, uri))
        self.coordinator.Begin(ip, inst, tid)
        print("Begin tentativeDicts:", self.tentativeDicts)
    
    def Deposit(self, ip, inst, tid, acc, amount):
        print("Deposit tentativeDicts prev:", self.tentativeDicts)
        readValue = None
        # do we have a tentative transaction?
        if (ip, inst, tid) in self.tentativeDicts.keys():
            # do we have acc in the tentative transaction
            if acc in self.tentativeDicts[(ip,inst,tid)].keys():
                # then read the tentative value
                if self.coordinator.Read(SERV_NAME, ip, inst, tid, acc):
                    readValue = self.tentativeDicts[(ip,inst,tid)][acc]
                else:
                    print("Deposit ABORT", ip, inst, tid)
                    return "ABORTED"
            # we do not have a tentative acc value
            else:
                # if we have a previous value
                if acc in self.finalDict.keys():
                    # then read prev value
                    if self.coordinator.Read(SERV_NAME, ip, inst, tid, acc):
                        readValue = self.finalDict[acc]
                # assign prev value to be 0                        
                else:
                    if self.coordinator.Read(SERV_NAME, ip, inst, tid, acc):
                        readValue = 0
                    else:
                        print("Deposit ABORT", ip, inst, tid)
                        return "ABORTED"
        # we do not have tentative acc balance but still need to read previous value
        else:
            # if we have a previous value
            if acc in self.finalDict.keys():
                # then read prev value
                if self.coordinator.Read(SERV_NAME, ip, inst, tid, acc):
                    readValue = self.finalDict[acc]
            # assign prev value to be 0                        
            else:
                if self.coordinator.Read(SERV_NAME, ip, inst, tid, acc):
                    readValue = 0
                else:
                    print("Deposit ABORT", ip, inst, tid)
                    return "ABORTED"
        
        assert readValue != None

        # now write the new value
        if self.coordinator.Write(SERV_NAME, ip, inst, tid, acc):
            with self.tentativeDictsLock:
                # we have transaction id already stored
                if (ip,inst,tid) in self.tentativeDicts.keys():
                    nextValue = -1
                    if readValue + float(amount) >= 1000000000:
                        nextValue = 1000000000
                    else:
                        nextValue = readValue + float(amount)
                    assert nextValue != -1
                    self.tentativeDicts[(ip,inst,tid)][acc] = nextValue
                    print("Deposit tentativeDicts after:", ip, inst, tid, self.tentativeDicts)
                    return "OK"
                # NOTE INCORRECT: create a new tetative transaction
                # somehow the coordinatorAbort possibly triggered adn now we do not have
                # the transaction in our tentative dicts
                else:
                    # if we do not have tentative dicts then we return 
                    if (ip, inst, tid) not in self.tentativeDicts.keys():
                        return ""
                    else:
                        nextValue = -1
                        if readValue + float(amount) >= 1000000000:
                            nextValue = 1000000000
                        else:
                            nextValue = readValue + float(amount)
                        assert nextValue != -1
                        self.tentativeDicts[(ip,inst,tid)][acc] = nextValue
                        # self.tentativeDicts.update({ (ip, inst, tid) : {acc : readValue + float(amount)} })
                        print("Deposit tentativeDicts after:", ip, inst, tid, self.tentativeDicts)
                        return "OK"
        else:
            print("Deposit ABORT", ip, inst, tid)
            return "ABORTED"

    def Balance(self, ip, inst, txId, acc):
        print("Balance", ip, inst, txId, acc)

        # check if we have a newer tentative value
        if (ip, inst, txId) in self.tentativeDicts.keys():
            # we have a tentative update for acc in question
            if acc in self.tentativeDicts[(ip, inst, txId)].keys():
                if self.coordinator.Read(SERV_NAME, ip, inst, txId, acc):
                    return SERV_NAME + "." + acc + " = " + str(self.tentativeDicts[(ip, inst, txId)][acc])
                else:
                    # abort if not found
                    self.coordinator.abortCommit(SERV_NAME, ip, inst, txId)
                    # delete our tentative transaction
                    with self.tentativeDictsLock:
                        del self.tentativeDicts[(ip,inst,txId)]
                    return "NOT FOUND"
            # else load the final value
            else:
                if acc in self.finalDict.keys():
                    if self.coordinator.Read(SERV_NAME, ip, inst, txId, acc):
                        return SERV_NAME + "." + acc + " = " + str(self.finalDict[acc])
                else:
                    # abort if not found
                    self.coordinator.abortCommit(SERV_NAME, ip, inst, txId)
                    # delete our tentative transaction
                    with self.tentativeDictsLock:
                        del self.tentativeDicts[(ip,inst,txId)]
                    return "NOT FOUND"
        # we try and load final value
        else:
            if acc in self.finalDict.keys():
                if self.coordinator.Read(SERV_NAME, ip, inst, txId, acc):
                    return SERV_NAME + "." + acc + " = " + str(self.finalDict[acc])
                else:
                    # abort if not found
                    self.coordinator.abortCommit(SERV_NAME, ip, inst, txId)
                    return "NOT FOUND"

    def Withdraw(self, ip, inst, tid, acc, amount):
        print("Withdraw", ip, inst, tid, acc, amount)
        readValue = None
        # do we have a tentative transaction?
        if (ip, inst, tid) in self.tentativeDicts.keys():
            # do we have acc in the tentative transaction
            if acc in self.tentativeDicts[(ip,inst,tid)].keys():
                # then read the tentative value
                if self.coordinator.Read(SERV_NAME, ip, inst, tid, acc):
                    readValue = self.tentativeDicts[(ip,inst,tid)][acc]
                else:
                    print("Withdraw ABORT", ip, inst, tid)
                    return "NOT FOUND"
            # we do not have a tentative acc value
            else:
                # if we have a previous value
                if acc in self.finalDict.keys():
                    # then read prev value
                    if self.coordinator.Read(SERV_NAME, ip, inst, tid, acc):
                        readValue = self.finalDict[acc]
                # assign prev value to be 0                        
                else:
                    if self.coordinator.Read(SERV_NAME, ip, inst, tid, acc):
                        readValue = 0
                    else:
                        print("Withdraw ABORT", ip, inst, tid)
                        return "NOT FOUND"
        # we do not have tentative acc balance but still need to read previous value
        else:
            # if we have a previous value
            if acc in self.finalDict.keys():
                # then read prev value
                if self.coordinator.Read(SERV_NAME, ip, inst, tid, acc):
                    readValue = self.finalDict[acc]
            # assign prev value to be 0                        
            else:
                if self.coordinator.Read(SERV_NAME, ip, inst, tid, acc):
                    readValue = 0
                else:
                    print("Withdraw ABORT", ip, inst, tid)
                    return "NOT FOUND"
        
        assert readValue != None

        # now write the new value
        if self.coordinator.Write(SERV_NAME, ip, inst, tid, acc):
            with self.tentativeDictsLock:
                # we have transaction id already stored
                if (ip,inst,tid) in self.tentativeDicts.keys():
                    self.tentativeDicts[(ip,inst,tid)][acc] = readValue - float(amount)
                    print("Deposit tentativeDicts after:", ip, inst, tid, self.tentativeDicts)
                    return "OK"
                # NOTE INCORRECT: create a new tetative transaction
                # somehow the coordinatorAbort possibly triggered adn now we do not have
                # the transaction in our tentative dicts
                else:
                    # if we do not have tentative dicts then we return 
                    if (ip, inst, tid) not in self.tentativeDicts.keys():
                        return ""
                    else:
                        self.tentativeDicts.update({ (ip, inst, tid) : {acc : readValue - float(amount)} })
                        print("Deposit tentativeDicts after:", ip, inst, tid, self.tentativeDicts)
                        return "OK"
        else:
            print("Deposit ABORT", ip, inst, tid)
            return "ABORTED"        

    def Commit(self, ip, inst, txId):
        # TODO: MAKE SURE ALL BALANCES ARE POSITIVE
        print("Commit", ip, inst, txId)
        # we have something to commit
        print("Commit tentativeDicts prev:", self.tentativeDicts)
        print("Commit finalDicts prev:", self.finalDict)

        # determine if we have a negative balance
        # if we have a negative balance abort
        with self.tentativeDictsLock:
            if (ip,inst,txId) in self.tentativeDicts.keys():
                for balance in self.tentativeDicts[(ip,inst,txId)].values():
                    if balance < 0:
                        print("Commit found negative balance")
                        self.coordinator.abortCommit(SERV_NAME, ip, inst, txId)
                        del self.tentativeDicts[(ip, inst, txId)]
                        return "COMMIT ABORTED"

        # determine if we can commit
        flag = False
        try:
            flag = self.coordinator.Commit(SERV_NAME, ip, inst, txId)
        except:
            print("Pyro TraceBack server COMMIT")
            print("".join(Pyro4.util.getPyroTraceback()))
        if flag:
            with self.finalDictLock and self.tentativeDictsLock:
                print("HI")
                if (ip, inst, txId) in self.tentativeDicts.keys():
                    for acc, amount in self.tentativeDicts[(ip,inst,txId)].items():
                        self.finalDict.update({acc : amount})
                    del self.tentativeDicts[(ip, inst, txId)]
                    print("Commit tentativeDicts after:", self.tentativeDicts)
                    print("Commit finalDicts after:", self.finalDict)
                    return "COMMIT OK"
                # nothing to commit
                else:
                    self.coordinator.abortCommit(SERV_NAME, ip, inst, txId)
                    return "COMMIT ABORTED"
        else:
            self.coordinator.abortCommit(SERV_NAME, ip, inst, txId)
            return "COMMIT ABORTED"

    def coordinatorAbort(self, ip, inst, txId):
        # if there is a tentative transaction with this identifier
        # remove the tentative tx
        with self.tentativeDictsLock:
            if (ip,inst,txId) in self.tentativeDicts.keys():
                print("Abort", ip, inst, txId)
                print("coodrinatorAbort before ", self.tentativeDicts)
                del self.tentativeDicts[(ip,inst,txId)]
                print("coodrinatorAbort after", self.tentativeDicts)
                # send a client abort
                for client in self.clients:
                    if client[0] == ip and client[1] == inst:
                        c = Pyro4.Proxy(client[2])
                        c.Abort()
                        break
            else:
                print("No need to abort", ip, inst, txId)

    def clientAbort(self, ip, inst, txId):
        # must exist tentative transaction
        with self.tentativeDictsLock:
            if (ip,inst,txId) in self.tentativeDicts.keys():
                print("clientAbort", ip, inst, txId)
                # clear our tentative dictionary
                del self.tentativeDicts[(ip,inst,txId)]
                # notify the coordinator to delete
                self.coordinator.abortCommit(SERV_NAME, ip, inst, txId)
                print("clientAbort completed")
                return "CLIENT ABORTED"
            else:
                print("clientAbort failed")
                return "CLIENT ABORT FAILED"




def main():
    global SERV_NAME
    if len(sys.argv) < 2:
        print("USAGE: python3 server.py <SERV_NAME>")
        print("<SERV_NAME> is A, B, C, D, or E")
        return
    SERV_NAME = sys.argv[1].capitalize()
    print("You are server", SERV_NAME)
    name = "serv" + SERV_NAME
    offset = None
    if SERV_NAME == "A":
        offset = 0
    elif SERV_NAME == "B":
        offset = 1
    elif SERV_NAME == "C":
        offset = 2
    elif SERV_NAME == "D":
        offset = 3
    elif SERV_NAME == "E":
        offset = 4
    else:
        print("USAGE: python3 server.py <SERV_NAME>")
        print("<SERV_NAME> is A, B, C, D, or E")
        return
    assert offset != None
    Pyro4.Daemon.serveSimple(
            {
                Server: name
            },
            host = socket.gethostbyname(socket.gethostname()),
            port = 9090 + offset,
            ns = False)

if __name__=="__main__":
    main()