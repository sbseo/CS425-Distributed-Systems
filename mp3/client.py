import Pyro4
import sys
import socket
import threading
import config 

MY_IP = socket.gethostbyname(socket.gethostname())
MY_INST = 0
MY_URI = None

# TODO: Temporary URI
SERV_A_URI = config.SERV_A_URI
SERV_B_URI = config.SERV_B_URI
SERV_C_URI = config.SERV_C_URI
SERV_D_URI = config.SERV_D_URI
SERV_E_URI = config.SERV_E_URI
SERV_A = None
SERV_B = None
SERV_C = None
SERV_D = None
SERV_E = None

inTransaction = False # mark whether we are currently in a tx
txId = 0 # init transaction ID

Pyro4.config.SERIALIZER = 'marshal'

@Pyro4.expose
class ClientAborter(object):
	def __init__(self):
		"""
		"""
	def Abort(self):
		global inTransaction
		global txId
		if inTransaction == True:
			inTransaction = False
			print("ClientAborter ABORTED")
			txId += 1

def connectToAll():
	sys.execepthook = Pyro4.util.excepthook
	return Pyro4.Proxy(SERV_A_URI), \
		Pyro4.Proxy(SERV_B_URI), \
		Pyro4.Proxy(SERV_C_URI), \
		Pyro4.Proxy(SERV_D_URI), \
		Pyro4.Proxy(SERV_E_URI)

"""
	parseCommand
	Inputs:
		cmd: A string
	Outputs:
		cmdType: The type of command
		server: The server ID we wish to contact
		acc: Account ID
		amount: THe amount of money for the operation
	Description:
		Parse the command input via CLI and
		return the cmdType, server, acc, and amount
		If the value of any of these are not present they are None
"""
def parseCommand(cmd):
	splitted = cmd.split()
	cmdType = None
	server = None
	acc = None
	amount = None
	assert len(splitted) <= 3
	for i in range(len(splitted)):
		if i == 0:
			cmdType = splitted[i]
		elif i == 1:
			server = splitted[i].split('.')[0].capitalize()
			acc = splitted[i].split('.')[1]
		elif i == 2:
			amount = splitted[i]
	return cmdType, server, acc, amount

def aborter():
	global MY_URI
	daemon = Pyro4.Daemon(host=socket.gethostbyname(socket.gethostname()))
	MY_URI = daemon.register(ClientAborter)
	daemon.requestLoop()
