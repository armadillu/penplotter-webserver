import os
import glob
import subprocess
import threading
import time

count = 0
save_directory = '/home/pi/webplotter/timelapse/'
command = 'libcamera-jpeg -o /home/pi/webplotter/timelapse/{}.jpg -n -t 1 --shutter 8000 --exposure sport --awb tungsten'

isExist = os.path.exists(save_directory)
if not isExist:
  os.makedirs(save_directory)

files = glob.glob('/home/pi/webplotter/timelapse/*')
for f in files:
    os.remove(f)
while True:
    count+=1
    #subprocess.run(command.format("{:08d}".format(count)), shell=True) #run with blocking
    subprocess.Popen(command.format("{:08d}".format(count)), shell=True) #run in background
    time.sleep(4)
