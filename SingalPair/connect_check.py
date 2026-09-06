# 采用ESP-NOW连接方式，确认两个esp32是否正常连接
import time
import network
import espnow
from machine import Pin


# ============================================================
# 配置
# ============================================================

LED_PIN = 2

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
# LED
# ============================================================

led = Pin(LED_PIN, Pin.OUT)


# ============================================================
# Wi-Fi
# ============================================================

sta = network.WLAN(network.STA_IF)
sta.active(True)


# ============================================================
# ESP-NOW
# ============================================================

e = espnow.ESPNow()
e.active(True)

try:
    e.add_peer(PEER_MAC)
except Exception as err:
    print("add_peer:", err)


# ============================================================
# 状态
# ============================================================

connected = False

last_hello = 0
last_ping = 0
last_recv = 0

HELLO_INTERVAL = 1000
PING_INTERVAL = 2000

# 超过 5 秒没有收到任何消息，认为连接断开
TIMEOUT = 5000


# ============================================================
# LED
# ============================================================

def update_led():

    if connected:
        # 通信正常：常亮
        led.value(1)

    else:
        # 没连接：闪烁
        led.value((time.ticks_ms() // 250) % 2)


# ============================================================
# 发送 HELLO
# ============================================================

def send_hello():

    try:
        e.send(PEER_MAC, b'HELLO')
        print("SEND HELLO")

    except Exception as err:
        print("SEND HELLO ERROR:", err)


# ============================================================
# 发送 PING
# ============================================================

def send_ping():

    try:
        e.send(PEER_MAC, b'PING')
        print("SEND PING")

    except Exception as err:
        print("SEND PING ERROR:", err)


# ============================================================
# 主循环
# ============================================================

print("==============================")
print("ESP-NOW connection test")
print("==============================")

print("My MAC:", sta.config('mac'))
print("Peer MAC:", PEER_MAC)


while True:

    now = time.ticks_ms()


    # ========================================================
    # 1. 接收消息
    # ========================================================

    result = e.recv(0)

    if result:

        host, message = result

        print("RECV:", host, message)

        last_recv = now

        # ----------------------------------------------------
        # 收到 HELLO
        # ----------------------------------------------------

        if message == b'HELLO':

            print("Peer found!")

            connected = True

            # 回一个 HELLO
            try:
                e.send(host, b'HELLO')
            except Exception as err:
                print("HELLO reply error:", err)


        # ----------------------------------------------------
        # 收到 PING
        # ----------------------------------------------------

        elif message == b'PING':

            connected = True

            try:
                e.send(host, b'PONG')
                print("SEND PONG")
            except Exception as err:
                print("SEND PONG ERROR:", err)


        # ----------------------------------------------------
        # 收到 PONG
        # ----------------------------------------------------

        elif message == b'PONG':

            connected = True

            print("Connection OK")


    # ========================================================
    # 2. 定期发送 HELLO
    # ========================================================

    if time.ticks_diff(now, last_hello) >= HELLO_INTERVAL:

        send_hello()

        last_hello = now


    # ========================================================
    # 3. 定期发送 PING
    # ========================================================

    if connected:

        if time.ticks_diff(now, last_ping) >= PING_INTERVAL:

            send_ping()

            last_ping = now


    # ========================================================
    # 4. 判断是否超时
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