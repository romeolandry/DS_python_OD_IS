import argparse
import sys
from python_app import deepstream_od_resnet10_4_classes as ds_od_restnet 
import run_config as config



parser = argparse.ArgumentParser(description='RTSP Output Sample Application Help ')
## choose between TRT and Triton Inference Server
parser.add_argument("--trtis", default=False, action="store_true", help="Activate triton inference server")
## Model configuration
parser.add_argument("--model", choices= list(set(config.AVAILABLE_TRT_MODEL + config.AVAILABLE_TRTIS_MODEL)),
                        help="choose which model you wont to inference; custom you use your own model",
                        default="trt_resnet10")
parser.add_argument("-i", "--input", help="path to device CIS-device", default= config.CSI_INPUT)
parser.add_argument("-c", "--codec", help="RTSP Streaming Codec H264/H265" , default=config.CODEC, choices=['H264','H265'])
parser.add_argument("-b", "--bitrate", help="Set the encoding bitrate ", default=config.BITRATE, type=int)


if __name__ == '__main__':
    args = parser.parse_args()
    if(args.trtis):
        print("__________________Use Triton server for Inference__________________")
    else:
        print("____________________Use TensorRT for inference______________________")
    print(args.model)
    
    ds_od_restnet.main()