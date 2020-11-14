# Deepstream python custom Model
This poject run Deepstream SDK V 5.0 to inference native Tensorflow using triton inference server. As input we I use an rasberry .py camera and output will be render as RTSP.



## Running Pre-configurate Model

    python run.py [--tritis] --model [pre-configurate model name] --input [/dev/video0]

**Parameters**
- `--tritis` set Tinton inference server on treu. The default Inference methode is TRT. by default the inference will done with TensorRT not with Trinton.
- `--model` Give the of the model you wont to inference with. the both inerence have already pre-configured model setting.
    - TensorRT `['resnet10','custom']`
    - Trinton Inference Server `['yolov3', 'ssd_inceptionv2', 'custom']`
    - choose `custom` to run the inference methode with you own model.

- `--input` to give the input path of Raspberry camera. the default has already been setted in to [the run configuration file](/configurations/configuration.py).
- `birate` and `codec` can also be configurate in the same file.
