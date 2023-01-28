# Brainstem Annotation Tool

A basic UI which can be used to filter images and simultaneously edit a json file

## Setup

run python3 -m pip install -r requirements.txt

# Usage

Clone the repo
run 'python3 test_3.py' to start the ui

- Choose the folder containing the jsons using the 'Open Folder' button
- Choose the folder containing images (if necessary) using 'Image Path' button

## The required folder structure is:
```
march_jsons/
├── annotation_json
├── annotation_json_filtered
└── images
```

Note: preferably put all images into the folder as shown above, as they will be automatically loaded into the UI

# UI User Instructions

## Basic Image Options

Mouse Right Click = Retrieve box + show box attributes
Mouse Left Click = Delete box
'D' = Next Image
'A' = Previous Image

## Drawing Boxes

Press 'F' to trigger drawing mode

Inside drawing mode:
- Left click to start drawing boxes
- Right click to end box draw
- Hover over box edges (center of edges) to see cursor change into resize mode
- Left click to start resizing that edge
- Move mouse and then right click to finalize new edge position
- Press T to exit drawing mode and then press 'T' again to enter drawing mode and draw new box
- Or after box has been drawn, press Spacebar to save box into json
- Immediately after above step, if box is not required, press the "Undo Box Draw" button to remove the box
- IMPORTANT: If the box touched by any other click, then the "Undo Box Draw" button will not work
- If a drawn box gets removed by left_click, it will be masked, so be careful to only remove the box using the button

Note. The newly drawn box gets added to the annotation_json folder (original json is edited)

## Final Save

- After project is done, press "Save to temp folder" and then "Save to filtered_json folder"
- The above step saves filterd_json, i.e. it removes full image if no box present in image

IMPORTANT NOTE
In extension to the last point above, if a box has one good cotton and one bad cotton, remove only the bad cotton. This is because the json will hold only the position of the both boxes, but the ref_dict will specify which box is kept and which box is to be masked out

# After saving filtered_json

Run the mask_images script by giving the image folder, json_path and ref_dict path \
This script will mask out all unwanted boxes and give you a final json which you can use for training

To get trial_data use this link:
https://drive.google.com/file/d/1iIM8yDZvRqBWN_E7cwPG2rgxy2iHWZxM/view?usp=sharing