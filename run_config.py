import sys
import os

CUR_DIR = os.path.abspath(os.curdir)

# INPUT
CSI_INPUT = "/dev/video0" # Path to CSI- Camera eg. rasbery
CAMERA_WIDTH=1920
CAMERA_HEIGHT=1080
BATCH_SIZE=1
BATCH_PUSH_TIMEOUT= 4000000 # Default is 4000000

# OUTPUT RTSP Configuration
CODEC = "H264" # RTSP Streaming Codec H264/H265
BITRATE = 4000000 #  Set the encoding bitrate. Type INT
RTSP_PORT = 8554
UDP_PORT_SINK=5400

# MODEL CONFIGURATION
AVAILABLE_TRT_MODEL = ['resnet10','custom']
AVAILABLE_TRITIS_MODEL = ['yolov3', 'ssd_inceptionv2', 'custom']

# SSD Model configurtion

## tensorflow
CONFIG_SSD_INCEPTIONV2_COCO = "configurations/dstest_ssd_nopostprocess.txt"
UNTRACKED_OBJECT_ID = 0xffffffffffffffff
IMAGE_HEIGHT = 1080
IMAGE_WIDTH = 1920
MIN_BOX_WIDTH = 32
MIN_BOX_HEIGHT = 32
TOP_K = 20
IOU_THRESHOLD = 0.3

# Dataset
CLASS_NB = 91
ACCURACY_ALL_CLASS = 0.5
COCO_LABEL_PATH = "Models/tritis_model/ssd_inception_v2_coco_2018_01_28/labels.txt"