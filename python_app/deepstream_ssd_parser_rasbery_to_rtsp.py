#!/usr/bin/env python3

################################################################################
# Copyright (c) 2020, NVIDIA CORPORATION. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
################################################################################

""" Example of deepstream using SSD neural network and parsing SSD's outputs. """

import sys
import io
import os

sys.path.append(os.path.abspath(os.curdir))

import run_config as config


import gi
gi.require_version("Gst", "1.0")

from gi.repository import GObject, Gst, GstRtspServer

from utils.common.is_aarch_64 import is_aarch64
from utils.common.bus_call import bus_call
from utils.trtis.ssd_parser import nvds_infer_parse_custom_tf_ssd, DetectionParam, NmsParam, BoxSizeParam
import pyds




CLASS_NB = 91
ACCURACY_ALL_CLASS = 0.5
UNTRACKED_OBJECT_ID = 0xffffffffffffffff
IMAGE_HEIGHT = 1080
IMAGE_WIDTH = 1920
MIN_BOX_WIDTH = 32
MIN_BOX_HEIGHT = 32
TOP_K = 20
IOU_THRESHOLD = 0.3
##OUTPUT_VIDEO_NAME = "./streams/out.mp4"


def get_label_names_from_file(filepath):
    """ Read a label file and convert it to string list """
    f = io.open(filepath, "r")
    labels = f.readlines()
    labels = [elm[:-1] for elm in labels]
    f.close()
    return labels


def make_elm_or_print_err(factoryname, name, printedname, detail=""):
    """ Creates an element with Gst Element Factory make.
        Return the element  if successfully created, otherwise print
        to stderr and return None.
    """
    print("Creating", printedname)
    elm = Gst.ElementFactory.make(factoryname, name)
    if not elm:
        sys.stderr.write("Unable to create " + printedname + " \n")
        if detail:
            sys.stderr.write(detail)
    return elm


def osd_sink_pad_buffer_probe(pad, info, u_data):
    frame_number = 0
    # Intiallizing object counter with 0.
    obj_counter = dict(enumerate([0] * CLASS_NB))
    num_rects = 0

    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer ")
        return

    # Retrieve batch metadata from the gst_buffer
    # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
    # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            # Note that l_frame.data needs a cast to pyds.NvDsFrameMeta
            # The casting also keeps ownership of the underlying memory
            # in the C code, so the Python garbage collector will leave
            # it alone.
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        frame_number = frame_meta.frame_num
        num_rects = frame_meta.num_obj_meta
        l_obj = frame_meta.obj_meta_list
        while l_obj is not None:
            try:
                # Casting l_obj.data to pyds.NvDsObjectMeta
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break
            obj_counter[obj_meta.class_id] += 1
            try:
                l_obj = l_obj.next
            except StopIteration:
                break

        # Acquiring a display meta object. The memory ownership remains in
        # the C code so downstream plugins can still access it. Otherwise
        # the garbage collector will claim it when this probe function exits.
        display_meta = pyds.nvds_acquire_display_meta_from_pool(batch_meta)
        display_meta.num_labels = 1
        py_nvosd_text_params = display_meta.text_params[0]
        # Setting display text to be shown on screen
        # Note that the pyds module allocates a buffer for the string, and the
        # memory will not be claimed by the garbage collector.
        # Reading the display_text field here will return the C address of the
        # allocated string. Use pyds.get_string() to get the string content.
        id_dict = {
            val: index
            for index, val in enumerate(get_label_names_from_file("Models/trtis_model/ssd_inception_v2_coco_2018_01_28/labels.txt"))
        }
        disp_string = "Frame Number={} Number of Objects={} Vehicle_count={} Person_count={}"
        py_nvosd_text_params.display_text = disp_string.format(
            frame_number,
            num_rects,
            obj_counter[id_dict["car"]],
            obj_counter[id_dict["person"]],
        )

        # Now set the offsets where the string should appear
        py_nvosd_text_params.x_offset = 10
        py_nvosd_text_params.y_offset = 12

        # Font , font-color and font-size
        py_nvosd_text_params.font_params.font_name = "Serif"
        py_nvosd_text_params.font_params.font_size = 10
        # set(red, green, blue, alpha); set to White
        py_nvosd_text_params.font_params.font_color.set(1.0, 1.0, 1.0, 1.0)

        # Text background color
        py_nvosd_text_params.set_bg_clr = 1
        # set(red, green, blue, alpha); set to Black
        py_nvosd_text_params.text_bg_clr.set(0.0, 0.0, 0.0, 1.0)
        # Using pyds.get_string() to get display_text as string
        print(pyds.get_string(py_nvosd_text_params.display_text))
        pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)
        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    return Gst.PadProbeReturn.OK


