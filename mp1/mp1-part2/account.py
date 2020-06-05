class Account:
    """
        __init__
        Inputs:
            None
        Outputs:
            None
        Description:
            accountId will be set to default of None.
            This is because it is possible for the hash to equal -1 or 0.
            It also also assigns the initial balance of 0
    """
    def __init__(self):
        self.accountId = None
        self.balance = 0
    
    """
        assignNode
        Inputs:
            nodeIdIn: Input node ID number
        Outputs:
            None
        Description:
            This assigns a nodeId to this instance of node
    """
    def assignNode(self, nodeIdIn):
        self.nodeId = nodeIdIn

    """
        updateBalance
        Inputs:
            amount: Amount to decrement or increment the balance by
        Outputs:
            None
        Description:
            This function updates the balance off the account
    """
    def updateBalance(self, amount):
        self.balance = self.balance + amount



