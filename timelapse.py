import os
import glob
import subprocess
import threading
import time

count = 0
command = 'libcamera-jpeg -o /home/pi/webplotter/timelapse/{}.jpg -t 2000 --width 3840 --height 2160'

files = glob.glob('/home/pi/webplotter/timelapse/*')
for f in files:
    os.remove(f)

while True:
	count+=1
	subprocess.Popen(command.format("{:08d}".format(count)), shell=True)
	time.sleep(3)
