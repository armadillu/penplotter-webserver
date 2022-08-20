#!/usr/bin/python

# Based on vogelchr/hp7475a-send (https://github.com/vogelchr/hp7475a-send)

import sys
import time
import os
import serial
import serial.tools.list_ports
from serial import SerialException
from flask_socketio import SocketIO, emit
import configparser
import notification
import globals

ERRORS = {
    # our own code
    -1: 'Timeout',
    -2: 'Parse error of decimal return from plotter',
    # from the manual
    0: 'no error',
    10: 'overlapping output instructions',
    11: 'invalid byte after <ESC>.',
    12: 'invalid byte while parsing device control instruction',
    13: 'parameter out of range',
    14: 'too many parameters received',
    15: 'framing error, parity error or overrun',
    16: 'input buffer has overflowed'
}

class HPGLError(Exception):
    def __init__(self, n, cause=None):
        self.errcode = n
        if cause:
            self.causes = [cause]
        else:
            self.causes = []

    def add_cause(self, cause):
        self.causes.append(cause)

    def __repr__(self):
        if type(self.errcode) is str:
            errstr = self.errcode
        else:
            errstr = f'Error {self.errcode}: {ERRORS.get(self.errcode)}'

        if self.causes:
            cstr = ', '.join(self.causes)
            return f'HPGLError: {errstr}, caused by {cstr}'
        return f'HPGLError: {errstr}'

    def __str__(self):
        return repr(self)


# read decimal number, followed by carriage return from plotter
def read_answer(tty):
    buf = bytearray()
    while True:
        c = tty.read(1)
        if not c:  # timeout
            raise HPGLError(-1)  # timeout
        if c == b'\r':
            break
        buf += c
    try:
        return int(buf)
    except ValueError as e:
        print(repr(e))
        raise HPGLError(-2)


def chk_error(tty):
    tty.write(b'\033.E')
    ret = None
    try:
        ret = read_answer(tty)
    except HPGLError as e:
        e.add_cause('ESC.E (Output extended error code).')
        raise e
    if ret:
        raise HPGLError(ret)


def getReplySTR(tty,cmd):
    tty.write(cmd)    
    reply = str(tty.read_until(b'\r').decode("utf-8"))
    if len(reply) > 1:
        return reply
    else:
        raise HPGLError(-1)  # timeout
        return   


def plotter_cmd(tty, cmd, get_answer=True):
    tty.write(cmd)
    try:
        if get_answer:
            answ = read_answer(tty)
        # chk_error(tty)
        if get_answer:
            return answ
    except HPGLError as e:
        e.add_cause(f'after sending {repr(cmd)[1:]}')
        raise e

def listComPorts():
    ports = dict(name='ports', content=[])
    for i in serial.tools.list_ports.comports():
        ports['content'].append(str(i).split(" ")[0])
    return ports


def getBaudRate(t_port):

    baud_dict = [9600, 19200, 38400, 4800, 2400, 1200]
    message = 'IN;OI;OE'
    success = False
    ser = serial.Serial(port=t_port, timeout=0.3)
    
    for baud_rate in baud_dict:
        ser.baudrate = baud_rate
        ser.write(message.encode())
        read_val = ser.read(size=64)
        if  len(read_val) > 0:
            if read_val.decode() != message:
                return baud_rate 
                break
    ser.close() 
    

