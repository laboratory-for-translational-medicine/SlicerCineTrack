# SlicerTrack

SlicerTrack is a 3D Slicer extension designed for the visual verification of target tracking results. The ROI segmentation is resampled according to user-provided transformation data and overlaid on a set of time-series medical images.

DISCLAIMER: This software is not intended for clinical use.

## What can SlicerTrack do?

Please take a look at [documentation page](https://slicertrack.github.io/Documentation) on SlicerTrack's Homepage.
Here is a little demo

![Track.gif](https://github.com/slicertrack/slicertrack.github.io/blob/603168b23fd5b0adb6c4a1a495d314b104a438f1/resources/screenshots/Track.gif?raw=true)

## Directory Tree Description

`Track`

* Main SlicerTrack module directory

`Track/Resources`

* Holds various resource files that may be used by SlicerTrack like Icon and UI elements

## Quick Setup Instructions for developer

If you want to clone this demo and make it work with 3D Slicer software, please follow steps below

1) To access the module within your 3D Slicer installation you must first make the module available to 3D Slicer. Open 3D Slicer and click:

`Edit` -> `Application Settings` -> `Modules`

Now add the path to the `Track` folder within the `Additional module paths` selection box

* Hint: Click on the `>>` button to show the `Add` button
* Ensure to add the path to `SlicerTrack/Track`
* After the path is added, the program will restart

2) Reopen 3D Slicer and click on the module selection dropdown menu and find the SlicerTrack module under:

   `SlicerTrack` -> `Track`

3) Download sample dataset
   You can use 2 datasets below:

   * [Dataset 1](https://github.com/laboratory-for-translational-medicine/SlicerTrack/releases/download/v.1.0.0-slicertrack/Data.zip)
   * [Dataset 2](https://drive.google.com/drive/folders/1qJj53YfGM4Q7atsI-XZyySvR-F98ENXA?usp=sharing)

4) Unzip the data into folder `Track/Data`
5) Use the input selectors to import the sample data from the `Track/Data` folder:

   * Cine Images Folder : `Track/Data`
   * Segmentation File : `Track/Data/Segmentation.mha`
   * Transforms File : `Track/Data/Transforms.csv`

6) Press the `Play` button to begin playback

### Extension Development

See the [dev wiki](https://github.com/laboratory-for-translational-medicine/SlicerTrack/wiki/SlicerTrack-Development-Guide) for SlicerTrack development information.
