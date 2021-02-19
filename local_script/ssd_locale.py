import sys
import io
import os
import gi
import configurations.configuration as cfg
from datetime import date
today = date.today()

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
import pyds

from python_app.pipeline_src import cis_camera_source as make_src_elt
from python_app.pipeline_sink import local_display,local_output_file
import  python_app.pipeline_main as plmain

def main(output_dir,bitrate):

    # Standard GStreamer initialization
    GObject.threads_init()
    Gst.init(None)

    # Create gstreamer elements
    # Create Pipeline element that will form a connection of other elements
    print("Creating Pipeline \n ")
    pipeline = Gst.Pipeline()

    if not pipeline:
        sys.stderr.write(" Unable to create Pipeline \n")

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

    # Finally encode and save the osd output
    queue = plmain.make_elm_or_print_err("queue", "queue", "Queue")
    
    # create output elts to save into the file
    file_name = "ssd_" + str(today.strftime("%b-%d-%Y")) + ".mp4"
    if not os.path.exists(output_dir):     
        os.makedirs(output_dir)
    output_file = os.path.join(output_dir,file_name)
    nvvidconv_to_file,capsfilter,encoder,codeparser,container,sink_file = local_output_file(bitrate,
                                                                                output_file)

    # create output display
    #transform, sink_display = local_display()

    print("Adding all elements to the Pipeline \n")

    pipeline.add(source_src)
    pipeline.add(src_nvvidconv_1)
    pipeline.add(src_filter)
    pipeline.add(streammux)
    pipeline.add(pgie_for_infer)
    pipeline.add(nvvidconv_nv12_to_rgba)
    pipeline.add(nvosd_to_draw)
    pipeline.add(queue)
    pipeline.add(nvvidconv_to_file)
    pipeline.add(capsfilter)
    pipeline.add(encoder)
    pipeline.add(codeparser)
    pipeline.add(container)
    pipeline.add(sink_file)

    # we link the elements together
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

    srcpad.link(sinkpad)
    streammux.link(pgie_for_infer)
    pgie_for_infer.link(nvvidconv_nv12_to_rgba)
    nvvidconv_nv12_to_rgba.link(nvosd_to_draw)
    nvosd_to_draw.link(queue)
    queue.link(nvvidconv_to_file)
    nvvidconv_to_file.link(capsfilter)
    capsfilter.link(encoder)
    encoder.link(codeparser)
    codeparser.link(container)
    container.link(sink_file)

    # create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    # Add a probe on the primary-infer source pad to get inference output tensors
    pgiesrcpad = pgie_for_infer.get_static_pad("src")
    if not pgiesrcpad:
        sys.stderr.write(" Unable to get src pad of primary infer \n")

    pgiesrcpad.add_probe(Gst.PadProbeType.BUFFER, plmain.pgie_src_pad_buffer_probe, 0)

    # Lets add probe to get informed of the meta data generated, we add probe to
    # the sink pad of the osd element, since by that time, the buffer would have
    # had got all the metadata.
    osdsinkpad = nvosd_to_draw.get_static_pad("sink")
    if not osdsinkpad:
        sys.stderr.write(" Unable to get sink pad of nvosd \n")

    osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, plmain.osd_sink_pad_buffer_probe, 0)

    # start play back and listen to events
    print("Starting pipeline \n")
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass
    # cleanup
    pipeline.set_state(Gst.State.NULL)



