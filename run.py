import argparse
import sys
import os
from python_app import deepstream_ssd_parser_rasbery_to_rtsp as ds_tf_ssd
from python_app import deepstream_od_resnet10_4_classes as ds_od_restnet
import configurations.configuration as config

# Clear the GStreamer cache if pipeline creation 
print("\n")
os.system('rm ~/.cache/gstreamer-1.0/*')
print("\n")

parser = argparse.ArgumentParser(description='RTSP Output Sample Application Help ')
## choose between TRT and Triton Inference Server
parser.add_argument("--tritis", default=False, action="store_true", help="Activate triton inference server")
## Model configuration
parser.add_argument("--model", choices= list(set(config.AVAILABLE_TRT_MODEL + config.AVAILABLE_TRITIS_MODEL)),
                        help="choose which model you wont to inference; custom you use your own model",
                        required=True)
parser.add_argument("-i", "--input", help="path to device CIS-device", default= config.CSI_INPUT)
parser.add_argument("-c", "--codec", help="RTSP Streaming Codec H264/H265" , default=config.CODEC, choices=['H264','H265'])
parser.add_argument("-b", "--bitrate", help="Set the encoding bitrate ", default=config.BITRATE, type=int)


if __name__ == '__main__':
    args = parser.parse_args()
    if(args.tritis):

        print("###################### __________________Use Triton server for Inference__________________#############################\n")
        if(args.model not in config.AVAILABLE_TRITIS_MODEL):
            print("\n Not Availoable model to set custom model please")
            print(f"The availble model are {config.AVAILABLE_TRITIS_MODEL}.")
            print("choose custom to set your custom madel \n\n")
        else:
            if (args.model != "custom"):
                print(f"Running triton Inferency server with {args.model} model \n")
                ds_tf_ssd.main(args.model)
                #deepstream_ssd_parser_rasbery_to_rtsp.main(args.model)        
    else:
        print("\n ###################### ____________________Use TensorRT for inference______________________#########################")

        if(args.model not in config.AVAILABLE_TRT_MODEL):
            print("\n Not Availoable model to set custom model please")
            print(f"The availble model are {config.AVAILABLE_TRT_MODEL}")
            print("choose custom to set your custom madel \n\n")
        else:
            if (args.model != "custom"):
                print(f"Running TRT with {args.model} model \n")   
                ds_od_restnet.main(args.model)