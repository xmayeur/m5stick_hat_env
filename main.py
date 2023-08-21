import json
import wifiCfg
from m5stack import *
from m5ui import *
from uiflow import *
from machine import WDT, deepsleep
from secret import *
import ntptime
from umqtt.simple2 import MQTTClient as MQTT
import hat
import time

# Global Variable Section
hat_env2_0 = hat.get(hat.ENV2)
config = None
temp = None
hum = None
press = None
eco_mode = False
delay = 10000
wdt = None

# Auto-connect to WIFI
wifiCfg.autoConnect(lcdShow=True)


def set_eco(eco_mode):
    print("eco mode: " + str(eco_mode))
    if not eco_mode:
        wdt = WDT(timeout=delay + 10000)
        axp.setLcdBrightness(100)
        lcd.setRotation(1)
        setScreenColor(0x111111)
        return wdt
    else:
        axp.setLcdBrightness(0)
        return None


def process_m5stick_set(topic, msg):
    global delay, eco_mode, config, wdt
    try:
        data = json.loads(msg.decode())
    except ValueError:
        print("Topic {topic} - invalid message fmt: " + str(msg))
        return
    delay = int(data["delay"])
    eco_mode = data["eco"] == "1"
    config['delay'] = delay
    config['eco'] = "1" if eco_mode else "0"
    print('upd config')
    with open('config.json', 'w') as f:
        f.write(json.dumps(config))
    wdt = set_eco(eco_mode)


def process_m5stick_config(topic, msg):
    global config
    try:
        data = json.loads(msg.decode())
        # should not throw an exception if the keys are the same
        for k in config:
            _ = data[k]
        with open('config.json', 'w') as f:
            f.write(json.dumps(config))
    except ValueError:
        print("Topic " + str(topic) + ":  Not a json format: " + str(msg))
        return
    except KeyError:
        print("Topic " + str(topic) + ": invalid message fmt: " + str(msg))
        return


def mqtt_callback(topic, msg, retain, dup):
    print("Topic {topic} - message: " + str(msg))
    if topic == b'm5stick/set':
        process_m5stick_set(topic, msg)
    elif topic == b'm5stick/config':
        process_m5stick_config(topic, msg)


def obtain_config():
    global delay, eco_mode, config

    try:
        with open('config.json', 'r') as f:
            config = json.loads(f.read())

        try:
            delay = config['delay']
            eco_mode = config['eco'] == "1"
        except Exception:
            print('updated config file')
            delay = 10000
            eco_mode = "0"
            config['delay'] = delay
            config['eco'] = eco_mode
            with open('config.json', 'w') as f:
                f.write(json.dumps(config))

    except OSError:
        config = {"tk": 1, "to": (-4.5), "hk": 1, "ho": 0, "pk": 1, "po": 10, "delay": delay,
                  "eco": "1" if eco_mode else "0"}
        with open('config.json', 'w') as f:
            f.write(json.dumps(config))


def ha_autodiscover(client):
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
    client.publish(topic, msg, 0)

    #
    topic = str(ha_topic + 'P/config')
    msg = str(json.dumps(payload[2]))
    client.publish(topic, msg, 0)

    #
    topic = str(ha_topic + 'H/config')
    msg = str(json.dumps(payload[1]))
    client.publish(topic, msg, 0)


def main():
    global wdt
    global hat_env2_0
    print('initializing')
    obtain_config()
    wdt = set_eco(eco_mode)
    ntp = ntptime.client(host='de.pool.ntp.org', timezone=2)
    client = MQTT('EnvHat', mqtt_host, mqtt_port, mqtt_user, mqtt_password, 300)
    client.set_callback(mqtt_callback)
    client.connect()
    client.subscribe(b"m5stick/set")
    client.subscribe(b"m5stick/config")
    ha_autodiscover(client)

    n = 0

    print('starting loop')
    while True:
        client.check_msg()
        temp = (config['tk']) * (hat_env2_0.temperature) + (config['to'])
        hum = (config['hk']) * (hat_env2_0.humidity) + (config['ho'])
        press = (config['pk']) * (hat_env2_0.pressure) + (config['po'])
        client.publish(str('m5stick/temperature'), str(temp), 0)
        client.publish(str('m5stick/humidity'), str(hum), 0)
        client.publish(str('m5stick/pressure'), str(press), 0)

        # Home Assistant integration
        payload = {"temperature": str(("%.1f" % (temp))), "humidity": str(("%.1f" % (hum))),
                   "pressure": str(("%.0f" % (press)))}
        client.publish(str("homeassistant/sensor/m5stick/state"), str(json.dumps(payload)))
        if eco_mode and n > 0:
            deepsleep(delay)

        n += 1
        lcd.clear()
        lcd.print(((str(' Baro: ') + str(("%.0f" % (press))))), 1, 10, 0xffffff)
        lcd.print(((str(' Temp: ') + str(("%.1f" % (temp))))), 1, 30, 0xffffff)
        lcd.print(((str(' Hum: ') + str(("%.1f" % (hum))))), 1, 50, 0xffffff)
        time.sleep(delay / 1000)
        if wdt is not None:
            wdt.feed()


if __name__ == "__main__":
    main()
