
from raspi import ArduinoAPI, DummySerial, Serial

import json
import sys
import time
from pprint import pprint
from datetime import datetime, timedelta


class Brewer(object):
    STATE_STOPPED = 0
    STATE_LOADING = 1
    STATE_MASH_HEATING = 2
    STATE_ADD_GRAIN = 3
    STATE_MASHING = 4
    STATE_REMOVE_GRAIN = 5
    STATE_BRING_TO_BOIL = 6
    STATE_BOILING = 7
    STATE_START_COOLING = 8
    STATE_COOLING = 9
    STATE_DONE = 10

    transitions = {
        STATE_STOPPED: STATE_LOADING,
        STATE_LOADING: STATE_MASH_HEATING,
        STATE_MASH_HEATING: STATE_ADD_GRAIN,
        STATE_ADD_GRAIN: STATE_MASHING,
        STATE_MASHING: STATE_REMOVE_GRAIN,
        STATE_REMOVE_GRAIN: STATE_BRING_TO_BOIL,
        STATE_BRING_TO_BOIL: STATE_BOILING,
        STATE_BOILING: STATE_START_COOLING,
        STATE_START_COOLING: STATE_COOLING,
        STATE_COOLING: STATE_DONE
    }

    def __init__(self, recipe):
        self.recipe = recipe
        self.ser = Serial()
        self.api = ArduinoAPI(self.ser)
        self.state = Brewer.STATE_STOPPED
        self.desired_temp = 0
        self.end_time = None
        self.mash_index = -1
        self.boil_done_time = None

    def start(self):
        print "Starting recipe"
        water_volume = self.recipe['mash']['water_volume']
        msg1 = "Load %d l water" % water_volume
        msg2 = "Then press enter"
        self.api.set_lcd_message(msg1, msg2)
        self.state = Brewer.STATE_LOADING
        self.api.wait_for_button()

        mash_temp = self.recipe['mash']['temp']
        msg1 = "Heating to %dC" % mash_temp
        msg2 = ""
        self.api.set_lcd_message(msg1, msg2)
        self.desired_temp = mash_temp
        self.state = Brewer.STATE_MASH_HEATING
        self._ensure_heater_state(True, True)

        self._run()

    def _ensure_heater_state(self, st1, st2):
        if self.api.heaters[0] != st1:
            self.api.set_heater_status(0, st1)
            print "Turning heater %d %s" % (0, st1 and "ON" or "OFF")
        if self.api.heaters[1] != st2:
            self.api.set_heater_status(1, st2)
            print "Turning heater %d %s" % (1, st2 and "ON" or "OFF")

    def _check_heating(self):
        if self.api.temp < self.desired_temp:
            print "Desired temp: %d Actual temp: %d" % (self.desired_temp, self.api.temp)
            # ensure heaters are on
            self._ensure_heater_state(True, True)
            return False
        else:
            return True

    def _check_mash_state(self):
        now = datetime.utcnow()
        
        if self.end_time is not None and now < self.end_time:
            if self.api.temp < self.desired_temp:
                self._ensure_heater_state(True, True)
            elif self.api.temp > self.desired_temp:
                self._ensure_heater_state(False, False)
        else:
            if self.mash_index == len(self.recipe['mash']['rests']) - 1:
                return True
            else:
                self.mash_index += 1
                rest = self.recipe['mash']['rests'][self.mash_index]
                self.end_time = now + timedelta(seconds=rest['duration'])
                self.desired_temp = rest['temp']
                print "Starting mash rest - temp: %dC duration: %d minutes" % (rest['temp'], rest['duration'])

    def _check_boiling(self):
        now = datetime.utcnow()
        if self.boil_done_time is None:
            duration = self.recipe['boil_duration']
            self.boil_done_time = now + timedelta(seconds=duration)
            self.hop_index = 0
        if self.api.temp < 95:
            self._ensure_heater_state(True, True)
        else:
            self._ensure_heater_state(True, False)
        
        h = self.recipe["hops"][self.hop_index]
        t = timedelta(seconds=h["when"])
        ts = self.boil_done_time - t
        if now > ts:
            msg1 = "Add to boiler:"
            msg2 = h["what"]
            self.api.set_lcd_message(msg1, msg2)
            self.api.wait_for_button()
            self.hop_index += 1
            if self.hop_index >= len(self.recipe["hops"]):
                return True
        return False

    def _check_cooling(self):
        self._ensure_heater_state(False, False)
        desired_temp = self.recipe["final_temp"]
        if self.api.temp <= desired_temp:
            print "Reached %dC" % desired_temp
            return True
        else:
            print "Desired temp: %d Actual temp: %d" % (self.desired_temp, self.api.temp)
            return False

    def _next(self):
        self.state = Brewer.transitions[self.state]

    def _run(self):
        while self.state != Brewer.STATE_DONE:
            self.ser.check_messages()
            if self.state in (Brewer.STATE_MASH_HEATING,):
                if self._check_heating():
                    self._next()
            elif self.state in (Brewer.STATE_ADD_GRAIN, Brewer.STATE_REMOVE_GRAIN):
                msg1 = ""
                msg2 = ""
                if self.state == Brewer.STATE_ADD_GRAIN:
                    msg1 = "Add grain bag"
                if self.state == Brewer.STATE_REMOVE_GRAIN:
                    msg1 = "Remove grain bag"
                self.api.set_lcd_message(msg1, msg2)
                self.api.wait_for_button()
                self._next()
            elif self.state == Brewer.STATE_MASHING:
                if self._check_mash_state():
                    self._next()
            elif self.state == Brewer.STATE_BRING_TO_BOIL:
                self._ensure_heater_state(True, True)
                if self.api.temp >= 22:
                    self._next()
            elif self.state == Brewer.STATE_BOILING:
                if self._check_boiling():
                    self._next()
            elif self.state == Brewer.STATE_START_COOLING:
                msg1 = "Cooling to %dC" % self.recipe['final_temp']
                msg2 = ""
                self.api.set_lcd_message(msg1, msg2)
                self._next()
            elif self.state == Brewer.STATE_COOLING:
                if self._check_cooling():
                    self._next()

            time.sleep(1)

        self._ensure_heater_state(False, False)  # just in case
        print "Done brewing. Enjoy!"


if __name__ == '__main__':
    recipe_file = open('dummy_recipe.json')
    recipe = json.load(recipe_file)
    pprint(recipe)
    recipe_file.close()

    b = Brewer(recipe)
    b.start()
