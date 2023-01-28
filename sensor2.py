from enum import Flag
from hashlib import new
import sys, os
import shutil
import glob
import re
import filecmp
import threading
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
        self.radioButton_sharp_ir = self.findChild(QRadioButton, "radioButton_sharp_ir")
        self.radioButton_ultrasonic = self.findChild(QRadioButton, "radioButton_ultrasonic")
        self.radioButton_slot = self.findChild(QRadioButton, "radioButton_slot")

        self.potentiometer_label = self.findChild(QLabel, "label_potentiometer")
        self.trial_label = self.findChild(QLabel, "label_trial")
        self.potentiometer_values = [0,100]

		# Click-detection to open file explorer Box
        self.button_trial.clicked.connect(self.test)

        self.gv = self.findChild(QGraphicsView, "gv")
        self.gv.setMouseTracking(False)
        self.scene = QGraphicsScene()

        #set radio button state
        self.radioButton_1.toggled.connect(lambda:self.btnstate(self.radioButton_1))
        self.radioButton_2.toggled.connect(lambda:self.btnstate(self.radioButton_2))

        # Activated Filters
        self.pbar = self.findChild(QProgressBar, "progressBar")
        self.statusBar_1 = self.findChild(QStatusBar, "statusbar")
        main.setStatusBar(self, self.statusBar_1)
        self.statusBar_1.setFont(QFont('Helvetica',13))

        # set defualt mode to GUI
        self.mode = "GUI Driven"
        self.init_serial()

		# Show The App
        self.show()

    def init_serial(self):
            self.ser = serial.Serial(
                                    port='/dev/ttyACM0',
                                    baudrate=9600
                                    )

    # load folder and return list of projects(in sets of 7) to filter
    def test(self):
        if self.mode == "GUI Driven":
            print("RECEIVED USER INPUT")
            self.pbar.setValue(self.potentiometer_values[-1])
            self.port_switch("on")
            input = self.ser.read(10)
            self.ser.flush()
            self.trial_label.setText(str(input))
            # self.ser.write(b'1234')
            self.potentiometer_values.reverse()


    def port_switch(self, switch):
        if(self.ser.isOpen() == False and switch == "on"):
            self.ser.open()
        elif(self.ser.isOpen() == True and switch == "off"):
            self.ser.close()

    # monitor status of radiobutton and accordingly select project/json to load
    def btnstate(self,b):
        if b.isChecked():
            self.statusBar_1.showMessage(b.text())
            self.mode = b.text()
            if self.mode == "GUI Driven":
                self.port_switch("on")
            elif self.mode == "Manual":
                self.port_switch("off")

    # function to detect keyboard key press
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Right or event.key() == Qt.Key_D:
            pass

    # function to save curr proj before closing
    def closeEvent(self, event):
        self.ser.close()
        print("closing Tool")
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
