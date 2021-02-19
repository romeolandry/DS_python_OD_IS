"""
    The file content function to build the part of pipeline concerned sink
    sink: is the contening ouput type and setting of the pipeline

"""
import sys
import io
import os 

sys.path.append(os.path.abspath(os.curdir))



import gi
gi.require_version("Gst","1.0")

from gi.repository import Gst, GstRtspServer
from python_app.pipeline_main import make_elm_or_print_err

from utils.common.is_aarch_64 import is_aarch64

# On Jetson, there is a problem with the encoder failing to initialize
# due to limitation on TLS usage. To work around this, preload libgomp.
# Add a reminder here in case the user forgets.
preload_reminder = "If the following error is encountered:\n" + \
                    "/usr/lib/aarch64-linux-gnu/libgomp.so.1: cannot allocate memory in static TLS block\n" + \
                    "Preload the offending library:\n" + \
                    "export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1\n"


def rtsp_sink(codec,bitrate,dict_udp,preload_reminder=preload_reminder):

    print("Creating an filter for RTSP ")

    caps_rtsp = Gst.ElementFactory.make("capsfilter","filter")
    if not caps_rtsp:        
        sys.stderr.write("Unable to create rtsp filter \n")
    # setting property
    caps_rtsp.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), format=I420"))

    print("setting encoder and rtppay for rtsp")

    if codec == "H264":
        print("Creating H264 Encoder and rtppay")
        encoder_rtsp = Gst.ElementFactory.make("nvv4l2h264enc","encoder")
        if not encoder_rtsp:        
            sys.stderr.write("Unable to create encoder \n")

        rtppay = Gst.ElementFactory.make("rtph264pay","rtppay")
        if not rtppay:
            sys.stderr.write("Unable to create rtppay \n")

    elif codec == "H265":       
        print("Creating H265 Encoder and rtppay")
        encoder_rtsp = Gst.ElementFactory.make("nvv4l2h265enc","encoder") 
        if not encoder_rtsp :
            sys.stderr.write("Unable to create encoder \n")
        
        rtppay = Gst.ElementFactory.make("rtph265pay","rtppay")
        if not rtppay :
            sys.stderr.write("Unable to create rtppay \n")
    
    encoder_rtsp.set_property('bitrate', bitrate)

    # Make the UDP sink for RTSP
    print("creadte an UDP sink for rtsp")
    udp_sink = Gst.ElementFactory.make("udpsink","udpsink")
    if not udp_sink :
        sys.stderr.write("Unable to create udpsink for rtsp \n")
    
    udp_sink.set_property('host', dict_udp['host'] )
    udp_sink.set_property('port', dict_udp['port'])
    udp_sink.set_property('async', dict_udp['async'])
    udp_sink.set_property('sync', dict_udp['sync'])
    
    if is_aarch64():
        encoder_rtsp.set_property('preset-level', 1)
        encoder_rtsp.set_property('insert-sps-pps', 1)
        encoder_rtsp.set_property('bufapi-version', 1)

    return [caps_rtsp,encoder_rtsp,rtppay,udp_sink]


def local_display():
    transform = None
    if is_aarch64():
        transform = make_elm_or_print_err("nvegltransform",
                                          "nvegl-transform",
                                          "transform element for display")
    print("Create EGLSink \n")
    sink = make_elm_or_print_err("nveglglessink",
                                 "nvvideo-renderer",
                                 "Display output")
    return transform, sink

def local_output_file(bitrate,output_file, preload_reminder=preload_reminder):
    
    nvvidconv2 = make_elm_or_print_err("nvvideoconvert", "convertor_file_output", "Converter 2 (nvvidconv2)")

    capsfilter = make_elm_or_print_err("capsfilter", "capsfilter", "capsfilter")

    caps = Gst.Caps.from_string("video/x-raw, format=I420")
    capsfilter.set_property("caps", caps)

    encoder = make_elm_or_print_err("avenc_mpeg4", "encoder", "Encoder", preload_reminder)
    encoder.set_property("bitrate",bitrate)

    codeparser = make_elm_or_print_err("mpeg4videoparse", "mpeg4-parser", 'Code Parser')

    container = make_elm_or_print_err("qtmux", "qtmux", "Container")

    sink = make_elm_or_print_err("filesink", "filesink", "Sink")

    sink.set_property("location", output_file)
    sink.set_property("sync",0)
    sink.set_property("async",0)


    return (nvvidconv2,capsfilter,encoder,codeparser,container,sink)