import serial

ser = serial.Serial(
                    port='/dev/ttyACM0',
                    baudrate=9600
                    )

i = 0
while(i < 1000000):
    input = int.from_bytes(ser.read(), byteorder="little")
    print(input)
    i = i+1