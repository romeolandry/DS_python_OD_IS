import sys
import io
import os
import gi

import pyds
import cv2
import numpy as np

sys.path.append(os.path.join('..', os.curdir))

gi.require_version("Gst", "1.0")
gi.require_version('GstRtspServer', '1.0')

from gi.repository import GObject, Gst, GstRtspServer

from utils.trtis.ssd_parser import (nvds_infer_parse_custom_tf_ssd,
                                    DetectionParam,
                                    NmsParam,
                                    BoxSizeParam
                                    )
import configurations.configuration as cfg

from utils.common.utils import long_to_int
                         

global model_cfg
model_cfg = cfg.Model_CONF
global data_cfg
data_cfg = cfg.DATA_CONF

def set_config_data(config_name, value, config_type = None):
    if config_type == 'data':
        try:
            cfg.DATA_CONF[config_name] = value
        except Exception as e:
            sys.stderr.write(f" the name {config_name} doesn't exit as data config!")
    
    if config_type == 'model':
        try:
            cfg.Model_CONF[config_name] = value
        except Exception as e:
            sys.stderr.write(f" the name {config_name} doesn't exit as model config!")

    if config_type == 'udp':
        try:
            cfg.UDP_CONF[config_name] = value
        except Exception as e:
            sys.stderr.write(f" the name {config_name} doesn't exit as model config!")


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


def add_obj_meta_to_frame(frame_object,
                          batch_meta,
                          frame_meta,
                          label_names
                          ):

    """ Inserts an object into the metadata """
    # this is a good place to insert objects into the metadata.
    # Here's an example of inserting a single object.
    obj_meta = pyds.nvds_acquire_obj_meta_from_pool(batch_meta)
    # Set bbox properties. These are in input resolution.
    rect_params = obj_meta.rect_params
    rect_params.left = int(model_cfg['img_width'] * frame_object.left)
    rect_params.top = int(model_cfg['img_height'] * frame_object.top)
    rect_params.width = int(model_cfg['img_width'] * frame_object.width)
    rect_params.height = int(model_cfg['img_height'] * frame_object.height)

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
    obj_meta.object_id = model_cfg['untracted_object_id']

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
    txt_params.display_text = (label_names[lbl_id] + " " +  "{:04.3f}".format(frame_object.detectionConfidence))
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


def pgie_src_pad_buffer_probe(pad,
                              info,
                              u_data
                              ):

    gst_buffer = info.get_buffer()

    if not gst_buffer:
        print("Unable to get GstBuffer ")
        return

    # Retrieve batch metadata from the gst_buffer
    # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
    # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list

    detection_params = DetectionParam(data_cfg['nb_classes'], data_cfg['accuracy_all_class'])
    box_size_param = BoxSizeParam(model_cfg['img_height'],
                                  model_cfg['img_width'],
                                  model_cfg['min_box_width'],
                                  model_cfg['min_box_height']
                                  )
    nms_param = NmsParam(model_cfg['top_k'],
                         model_cfg['iou_threshold']
                         )

    label_names = get_label_names_from_file(data_cfg['patht_to_label'])

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

            if (user_meta.base_meta.meta_type != pyds.NvDsMetaType.NVDSINFER_TENSOR_OUTPUT_META):
                continue

            tensor_meta = pyds.NvDsInferTensorMeta.cast(user_meta.user_meta_data)

            # Boxes in the tensor meta should be in network resolution which is
            # found in tensor_meta.network_info.
            # Use this info to scale boxes to the input frame resolution.
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


def get_label_name(id_dict, obejct_id):
    for key,val in id_dict.items():
        if val == obejct_id:
            return key
    return None

def draw_bounding_boxes(image, obj_meta, confidence, id_dict):
    confidence = '{0:.2f}'.format(confidence)
    rect_params = obj_meta.rect_params
    top = int(rect_params.top)
    left = int(rect_params.left)
    width = int(rect_params.width)
    height = int(rect_params.height)
    obj_name = get_label_name(id_dict,obj_meta.class_id)
    image = cv2.rectangle(image, (left, top), (left + width, top + height), (0, 0, 255, 0), 2)
    # Note that on some systems cv2.putText erroneously draws horizontal lines across the image
    image = cv2.putText(image, obj_name + '_C=' + str(confidence), (left - 10, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255, 0), 2)
    return image


