import queue, threading

'''
    CONFIGURATION FILE

    Description:
        Please setup your HOST here.
        HOST is IP Address for mp2_service.py
        
            python3 mp2_service.py 9999 0.5
'''

# NOTE: FOR LOCAL TESTING 
# SERVICE_HOST, SERVICE_PORT = 'localhost', 9998
# vm1, vm2, vm3, vm4, vm5, vm6, vm7, vm8, vm9 = 'localhost', 'localhost', 'localhost', 'localhost', 'localhost', 'localhost', 'localhost', 'localhost', 'localhost'
# vmList = [vm1, vm2, vm3, vm4, vm5, vm6, vm7, vm8, vm9]


# NOTE: FOR ONLINE USE
SERVICE_HOST, SERVICE_PORT = "172.22.94.48", 9998
# vm1, vm2, vm3, vm4, vm5, vm6, vm7, vm8, vm9 = '172.22.94.48', '172.22.156.49', '172.22.158.49', '172.22.94.49', '172.22.156.50', '172.22.158.50', '172.22.94.50', '172.22.156.51', '172.22.158.51'
# vmList = [vm1, vm2, vm3, vm4, vm5, vm6, vm7, vm8, vm9]


'''
    Global
        Description:
            Please feel free to add more global variables below!
'''
def init():
    global THREADS
    global MAINLOCK, COMMAND, MYNAME, MYIP, MYPORT, MESSAGES, NODES, STOPFLAG, \
            BW, BW_STACK, BW_LOCK, MSG_ARRIVED_TIME, BLOCK_APPEAR_TIME, BLOCK_ARRIVED_TIME, \
            NUM_CHAIN_SPLIT

    global INSTANCEID, BASEPORT
    # global gossipMsgs, gossiplock, receivedTrans, receivedTranslock

    MAINLOCK = threading.RLock()
    COMMAND, MYNAME, MYIP, MYPORT = [None] * 4
    STOPFLAG = False

    THREADS = dict() # Stores connections for service server and introduced clients(upto 4)
    MESSAGES = queue.Queue() # Stores messages from transaction 
    NODES = dict() # Stores info regarding introduced clients

    # Bandwidth Recorder
    BW = list()
    BW_STACK = 0
    BW_LOCK = threading.RLock()

    # Propoagation Delay Recorder
    MSG_ARRIVED_TIME = dict()

    # Congestion Delay Recorder
    BLOCK_APPEAR_TIME = dict()

    # Block Propoagation Delay Recorder
    BLOCK_ARRIVED_TIME = dict()

    # Chain Split Recorder
    NUM_CHAIN_SPLIT = 0