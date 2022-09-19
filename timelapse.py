import os
import glob
import subprocess
import threading
import time
from datetime import datetime

count = 0
save_directory_parent = '/home/pi/webplotter/timelapse/'
command = 'libcamera-jpeg -o /home/pi/webplotter/timelapse/{}.jpg -n -t 1 --shutter 8000 --exposure sport --awb tungsten'

isExist = os.path.exists(save_directory_parent)
if not isExist:
  os.makedirs(save_directory_parent)

save_directory_child = os.path.join(save_directory_parent,datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '/')

isExist = os.path.exists(save_directory_child)
if not isExist:
  os.makedirs(save_directory_child)

command = 'libcamera-jpeg -o ' + save_directory_child + '{}.jpg -n -t 1 --shutter 8000 --exposure sport --awb tungsten'

#files = glob.glob('/home/pi/webplotter/timelapse/*')
#for f in files:
#    os.remove(f)
while True:
    count+=1
    #subprocess.run(command.format("{:08d}".format(count)), shell=True) #run with blocking
    subprocess.Popen(command.format("{:08d}".format(count)), shell=True) #run in background
    time.sleep(4)
