
'''
    Message

    Description:
        It contains received message information

        INTRODUCE 10 127.0.0.1 2010"
        TRANSACTION 1584925234.965515 654a7cbfc8f92b6a05cf2217a4d5a501 3 5 18"
'''
class Message:
    def __init__(self, data):
        self.data = data
        self.command, self.nodeNum, self.ip, self.port, self.timeStamp, self.transactionID, self.source, self.dest, self.amount = [None] * 9
        self.preProcessing(data)

    def preProcessing(self, data):
        string = self.data
        if string[0] == "INTRODUCE":
            self.command, self.nodeNum, self.ip, self.port = string[0], string[1], string[2], string[3]

        elif string[0] == "TRANSACTION":
            self.command, self.timeStamp, self.transactionID, self.source, self.dest, self.amount = string[0], string[1], string[2], string[3], string[4], string[5]

        elif string[0] == "INTRO_CONNECT":
            self.command, self.ip, self.nodeNum, self.port = string[0], string[1], string[2], string[3]

        else:
            pass

    