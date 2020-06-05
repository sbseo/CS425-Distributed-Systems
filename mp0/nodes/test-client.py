# Echo client program
import socket
import sys
import signal
import sys
def signal_handler(signal, frame):
        # close the socket here
        print("exiting")
        s.close()
        sys.exit(0)

HOST = '172.22.94.48'    # The remote host
PORT = 1234          # The same port as used by the server
signal.signal(signal.SIGINT, signal_handler)
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))

    while True:
        for line in sys.stdin:
            print(line, end='')
            s.sendall(str.encode(line))