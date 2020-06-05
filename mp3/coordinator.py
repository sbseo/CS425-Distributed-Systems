import Pyro4
import socket
import threading
import sys
import config

SERV_A_URI = config.SERV_A_URI
SERV_B_URI = config.SERV_B_URI
SERV_C_URI = config.SERV_C_URI
SERV_D_URI = config.SERV_D_URI
SERV_E_URI = config.SERV_E_URI
NUM_SERVERS = None

Pyro4.config.SERIALIZER = 'marshal'

@Pyro4.expose
@Pyro4.behavior(instance_mode="single")
class Coordinator(object):
    def __init__(self):
        self.tsDict = {"A" : {}, "B" : {}, "C" : {}, "D" : {}, "E" : {}}
        self.tsDictLock = threading.Lock()
        # index = timestamp
        self.txIdList = []
        self.txIdListLock = threading.Lock()
        # Contains the accounts that a transaction is using
        self.txIdAccList = []
        self.txIdAccListLock = threading.Lock()
        self.deadTxId = set()
        # keep track of transactions that have been terminated
        self.deadTxIdLock = threading.Lock()
        self.txId = 0
        self.servA = Pyro4.Proxy(SERV_A_URI)
        self.servB = Pyro4.Proxy(SERV_B_URI)
        self.servC = Pyro4.Proxy(SERV_C_URI)
        self.servD = Pyro4.Proxy(SERV_D_URI)
        self.servE = Pyro4.Proxy(SERV_E_URI)
    
    def getTimeStampRead(self, serv, acc):
        # if the account already has a timestamp tuple
        if acc in self.tsDict[serv].keys():
            return self.tsDict[serv][acc][0] # read ts
        # else create a new timestamp tuple
        else:
            with self.tsDictLock:
                # initialize to -1 as all txId are >= 0
                self.tsDict[serv].update({acc : (-1,-1)})
            return -1

    def getTimeStampWrite(self, serv, acc):
        # if the account already has a timestamp tuple
        if acc in self.tsDict[serv].keys():
            return self.tsDict[serv][acc][1] #= write ts
        # else create a new timestamp tuple
        else:
            with self.tsDictLock:
                # initialize to -1 as all txId are >= 0
                self.tsDict[serv].update({acc : (-1,-1)})
            return -1
    
    def updateTimeStampRead(self, serv, acc, ts):
        print(self.tsDict)
        print(self.tsDict[serv])
        print(self.tsDict[serv][acc])
        with self.tsDictLock:
            tsTuple = self.tsDict[serv][acc]
            newTuple = (ts, tsTuple[1])
            self.tsDict[serv][acc] = newTuple

    def updateTimeStampWrite(self, serv, acc, ts):
        print(self.tsDict)
        print(self.tsDict[serv])
        print(acc)
        print(self.tsDict[serv][acc])
        with self.tsDictLock:
            print("A")
            tsTuple = self.tsDict[serv][acc]
            print("B", tsTuple)
            newTuple = (tsTuple[0], ts)
            print("C", newTuple)
            self.tsDict[serv][acc] = newTuple
            print("D")
        print("FUCK")
    
    def abortNewerTx(self, serv, ip, inst, tid, acc, rw):
        print("abortNewerTx:", serv, ip, inst, tid, acc)
        print("abortNewerTx:", self.txIdList)
        print("abortNewerTx:", self.txIdAccList)
        # this is the timestamp of the transaction we want to go through
        tsRevive = self.txIdList.index((ip,inst,tid))
        print("A", tsRevive)
        # list of transactions to abort
        toAbort = []
        print("B")
        # find larger ts with (serv, acc)
        for idx in range(tsRevive + 1, len(self.txIdList)):
            print((serv,acc), "||", self.txIdAccList[idx])
            if self.txIdAccList[idx] != None:
                if (serv, acc) in self.txIdAccList[idx]:
                    toAbort.append(idx)
        # call abort on the relevant transactions
        print(toAbort)
        with self.txIdAccListLock and self.txIdListLock:
            for idx in toAbort:
                print(idx, self.txIdList[idx])
                tup = self.txIdList[idx]
                # send abort signal to server
                for i in range(NUM_SERVERS):
                    if i == 0:
                        self.servA.coordinatorAbort(tup[0], tup[1], tup[2])
                    elif i == 1:
                        self.servB.coordinatorAbort(tup[0], tup[1], tup[2])
                    elif i == 2:
                        self.servC.coordinatorAbort(tup[0], tup[1], tup[2])
                    elif i == 3:
                        self.servD.coordinatorAbort(tup[0], tup[1], tup[2])
                    elif i == 4:
                        self.servE.coordinatorAbort(tup[0], tup[1], tup[2])

                # also remove the transactions frome our lists
                self.txIdList[idx] = None
                self.txIdAccList[idx] = None
        # reset our timestamps
        if rw == "WRITE":
            self.updateTimeStampWrite(serv, acc, self.txIdList.index((ip,inst,tid)))
        elif rw == "READ":
            self.updateTimeStampRead(serv, acc, self.txIdList.index((ip,inst,tid)))
        else:
            self.updateTimeStampWrite(serv, acc, self.txIdList.index((ip,inst,tid)))
            self.updateTimeStampRead(serv, acc, self.txIdList.index((ip,inst,tid)))

    def Begin(self, ip, inst, tid):
        # initialize txIdList and acc list when we receive a begin
        with self.txIdListLock:
            if (ip, inst, tid) not in self.txIdList:
                self.txIdList.append((ip, inst, tid))
                with self.txIdAccListLock:
                    self.txIdAccList.append(set())

    def Read(self, serv, ip, inst, tid, acc):
        print("coordinatorRead: serv", serv, "ip", ip, "inst", inst, "tid", tid, "acc", acc)
        print("coordinatorRead txIdList:", self.txIdList)
        # if we have already assigned a transaction ID
        if (ip,inst,tid) in self.txIdList:
            ts = self.txIdList.index((ip,inst,tid))
            rts = self.getTimeStampRead(serv, acc)
            wts = self.getTimeStampWrite(serv, acc)
            # if we can read return True
            if wts > ts:
                with self.txIdAccListLock:
                    self.txIdAccList[ts].add((serv, acc))
                self.abortNewerTx(serv, ip, inst, tid, acc, "READ")
                print("coordinatorRead REP SUCC: serv", serv, "ip", ip, "inst", inst, "tid", tid, "acc", acc)
                print("coordinatorRead tsDict after:", self.tsDict)
                print("coordinatorRead txIdList after:", self.txIdList)
                return True
            else:
                # update active acc
                with self.txIdAccListLock:
                    self.txIdAccList[ts].add((serv, acc))
                self.updateTimeStampRead(serv, acc, max(ts, rts))
                print("coordinatorRead SUCC: serv", serv, "ip", ip, "inst", inst, "tid", tid, "acc", acc)
                print("coordinatorRead tsDict after:", self.tsDict)
                print("coordinatorRead txIdList after:", self.txIdList)
                return True
        # else we need to create a transaction ID
        else:
            # create new timestamp and update active accs
            with self.txIdListLock:
                self.txIdList.append((ip, inst, tid))
            with self.txIdAccListLock:
                self.txIdAccList.append(set())
            ts = self.txIdList.index((ip,inst,tid))
            rts = self.getTimeStampRead(serv, acc)
            wts = self.getTimeStampWrite(serv, acc)
            # if we can read return True
            if wts > ts:
                with self.txIdAccListLock:
                    self.txIdAccList[ts].add((serv, acc))
                self.abortNewerTx(serv, ip, inst, tid, acc, "READ")
                print("coordinatorRead REP SUCC: serv", serv, "ip", ip, "inst", inst, "tid", tid, "acc", acc)
                print("coordinatorRead tsDict after:", self.tsDict)
                return True
            else:
                # update active acc
                with self.txIdAccListLock:
                    self.txIdAccList[ts].add((serv, acc))
                self.updateTimeStampRead(serv, acc, max(ts, rts))
                print("coordinatorRead SUCC: serv", serv, "ip", ip, "inst", inst, "tid", tid, "acc", acc)
                print("coordinatorRead tsDict after:", self.tsDict)
                return True
    
    def Write(self, serv, ip, inst, tid, acc):
        print("coordinatorWrite: serv", serv, "ip", ip, "inst", inst, "tid", tid, "acc", acc)
        # if we have already assigned a transaction ID
        if (ip,inst,tid) in self.txIdList:
            ts = self.txIdList.index((ip,inst,tid))
            rts = self.getTimeStampRead(serv, acc)
            wts = self.getTimeStampWrite(serv, acc)
            print("A", ts, rts, wts)
            # if we can write return True
            if rts > ts or wts > ts:
                with self.txIdAccListLock:
                    self.txIdAccList[ts].add((serv, acc))
                self.abortNewerTx(serv, ip, inst, tid, acc, "WRITE")
                print("coordinatorWrite REP SUCC: serv", serv, "ip", ip, "inst", inst, "tid", tid, "acc", acc)
                print("coordinatorWrite tsDict after:", self.tsDict)
                # print("coordinatorWrite FAIL: serv", serv, "ip", ip, "inst", inst, "tid", tid, "acc", acc)
                return True
            else:
                with self.txIdAccListLock:
                    self.txIdAccList[ts].add((serv, acc))
                self.updateTimeStampWrite(serv, acc, ts)
                print("coordinatorWrite SUCC: serv", serv, "ip", ip, "inst", inst, "tid", tid, "acc", acc)
                print("coordinatorWrite tsDict after:", self.tsDict)
                return True
        # else we need to create a transaction ID
        else:
            with self.txIdListLock:
                self.txIdList.append((ip, inst, tid))
            with self.txIdAccListLock:
                self.txIdAccList.append(set())
            ts = self.txIdList.index((ip,inst,tid))
            rts = self.getTimeStampRead(serv, acc)
            wts = self.getTimeStampWrite(serv, acc)
            print("B", ts, rts, wts)
            # if we can write return True
            if rts > ts or wts > ts:
                with self.txIdAccListLock:
                    self.txIdAccList[ts].add((serv, acc))
                self.abortNewerTx(serv, ip, inst, tid, acc, "WRITE")
                print("coordinatorWrite REP SUCC: serv", serv, "ip", ip, "inst", inst, "tid", tid, "acc", acc)
                print("coordinatorWrite tsDict after:", self.tsDict)
                # print("coordinatorWrite FAIL: serv", serv, "ip", ip, "inst", inst, "tid", tid, "acc", acc)
                return True
            else:
                with self.txIdAccListLock:
                    self.txIdAccList[ts].add((serv, acc))
                self.updateTimeStampWrite(serv, acc, ts)
                print("coordinatorWrite SUCC: serv", serv, "ip", ip, "inst", inst, "tid", tid, "acc", acc)
                print("coordinatorWrite tsDict after:", self.tsDict)
                return True
    
    def abortCommit(self, serv, ip, inst, tid):
        print("abortCommit", serv, ip, inst, tid)
        # check that this current transaction is the current transaction list
        with self.txIdAccListLock and self.txIdListLock and self.deadTxIdLock:
            if (ip,inst,tid) in self.txIdList:
                ts = self.txIdList.index((ip,inst,tid))
                tup = self.txIdList[ts]
                for i in range(NUM_SERVERS):
                    if i == 0 and "A" != serv:
                        self.servA.coordinatorAbort(tup[0], tup[1], tup[2])
                    elif i == 1 and "B" != serv:
                        self.servB.coordinatorAbort(tup[0], tup[1], tup[2])
                    elif i == 2 and "C" != serv:
                        self.servC.coordinatorAbort(tup[0], tup[1], tup[2])
                    elif i == 3 and "D" != serv:
                        self.servD.coordinatorAbort(tup[0], tup[1], tup[2])
                    elif i == 4 and "E" != serv:
                        self.servE.coordinatorAbort(tup[0], tup[1], tup[2])
                print("Commit found tx with ts", ts)
                self.txIdList[ts] = None
                self.txIdAccList[ts] = None
                # also add to dead transactions
                self.deadTxId.add((ip,inst,tid))
                print("aborted commit", serv, ip, inst, tid)
                return True
            # if someone has already terminated the transaction for you
            elif (ip,inst,tid) in self.deadTxId:
                print("Someone has already aborted for you", serv, "!")
                return True
            else:
                print("failed to server abort")
                return False
    
    def abortInMiddle(self, serv, ip, inst, tid):
        print("abortInMiddle", serv, ip, inst, tid)
        print(self.txIdList)
        print(self.txIdAccList)
        if (ip,inst,tid) in self.txIdList:
            ts = self.txIdList.index((ip,inst,tid))
            print("Commit found tx with ts", ts)
            with self.txIdListLock:
                self.txIdList[ts] = None
            with self.txIdAccListLock:
                self.txIdAccList[ts] = None
            # also add to dead transactions
            with self.deadTxIdLock:
                self.deadTxId.add((ip,inst,tid))
            print("aborted in middle of tx", serv, ip, inst, tid)
            return True
        # if someone has already terminated the transaction for you
        elif (ip,inst,tid) in self.deadTxId:
            print("Someone has already aborted for you", serv, "!")
            return True
        else:
            print("no transaction to abort in coordinator yet")
            return True

    def Commit(self, serv, ip, inst, tid):
        print("Commit", serv, ip, inst, tid)
        # check that this current transaction is the current transaction list
        if (ip,inst,tid) in self.txIdList:
            ts = self.txIdList.index((ip,inst,tid))
            print("Commit found tx with ts", ts)
            # check if there are any previous transactions with tid less than
            # ts that are using same resources
            with self.txIdAccListLock and self.txIdListLock:
                for idx in range(ts, -1, -1):
                    # do they share accessed accounts?
                    if ts != idx and self.txIdAccList[idx] != None:
                        for accTemp in self.txIdAccList[ts]:
                            if accTemp in self.txIdAccList[idx]:
                                print("Found previous uncommited transaction", idx, ", aborted.")
                                self.txIdAccList[ts] = None
                                self.txIdList[ts] = None
                                return False
                # check if there are any future/pending transactions that are using the same accouts
                for idx in range(ts, len(self.txIdAccList)):
                    # do they share accessed accounts?
                    if ts != idx and self.txIdAccList[idx] != None and self.txIdAccList[ts] != None:
                        for accTemp in self.txIdAccList[ts]:
                            # has accessed the account
                            if accTemp in self.txIdAccList[idx]:
                                print("Found future uncommited transaction", idx, "need to abort future tx if higher wts.")
                                print(self.txIdList)
                                tup = self.txIdList[idx]
                                print(tup)
                                for i in range(NUM_SERVERS):
                                    print(i)
                                    if i == 0:
                                        self.servA.coordinatorAbort(tup[0], tup[1], tup[2])
                                        # ts = idx
                                        # rts = self.getTimeStampRead("A", accTemp[1])
                                        # wts = self.getTimeStampWrite("A", accTemp[1])
                                        # if wts > ts:
                                        #     self.servA.coordinatorAbort(tup[0], tup[1], tup[2])
                                        #     self.updateTimeStampWrite(accTemp[0], accTemp[1], self.txIdList.index((ip,inst,tid)))
                                        #     self.updateTimeStampRead(accTemp[0], accTemp[1], self.txIdList.index((ip,inst,tid)))
                                    elif i == 1:
                                        self.servB.coordinatorAbort(tup[0], tup[1], tup[2])
                                    elif i == 2:
                                        self.servC.coordinatorAbort(tup[0], tup[1], tup[2])
                                    elif i == 3:
                                        self.servD.coordinatorAbort(tup[0], tup[1], tup[2])
                                    elif i == 4:
                                        self.servE.coordinatorAbort(tup[0], tup[1], tup[2])
                                print("A")
                                self.txIdList[idx] = None
                                print("B")
                                self.txIdAccList[idx] = None
                                print("C")
                                # self.updateTimeStampWrite(accTemp[0], accTemp[1], self.txIdList.index((ip,inst,tid)))
                                print("D")
                                # self.updateTimeStampRead(accTemp[0], accTemp[1], self.txIdList.index((ip,inst,tid)))
                                # return False
            print("Commit no conflicting ts found. Finish commit")
            # clear the lists to none
            with self.txIdListLock:
                self.txIdList[ts] = None
            with self.txIdAccListLock:
                self.txIdAccList[ts] = None
            # also keep track of now dead transactions
            with self.deadTxIdLock:
                self.deadTxId.add((ip,inst,tid))
            return True
        # another server has already initiated the commit and has cleared the coordinator
        # therefoer we can just reutrn true here because another server has done all the work
        elif (ip,inst,tid) in self.deadTxId:
            print("Commit another server has already commited for you", serv, "!")
            return True
        else:
            print("Commit transaction does not exist")
            return False

def main():
    global NUM_SERVERS
    if len(sys.argv) < 2:
        print("USAGE: python3 coordinator.py <NUM_SERVERS>")
        print("NUM_SERVERS is a number >0 representing the number of servers running")
        return
    numserv = int(sys.argv[1])
    NUM_SERVERS = numserv
    assert NUM_SERVERS > 0
    Pyro4.Daemon.serveSimple(
            {
                Coordinator: "coordinator"
            },
            host = socket.gethostbyname(socket.gethostname()),
            port = 8080,
            ns = False)

if __name__=="__main__":
    main()