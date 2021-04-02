# Deepstream python custom Model
This poject run Deepstream SDK V 5.1 to inference native Tensorflow using triton inference server. As input we I use an rasberry .py camera and output will be render as RTSP.

## Requirement
    
Backend Server runnig Apache Kafka to receive. you can use this [tutorial](./documentations/Apach_Kafk_on_ubuntu.md)  

Before using this repo make sure you are already install DeepStream SDK following. you can use this [tutorail](./documentations/Prepare_Jetson_Nano_for_Edge_Computing.md)

Once its done, change the path of kafka library and of the path Custompaerser. Each model confguration file into [configuration](./configurations/configuration.py) direction content parameter `custom path` make sure the point to `/opt/nvidia/deepstream/deepstream-5.1/lib/libnvds_infercustomparser.so` which should corepond to installation dirctory of DeepStream respectivly. Also have to set the path of `libnvds_kafka_proto`, to do that change the parameter `BROKER_CONF['proto_lib']` in to the [configuration](./configurations/configuration.py) file.



## Running Pre-configurate Model

    python run.py --model [pre-configurate model name] --input [/dev/video0]

**Parameters**

- `--model` Give the of the model you wont to inference with. the both inerence have already pre-configured model setting.
    - TensorRT `['resnet10','custom']`
    - Trinton Inference Server `['yolov3', 'ssd_inceptionv2', 'custom']`
    - choose `custom` to run the inference methode with you own model.

- `--input` to give the input path of Raspberry camera. the default has already been setted in to [the run configuration file](/configurations/configuration.py).
- `birate` and `codec` can also be configurate in the same file.

## Done
- [x] Parser Freezed tensorflow model and apply inference using triton inference server
- [x] build pipeline that parser the on-Screnn Display objet and extract somme frame.
- [x] send Information to the Server using Apache kafta
- [x] Stream OSD as RTSP link
## To Do
- [] Save video localy
- []  Add Instance segmentaion model