def sendToPlotter(socketio, hpglfile, port , baud , flowControl):
    
    config = configparser.ConfigParser()
    config.read('config.ini')
    PLOTTER_NAME = 'Plotter'
    if (config.has_option('plotter', 'name')):
        PLOTTER_NAME = config['plotter']['name']
    
    globals.printing = True
    input_bytes = None

    try:
        ss = os.stat(hpglfile)
        if ss.st_size != 0:
            input_bytes = ss.st_size
    except Exception as e:
        print('Error stat\'ing file', hpglfile, str(e))
        socketio.emit('error', {'error': 'Error stat\'ing file'})

    hpgl = open(hpglfile, 'rb')

    if (flowControl == 'XON/XOFF'):
        
        try:
            tty = serial.Serial(port = port, baudrate = baud, parity = serial.PARITY_NONE, stopbits = serial.STOPBITS_ONE, bytesize = serial.EIGHTBITS, xonxoff = True, timeout = 2.0)
            tty.write(b'IN;\033.I80;;17:\033.N10;19:\033.@;0:')
            # tty.write(b'\033.E')
        except SerialException as e:
            socketio.emit('error', {'error': repr(e)})
            print(repr(e))
            return False

    if (flowControl == 'HP-IB'):
        try:
            tty = serial.Serial(port = port, baudrate = 9600, parity = serial.PARITY_NONE, stopbits = serial.STOPBITS_ONE, bytesize = serial.EIGHTBITS, timeout = 2.0)
        except SerialException as e:
            socketio.emit('error', {'error': repr(e)})
            print(repr(e))
            return False               

    else:
        try:
            tty = serial.Serial(port = port, baudrate = baud, parity = serial.PARITY_NONE, stopbits = serial.STOPBITS_ONE, bytesize = serial.EIGHTBITS, timeout = 2.0)
            tty.write(b'IN;\033.R')
        except SerialException as e:
            socketio.emit('error', {'error': repr(e)})
            print(repr(e))
            return False

    try:
        plotter_id = getReplySTR(tty, b'IN;OI;')
        socketio.emit('status_log', {'data': 'Plotter identifies as ' + plotter_id})    

    except HPGLError as e:
        print('No plotter detected!')
        socketio.emit('error', {'data': 'No plotter detected!'})
        return
    
    print('Configured for ', flowControl, ' flow control.')
    socketio.emit('status_log', {'data': 'Configured for ' + str(flowControl) + ' flow control.'})
    total_bytes_written = 0

    if flowControl not in ['HP-IB','XON/XOFF']:
        try:
            bufsz = plotter_cmd(tty, b'\033.L', True)
            socketio.emit('buffer_size', {'data': str(bufsz) })

        except HPGLError as e:
            print('*** Error initializing the plotter!')
            print(e)

            socketio.emit('error', {'data': '*** Error initializing the plotter!'})
            socketio.emit('error', {'data': str(e)})
            notification.telegram_sendNotification(PLOTTER_NAME + ': Error initializing the plotter')
            return

        print('Size of plotter buffer is ', bufsz, ' bytes.')
        socketio.emit('status_log', {'data': 'Size of plotter buffer is ' + str(bufsz) + ' bytes.'})
        socketio.emit('buffer_size', {'data': str(bufsz) })
        notification.telegram_sendNotification(PLOTTER_NAME + ': Starting Plot')

    prev_percent = 0

    while globals.printing == True:
  
        if (flowControl == 'HP-IB'):
            data = hpgl.read(1)
        else :
            if (bufsz < 80):
                data = hpgl.read(10)   
            else :
                data = hpgl.read(30)
        bufsz_read = len(data)
        #  there is a bug in pyserial - we need to handle CTS ourselves 
        #  https://github.com/pyserial/pyserial/issues/89#issuecomment-811932067

        if flowControl in ["CTS/RTS", "HP-IB"]:
            while not tty.getCTS():
                pass

        if flowControl not in ['HP-IB','XON/XOFF']:
            try:
                bufsp = plotter_cmd(tty, b'\033.B', True)

            except HPGLError as e:
                print('*** Error initializing the plotter!')
                print(e)

                socketio.emit('error', {'data': '*** Error on buffer spcace querry!'})
                socketio.emit('error', {'data': str(e)})
                notification.telegram_sendNotification(PLOTTER_NAME + ': Error on buffer spcace querry')
                return

            # print('Buffer has ', bufsp, ' bytes of free space.')
            socketio.emit('buffer_space', {'data': str(bufsp) })

        
        if (flowControl == 'Software'):
            if bufsp < bufsz/2: # the smallest buffer on the 7440a is 60 bytes                    
                time.sleep(0.1)                    

        tty.write(data)
        total_bytes_written += bufsz_read        

        if bufsz_read == 0:

            if flowControl not in ['HP-IB','XON/XOFF']:
                while bufsp != bufsz:
                    bufsp = plotter_cmd(tty, b'\033.B', True)  
                    time.sleep(0.5)
                    socketio.emit('buffer_space', {'data': str(bufsp)})
                    
            print('*** End of Print, exiting.')    
            notification.telegram_sendNotification(PLOTTER_NAME + ': Plot Finished')    
            socketio.emit('bytes_written', {'data': f'**EOP** - {total_bytes_written} bytes sent. Exiting.'})
            socketio.emit('end_of_print', {'data': 'True' })
            break

        if input_bytes != None:

            percent = int(100.0 * total_bytes_written/input_bytes)

            if (percent != prev_percent):
                if (percent == 25):
                    notification.telegram_sendNotification(PLOTTER_NAME + ': Plot @ 25%')
                if (percent == 50):
                    notification.telegram_sendNotification(PLOTTER_NAME + ': Plot @ 50%')
                if (percent == 75):
                    notification.telegram_sendNotification(PLOTTER_NAME + ': Plot @ 75%')
                # print(f'{percent:.0f}%, {total_bytes_written} bytes written.')
                socketio.emit('bytes_written', {'data': f'{percent:.0f}%, {total_bytes_written} bytes written.'})
                # socketio.emit('bytes_written', {'data': f'{percent:.0f}%, {total_bytes_written} bytes written.'})
                socketio.emit('print_progress', {'data': percent})
                prev_percent = percent

        else:
            # print(f'{percent:.0f}%, {bufsz_read} bytes added.')
            socketio.emit('status_log', {'data': f'{percent:.0f}%, {bufsz_read} bytes added.'})

    return
