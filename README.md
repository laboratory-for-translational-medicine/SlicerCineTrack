# SlicerCineTrack

Main: [![main branch](https://github.com/laboratory-for-translational-medicine/SlicerCineTrack/actions/workflows/build-test.yml/badge.svg?branch=main)](https://github.com/laboratory-for-translational-medicine/SlicerCineTrack/actions/workflows/build-test.yml) 

Dev:  [![dev branch](https://github.com/laboratory-for-translational-medicine/SlicerCineTrack/actions/workflows/build-test.yml/badge.svg?branch=dev)](https://github.com/laboratory-for-translational-medicine/SlicerCineTrack/actions/workflows/build-test.yml)

SlicerCineTrack is a 3D Slicer extension designed for the visual verification of target tracking results. The ROI segmentation is resampled according to user-provided transformation data and overlaid on a set of time-series medical images.

**DISCLAIMER**: This software is not intended for clinical use.

## What can SlicerCineTrack do?

Please take a look at [documentation page](https://slicercinetrack.github.io/Documentation) on SlicerCineTrack's Homepage.
<!-- Here is a little demo

![Track.gif](https://github.com/slicercinetrack/slicercinetrack.github.io/blob/603168b23fd5b0adb6c4a1a495d314b104a438f1/resources/screenshots/Track.gif?raw=true) -->

## Directory Tree Description

`Track`

* Main SlicerCineTrack module directory

`Track/Resources`

* Holds various resource files that may be used by SlicerCineTrack like Icon and UI elements

## Setup Instructions

The video below demonstrates sample usage and behaviour of SlicerCineTrack. This demo can also be performed locally, using the provided steps and dataset below.



[!SlicerCineTrackTutorial.mp4](https://github.com/user-attachments/assets/d72f8d53-ca74-4ec4-a0d0-8e7131de3a62)



1) Install the "SlicerCineTrack" extension from the 3D Slicer extension manager

2) Reopen 3D Slicer and click on the module selection dropdown menu and find the SlicerCineTrack module under:

   `SlicerCineTrack` -> `Track`

3) Download a sample dataset
   You can use either of the 2 datasets below:

   * [Dataset 1](https://github.com/laboratory-for-translational-medicine/SlicerCineTrack/releases/download/v1.0.0-SlicerCineTrack/Data.zip)
   * [Dataset 2](https://drive.google.com/drive/folders/1qJj53YfGM4Q7atsI-XZyySvR-F98ENXA?usp=sharing)

4) Unzip the data into folder `Track/Data`
5) Use the input selectors to import the sample data from the `Track/Data` folder:

   * Cine Images : `Track/Data/2D Cine Images`
   * Segmentation File : `Track/Data/Segmentation.mha`
   * Transforms File : `Track/Data/Transforms.csv`

6) Press the `Play` button to begin playback 

## Using the Preview Release of SlicerCineTrack for Development

1) Navigate to the desired location and clone this repository using: 
   ```
   git clone https://github.com/laboratory-for-translational-medicine/SlicerCineTrack.git
   ```
   Ensure that the branch is set to the `dev` branch, as it contains the latest changes.

2) To access the module within your 3D Slicer installation you must first make the module available to 3D Slicer. Open 3D Slicer and click:

   `Edit` -> `Application Settings` -> `Modules`

   Now add the path to the `Track` folder within the `Additional module paths` selection box

* Hint: Click on the `>>` button to show the `Add` button
* Ensure to add the path to `SlicerCineTrack/Track`
* After the path is added, the program will restart

### Extension Development

See the [dev wiki](https://github.com/laboratory-for-translational-medicine/SlicerCineTrack/wiki/SlicerCineTrack-Development-Guide) for SlicerCineTrack development information.
