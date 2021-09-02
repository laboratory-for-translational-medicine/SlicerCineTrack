# Development instructions

## Requirements
* Visual Studio 2019 with basic C++ Development packages
* vcpkg: https://github.com/hexthedev-forks/vcpkg
* ITK 5.1 installed using vcpkg

## Setup
Once the above three steps have been completed you should be able to open ./TrackingDataProcessor.sln

The solution won't build unless the include directories are set to your vcpkg/packages folder.

In VisualStudio
1) Right click the project
2) Go to C++ -> Include Directories
3) Add the path to your vcpkg/packages folder

You should now be able to build the project. Make sure to build Release/x64

## Using the project
An .exe will be built to the Release folder. Use the .exe using the command described in ../README.md