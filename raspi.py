#!/

import struct
import serial
from collections import defaultdict


HEADER_SIZE = 3


class DummySerial(object):
    def add_listener(self, listener): pass
    def check_messages(self): pass
    def set_heater_status(self, heater_id, status): pass
    def set_lcd_message(self, line1, line2): 
        print line1
        print line2
    def beep(self): pass
    def set_led_status(self, led_idx, status): pass
    

class Serial(object):
    def __init__(self):
        self.listeners = []
        self.serial = serial.Serial('/dev/tty.usbmodem1411', 9600)
        self.serial.nonblocking()
        self.buffer = ""

    def add_listener(self, listener):
        self.listeners.append(listener)

    def check_messages(self):
        while self.serial.inWaiting() > 0:
            b = self.serial.read(self.serial.inWaiting())
            #print "read:", b
            self.buffer += b

        while len(self.buffer) >= HEADER_SIZE:
            (msg_size, msg_type) = struct.unpack_from('<HB', self.buffer, 0)
            #print "MsgSize: %d MsgType: %s" % (msg_size, chr(msg_type))
            if len(self.buffer) < HEADER_SIZE + msg_size:
                break

            if msg_type == ord('t'):
                temp = struct.unpack_from('<B', self.buffer, HEADER_SIZE)[0]
                for l in self.listeners:
                    l.on_temp_message(temp)
            elif msg_type == ord('h'):
                (heater_id, status) = struct.unpack_from('<BB', self.buffer, HEADER_SIZE)
                for l in self.listeners:
                    l.on_heater_status(heater_id, status)

            self.buffer = self.buffer[HEADER_SIZE + msg_size:]

    def set_heater_status(self, heater_id, status):
        msg = struct.pack('<HBBB', 2, ord('H'), heater_id, status and 1 or 0)
        self.send(msg)

    def set_lcd_message(self, line1, line2):
        msg = struct.pack('<HB', 32, ord('D'))
        if len(line1) < 16:
            line1 = "%16s" % line1
        if len(line2) < 16:
            line2 = "%16s" % line2
        msg += line1[:16] + line2[:16]
        #self.send(msg)

        print "LCD DISPLAY:"
        print line1
        print line2
        print ""

    def beep(self):
        msg = struct.pack('<HB', 0, ord('B'))
        #self.send(msg)

    def set_led_status(self, led_idx, status):
        msg = struct.pack('<HBBB', 2, ord('L'), led_idx, status and 1 or 0)
        self.send(msg)

    def debug_set_temp(self, temp):
        msg = struct.pack('<HBH', 2, ord('T'), temp)
        self.send(msg)

    def send(self, msg):
        self.serial.write(msg)


class ArduinoAPI(object):
    def __init__(self, s):
        self.s = s
        self.s.add_listener(self)
        self.temp = 0
        self.heaters = defaultdict(lambda: False)

    def get_temp(self):
        return self.temp

    def get_heater_status(self, heater_id):
        return self.heaters[heater_id]

    def set_heater_status(self, heater_id, status):
        self.s.set_heater_status(heater_id, status)
        self.heaters[heater_id] = status

    def set_lcd_message(self, line1, line2):
        self.s.set_lcd_message(line1, line2)

    def set_led_status(self, led_idx, status):
        self.s.set_led_status(led_idx, status)

    def beep(self):
        self.s.beep()

    def wait_for_button(self):
        raw_input("Press enter to continue ...")

    def on_temp_message(self, temp):
        self.temp = temp
        #print "New Temp:", temp

    def on_heater_status(self, id, status):
        self.heaters[id] = status

if __name__ == '__main__':
    import time
    import random

    random.seed()

    s = Serial()
    api = ArduinoAPI(s)

    i = 0
    while 1:
        if i % 5 == 0:
            #new_temp = random.randint(0, 100)
            #print "Setting new temp to:", new_temp
            #s.debug_set_temp(new_temp)
            #api.set_led_status(i % 2, i % 4)
            pass
        s.check_messages()
        time.sleep(1)
        i += 1

    #api.set_led_status(0, True)
