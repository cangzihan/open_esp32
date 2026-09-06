# 两个开发板共享I/O状态
import time
import network
import espnow
from machine import Pin


# ============================================================
# 配置
# ============================================================

LED_PIN = 2
SWITCH_PIN = 15

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
my_state = switch.value()

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
        # LED = 本机状态 XOR 对方状态
        led.value(my_state ^ peer_state)


# ============================================================
# 发送自己的状态
# ============================================================

def send_state():

    if my_state:
        message = b'S1'
    else:
        message = b'S0'

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

    if my_state:
        message = b'A1'
    else:
        message = b'A0'

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

print("Initial Y:", my_state)


while True:

    now = time.ticks_ms()


    # ========================================================
    # 1. 检查自己的 Y 是否变化
    # ========================================================

    new_state = switch.value()

    if new_state != my_state:

        my_state = new_state

        print("LOCAL CHANGE:", my_state)

        # 状态变化后立即发送
        send_state()


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

        if message == b'S0' or message == b'S1':

            connected = True

            if message == b'S1':
                peer_state = 1
            else:
                peer_state = 0

            print("PEER Y:", peer_state)

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

        elif message == b'A0' or message == b'A1':

            connected = True

            if message == b'A1':
                peer_state = 1
            else:
                peer_state = 0

            print("PEER Y:", peer_state)

            update_led()


    # ========================================================
    # 3. 定期发送自己的状态
    # ========================================================

    if time.ticks_diff(now, last_send) >= SEND_INTERVAL:

        send_state()

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