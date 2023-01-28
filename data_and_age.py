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

## Selective Dataset Review Version
## Trial with changing jsons

AGE_GROUP_DICT = {1:"Superior_Colliculus", 2:"Inferior_Colliculus", 3:"Red_Nucleus", 4:"Inferior_Olive", 5:"Corticospinal_Tract"}

# Create our custom QGraphicsScene
class MyGraphicsScene(QGraphicsScene):
    signalMousePos = pyqtSignal(QPointF)
    signalMousePos_tracking = pyqtSignal(QPointF)
    signalMousePos_end = pyqtSignal(QPointF)
    def __init__(self, indicator, parent=None):
        self.indicator = indicator
        super(MyGraphicsScene, self).__init__(parent)

    def mousePressEvent(self, QGraphicsSceneMouseEvent):
        if self.indicator == True:
            pos = QGraphicsSceneMouseEvent.lastScenePos()
            #print("position is: ",pos)
            self.signalMousePos.emit(pos)

    def mouseMoveEvent(self, QGraphicsSceneMouseEvent):
        if self.indicator == True:
            pos = QGraphicsSceneMouseEvent.lastScenePos()
            #print("updated position is: ",pos)
            self.signalMousePos_tracking.emit(pos)

    def mouseReleaseEvent(self, QGraphicsSceneMouseEvent):
        if self.indicator == True:
            pos = QGraphicsSceneMouseEvent.lastScenePos()
            self.signalMousePos_end.emit(pos)

