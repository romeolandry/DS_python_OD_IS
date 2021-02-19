""" This will reab cis-camera and render to rtsp
    the meta dat will bge extracting with.
    ------------ To make change ---------
     - to change the model: change config .txt file 
     - and the parse function  'pgie_src_pad_buffer_probe' with the corresponded parser for th new model
"""
import sys
import io
import os
import gi
sys.path.append(os.path.join('.', os.curdir))

from configurations import configuration as cfg

gi.require_version("Gst", "1.0")
gi.require_version('GstRtspServer', '1.0')

from gi.repository import GObject, Gst, GstRtspServer
from utils.common.is_aarch_64 import is_aarch64
from utils.common.bus_call import bus_call
from utils.trtis.ssd_parser import (nvds_infer_parse_custom_tf_ssd,
                                    DetectionParam,
                                    NmsParam,
                                    BoxSizeParam
                                    )

from python_app.pipeline_src import cis_camera_source as make_src_elt
from python_app.pipeline_sink import rtsp_sink, local_display
import python_app.pipeline_main as plmain
# from python_app.pipeline_main import *
# from python_app.pipeline_main import model_cfg, data_cfg,pgie_src_pad_buffer_probe

# sys.path.append(os.path.abspath(os.curdir))

def tf_ssd_model(model_name):
    GObject.threads_init()
    Gst.init(None)
    # Create an Pipeline 
    pipeline = Gst.Pipeline()

    if not pipeline:
        sys.stderr.write("unable to create Pipeline \n")
    
    print("create source elements and setting")
    source_src, src_nvvidconv_1, src_filter = make_src_elt(cfg.CSI_INPUT)

    # Streammux to playing and get get Frame for inference
    print("Creating Streammux")
    
    streammux = plmain.make_elm_or_print_err("nvstreammux",
                                     "Stream-muxer",
                                     "NsStreamMux")

    streammux.set_property('width', cfg.CAMERA_WIDTH)
    streammux.set_property('height', cfg.CAMERA_HEIGHT)
    streammux.set_property('batch-size', cfg.BATCH_SIZE)
    streammux.set_property('batched-push-timeout', cfg.BATCH_PUSH_TIMEOUT)

    # nvinferserver run Inference on decoder output
    # nvinferserv get as input NV12 from NsStreamMux 
    # and return NV12, and meta-data contened coordinate for bbox
    # all parameter of inference  is  set  through config file for model (.txt)
    print("Creating inference element for pipeline!")
    # we creta an object 'nvinferserver' whith name 'primary-inference 
    # because the we  apply the first inference on frame
    pgie_for_infer = plmain.make_elm_or_print_err("nvinferserver",
                                          "primary-inference",
                                          "Nvinferserver"
                                         )
    #  load setting or config from .txt
    pgie_for_infer.set_property("config-file-path",cfg.Model_CONF['config_file'])

    # Convert the NV12 to RGBA. Because the nvosd require RGBA to draw 
    # bbox on top of it. Create an converttor to do it.
    nvvidconv_nv12_to_rgba = plmain.make_elm_or_print_err("nvvideoconvert",
                                                         "convertor",
                                                         "Nvvidconv",
                                                        )
    # we can now draw the bbox with OSD on the converted buffer
    # and display on screen
    nvosd_to_draw = plmain.make_elm_or_print_err("nvdsosd",
                                                 "onscreendisplay",
                                                 "OSD (nvosd) to draw and display"
                                                )

    #--------------- pipeline elements for sink (output)---------

    # ++++++ create elements for broker ++++++++++++++++++
    msgconv = plmain.make_elm_or_print_err("nvmsgconv",
                                           "msgconv",
                                           "nvmsgconv to convert for broker")
    
    msgconv.set_property('config',cfg.BROKER_CONF['msconv_cfg_file']) 
    msgconv.set_property('payload-type', cfg.BROKER_CONF['schema_type'])

    msgbroker = plmain.make_elm_or_print_err("nvmsgbroker",
                                             "msgbroker",
                                             "msg broker to send")
    
    msgbroker.set_property('proto-lib', cfg.BROKER_CONF['proto_lib'])
    msgbroker.set_property('conn-str', cfg.BROKER_CONF['IP'] + ";" + cfg.BROKER_CONF['port'] + ";" + cfg.BROKER_CONF['topic']) # "ip;port;topicname"
    msgbroker.set_property('sync', False)



    # +++++++++++++++++++++ RTSP elements +++++++++++++++
    # To create and post convertor 
    # to converte the displaying screen element
    # for RTSP output
    nvvidconv_post_osd_to_rtsp = plmain.make_elm_or_print_err("nvvideoconvert",
                                                       "convertor_postosd",
                                                       "Post OSD for nvosd"
                                                      )
    
    # Create RTPS Sink Element with her filter and encoder
    filter_for_rtsp, encoder_rtsp, rtppay, sink_rtsp = rtsp_sink(cfg.CODEC,
                                                                 cfg.BITRATE,
                                                                 cfg.UDP_CONF
                                                                )
        

    # ------- Create element for multiple output configuration -----

    tee = plmain.make_elm_or_print_err("tee",
                                       "nvsink-tee",
                                       "tee to set multiple src as output")
    
    broker_queue = plmain.make_elm_or_print_err("queue",
                                                "nvtee-broker",
                                                "queue for broker")
    
    rtsp_queue = plmain.make_elm_or_print_err("queue",
                                              "nvtee-rtsp",
                                              "queue for rtsp")       

    print("Adding all elements to the Pipeline \n")

    pipeline.add(source_src)
    pipeline.add(src_nvvidconv_1)
    pipeline.add(src_filter)
    pipeline.add(streammux)
    pipeline.add(pgie_for_infer)
    pipeline.add(nvvidconv_nv12_to_rgba)
    pipeline.add(nvosd_to_draw)
    pipeline.add(tee)

    print("Adding Broker element")
    pipeline.add(broker_queue)
    pipeline.add(msgconv)
    pipeline.add(msgbroker)

    print("Adding RTSP element")
    pipeline.add(rtsp_queue)
    pipeline.add(nvvidconv_post_osd_to_rtsp)
    pipeline.add(filter_for_rtsp)
    pipeline.add(encoder_rtsp)
    pipeline.add(rtppay)
    pipeline.add(sink_rtsp)
            
    print("Linking elements in the  pipeline \n")

    source_src.link(src_nvvidconv_1)
    src_nvvidconv_1.link(src_filter)

    # from the source filter  get the src
    srcpad = src_filter.get_static_pad("src")
    if not srcpad:
        sys.stderr.write(" Unable to get source pad of decoder \n")

    #  from  streammux get the streaming output
    sinkpad = streammux.get_request_pad("sink_0")
    if not sinkpad:
        sys.stderr.write(" Unable to get the sink pad of streammux \n")
    
    # link the filter src-element  with streaming  output
    srcpad.link(sinkpad)
    streammux.link(pgie_for_infer)
    pgie_for_infer.link(nvvidconv_nv12_to_rgba)
    nvvidconv_nv12_to_rgba.link(nvosd_to_draw)
    nvosd_to_draw.link(tee)
    
    # link elt for rtsp
    rtsp_queue.link(nvvidconv_post_osd_to_rtsp)
    nvvidconv_post_osd_to_rtsp.link(filter_for_rtsp)
    filter_for_rtsp.link(encoder_rtsp)
    encoder_rtsp.link(rtppay)
    rtppay.link(sink_rtsp)

    # link elt for broker
    broker_queue.link(msgconv)
    msgconv.link(msgbroker)

    # link the both with tee elt
    broker_sink_pad = broker_queue.get_static_pad("sink") # get output interface of broker_queue object 
    rtsp_sink_pad = rtsp_queue.get_static_pad("sink") # get output interface of rtsp_queue object
    
    # instantiate the two output(src) wee need
    tee_msg_pad = tee.get_request_pad('src_%u') # output for broker
    tee_rtsp_pad = tee.get_request_pad('src_%u') # output for rtsp

    if not tee_msg_pad or not tee_rtsp_pad:
        sys.stderr.write("Unable to get request pads\n")


    tee_msg_pad.link(broker_sink_pad)
    tee_rtsp_pad.link(rtsp_sink_pad)

    print("linked with broker element")

    # create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    # start Streaming on RTSP
    server = GstRtspServer.RTSPServer.new()
    server.props.service = "%d" % cfg.RTSP_PORT
    server.attach(None)

    factory = GstRtspServer.RTSPMediaFactory.new()
    factory.set_launch("( udpsrc name=pay0 port=%d buffer-size=524288 caps=\"application/x-rtp, media=video, clock-rate=90000, encoding-name=(string)%s,payload=96 \" )" % (cfg.UDP_CONF['port'], cfg.CODEC))

    factory.set_shared(True)
    server.get_mount_points().add_factory("/" + str(model_name), factory)

    print(f"\n *** DeepStream: Launched RTSP Streaming at rtsp://localhost:{cfg.RTSP_PORT}/{model_name} ***\n\n")

    # Add a probe on the primary-infer source pad
    # to get inference output tensors
    
    # As nvosd can't draw  the bbox  for native TF model
    # the 'pgie_src_pad_buffer_probe' will parse the meta data 
    # and  generate an layer for every frame on buffer
    # so that the 'nvosd can read and display it.'

    pgiesrcpad = pgie_for_infer.get_static_pad("src")
    if not pgiesrcpad:
        sys.stderr.write(" Unable to get src pad of primary infer \n")

    # to chane the default configuration
    # config_type could be 'model', 'data' or 'udp'
    
    # plmain.set_config_data(config_type="DATA_CONF", config_name="nb_classes",value=20)
   
    pgiesrcpad.add_probe(Gst.PadProbeType.BUFFER, plmain.pgie_src_pad_buffer_probe, 0)

    # Lets add probe to get informed of the meta data generated,
    # we add probe to the sink pad of the osd element,
    # since by that time, the buffer would have had got all the metadata.

    osdsinkpad = nvosd_to_draw.get_static_pad("sink")
    if not osdsinkpad:
        sys.stderr.write(" Unable to get sink pad of nvosd \n")

    print("probe with msg_broker was loaded")
    osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, plmain.osd_sink_pad_buffer_probe_msg_broker, 0)
    
    # start play back and listen to events
    print("Starting pipeline \n")
    pipeline.set_state(Gst.State.PLAYING)
    loop.run()
    # cleanup
    pipeline.set_state(Gst.State.NULL)


