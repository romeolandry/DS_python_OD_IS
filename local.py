import argparse
import sys
import os
from local_script import ssd_locale
from python_app import deepstream_od_resnet10_4_classes as ds_od_restnet
import configurations.configuration as config

# Clear the GStreamer cache if pipeline creation 
#print("\n")
#os.system('rm ~/.cache/gstreamer-1.0/*')
#print("\n")

parser = argparse.ArgumentParser(description='RTSP Output Sample Application Help ')
## Model configuration
parser.add_argument("--model",
                    choices= list(set(config.AVAILABLE_TRT_MODEL + config.AVAILABLE_TRITIS_MODEL)),
                    help="choose which model you wont to inference; custom you use your own model",
                    required=True
                    )

parser.add_argument("--output_dir",
                    default= config.OUTPUT_DIR,
                    help="choose which where the viode will save"
                    )
parser.add_argument("--bitrate",
                    default= config.BITRATE,
                    help="choose which where the viode will save"
                    )

def main(args):

    output_dir = args.output_dir
    bitrate = args.bitrate
    print(" Use Triton server for Inference\n")

    if(args.model not in config.AVAILABLE_TRITIS_MODEL):
        print("\n Not Availoable model to set custom model please")
        print(f"The availble model are {config.AVAILABLE_TRITIS_MODEL}.")
        sys.stderr.write("choose custom to set your custom madel \n\n")

    ssd_locale.main(output_dir,bitrate)

if __name__ == '__main__':
    args = parser.parse_args()
    main(args)
        