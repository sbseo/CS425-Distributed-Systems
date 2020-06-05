import socketserver, time
import network
from message import Message
import config

""" 
    threadFunc

    Description:
        Collection of thread, envent, and hanlder functions!
        When fun_on_intro_thread is called, thread_handler runs!
    
        eg) func_on_intro_thread(msg) -> thread_handler Runs!

"""
'''For Server'''
class LoggerHandler(socketserver.BaseRequestHandler):

    def handle(self):
        file = self.request.makefile('r')
        # name = file.readline().strip()

        data = self.request.recv(1024).decode()
        msg = Message(data.split())

        # Add connected clients!
        config.NODES.update({msg.nodeNum: msg})
        print(config.NODES.keys())        

        # Send message to client !
        s = "Server can send message!"
        self.request.sendall(s.encode())

        print(time.time(), "-", f"node{msg.nodeNum} connected")    
        for line in file:
            # print connected node info    
            ts, rest = line.strip().split(maxsplit=1)
            print(ts, msg.nodeNum, rest)

        while True:
            data = self.request.recv(1024).decode()
            print("handle gossip: ", data)
            # When connection is lost, it stops receiving data
            # if data is "": break
        
        print("node" + str(msg.nodeNum) + " Disconnected")
        drop_node_handler(msg.nodeNum)
        

'''Drops nodes when disconnected'''
def drop_node_handler(object):
    config.NODES.pop(str(object))  # Removes from CONNECTION
    print(config.NODES.keys())
    

'''To add more threads in main thread'''
'''When received INTRODUCTION MESSAGE'''

def thread_handler(object, MYNAME, MYIP, MYPORT):
    # Connect to introduced clients
    with config.MAINLOCK:    
        thread3 = network.myThread(len(config.NODES)+1, "Client Thread", len(config.NODES)+1)
        config.THREADS.update({object.nodeNum: thread3})
        print("CURRENT THREADS:, ", config.THREADS.keys())
        
        thread3.config("INTRO_CONNECT", MYNAME, MYIP, MYPORT)
        thread3.targetConfig(object.nodeNum, object.ip, object.port)
        thread3.start()

# When fun_on_intro_thread is called, thread_handler runs! :) 
func_on_intro_thread = thread_handler
