"""
    The file content function to build the part of pipeline concerned source 

"""
import sys
import io
import os 

sys.path.append(os.path.abspath(os.curdir))



import gi
gi.require_version("Gst","1.0")

from gi.repository import Gst



def cis_camera_source(path_camera):
    print(f"Creating  Source for  and CIS Camera wiht the path {path_camera}")

    source_cis = Gst.ElementFactory.make("nvarguscamerasrc", "src-elem")
    if not source_cis:
        sys.stderr.write(" Unable to create Source \n")
    
    print("Creating an convertor to scale the recieved image from camera")
    
    # Converter to scale the image
    nvvidconv_src_cis = Gst.ElementFactory.make("nvvideoconvert", "convertor_src")
    if not nvvidconv_src_cis:
        sys.stderr.write(" Unable to create nvvidconv_src \n")

    print("Create an filter for NVMM and resolution scaling")

    caps_nvvidconv_src_cis = Gst.ElementFactory.make("capsfilter", "nvmm_caps")
    if not caps_nvvidconv_src_cis:
        sys.stderr.write(" Unable to create capsfilter \n")

    ## Setting 
    source_cis.set_property('bufapi-version', True)

    caps_nvvidconv_src_cis.set_property('caps', Gst.Caps.from_string('video/x-raw(memory:NVMM), width=1280, height=720'))

    print("elements for source was created and setted!")

    return [source_cis,nvvidconv_src_cis,caps_nvvidconv_src_cis]





if __name__ == "__main__":
    Print
    print(os.curdir)

