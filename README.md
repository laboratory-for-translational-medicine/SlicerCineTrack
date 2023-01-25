## SlicerTrack

SlicerTrack is a 3D Slicer extension designed for easy target tracking of a ROI as it moves through a set of time-series medical images.

DISCLAIMER: This software is not intended for clinical use.

### Directory Tree Description

`Track`

* Main SlicerTrack module directory

`TrackingDataProcessor`

* Legacy target tracking implementation in C++

`Track/Data`

* Sample medical image data to be used with SlicerTrack

`Tack/Resources`

* Holds various resource files that may be used by SlicerTrack

### Quick Setup Instructions

1) To access the module within your 3D Slicer installation you must first make the module available to 3D Slicer. Open 3D Slicer and click:

   `Edit` -> `Application Settings` -> `Modules`

   Now add the path to the `Track` folder within the `Additional module paths` selection box
   - Hint: Click on the `>>` button to show the `Add` button
   - Ensure to add the path to `SlicerTrack/Track`
   - After the path is added, the program will restart
2) Reopen 3D Slicer and click on the module selection dropdown menu and find the SlicerTrack module under:

   `Tracking` -> `Track`

3) Use the input selectors to import the sample data from the `Track/Data` folder:
   - 2D Images Folder : `Track/Data`
   - 3D Segmentation File : `Track/Data/Segmentation.mha`
   - Transforms File : `Track/Data/Transforms.csv`
4) Press the `Play` button to begin playback

### Extension Development

See the [dev wiki](https://github.com/laboratory-for-translational-medicine/SlicerTrack/wiki/SlicerTrack-Development-Guide) for SlicerTrack development information.