def add_obj_meta_to_frame(frame_object, batch_meta, frame_meta, label_names):
    """ Inserts an object into the metadata """
    # this is a good place to insert objects into the metadata.
    # Here's an example of inserting a single object.
    obj_meta = pyds.nvds_acquire_obj_meta_from_pool(batch_meta)
    # Set bbox properties. These are in input resolution.
    rect_params = obj_meta.rect_params
    rect_params.left = int(IMAGE_WIDTH * frame_object.left)
    rect_params.top = int(IMAGE_HEIGHT * frame_object.top)
    rect_params.width = int(IMAGE_WIDTH * frame_object.width)
    rect_params.height = int(IMAGE_HEIGHT * frame_object.height)

    # Semi-transparent yellow backgroud
    rect_params.has_bg_color = 0
    rect_params.bg_color.set(1, 1, 0, 0.4)

    # Red border of width 3
    rect_params.border_width = 3
    rect_params.border_color.set(1, 0, 0, 1)

    # Set object info including class, detection confidence, etc.
    obj_meta.confidence = frame_object.detectionConfidence
    obj_meta.class_id = frame_object.classId

    # There is no tracking ID upon detection. The tracker will
    # assign an ID.
    obj_meta.object_id = UNTRACKED_OBJECT_ID

    lbl_id = frame_object.classId
    if lbl_id >= len(label_names):
        lbl_id = 0

    # Set the object classification label.
    obj_meta.obj_label = label_names[lbl_id]

    # Set display text for the object.
    txt_params = obj_meta.text_params
    if txt_params.display_text:
        pyds.free_buffer(txt_params.display_text)

    txt_params.x_offset = int(rect_params.left)
    txt_params.y_offset = max(0, int(rect_params.top) - 10)
    txt_params.display_text = (
        label_names[lbl_id] + " " + "{:04.3f}".format(frame_object.detectionConfidence)
    )
    # Font , font-color and font-size
    txt_params.font_params.font_name = "Serif"
    txt_params.font_params.font_size = 10
    # set(red, green, blue, alpha); set to White
    txt_params.font_params.font_color.set(1.0, 1.0, 1.0, 1.0)

    # Text background color
    txt_params.set_bg_clr = 1
    # set(red, green, blue, alpha); set to Black
    txt_params.text_bg_clr.set(0.0, 0.0, 0.0, 1.0)

    # Inser the object into current frame meta
    # This object has no parent
    pyds.nvds_add_obj_meta_to_frame(frame_meta, obj_meta, None)


