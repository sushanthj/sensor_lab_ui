from multiprocessing import connection
import numpy as np
import cv2
import math
import os
from copy import deepcopy

## Selective Dataset Review Version

AGE_GROUP_DICT = {1:"Superior_Colliculus", 2:"Inferior_Colliculus", 3:"Red_Nucleus", 4:"Inferior_Olive", 5:"Corticospinal_Tract"}

class Images:
    def __init__(self, img_selected, ann, box_dict):
        self.box_dict = deepcopy(box_dict)
        self.img = cv2.imread(img_selected, 1)
        self.img_width = 744
        self.img_height = 744
        self.resize_tracker = False
        self.annotation = deepcopy(ann)
        self.resized_img = None

        # tag to check if we have a drawn box in an image
        self.drawn_box = False
        self.drawn_box_index = []

        self.img_name = img_selected.split('/images/')[1].split("/")[1]
        self.proj_name = img_selected.split('/images/')[1].split("/")[0]
        #self.img_format = img.split('\\')[-1].split(".")[1]

        self.left, self.right, self.top, self.bottom = None, None, None, None

    def add_bbox(self):
        box_img = self.img
        box_thickness = 2 #* scale_to_draw_box
        text_thickness = 2 #* scale_to_draw_box
        box_count = 0
        image_skip = 0

        if box_img is not None:
            if self.img.shape[0] == 744 and self.img.shape[1] == 744:
                self.resized_img = box_img
            else:
                self.resized_img = cv2.resize(box_img, (self.img_width, self.img_height))
                self.resize_tracker = True
        else:
            self.resized_img = np.zeros((744,744,3), np.uint8) # create an empty image
            self.resized_img = cv2.putText(self.resized_img, "Image Not Found",(10,300),
                                                            cv2.FONT_HERSHEY_SIMPLEX, 2, 
                                                            (255,255,255), text_thickness)
            return self.resized_img, 1,1,1
        
        scale_factor_x = 744/self.img.shape[1]
        scale_factor_y = 744/self.img.shape[0]
        #scale_to_draw_box = math.ceil(self.img.shape[1]/744)
        
        for i in range(len(self.box_dict)):
            bbox_coordinates, box_skip_status = self.get_active_box_coordinates(i)
            if box_skip_status == 'box_skipped':
                 continue
            elif box_skip_status == 'user_deselected':
                box_count += 1
            elif bbox_coordinates is not None:
                box_count += 1
                xmin, ymin, xmax, ymax = bbox_coordinates
                #scale down coords
                xmin2 = math.floor(xmin*scale_factor_x)
                ymin2 = math.floor(ymin*scale_factor_y)
                xmax2 = math.ceil(xmax*scale_factor_x)
                ymax2 = math.ceil(ymax*scale_factor_y)
                self.resized_img = cv2.rectangle(self.resized_img, (xmin2,ymin2), (xmax2,ymax2),(75,61,219), box_thickness)
                if self.box_dict[i]['box_age'] != 0:
                    text_to_draw = AGE_GROUP_DICT[self.box_dict[i]['box_age']]
                    self.resized_img = cv2.putText(self.resized_img, text_to_draw, (xmin2+2, ymin2-5),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,0,0), text_thickness)
        
        if box_count > 0:
            image_skip = 1
        return self.resized_img, image_skip, scale_factor_x, scale_factor_y

        ''' If you want to skip certain types of images in the future
        if 1 not in self.box_del_list and 2 not in self.box_del_list:
            # copy paste the above code block
            return self.resized_img, 1, scale_factor_x, scale_factor_y
        else:
            if self.img.shape[0] == 744 and self.img.shape[1] == 744:
                self.resized_img = self.img
            else:
                self.resized_img = cv2.resize(self.img, (self.img_width, self.img_height))
            return self.resized_img, 0, scale_factor_x, scale_factor_y
         '''

    def get_active_box_coordinates(self, i):
        box_skip = 'not_skipped'
        if (self.box_dict[i]['box_redraw'] == 1) and (self.box_dict[i]['box_status'] == 1):
            bbox_coordinates = self.box_dict[i]['box_redraw_dimensions']
        elif (self.box_dict[i]['box_redraw'] == 1) and (self.box_dict[i]['box_status'] == 0):
            bbox_coordinates = None
            box_skip = 'user_deselected'
        elif (self.box_dict[i]['box_new'] == 1) and (self.box_dict[i]['box_status'] == 1):
            bbox_coordinates = self.box_dict[i]['box_new_dimensions']
        elif (self.box_dict[i]['box_new'] == 1) and (self.box_dict[i]['box_status'] == 0):
            bbox_coordinates = None
            box_skip = 'user_deselected'
        elif self.box_dict[i]['box_status'] == 1:
            bbox_coordinates = self.annotation["bbox_info"][i]['box_coordinates']
            if len(bbox_coordinates) == 0:
                bbox_coordinates = None
                box_skip = 'box_skipped'
        elif (self.box_dict[i]['box_status'] == 0) and (
                len(self.annotation["bbox_info"][i]['box_coordinates']) != 0):
                bbox_coordinates = self.annotation["bbox_info"][i]['box_coordinates']
                box_skip = 'user_deselected'
        else:
            bbox_coordinates = None
        return bbox_coordinates, box_skip
    
    def get_all_box_coordinates(self, i):
        bbox_coordinates = None
        if self.box_dict[i]['box_redraw'] == 1:
            bbox_coordinates = self.box_dict[i]['box_redraw_dimensions']
        elif self.box_dict[i]['box_new'] == 1:
            bbox_coordinates = self.box_dict[i]['box_new_dimensions']
        else:
            bbox_coordinates = self.annotation["bbox_info"][i]['box_coordinates']
            if len(bbox_coordinates) == 0:
                bbox_coordinates = None
        return bbox_coordinates

    def box_index(self, pos_x, pos_y):
        # box_select tracks which box has been chosen
        box_select = []
        box_atts = None
        for i in range(len(self.box_dict)):
            box_select.append(0)

        #according to the QMainWindow layout, the image is offset from left by 298 and from top by 42
        #therefore, make adjustmets to pos_x and pos_y to convert to image frame of reference
        pos_x2 = pos_x - 298
        pos_y2 = pos_y - 42
        # if image has been rescaled down to 744x744
        if self.resize_tracker:
            #scaling assuming img width = height
            scale_factor_x = 744/self.img.shape[1]
            scale_factor_y = 744/self.img.shape[0]
            #iterating through boxes to see if we have clicked within the area of any particular box
            for i in range(len(self.box_dict)):
                bbox_coordinates = self.get_all_box_coordinates(i)
                if bbox_coordinates is not None:    
                    xmin, ymin, xmax, ymax = bbox_coordinates
                    #scale down coords
                    xmin2 = int(xmin*scale_factor_x)
                    ymin2 = int(ymin*scale_factor_y)
                    xmax2 = int(xmax*scale_factor_x)
                    ymax2 = int(ymax*scale_factor_y)

                    #compare with click coords to see if we fall within area
                    if (pos_x2 > xmin2 and pos_x2 < xmax2 and pos_y2 > ymin2 and pos_y2 < ymax2):
                        box_select[i] = -1
                        try:
                            box_atts = self.annotation["bbox_info"][i].get('box_attr', '')
                        except IndexError:
                            box_atts = ''
                    else:
                        pass

        # if image has not been rescaled
        else:
            #iterating through boxes to see if we have clicked within the area of any particular box
            for i in range(len(self.box_dict)):
                bbox_coordinates = self.get_all_box_coordinates(i)
                if bbox_coordinates is not None:    
                    xmin, ymin, xmax, ymax = bbox_coordinates
                    #compare with click coords to see if we fall within area
                    if (pos_x2 > xmin and pos_x2 < xmax and pos_y2 > ymin and pos_y2 < ymax):
                        box_select[i] = -1
                        try:
                            box_atts = self.annotation["bbox_info"][i].get('box_attr', '')
                        except IndexError:
                            box_atts = ''
                    else:
                        pass

        return (box_select,box_atts)

    def img_save_for_ref(self):
        box_img = None
        for i in range(len(self.box_dict)):
            bbox_coordinates = self.annotation["bbox_info"][i]['box_coordinates']
            xmin, ymin, xmax, ymax = bbox_coordinates
            box_img = cv2.rectangle(self.img, (xmin,ymin), (xmax,ymax),(36,255,120), 3)

        if self.img.shape[0] == 744 and self.img.shape[1] == 744:
            resized_img = box_img
        else:
            resized_img = cv2.resize(box_img, (self.img_width, self.img_height))

        return (resized_img, self.proj_name, self.img_name)
