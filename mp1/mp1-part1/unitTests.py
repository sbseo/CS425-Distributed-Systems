# from isis import *
# from message import *
# from process import *
# import hashlib

# """
#     Tests for messasge.py
# """
# Msg = Message()

# # Test initialization
# print("UNIT: message.py, Message() Init")
# assert Msg.source == None
# assert Msg.messageId == None
# assert Msg.proposedSeq == None
# assert Msg.type == None
# assert Msg.sourceAcc == None
# assert Msg.targetAcc == None
# assert Msg.amount == None
# assert Msg.isDeliverable == False
# assert Msg.isRRep == False
# assert Msg.isSRep == False
# assert Msg.counter == 1

# # preprocess: Test deposit positive amount
# print("UNIT: message.py, preprocess deposit")
# yxpqg_dep_75 = "DEPOSIT yxpqg 75"

# Msg.preprocess(0, yxpqg_dep_75)
# m = hashlib.sha256()
# m.update(str.encode(yxpqg_dep_75))

# assert Msg.source == 0
# assert Msg.messageId == m.digest()
# assert Msg.proposedSeq == None
# assert Msg.type == 'DEPOSIT'
# assert Msg.sourceAcc == None
# assert Msg.targetAcc == "yxpqg"
# assert Msg.amount == 75
# assert Msg.isDeliverable == False
# assert Msg.isRRep == False
# assert Msg.isSRep == False

# # preprocess: Test Transfer
# print("UNIT: message.py, preprocess transfer")
# Msg = Message()
# wqkby_to_buyqa_transfer_15 = "TRANSFER wqkby -> buyqa 15"

# Msg.preprocess(0, wqkby_to_buyqa_transfer_15)
# m = hashlib.sha256()
# m.update(str.encode(wqkby_to_buyqa_transfer_15))

# assert Msg.source == 0
# assert Msg.messageId == m.digest()
# assert Msg.proposedSeq == None
# assert Msg.type == 'TRANSFER'
# assert Msg.sourceAcc == "wqkby"
# assert Msg.targetAcc == "buyqa"
# assert Msg.amount == 15
# assert Msg.isDeliverable == False
# assert Msg.isRRep == False
# assert Msg.isSRep == False

# # TODO: Message setters

# """
#     Tests for process.py
# """
# Proc = Process()

# # Test initialization
# print("UNIT: process.py, Process() Init")
# assert Proc.pid == None
# assert Proc.proposedSeq == None
# assert Proc.agreedSeq == None
# assert Proc.holdback == [] and len(Proc.holdback) == 0
# assert Proc.delivered == [] and len(Proc.delivered) == 0
# assert Proc.accountDict == {} and len(Proc.accountDict) == 0
# assert Proc.socketsDict == {} and len(Proc.socketsDict) == 0

# # assign pid
# Proc.assignPid(1)

# # TODO: Process Setters
# print("UNIT: process.py, assignPid")
# assert Proc.pid == 1

# # createNewMessage: Deposit
# print("UNIT: process.py, createNewMessage deposit")
# Proc = Process()
# Proc.assignPid(0)

# yxpqg_dep_75 = "DEPOSIT yxpqg 75"
# TempMsg = Proc.createNewMessage(yxpqg_dep_75)
# Msg = Message()
# Msg.preprocess(1, yxpqg_dep_75)
# m = hashlib.sha256()
# m.update(str.encode(yxpqg_dep_75))

# print(Proc.holdback)

# # assert Proc.holdback[0][1].source == 0
# # assert Proc.holdback[0][1].messageId == m.digest()
# # assert Proc.holdback[0][1].proposedSeq == None
# # assert Proc.holdback[0][1].type == 'DEPOSIT'
# # assert Proc.holdback[0][1].sourceAcc == None
# # assert Proc.holdback[0][1].targetAcc == "yxpqg"
# # assert Proc.holdback[0][1].amount == 75
# # assert Proc.holdback[0][1].isDeliverable == False
# # assert Proc.accountDict["yxpqg"] == 75

# # createNewMessage: Transfer
# print("UNIT: process.py, createNewMessage balance neg transfer")
# Proc = Process()
# Proc.assignPid(0)
# wqkby_to_buyqa_transfer_15 = "TRANSFER wqkby -> buyqa 15"
# TempMsg = Proc.createNewMessage(wqkby_to_buyqa_transfer_15)
# assert TempMsg == None
# assert Proc.holdback == []

# print("UNIT: process.py, createNewMessage balance valid transfer (new target acc)")
# Proc = Process()
# Proc.assignPid(0)
# Proc.accountDict.update({"wqkby": 15})

# wqkby_to_buyqa_transfer_15 = "TRANSFER wqkby -> buyqa 15"
# TempMsg = Proc.createNewMessage(wqkby_to_buyqa_transfer_15)
# # assert Proc.holdback[0] == TempMsg
# assert Proc.accountDict["wqkby"] == 0
# assert Proc.accountDict["buyqa"] == 15

