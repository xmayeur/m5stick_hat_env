import json
import wifiCfg
from m5stack import *
from m5ui import *
from uiflow import *
from machine import WDT
from secret import *
import ntptime
# from m5mqtt import M5mqtt
from umqtt.simple2 import MQTTClient as M5mqtt
import hat

lcd.setRotation(1)
setScreenColor(0x111111)

hat_env2_0 = hat.get(hat.ENV2)

config = None
temp = None
hum = None
press = None

wifiCfg.autoConnect(lcdShow=True)




def fun_m5stack_setConfig_(topic_data):
    global config, temp, hum, press
    config = json.loads(topic_data)
    with open('config.json', 'w') as f:
        f.write(topic_data)
    # ezdata.setData('7FNCfls4WIbuFChYq6b1XiYFEuNRTZ8Q', 'config', topic_data)


# wdt = WDT(timeout=20000)
setScreenColor(0x000000)
ntp = ntptime.client(host='de.pool.ntp.org', timezone=2)
# lcd.print((ntp.formatDatetime('dd-mm-yy', 'hh:mm')), 1, 1, 0x33cc00)
m5mqtt = M5mqtt('EnvHat', mqtt_host, mqtt_port, mqtt_user, mqtt_password, 300)
# m5mqtt.subscribe(str('m5stack/setConfig'), fun_m5stack_setConfig_)
# m5mqtt.start()
m5mqtt.connect()
m5mqtt.publish(str('m5stack/status'), str('Up'), 0)
wait(2)

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
m5mqtt.publish(topic, msg, 2)

#
topic = str(ha_topic + 'P/config')
msg = str(json.dumps(payload[2]))
m5mqtt.publish(topic, msg, 2)

#
topic = str(ha_topic + 'H/config')
msg = str(json.dumps(payload[1]))
m5mqtt.publish(topic, msg, 2)


try:
    # config = json.loads((ezdata.getData('7FNCfls4WIbuFChYq6b1XiYFEuNRTZ8Q', 'config')))
    with open('config.json', 'r') as f:
        config = json.loads(f.read())
except:
    config = {'tk': 1, 'to': (-4.5), 'hk': 1, 'ho': 0, 'pk': 1, 'po': 0}
    # ezdata.setData('7FNCfls4WIbuFChYq6b1XiYFEuNRTZ8Q', 'config', (json.dumps(config)))
    with open('config.json', 'w') as f:
        f.write(json.dumps(config))
while True:
    lcd.clear()
    temp = (config['tk']) * (hat_env2_0.temperature) + (config['to'])
    hum = (config['hk']) * (hat_env2_0.humidity) + (config['ho'])
    press = (config['pk']) * (hat_env2_0.pressure) + (config['po'])
    m5mqtt.publish(str('m5stack/temperature'), str(temp), 0)
    m5mqtt.publish(str('m5stack/humidity'), str(hum), 0)
    # m5mqtt.publish(str('m5stack/pressure'), str(press), 0)
    # m5mqtt.publish(str('m5stack/config'), str(config), 0)
    # Home Assistant integration
    payload = {"temperature": str(("%.1f" % (temp))), "humidity": str(("%.1f" % (hum))), "pressure": str(("%.0f" % (press)))}
    m5mqtt.publish(str("homeassistant/sensor/m5stick/state"), str(json.dumps(payload)))
    lcd.print(((str(' Baro: ') + str(("%.0f" % (press))))), 1, 10, 0xffffff)
    lcd.print(((str(' Temp: ') + str(("%.1f" % (temp))))), 1, 30, 0xffffff)
    lcd.print(((str(' Hum: ') + str(("%.1f" % (hum))))), 1, 50, 0xffffff)
    wait(10)
    # wdt.feed()
