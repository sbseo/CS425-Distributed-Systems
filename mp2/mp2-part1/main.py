import config as g
import signal
import network
import os
from sysin import SystemInput

if __name__ == '__main__':
    """ Load Global Variables """
    g.init()

    """ User input starts from here """
    # Saves command line information
    newSys = SystemInput()
    g.BASEPORT = 2000
    g.COMMAND, g.MYIP, g.MYNAME, g.MYPORT, g.INSTANCEID = newSys.run()
    print("main:", g.COMMAND, g.MYIP, g.MYNAME, g.MYPORT)

    # Setup ctrl+c handler: signal killer
    signal.signal(signal.SIGINT, SystemInput.signal_handler)

    """ Networking starts from here"""
    # Connect to service.py
    thread1 = network.myThread(1, "service")
    thread1.config(g.COMMAND, g.MYIP, g.MYNAME, g.MYPORT)
    g.THREADS.update({"service": thread1})
    thread1.start()

    # Runs it's own server
    # this thread will handle requests from other nodes create
    # a connection to them to receive their gossip 
    # in addition we also create an INTRODUCE message for
    # gossipsenderhandler so that it is able to create a send thread
    thread2 = network.myThread(2, "gossiprecvhandler")
    thread2.config(g.COMMAND, g.MYIP, g.MYNAME, g.MYPORT)
    g.THREADS.update({"gossiprecvhandler": thread2})
    thread2.start()

    # this is the thread which will handle respones to INTRODUCE messages
    # created by both gossiprecvhandler and received from service
    thread3 = network.myThread(3, "gossipsendhandler")
    thread3.config(g.COMMAND, g.MYIP, g.MYNAME, g.MYPORT)
    g.THREADS.update({"gossipsendhandler": thread3})
    thread3.start()

    # this is the thread which records bandwidth every second
    thread4 = network.myThread(4, "bwhandler")
    g.THREADS.update({"bwhandler": thread4})
    thread4.start()

    # Wait for all threads to complete
    try:
        for t in g.THREADS.values():
            t.join() 
    except:
        SystemInput.kill_handler()        

    print("Exiting Main Thread")