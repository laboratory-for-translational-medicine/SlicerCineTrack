# SlicerTrack
This repo contains resources used to develop an extension for 3DSlicer that allows for easy visualization of tracking data. 

DISCLAIMER: This software is not intended for clinical use.

## Components
Currently, there are two components that make up the slicer extension. 
* ~~TrackingDataProcessor C++ Console App~~  
    * the module provides this functionality already
* Track 3D Slicer Python Extension

## usage 
1) to load the module, go to `Edit`->`Application settings`->`Modules` and add the path in the additional modules path (click on the `>>` arrow to show the add button).
    -Ensure to add the path: `/.../SlicerTrack/Track`
    -After the path is added, the program will restart.
2) On the home page, select the module by going clicking on `modules list`->`Tracking`->`Track`
3) Now select the data folder in the `Tracking Folder` input box. This should load the data into sequences and show them in the Red, Green and Yellow Slice visualizers.
    * You can select the `Data` folder in the `Track` folder of this repo

## Development (3DSlicer Extension)
See Track/README.md for development instructions