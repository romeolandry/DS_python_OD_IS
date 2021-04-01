import argparse
import sys
import os
from python_app import ds_meta_rasp_rtsp
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
parser.add_argument("--local", "-l",
                    default=False,
                    action="store_true",
                    help="True if won to use jetson nano screen."
                    )

parser.add_argument("--ip", "-i",
                    default=config.BROKER_CONF['IP'],
                    help="Ip-Address for kafka"
                    )

parser.add_argument("--port","-p",
                    default="9092",
                    help="Kafka Port")

parser.add_argument("--topic",
                    default=config.BROKER_CONF['topic'],
                    help="give kafka topic"
                    )

def main(args):

    if not args.local:

        if(args.ip):
            config.BROKER_CONF['IP']= args.ip

        if(args.port):
            config.BROKER_CONF['port']= args.port

        if(args.topic):
            config.BROKER_CONF['topic']= args.topic

    print(" Use Triton server for Inference\n")

    if(args.model not in config.AVAILABLE_TRITIS_MODEL):
        print("\n Not Availoable model to set custom model please")
        print(f"The availble model are {config.AVAILABLE_TRITIS_MODEL}.")
        sys.stderr.write("choose custom to set your custom madel \n\n")

    if not args.local:
        ds_meta_rasp_rtsp.tf_ssd_model(args.model)
    else:
        ds_meta_rasp_rtsp.tf_ssd_model_local(args.model)

if __name__ == '__main__':
    args = parser.parse_args()
    main(args)
        