"""
	main loop
"""
def main():
	global MY_INST
	global txId
	global inTransaction
	if len(sys.argv) < 3:
		print("USAGE: python3 client.py <INSTACE_ID> <NUM_SERVERS>")
		print("We assume that 1 <= NUM_SERVERS <= 5")
		print("If you are using one server please spawn server A")
		print("If you are using two servers please spawn server A and B")
		print("If you are using three servers please spawn server A, B, and C")
		print("If you are using four servers please spawn server A, B, C, and D")
		print("If you are using five servers please spawn server A, B, C, D, and E")
		return
	MY_INST = sys.argv[1]
	NUM_SERVERS = int(sys.argv[2])
	print("You are instance ID", MY_INST, "on", MY_IP)
	SERV_A, SERV_B, SERV_C, SERV_D, SERV_E = connectToAll()
	servProxyDict = {"A" : SERV_A, "B" : SERV_B, "C" : SERV_C, "D" : SERV_D, "E" : SERV_E}

	aborterThread = threading.Thread(target=aborter, args=())
	aborterThread.start()
	
	while True:
		cmd = input()
		cmdType, server, acc, amount = parseCommand(cmd)
		
		# Begin a transaction
		if inTransaction == False and (cmdType == "BEGIN" or cmdType == "begin"):
			inTransaction = True
			print("client", MY_IP, MY_INST, "beginning new transaction with ID", (MY_IP, MY_INST, txId))
			for i in range(NUM_SERVERS):
				if i == 0:
					ret = SERV_A.Begin(MY_IP, MY_INST, txId, MY_URI)
					print(ret)
				elif i == 1:
					ret = SERV_B.Begin(MY_IP, MY_INST, txId, MY_URI)
					print(ret)
				elif i == 2:
					ret = SERV_C.Begin(MY_IP, MY_INST, txId, MY_URI)
					print(ret)
				elif i == 3:
					ret = SERV_D.Begin(MY_IP, MY_INST, txId, MY_URI)
					print(ret)
				elif i == 4:
					ret = SERV_E.Begin(MY_IP, MY_INST, txId, MY_URI)
					print(ret)
		# otherwise currently in transaction
		elif inTransaction == True:
			if (cmdType == "DEPOSIT" or cmdType == "deposit") and acc != None and amount != None:
				print("client", MY_IP, MY_INST, "txId", txId, "deposit", amount, "into", acc)
				try:
					ret = servProxyDict[server].Deposit(MY_IP, MY_INST, txId, acc, amount)
					print(ret)
				except:
					print("Pyro Traceback DEPOSIT")
					print("".join(Pyro4.util.getPyroTraceback()))
			elif cmdType == "BALANCE" or cmdType == "balance":
				print("client", MY_IP, MY_INST, "txId", txId, "balance of acc", acc)
				ret = servProxyDict[server].Balance(MY_IP, MY_INST, txId, acc)
				print(ret)
				# if we fail out abort
				if ret == "NOT FOUND":
					inTransaction = False
					txId += 1
			elif cmdType == "WITHDRAW" or cmdType == "withdraw":
				print("client", MY_IP, MY_INST, "txId", txId, "withdraw", amount, "from", acc)
				ret = servProxyDict[server].Withdraw(MY_IP, MY_INST, txId, acc, amount)
				print(ret)
			elif cmdType == "COMMIT" or cmdType == "commit":
				print("client", MY_IP, MY_INST, "txId", txId, "commit")
				for i in range(NUM_SERVERS):
					if i == 0:
						try:
							ret = SERV_A.Commit(MY_IP, MY_INST, txId)
							print(ret)
						except:
							print("Pyro Traceback COMMIT A")
							print("".join(Pyro4.util.getPyroTraceback()))
					elif i == 1:
						try:
							ret = SERV_B.Commit(MY_IP, MY_INST, txId)
							print(ret)
						except:
							print("Pyro Traceback COMMIT B")
							print("".join(Pyro4.util.getPyroTraceback()))
					elif i == 2:
						try:
							ret = SERV_C.Commit(MY_IP, MY_INST, txId)
							print(ret)
						except:
							print("Pyro Traceback COMMIT C")
							print("".join(Pyro4.util.getPyroTraceback()))
					elif i == 3:
						try:
							ret = SERV_D.Commit(MY_IP, MY_INST, txId)
							print(ret)
						except:
							print("Pyro Traceback COMMIT D")
							print("".join(Pyro4.util.getPyroTraceback()))
					elif i == 4:
						try:
							ret = SERV_E.Commit(MY_IP, MY_INST, txId)
							print(ret)
						except:
							print("Pyro Traceback COMMIT E")
							print("".join(Pyro4.util.getPyroTraceback()))
				txId += 1
				inTransaction = False
			elif cmdType == "ABORT" or cmdType == "abort":
				print("client", MY_IP, MY_INST, "txId", txId, "abort")
				for i in range(NUM_SERVERS):
					if i == 0:
						ret = SERV_A.clientAbort(MY_IP, MY_INST, txId)
						print(ret)
					elif i == 1:
						ret = SERV_B.clientAbort(MY_IP, MY_INST, txId)
						print(ret)
					elif i == 2:
						ret = SERV_C.clientAbort(MY_IP, MY_INST, txId)
						print(ret)
					elif i == 3:
						ret = SERV_D.clientAbort(MY_IP, MY_INST, txId)
						print(ret)
					elif i == 4:
						ret = SERV_E.clientAbort(MY_IP, MY_INST, txId)
						print(ret)
				inTransaction = False
				txId += 1
			else:
				print("client: INVALID COMMAND TYPE")
		else:
			print("client: PLEASE BEGIN FIRST")

if __name__=="__main__":
    main()