import os, sys, socket, signal, config

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
        self.command, self.myIp, self.myName, self.myPort = [None] * 4       

    def run(self):
        # Grab System Input
        if len(sys.argv) == 4:
            self.command, self.myIp, self.myName = str(sys.argv[1]), str(sys.argv[2]), int(sys.argv[3])
        # For Easy Development
        elif len(sys.argv) == 3:
            self.command, self.myName = str(sys.argv[1]), int(sys.argv[2])
            hostname = socket.gethostname()    
            self.myIp = socket.gethostbyname(hostname)    
        else:
            print("Please enter CONNECT, target IP adress, and your node number")
            print("\n    python3 main.py CONNECT 192.168.1.1 2")
            print("\n    python3 main.py CONNECT 2")

        self.myPort = self.myName + 2000

        return self.command, self.myIp, str(self.myName), str(self.myPort)
    
    @staticmethod
    def signal_handler(self, signal, frame):
        print("System Exiting")
        print(os.getpid())
        os.kill(os.getpid(), signal.SIGKILL)
        sys.exit(0)