def tf_ssd_model_local(model):
    GObject.threads_init()
    Gst.init(None)
    # Create an Pipeline 
    pipeline = Gst.Pipeline()

    if not pipeline:
        sys.stderr.write("unable to create Pipeline \n")
    
    print("create source elements and setting")
    source_src, src_nvvidconv_1, src_filter = make_src_elt(cfg.CSI_INPUT)

    # Streammux to playing and get get Frame for inference
    print("Creating Streammux")
    
    streammux = plmain.make_elm_or_print_err("nvstreammux",
                                     "Stream-muxer",
                                     "NsStreamMux")

    streammux.set_property('width', cfg.CAMERA_WIDTH)
    streammux.set_property('height', cfg.CAMERA_HEIGHT)
    streammux.set_property('batch-size', cfg.BATCH_SIZE)
    streammux.set_property('batched-push-timeout', cfg.BATCH_PUSH_TIMEOUT)

    # nvinferserver run Inference on decoder output
    # nvinferserv get as input NV12 from NsStreamMux 
    # and return NV12, and meta-data contened coordinate for bbox
    # all parameter of inference  is  set  through config file for model (.txt)
    print("Creating inference element for pipeline!")
    # we creta an object 'nvinferserver' whith name 'primary-inference 
    # because the we  apply the first inference on frame
    pgie_for_infer = plmain.make_elm_or_print_err("nvinferserver",
                                          "primary-inference",
                                          "Nvinferserver"
                                         )
    #  load setting or config from .txt
    pgie_for_infer.set_property("config-file-path",cfg.Model_CONF['config_file'])

    # Convert the NV12 to RGBA. Because the nvosd require RGBA to draw 
    # bbox on top of it. Create an converttor to do it.
    nvvidconv_nv12_to_rgba = plmain.make_elm_or_print_err("nvvideoconvert",
                                                         "convertor",
                                                         "Nvvidconv",
                                                        )
    # we can now draw the bbox with OSD on the converted buffer
    # and display on screen
    nvosd_to_draw = plmain.make_elm_or_print_err("nvdsosd",
                                                 "onscreendisplay",
                                                 "OSD (nvosd) to draw and display"
                                                )

    #--------------- pipeline elements for sink (output)---------
    transform_display, sink_display = local_display()       

    print("Adding all elements to the Pipeline \n")

    pipeline.add(source_src)
    pipeline.add(src_nvvidconv_1)
    pipeline.add(src_filter)
    pipeline.add(streammux)
    pipeline.add(pgie_for_infer)
    pipeline.add(nvvidconv_nv12_to_rgba)
    pipeline.add(nvosd_to_draw)

    if transform_display is not None:
        pipeline.add(transform_display)
    pipeline.add(sink_display)
            
    print("Linking elements in the  pipeline \n")

    source_src.link(src_nvvidconv_1)
    src_nvvidconv_1.link(src_filter)

    # from the source filter  get the src
    srcpad = src_filter.get_static_pad("src")
    if not srcpad:
        sys.stderr.write(" Unable to get source pad of decoder \n")

    #  from  streammux get the streaming output
    sinkpad = streammux.get_request_pad("sink_0")
    if not sinkpad:
        sys.stderr.write(" Unable to get the sink pad of streammux \n")
    # link the filter src-element  with streaming  output
    srcpad.link(sinkpad)
    streammux.link(pgie_for_infer)
    pgie_for_infer.link(nvvidconv_nv12_to_rgba)
    nvvidconv_nv12_to_rgba.link(nvosd_to_draw)

    if transform_display is not None:
        nvvidconv_nv12_to_rgba.link(transform_display)
        transform_display.link(sink_display)
    else:
        nvvidconv_nv12_to_rgba.link(sink_display)

    # create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    # Add a probe on the primary-infer source pad
    # to get inference output tensors
    
    # As nvosd can't draw  the bbox  for native TF model
    # the 'pgie_src_pad_buffer_probe' will parse the meta data 
    # and  generate an layer for every frame on buffer
    # so that the 'nvosd can read and display it.'

    pgiesrcpad = pgie_for_infer.get_static_pad("src")
    if not pgiesrcpad:
        sys.stderr.write(" Unable to get src pad of primary infer \n")

    # to chane the default configuration
    # config_type could be 'model', 'data' or 'udp'
    
    # plmain.set_config_data(config_type="DATA_CONF", config_name="nb_classes",value=20)
   
    pgiesrcpad.add_probe(Gst.PadProbeType.BUFFER, plmain.pgie_src_pad_buffer_probe, 0)

    # Lets add probe to get informed of the meta data generated,
    # we add probe to the sink pad of the osd element,
    # since by that time, the buffer would have had got all the metadata.

    osdsinkpad = nvosd_to_draw.get_static_pad("sink")
    if not osdsinkpad:
        sys.stderr.write(" Unable to get sink pad of nvosd \n")

    print("probe with msg_broker was loaded")
    osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, plmain.osd_sink_pad_buffer_probe_msg_broker, 0)
    
    # start play back and listen to events
    print("Starting pipeline \n")
    pipeline.set_state(Gst.State.PLAYING)
    loop.run()
    # cleanup
    pipeline.set_state(Gst.State.NULL)
