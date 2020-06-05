import threading

class Account():
	def __init__(self):
		self.accDict = {0 : 1000}
		self.accDictLock = threading.Lock()

	def resetBalances(self):
		with self.accDictLock:
			for key in self.accDict.keys():
				self.accDict.update({key : 0})
			self.accDict.update({0 : 1000})

	def updateBalance(self, source, dest, amount):
		with self.accDictLock:
			if dest not in self.accDict.keys():
					self.accDict.update({dest : 0})
			if source not in self.accDict.keys():
					self.accDict.update({source : 0})
			if source == 0:
				if dest not in self.accDict.keys():
					self.accDict.update({dest : amount })
				else:
					self.accDict[dest] += amount
			else:
				if self.accDict[source] - amount >= 0:
					if dest not in self.accDict.keys():
						self.accDict.update({dest : amount})
						self.accDict[source] -= amount
					else:
						self.accDict[dest] += amount
						self.accDict[source] -= amount

	def checkValidTransaction(self, source, dest, amount):
		with self.accDictLock:
			if dest not in self.accDict.keys():
					self.accDict.update({dest : 0})
			if source not in self.accDict.keys():
					self.accDict.update({source : 0})
			if source == 0:
				return True
			else:
				if source in self.accDict.keys():
					if self.accDict[source] - amount >= 0:
						return True
					else:
						return False
				else:
					return False

# a = Account()
# print(a.accDict)
# print(a.checkValidTransaction("0", "1", 100))
# a.updateBalance("0","1",100)
# print(a.accDict)
# print(a.checkValidTransaction("1", "1", 100))
# a.updateBalance("1","2",200)
# print(a.checkValidTransaction("1", "2", 200))
# print(a.accDict)
# print(a.checkValidTransaction("1", "2", 50))
# a.updateBalance("1","2",50)
# print(a.accDict)