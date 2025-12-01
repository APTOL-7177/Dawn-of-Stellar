"""DualSense 진동 테스트"""
from pydualsense import pydualsense
import time

ds = pydualsense()
ds.init()

print(f"DualSense 연결됨")
print("진동 테스트...")

# 진동 (0-255)
ds.setLeftMotor(128)
ds.setRightMotor(128)
time.sleep(0.3)

ds.setLeftMotor(0)
ds.setRightMotor(0)

print("완료")
ds.close()
