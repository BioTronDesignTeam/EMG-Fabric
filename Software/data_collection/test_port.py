import serial

# Replace with your actual port and baud rate
PORT = "/dev/cu.SLAB_USBtoUART"  # e.g. "COM3" on Windows, "/dev/ttyUSB0" or "/dev/ttyACM0" on Linux/Mac
BAUD = 9600

# Open serial connection
ser = serial.Serial(PORT, BAUD, timeout=1)

try:
    while True:
        line = ser.readline().decode('utf-8').strip()
        if line:
            print(line)

            
except KeyboardInterrupt:
    print("\nExiting...")
finally:
    ser.close()
