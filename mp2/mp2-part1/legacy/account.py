class Bank():
	def __init__(self):
		self.accs = {0 : 1000}

	def addAcc(self, id):
		self.accs.update({id : 0})
	
	# TODO: THIS NEEDS TO ACOUNT FOR NEGATIVE BALANCES?
	def updateBalance(self, transaction):
		assert transaction.split()[0] == "TRANSACTION"
		splitted = transaction.split()
		
		# do not modify account 0
		# NOTE DEFAULT ACC 0 IS ALWAYS BALANCE 1000
		if splitted[3] == "0":
			if splitted[4] not in self.accs.keys():
				self.addAcc(splitted[4])
			self.accs[splitted[4]] += float(splitted[5])
		else:
			assert splitted[3] in self.accs.keys()
			if splitted[4] not in self.accs.keys():
				self.addAcc(splitted[4])
			self.accs[splitted[4]] += float(splitted[5])
			self.accs[splitted[3]] -= float(splitted[5])

# transaction = "TRANSACTION 1585093425.294339 756e9457eec7e9c076382c76058f3b85 0 1 89"

# test = Bank()
# test.updateBalance(transaction)

# transaction = "TRANSACTION 1585093425.294339 756e9457eec7e9c076382c76058f3b85 1 2 8"
# test.updateBalance(transaction)

# print(test.accs)