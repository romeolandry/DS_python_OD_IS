import sys
import os

CUR_DIR = os.path.abspath(os.curdir)

# INPUT
CSI_INPUT = "/dev/video0" # Path to CSI- Camera eg. rasbery
CAMERA_WIDTH=720
CAMERA_HEIGHT=720
BATCH_SIZE=1
BATCH_PUSH_TIMEOUT= 4000000 # Default is 4000000 

# OUTPUT RTSP Configuration
CODEC = "H264" # RTSP Streaming Codec H264/H265
BITRATE = 4000000 #  Set the encoding bitrate. Type INT
RTSP_PORT = 8554
UDP_PORT_SINK=5400

# MODEL CONFIGURATION
AVAILABLE_TRT_MODEL = ['trt_resnet10','custom']
AVAILABLE_TRTIS_MODEL = ['trtis_yolov3', 'trtis_ssd_inceptionv3', 'custom']