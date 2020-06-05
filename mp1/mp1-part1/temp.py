import ntplib
import math
import time
c = ntplib.NTPClient()
response = c.request('0.north-america.pool.ntp.org')
print(math.floor(response.tx_time * 1000))

time.time()