## Kafka get message from kafka protocol

# Callback function for deep-copying an NvDsEventMsgMeta struct
def meta_copy_func(data,user_data):
    # Cast data to pyds.NvDsUserMeta
    user_meta=pyds.NvDsUserMeta.cast(data)
    src_meta_data=user_meta.user_meta_data
    # Cast src_meta_data to pyds.NvDsEventMsgMeta
    srcmeta=pyds.NvDsEventMsgMeta.cast(src_meta_data)
    # Duplicate the memory contents of srcmeta to dstmeta
    # First use pyds.get_ptr() to get the C address of srcmeta, then
    # use pyds.memdup() to allocate dstmeta and copy srcmeta into it.
    # pyds.memdup returns C address of the allocated duplicate.
    dstmeta_ptr=pyds.memdup(pyds.get_ptr(srcmeta), sys.getsizeof(pyds.NvDsEventMsgMeta))
    # Cast the duplicated memory to pyds.NvDsEventMsgMeta
    dstmeta=pyds.NvDsEventMsgMeta.cast(dstmeta_ptr)

    # Duplicate contents of ts field. Note that reading srcmeat.ts
    # returns its C address. This allows to memory operations to be
    # performed on it.
    dstmeta.ts=pyds.memdup(srcmeta.ts, cfg.MAX_TIME_STAMP_LEN + 1)

    # Copy the sensorStr. This field is a string property.
    # The getter (read) returns its C address. The setter (write)
    # takes string as input, allocates a string buffer and copies
    # the input string into it.
    # pyds.get_string() takes C address of a string and returns
    # the reference to a string object and the assignment inside the binder copies content.
    dstmeta.sensorStr=pyds.get_string(srcmeta.sensorStr)

    if(srcmeta.objSignature.size>0):
        dstmeta.objSignature.signature=pyds.memdup(srcmeta.objSignature.signature,srcMeta.objSignature.size)
        dstmeta.objSignature.size = srcmeta.objSignature.size

    if(srcmeta.extMsgSize>0):
        if(srcmeta.objType==pyds.NvDsObjectType.NVDS_OBJECT_TYPE_VEHICLE):
            srcobj = pyds.NvDsVehicleObject.cast(srcmeta.extMsg)
            obj = pyds.alloc_nvds_vehicle_object()
            obj.type=pyds.get_string(srcobj.type)
            obj.make=pyds.get_string(srcobj.make)
            obj.model=pyds.get_string(srcobj.model)
            obj.color=pyds.get_string(srcobj.color)
            obj.license = pyds.get_string(srcobj.license)
            obj.region = pyds.get_string(srcobj.region)
            dstmeta.extMsg = obj
            dstmeta.extMsgSize = sys.getsizeof(pyds.NvDsVehicleObject)
        if(srcmeta.objType==pyds.NvDsObjectType.NVDS_OBJECT_TYPE_PERSON):
            srcobj = pyds.NvDsPersonObject.cast(srcmeta.extMsg)
            obj = pyds.alloc_nvds_person_object()
            obj.age = srcobj.age
            obj.gender = pyds.get_string(srcobj.gender)
            obj.cap = pyds.get_string(srcobj.cap)
            obj.hair = pyds.get_string(srcobj.hair)
            obj.apparel = pyds.get_string(srcobj.apparel)
            dstmeta.extMsg = obj
            dstmeta.extMsgSize = sys.getsizeof(pyds.NvDsVehicleObject)

    return dstmeta

# Callback function for freeing an NvDsEventMsgMeta instance
def meta_free_func(data,user_data):
    user_meta=pyds.NvDsUserMeta.cast(data)
    srcmeta=pyds.NvDsEventMsgMeta.cast(user_meta.user_meta_data)

    # pyds.free_buffer takes C address of a buffer and frees the memory
    # It's a NOP if the address is NULL
    pyds.free_buffer(srcmeta.ts)
    pyds.free_buffer(srcmeta.sensorStr)

    if(srcmeta.objSignature.size > 0):
        pyds.free_buffer(srcmeta.objSignature.signature);
        srcmeta.objSignature.size = 0

    if(srcmeta.extMsgSize > 0):
        if(srcmeta.objType == pyds.NvDsObjectType.NVDS_OBJECT_TYPE_VEHICLE):
            obj =pyds.NvDsVehicleObject.cast(srcmeta.extMsg)
            pyds.free_buffer(obj.type);
            pyds.free_buffer(obj.color);
            pyds.free_buffer(obj.make);
            pyds.free_buffer(obj.model);
            pyds.free_buffer(obj.license);
            pyds.free_buffer(obj.region);
        if(srcmeta.objType == pyds.NvDsObjectType.NVDS_OBJECT_TYPE_PERSON):
            obj = pyds.NvDsPersonObject.cast(srcmeta.extMsg);
            pyds.free_buffer(obj.gender);
            pyds.free_buffer(obj.cap);
            pyds.free_buffer(obj.hair);
            pyds.free_buffer(obj.apparel);
        pyds.free_gbuffer(srcmeta.extMsg);
        srcmeta.extMsgSize = 0;

