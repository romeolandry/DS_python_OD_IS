#  Prepare Jetson Nano for Nvidia-DeepStream-SDK  Raspberry and RTSP as Render Canal.

## Prepare the Jetson Nano dev-Kit

- Flash you SD Card as mentioned on the [Nvidia web page](https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit).

- Setup Cuda environment variable

     ```shell
     $ sudo vi ~/.bashrc
     ### add the following line at the end of the file
     export CUDA_HOME=/usr/local/cuda
     export PATH = $CUDA_HOME/bin:$PATH
     export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
     ## save and exit 
     ## reload bashrc
     source ~/.bashr
     ```
     
- To boost the clocks

  ```shell
  # select the power options mode: 5w is the mode 1 and 10w is the mode 0  
  $ sudo nvpmodel -m 1 # To use the Maximun power available
  # force the mode by running jetson_clocks
  $ sudo jetson_clocks
  ```


- **Create swap file** its necessary because Jetson Nano just allocate `~1 GB`for Swap and `4GB` as memory whom is not sufficient.  I add `8GB` to increase the swap partition

  ```shell
  $ sudo fallocate -l 8GB /mnt/8GB.swap
  $ sudo mkswap /mnt/8GB.swap
  $ sudo swapon 8GB /mnt/8GB.swap
  # add the new partiton in to etc/fstab so that it will be monted on boot
  $ sudo bash -c 'echo "/mnt/8GB.swap  none  swap  sw 0  0" >> /etc/fstab'
  ```

  

- Remove `LibreOffice` to get mode space 

  ```shell
  $ sudo apt-get purge libreoffice*
  $ sudo apt-get clean
  ```

At this Level its possible to continue using an SSH-Connection . From client connect to Jetson with 

```shell
$ ssh [username]@[jetsonIP]
```

```shell
$ whoami # show user name
$ ifconfig # show Ip
```

## Install DeepStream SDK on Jetson Nano

