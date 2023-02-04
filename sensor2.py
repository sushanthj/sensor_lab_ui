import sys
from PyQt5.uic.uiparser import QtCore
from copy import deepcopy
from scripts import Images
import numpy as np
from PyQt5 import uic
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import serial
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import time


DEVICE_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600
PROJECT_TITLE = 'Sensors and Motors Lab - Team H'
INPUT_BYTE_SIZE = 5 # seconds

POTENTIOMETER_MAP = (5/255)
IR_MAP = (80/255)
ULTRASONIC_MAP = (5/255)
SLOT_MAP = (1/255)

STEPPER_MAP = (255/360)
MOTOR_POSITION_MAP = (255/360)
MOTOR_RPM_MAP = (255/70)

class main(QMainWindow):
    def __init__(self):
        super(main, self).__init__()

		# Load the ui file
        uic.loadUi("sensor2.ui", self)

        self.setWindowTitle(PROJECT_TITLE)

		# Define our widgets
        self.button_clear_selections = self.findChild(QPushButton, "pushButton_clear_graphs")

        self.radioButton_1 = self.findChild(QRadioButton, "radioButton_1")
        self.radioButton_2 = self.findChild(QRadioButton, "radioButton_2")

        self.radioButton_potentiometer = self.findChild(QRadioButton, "radioButton_pot")
        self.radioButton_infrared = self.findChild(QRadioButton, "radioButton_infrared")
        self.radioButton_ultrasonic = self.findChild(QRadioButton, "radioButton_ultrasonic")
        self.radioButton_slot = self.findChild(QRadioButton, "radioButton_slot")

        self.motor_slider_rpm = self.findChild(QSlider, "slider_motor_rpm")
        self.motor_slider_position = self.findChild(QSlider, "slider_motor_position")
        self.servo_slider = self.findChild(QSlider, "slider_servo")
        self.stepper_position = self.findChild(QLineEdit, "lineEdit_stepper_position")

        self.motor_direction = self.findChild(QPushButton, "pushButton_motor_direction")
        self.motor_position_delta = self.findChild(QLineEdit, "lineEdit_motor_position")
        self.all_stop = self.findChild(QPushButton, "pushButton_all_stop")

		# trial stuff
        self.potentiometer_values = [0,100]
        self.potentiometer_label = self.findChild(QLabel, "label_potentiometer")
        self.trial_label = self.findChild(QLabel, "label_trial")

        self.scene = QGraphicsScene()

        # set button connections
        self.button_clear_selections.clicked.connect(self.clear_selections)

        self.radioButton_1.toggled.connect(lambda:self.modestate(self.radioButton_1))
        self.radioButton_2.toggled.connect(lambda:self.modestate(self.radioButton_2))

        self.radioButton_potentiometer.toggled.connect(lambda:self.sensorstate(self.radioButton_potentiometer))
        self.radioButton_infrared.toggled.connect(lambda:self.sensorstate(self.radioButton_infrared))
        self.radioButton_ultrasonic.toggled.connect(lambda:self.sensorstate(self.radioButton_ultrasonic))
        self.radioButton_slot.toggled.connect(lambda:self.sensorstate(self.radioButton_slot))

        self.motor_slider_rpm.sliderReleased.connect(lambda:self.motor_write_rpm())
        self.servo_slider.sliderReleased.connect(lambda:self.servo_write())
        self.stepper_position.returnPressed.connect(lambda:self.stepper_write_position())

        self.motor_direction.clicked.connect(lambda:self.change_direction(actuator=3))
        self.motor_position_delta.returnPressed.connect(lambda:self.motor_write_position())

        self.all_stop.clicked.connect(lambda:self.write_output())

        # Activate toolbars
        self.pbar = self.findChild(QProgressBar, "progressBar")
        self.statusBar_1 = self.findChild(QStatusBar, "statusbar")
        main.setStatusBar(self, self.statusBar_1)
        self.statusBar_1.setFont(QFont('Helvetica',13))

        # set defualt mode to Read sensor data (optional)
        # initilaize the Aruduino's Serial Port
        try:
            self.init_serial()
        except serial.SerialException:
            print("NO ARDUINO DETECTED")
            print("Please connect the Arduino and ensure the Port and Baud Rates are correct")
            exit()

        self.active_function = None
        self.mode = None

        self.init_data_holders()
        # set the default mode to read
        self.read_write_lock = "read"
        pg.setConfigOptions(antialias=True)

        # the de-facto main loop of the program which keeps calling the activated function
        self.timer = QTimer()
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.activate_function)
        self.timer.start()

		# Show The App
        self.show()

    def init_serial(self):
        self.ser = serial.Serial(
                                port=DEVICE_PORT,
                                baudrate=BAUD_RATE
                                )


    def clear_selections(self):
        self.graphWidget.clear()
        self.plot_object = None
        self.init_data_holders()
        self.read_write_lock = None


    def init_data_holders(self):
        # self.read_write_lock = "read"
        self.direction = [0,1]
        self.plot_cache_length = 100
        self.xdata = [0]
        self.ydata = [0]
        self.xdata_motor = [0]
        self.ydata_motor = [0]
        self.xdata_servo = [0]
        self.ydata_servo = [0]
        self.xdata_stepper = [0]
        self.ydata_stepper = [0]
        self.plot_object = None
        self.plot_object_motor = None
        self.plot_object_servo = None
        self.plot_object_stepper = None
        self.update_plot(y_axis_label="voltage", x_axis_label="samples",
                         x_range=100, y_range=7 ,new_y=0)
        self.update_plot_actuators(new_y_motor=0, new_y_servo=0, new_y_stepper=0)


    #TODO: Remove this function after testing
    def update_plot(self,y_axis_label, x_axis_label, x_range, y_range, new_y):
        color = self.palette().color(QPalette.Window)  # Get the default window background,
        pen = pg.mkPen(color=(255, 0, 0), width=3)

        if self.plot_object is None:
            print("Creating plot object")
            self.graphWidget.setBackground(color)
            self.graphWidget.setLabel('left', y_axis_label)
            self.graphWidget.setLabel('bottom', x_axis_label)
            self.graphWidget.showGrid(x=True, y=True)
            self.plot_object = self.graphWidget.plot(self.xdata, self.ydata, pen=pen)
        else:
            if len(self.xdata) > self.plot_cache_length and len(self.ydata) > self.plot_cache_length:
                # clear graph after reaching max_length
                self.xdata = self.xdata[1:]
                self.ydata = self.ydata[1:]

            self.graphWidget.setYRange(0, y_range, padding=0)
            self.xdata.append(self.xdata[-1] + 1)  # Add a new value 1 higher than the last.
            self.ydata.append(new_y)  # Add a new vales to end of ydata list
            self.plot_object.setData(self.xdata, self.ydata)


    def update_plot_actuators(self, new_y_motor, new_y_servo, new_y_stepper):
        color = self.palette().color(QPalette.Window)  # Get the default window background,
        pen = pg.mkPen(color=(255, 0, 0), width=3)

        #TODO: Change xdata and ydata
        if self.plot_object_motor is None and self.plot_object_servo is None and self.plot_object_stepper is None:
            print("Creating plot object for motor")
            self.graphWidget_motor.setBackground(color)
            self.graphWidget_motor.setLabel('left', 'RPM')
            self.graphWidget_motor.setLabel('bottom', 'samples')
            self.graphWidget_motor.setYRange(0, 100, padding=0)
            self.graphWidget_motor.showGrid(x=True, y=True)
            self.plot_object_motor = self.graphWidget_motor.plot(self.xdata_motor, self.ydata_motor, pen=pen)

            print("Creating plot object for servo")
            self.graphWidget_servo.setBackground(color)
            self.graphWidget_servo.setLabel('left', 'Angle (Degrees)')
            self.graphWidget_servo.setLabel('bottom', 'samples')
            self.graphWidget_servo.setYRange(0, 100, padding=0)
            self.graphWidget_servo.showGrid(x=True, y=True)
            self.plot_object_servo = self.graphWidget_servo.plot(self.xdata_servo, self.ydata_servo, pen=pen)

            print("Creating plot object for stepper")
            self.graphWidget_stepper.setBackground(color)
            self.graphWidget_stepper.setLabel('left', 'Angle (Degrees)')
            self.graphWidget_stepper.setLabel('bottom', 'samples')
            self.graphWidget_stepper.setYRange(0, 100, padding=0)
            self.graphWidget_stepper.showGrid(x=True, y=True)
            self.plot_object_stepper = self.graphWidget_stepper.plot(self.xdata_stepper, self.ydata_stepper, pen=pen)

        else:
            if len(self.xdata_motor) > self.plot_cache_length:
                # clear graph after reaching max_length
                self.xdata_motor = self.xdata_motor[1:]
                self.ydata_motor = self.ydata_motor[1:]
                self.xdata_servo = self.xdata_servo[1:]
                self.ydata_servo = self.ydata_servo[1:]
                self.xdata_stepper = self.xdata_stepper[1:]
                self.ydata_stepper = self.ydata_stepper[1:]

            # add new data to end of the ydata list
            self.xdata_motor.append(self.xdata_motor[-1] + 1)
            self.xdata_servo.append(self.xdata_servo[-1] + 1)
            self.xdata_stepper.append(self.xdata_stepper[-1] + 1)  # Add a new value 1 higher than the last.
            self.ydata_motor.append(new_y_motor)
            self.ydata_servo.append(new_y_servo)
            self.ydata_stepper.append(new_y_stepper)

            self.plot_object_motor.setData(self.xdata_motor, self.ydata_motor)
            self.plot_object_servo.setData(self.xdata_servo, self.ydata_servo)
            self.plot_object_stepper.setData(self.xdata_stepper, self.ydata_stepper)


    def potentiometer_read(self):
        input = self.read_input()
        self.ser.reset_input_buffer()
        if input is not None:
            input_scaled = input[0]*POTENTIOMETER_MAP
            self.update_plot(y_axis_label="voltage (V)", x_axis_label="samples",
                            x_range=100, y_range=7 ,new_y=input_scaled)


    def ir_read(self):
        input = self.read_input()
        self.ser.reset_input_buffer()
        if input is not None:
            input_scaled = input[1]*IR_MAP
            self.update_plot(y_axis_label="distance (cm)", x_axis_label="samples",
                            x_range=100, y_range=90 ,new_y=input_scaled)


    def ultrasonic_read(self):
        input = self.read_input()
        self.ser.reset_input_buffer()
        if input is not None:
            input_scaled = input[2]*ULTRASONIC_MAP
            self.update_plot(y_axis_label="distance (cm)", x_axis_label="samples",
                            x_range=100, y_range=7 ,new_y=input_scaled)


    def slot_read(self):
        input = self.read_input()
        self.ser.reset_input_buffer()
        if input is not None:
            input_scaled = input[3]*SLOT_MAP
            self.update_plot(y_axis_label="digital_in", x_axis_label="samples",
                            x_range=100, y_range=7 ,new_y=input_scaled)


    def motor_servo_stepper_read(self):
        input = self.read_input()
        self.ser.reset_input_buffer()
        if input is not None:
            input_scaled = input[4]*(5/255)
            #TODO: Pass the right values to each of new_y_*
            self.update_plot_actuators(new_y_motor=input_scaled, new_y_servo=input_scaled, new_y_stepper=input_scaled)


    def read_input(self):
        if self.read_write_lock == "read" and self.ser.in_waiting > 0:
            data = []
            # read 4 bytes at a time
            for i in range(INPUT_BYTE_SIZE):
                data.append(int.from_bytes(self.ser.read(1), byteorder="little"))
            self.trial_label.setText(("Serial Input: " + str(data)))
            return data
        elif self.ser.in_waiting == 0:
            # print("NO INPUT AVAILABLE")
            self.trial_label.setText("Serial Input: N/A")
            return None
        else:
            return None

        '''
        Note: Index and tag used in below functions is according to this mapping:

        send 'r' to read data
        * Write buffer is a byte array of size four. With the following order of elements:
        1. Potentiometer reading with mapping (0-255) to (0-5V)
        2. SharpIR sensor reading with mapping (0-255) to (10cm-80cm)
        3. Ultrasonic sensor
        4. Slot Sensor 0 or 255 to indicate ON or OFF
        send 'w' to write data
        * Read Buffer is a byte buffer of size seven used to control the actuators:
        1. which actuator to control: 0 - STOP & RESET everything, 1 - stepper, 2 - servo, 3 - dc motor-position, 4 - dc motor-velocity
        2. stepper
        3. servo
        4. dc-motor - position control - direction
        5. dc-motor - position control - target position (degrees 0 to 360 0 to -360)
        6. dc-motor - velocity control - direction
        7. dc-motor - velocity control - target velocity (rpm)
        * To just stop the DC motor - send 3 or 4 and target position/velocity = 0
        '''


    def motor_write_rpm(self):
        if self.mode == "Control Actuators":
            reading = self.motor_slider_rpm.value()
            data = reading * MOTOR_RPM_MAP
            self.write_output(data=data, index=6, tag=4)
            self.ser.reset_output_buffer()
            self.read_write_lock = "read"


    def motor_write_position(self):
        if self.mode == "Control Actuators":
            reading = min(abs(int(self.motor_position_delta.text())),360) * MOTOR_POSITION_MAP
            data = str(reading)
            self.write_output(data=data, index=4, tag=3)
            self.ser.reset_output_buffer()
            self.read_write_lock = "read"


    def servo_write(self):
        print("")
        if self.mode == "Control Actuators":
            self.trial_label.setText("Trying to move servo")
            # data = max(self.servo_slider.value(),5) * SERVO_MAP
            self.write_output(data=self.servo_slider.value(), index=2, tag=2)
            self.ser.reset_output_buffer()
            self.read_write_lock = "read"


    def stepper_write_position(self):
        if self.mode == "Control Actuators":
            sign = 1
            if "-" in self.stepper_position.text(): sign = -1
            data=int(self.stepper_position.text())
            useful_data = min(abs(data),360) * STEPPER_MAP
            if sign == 1:
                self.write_output(data=useful_data, index=1, tag=1)
                self.ser.reset_output_buffer()
                self.read_write_lock = "read"
            else:
                self.change_direction()
                self.write_output(data=useful_data, index=1, tag=1)
                self.ser.reset_output_buffer()
                self.read_write_lock = "read"


    def change_direction(self, actuator=1):
        self.direction.reverse()
        # TODO: call only the necessary function not write_rpm or write_position
        # self.motor_write_rpm(direction=self.direction[-1])
        # time.sleep(2)


    def write_output(self, data=0, index=0, tag=0):
        """
        Write output to serial
        Args:
            data  : actuator control signal
            index : index to modify control string
            tag   : indicator to specify actuator
        """
        # tag args
        # 1 - stepper, 2 - servo, 3 - dc motor-position, 4 - dc motor-velocity

        self.read_write_lock = "write"
        self.ser.write(b'w')

        # Build and Modify Control String
        # string args:  actutor   stepper   servo   pdirection   deltap   vdirec  velocity
        write_string = [  "0",      "0",     "0",      "0",        "0",     "0",    "0"]

        write_string[0] = str(tag)
        write_string[index] = str(data)
        write_string[3] = str(self.direction[-1])
        write_string[5] = str(self.direction[-1])
        print(write_string)

        for i in range(7):
            print(write_string[i])
            self.ser.write(self.custom_atoi(write_string[i]))


    def custom_atoi(self, str_inp):
        res = 0
        for i in range(len(str_inp)):
            res = res * 10 + (ord(str_inp[i]) - ord('0'))

        return res.to_bytes(1, 'big')


    def activate_function(self):
        """
        Calls all functions whcih read data from serial buffer
        Note. This uses the class attribure self.read_write_lock to prevent child
              functions from accessing the serial buffer when something is being written
        """
        if self.mode == "Read Sensor Data" and self.read_write_lock == "read":
            self.port_switch("on")

            # request the arduino for data
            self.ser.write(b'r')

            # activate the function associated with current button
            if self.active_function == "Potentiometer":
                self.potentiometer_read()
            elif self.active_function == "IR":
                self.ir_read()
            elif self.active_function == "Ultrasonic":
                self.ultrasonic_read()
            elif self.active_function == "Slot":
                self.slot_read()

        elif self.mode == "Control Actuators" and self.read_write_lock == "read":
            self.port_switch("on")
            # request the arduino for data
            self.ser.write(b'r')
            self.motor_servo_stepper_read()


    def port_switch(self, switch):
        if(self.ser.isOpen() == False and switch == "on"):
            self.ser.open()
        elif(self.ser.isOpen() == True and switch == "off"):
            self.ser.close()


    def clear_plot(self):
        self.graphWidget.clear()
        self.graphWidget_motor.clear()
        self.graphWidget_servo.clear()
        self.graphWidget_stepper.clear()
        self.init_data_holders()
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()


    # monitor status of radiobutton and accordingly select project/json to load
    def modestate(self,b):
        if b.isChecked():
            self.read_write_lock = "read"
            self.statusBar_1.showMessage(b.text())
            self.mode = b.text()
            # self.clear_plot()
            # self.port_switch("on")


    def sensorstate(self,button):
        if button.isChecked():
            self.graphWidget.clear()
            self.plot_object = None
            self.init_data_holders()
            self.read_write_lock = "read"
            self.active_function = button.text()


    # function to detect keyboard key press
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Right or event.key() == Qt.Key_D:
            pass


    # function to save curr proj before closing
    def closeEvent(self, event):
        self.ser.close()
        print("Closing UI")
        event.accept()



# Initialize The App
app = QApplication(sys.argv)
app.setStyle("Fusion")
palette = QPalette()
palette.setColor(QPalette.Window, QColor(53, 53, 53))
palette.setColor(QPalette.WindowText, Qt.lightGray)
palette.setColor(QPalette.Base, QColor(25, 25, 25))
palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
palette.setColor(QPalette.ToolTipBase, Qt.black)
palette.setColor(QPalette.ToolTipText, Qt.lightGray)
palette.setColor(QPalette.Text, Qt.lightGray)
palette.setColor(QPalette.Button, QColor(53, 53, 53))
palette.setColor(QPalette.ButtonText, Qt.lightGray)
palette.setColor(QPalette.BrightText, Qt.red)
palette.setColor(QPalette.Link, QColor(42, 130, 218))
palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
palette.setColor(QPalette.HighlightedText, Qt.black)
app.setPalette(palette)
UIWindow = main()
app.exec_()
