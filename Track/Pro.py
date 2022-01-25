#!/usr/bin/python
# -*- coding: UTF-8 -*-
import csv
import os
import numpy as np
import os
import glob
import sys
import SimpleITK as sitk
TranslationsFileName = "Transforms"
SegmentationFileName = "Segmentation"
Volume3DFileName = "Volume3D"

def RetrieveOrientation(direct):
    # Find the orientation of each image
    orientation = "oblique"
    if (round(abs(direct[2])) == 1):
        orientation = "Sagittal"
    elif (round(abs(direct[5])) == 1):
        orientation = "Coronal"
    elif (round(abs(direct[8])) == 1):
        orientation = "Axial"
    return orientation

def WriteCommonOrientationSlices(slices, direct, outPathBase):
    orientation = direct
    img_number = 10000
    for iterating_sli in slices:
        output_filename = outPathBase + "_" + orientation + "_" + str(img_number) + ".mha"
        sitk.WriteImage(iterating_sli, output_filename)
        img_number = img_number + 1
    return

def ListImages(imagePathName):
    # Find all the moving images in the 'movingFolder' folder
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
    folder = os.path.exists(path)
    if not folder:
        os.makedirs(path)
    return

def ImgProcessing(cine2DPathName, maskPathName, CsvPath):
    # Read tracking log, mask and list cine images
    mask3D = sitk.ReadImage(maskPathName, sitk.sitkUInt32)
    cineFiles = ListImages(cine2DPathName)
    outpath = cine2DPathName + "output"
    Mkpath(outpath)
    outSegPathName = outpath + "\\seg"
    outImgPathName = outpath + "\\img"
    # output images
    coronalSegImageList = []
    sagittalSegImageList = []
    coronalImgImageList = []
    sagittalImgImageList = []
    with open(CsvPath, 'r') as read_transforms:
        csv_reader = csv.reader(read_transforms)
        header = next(csv_reader)
        imgIterator = 0
        for row in csv_reader:
            print("image:", imgIterator)
            moving = sitk.ReadImage(cineFiles[imgIterator], sitk.sitkFloat32)
            directionSlice = moving.GetDirection()
            orientation = RetrieveOrientation(directionSlice)
            if (orientation == "Coronal") or (orientation == "Sagittal"):
                # If this is the first time this orientation is met:
                # if (len(coronalSegImageList) == 0) and (orientation == "Coronal"):
                #     coronalDirection = directionSlice
                # if (len(sagittalSegImageList) == 0) and (orientation == "Sagittal"):
                #     sagittalDirection = directionSlice
                if (orientation == "Coronal"):
                    affine_transform = sitk.AffineTransform(3)
                    affine_transform.Translate([float(row[0]), float(row[1]), float(row[2])])
                    #params = affine_transform.GetParameters()
                    #affine_transform.SetParameters()
                    imageOut = sitk.Resample(mask3D, moving, affine_transform.GetInverse())
                    coronalSegImageList.append(imageOut)
                    coronalImgImageList.append(moving)
                elif (orientation == "Sagittal"):
                    affine_transform = sitk.AffineTransform(3)
                    affine_transform.Translate([float(row[0]), float(row[1]), float(row[2])])
                    #params = affine_transform.GetParameters()
                    #affine_transform.SetParameters()
                    imageOut = sitk.Resample(mask3D, moving, affine_transform.GetInverse())
                    sagittalSegImageList.append(imageOut)
                    sagittalImgImageList.append(moving)
            imgIterator = imgIterator + 1
    WriteCommonOrientationSlices(coronalSegImageList, "Coronal", outSegPathName)
    WriteCommonOrientationSlices(sagittalSegImageList, "Sagittal", outSegPathName)
    WriteCommonOrientationSlices(coronalImgImageList, "Coronal", outImgPathName)
    WriteCommonOrientationSlices(sagittalImgImageList, "Sagittal", outImgPathName)
    return outpath

def ProTry(input_path):
    #image_paths = []
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
        elif os.path.isfile(s_path) and Volume3DFileName in s:
            continue
        else:
            #image_paths.append(s_path)
            continue
    outpath = ImgProcessing(input_path, segmentation_path, translations_path)
    return outpath

if __name__ == '__main__':
    #input_path = "D:\\AWorkSpace\\SlicerTrack\\Track\\def1.trackpackage\\"
    #ProTry(input_path)
    dicomDataDir = "D:\AWorkSpace\SlicerTrack\Track\def1.trackpackage\output"  # input folder with DICOM files
    pathlist = sorted(os.listdir(dicomDataDir))
    print(pathlist)
