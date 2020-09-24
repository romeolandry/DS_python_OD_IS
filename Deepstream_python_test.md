# Deepstream python app test


Explanation of deepstream python and an simple implementation [hier](Deep Eye - DeepStream Based Video Analytics Made Easy)

## # Deepstream python app test1 read h264 file
The Deepstream python Application is run through an `pipeline`.

an simple pipeline is:
	
	Source -> Parser -> decoder -> Sink -> 

1- Initialize GStreamer

	GObject.threads_init()
	Gst.init(None)

2- Create pipeline that will form a connection of other elements
	
	pipeline = Gst.Pipeline()

3- Create different elements of the stream. the function to use is `Gst.ElementFactory.make("","")`

- Create source eg. `Gst.ElementFactory.make("filesrc", "file-source")` to read from file	
- Create parser eg. `H264Parser`
- Create Decoder eg. `Gst.ElementFactory.make("nvv4l2decoder", "nvv4l2-decoder")`
- Creating a nvstreammux instance to form batches for one or more sources eg. `streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")`
- converter to convert from NV12 to RGBA as required by nvosd `nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")`
- Create OSD to draw on the converted RGBA buffer `nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")`
- Creating the necessary sink for the same to render osd `Gst.ElementFactory.make("nveglglessink", "nvvideo-renderer")`

4- set the property

	print("Playing file /opt/nvidia/deepstream/deepstream-5.0/samples/streams/sample_720p.h264 ")
	source.set_property('location', [path to file]) 
	streammux.set_property('width', 1920)
	streammux.set_property('height', 1080)
	streammux.set_property('batch-size', 1)
	streammux.set_property('batched-push-timeout', 4000000)
	pgie.set_property('config-file-path',[path to config file])

4- linking the element in to the pipline

	print("Adding elements to Pipeline \n")
	pipeline.add(source) "input: file usb or rasberri"
	pipeline.add(h264parser)
	pipeline.add(decoder)
	pipeline.add(streammux) " to batch the source"
	pipeline.add(pgie) "model cofiguration"
	pipeline.add(nvvidconv)
	pipeline.add(nvosd) "draw box on the converted buffer"
	pipeline.add(sink) "output where the result will be rendered"

	**The linking**
	Elt_A.link(Elt_B)
	Elt_B.link(Elt_C)
	sud_Elt_of_C.link(Elt_D)
5- Create event loop to run the pipeline

	loop = GObject.MainLoop() "Declaration"
	bus = pipeline.get_bus()
	bus.add_signal_watch()
	bus.connect ("message", bus_call, loop)
6- Adding a probe to get the meta data generated

	# we add probe to the sink pad of the osd element, since by that time, 
	# the buffer would have had got all the metadata.
	osdsinkpad = nvosd.get_static_pad("sink")
	if not osdsinkpad:
	    sys.stderr.write(" Unable to get sink pad of nvosd \n")

	osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, 0)

7- start the pipline

	print("Starting pipeline \n")
	pipeline.set_state(Gst.State.PLAYING)
	try:
	    loop.run()
	except:
	    pass
	# cleaning up as the pipeline comes to an end
	pipeline.set_state(Gst.State.NULL)

## Deepstream pipline 

- The end of the pipline (common_part) are almost the same:

	nvstreammux --> nvinfer --> [tracker] --> nvvideoconvert --> nvdsosd --> [sink_output]

### Input type setting source

- for file as source

	file-source --> parser --> decoder --> common_part

- for usb camera as source

	usd-source[v4l2src] --> capsfilter[capsfilter] --> video_convertor[videoconvert] --> 		caps_vidconvsrc[capsfilter] --> common_part

you have set camera to play

	 print("Playing cam %s " %args[1])
    caps_v4l2src.set_property('caps', Gst.Caps.from_string("video/x-raw, framerate=30/1"))
    caps_vidconvsrc.set_property('caps', Gst.Caps.from_string("video/x-raw(memory:NVMM)"))
    source.set_property('device', args[1])
    streammux.set_property('width', 1920)
    streammux.set_property('height', 1080)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)
	

- for CIS camera eg. Rasberry py as source

	CIS-Source[nvarguscamerasrc] --> video Convertor[nvvideoconvert] --> capsfilter[capsfilter] --> common_part

and set CIS -device / set source property

	 source.set_property('bufapi-version', True)

    caps_nvvidconv_src.set_property('caps', Gst.Caps.from_string('video/x-raw(memory:NVMM), width=1280, height=720'))

    streammux.set_property('width', 1280)
    streammux.set_property('height', 720)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)

### outtype setting (sink/EGLSink)

- nvvideao renderer 

	print("Creating EGLSink \n")
    sink = Gst.ElementFactory.make("nveglglessink", "nvvideo-renderer")

- use RTSP as Output



## Issue 
-  no module name `common`.
	
	in to the file change `sys.path.append('../')` with `sys.path.append('[absolute path to the directory apps]') or run without Env

- No module named 'gi'
	
	if running into an virtualenv add the following line `sys.path.append('/usr/lib/python3/dist-packages')` to bind the python installation 
	or just run it without an virtualenv.

