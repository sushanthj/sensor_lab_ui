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

        self.potentiometer_label = self.findChild(QLabel, "label_potentiometer")
        self.trial_label = self.findChild(QLabel, "label_trial")
        self.potentiometer_values = [0,100]

		# Click-detection to open file explorer Box
        self.button_trial.clicked.connect(self.test)

        self.scene = QGraphicsScene()

        #set radio button state
        self.radioButton_1.toggled.connect(lambda:self.modestate(self.radioButton_1))
        self.radioButton_2.toggled.connect(lambda:self.modestate(self.radioButton_2))

        self.radioButton_potentiometer.toggled.connect(lambda:self.sensorstate(self.radioButton_potentiometer))
        self.radioButton_infrared.toggled.connect(lambda:self.sensorstate(self.radioButton_infrared))
        self.radioButton_ultrasonic.toggled.connect(lambda:self.sensorstate(self.radioButton_ultrasonic))
        self.radioButton_slot.toggled.connect(lambda:self.sensorstate(self.radioButton_slot))

        # Activated Filters
        self.pbar = self.findChild(QProgressBar, "progressBar")
        self.statusBar_1 = self.findChild(QStatusBar, "statusbar")
        main.setStatusBar(self, self.statusBar_1)
        self.statusBar_1.setFont(QFont('Helvetica',13))

        # set defualt mode to GUI
        self.mode = "Read Sensor Data"
        self.init_serial()
        self.active_function = None

        self.plot_cache_length = 100
        self.xdata = [0]
        self.ydata = [0]
        self.plot_object = None

        self.timer = QTimer()
        self.timer.setInterval(10)
        # self.timer.timeout.connect(self.update_plot)
        self.timer.timeout.connect(self.activate_function)
        self.timer.start()

		# Show The App
        self.show()

    #TODO: Remove this function after testing
    def update_plot(self,y_axis_label, x_axis_label, x_range, y_range, new_y):
        color = self.palette().color(QPalette.Window)  # Get the default window background,
        pen = pg.mkPen(color=(255, 0, 0))

        if self.plot_object is None:
            print("Creating plot object")
            self.graphWidget.setBackground(color)
            self.graphWidget.setLabel('left', y_axis_label)
            self.graphWidget.setLabel('bottom', x_axis_label)
            # self.graphWidget.setXRange(0, x_range, padding=0)
            self.graphWidget.setYRange(0, y_range, padding=0)
            self.plot_object = self.graphWidget.plot(self.xdata, self.ydata, pen=pen)
        else:
            if len(self.xdata) > self.plot_cache_length and len(self.ydata) > self.plot_cache_length:
                # clear graph after reaching max_length
                self.xdata = self.xdata[1:]
                self.ydata = self.ydata[1:]

            self.xdata.append(self.xdata[-1] + 1)  # Add a new value 1 higher than the last.
            self.ydata.append(new_y)  # Add a new random value.
            self.plot_object.setData(self.xdata, self.ydata)


    def potentiometer_calc(self):
        input = int.from_bytes(self.ser.read(), byteorder="little")
        self.ser.flush()
        input_scaled = input*(5/255)
        self.update_plot(y_axis_label="voltage", x_axis_label="samples",
                         x_range=100, y_range=7 ,new_y=input_scaled)

    def init_serial(self):
        self.ser = serial.Serial(
                                port='/dev/ttyACM0',
                                baudrate=9600
                                )

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
        if self.mode == "Read Sensor Data":
            self.port_switch("on")
            if self.active_function == "Potentiometer":
                self.potentiometer_calc()
            elif self.active_function == "IR":
                self.ir_calc()
            elif self.active_function == "Ultrasonic":
                self.ultrasonic_calc()
            elif self.active_function == "Slot":
                self.slot_calc()
        #TODO: Not sure about this
        else:
            self.active_function = "Motor Control"


    def port_switch(self, switch):
        if(self.ser.isOpen() == False and switch == "on"):
            self.ser.open()
        elif(self.ser.isOpen() == True and switch == "off"):
            self.ser.close()


    def clear_plot(self):
        self.graphWidget.clear()
        self.plot_object = None
        self.xdata = [0]
        self.ydata = [0]
        self.ser.flush()


    # monitor status of radiobutton and accordingly select project/json to load
    def modestate(self,b):
        if b.isChecked():
            self.statusBar_1.showMessage(b.text())
            self.mode = b.text()
            if self.mode == "Read Sensor Data":
                self.port_switch("on")
            elif self.mode == "Control Actuators":
                self.clear_plot()
                self.port_switch("on")
            else:
                self.port_switch("off")


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
