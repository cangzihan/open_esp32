# 两个开发板共享状态
# 为了使1套程序运用于2个开发板（实际使用时只有一个信号发送端）：两个开发板共享一个变量，每次当某开发板有按钮按下时，这个变量数字+1并使2个开发板同时更新
import time

import neopixel
import network
import espnow
from machine import Pin


# ============================================================
# 配置
# ============================================================

LED_PIN = 2
SWITCH_PIN = 15

# Neopixel
pin = Pin(16, Pin.OUT)
np = neopixel.NeoPixel(pin,1)
#brightness :0-255
brightness=10                                
colors=[[brightness,0,0],                    #red
        [0,brightness,0],                    #green
        [0,0,brightness],                    #blue
        [brightness,brightness,brightness],  #white
        [0,0,0]]     

# ============================================================
# 在这里填写“对方 ESP32”的 MAC 地址
#
# 板子 1：
# PEER_MAC = b'\x1c\x8fW\x0eCd'
#
# 板子 2：
# PEER_MAC = b'\xe0\x8c\xfe\xfe\xa2\xbc'
# ============================================================

PEER_MAC = b'\x1c\x8fW\x0eCd'


# ============================================================
# GPIO
# ============================================================

led = Pin(LED_PIN, Pin.OUT)
led1 = Pin(14, Pin.OUT)
led2 = Pin(12, Pin.OUT)
led3 = Pin(13, Pin.OUT)

# GPIO15：
# 接 GND -> 0
# 不接   -> 1
switch = Pin(SWITCH_PIN, Pin.IN, Pin.PULL_UP)


# ============================================================
# Wi-Fi / ESP-NOW
# ============================================================

sta = network.WLAN(network.STA_IF)
sta.active(True)

e = espnow.ESPNow()
e.active(True)

try:
    e.add_peer(PEER_MAC)
except Exception as err:
    print("add_peer:", err)


# ============================================================
# 状态
# ============================================================

# 本机 Y
state = 1

# 对方 Y
peer_state = 0

# 是否已经收到过对方的数据
connected = False

# 上一次发送时间
last_send = 0

# 定期发送状态
SEND_INTERVAL = 1000

# 超过这个时间没有收到对方消息，就认为断开
TIMEOUT = 5000

last_recv = 0


# ============================================================
# LED
# ============================================================

def update_led():

    if not connected:

        # 尚未连接：闪烁
        led.value((time.ticks_ms() // 250) % 2)

    else:
        # 已连接：
        # 核心板上LED = 0
        led.value(0)
        if state == 1:
            led1.value(0)
            led2.value(1)
            led3.value(1)
            
            # 板载彩色LED
            np[0]=colors[1]
            np.write()
        elif state == 2:
            led1.value(1)
            led2.value(0)
            led3.value(1)
            
            # 板载彩色LED
            np[0]=colors[3]
            np.write()
        elif state == 3:
            led1.value(1)
            led2.value(1)
            led3.value(0)

            # 板载彩色LED
            np[0]=colors[0]
            np.write()

# ============================================================
# 发送自己的状态
# ============================================================

def send_state(state=1):

    if state == 1:
        message = b'S1'
    elif state == 2:
        message = b'S2'
    elif state == 3:
        message = b'S3'

    try:
        e.send(PEER_MAC, message)

        print("SEND:", message)

    except Exception as err:
        print("SEND ERROR:", err)


# ============================================================
# 发送 ACK
# ============================================================

def send_ack(host):

    # ACK 中带上自己当前的 Y 状态

    if state == 1:
        message = b'A1'
    elif state == 2:
        message = b'A2'
    elif state == 3:
        message = b'A3'

    try:
        e.send(host, message)

        print("ACK:", message)

    except Exception as err:
        print("ACK ERROR:", err)


# ============================================================
# 主循环
# ============================================================

print("==============================")
print("ESP-NOW XOR Switch")
print("==============================")

print("My MAC:", sta.config('mac'))
print("Peer MAC:", PEER_MAC)

while True:

    now = time.ticks_ms()

    # ========================================================
    # 1. 检查自己的 Y 是否变化
    # ========================================================

    new_state = switch.value()

    if new_state == 0:
        time.sleep_ms(10)
        new_state = switch.value()
        # 消抖
        if new_state == 0:
            print("按钮按下")

            state += 1
            if state > 3:
                state = 1
            # 状态变化后立即发送
            send_state(state)
            
            # 松手
            while new_state == 0:
                new_state = switch.value()


    # ========================================================
    # 2. 接收 ESP-NOW
    # ========================================================

    result = e.recv(0)

    if result:

        host, message = result

        print("RECV:", host, message)

        last_recv = now

        # ----------------------------------------------------
        # 收到对方的状态
        # ----------------------------------------------------

        if message == b'S1' or message == b'S2' or message == b'S3':
            connected = True

            if message == b'S1':
                state = 1
            elif message == b'S2':
                state = 2
            elif message == b'S3':
                state = 3

            print("PEER Y:", state)

            # 根据 XOR 更新 LED
            update_led()

            # 回复 ACK
            send_ack(host)


        # ----------------------------------------------------
        # 收到对方 ACK
        #
        # ACK 中带的是对方自己的 Y
        # 所以也可以用来更新 peer_state
        # ----------------------------------------------------

        elif message in [b'A1', b'A2', b'A3']:
            connected = True

            if message == b'A1':
                peer_state = 1
            elif message == b'A2':
                peer_state = 2
            elif message == b'A3':
                peer_state = 3

            print("PEER Y:", peer_state)

            update_led()


    # ========================================================
    # 3. 定期发送自己的状态
    # ========================================================

    if time.ticks_diff(now, last_send) >= SEND_INTERVAL:

        send_state(state)

        last_send = now


    # ========================================================
    # 4. 判断连接是否断开
    # ========================================================

    if connected:

        if time.ticks_diff(now, last_recv) >= TIMEOUT:

            print("Connection lost")

            connected = False


    # ========================================================
    # 5. 更新 LED
    # ========================================================

    update_led()


    # ========================================================
    # 6. 稍微让出 CPU
    # ========================================================

    time.sleep_ms(20)
