cmake_minimum_required(VERSION 3.13.4)

project(SlicerTrack)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://slicertrack.github.io/")
set(EXTENSION_CATEGORY "SlicerTrack")
set(EXTENSION_CONTRIBUTORS "Elodie Lugez (Toronto Metropolitan University), \
                            HaPhan Tran (Toronto Metropolitan University), \
                            Fabyan Mikhael (Toronto Metropolitan University), \
                            Mubariz Afzal (Toronto Metropolitan University), \
                            Teo Mesrkhani (Toronto Metropolitan University), \
                            Jacqueline Banh (Toronto Metropolitan University), \
                            Nicholas Caro Lopez (Toronto Metropolitan University), \
                            Venkat Guru Prasad (Toronto Metropolitan University), \
                            Sayeed Jalil (Toronto Metropolitan University)")
set(EXTENSION_DESCRIPTION "Module providing tracking tools and displacement visualizations")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/slicertrack/slicertrack.github.io/main/resources/SlicerTrack_logo.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/slicertrack/slicertrack.github.io/main/resources/screenshots/ST_Document1.png https://raw.githubusercontent.com/slicertrack/slicertrack.github.io/main/resources/screenshots/ST_Document2.png https://raw.githubusercontent.com/slicertrack/slicertrack.github.io/main/resources/screenshots/ST_Document3.png https://raw.githubusercontent.com/slicertrack/slicertrack.github.io/main/resources/screenshots/ST_Document5.png")
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
