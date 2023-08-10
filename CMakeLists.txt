cmake_minimum_required(VERSION 3.13.4)

project(SlicerTrack)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://slicertrack.github.io/")
set(EXTENSION_CATEGORY "Tracking")
set(EXTENSION_CONTRIBUTORS "HaPhan Tran (laboratory-for-translational-medicine), \
                            Mubariz Afzal (laboratory-for-translational-medicine) \
                            James McCafferty (laboratory-for-translational-medicine), \
                            Teo Mesrkhani ((laboratory-for-translational-medicine)")
set(EXTENSION_DESCRIPTION "Module providing tracking tools and displacement visualizations")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/Track.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/Track/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(Track)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
