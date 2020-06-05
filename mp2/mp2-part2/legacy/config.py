import queue, threading

'''
    CONFIGURATION FILE

    Description:
        Please setup your HOST here.
        HOST is IP Address for mp2_service.py
        
            python3 mp2_service.py 9999 0.5
'''

# NOTE: FOR LOCAL TESTING 
SERVICE_HOST, SERVICE_PORT = 'localhost', 9998


# NOTE: FOR ONLINE USE
# SERVICE_HOST, SERVICE_PORT = "172.22.94.48", 9999 


'''
    Global
        Description:
            Please feel free to add more global variables below!
'''
def init():
    global THREADS
    global MAINLOCK, COMMAND, MYNAME, MYIP, MYPORT, MESSAGES, NODES, STOPFLAG

    MAINLOCK = threading.RLock()
    COMMAND, MYNAME, MYIP, MYPORT = [None] * 4
    STOPFLAG = False

    THREADS = dict() # Stores connections for service server and introduced clients(upto 4)
    MESSAGES = queue.Queue() # Stores messages from transaction 
    NODES = dict() # Stores info regarding introduced clients
