#!/usr/bin/python
# -*- coding: UTF-8 -*-
import csv
import os
import numpy as np
import os
import glob
import sys
import SimpleITK as sitk

'''
This script processes the .mha data by splitting it into Sagittal and Coronal files
so that it can displayed in 3d slicer more easily
'''

TranslationsFileName = "Transforms"
SegmentationFileName = "Segmentation"
Volume3DFileName = "Volume3D"

def RetrieveOrientation(direct):
    """Find the orientation of each image"""
    orientation = "oblique"
    if (round(abs(direct[2])) == 1):
        orientation = "Sagittal"
    elif (round(abs(direct[5])) == 1):
        orientation = "Coronal"
    else:# elif (round(abs(direct[8])) == 1):
        orientation = "Transverse"
    return orientation

def WriteCommonOrientationSlices(slices, orientation, outPathBase):
    """writes the separate orientations out to the output folder"""
    img_number = 10000
    for iterating_sli in slices:
        output_filename = outPathBase + "_" + orientation + "_" + str(img_number) + ".mha"
        sitk.WriteImage(iterating_sli, output_filename)
        img_number = img_number + 1
    return

def ListImages(imagePathName):
    """Find all the moving images in the 'movingFolder' folder"""
    types = ["*.dcm", "*.mha"]
    imageFiles = []
    for type in types:
        this_type_files = glob.glob(imagePathName + '\\' + type, recursive = True)
        imageFiles += this_type_files
    if len(imageFiles) == 0:
        print(imagePathName + " is empty")
        sys.exit(1)
    return imageFiles

def Mkpath(path):
    """Creates a folder if it does not already exist"""
    if not os.path.exists(path):
        os.makedirs(path)

def ImgProcessing(cine2DPathName, maskPathName, CsvPath):
    """Splits the .mha files into each of the orientations and writes them to an output file"""

    # Read tracking log, mask and list cine images
    mask3D = sitk.ReadImage(maskPathName, sitk.sitkUInt32)
    cineFiles = ListImages(cine2DPathName)
    outpath = cine2DPathName+"/output"
    
    print('processing: ', outpath)
    Mkpath(outpath)
    outSegPathName = outpath + "\\seg"
    outImgPathName = outpath + "\\img"
    
    # output images
    Output = {
        'Coronal': {
            'Seg': [],
            'Img': []
        },
        'Sagittal': {
            'Seg': [],
            'Img': []
        },
        'Transverse': {
            'Seg': [],
            'Img': []
        }
    }

    with open(CsvPath, 'r') as read_transforms:
        csv_reader = csv.reader(read_transforms)

        #discard the names for the columns
        header = next(csv_reader)

        for imgIterator, row in enumerate(csv_reader):
            print("image:", imgIterator)
            moving = sitk.ReadImage(cineFiles[imgIterator], sitk.sitkFloat32)
            directionSlice = moving.GetDirection()
            orientation = RetrieveOrientation(directionSlice)
            if orientation in Output:
                affine_transform = sitk.AffineTransform(3)
                affine_transform.Translate([float(row[0]), float(row[1]), float(row[2])])
                imageOut = sitk.Resample(mask3D, moving, affine_transform.GetInverse())
                Output[orientation]['Seg'].append(imageOut)
                Output[orientation]['Img'].append(moving)

    for orientation in Output:
        WriteCommonOrientationSlices(Output[orientation]['Seg'], orientation, outSegPathName)
        WriteCommonOrientationSlices(Output[orientation]['Img'], orientation, outImgPathName)
    return outpath

def ProTry(input_path, force: bool = False):
    outpath = input_path+"/output"
    if os.path.exists(outpath) and not force: return
    translations_path = ''
    segmentation_path = ''
    for s in os.listdir(input_path):
        s_path = os.path.join(input_path, s)
        if os.path.isdir(s_path):
            continue
        elif os.path.isfile(s_path) and SegmentationFileName in s:
            segmentation_path = s_path
        elif os.path.isfile(s_path) and TranslationsFileName in s:
            translations_path = s_path
    outpath = ImgProcessing(input_path, segmentation_path, translations_path)
    return outpath