def generate_vehicle_meta(data,save_path):
    obj = pyds.NvDsVehicleObject.cast(data)
    obj.type ="none"
    if save_path is not None:
        obj.type = save_path
    obj.color="blue"
    obj.make ="Bugatti"
    obj.model = "M"
    obj.license ="XX1234"
    obj.region ="CA"
    return obj

def generate_person_meta(data,save_path):
    obj = pyds.NvDsPersonObject.cast(data)
    
    obj.age = 45
    obj.cap = "none"
    if save_path is not None:
        obj.cap= save_path
    obj.hair = "black"
    obj.gender = "male"
    obj.apparel= "formal"
    return obj

def generate_phone_meta(data,save_path):
    obj = pyds.NvDsPersonObject.cast(data)
    obj.age = 45
    obj.cap = "none"
    if save_path is not None:
        obj.cap= save_path
    obj.hair = "black"
    obj.gender = "male"
    obj.apparel= "formal"
    return obj

def generate_event_msg_meta(data, class_id,id_dict,save_path):
    meta =pyds.NvDsEventMsgMeta.cast(data)
    meta.sensorId = 0
    meta.placeId = 0
    meta.moduleId = 0
    meta.sensorStr = "sensor-0"
    meta.ts = pyds.alloc_buffer(cfg.MAX_TIME_STAMP_LEN + 1)
    pyds.generate_ts_rfc3339(meta.ts, cfg.MAX_TIME_STAMP_LEN)

    # This demonstrates how to attach custom objects.
    # Any custom object as per requirement can be generated and attached
    # like NvDsVehicleObject / NvDsPersonObject. Then that object should
    # be handled in payload generator library (nvmsgconv.cpp) accordingly.
    if(class_id==id_dict["car"]):
        meta.type = pyds.NvDsEventType.NVDS_EVENT_MOVING
        meta.objType = pyds.NvDsObjectType.NVDS_OBJECT_TYPE_VEHICLE
        meta.objClassId = id_dict["car"]
        obj = pyds.alloc_nvds_vehicle_object()
        obj = generate_vehicle_meta(obj,save_path)
        meta.extMsg = obj
        meta.extMsgSize = sys.getsizeof(pyds.NvDsVehicleObject);
    if(class_id == id_dict["person"]):
        meta.type =pyds.NvDsEventType.NVDS_EVENT_ENTRY
        meta.objType = pyds.NvDsObjectType.NVDS_OBJECT_TYPE_PERSON;
        meta.objClassId = id_dict["person"]
        obj = pyds.alloc_nvds_person_object()
        obj=generate_person_meta(obj,save_path)
        meta.extMsg = obj
        meta.extMsgSize = sys.getsizeof(pyds.NvDsPersonObject)
    if(class_id == id_dict["cell phone"]):
        meta.type =pyds.NvDsEventType.NVDS_EVENT_ENTRY
        meta.objType = pyds.NvDsObjectType.NVDS_OBJECT_TYPE_PERSON;
        meta.objClassId = id_dict["person"]
        obj = pyds.alloc_nvds_person_object()
        obj=generate_phone_meta(obj,save_path)
        meta.extMsg = obj
        meta.extMsgSize = sys.getsizeof(pyds.NvDsPersonObject)
    return meta


