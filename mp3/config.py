"""
    Global Variables
    
    Description:
        Globals variables declared here can be accessed from the entire program.
"""
def init():
    ''' Step1) Add name of your variable here for globalization '''
    global HOST, SERV_A_URI, SERV_B_URI, SERV_C_URI, SERV_D_URI , SERV_E_URI, COORDINATOR_URI
    
    ''' Step2) Declare your variable '''
    # Choose your setting
    SETTING = 'ONLINE' # currently supports online/sbseo2/ppng2 
    
    if SETTING == 'ONLINE':
        vm1, vm2, vm3, vm4, vm5, vm6 = '172.22.94.48', '172.22.156.49', '172.22.158.49', '172.22.94.49', '172.22.156.50', '172.22.158.50'
        COORDINATOR_URI = "PYRO:coordinator@" + vm1 + ":8080"
        SERV_A_URI = "PYRO:servA@" + vm2 + ":9090"
        SERV_B_URI = "PYRO:servB@" + vm3 + ":9091"
        SERV_C_URI = "PYRO:servC@" + vm4 + ":9092"
        SERV_D_URI = "PYRO:servD@" + vm5 + ":9093"
        SERV_E_URI = "PYRO:servE@" + vm6 + ":9094"

    elif SETTING == 'sbseo2':
        HOST = 'localhost'  
        COORDINATOR_URI = "PYRO:coordinator@" + HOST + ":8080"
        SERV_A_URI = "PYRO:servA@" + HOST + ":9090"
        SERV_B_URI = "PYRO:servB@" + HOST + ":9091"
        SERV_C_URI = "PYRO:servC@" + HOST + ":9092"
        SERV_D_URI = "PYRO:servD@" + HOST + ":9093"
        SERV_E_URI = "PYRO:servE@" + HOST + ":9094"

    elif SETTING == 'ppng2':
        HOST = '127.0.1.1'
        COORDINATOR_URI = "PYRO:coordinator@" + HOST + ":8080"
        SERV_A_URI = "PYRO:servA@" + HOST + ":9090"
        SERV_B_URI = "PYRO:servB@" + HOST + ":9091"
        SERV_C_URI = "PYRO:servC@" + HOST + ":9092"
        SERV_D_URI = "PYRO:servD@" + HOST + ":9093"
        SERV_E_URI = "PYRO:servE@" + HOST + ":9094"

init()