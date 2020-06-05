import os, sys, socket, socketserver, time, threading, signal, queue
import config
from sysin import SystemInput
import network
import threadFunc

TEST_MESSAGES = [
    'TRANSACTION 1585069320.893857 c482e58cf709b75c4728720d611112a0 0 1 76\n',
    'TRANSACTION 1585069320.932648 f6b4a0a57d05fae355070c8957f2bd20 1 2 49\n',
    'TRANSACTION 1585069321.118395 b6ddecd6917e04e2b6bc909d922ca541 1 3 1\n',
    'TRANSACTION 1585069321.518087 48b2ba582e211a204cc47b495cb78448 1 4 15\n',
    'TRANSACTION 1585069321.600986 4af55a86db117c2c5553996ca927d06c 4 2 5\n',
    'TRANSACTION 1585069323.666364 a93655ebabf510005349d699929e89be 2 1 45\n'
    ]

def test():
    t = network.myThread(1, "Service Thread", 1)

    # test incomplete first message
    print("TESTING INCOMPLETE FIRST MESSAGE")
    m = TEST_MESSAGES[0][:5]
    print(m)
    ret = t.serialDecode(m)
    assert ret == None
    print(t.prevMessage)
    print("##")

    # parse 1 full messages
    print("TESTING ONE FULL MESSAGE")
    m = TEST_MESSAGES[0]
    print(m)
    t.firstMessage = True
    ret = t.serialDecode(m)
    print(ret)
    print("##")

    # parse greater than one message at a time
    print("TESTING THREE MESSAGES AT A TIME")
    m = TEST_MESSAGES[0] + TEST_MESSAGES[1] + TEST_MESSAGES[2]
    print(m)
    t.firstMessage = True
    ret = t.serialDecode(m)
    print(ret)
    print("##")
    
    # parse one message that is not sent fully all at once
    print("TEST ONE CHAR AT A TIME MESSAGE")
    t.firstMessage = True
    m = TEST_MESSAGES[0]
    for idx in range(len(m)):
        ret = t.serialDecode(m[idx])
        if ret != None:
            print(ret, end="aaaaaaaa")

    # parse buffer that contains 1.5 full messages and then 0.5 full messages
    print("TEST 1.5 FULL MESSAGE THEN 0.5 MESSAGE")
    t.firstMessage = True
    m = TEST_MESSAGES[0] + TEST_MESSAGES[1][:5]
    m2 = TEST_MESSAGES[1][5:]
    ret = t.serialDecode(m)
    print(ret)
    ret = t.serialDecode(m2)
    print(ret)
    
    return 0
''' 
    Main
    
    Description:
        Mostly manages threads
'''
if __name__ == '__main__':
    # test()
    # exit()

    """ Load Global Variables """
    config.init()
    
    """ User input starts from here """
    # Saves command line information
    newSys = SystemInput()
    COMMAND, MYNAME, MYIP, MYPORT = newSys.run()

    # Setup ctrl+c handler: signal killer
    signal.signal(signal.SIGINT, SystemInput.signal_handler)

    """ Networking starts from here"""
    # Connect to service.py
    thread1 = network.myThread(1, "Service Thread", 1)
    thread1.config(COMMAND, MYNAME, MYIP, MYPORT)
    config.THREADS.update({"service": thread1})
    thread1.start()

    # Runs it's own server
    thread2 = network.myThread(2, "Server Thread", 2)
    thread2.config(COMMAND, MYNAME, MYIP, MYPORT)
    config.THREADS.update({"server": thread2})
    thread2.start()

    # Wait for all threads to complete
    try:
        for t in config.THREADS.values():
            t.join() 
    except:
        print("THANOS...")
        os.kill(os.getpid(), signal.SIGKILL)

    print("Exiting Main Thread")
