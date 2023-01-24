## SlicerTrack

SlicerTrack is an 3D Slicer extension designed for easy target tracking of a ROI as it moves through a set of time-series medical images.

DISCLAIMER: This software is not intended for clinical use.

#### Directory Tree Description

`Track`

`TrackingDataProcessor`

`Track/Data`

`Tack/Resources`

#### Quick Setup Instructions

1) to load the module, go to `Edit`->`Application settings`->`Modules` and add the path in the additional modules path (click on the `>>` arrow to show the add button).
   -Ensure to add the path: `/.../SlicerTrack/Track`
   -After the path is added, the program will restart.
2) On the home page, select the module by going clicking on `modules list`->`Tracking`->`Track`
3) Now select the data folder in the `Tracking Folder` input box. This should load the data into sequences and show them in the Red, Green and Yellow Slice visualizers.
   * You can select the `Data` folder in the `Track` folder of this repo

#### Extension Development

See [dev wiki](https://github.com/laboratory-for-translational-medicine/SlicerTrack/wiki/SlicerTrack-Development-Guide) for SlicerTrack development information.