For more explanation please read [nvidia Deepstream API](https://docs.nvidia.com/metropolis/deepstream/dev-guide/index.html#page/DeepStream_Development_Guide/deepstream_quick_start.html#wwpID0E0GI0HA)

- Install prerequisite package

  ```shell
  $ sudo apt install \
      libssl1.0.0 \
      libgstreamer1.0-0 \
      gstreamer1.0-tools \
      gstreamer1.0-plugins-good \
      gstreamer1.0-plugins-bad \
      gstreamer1.0-plugins-ugly \
      gstreamer1.0-libav \
      libgstrtspserver-1.0-0 \
      libjansson4=2.11-1
  ```

- Install DeepStream `apt-server`

  1. Open the apt source configuration file in a text editor, for example:	

  ```shell
  $ sudo nano /etc/apt/sources.list.d/nvidia-l4t-apt-source.list
  ```

  2. Change the repository name and download URL in the deb commands shown below:

     deb https://repo.download.nvidia.com/jetson/common r32.5 main

     deb https://repo.download.nvidia.com/jetson/<platform> r32.5 main

  ```shell
  $ sudo apt update
  $ sudo apt install deepstream-5.x
  ```

- Install `librdkafka` (to enable Kafka protocol adapter for message broker)

  1- clone librdkafka repository from GitHub

  ```shell
  $ git clone https://github.com/edenhill/librdkafka.git
  ```

  2- Configure and build the library

  ```shell
  $ cd librdkafka
  $ git reset --hard 7101c2310341ab3f4675fc565f64f0967e135a6a
  $ ./configure
  $ make
  $ sudo make install
  ```

  Install additional dependencies

  ```shell
  $ sudo apt-get install libglib2.0 libglib2.0-dev
  $ sudo apt-get install gir1.2-gst-rtsp-server-1.0
  ```
  

3- Copy the generated libraries to the DeepStream directory

DeepStream-5.x: 5.x is version you wont to install.  **recommended** [More about this realese](https://docs.nvidia.com/metropolis/deepstream/DeepStream_5.0_Release_Notes.pdf)

```shell
  $ sudo cp /usr/local/lib/librdkafka* /opt/nvidia/deepstream/deepstream-5.x/lib
```

## Python Bindings

After install DeepStream and make all required configuration install Python Bindings to run deepStream python application.

```shell
$ sudo apt-get install python-gi-dev
$ export GST_LIBS="-lgstreamer-1.0 -lgobject-2.0 -lglib-2.0"
$ export GST_CFLAGS="-pthread -I/usr/include/gstreamer-1.0 -I/usr/include/glib-2.0 -I/usr/lib/x86_64-linux-gnu/glib-2.0/include"
$ git clone https://github.com/GStreamer/gst-python.git
$ cd gst-python
$ git checkout 1a8f48a
$ ./autogen.sh PYTHON=python3
$ ./configure PYTHON=python3
$ make
$ sudo make install


##  Configure Python

- **Installing system package prerequisites.**

  ```shell
  $ sudo apt-get install git cmake
  $ sudo apt-get install libatlas-base-dev gfortran
  $ sudo apt-get install libhdf5-serial-dev hdf5-tools
  $ sudo apt-get install python3-dev
  ```

  Some python library required 3.x x > 7 [Build python](https://arcanesciencelab.wordpress.com/2020/05/24/building-python-3-8-3-on-jetpack-4-4-dp-and-the-jetson-xavier-nx/)

- **Use virtual environments(optional) **

  ```shell
  ## Install pip
  $ sudo apt install python3-pip
  ```
  

To manage our Python virtual environment we use `virtualenv and virtualenvwrapper`

```
  sudo pip install virtualenv virtualenvwrapper
```

configure the `~/.bashrc` to use `virtualenvWrapper` command such as   `workon`

run `nan ~/.bashrc` and at the end of line put

```
  # virtualenv and virtualenvwrapper
  export WORKON_HOME=$HOME/.virtualenvs
  export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
  source /usr/local/bin/virtualenvwrapper.sh
```

reload the contents of the ~/.bashrc 

```
  source ~/.bashrc
```

**NOTE**: If you decide to use Environment make sure you install python3-gi into all  created environment with `vext` otherwise you will have `no module name gi` running `GST-Python`

```
  ## in to ENV
  pip install vext
  pip install vext.gi
  ## without ENV 
  sudo apt install python3-gi
```

- **Setting up Jupyter Notebook** (Optional)

  Create a EV with `mkvirtualenv [envename] -p python[version]'`. the created EV will be activated after the creation

  **Note** install wheel in every crated Environment with `pip install wheel`

  - **Install Jupyter**

  ```
  pip3 install jupyter
  ```

  - **run Jupyter Notebook through SSH**

    We recommend using your own computer’s browser for accessing Jupyter  notebooks on the Nano. Running the browser on the Jetson requires  resources that would better be allocated to the actual deep learning  part. To access the Jupyter server on the Jetson, we use SSH tunneling.  The command for SSH tunneling works in Ubuntu, macOS, and Windows 10  (post the April 2018 update). Run it **on your own desktop or laptop** in a new terminal that **you must leave open** (alternatively exit the current SSH session by pressing Ctrl+D):

    ```
    ## On your Laptop or Desktop
    ssh -L 8000:localhost:8888 [Username]@IP_JetsonNano
    ```

    Start the Jupyter server on the Jetson with `jupyter notebook`, then go to http://localhost:8000 **on your own computer**. You should be greeted by a page with the Jupyter logo and a field that asks for a token or a password. You can [read about how to use passwords](https://jupyter-notebook.readthedocs.io/en/stable/public_server.html) but for the sake of brevity we'll use tokens here. The token is all that comes after `http://localhost:8888/?token=`. Copy paste it in the browser and you should be good to go!

- Tensorflow official [documentation](https://docs.nvidia.com/deeplearning/frameworks/install-tf-jetson-platform/index.html)

  

## CIS-Camera Raspberry Pi

DeepStream first check if Raspberry Pi is worked

```
$ ls /dev/video0 # to list availabel
```

Test the camera

```
gst-launch-1.0 nvarguscamerasrc sensor_mode=0 ! 'video/x-raw(memory:NVMM),width=3820, height=2464, framerate=21/1, format=NV12' ! nvvidconv flip-method=0 ! 'video/x-raw,width=960, height=616' ! nvvidconv ! nvegltransform ! nveglglessink -e
```

More about camera on Jetson Nano [see](https://github.com/JetsonHacksNano/CSI-Camera).

## Issues

- By building TensorRT OSS

  - *CMAKE_CUDA_COMPILER*

    Set path to CUDACXX into `/etc/environement` so that cmake cloud see cuda as cmake can't not access to `~/.bashrc`.

    ```
    ## add at the end of file
    CUDACXX="[Path to nvcc]" e.g /usr/local/cuda-10.1/bin/nvcc
    ```

- Cv2: Cannot allocate memory in static TLS block: run the following command before running the script 

  ```shell
  $ export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1
  ```

  

- If the application encounters errors and cannot create Gst elements,  remove the GStreamer cache, then try again. To remove the GStreamer  cache, enter this command:

  ```shell
  $ rm ${HOME}/.cache/gstreamer-1.0/registry.aarch64.bin
  ```

  