class main(QMainWindow):
    def __init__(self):
        super(main, self).__init__()

		# Load the ui file
        uic.loadUi("data_and_age.ui", self)

        self.IMAGE_FOLDER_PATH = ""

        # variable which tracks the set of projects (the unfiltered projects are divided into sets of 7)
        self.proj_set_track = 0

        # variable which holds file path to the eg. 'v2' folder (the folder which has subfolders
        # named specifically as 'annotation_jsons' and 'annotation_jsons_filtered')
        self.fname = None

        # variable that loads the json of whicever project is selected (whichever radiobutton is pressed)
        self.proj = None
        self.proj_replica = None

        # variable to keep note of image position to which user has scrolled (also used to update progress bar)
        self.json_pos_tracker = {}

        # variable to track if we need to load from temp folder instead of annotation_jsons (used in json_loader)
        self.load_temp_tracker = 1

        # variable to track the box deletion status of each image in each project
        # of structure {proj_1: {img_1 :[0,1], img2: [0,0]}}, meaning for proj_1's img_2, no boxes are to be deleted
        # for proj_1's img_1 the second box is to be deleted
        self.box_del_tracker = {}

        # variable to store displayed (current) image object
        self.current_img_object = None

        self.removed_box_count = 0
        self.curr_proj = ""

        # a derivative of self.json_pos_tracker
        self.json_pos = 0
        self.all_jsons_list = None
        self.unfiltered_jsons = None

        # tracker to detect last image forward or backward command
        self.forward_backward_tracker = 1

        # variables involved in allowing user to draw boxes
        self.drawing = False
        self.box_start = [0,0]
        self.box_end = [0,0]
        self.box_curernt_pos = None
        self.new_box_height = None
        self.new_box_width = None

        self.indicator = ''
        self.box_left_edge = [0,0,0,0]
        self.box_right_edge = [0,0,0,0]
        self.box_top_edge = [0,0,0,0]
        self.box_bot_edge = [0,0,0,0]
        self.resize_edge_lock = None
        self.box_buffer = 0.15

        # gets the scale factor from scripts.py which we will use when re-drawing boxes
        self.scale_x, self.scale_y = None, None

        # tracker to see if image path has been loaded
        self.img_path_load_tracker = 0

        # tracker to differentiate between redrawing on an existing box or adding a completely new box
        self.redraw_box_tracker = False

        # tracker to note index of box in box_del_list which has been asked to redraw
        self.box_index = None

        # tracker to check which box in the current image has been selected for age categorisation
        self.selected_box_index = None

		# Define our widgets
        self.button_load_img_path = self.findChild(QPushButton, "pushButton_open_img")
        self.button_open = self.findChild(QPushButton, "pushButton_open")
        self.button_next = self.findChild(QPushButton, "pushButton_next")
        self.button_prev = self.findChild(QPushButton, "pushButton_prev")
        self.button_next_proj = self.findChild(QPushButton, "pushButton_next_proj")
        self.button_prev_proj = self.findChild(QPushButton, "pushButton_prev_proj")
        self.button_save_1 = self.findChild(QPushButton, "pushButton_save_1")
        self.button_save_2 = self.findChild(QPushButton, "pushButton_save_2")
        #self.button_save_3 = self.findChild(QPushButton, "pushButton_save_3")
        #self.button_load = self.findChild(QPushButton, "pushButton_load")
        self.button_del_img = self.findChild(QPushButton, "pushButton_del_img")
        self.button_save_img_ref = self.findChild(QPushButton, "pushButton_save_img_ref")
        self.button_undo_draw = self.findChild(QPushButton, "pushButton_undo_draw")

        self.radioButton_1 = self.findChild(QRadioButton, "radioButton_1")
        self.radioButton_2 = self.findChild(QRadioButton, "radioButton_2")
        self.radioButton_3 = self.findChild(QRadioButton, "radioButton_3")
        self.radioButton_4 = self.findChild(QRadioButton, "radioButton_4")
        self.radioButton_5 = self.findChild(QRadioButton, "radioButton_5")
        self.radioButton_6 = self.findChild(QRadioButton, "radioButton_6")
        self.radioButton_7 = self.findChild(QRadioButton, "radioButton_7")

        self.checkbox_1 = self.findChild(QCheckBox, "checkBox_1")
        self.checkbox_2 = self.findChild(QCheckBox, "checkBox_2")
        self.checkbox_3 = self.findChild(QCheckBox, "checkBox_3")
        self.checkbox_4 = self.findChild(QCheckBox, "checkBox_4")
        self.checkbox_5 = self.findChild(QCheckBox, "checkBox_5")
        self.checkbox_6 = self.findChild(QCheckBox, "checkBox_6")
        self.checkbox_7 = self.findChild(QCheckBox, "checkBox_7")

        self.curr_img_name = self.findChild(QLabel, "label_img_name")
        self.img_atts = self.findChild(QLabel, "label_img_atts")
        self.box_atts = self.findChild(QLabel, "label_box_atts")
        self.prog_bar_label = self.findChild(QLabel, "label_prog_bar_name")
        self.label_img_path = self.findChild(QLabel, "label_img_path")
        self.label_ann_path = self.findChild(QLabel, "label_ann_path")
        self.label_img_count = self.findChild(QLabel, "label_img_count")

        self.small_box_filter_checkbox = self.findChild(QAction, "actionSmall_Box_Filter_2")
        self.random_object_filter_checkbox = self.findChild(QAction, "actionRandom_Object_Filter_2")
        self.blurred_image_filter_checkbox = self.findChild(QAction, "actionBlurred_Image_Filter_2")
        self.side_partial_filter_checkbox = self.findChild(QAction, "actionSide_Partial_Filter_2")
        self.saturated_filter_checkbox = self.findChild(QAction, "actionSaturated_Box_Filter_2")

        self.run_filter = self.findChild(QAction, "actionRun_Filter")

		# Click-detection to open file explorer Box
        self.button_open.clicked.connect(self.load_folder)
        self.button_load_img_path.clicked.connect(self.load_img_path)

        #Click-detection to go to next/prev set of projects
        self.button_next_proj.clicked.connect(self.next_proj_set)
        self.button_prev_proj.clicked.connect(self.prev_proj_set)

        # Click-detection to go to next image
        self.button_next.clicked.connect(self.json_next_img)
        self.button_prev.clicked.connect(self.json_prev_img)

        # Click-detection to save to temp folder
        self.button_save_1.clicked.connect(self.save_temp)

        # Click-detection to save as filtered json
        self.button_save_2.clicked.connect(self.save_as_filtered_json)

        # Click-detection to save all temp jsons to filtered jsons folder
        #self.button_save_3.clicked.connect(self.save_all_temp)

        # Click-detection to delete image
        self.button_del_img.clicked.connect(self.del_img)

        # Click-detection to save image for future reference
        self.button_save_img_ref.clicked.connect(self.save_img_ref)

        # Click-detection to undo drawn box
        self.button_undo_draw.clicked.connect(self.undo_draw)

        # Connect Filter QAction to function
        self.run_filter.triggered.connect(self.run_custom_filters)

        # lock for box_del_tracker
        self.box_lock = threading.Lock()

        self.gv = self.findChild(QGraphicsView, "gv")
        self.gv.setMouseTracking(True)
        # QGraphicsScene is the default class, but we'll be using a custom class
        # self.scene = QGraphicsScene()
        self.scene = MyGraphicsScene(indicator=self.drawing)
        self.scene.signalMousePos.connect(self.pointSelection)
        self.scene.signalMousePos_tracking.connect(self.pointSelection_tracking)
        self.scene.signalMousePos_tracking.connect(self.pointResize_tracking)
        self.scene.signalMousePos_end.connect(self.end_box_draw)

        # enable mouse tracking
        self.setMouseTracking(True)

        #set radio button state
        self.radioButton_1.toggled.connect(lambda:self.btnstate(self.radioButton_1))
        self.radioButton_2.toggled.connect(lambda:self.btnstate(self.radioButton_2))
        self.radioButton_3.toggled.connect(lambda:self.btnstate(self.radioButton_3))
        self.radioButton_4.toggled.connect(lambda:self.btnstate(self.radioButton_4))
        self.radioButton_5.toggled.connect(lambda:self.btnstate(self.radioButton_5))
        self.radioButton_6.toggled.connect(lambda:self.btnstate(self.radioButton_6))
        self.radioButton_7.toggled.connect(lambda:self.btnstate(self.radioButton_7))

        # Activated Filters


        self.pbar = self.findChild(QProgressBar, "progressBar")
        self.statusBar_1 = self.findChild(QStatusBar, "statusbar")
        main.setStatusBar(self, self.statusBar_1)
        self.statusBar_1.setFont(QFont('Helvetica',13))

		# Show The App
        self.show()


    # load image path folder (1 above images folder)
    # if this function is not executed, take default value of self.IMAGE_FOLDER_PATH
    def load_img_path(self):
        temp_path = QFileDialog.getExistingDirectory(self, 'Select folder which contains the "images" folder',
                                                          '/home/sush/TS/', QFileDialog.ShowDirsOnly)
        if temp_path != "":
            self.IMAGE_FOLDER_PATH = temp_path
            self.img_path_load_tracker = 1

    # load folder and return list of projects(in sets of 7) to filter
    def load_folder(self):
        #initialize few variables
        ann_jsons = []
        ann_jsons_filtered = []

        #open file explorer dialog window and compute which jsons/projects need are unfiltered
        self.fname = QFileDialog.getExistingDirectory(self, 'Select dataset json folder (eg. v2 folder)',
                                                '/home/sush/TS/jsons+tfrecords/', QFileDialog.ShowDirsOnly)

        if self.fname != "":
            for x in os.listdir(os.path.join(self.fname,"annotation_json")):
                if x.endswith(".json"):
                    ann_jsons.append(x)

            if os.path.exists(os.path.join(self.fname, "annotation_json_filtered")):
                for x in os.listdir(os.path.join(self.fname,"annotation_json_filtered")):
                    if x.endswith(".json"):
                        ann_jsons_filtered.append(x)

            else:
                os.makedirs(os.path.join(self.fname,"annotation_json_filtered"))
                for x in os.listdir(os.path.join(self.fname,"annotation_json_filtered")):
                    if x.endswith(".json"):
                        ann_jsons_filtered.append(x)

            # update label to show which annotation folder is loaded
            temp_name = "annotation folder path: " + self.fname
            self.label_ann_path.setText(temp_name)

            # find out which jsons are yet to be filtered
            self.unfiltered_jsons = list(set(ann_jsons) - set(ann_jsons_filtered))
            ann_jsons.sort()

            if ann_jsons != None:
                temp_iter = iter(ann_jsons)
                length_to_split = [7]*(int(len(ann_jsons)/7)+1)
                self.all_jsons_list = [list(itertools.islice(temp_iter, elem))for elem in length_to_split]
                #for i in self.unfilterd_jsons_list:
                #    print(i)
                #print(len(self.unfilterd_jsons_list))
            #each item of unfiltered_jsons_list is a set of seven projects to be assigned to radiobuttons
            #returning 1 tells listener function that we are passing projects for first time (to assign first 7 proj)
            self.statusBar_1.showMessage("loaded %d project jsons", len(ann_jsons))
            self.projec_assign(self.all_jsons_list, self.proj_set_track)

        else:
            print("No file selected")
            pass


    # function to assign proj names to radiobutton
    def projec_assign(self, projects, tracker):
        projs_to_assign = projects[tracker]
        radio_button_list = [self.radioButton_1, self.radioButton_2, self.radioButton_3,
                            self.radioButton_4, self.radioButton_5, self.radioButton_6, self.radioButton_7]
        checkbox_list = [self.checkbox_1, self.checkbox_2, self.checkbox_3, self.checkbox_4,
                        self.checkbox_5, self.checkbox_6, self.checkbox_7]
        print("current project", self.curr_proj)
        for p in range(7):
            try:
                radio_button_list[p].setText(projs_to_assign[p])
                #print(projs_to_assign[p])
                if projs_to_assign[p] not in self.unfiltered_jsons:
                    checkbox_list[p].setChecked(True)
                else:
                    checkbox_list[p].setChecked(False)
            except IndexError:
                radio_button_list[p].setText("")


    # monitor status of radiobutton and accordingly select project/json to load
    def btnstate(self,b):
        if b.isChecked():
            self.statusBar_1.showMessage(b.text())
            self.curr_proj = b.text()
            print(self.curr_proj)
            self.json_loader()

    # initialize json_pos_tracker if not already done and load the respective json file
    def json_loader(self):
        curr_proj_name = self.curr_proj
        # check if the button has even been linked to anything
        if curr_proj_name != "RadioButton" and curr_proj_name != "":
            # if the curr_proj has not been loaded before
            if curr_proj_name not in self.json_pos_tracker.keys():
                # initialize box_del_tracker for this new project
                self.box_del_tracker[curr_proj_name] = {}
                self.pbar.setValue(0)
                # json_pos_tracker is a dict of type {json_1: [0,10], json_2: [2,20]} meaning json_2 has
                # been scrolled to 3rd image and can go upto max 20 (as 20 is total no. of imgs in json)
                self.json_pos_tracker[curr_proj_name] = []
                self.json_pos_tracker[curr_proj_name].append(0)
                print("file name: ",self.fname)
                print("curr_proj_name: ", curr_proj_name)

                #check if we are loading from temp or else loading fresh

                # loading from temp
                # if self.load_temp_tracker == 1:
                #     try:
                #         json_location = os.path.join(self.fname,"temp_json",curr_proj_name)
                #         self.proj = json.load(open(json_location,'r'))
                #         self.proj_replica = json.load(open(json_location,'r'))
                #         temp_json_ref_dict_path = os.path.join(self.fname,"temp_json",'ref_dicts',curr_proj_name)
                #         temp_json_ref_dict = json.load(open(temp_json_ref_dict_path,'r'))
                #         self.box_del_tracker[self.curr_proj] = temp_json_ref_dict
                #     except FileNotFoundError:
                #         json_location = os.path.join(self.fname,"annotation_json",curr_proj_name)
                #         self.proj = json.load(open(json_location,'r'))
                #         self.proj_replica = json.load(open(json_location,'r'))
                #         for i in range(len(self.proj['annotations'])):
                #             boxes_count = len(self.proj['annotations'][i]['bbox_info'])
                #             box_del_list = [1]*boxes_count
                #             self.box_del_tracker[self.curr_proj][str(i)] = box_del_list
                #
                #
                # loading fresh
                # else:
                    # json_location = os.path.join(self.fname,"annotation_json",curr_proj_name)
                    # self.proj = json.load(open(json_location,'r'))
                    # self.proj_replica = json.load(open(json_location,'r'))
                    # for i in range(len(self.proj['annotations'])):
                    #     boxes_count = len(self.proj['annotations'][i]['bbox_info'])
                    #     box_del_list = [1]*boxes_count
                    #     self.box_del_tracker[self.curr_proj][str(i)] = box_del_list

                json_location = os.path.join(self.fname,"annotation_json",curr_proj_name)
                self.proj = json.load(open(json_location,'r'))
                self.proj_replica = json.load(open(json_location,'r'))
                # initialize the format of the ref dict which will be saved for each box
                box_dict = {
                    'box_status': 1,
                    'box_age': 0,
                    'box_redraw': 0,
                    'box_redraw_dimensions': [],
                    'box_new': 0,
                    'box_new_dimensions': []
                }
                if self.load_temp_tracker == 1:
                    try:
                        temp_json_ref_dict_path = os.path.join(self.fname,"temp_json",'ref_dicts',curr_proj_name)
                        temp_json_ref_dict = json.load(open(temp_json_ref_dict_path,'r'))
                        self.box_del_tracker[self.curr_proj] = temp_json_ref_dict

                    except FileNotFoundError:
                        print("len of ref_dict will be :",len(self.proj['annotations']))
                        for i in range(len(self.proj['annotations'])):
                            boxes_count = len(self.proj['annotations'][i]['bbox_info'])
                            box_del_list = []
                            for j in range(boxes_count):
                                box_del_list.append(deepcopy(box_dict))
                            self.box_del_tracker[self.curr_proj][str(i)] = box_del_list
                # loading fresh
                else:
                    print("len of ref_dict will be :",len(self.proj['annotations']))
                    for i in range(len(self.proj['annotations'])):
                        boxes_count = len(self.proj['annotations'][i]['bbox_info'])
                        box_del_list = []
                        for j in range(boxes_count):
                            box_del_list.append(deepcopy(box_dict))
                        self.box_del_tracker[self.curr_proj][str(i)] = box_del_list

                # since project being loaded first time, initialize json_pos to 0
                self.json_pos = 0
                #extract images from json using json_pos and accordingly update checkbox
                curr_annotation = deepcopy(self.proj['annotations'][self.json_pos])
                proj_length = len(self.proj['annotations'])
                self.json_pos_tracker[curr_proj_name].append(proj_length)
                print(curr_annotation)
                self.load_img(curr_annotation)

            # if the curr_proj has been loaded before
            else:
                json_location = os.path.join(self.fname,"annotation_json",curr_proj_name)
                self.proj = json.load(open(json_location,'r'))
                self.proj_replica = json.load(open(json_location,'r'))
                # since project already exists, get the old json position from json_pos_tracker
                self.json_pos = self.json_pos_tracker[curr_proj_name][0]
                # get back the progress bar value as well
                if self.json_pos_tracker[curr_proj_name][0] == 0:
                    pass
                else:
                    progress = ((self.json_pos_tracker[curr_proj_name][0]+1)/self.json_pos_tracker[curr_proj_name][1])
                    progress = int(progress*100)
                    self.pbar.setValue(progress)
                #extract images from json using json_pos and accordingly update checkbox
                curr_annotation = deepcopy(self.proj['annotations'][self.json_pos])
                self.load_img(curr_annotation)
        else:
            print("Incorrect project chosen")
            self.statusBar_1.showMessage("Incorrect project chosen")
            pass


    def json_next_img(self):
        curr_proj_name = self.curr_proj
        # ensure we don't increment index above len(no. of images in json)
        if self.json_pos_tracker[curr_proj_name][0] == (self.json_pos_tracker[curr_proj_name][1]-1):
            pass
        else:
            del self.current_img_object
            del self.img_m
            self.gv.items().clear
            del self.scene_img
            self.scene.clear()
            self.selected_box_index = None
            self.json_pos_tracker[curr_proj_name][0] += 1
            self.json_pos = self.json_pos_tracker[curr_proj_name][0]
            curr_annotation = deepcopy(self.proj['annotations'][self.json_pos])
            if self.json_pos_tracker[curr_proj_name][0] == 0:
                pass
            else:
                progress = ((self.json_pos_tracker[curr_proj_name][0]+1)/self.json_pos_tracker[curr_proj_name][1])
                progress = int(progress*100)
                print("project completion {}%".format(progress))
                self.pbar.setValue(progress)
                temp_label = "Project Image Count: " + str(self.json_pos_tracker[curr_proj_name][1])
                self.label_img_count.setText(temp_label)
            self.box_atts.setText("")
            self.forward_backward_tracker = 1
            self.load_img(curr_annotation)

    def json_prev_img(self):
        curr_proj_name = self.curr_proj
        # ensure we don't decrement below 0
        if self.json_pos_tracker[curr_proj_name][0] == 0:
            pass
        else:
            del self.current_img_object
            del self.img_m
            self.gv.items().clear
            del self.scene_img
            self.scene.clear()
            self.selected_box_index = None
            self.json_pos_tracker[curr_proj_name][0] -= 1
            self.json_pos = self.json_pos_tracker[curr_proj_name][0]
            curr_annotation = deepcopy(self.proj['annotations'][self.json_pos])
            self.forward_backward_tracker = 0
            self.load_img(curr_annotation)
            if self.json_pos_tracker[curr_proj_name][0] == 0:
                self.pbar.setValue(0)
            else:
                progress = ((self.json_pos_tracker[curr_proj_name][0]+1)/self.json_pos_tracker[curr_proj_name][1])
                progress = int(progress*100)
                print(progress)
                self.pbar.setValue(progress)


    def load_img(self, ann):
        # path of image initialized here
        if self.img_path_load_tracker == 0:
            self.IMAGE_FOLDER_PATH = self.fname

        elif self.img_path_load_tracker == 1:
            pass

        else:
            print("No Image folder found, please specify path by pressing 'Image folder path' button")
            self.statusBar_1.showMessage("No Image folder found, please specify path by pressing 'Image folder path' button")

        if self.IMAGE_FOLDER_PATH != "":
            temp_name = "image folder path: " + self.IMAGE_FOLDER_PATH
            self.label_img_path.setText(temp_name)
            # if using windows use second line below instead first
            # current_image_name = os.path.join(self.IMAGE_FOLDER_PATH, ann["image_path"])
            current_image_name = self.IMAGE_FOLDER_PATH + "/" + ann["image_path"]
            print("selected_img:", current_image_name)
            # get the box_dict for that particular image (self.json_pos gives image)
            box_dict = deepcopy(self.box_del_tracker[self.curr_proj][str(self.json_pos)])

            # get current image object and convert to right format
            self.current_img_object = Images(current_image_name, ann, box_dict)
            resized_img, conditional, self.scale_x, self.scale_y = self.current_img_object.add_bbox()
            self.img_m = QPixmap(qimage2ndarray.array2qimage(cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB)))

            # display img
            self.scene_img = self.scene.addPixmap(self.img_m)
            self.gv.setScene(self.scene)

            # update image name and attributes
            self.curr_img_name.setText(self.current_img_object.img_name)
            temp_img_atts = json.dumps(self.proj["details"], indent=2)
            temp_img_atts = temp_img_atts.strip("{}")
            self.img_atts.setText(temp_img_atts)

            # Use this conditional if you want to skip any particular type of images in the future
            if conditional == 0:
                if self.forward_backward_tracker == 1:
                    self.json_next_img()
                elif self.forward_backward_tracker == 0:
                    self.json_prev_img()
                else:
                    pass


    # remove the deleted boxes from original json and save new filtered_json to temp folder
    def save_temp(self):
        # create folder for temp_jsons
        temp_folder_path = os.path.join(self.fname,"temp_json")
        if not os.path.exists(temp_folder_path):
            os.makedirs(temp_folder_path)

        # create folder for reference_dicts of temp_jsons
        temp_folder_path_2 = os.path.join(self.fname,"temp_json","ref_dicts")
        if not os.path.exists(temp_folder_path_2):
            os.makedirs(temp_folder_path_2)

        # get the dict which dictates which images should be kept/removed
        ref_dict = self.box_del_tracker[self.curr_proj]
        # new_json = self.proj

        # new_json_path = os.path.join(temp_folder_path,self.curr_proj)
        # with open(new_json_path, "w") as outfile:
        #     json.dump(new_json, outfile)
        new_json_ref_dict_path = os.path.join(temp_folder_path_2,self.curr_proj)
        with open(new_json_ref_dict_path, "w") as outfile:
            json.dump(ref_dict, outfile)
        print("Saved to temp Folder")
        self.statusBar_1.showMessage("Saved to temp Folder")

    # remove the deleted boxes from original json and save new filtered_json to annotation_jsons_filtered folder
    def save_as_filtered_json(self):
        self.save_temp()
        final_folder_path = os.path.join(self.fname,"annotation_json_filtered")
        # get the dict which dictates which images should be kept/removed
        ref_dict = self.box_del_tracker[self.curr_proj]
        ref_json = self.proj
        new_json = self.proj_replica
        i_del_counter = 0
        annotations = ref_json['annotations']
        print("number of images in project :",len(annotations))
        #print(len(ref_dict.keys()))
        for i in range(len(annotations)):
            # ref dict is {image_1: [1,1,0]} meaning first two boxes should be retained and last one deleted
            # delete image if no boxes in image
            for j in range(len(ref_dict[str(i)])):
                # check if box_attributes exists as a dict in json
                try:
                    if isinstance(new_json['annotations'][i]['bbox_info'][j]['box_attr'], dict):
                        pass
                    else:
                        new_json['annotations'][i]['bbox_info'][j]['box_attr'] = {}
                except IndexError:
                    # check if new box has been added
                    if ref_dict[str(i)][j]['box_new'] == 1:
                        new_box_info = {
                            'box_coordinates': ref_dict[str(i)][j]['box_new_dimensions'],
                            'box_attr': {'box_retain': ref_dict[str(i)][j]['box_status'], 'box_age': ref_dict[str(i)][j]['box_age']}
                        }
                        new_json['annotations'][i]['bbox_info'].append(new_box_info)
                # check if box has been redrawn
                if ref_dict[str(i)][j]['box_redraw'] == 1:
                    new_json['annotations'][i]['bbox_info'][j]['box_coordinates'] = ref_dict[str(i)][j]['box_redraw_dimensions']

                new_json['annotations'][i]['bbox_info'][j]['box_attr']['box_retain'] = ref_dict[str(i)][j]['box_status']
                new_json['annotations'][i]['bbox_info'][j]['box_attr']['box_age'] = ref_dict[str(i)][j]['box_age']
                new_json['Age Details'] = AGE_GROUP_DICT

        new_json_path = os.path.join(final_folder_path,self.curr_proj)
        with open(new_json_path, "w") as outfile:
            json.dump(new_json, outfile)
        print("saved to filtered folder")
        self.statusBar_1.showMessage("Saved to annotation_json_filtered Folder")
        print(self.curr_proj)
        if(self.curr_proj in self.unfiltered_jsons):
            self.unfiltered_jsons.remove(self.curr_proj)
        self.projec_assign(self.all_jsons_list, self.proj_set_track)


    # Function yet to be done
    '''
    def save_all_temp(self):
        print("saving all temp jsons to filtered folder")
        for filename in glob.glob(os.path.join(self.fname,"temp_jsons",'*.json')):
            print(filename)
            json_name = filename.split("/temp_jsons/")[1]
            print(json_name)
            os.rename(filename, os.path.join(self.fname,"annotation_jsons_filtered",json_name))
            #os.replace(filename, os.path.join(self.fname,"annotation_jsons_filtered",filename))
            #shutil.move(filename, os.path.join(self.fname,"annotation_jsons_filtered",json_name))
    '''

    def run_custom_filters(self):
        print("Running Custom Filters")

    def refine_coords(self,point):
        if point < 0:
            point_r = 0
        elif point > 744:
            point_r = 744
        else:
            point_r = int(point)
        return point_r

    # function to detect mouse click
    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.RightButton and self.drawing == False:
            self.box_deleter(QMouseEvent.x(), QMouseEvent.y())
        elif QMouseEvent.button() == Qt.LeftButton and self.drawing == False:
            self.box_retriever(QMouseEvent.x(), QMouseEvent.y())

        elif QMouseEvent.button() == Qt.MidButton and self.drawing == False:
            self.redraw_existing_box(QMouseEvent.x(), QMouseEvent.y())

        elif QMouseEvent.button() == Qt.LeftButton and self.drawing == True and (self.indicator != 'resize_left'
            and self.indicator != 'resize_right' and self.indicator != 'resize_top' and self.indicator != 'resize_bot'):
            self.draw_bb('start')

        elif QMouseEvent.button() == Qt.LeftButton and self.drawing == True and (self.indicator == 'resize_left'
            or self.indicator == 'resize_right' or self.indicator == 'resize_top' or self.indicator == 'resize_bot'):
            self.resize_edge_lock = self.indicator


    def end_box_draw(self,_pos):
        if self.drawing == True and (self.indicator != 'resize_left'
            and self.indicator != 'resize_right' and self.indicator != 'resize_top' and self.indicator != 'resize_bot'):
            self.draw_bb('end')

        elif self.drawing == True and (self.indicator == 'resize_left'
            or self.indicator == 'resize_right' or self.indicator == 'resize_top' or self.indicator == 'resize_bot'):
            self.resize_edge_lock = None

    # function to continously map mouse movements
    def pointSelection(self,pos):
        self.box_curernt_pos = pos
        #print("box_draw activation position is :", pos)

    def pointSelection_tracking(self,pos):
        if self.indicator == '':
            self.statusBar_1.showMessage("YOU ARE IN DRAWING MODE")
            self.box_curernt_pos = pos
            #print("dynamic position is :", pos)
            self.scene.clear()
            self.scene_img = self.scene.addPixmap(self.img_m)
            self.gv.setScene(self.scene)
            line_x = self.box_curernt_pos.toPoint().x()
            line_y = self.box_curernt_pos.toPoint().y()
            line_x = self.refine_coords(line_x)
            line_y = self.refine_coords(line_y)
            l1 = QGraphicsLineItem(0,line_y,744,line_y)
            l2 = QGraphicsLineItem(line_x,0,line_x,744)
            pen = QPen(Qt.yellow)
            pen.setWidth(2)
            l1.setPen(pen)
            l2.setPen(pen)
            self.scene.addItem(l1)
            self.scene.addItem(l2)

        if self.indicator == 'start':
            self.box_curernt_pos = pos
            #print("dynamic position is :", pos)
            self.scene.clear()
            self.scene_img = self.scene.addPixmap(self.img_m)
            self.gv.setScene(self.scene)
            box_x = self.box_curernt_pos.toPoint().x()
            box_y = self.box_curernt_pos.toPoint().y()
            box_x = self.refine_coords(box_x)
            box_y = self.refine_coords(box_y)
            self.new_box_width = box_x - self.box_start[0]
            self.new_box_height = box_y - self.box_start[1]
            pen = QPen(Qt.blue)
            pen.setWidth(3)
            r = QGraphicsRectItem(self.box_start[0],self.box_start[1],self.new_box_width,self.new_box_height)
            r.setPen(pen)
            self.scene.addItem(r)


        x_m = pos.toPoint().x()
        y_m = pos.toPoint().y()
        x_m = self.refine_coords(x_m)
        y_m = self.refine_coords(y_m)
        if self.drawing == True:
            if (x_m > self.box_left_edge[0] and y_m > self.box_left_edge[1] and x_m < self.box_left_edge[2] and
                y_m < self.box_left_edge[3]):

                QApplication.setOverrideCursor(Qt.CrossCursor)
                self.indicator = 'resize_left'

            elif (x_m > self.box_right_edge[0] and y_m > self.box_right_edge[1]
                and x_m < self.box_right_edge[2] and y_m < self.box_right_edge[3]):

                QApplication.setOverrideCursor(Qt.CrossCursor)
                self.indicator = 'resize_right'

            elif (x_m > self.box_top_edge[0] and y_m > self.box_top_edge[1] and x_m < self.box_top_edge[2]
                and y_m < self.box_top_edge[3]):

                QApplication.setOverrideCursor(Qt.CrossCursor)
                self.indicator = 'resize_top'

            elif (x_m > self.box_bot_edge[0] and y_m > self.box_bot_edge[1] and x_m < self.box_bot_edge[2] and
                y_m < self.box_bot_edge[3]):

                QApplication.setOverrideCursor(Qt.CrossCursor)
                self.indicator = 'resize_bot'

            else:
                QApplication.restoreOverrideCursor()

    def pointResize_tracking(self,pos):
        x_track = pos.toPoint().x()
        y_track = pos.toPoint().y()
        x_track = self.refine_coords(x_track)
        y_track = self.refine_coords(y_track)
        if self.resize_edge_lock == 'resize_left':
            #print("resize dynamic position is :", pos)
            self.scene.clear()
            self.scene_img = self.scene.addPixmap(self.img_m)
            self.gv.setScene(self.scene)
            self.box_start[0] = x_track
            self.new_box_width = self.box_end[0] - self.box_start[0]
            self.define_box_edges()
            pen = QPen(Qt.blue)
            pen.setWidth(3)
            r = QGraphicsRectItem(self.box_start[0],self.box_start[1],self.new_box_width,self.new_box_height)
            r.setPen(pen)
            self.scene.addItem(r)
        elif self.resize_edge_lock == 'resize_right':
            #print("resize dynamic position is :", pos)
            self.scene.clear()
            self.scene_img = self.scene.addPixmap(self.img_m)
            self.gv.setScene(self.scene)
            self.box_end[0] = x_track
            self.new_box_width = self.box_end[0] - self.box_start[0]
            self.define_box_edges()
            pen = QPen(Qt.blue)
            pen.setWidth(3)
            r = QGraphicsRectItem(self.box_start[0],self.box_start[1],self.new_box_width,self.new_box_height)
            r.setPen(pen)
            self.scene.addItem(r)
        elif self.resize_edge_lock == 'resize_top':
            #print("resize dynamic position is :", pos)
            self.scene.clear()
            self.scene_img = self.scene.addPixmap(self.img_m)
            self.gv.setScene(self.scene)
            self.box_start[1] = y_track
            self.new_box_height = self.box_end[1] - self.box_start[1]
            self.define_box_edges()
            pen = QPen(Qt.blue)
            pen.setWidth(3)
            r = QGraphicsRectItem(self.box_start[0],self.box_start[1],self.new_box_width,self.new_box_height)
            r.setPen(pen)
            self.scene.addItem(r)
        elif self.resize_edge_lock == 'resize_bot':
            #print("resize dynamic position is :", pos)
            self.scene.clear()
            self.scene_img = self.scene.addPixmap(self.img_m)
            self.gv.setScene(self.scene)
            self.box_end[1] = y_track
            self.new_box_height = self.box_end[1] - self.box_start[1]
            self.define_box_edges()
            pen = QPen(Qt.blue)
            pen.setWidth(3)
            r = QGraphicsRectItem(self.box_start[0],self.box_start[1],self.new_box_width,self.new_box_height)
            r.setPen(pen)
            self.scene.addItem(r)


    def draw_bb(self,indicator):
        self.indicator = indicator
        if (indicator == 'start') and (self.redraw_box_tracker == False):
            box_x = self.box_curernt_pos.toPoint().x()
            box_y = self.box_curernt_pos.toPoint().y()
            box_x = self.refine_coords(box_x)
            box_y = self.refine_coords(box_y)
            # print("box_x and box_y is {} and {}".format(box_x,box_y))
            self.box_start = [box_x,box_y]
        elif (indicator == 'end') and (self.redraw_box_tracker == False):
            #self.box_end = x,y
            box_x = self.box_curernt_pos.toPoint().x()
            box_y = self.box_curernt_pos.toPoint().y()
            box_x = self.refine_coords(box_x)
            box_y = self.refine_coords(box_y)
            self.box_end = [box_x,box_y]
            self.new_box_width = self.box_end[0] - self.box_start[0]
            self.new_box_height = self.box_end[1] - self.box_start[1]
            pen = QPen(Qt.blue)
            pen.setWidth(3)
            r = QGraphicsRectItem(self.box_start[0],self.box_start[1],self.new_box_width,self.new_box_height)
            #r.setFlag(QGraphicsRectItem.ItemIsMovable, True)
            r.setPen(pen)
            self.scene.addItem(r)

            # define box edges for resizing optionality
            # box_edge[xmin,ymin,xmax,ymax]
            self.define_box_edges()

    def define_box_edges(self):
        box_buffer = self.box_buffer
        self.box_left_edge[0] = self.box_start[0] - int(self.new_box_width*box_buffer)
        self.box_left_edge[1] = self.box_start[1] + int(self.new_box_height/2) - int(self.new_box_height*box_buffer)
        self.box_left_edge[2] = self.box_start[0] + int(self.new_box_width*box_buffer)
        self.box_left_edge[3] = self.box_start[1] + int(self.new_box_height/2) + int(self.new_box_height*box_buffer)

        self.box_right_edge[0] = self.box_end[0] - int(self.new_box_width*box_buffer)
        self.box_right_edge[1] = self.box_end[1] - int(self.new_box_height/2) - int(self.new_box_height*box_buffer)
        self.box_right_edge[2] = self.box_end[0] + int(self.new_box_width*box_buffer)
        self.box_right_edge[3] = self.box_end[1] - int(self.new_box_height/2) + int(self.new_box_height*box_buffer)

        self.box_top_edge[0] = self.box_start[0] + int(self.new_box_width/2) - int(self.new_box_width*box_buffer)
        self.box_top_edge[1] = self.box_start[1] - int(self.new_box_height*box_buffer)
        self.box_top_edge[2] = self.box_start[0] + int(self.new_box_width/2) + int(self.new_box_width*box_buffer)
        self.box_top_edge[3] = self.box_start[1] + int(self.new_box_height*box_buffer)

        self.box_bot_edge[0] = self.box_end[0] - int(self.new_box_width/2) - int(self.new_box_width*box_buffer)
        self.box_bot_edge[1] = self.box_end[1] - int(self.new_box_height*box_buffer)
        self.box_bot_edge[2] = self.box_end[0] - int(self.new_box_width/2) + int(self.new_box_width*box_buffer)
        self.box_bot_edge[3] = self.box_end[1] + int(self.new_box_height*box_buffer)


    def add_box_to_json(self):
        print("ADDING NEW BOX TO REF DICT")
        inv_scale_x = 1/self.scale_x
        inv_scale_y = 1/self.scale_y
        print("inv scale_x and inv_scale_y is: {} and {}".format(inv_scale_x, inv_scale_y))
        print("box_start is:",self.box_start[0])
        print("box_start * scale:", self.box_start[0]*inv_scale_x)

        self.proj['annotations'][self.json_pos]['bbox_info'].append(
            {'box_coordinates':[int(self.box_start[0]*inv_scale_x),int(self.box_start[1]*inv_scale_y),
            int(self.box_end[0]*inv_scale_x),int(self.box_end[1]*inv_scale_y)]})

        box_dict = {
                    'box_status': 1,
                    'box_age': 0,
                    'box_redraw': 0,
                    'box_redraw_dimensions': [],
                    'box_new': 1,
                    'box_new_dimensions': [int(self.box_start[0]*inv_scale_x),
                                            int(self.box_start[1]*inv_scale_y),
                                            int(self.box_end[0]*inv_scale_x),
                                            int(self.box_end[1]*inv_scale_y)]
                }
        self.box_del_tracker[self.curr_proj][str(self.json_pos)].append(box_dict)
        curr_annotation = self.proj['annotations'][self.json_pos]
        self.load_img(curr_annotation)

    def undo_draw(self):
        for i in range(len(self.box_del_tracker[self.curr_proj][str(self.json_pos)])):
            if self.box_del_tracker[self.curr_proj][str(self.json_pos)]['box_new'] == 1:
                del self.box_del_tracker[self.curr_proj][str(self.json_pos)][i]
                #del self.proj['annotations'][self.json_pos]['bbox_info'][i]

        print("removed drawn box from ref dict")
        curr_annotation = self.proj['annotations'][self.json_pos]
        self.load_img(curr_annotation)
        #self.json_loader()

    def redraw_existing_box(self, pos_x, pos_y):
        self.redraw_box_tracker = True
        curr_annotation = self.proj['annotations'][self.json_pos]
        if pos_x > 298 and pos_x < 1042 and pos_y > 42 and pos_y < 786 and self.current_img_object != None:
            return_vals = self.current_img_object.box_index(pos_x,pos_y)
            for i in range(len(return_vals[0])):
                if return_vals[0][i] == -1:
                    # get box coords from existing box
                    new_box_coords = curr_annotation['bbox_info'][i]['box_coordinates']
                    self.box_start[0] = new_box_coords[0]*self.scale_x
                    self.box_start[1] = new_box_coords[1]*self.scale_y
                    self.box_end[0] = new_box_coords[2]*self.scale_x
                    self.box_end[1] = new_box_coords[3]*self.scale_y
                    self.new_box_width = self.box_end[0] - self.box_start[0]
                    self.new_box_height = self.box_end[1] - self.box_start[1]
                    pen = QPen(Qt.blue)
                    pen.setWidth(3)
                    r = QGraphicsRectItem(self.box_start[0],self.box_start[1],self.new_box_width,self.new_box_height)
                    r.setFlag(QGraphicsRectItem.ItemIsMovable, True)
                    r.setPen(pen)
                    self.scene.addItem(r)
                    self.define_box_edges()
                    self.box_index = i #define which box in the current image has been redrawn

                    self.statusBar_1.showMessage("Resize box mode")
                    self.scene.indicator = True
                    self.drawing = True
        else:
            print("you pressed elsewhere")
            pass

    def add_mod_box_to_del_tracker(self):
        inv_scale_x = 1/self.scale_x
        inv_scale_y = 1/self.scale_y
        print("inv scale_x and inv_scale_y is: {} and {}".format(inv_scale_x, inv_scale_y))
        print("box_start is:",self.box_start[0])
        print("box_start * scale:", self.box_start[0]*inv_scale_x)
        new_box_coords = [int(self.box_start[0]*inv_scale_x),
                                int(self.box_start[1]*inv_scale_y),
                                int(self.box_end[0]*inv_scale_x), int(self.box_end[1]*inv_scale_y)]
        del self.current_img_object
        del self.img_m
        self.gv.items().clear
        del self.scene_img
        self.scene.clear()
        self.box_del_tracker[self.curr_proj][str(self.json_pos)][self.box_index]['box_redraw'] = 1
        self.box_del_tracker[self.curr_proj][str(self.json_pos)][self.box_index]['box_redraw_dimensions'] = new_box_coords
        curr_annotation = self.proj['annotations'][self.json_pos]
        self.load_img(curr_annotation)

    # function which finds box to delete and saves that info in self.box_delete_tracker
    def box_deleter(self, pos_x, pos_y):
        if pos_x > 298 and pos_x < 1042 and pos_y > 42 and pos_y < 786 and self.current_img_object != None:
            return_vals = self.current_img_object.box_index(pos_x,pos_y)
            for i in range(len(return_vals[0])):
                if return_vals[0][i] == -1:
                    self.box_del_tracker[self.curr_proj][str(self.json_pos)][i]['box_status'] = 0
            curr_annotation = self.proj['annotations'][self.json_pos]
            #reloader = 'reloader'
            self.load_img(curr_annotation)
        else:
            print("you pressed elsewhere")
            pass

    # function which finds box to retrieve and saves that info in self.box_delete_tracker
    # also displays box attributes
    def box_retriever(self, pos_x, pos_y):
        print("entered box_retriever")
        if pos_x > 298 and pos_x < 1042 and pos_y > 42 and pos_y < 786 and self.current_img_object != None:
            return_vals = self.current_img_object.box_index(pos_x,pos_y)
            print("return vals is :", return_vals)
            for i in range(len(return_vals[0])):
                if return_vals[0][i] == -1:
                    self.box_del_tracker[self.curr_proj][str(self.json_pos)][i]['box_status'] = 1
                    self.selected_box_index = i
            curr_annotation = self.proj['annotations'][self.json_pos]
            temp_box_atts = json.dumps(return_vals[1], indent=2)
            temp_box_atts = temp_box_atts.strip("{}")
            self.box_atts.setText(temp_box_atts)
            #reloader = 'reloader'
            self.load_img(curr_annotation)

        else:
            print("you pressed elsewhere")
            pass

    def del_img(self):
        for i in range(len(self.box_del_tracker[self.curr_proj][str(self.json_pos)])):
            self.box_del_tracker[self.curr_proj][str(self.json_pos)][i]['box_status'] = 0
        curr_annotation = self.proj['annotations'][self.json_pos]
        #reloader = 'reloader'
        self.load_img(curr_annotation)

    def save_img_ref(self):
        img_obj_values = self.current_img_object.img_save_for_ref()
        img_to_save = img_obj_values[0]
        proj_name = img_obj_values[1]
        img_name = img_obj_values[2]
        print("Saving Image: ", img_name)

        if os.path.exists(os.path.join(self.fname, "ref_images", proj_name)):
            cv2.imwrite((os.path.join(self.fname, "ref_images", proj_name, img_name)),img_to_save)

        else:
            os.makedirs(os.path.join(self.fname,"ref_images", proj_name))
            cv2.imwrite((os.path.join(self.fname, "ref_images", proj_name, img_name)),img_to_save)
        self.statusBar_1.showMessage("Saved image for future reference")


    # function to detect keyboard key press
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Right or event.key() == Qt.Key_D:
            self.json_next_img()
        elif event.key() == Qt.Key_Left or event.key() == Qt.Key_A:
            self.json_prev_img()
        elif event.key() == Qt.Key_F:
            if self.drawing == True:
                self.drawing = False
                self.scene.indicator = False

                self.box_start[0],self.box_start[1] = 0,0
                self.box_end[0],self.box_end[1] = 0,0
                self.new_box_width, self.new_box_height = None, None
                self.box_left_edge[0], self.box_left_edge[1], self.box_left_edge[2], self.box_left_edge[3] = 0,0,0,0
                self.box_right_edge[0], self.box_right_edge[1], self.box_right_edge[2], self.box_right_edge[3] = 0,0,0,0
                self.box_top_edge[0], self.box_top_edge[1], self.box_top_edge[2], self.box_top_edge[3] = 0,0,0,0
                self.box_bot_edge[0], self.box_bot_edge[1], self.box_bot_edge[2], self.box_bot_edge[3] = 0,0,0,0
                self.resize_edge_lock = None
                self.redraw_box_tracker = False

                QApplication.setOverrideCursor(Qt.ArrowCursor)
                self.statusBar_1.showMessage("You have exited drawing mode")
            else:
                self.indicator = ''
                self.drawing = True
                self.scene.indicator = True
        elif event.key() == Qt.Key_Space:
            if self.redraw_box_tracker == False:
                self.add_box_to_json()
            else:
                self.add_mod_box_to_del_tracker()
            self.drawing = False
            self.indicator = None
            self.scene.indicator = False
            self.box_start[0],self.box_start[1] = 0,0
            self.box_end[0],self.box_end[1] = 0,0
            self.new_box_width, self.new_box_height = None, None
            self.box_left_edge[0], self.box_left_edge[1], self.box_left_edge[2], self.box_left_edge[3] = 0,0,0,0
            self.box_right_edge[0], self.box_right_edge[1], self.box_right_edge[2], self.box_right_edge[3] = 0,0,0,0
            self.box_top_edge[0], self.box_top_edge[1], self.box_top_edge[2], self.box_top_edge[3] = 0,0,0,0
            self.box_bot_edge[0], self.box_bot_edge[1], self.box_bot_edge[2], self.box_bot_edge[3] = 0,0,0,0
            self.resize_edge_lock = None
            QApplication.setOverrideCursor(Qt.ArrowCursor)
            self.statusBar_1.showMessage("You have exited drawing mode")
            self.redraw_box_tracker = False
            self.save_temp()
        elif event.key() == Qt.Key_1:
            self.save_age_group(1)
        elif event.key() == Qt.Key_2:
            self.save_age_group(2)
        elif event.key() == Qt.Key_3:
            self.save_age_group(3)
        elif event.key() == Qt.Key_4:
            self.save_age_group(4)
        elif event.key() == Qt.Key_5:
            self.save_age_group(5)

    # function to save age into ref dict
    def save_age_group(self, age_group):
        if self.selected_box_index is not None:
            self.box_del_tracker[self.curr_proj][str(self.json_pos)][self.selected_box_index]['box_age'] = age_group
            curr_annotation = self.proj['annotations'][self.json_pos]
            self.load_img(curr_annotation)
        else:
            print("no box selected")
    
    # function to increment value of set_proj_track
    def next_proj_set(self):
        print("trying to go to next project")
        try:
            self.proj_set_track += 1
            self.projec_assign(self.all_jsons_list,self.proj_set_track)
        except IndexError:
            self.proj_set_track -= 1

    # function to decreemtn value of set_proj_track
    def prev_proj_set(self):
        try:
            self.proj_set_track -= 1
            self.projec_assign(self.all_jsons_list,self.proj_set_track)
        except IndexError:
            self.proj_set_track += 1

    # function to save curr proj before closing
    def closeEvent(self, event):
        print("closing Tool")
        self.save_temp()
        event.accept()



# Initialize The App
app = QApplication(sys.argv)
'''
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
'''
UIWindow = main()
app.exec_()
