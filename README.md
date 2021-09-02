# SlicerTrack
This repo contains resources used to develop an extension for 3DSlicer that allows for easy visualization of tracking data. 

DISCLAIMER: This software is not intended for clinical use.

## Components
Currently, there are two components that make up the slicer extension. 
* TrackingDataProcessor C++ Console App
* Track 3D Slicer Python Extension

### TrackingDataProcessor
The TrackingDataProcessor is used to process data using ITK and output a series of images that can be easily loaded as a 3DSlicer Sequence. 

See TrackingDataProcessor/README.md for development instructions. 

Once built, the TrackingDataProcessor.exe can be used to process tracking data. 

`./TrackingDataProcessor.exe path/to/trackingDataFolder.trackpackage`

The tracking data folder should have the following layout:

```
<name>.trackpackage
-> 00001.mha
-> 00002.mha
-> ...              // up to image n
-> Segmentation.mha // 3D volume
-> Transforms.csv   // containing n X,Y,Z data points
```

The output will be in the same folder as the original, with the following layout
```
<name>.trackpackage_output
-> img_Coronal_0.mha
-> img_Coronal_1.mha
-> ...
-> img_Saggital_0.mha
-> img_Saggital_1.mha
-> ...
-> img_Axial_0.mha
-> img_Axial_1.mha
-> ...
-> seg_Coronal_0.mha
-> seg_Coronal_1.mha
-> ...
-> seg_Saggital_0.mha
-> seg_Saggital_1.mha
-> ...
-> seg_Axial_0.mha
-> seg_Axial_1.mha
```

All orientations may not be present, it depends on the orientations of the n images provided.

### 3DSlicer Extension
See Track/README.md for development instructions. 

Once SlicerTrack is added as an extension to your version of 3DSlicer, you can use the extension to visualize the _output data described above. 

To do so:
1) From 3DSlicer data view, add all the files from the _couput folder to the scene
2) Go to the track module in 3DSlicer, this should be loaded if the development instructions were followed correctly
3) Click the `OrganizeData` button. This should load the data into sequences and show them in the Red, Green and Yellow Slice visualizers.