# print("UNIT: process.py, createNewMessage balance valid transfer (old target acc)")
# Proc = Process()
# Proc.assignPid(0)
# Proc.accountDict.update({"wqkby": 15})
# Proc.accountDict.update({"buyqa": 15})

# wqkby_to_buyqa_transfer_15 = "TRANSFER wqkby -> buyqa 15"
# TempMsg = Proc.createNewMessage(wqkby_to_buyqa_transfer_15)
# assert Proc.accountDict["wqkby"] == 0
# assert Proc.accountDict["buyqa"] == 30

# print("UNIT: process.py, createNewMessage balance invalid transfer (source acc doesn't exist)")
# Proc = Process()
# Proc.assignPid(0)

# wqkby_to_buyqa_transfer_15 = "TRANSFER wqkby -> buyqa 15"
# TempMsg = Proc.createNewMessage(wqkby_to_buyqa_transfer_15)
# assert TempMsg == None
# assert len(Proc.accountDict) == 0

# # TODO:
# # process.py: createReceiverReply
# # process.py: createSenderReply

# """
#     Tests for isis.py
# """
# print("UNIT: process.py, propose seq")
# Proc = Process()
# Proc.assignPid(0)
# Proc.accountDict.update({"wqkby": 15})
# Proc.accountDict.update({"buyqa": 15})
# Proc.proposedSeq = 0
# Proc.agreedSeq = 0
# assert Isis.proposeSeq(Proc)

# print("UNIT: message.py, mutiple messages received by sender")
# Msg1, Msg2, Msg3, Msg4, Msg5, Msg6, Msg7, Msg8 = Message(), Message(), Message(), Message(), Message(), Message(), Message(), Message()
# Msg1.preprocess(1, 'DEPOSIT n 10')
# Msg2.preprocess(2, 'DEPOSIT n 20')
# Msg3.preprocess(3, 'DEPOSIT n 30')
# Msg4.preprocess(4, 'DEPOSIT n 40')
# Msg5.preprocess(5, 'TRANSFER n -> g 18')
# Msg6.preprocess(6, 'TRANSFER n -> g 18')
# Msg7.preprocess(7, 'TRANSFER n -> g 18')
# Msg8.preprocess(8, 'TRANSFER n -> g 18')
# m = hashlib.sha256()
# m.update(str.encode(yxpqg_dep_75))

# proposedNum = Isis.proposeSeq(Proc)
# Msg1.assignSeq(proposedNum)
# proposedNum = Isis.proposeSeq(Proc)
# Msg2.assignSeq(proposedNum)
# proposedNum = Isis.proposeSeq(Proc)
# Msg3.assignSeq(proposedNum)
# proposedNum = Isis.proposeSeq(Proc)
# Msg4.assignSeq(proposedNum)
# proposedNum = Isis.proposeSeq(Proc)
# Msg5.assignSeq(proposedNum)
# proposedNum = Isis.proposeSeq(Proc)
# Msg6.assignSeq(proposedNum)
# proposedNum = Isis.proposeSeq(Proc)
# Msg7.assignSeq(proposedNum)
# proposedNum = Isis.proposeSeq(Proc)
# Msg8.assignSeq(proposedNum)

# ml = [Msg1, Msg2, Msg3, Msg4, Msg5, Msg6, Msg7, Msg8]
# agreedNum = Isis.chooseAgreedNum(ml)
# Proc.agreedSeq = agreedNum
# Msg1.agreedSeq = agreedNum
# Isis.storeMsg(Proc, Msg1)
# Isis.storeMsg(Proc, Msg2)
# Isis.storeMsg(Proc, Msg3)
# print(Proc.agreedSeq)
# print(Proc.holdback)
# print("#")
# Isis.reorderMessages(Proc, Msg1)
# print(Proc.holdback)
# print("#")

# print(Isis.deliverableMsgs(Proc))
# print(Proc.holdback)
# print(Proc.holdback[0][1].isDeliverable)



# s = "b'TRANSFER n -> b 47\\n'"
# print(s.strip("b'").rstrip('\\n').rstrip("'"))

# s = ('172.22.94.48', 43734)
# print(s[0])


# newMsg = Message()

# # newMsg.preprocess(Proc, "DEPOSIT n 10")
# # newMsg.proposedSeq = Isis.proposeSeq(Proc)
# # Proc.proposedSeq = Isis.proposeSeq(Proc)
# # print("Here")
# # print(newMsg.proposedSeq)
# # print(Proc.proposedSeq)
# # print(newMsg.messageId)

print("hellp \n hello")


temp = list()
temp.append(str("11") + str("22"))
temp.append("1111")
print(str(temp))

for i in temp:
    i = 1
print(temp)



s = '3kjlsfk23jlkjgfg'
print(s[:5])