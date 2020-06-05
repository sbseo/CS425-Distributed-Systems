import threading
import time

class blockingRecvThread(threading.Thread):
    def __init__(self, inn):
        self._running_flag = False
        self.stop  = threading.Event()
        threading.Thread.__init__(self, target=self.test_method, args=(inn, ))
        self.i = None

    def test_method(self,inn):
        try:
            while(not self.stop.wait(1)):
                # self.i = inn
                print("asdf", inn)
                self._running_flag = True
                print ('Start wait')
                self.stop.wait(100)
                print ('Done waiting')
        finally:
                self._running_flag = False

    def terminate(self):
         self.stop.set()
         
thread = blockingRecvThread(1231)
thread.start()
print(thread.i)

time.sleep(2)
print('Time sleep 2')
thread.terminate()
print("Joining thread")
thread.join()
print("Done Joining thread")