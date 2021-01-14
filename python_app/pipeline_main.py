import sys
import io
import os
import gi
sys.path.append(os.path.join('..', os.curdir))

gi.require_version("Gst", "1.0")
gi.require_version('GstRtspServer', '1.0')

from gi.repository import GObject, Gst, GstRtspServer

from utils.trtis.ssd_parser import (nvds_infer_parse_custom_tf_ssd,
                                    DetectionParam,
                                    NmsParam,
                                    BoxSizeParam
                                    )
                         
global PGIE_CLASS_ID_VEHICLE
PGIE_CLASS_ID_VEHICLE = 0
global PGIE_CLASS_ID_PERSON
PGIE_CLASS_ID_PERSON = 2

PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 2
PGIE_CLASS_ID_ROADSIGN = 3


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


def osd_sink_pad_buffer_probe(pad, info, u_data, data_cfg):
    frame_number = 0
    # Intiallizing object counter with 0.
    obj_counter = dict(enumerate([0] * data_cfg['nb_classes']))
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
        label_names_from_file = get_label_names_from_file(data_cfg['patht_to_label'])
        id_dict = {
            val: index
            for index, val in enumerate(label_names_from_file)
        }
        disp_string = ("Frame Number={} Number of Objects={} Vehicle_count={} Person_count={}")

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


def add_obj_meta_to_frame(frame_object,
                          batch_meta,
                          frame_meta,
                          label_names,
                          model_cfg
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
    txt_params.display_text = ("label_names[lbl_id] {:04.3f}".format(frame_object.detectionConfidence))
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
                              u_data,
                              model_cfg,
                              data_cfg
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


# tiler_sink_pad_buffer_probe  will extract metadata received on tiler src pad
# and update params for drawing rectangle, object information etc.
def tiler_sink_pad_buffer_probe(pad, info, u_data):
    frame_number = 0
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
            # The casting is done by pyds.NvDsFrameMeta.cast()
            # The casting also keeps ownership of the underlying memory
            # in the C code, so the Python garbage collector will leave
            # it alone.
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        frame_number = frame_meta.frame_num
        l_obj = frame_meta.obj_meta_list
        num_rects = frame_meta.num_obj_meta
        is_first_obj = True
        save_image = False

        obj_counter = {
            PGIE_CLASS_ID_VEHICLE: 0,
            PGIE_CLASS_ID_PERSON: 0,
            PGIE_CLASS_ID_BICYCLE: 0,
            PGIE_CLASS_ID_ROADSIGN: 0
        }
        while l_obj is not None:
            try:
                # Casting l_obj.data to pyds.NvDsObjectMeta
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break
            obj_counter[obj_meta.class_id] += 1
            # Periodically check for objects with borderline confidence value that may be false positive detections.
            # If such detections are found, annoate the frame with bboxes and confidence value.
            # Save the annotated frame to file.
            if((saved_count["stream_" + str(frame_meta.pad_index)] % 30 == 0) and (obj_meta.confidence > 0.3 and obj_meta.confidence < 0.31)):
                if is_first_obj:
                    is_first_obj = False
                    # Getting Image data using nvbufsurface
                    # the input should be address of buffer and batch_id
                    n_frame = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
                    # convert python array into numy array format.
                    frame_image = np.array(n_frame, copy=True, order='C')
                    # covert the array into cv2 default color format
                    frame_image = cv2.cvtColor(frame_image, cv2.COLOR_RGBA2BGRA)

                save_image = True
                frame_image = draw_bounding_boxes(frame_image, obj_meta, obj_meta.confidence)
            try:
                l_obj = l_obj.next
            except StopIteration:
                break

        print("Frame Number=", frame_number, "Number of Objects=", num_rects, "Vehicle_count=", obj_counter[PGIE_CLASS_ID_VEHICLE], "Person_count=", obj_counter[PGIE_CLASS_ID_PERSON])
        # Get frame rate through this probe
        fps_streams["stream{0}".format(frame_meta.pad_index)].get_fps()
        if save_image:
            cv2.imwrite(folder_name + "/stream_" + str(frame_meta.pad_index) + "/frame_" + str(frame_number) + ".jpg", frame_image)
        saved_count["stream_" + str(frame_meta.pad_index)] += 1
        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    return Gst.PadProbeReturn.OK


def draw_bounding_boxes(image, obj_meta, confidence):
    confidence = '{0:.2f}'.format(confidence)
    rect_params = obj_meta.rect_params
    top = int(rect_params.top)
    left = int(rect_params.left)
    width = int(rect_params.width)
    height = int(rect_params.height)
    obj_name = pgie_classes_str[obj_meta.class_id]
    image = cv2.rectangle(image, (left, top), (left + width, top + height), (0, 0, 255, 0), 2)
    # Note that on some systems cv2.putText erroneously draws horizontal lines across the image
    image = cv2.putText(image, obj_name + ',C=' + str(confidence), (left - 10, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255, 0), 2)
    return image