def osd_sink_pad_buffer_probe_msg_broker_drawing(pad, info, u_data):
    frame_number = 0
    num_rects =0

    # Intiallizing object counter with 0.
    obj_counter = dict(enumerate([0] * data_cfg['nb_classes']))

    gst_buffer = info.get_buffer()

    if not gst_buffer:
        print("Unable to get GstBuffer")
        return
    # Retrieve batch metadata from the gst_buffer
    # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
    # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        frame_number = frame_meta.frame_num
        num_rects = frame_meta.num_obj_meta
        l_obj = frame_meta.obj_meta_list
        save_image = False
        while l_obj is not None:
            try:
                # Casting l_obj.data to pyds.NvDsObjectMeta
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                continue

            obj_counter[obj_meta.class_id] += 1

            display_meta = pyds.nvds_acquire_display_meta_from_pool(batch_meta)
            display_meta.num_labels = 1

            py_nvosd_text_params = display_meta.text_params[0]

            label_names_from_file = get_label_names_from_file(data_cfg['patht_to_label'])
            id_dict = {
                val: index
                for index, val in enumerate(label_names_from_file)
            }
            tracked_id = []
            for val in cfg.Tracked:
                tracked_id.append(id_dict[val])

            disp_string = ("Frame Number={} Number of Objects={} Vehicle_count={} Person_count={} Phone_count={}")

            py_nvosd_text_params.display_text = disp_string.format(
                frame_number,
                num_rects,
                obj_counter[id_dict["car"]],
                obj_counter[id_dict["person"]],
                obj_counter[id_dict["cell phone"]],
            )
            py_nvosd_text_params.x_offset = 10
            py_nvosd_text_params.y_offset = 12
            py_nvosd_text_params.font_params.font_name = "Serif"
            py_nvosd_text_params.font_params.font_size = 10
            py_nvosd_text_params.font_params.font_color.set(1.0, 1.0, 1.0, 1.0)

            # Text background color
            py_nvosd_text_params.set_bg_clr = 1
            # set(red, green, blue, alpha); set to Black
            py_nvosd_text_params.text_bg_clr.set(0.0, 0.0, 0.0, 1.0)

            # get object with somme score draw it and sent it to backend
            # server using msgbrker
            if( obj_meta.class_id in tracked_id):
                # Draw and save with open cv
                save_path = None
                # Getting Image data using nvbufsurface
                # the input should be address of buffer and batch_id
                n_frame = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
                # convert python array into numy array format.
                frame_image = np.array(n_frame, copy=True, order='C')
                # covert the array into cv2 default color format
                frame_image = cv2.cvtColor(frame_image, cv2.COLOR_RGBA2BGRA)
                if (obj_meta.confidence  >.5 ):
                    save_path = os.path.join(os.getcwd(),cfg.OUTPUT_DIR + "/stream_" + str(frame_meta.pad_index) + "/frame_" + str(frame_number) + ".jpg")
                    try:
                        cv2.imwrite(save_path, frame_image)
                    except Exception as e:
                        print("open cv didn't save")
                                    
                msg_meta=pyds.alloc_nvds_event_msg_meta()
                msg_meta.bbox.top =  obj_meta.rect_params.top
                msg_meta.bbox.left =  obj_meta.rect_params.left
                msg_meta.bbox.width = obj_meta.rect_params.width
                msg_meta.bbox.height = obj_meta.rect_params.height
                msg_meta.frameId = frame_number
                msg_meta.trackingId = long_to_int(obj_meta.object_id)
                msg_meta.confidence = obj_meta.confidence
                msg_meta = generate_event_msg_meta(msg_meta, obj_meta.class_id,id_dict,save_path)
                user_event_meta = pyds.nvds_acquire_user_meta_from_pool(batch_meta)
                if(user_event_meta):
                    user_event_meta.user_meta_data = msg_meta
                    user_event_meta.base_meta.meta_type = pyds.NvDsMetaType.NVDS_EVENT_MSG_META
                    # Setting callbacks in the event msg meta. The bindings layer
                    # will wrap these callables in C functions. Currently only one
                    # set of callbacks is supported.
                    pyds.set_user_copyfunc(user_event_meta, meta_copy_func)
                    pyds.set_user_releasefunc(user_event_meta, meta_free_func)
                    pyds.nvds_add_user_meta_to_frame(frame_meta, user_event_meta)                        
                else:
                    print("Error in attaching event meta to buffer\n")
                
            
            print(pyds.get_string(py_nvosd_text_params.display_text))
            
            pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)

            try:
                l_obj=l_obj.next
            except StopIteration:
                break
        
        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    return Gst.PadProbeReturn.OK