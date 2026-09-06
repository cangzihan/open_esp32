# 查看两个esp32的Mac地址
import network

sta = network.WLAN(network.STA_IF)
sta.active(True)

mac = sta.config('mac')

print(':'.join('{:02X}'.format(x) for x in mac))