def pgie_src_pad_buffer_probe(pad, info, u_data):

    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer ")
        return

    # Retrieve batch metadata from the gst_buffer
    # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
    # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list

    detection_params = DetectionParam(CLASS_NB, ACCURACY_ALL_CLASS)
    box_size_param = BoxSizeParam(IMAGE_HEIGHT, IMAGE_WIDTH,
                                  MIN_BOX_WIDTH, MIN_BOX_HEIGHT)
    nms_param = NmsParam(TOP_K, IOU_THRESHOLD)

    label_names = get_label_names_from_file("Models/trtis_model/ssd_inception_v2_coco_2018_01_28/labels.txt")

    while l_frame is not None:
        try:
            # Note that l_frame.data needs a cast to pyds.NvDsFrameMeta
            # The casting also keeps ownership of the underlying memory
            # in the C code, so the Python garbage collector will leave
            # it alone.
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        l_user = frame_meta.frame_user_meta_list
        while l_user is not None:
            try:
                # Note that l_user.data needs a cast to pyds.NvDsUserMeta
                # The casting also keeps ownership of the underlying memory
                # in the C code, so the Python garbage collector will leave
                # it alone.
                user_meta = pyds.NvDsUserMeta.cast(l_user.data)
            except StopIteration:
                break

            if (
                    user_meta.base_meta.meta_type
                    != pyds.NvDsMetaType.NVDSINFER_TENSOR_OUTPUT_META
            ):
                continue

            tensor_meta = pyds.NvDsInferTensorMeta.cast(user_meta.user_meta_data)

            # Boxes in the tensor meta should be in network resolution which is
            # found in tensor_meta.network_info. Use this info to scale boxes to
            # the input frame resolution.
            layers_info = []

            for i in range(tensor_meta.num_output_layers):
                layer = pyds.get_nvds_LayerInfo(tensor_meta, i)
                layers_info.append(layer)

            frame_object_list = nvds_infer_parse_custom_tf_ssd(
                layers_info, detection_params, box_size_param, nms_param
            )
            try:
                l_user = l_user.next
            except StopIteration:
                break

            for frame_object in frame_object_list:
                add_obj_meta_to_frame(frame_object, batch_meta, frame_meta, label_names)

        try:
            l_frame = l_frame.next
        except StopIteration:
            break
    return Gst.PadProbeReturn.OK


