import sys
import os

CUR_DIR = os.path.abspath(os.curdir)

# INPUT
CSI_INPUT = "/dev/video0"  # Path to CSI- Camera eg. rasbery
CAMERA_WIDTH = 1920 # 1920
CAMERA_HEIGHT = 1080  #1080
BATCH_SIZE = 1
BATCH_PUSH_TIMEOUT = 4000000  # Default is 4000000

# OUTPUT RTSP Configuration
CODEC = "H264"  # RTSP Streaming Codec H264/H265
BITRATE = 4000000  # Set the encoding bitrate. Type INT
RTSP_PORT = 8554

UDP_CONF = {
    'host': '224.224.255.255',
    'port': 5400,
    'async': False,
    'sync': 1
}


# MODEL CONFIGURATION
AVAILABLE_TRT_MODEL = ['resnet10', 'custom']
AVAILABLE_TRITIS_MODEL = ['yolov3', 'ssd_inceptionv2', 'mask']

# SSD Model configurtion

# tensorflow
Model_CONF = {
    'config_file': "configurations/dstest_ssd_nopostprocess.txt",
    'untracted_object_id': 0xffffffffffffffff,
    'img_height': 750,
    'img_width': 750,
    'min_box_width': 32,
    'min_box_height': 32,
    'top_k': 20,
    'iou_threshold': 0.3
}

# Dataset
DATA_CONF = {
    'nb_classes': 91,
    'accuracy_all_class': 0.5,
    'patht_to_label': "Models/tritis_model/ssd_inception_v2_coco_2018_01_28/labels.txt"
}

# msg Broker configuration

BROKER_CONF = {
    'IP':"192.168.0.5",
    'port':'9092',
    'topic':'jetson-topic',
    'schema_type' : 0,
    'msconv_cfg_file': "configurations/dstest4_msgconv_config.txt",
    'proto_lib': '/opt/nvidia/deepstream/deepstream-5.0/lib/libnvds_kafka_proto.so'
}

MAX_TIME_STAMP_LEN=32
PGIE_CLASS_ID_VEHICLE = 0
PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 2
PGIE_CLASS_ID_ROADSIGN = 3

OUTPUT_DIR = "OUT_PUT"