import os, sys, socket, signal
import config as g
import network

''' 
        SYSTEM INPUT

            run() : User inputs commandline
            signal_handler: User inputs ctrl+c

            Description:
                To meet submission requirement, please use
                    python3 main.py CONNECT 192.168.1.1 2
                
                For easy development, please use (USE config.py FOR CUSTOMIZATION)
                    python3 main.py CONNECT 1
                    python3 main.py CONNECT 2
'''    
class SystemInput:
    
    def __init__(self):     
        self.command, self.myIp, self.myName, self.myPort, self.instanceID = [None] * 5

    def run(self):
        # Grab System Input
        # if len(sys.argv) == 4:
            # self.command, self.myIp, self.myName = str(sys.argv[1]), str(sys.argv[2]), int(sys.argv[3])
        
        # For Easy Development
        if len(sys.argv) == 4:
            # third argument represents the nth instance of our node on this VM
            self.command, self.myName, self.instanceID = str(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
            hostname = socket.gethostname()    
            self.myIp = socket.gethostbyname(hostname)    
        else:
            print("Please enter CONNECT, VM identifier, and instance id")
            print("\n    python3 main.py CONNECT 2 1")
            print("This is the second VM with the first instance of the node running")
            exit(-1)

        # local testing
        # self.myPort = (self.myName*10) + 2000
        
        # remote testing
        # 2000 = inst 1
        # 2001 = inst 1
        # 2002 = inst 2
        # 2003 = inst 2
        self.myPort = 2000 + 2 * (int(self.instanceID) - 1)

        return self.command, self.myIp, str(self.myName), str(self.myPort), str(self.instanceID)
    
    @staticmethod
    def signal_handler(self, signal, frame):
        self.kill_handler()

    @staticmethod
    def kill_handler():
        print("System Exiting")
        # Save log files
        SystemInput.tx_logger()
        SystemInput.bw_logger()  
        SystemInput.delay_logger()      
        
        # Program shutdown
        os.kill(os.getpid(), signal.SIGKILL)

    @staticmethod
    def tx_logger():
        with open("node" + str(g.MYNAME) + "-" + str(g.INSTANCEID) + ".txt", "w") as fd:
            print("tx_logger: sorting messages by timestamp")
            sorted_trans = []
            with network.receivedTranslock:
                for msg in network.receivedTrans:
                    sorted_trans.append(msg.split())
            sorted_trans = sorted(sorted_trans, key = lambda x : x[1])
            for entry in sorted_trans:
                fd.write(str(entry [3] + " " + entry[4] + " " + entry[5]))
                fd.write('\n')
        fd.close()
        print("Node " + str(g.MYNAME) + " dumping has finished.")

    @staticmethod
    def bw_logger():
        with open("bandwidth_node" + str(g.MYNAME) + "-" + str(g.INSTANCEID) + ".txt", "w") as fd:
            # print("bw_logger: records bandwidth usage every second")
            with g.BW_LOCK:
                for entry in g.BW:
                    fd.write(str(entry))
                    fd.write('\n')
            print("bw_logger: bandwidth recording is complete")
        fd.close()
    
    '''
        Description: 
            Records time when it arrived 
    '''
    @staticmethod
    def delay_logger():
        with open("delay_node" + str(g.MYNAME) + "-" + str(g.INSTANCEID) + ".txt", "w") as fd:
            # print("delay_logger: records bandwidth usage every second")
            for (id, time) in g.MSG_ARRIVED_TIME.items():
                fd.write(str(id) + " " + str(time))
                fd.write('\n')
            print("delay_logger: Propogation delay recording is complete")
        fd.close()
        