def main(args):

    # Standard GStreamer initialization
    GObject.threads_init()
    Gst.init(None)

    # Create gstreamer elements
    # Create Pipeline element that will form a connection of other elements
    print("Creating Pipeline \n ")
    pipeline = Gst.Pipeline()

    if not pipeline:
        sys.stderr.write(" Unable to create Pipeline \n")
    
    ########################### change source element: file to rasbery ##########################
    # Source element for reading from the file
    print("Creating Source \n")
    source = Gst.ElementFactory.make("nvarguscamerasrc", "src-elem")
    if not source:
        sys.stderr.write(" Unable to create Source \n")

    # Converter to scale the image
    nvvidconv_src = Gst.ElementFactory.make("nvvideoconvert", "convertor_src")
    if not nvvidconv_src:
        sys.stderr.write(" Unable to create nvvidconv_src \n")
    
    # Caps for NVMM and resolution scaling
    caps_nvvidconv_src = Gst.ElementFactory.make("capsfilter", "nvmm_caps")
    if not caps_nvvidconv_src:
        sys.stderr.write(" Unable to create capsfilter \n")

    # Since the data format in the input file is elementary h264 stream,
    # we need a h264parser
    #h264parser = make_elm_or_print_err("h264parse", "h264-parser", "H264Parser")

    # Use nvdec_h264 for hardware accelerated decode on GPU
    #decoder = make_elm_or_print_err("nvv4l2decoder", "nvv4l2-decoder", "Decoder")

    ################################################################################################################

    # Create nvstreammux instance to form batches from one or more sources.
    streammux = make_elm_or_print_err("nvstreammux", "Stream-muxer", "NvStreamMux")

    # Use nvinferserver to run inferencing on decoder's output,
    # behaviour of inferencing is set through config file
    pgie = make_elm_or_print_err("nvinferserver", "primary-inference", "Nvinferserver")

    # Use convertor to convert from NV12 to RGBA as required by nvosd
    nvvidconv = make_elm_or_print_err("nvvideoconvert", "convertor", "Nvvidconv")

    # Create OSD to draw on the converted RGBA buffer
    nvosd = make_elm_or_print_err("nvdsosd", "onscreendisplay", "OSD (nvosd)")

    # Create Post ODS Convertor for RTSP
    nvvidconv_post_osd = make_elm_or_print_err("nvvideoconvert", "convertor_postosd", "Post OSD for nvosd")


    # Finally encode and save the osd output
    #queue = make_elm_or_print_err("queue", "queue", "Queue")

    #nvvidconv2 = make_elm_or_print_err("nvvideoconvert", "convertor2", "Converter 2 (nvvidconv2)")

    #capsfilter = make_elm_or_print_err("capsfilter", "capsfilter", "capsfilter")
    ### caps for h264 datei to change as we will use raspberry Pi Camera
    #caps = Gst.Caps.from_string("video/x-raw, format=I420")
    #capsfilter.set_property("caps", caps)
    #################################################################

    # On Jetson, there is a problem with the encoder failing to initialize
    # due to limitation on TLS usage. To work around this, preload libgomp.
    # Add a reminder here in case the user forgets.
    preload_reminder = "If the following error is encountered:\n" + \
                       "/usr/lib/aarch64-linux-gnu/libgomp.so.1: cannot allocate memory in static TLS block\n" + \
                       "Preload the offending library:\n" + \
                       "export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1\n"
    ## encoder for out_file
    #encoder = make_elm_or_print_err("avenc_mpeg4", "encoder", "Encoder", preload_reminder)

    #encoder.set_property("bitrate", 2000000)

    #codeparser = make_elm_or_print_err("mpeg4videoparse", "mpeg4-parser", 'Code Parser')

    #container = make_elm_or_print_err("qtmux", "qtmux", "Container")
    #sink = make_elm_or_print_err("filesink", "filesink", "Sink")

    #sink.set_property("location", OUTPUT_VIDEO_NAME)
    #sink.set_property("sync", 0)
    #sink.set_property("async", 0)

    ################################### CSI_Camera set properties #####################################

    source.set_property('bufapi-version', True)

    caps_nvvidconv_src.set_property('caps', Gst.Caps.from_string('video/x-raw(memory:NVMM), width=1280, height=720'))

    streammux.set_property('width', config.CAMERA_WIDTH)
    streammux.set_property('height', config.CAMERA_HEIGHT)
    streammux.set_property('batch-size', config.BATCH_SIZE)
    streammux.set_property('batched-push-timeout', config.BATCH_PUSH_TIMEOUT)

    ##############################################################################################

    ################################## Make an encoder for RTSP ##################################

    if config.CODEC == "H264":
        encoder_rtsp = make_elm_or_print_err("nvv4l2h264enc","encoder", "Encoder",preload_reminder)
        print("Creating H264 Encoder")
    elif config.CODEC == "H265":
        encoder_rtsp = make_elm_or_print_err("nvv4l2h265enc","encoder", "Encoder",preload_reminder)
        print("Creating H265 Encoder")
    

    encoder_rtsp.set_property('bitrate', config.BITRATE)
    if is_aarch64():
        encoder_rtsp.set_property('preset-level', 1)
        encoder_rtsp.set_property('insert-sps-pps', 1)
        encoder_rtsp.set_property('bufapi-version', 1)
    
    ## Create Filter for RTSP
    caps_rtsp = make_elm_or_print_err("capsfilter", "filter", "caps_rtsp")
    caps_rtsp.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), format=I420"))

    # Make the payload-encode video into RTP packets
    if config.CODEC == "H264":
        rtppay = make_elm_or_print_err("rtph264pay", "rtppay","RTPPAY")
        print("Creating H264 rtppay")
    elif config.CODEC == "H265":
        rtppay = make_elm_or_print_err("rtph265pay", "rtppay","RTPPAY")
        print("Creating H265 rtppay")
    if not rtppay:
        sys.stderr.write(" Unable to create rtppay")
    
    # Make the UDP sink for RTSP
    updsink_port_num = config.UDP_PORT_SINK
    sink_rtsp = make_elm_or_print_err("udpsink","udpsink","Sink For RTSP")
    
    sink_rtsp.set_property('host', '224.224.255.255')
    sink_rtsp.set_property('port', updsink_port_num)
    sink_rtsp.set_property('async', False)
    sink_rtsp.set_property('sync', 1)


    ##################### change play file to play CIS-Camera ####################
    #print("Playing file %s " % args[1])
    #source.set_property("location", args[1])
    #streammux.set_property("width", IMAGE_WIDTH)
    #streammux.set_property("height", IMAGE_HEIGHT)
    #streammux.set_property("batch-size", 1)
    #streammux.set_property("batched-push-timeout", 4000000)
    #############################################################


    pgie.set_property("config-file-path", "configurations/dstest_ssd_nopostprocess.txt")
    ##################### change play file to play CIS-Camera ####################



    print("Adding elements to Pipeline \n")
    pipeline.add(source)
    pipeline.add(nvvidconv_src)
    pipeline.add(caps_nvvidconv_src)
    pipeline.add(streammux)
    pipeline.add(pgie)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(nvvidconv_post_osd)
    pipeline.add(caps_rtsp)
    pipeline.add(encoder_rtsp)
    pipeline.add(rtppay)
    #pipeline.add(queue)
    #pipeline.add(capsfilter)
    #pipeline.add(encoder)
    #pipeline.add(codeparser)
    #pipeline.add(container)
    pipeline.add(sink_rtsp)

    ## add comment to show pipeline struckture.

    print("Linking elements in the Pipeline \n")
    source.link(nvvidconv_src)
    nvvidconv_src.link(caps_nvvidconv_src)

    sinkpad = streammux.get_request_pad("sink_0")
    if not sinkpad:
        sys.stderr.write(" Unable to get the sink pad of streammux \n")
    srcpad = caps_nvvidconv_src.get_static_pad("src")
    if not srcpad:
        sys.stderr.write(" Unable to get source pad of decoder \n")
    srcpad.link(sinkpad)
    streammux.link(pgie)
    pgie.link(nvvidconv)
    nvvidconv.link(nvosd)
    nvosd.link(nvvidconv_post_osd)
    nvvidconv_post_osd.link(caps_rtsp)
    caps_rtsp.link(encoder_rtsp)
    encoder_rtsp.link(rtppay)
    rtppay.link(sink_rtsp)

    #nvosd.link(queue)
    #queue.link(nvvidconv2)
    #nvvidconv2.link(capsfilter)
    #capsfilter.link(encoder)
    #encoder.link(codeparser)
    #codeparser.link(container)
    #container.link(sink)

    # create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    ## start Streaming
    #  
    rtsp_port_num = 8554
    
    server = GstRtspServer.RTSPServer.new()
    server.props.service = "%d" % rtsp_port_num
    server.attach(None)
    
    factory = GstRtspServer.RTSPMediaFactory.new()
    factory.set_launch( "( udpsrc name=pay0 port=%d buffer-size=524288 caps=\"application/x-rtp, media=video, clock-rate=90000, encoding-name=(string)%s, payload=96 \" )" % (updsink_port_num, config.CODEC))
    factory.set_shared(True)
    server.get_mount_points().add_factory("/ds-resnet10", factory)
    
    print("\n *** DeepStream: Launched RTSP Streaming at rtsp://localhost:%d/ds-resnet10 ***\n\n" % rtsp_port_num)
    
    # Add a probe on the primary-infer source pad to get inference output tensors
    pgiesrcpad = pgie.get_static_pad("src")
    if not pgiesrcpad:
        sys.stderr.write(" Unable to get src pad of primary infer \n")

    pgiesrcpad.add_probe(Gst.PadProbeType.BUFFER, pgie_src_pad_buffer_probe, 0)

    # Lets add probe to get informed of the meta data generated, we add probe to
    # the sink pad of the osd element, since by that time, the buffer would have
    # had got all the metadata.
    osdsinkpad = nvosd.get_static_pad("sink")
    if not osdsinkpad:
        sys.stderr.write(" Unable to get sink pad of nvosd \n")

    osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, 0)

    # start play back and listen to events
    print("Starting pipeline \n")
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass
    # cleanup
    pipeline.set_state(Gst.State.NULL)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
