import sys
from PyQt5.uic.uiparser import QtCore
import cv2
import qimage2ndarray
import pathlib
import itertools
import json
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
import random
from ast import literal_eval

DEVICE_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600

class main(QMainWindow):
    def __init__(self):
        super(main, self).__init__()

		# Load the ui file
        uic.loadUi("sensor2.ui", self)

		# Define our widgets
        self.button_trial = self.findChild(QPushButton, "pushButton_trial")

        self.radioButton_1 = self.findChild(QRadioButton, "radioButton_1")
        self.radioButton_2 = self.findChild(QRadioButton, "radioButton_2")

        self.radioButton_potentiometer = self.findChild(QRadioButton, "radioButton_pot")
        self.radioButton_infrared = self.findChild(QRadioButton, "radioButton_infrared")
        self.radioButton_ultrasonic = self.findChild(QRadioButton, "radioButton_ultrasonic")
        self.radioButton_slot = self.findChild(QRadioButton, "radioButton_slot")

        self.motor_slider = self.findChild(QSlider, "slider_motor")
        self.motor_servo = self.findChild(QSlider, "slider_servo")
        self.motor_stepper = self.findChild(QSlider, "slider_stepper")
        self.motor_stepper.setValue(50)

		# trial stuff
        self.potentiometer_values = [0,100]
        self.potentiometer_label = self.findChild(QLabel, "label_potentiometer")
        self.trial_label = self.findChild(QLabel, "label_trial")

        self.scene = QGraphicsScene()

        # set button connections
        self.button_trial.clicked.connect(self.test)

        self.radioButton_1.toggled.connect(lambda:self.modestate(self.radioButton_1))
        self.radioButton_2.toggled.connect(lambda:self.modestate(self.radioButton_2))

        self.radioButton_potentiometer.toggled.connect(lambda:self.sensorstate(self.radioButton_potentiometer))
        self.radioButton_infrared.toggled.connect(lambda:self.sensorstate(self.radioButton_infrared))
        self.radioButton_ultrasonic.toggled.connect(lambda:self.sensorstate(self.radioButton_ultrasonic))
        self.radioButton_slot.toggled.connect(lambda:self.sensorstate(self.radioButton_slot))

        self.motor_slider.sliderReleased.connect(lambda:self.motor_write)

        # Activate toolbars
        self.pbar = self.findChild(QProgressBar, "progressBar")
        self.statusBar_1 = self.findChild(QStatusBar, "statusbar")
        main.setStatusBar(self, self.statusBar_1)
        self.statusBar_1.setFont(QFont('Helvetica',13))

        # set defualt mode to Read sensor data (optional)
        self.mode = "Read Sensor Data"
        # initilaize the Aruduino's Serial Port
        try:
            self.init_serial()
        except serial.SerialException:
            print("NO ARDUINO DETECTED")
            print("Please connect the Arduino and ensure the Port and Baud Rates are correct")
            exit()

        self.active_function = None

        self.init_data_holders()
        # set the default mode to read
        self.read_write_lock = "read"

        # the de-facto main loop of the program which keeps calling the activated function
        self.timer = QTimer()
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.activate_function)
        self.timer.start()

		# Show The App
        self.show()

    def init_serial(self):
        self.ser = serial.Serial(
                                port=DEVICE_PORT,
                                baudrate=BAUD_RATE
                                )


    def init_data_holders(self):
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
            # self.graphWidget.setXRange(0, x_range, padding=0)
            self.graphWidget.setYRange(0, y_range, padding=0)
            self.graphWidget.showGrid(x=True, y=True)
            self.plot_object = self.graphWidget.plot(self.xdata, self.ydata, pen=pen)
        else:
            if len(self.xdata) > self.plot_cache_length and len(self.ydata) > self.plot_cache_length:
                # clear graph after reaching max_length
                self.xdata = self.xdata[1:]
                self.ydata = self.ydata[1:]

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
        input = int.from_bytes(self.ser.read(), byteorder="little")
        self.ser.flush()
        input_scaled = input*(5/255)
        self.update_plot(y_axis_label="voltage", x_axis_label="samples",
                         x_range=100, y_range=7 ,new_y=input_scaled)


    def motor_servo_stepper_read(self):
        input = int.from_bytes(self.ser.read(), byteorder="little")
        self.ser.flush()
        input_scaled = input*(5/255)
        #TODO: Pass the right values to each of new_y_*
        self.update_plot_actuators(new_y_motor=input_scaled, new_y_servo=input_scaled, new_y_stepper=input_scaled)


    def motor_write(self):
        pass

    def servo_write(self):
        pass

    def stepper_write(self):
        pass

    # load folder and return list of projects(in sets of 7) to filter
    def test(self):
        if self.mode == "Read Sensor Data":
            print("RECEIVED USER INPUT")
            self.pbar.setValue(self.potentiometer_values[-1])
            # self.port_switch("on")
            input = int.from_bytes(self.ser.read(), byteorder="little")
            input = input*(5/255)
            # self.ser.flush()
            self.trial_label.setText(str(input))
            # self.ser.write(b'1234')
            self.potentiometer_values.reverse()


    def activate_function(self):
        """
        Calls all functions whcih read data from serial buffer
        Note. This uses the class attribure self.read_write_lock to prevent child
              functions from accessing the serial buffer when something is being written
        """
        if self.mode == "Read Sensor Data" and self.read_write_lock == "read":
            self.port_switch("on")
            if self.active_function == "Potentiometer":
                self.potentiometer_read()
            elif self.active_function == "IR":
                self.ir_calc()
            elif self.active_function == "Ultrasonic":
                self.ultrasonic_calc()
            elif self.active_function == "Slot":
                self.slot_calc()

        elif self.mode == "Control Actuators" and self.read_write_lock == "read":
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
        self.ser.flush()


    # monitor status of radiobutton and accordingly select project/json to load
    def modestate(self,b):
        if b.isChecked():
            self.statusBar_1.showMessage(b.text())
            self.mode = b.text()
            self.clear_plot()
            self.port_switch("on")


    def sensorstate(self,button):
        if button.isChecked():
            self.clear_plot()
            self.active_function = button.text()

    # function to detect keyboard key press
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Right or event.key() == Qt.Key_D:
            pass

    # function to save curr proj before closing
    def closeEvent(self, event):
        self.ser.close()
        print("Closing Tool")
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
