import json
import wifiCfg
from m5stack import *
from m5ui import *
from uiflow import *
from machine import WDT
from secret import *
import ntptime
from m5mqtt import M5mqtt
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

wdt = WDT(timeout=20000)
setScreenColor(0x000000)
ntp = ntptime.client(host='de.pool.ntp.org', timezone=2)
# lcd.print((ntp.formatDatetime('dd-mm-yy', 'hh:mm')), 1, 1, 0x33cc00)
m5mqtt = M5mqtt('EnvHat', mqtt_host, mqtt_port, mqtt_user, mqtt_password, 300)
m5mqtt.subscribe(str('m5stack/setConfig'), fun_m5stack_setConfig_)
m5mqtt.start()
m5mqtt.publish(str('m5stack/status'), str('Up'), 0)
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
    m5mqtt.publish(str('m5stack/pressure'), str(press), 0)
    m5mqtt.publish(str('m5stack/config'), str(config), 0)
    # Home Assistant integration
    payload = {"temperature": str(("%.1f" % (temp))), "humidity": str(("%.1f" % (hum))), "pressure": str(("%.0f" % (press)))}
    m5mqtt.publish(str("homeassistant/sensor/m5stick/state"), json.dumps(payload))
    lcd.print(((str(' Baro: ') + str(("%.0f" % (press))))), 1, 10, 0xffffff)
    lcd.print(((str(' Temp: ') + str(("%.1f" % (temp))))), 1, 30, 0xffffff)
    lcd.print(((str(' Hum: ') + str(("%.1f" % (hum))))), 1, 50, 0xffffff)
    wait(10)
    wdt.feed()
