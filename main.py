import json
import wifiCfg
from m5stack import *
from m5ui import *
from uiflow import *
from machine import WDT, deepsleep
from secret import *
import ntptime
# from m5mqtt import M5mqtt
from umqtt.simple2 import MQTTClient as M5mqtt
import hat
import time

hat_env2_0 = hat.get(hat.ENV2)

config = None
temp = None
hum = None
press = None
eco_mode = "0"
delay = 10000
wdt = None

wifiCfg.autoConnect(lcdShow=True)


def set_eco(eco_mode):
    if not eco_mode:
        # wdt = WDT(timeout=delay+10000)
        axp.setLcdBrightness(100)
        lcd.setRotation(1)
        setScreenColor(0x111111)
        return wdt
    else:
        axp.setLcdBrightness(0)
        return None


def sub_cb(topic, msg, retain, dup):
    global delay
    global eco_mode
    global config
    print("Topic " + str(topic) + " - message: " + str(msg))
    if topic == b'm5stick/set':
        try:
            data = json.loads(msg.decode())
        except ValueError:
            print("Topic "+str(topic) + " - invalid message fmt: "+str(msg))
            return
        delay = int(data["delay"])
        eco_mode = True if data["eco"] == "1" else False
        set_eco(eco_mode)
    elif topic == b'm5stick/config':
        try:
            config = json.loads(msg.decode())
            with open('config.json', 'w') as f:
                f.write(json.dumps(config))
        except ValueError:
            print("Topic "+str(topic) + " - invalid message fmt: "+str(msg))
            return

try:
    # config = json.loads((ezdata.getData('7FNCfls4WIbuFChYq6b1XiYFEuNRTZ8Q', 'config')))
    with open('config.json', 'r') as f:
        config = json.loads(f.read())
        try:
            delay = config['delay']
            eco_mode = config['eco']
        except KeyError:
            delay = 10000
            eco_mode = "0"
            config['delay'] = delay
            config['eco'] = eco_mode
            with open('config.json', 'w') as f:
                f.write(json.dumps(config))

except OSError:
    config = {'tk': 1, 'to': (-4.5), 'hk': 1, 'ho': 0, 'pk': 1, 'po': 0, 'delay':delay, 'eco': eco_mode}
    # ezdata.setData('7FNCfls4WIbuFChYq6b1XiYFEuNRTZ8Q', 'config', (json.dumps(config)))
    with open('config.json', 'w') as f:
        f.write(json.dumps(config))

wdt = set_eco(eco_mode)
ntp = ntptime.client(host='de.pool.ntp.org', timezone=2)
# lcd.print((ntp.formatDatetime('dd-mm-yy', 'hh:mm')), 1, 1, 0x33cc00)
m5mqtt = M5mqtt('EnvHat', mqtt_host, mqtt_port, mqtt_user, mqtt_password, 300)
# m5mqtt.subscribe(str('m5stack/setConfig'), fun_m5stack_setConfig_)
# m5mqtt.start()
m5mqtt.set_callback(sub_cb)
m5mqtt.connect()
m5mqtt.subscribe(b"m5stick/set")
m5mqtt.subscribe(b"m5stick/config")
m5mqtt.publish(str('m5stack/status'), str('Up'), 0)

# Send the autodiscovery messages to home assistant
# to register the devices and its sensors as 'm5stick'
ha_topic = "homeassistant/sensor/m5stick"
payload = [
    {
        "device_class": "temperature",
        "name": "m5stick_temp",
        "state_topic": "homeassistant/sensor/m5stick/state",
        "unit_of_measurement": "°C",
        "value_template": "{{ value_json.temperature}}",
        "unique_id": "temp01ae",
        "device": {"identifiers": "m5stick01ae", "name": "m5stick", "manufacturer": "M5Stack", "model": "M5Stick"}
    },
    {
        "device_class": "humidity",
        "name": "m5stick_hum",
        "state_topic": "homeassistant/sensor/m5stick/state",
        "unit_of_measurement": "%",
        "value_template": "{{ value_json.humidity}}",
        "unique_id": "hum01ae",
        "device": {"identifiers": "m5stick01ae", "name": "m5stick", "manufacturer": "M5Stack", "model": "M5Stick"}
    },
    {
        "device_class": "pressure",
        "name": "m5stick_pres",
        "state_topic": "homeassistant/sensor/m5stick/state",
        "unit_of_measurement": "hPa",
        "value_template": "{{ value_json.pressure}}",
        "unique_id": "press01ae",
        "device": {"identifiers": "m5stick01ae", "name": "m5stick", "manufacturer": "M5Stack", "model": "M5Stick"}
    },
]
#
topic = str(ha_topic + 'T/config')
msg = str(json.dumps(payload[0]))
m5mqtt.publish(topic, msg, 0)

#
topic = str(ha_topic + 'P/config')
msg = str(json.dumps(payload[2]))
m5mqtt.publish(topic, msg, 0)

#
topic = str(ha_topic + 'H/config')
msg = str(json.dumps(payload[1]))
m5mqtt.publish(topic, msg, 0)


while True:
    m5mqtt.check_msg()
    temp = (config['tk']) * (hat_env2_0.temperature) + (config['to'])
    hum = (config['hk']) * (hat_env2_0.humidity) + (config['ho'])
    press = (config['pk']) * (hat_env2_0.pressure) + (config['po'])
    m5mqtt.publish(str('m5stack/temperature'), str(temp), 0)
    m5mqtt.publish(str('m5stack/humidity'), str(hum), 0)
    # m5mqtt.publish(str('m5stack/pressure'), str(press), 0)
    # m5mqtt.publish(str('m5stack/config'), str(config), 0)
    # Home Assistant integration
    payload = {"temperature": str(("%.1f" % (temp))), "humidity": str(("%.1f" % (hum))),
               "pressure": str(("%.0f" % (press)))}
    m5mqtt.publish(str("homeassistant/sensor/m5stick/state"), str(json.dumps(payload)))
    time.sleep(1)
    if eco_mode:
        deepsleep(delay)
    else:
        lcd.clear()
        lcd.print(((str(' Baro: ') + str(("%.0f" % (press))))), 1, 10, 0xffffff)
        lcd.print(((str(' Temp: ') + str(("%.1f" % (temp))))), 1, 30, 0xffffff)
        lcd.print(((str(' Hum: ') + str(("%.1f" % (hum))))), 1, 50, 0xffffff)
        time.sleep(delay/1000-1)
        wdt.feed()
