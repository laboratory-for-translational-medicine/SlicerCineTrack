"""
==============================================================================

  Copyright (c) 2024, laboratory-for-translational-medicine
  Toronto Metropolitan University, Toronto, ON, Canada. All Rights Reserved.

  See LICENSE.txt
  or http://www.slicer.org/copyright/copyright.txt for details.

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.


==============================================================================
"""


import os
import csv
import re
import numpy as np
import functools

import ctk
import qt
import vtk
import SimpleITK as sitk

import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import *
from slicer import vtkMRMLSequenceNode
from slicer import vtkMRMLSequenceBrowserNode
from utils.Helper import SpinBox, Slider
from utils.TrackLogic import TrackLogic
from typing import List
from slicer.util import arrayFromVolume, updateVolumeFromArray


#
# Track
#


class Track(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Track"
    self.parent.categories = ["Sequences"]
    self.parent.dependencies = []
    self.parent.contributors = ["Elodie Lugez ",
                                "James McCafferty ",
                                "Fabyan Mikhael ",
                                "HaPhan Tran ",
                                "Mubariz Afzal ",
                                "Teo Mesrkhani ",
                                "Jacqueline Banh ",
                                "Nicholas Caro Lopez ",
                                "Venkat Guru Prasad ",
                                "Homa Ahmadinoori "
                                ]
    self.parent.helpText = """From the input dropdown, select valid 2D cine images in the Cine
    Images Folder, a target to track in the 3D Segmentation File, and a transforms file containing information
    about the X,Y,Z coordinates of exactly where the target is. <br> <br>
    For more information see <a href="https://slicercinetrack.github.io/">the online documentation</a>"""
    self.parent.acknowledgementText = """
This extension was developed by the Laboratory for Translational Medicine.
"""

#
# Custom Parameter Node
#


@parameterNodeWrapper
class CustomParameterNode:
  files2DImages: list[str] = []
  sequenceNode2DImages: vtkMRMLSequenceNode
  path3DSegmentation: str
  node3DSegmentation: int  # subject hierarchy id
  files3DSegmentations: list[str] = []
  node3DSegmentationLabelMap: int  # subject hierarchy id
  transformsFilePath: str
  sequenceNodeTransforms: vtkMRMLSequenceNode
  sequenceBrowserNode: vtkMRMLSequenceBrowserNode
  totalImages: int
  fps: float
  opacity: float
  overlayAsOutline: bool
  overlayColor: list[float] = [0.0, 1.0, 0.0] # [r, g, b] values from 0 to 1
  overlayThickness: int = 4
  deformedMaskSequenceNode: vtkMRMLSequenceNode = None


#
# TrackWidget
#


#  this is our module that we will load into 3d slicer

class TrackWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  
    
  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation

    self.logic = None
    self.customParamNode = None
    self._updatingGUIFromParameterNode = False
    self.isDarkMode = None
    self.labelColorButtons = {}
    self._appliedState= None

  def onColumnXSelectorChange(self):
    self.applyTransformButton.enabled = True
    self._appliedState = None
    self.transformationAppliedLabel.setVisible(False)
    
  

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)
    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    # uiWidget.setMRMLScene(slicer.mrmlScene)

    #
    # Begin GUI
    #

    ## Inputs Area

    inputsCollapsibleButton = ctk.ctkCollapsibleButton()
    inputsCollapsibleButton.text = "Inputs"
    self.layout.addWidget(inputsCollapsibleButton)

    # Layout within the dummy collapsible button
    self.inputsFormLayout = qt.QFormLayout(inputsCollapsibleButton)

    iconSize = qt.QSize(24, 19)
    buttonSize = qt.QSize(25, 25)

    # File and folder selectors for our input data
    # 2D time series image data multi file selector
    self.selector2DImagesFiles = ctk.ctkPathListWidget()
    self.selector2DImagesFiles.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed)
    self.selector2DImagesFiles.setMinimumWidth(95)
    self.selector2DImagesFiles.setMaximumHeight(75)

    # Create buttons for browsing and deleting images
    self.deleteImagesButton = qt.QPushButton("X")
    self.deleteImagesButton.setIconSize(iconSize)
    self.deleteImagesButton.setFixedSize(buttonSize)
    self.deleteImagesButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)

    self.browseImagesButton = qt.QPushButton("...")
    self.browseImagesButton.setIconSize(qt.QSize(50, 25))
    self.browseImagesButton.setFixedSize(qt.QSize(26, 21))
    self.browseImagesButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)

    # Spacer for adjusting UI
    spacer = qt.QSpacerItem(10, 25, qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)

    # Create "View More" button for displaying all selected files
    self.mediaIconsPath = os.path.join(os.path.dirname(slicer.util.modulePath(self.__module__)),
                                       'Resources', 'Icons')
    self.viewMoreButton = qt.QPushButton()
    self.viewMoreButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.viewMoreButton.setFixedSize(qt.QSize(28, 26))

    # Initial colour of the icon
    self.updateViewMoreIcon()
    slicer.app.paletteChanged.connect(lambda *args: self.updateViewMoreIcon())


    # Create a layout for the buttons
    self.buttonsLayout = qt.QVBoxLayout()
    self.buttonsLayout.setAlignment(qt.Qt.AlignTop)

    self.buttonsLayout.addSpacerItem(spacer)

    # Create a horizontal layout for X and ... buttons
    self.topButtonsLayout = qt.QHBoxLayout()
    self.topButtonsLayout.addWidget(self.browseImagesButton)
    self.topButtonsLayout.addWidget(self.deleteImagesButton)

    self.buttonsLayout.addLayout(self.topButtonsLayout)

    # Add the "View More" button below
    self.buttonsLayout.addWidget(self.viewMoreButton)
    self.buttonsLayout.setSpacing(3)

    self.selectorImageFilesLayout = qt.QHBoxLayout()
    self.selectorImageFilesLayout.setSpacing(0)
    self.selectorImageFilesLayout.setContentsMargins(0, 0, 0, 2)
    self.selectorImageFilesLayout.setAlignment(qt.Qt.AlignLeft)
    self.selectorImageFilesLayout.addWidget(self.selector2DImagesFiles)
    self.selectorImageFilesLayout.addWidget(self.browseImagesButton)
    self.selectorImageFilesLayout.addWidget(self.viewMoreButton)
    self.selectorImageFilesLayout.addWidget(self.deleteImagesButton)
    
    spacerRowCine = qt.QSpacerItem(0, 3, qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
    self.inputsFormLayout.addItem(spacerRowCine)
    self.inputsFormLayout.addRow("Cine Image Files: ", self.selectorImageFilesLayout)

    # Set tooltips for the widgets
    tooltipText = "Select Cine images in .mha format."
    self.selector2DImagesFiles.setToolTip(tooltipText)
    self.deleteImagesButton.setToolTip("Remove selected Cine Images.")
    self.browseImagesButton.setToolTip("Browse and add Cine Images.")
    self.viewMoreButton.setToolTip("View all selected files")

    self.selector3DSegmentationFiles = ctk.ctkPathListWidget()
    self.selector3DSegmentationFiles.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed)
    self.selector3DSegmentationFiles.setMinimumWidth(95)
    self.selector3DSegmentationFiles.setMaximumHeight(75)
    self.selector3DSegmentationFiles.setToolTip(
        "Select one segmentation file, or one per cine image for pre-warped playback.")

    self.browseSegmentationButton = qt.QPushButton("...")
    self.browseSegmentationButton.setFixedSize(qt.QSize(26, 21))
    self.browseSegmentationButton.setToolTip("Browse and add segmentation file(s).")

    self.deleteSegmentationButton = qt.QPushButton("X")
    self.deleteSegmentationButton.setFixedSize(qt.QSize(25, 25))
    self.deleteSegmentationButton.setToolTip("Remove segmentation file(s).")

    # View More button for segmentation (mirrors the cine one)
    self.viewMoreSegButton = qt.QPushButton()
    self.viewMoreSegButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.viewMoreSegButton.setFixedSize(qt.QSize(28, 26))
    self.viewMoreSegButton.setToolTip("View all selected files")
    # give it the same icon cine currently has
    isDark = slicer.app.palette().color(qt.QPalette.Window).lightness() < 128
    iconPath = os.path.join(self.mediaIconsPath, 'ViewMore.png' if isDark else 'ViewMore2.png')
    self.viewMoreSegButton.setIcon(qt.QIcon(iconPath))
    self.viewMoreSegButton.setIconSize(qt.QSize(24, 19))

    self.selectorSegmentationLayout = qt.QHBoxLayout()
    self.selectorSegmentationLayout.setSpacing(0)
    self.selectorSegmentationLayout.setAlignment(qt.Qt.AlignLeft | qt.Qt.AlignTop)
    self.selectorSegmentationLayout.addWidget(self.selector3DSegmentationFiles)
    self.selectorSegmentationLayout.addWidget(self.browseSegmentationButton)
    self.selectorSegmentationLayout.addWidget(self.viewMoreSegButton)
    self.selectorSegmentationLayout.addWidget(self.deleteSegmentationButton)
    spacerRowSeg = qt.QSpacerItem(0, 3, qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
    self.inputsFormLayout.addItem(spacerRowSeg)
    self.inputsFormLayout.addRow("Segmentation File(s): ", self.selectorSegmentationLayout)

    #  Dropdown: Transform Type 

    self.transformTypeDropdown = qt.QComboBox()
    self.transformTypeDropdown.addItems(["Translation", "Displacement Field"])
    self.transformTypeDropdown.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed)
    self.transformTypeDropdown.setMinimumWidth(95)
    # Small vertical gap above Transform Type
    spacerRow = qt.QSpacerItem(0, 5, qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
    self.inputsFormLayout.addItem(spacerRow)
    self.inputsFormLayout.addRow("Transform Type: ", self.transformTypeDropdown)

    # when changed selection signal to run onTransformTypeChanged
    self.transformTypeDropdown.currentTextChanged.connect(self.onTransformTypeChanged)


    # Deformation field file Selector 

    self.deformationFileSelector = ctk.ctkPathListWidget()
    self.deformationFileSelector.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed)
    self.deformationFileSelector.setMinimumWidth(95)
    self.deformationFileSelector.setMaximumHeight(75)
    self.deformationFileSelector.setToolTip("Select one .h5/.hdf5 file for each cine image.")

   
    # Buttons to browse and delete deformation files
    self.browseDeformationFilesButton = qt.QPushButton("...")
    self.browseDeformationFilesButton.setFixedSize(qt.QSize(26, 21))
    self.browseDeformationFilesButton.setToolTip("Browse and add deformation field files")
    self.deleteDeformationFilesButton = qt.QPushButton("X")
    self.deleteDeformationFilesButton.setFixedSize(qt.QSize(25, 25))
    self.deleteDeformationFilesButton.setToolTip("Remove selected deformation field files")

    # View More button for deformation files (mirrors the cine and segmentation ones)
    self.viewMoreDeformationButton = qt.QPushButton()
    self.viewMoreDeformationButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.viewMoreDeformationButton.setFixedSize(qt.QSize(28, 26))
    self.viewMoreDeformationButton.setToolTip("View all selected files")
    isDark = slicer.app.palette().color(qt.QPalette.Window).lightness() < 128
    iconPath = os.path.join(self.mediaIconsPath, 'ViewMore.png' if isDark else 'ViewMore2.png')
    self.viewMoreDeformationButton.setIcon(qt.QIcon(iconPath))
    self.viewMoreDeformationButton.setIconSize(qt.QSize(24, 19))

    # Button click functions 
    self.browseDeformationFilesButton.clicked.connect(self.onBrowseDeformationFiles)
    self.deleteDeformationFilesButton.clicked.connect(
        lambda: [self.deformationFileSelector.clear(),
                 setattr(self, "_appliedState", None),
                 self.transformationAppliedLabel.setVisible(False)])

    # Layout for the deformation file selector + buttons
    self.deformationFilesLayout = qt.QHBoxLayout()
    self.deformationFilesLayout.setSpacing(0)
    self.deformationFilesLayout.setContentsMargins(0, 0, 0, 2)
    self.deformationFilesLayout.setAlignment(qt.Qt.AlignLeft)
    self.deformationFilesLayout.addWidget(self.deformationFileSelector)
    self.deformationFilesLayout.addWidget(self.browseDeformationFilesButton)
    self.deformationFilesLayout.addWidget(self.viewMoreDeformationButton)
    self.deformationFilesLayout.addWidget(self.deleteDeformationFilesButton)

    self.inputsFormLayout.addRow("Deformation Field Files: ", self.deformationFilesLayout)
    self.deformationFieldLabel = self.inputsFormLayout.labelForField(self.deformationFilesLayout)
    self.deformationFileSelector.hide()
    self.browseDeformationFilesButton.hide()
    self.viewMoreDeformationButton.hide()
    self.deleteDeformationFilesButton.hide()
    self.deformationFieldLabel.hide()




    # Transforms file selector + delete button
    self.selectorTransformsFile = ctk.ctkPathLineEdit()
    self.selectorTransformsFile.filters = ctk.ctkPathLineEdit.Files | ctk.ctkPathLineEdit.NoDot | ctk.ctkPathLineEdit.NoDotDot | ctk.ctkPathLineEdit.Readable
    self.selectorTransformsFile.settingKey = 'TransformsFile'
    self.selectorTransformsFile.showHistoryButton = False

    self.deleteTransformsButton = qt.QPushButton("X")  
    self.deleteTransformsButton.setIconSize(iconSize)
    self.deleteTransformsButton.setFixedSize(buttonSize)
    self.deleteTransformsButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed) 

    self.selectorTransformsLayout = qt.QHBoxLayout()
    self.selectorTransformsLayout.setAlignment(qt.Qt.AlignLeft)
    self.selectorTransformsLayout.addWidget(self.selectorTransformsFile)
    self.selectorTransformsLayout.addWidget(self.deleteTransformsButton)
    self.inputsFormLayout.addRow("Transforms File: ", self.selectorTransformsLayout)
    #assign label variable to call later :
    self.transformsFileLabel = self.inputsFormLayout.labelForField(self.selectorTransformsLayout)

    tooltipText = "Insert a Transforms file. Valid filetypes: .csv, .xls, .xlsx"
    self.selectorTransformsFile.setToolTip(tooltipText)
    browseButton = self.selectorTransformsFile.findChildren(qt.QToolButton)[0]
    browseButton.setToolTip(tooltipText)
    tooltipText = "Remove Transforms File."
    self.deleteTransformsButton.setToolTip(tooltipText)

    # Column headers selectors
    ## Column X
    self.columnXSelector = qt.QComboBox()
    self.columnXSelector.enabled = False
    self.columnXSelector.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
    self.columnXSelectorLabel = qt.QLabel("X_Dicom:")
    self.columnXSelectorLabel.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)

    ## Column Y
    self.columnYSelector = qt.QComboBox()
    self.columnYSelector.enabled = False
    self.columnYSelector.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
    self.columnYSelectorLabel = qt.QLabel("Y_Dicom:")
    self.columnYSelectorLabel.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)

    ## Column Z
    self.columnZSelector = qt.QComboBox()
    self.columnZSelector.enabled = False
    self.columnZSelector.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
    self.columnZSelectorLabel = qt.QLabel("Z_Dicom:")
    self.columnZSelectorLabel.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)

    comboHeight = self.selectorTransformsFile.sizeHint.height()
    for combo in (self.columnXSelector, self.columnYSelector, self.columnZSelector):
      combo.setSizeAdjustPolicy(qt.QComboBox.AdjustToMinimumContentsLengthWithIcon)
      combo.setMinimumContentsLength(3)
      combo.setFixedHeight(comboHeight)

    
    ## Widget and Layout setup for columns selectors

    self.columnSelectorsLayout = qt.QHBoxLayout()
    self.columnSelectorsLayout.setSpacing(3)
    self.columnSelectorsLayout.addWidget(self.columnXSelectorLabel)
    self.columnSelectorsLayout.addWidget(self.columnXSelector)
    self.columnSelectorsLayout.addWidget(self.columnYSelectorLabel)
    self.columnSelectorsLayout.addWidget(self.columnYSelector)
    self.columnSelectorsLayout.addWidget(self.columnZSelectorLabel)
    self.columnSelectorsLayout.addWidget(self.columnZSelector)
    
    self.inputsFormLayout.addRow('Translations: ',self.columnSelectorsLayout)
    #assign label variable to call later :
    self.translationsLabel = self.inputsFormLayout.labelForField(self.columnSelectorsLayout)

    # Layout for apply transformation button
    # Apply / Status / Reset (same row)
    self.applyTransformButton = qt.QPushButton("Apply")
    self.applyTransformButton.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)

    self.columnTransformsLayout = qt.QHBoxLayout()
    self.columnTransformsLayout.setContentsMargins(0, 0, 0, 0)
    self.columnTransformsLayout.setSpacing(6)

    # Left: Apply
    self.columnTransformsLayout.addWidget(self.applyTransformButton)

    # Middle: status label
    self.transformationAppliedLabel = qt.QLabel("Transformation Applied")
    self.transformationAppliedLabel.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.transformationAppliedLabel.setContentsMargins(20, 0, 10, 0)
    self.columnTransformsLayout.addWidget(self.transformationAppliedLabel)

    # Push Reset to the far right
    self.columnTransformsLayout.addStretch(1)

    # Right: Reset
    self.resetButton = qt.QPushButton("Reset All")
    self.resetButton.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    self.columnTransformsLayout.addWidget(self.resetButton)

    # One row on the form
    self.inputsFormLayout.addRow('', self.columnTransformsLayout)
   

    ## Sequence Area

    sequenceCollapsibleButton = ctk.ctkCollapsibleButton()
    sequenceCollapsibleButton.text = "Sequence"
    self.layout.addWidget(sequenceCollapsibleButton)

    # Layout within the dummy collapsible button
    self.sequenceFormLayout = qt.QFormLayout(sequenceCollapsibleButton)

    # Sequence layout
    self.sliderWidget = qt.QWidget()
    self.sliderWidget.setMinimumHeight(35)
    self.sliderLayout = qt.QHBoxLayout()
    self.sliderWidget.setLayout(self.sliderLayout)
    self.sequenceFormLayout.addWidget(self.sliderWidget)

    # Sequence slider
    self.sequenceSlider = Slider()
    self.sequenceSlider.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
    self.sequenceSlider.setMinimum(1)
    self.sequenceSlider.setSingleStep(1)
    self.sliderLayout.addWidget(self.sequenceSlider)
    self.sequenceSlider.setToolTip("To enable this feature, load valid files in the inputs area above.")

    # The next three labels collectively will show Image __ of __
    self.divisionFrameLabel = qt.QLabel("Image ")
    self.divisionFrameLabel.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Maximum)
    self.sliderLayout.addWidget(self.divisionFrameLabel)
    
    # Current image/frame spinbox    
    self.currentFrameInputBox = SpinBox()
    self.currentFrameInputBox.minimum = 1
    self.currentFrameInputBox.setSpecialValueText(' ')
    self.currentFrameInputBox.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Maximum)
    self.sliderLayout.addWidget(self.currentFrameInputBox)
    self.currentFrameInputBox.setToolTip("To enable this feature, load valid files in the inputs area above.")

    # this label will show total number of images
    self.totalFrameLabel = qt.QLabel("of 0")
    self.totalFrameLabel.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    self.sliderLayout.addWidget(self.totalFrameLabel)

    # Playback control layout
    self.controlWidget = qt.QWidget()
    self.controlWidget.setMinimumHeight(30)
    self.controlLayout = qt.QHBoxLayout()
    self.controlLayout.setAlignment(qt.Qt.AlignLeft)
    self.controlWidget.setLayout(self.controlLayout)
    self.sequenceFormLayout.addWidget(self.controlWidget)


    iconSize = qt.QSize(14, 14)
    buttonSize = qt.QSize(36, 30)
    mediaIconsPath = os.path.join(os.path.dirname(slicer.util.modulePath(self.__module__)),
                                  'Resources', 'Icons', 'media-control-icons')

    # Previous frame/image button
    self.previousFrameButton = qt.QPushButton()
    icon = qt.QIcon(os.path.join(mediaIconsPath, 'previous.png'))
    self.previousFrameButton.setIcon(icon)
    self.previousFrameButton.setIconSize(qt.QSize(16, 16))
    self.previousFrameButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.previousFrameButton.setFixedSize(buttonSize)
    self.controlLayout.addWidget(self.previousFrameButton)
    self.previousFrameButton.setToolTip("To enable this feature, load valid files in the inputs area above.")

    # Next frame/image button
    self.nextFrameButton = qt.QPushButton()
    icon = qt.QIcon(os.path.join(mediaIconsPath, 'next.png'))
    self.nextFrameButton.setIcon(icon)
    self.nextFrameButton.setIconSize(qt.QSize(16, 16))
    self.nextFrameButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.nextFrameButton.setFixedSize(buttonSize)
    self.controlLayout.addWidget(self.nextFrameButton)
    self.nextFrameButton.setToolTip("To enable this feature, load valid files in the inputs area above.")

    # Play button
    self.playSequenceButton = qt.QPushButton()
    icon = qt.QIcon(os.path.join(mediaIconsPath, 'play.png'))
    self.playSequenceButton.setIcon(icon)
    self.playSequenceButton.setIconSize(iconSize)
    self.playSequenceButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.playSequenceButton.setFixedSize(buttonSize)
    self.controlLayout.addWidget(self.playSequenceButton)
    self.playSequenceButton.setToolTip("To enable this feature, load valid files in the inputs area above.")

    # Stop button
    self.stopSequenceButton = qt.QPushButton()
    icon = qt.QIcon(os.path.join(mediaIconsPath, 'stop.png'))
    self.stopSequenceButton.setIcon(icon)
    self.stopSequenceButton.setIconSize(iconSize)
    self.stopSequenceButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.stopSequenceButton.setFixedSize(buttonSize)
    self.controlLayout.addWidget(self.stopSequenceButton)
    self.playSequenceButton.setToolTip("To enable this feature, load valid files in the inputs area above.")

    # Playback speed label and spinbox
    self.playbackSpeedLabel = qt.QLabel("Playback Speed:")
    self.playbackSpeedLabel.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.playbackSpeedLabel.setContentsMargins(5, 0, 3, 0)
    self.controlLayout.addWidget(self.playbackSpeedLabel)
    self.playbackSpeedLabel.setToolTip("Modify playback speed in increments of 0.5.")

    self.playbackSpeedBox = qt.QDoubleSpinBox()
    self.playbackSpeedBox.minimum = 0.1
    self.playbackSpeedBox.maximum = 30.0
    self.playbackSpeedBox.value = 5.0
    self.playbackSpeedBox.setSingleStep(0.5)
    self.playbackSpeedBox.suffix = " fps"
    self.playbackSpeedBox.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.controlLayout.addWidget(self.playbackSpeedBox)
    self.playbackSpeedBox.setToolTip("Modify playback speed using the arrows on the right.")

    # Overlay collapsible section
    overlayColoursCollapsibleButton = ctk.ctkCollapsibleButton()
    overlayColoursCollapsibleButton.text = "Overlay"
    overlayColoursCollapsibleButton.collapsed = False  # Open by default
    self.layout.addWidget(overlayColoursCollapsibleButton)

    self.overlayColoursFormLayout = qt.QFormLayout(overlayColoursCollapsibleButton)
    # Visual controls layout
    self.visualControlsWidget = qt.QWidget()
    self.visualControlsWidget.setMinimumHeight(27)
    self.visualControlsLayout = qt.QHBoxLayout()
    self.visualControlsLayout.setAlignment(qt.Qt.AlignLeft)
    self.visualControlsWidget.setLayout(self.visualControlsLayout)
    self.overlayColoursFormLayout.addWidget(self.visualControlsWidget)

    # Overlay outline label and checkbox
    self.outlineLabel = qt.QLabel("Outlined Overlay:")
    self.outlineLabel.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    self.outlineLabel.setContentsMargins(0, 0, 10, 0)
    self.visualControlsLayout.addWidget(self.outlineLabel)

    self.overlayOutlineOnlyBox = qt.QCheckBox()
    self.overlayOutlineOnlyBox.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    self.overlayOutlineOnlyBox.checked = True
    self.visualControlsLayout.addWidget(self.overlayOutlineOnlyBox)

    # Opacity labels and slider widget
    self.opacityLabel = qt.QLabel(" Opacity:")
    self.opacityLabel.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    self.opacityLabel.setContentsMargins(5, 0, 3, 0)
    self.visualControlsLayout.addWidget(self.opacityLabel)

    self.opacitySlider = ctk.ctkDoubleSlider()
    self.opacitySlider.setMinimumWidth(43) 
    self.opacitySlider.orientation = qt.Qt.Horizontal
    self.opacitySlider.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    self.opacitySlider.minimum = 0
    self.opacitySlider.maximum = 1.0
    self.opacitySlider.singleStep = 0.01
    self.opacitySlider.value = 1.0
    self.visualControlsLayout.addWidget(self.opacitySlider)

    self.opacityPercentageLabel = qt.QLabel("100%")
    self.opacityPercentageLabel.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    self.opacityPercentageLabel.setContentsMargins(0, 0, 0, 0)
    self.visualControlsLayout.addWidget(self.opacityPercentageLabel)
    

    # Overlay thickness slider
    self.overlayThicknessLabel = qt.QLabel("Thickness:")
    self.overlayThicknessLabel.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    self.overlayThicknessLabel.setContentsMargins(5, 0, 3, 0)
    self.visualControlsLayout.addWidget(self.overlayThicknessLabel)

    self.overlayThicknessSlider = ctk.ctkSliderWidget()
    self.overlayThicknessSlider.setMinimumWidth(90) 
    self.overlayThicknessSlider.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    self.overlayThicknessSlider.minimum = 1
    self.overlayThicknessSlider.maximum = 10
    self.overlayThicknessSlider.value = 4
    self.overlayThicknessSlider.singleStep = 1
    self.overlayThicknessSlider.enabled = False
    self.visualControlsLayout.addWidget(self.overlayThicknessSlider)

    # Layout for color picker
    self.overlayColoursLayout = qt.QGridLayout()
    self.overlayColoursLayout.setVerticalSpacing(15)  # space between rows
    self.overlayColoursLayout.setAlignment(qt.Qt.AlignLeft)
    self.overlayColoursFormLayout.addRow(self.overlayColoursLayout)


    #
    # End GUI
    #
    


    #
    # Begin logic
    #

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = TrackLogic()
  

    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)
  

    self.playSequenceButton.connect("clicked(bool)", self.onPlayButton)
    self.stopSequenceButton.connect("clicked(bool)", self.onStopButton)
    self.nextFrameButton.connect("clicked(bool)", self.onIncrement)
    self.previousFrameButton.connect("clicked(bool)", self.onDecrement)

    self.sequenceSlider.connect("valueChanged(int)",
                            lambda v: self.currentFrameInputBox.setValue(v))

    self.sequenceSlider.connect("sliderReleased()", self.onSkipImages)

    self.currentFrameInputBox.connect("valueChanged(int)",
                                  lambda v: self.sequenceSlider.setValue(v))

    self.currentFrameInputBox.connect("upButtonClicked()", self.onIncrement)
    self.currentFrameInputBox.connect("downButtonClicked()", self.onDecrement)
    self.currentFrameInputBox.connect("editingFinished()", self.onSkipImages)
    self.playbackSpeedBox.connect("valueChanged(double)", self.onPlaybackSpeedChange)
    self.opacitySlider.connect("valueChanged(double)", self.onOpacityChange)
    self.overlayOutlineOnlyBox.connect("toggled(bool)", self.onOverlayOutlineChange)
    self.resetButton.connect("clicked(bool)", self.onResetButton)
    self.browseImagesButton.clicked.connect(self.onMultiFileBrowse)
    self.browseSegmentationButton.clicked.connect(self.onBrowseSegmentationFiles)
    self.viewMoreButton.clicked.connect(lambda: self.onViewMoreClicked(self.selector2DImagesFiles))
    self.deleteImagesButton.clicked.connect(self.onDeleteImagesButton)
    self.overlayThicknessSlider.connect("valueChanged(double)", self.onOverlayThicknessChange)

    # These connections ensure that whenever user changes some settings on the GUI, that is saved
    # in the MRML scene (in the selected parameter node).
    self.selector2DImagesFiles.connect("pathsChanged(QStringList,QStringList)", \
      lambda *args: self.updateParameterNodeFromGUI("selector2DImagesFiles", "pathsChanged"))
    self.selector3DSegmentationFiles.connect("pathsChanged(QStringList,QStringList)", \
      lambda *args: self.updateParameterNodeFromGUI("selector3DSegmentationFiles", "pathsChanged"))
    self.selectorTransformsFile.connect("currentPathChanged(QString)", \
      self.onTransformsFilePathChange)
    self.viewMoreSegButton.clicked.connect(lambda: self.onViewMoreClicked(self.selector3DSegmentationFiles))    
    self.viewMoreDeformationButton.clicked.connect(lambda: self.onViewMoreClicked(self.deformationFileSelector))   

    self.columnXSelector.connect("currentTextChanged(QString)", self.onColumnXSelectorChange)
    self.columnYSelector.connect("currentTextChanged(QString)", self.onColumnXSelectorChange)
    self.columnZSelector.connect("currentTextChanged(QString)", self.onColumnXSelectorChange)
    
    self.applyTransformButton.connect("clicked(bool)", \
      lambda: self.updateParameterNodeFromGUI("applyTransformsButton", "clicked"))
    
    # These connections ensure that whenever the user deletes some settings on the GUI, the appropiate
    # parameter node is deleted as well
    self.deleteImagesButton.connect("clicked(bool)", self.resetVisuals)
    self.deleteSegmentationButton.connect("clicked(bool)", self.resetVisuals)
    self.deleteImagesButton.connect("clicked(bool)", \
      lambda: [self.selector2DImagesFiles.clear(),
               self.updateParameterNodeFromGUI("selector2DImagesFiles", "currentPathChanged")])
    self.deleteSegmentationButton.connect("clicked(bool)", \
      lambda: [self.selector3DSegmentationFiles.clear(),
               self.updateParameterNodeFromGUI("selector3DSegmentationFiles", "pathsChanged")])
    self.deleteTransformsButton.connect("clicked(bool)", \
      lambda: [self.selectorTransformsFile.setCurrentPath(''),
               self.updateParameterNodeFromGUI("applyTransformsButton", "clicked"),
               setattr(self, "_appliedState", None),
               self.transformationAppliedLabel.setVisible(False)])

    # These connections will reset the visuals when one of the main inputs are modified
    self.selector2DImagesFiles.connect("currentPathChanged(QString)", self.resetVisuals)
    self.selector3DSegmentationFiles.connect("pathsChanged(QStringList,QStringList)", \
      lambda *args: self.resetVisuals())    


    # Initialize deformation field paths list
    self.deformationFieldPaths = []
    #
    # End logic
    #
    

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()
    # Resize the module panel to occupy 30% of the main window width
    # (slice views automatically get the remaining 70%).
    # singleShot(0) defers this until after the window layout has settled.
    qt.QTimer.singleShot(0, self.applyPanelRatio)
    self.installPanelRatioEventFilter()

  def applyPanelRatio(self):
    """
    Sets the left module panel to 30% of the main window width as the default.
    The splitter remains draggable, but never below PANEL_FLOOR_WIDTH, so
    components are never clipped or overlapped.
    """
    PANEL_FLOOR_WIDTH = 480

    mainWindow = slicer.util.mainWindow()
    if not mainWindow:
      return
    panelDockWidget = mainWindow.findChild(qt.QDockWidget, "PanelDockWidget")
    modulePanel = mainWindow.findChild(qt.QWidget, "ModulePanel")
    if not panelDockWidget or not modulePanel:
      return
    if not hasattr(self, "_panelMinWidth"):
      contentMin = 0
      scrollArea = modulePanel.findChild(qt.QScrollArea)
      if scrollArea and scrollArea.widget():
        contentMin = scrollArea.widget().minimumSizeHint.width()
      scrollbarExtent = qt.QApplication.style().pixelMetric(qt.QStyle.PM_ScrollBarExtent)
      self._panelMinWidth = max(PANEL_FLOOR_WIDTH, contentMin + scrollbarExtent + 4)

    if not hasattr(self, "_originalPanelHPolicy"):
      self._originalPanelHPolicy = modulePanel.sizePolicy.horizontalPolicy()
    sizePolicy = modulePanel.sizePolicy
    sizePolicy.setHorizontalPolicy(qt.QSizePolicy.Ignored)
    modulePanel.setSizePolicy(sizePolicy)
    panelDockWidget.setMinimumWidth(self._panelMinWidth)
    targetWidth = max(int(mainWindow.width * 0.30), self._panelMinWidth)
    mainWindow.resizeDocks([panelDockWidget], [targetWidth], qt.Qt.Horizontal)

  def releasePanelConstraint(self):
    """Restores the module panel's original sizing behavior for other modules."""
    mainWindow = slicer.util.mainWindow()
    if not mainWindow:
      return
    modulePanel = mainWindow.findChild(qt.QWidget, "ModulePanel")
    if modulePanel and hasattr(self, "_originalPanelHPolicy"):
      sizePolicy = modulePanel.sizePolicy
      sizePolicy.setHorizontalPolicy(self._originalPanelHPolicy)
      modulePanel.setSizePolicy(sizePolicy)

  def installPanelRatioEventFilter(self):
    """
    Installs an event filter on the main window so the 30% : 70% split is
    preserved when the user resizes the application window.
    """
    mainWindow = slicer.util.mainWindow()
    if not mainWindow:
      return
    # Avoid stacking duplicate filters when the module is reloaded
    if getattr(self, "_panelRatioFilter", None):
      mainWindow.removeEventFilter(self._panelRatioFilter)
    self._panelRatioFilter = _PanelRatioEventFilter(self.applyPanelRatio, mainWindow)
    mainWindow.installEventFilter(self._panelRatioFilter)

  def isPrewarpedMode(self):
    """True when the user loaded one segmentation per cine image (pre-warped masks)."""
    return len(self.customParamNode.files3DSegmentations) > 1

  def getEffectiveTransformType(self):
      """
      Derive the transform branch from actual state, not the dropdown widget.
      Any per-frame mask sequence (DVF-deformed or user-supplied pre-warped)
      must take the mask-swap path regardless of what the dropdown shows.
      """
      if self.customParamNode.deformedMaskSequenceNode:
          return "Displacement Field"
      return self.transformTypeDropdown.currentText

  def updateTransformsInputsState(self):
      """
      Enable/disable all transform-related inputs based on pre-warped mode.
      Only acts when the mode actually changes, so it never fights the
      enable/disable logic in updatePlaybackButtons or onTransformsFilePathChange.
      """
      prewarped = self.isPrewarpedMode()
      if prewarped == getattr(self, "_prewarpedUIApplied", None):
          return  # no change — leave widget states to their normal owners
      self._prewarpedUIApplied = prewarped

      widgets = (self.transformTypeDropdown,
                 self.selectorTransformsFile, self.deleteTransformsButton,
                 self.columnXSelector, self.columnYSelector, self.columnZSelector,
                 self.deformationFileSelector, self.browseDeformationFilesButton,
                 self.viewMoreDeformationButton, self.deleteDeformationFilesButton)

      if prewarped:
          reason = ("Transforms are disabled: one segmentation was loaded per cine image, "
                    "so each frame already has its own pre-warped mask.")
          for w in widgets:
              w.enabled = False
              w.setToolTip(reason)
      else:
          # Leaving pre-warped mode: re-enable and restore original tooltips
          self.transformTypeDropdown.enabled = True
          self.transformTypeDropdown.setToolTip("")
          self.selectorTransformsFile.enabled = bool(self.customParamNode.sequenceNode2DImages)
          self.selectorTransformsFile.setToolTip("Insert a Transforms file. Valid filetypes: .csv, .xls, .xlsx")
          self.deleteTransformsButton.enabled = True
          self.deleteTransformsButton.setToolTip("Remove Transforms File.")
          # Column selectors are only meaningful once a transforms file populated them
          hasColumns = self.columnXSelector.count > 0
          for w in (self.columnXSelector, self.columnYSelector, self.columnZSelector):
              w.enabled = hasColumns
              w.setToolTip("")
          self.deformationFileSelector.enabled = True
          self.deformationFileSelector.setToolTip("Select one .h5/.hdf5 file for each cine image.")
          self.browseDeformationFilesButton.enabled = True
          self.browseDeformationFilesButton.setToolTip("Browse and add deformation field files")
          self.viewMoreDeformationButton.enabled = True
          self.viewMoreDeformationButton.setToolTip("View all selected files")
          self.deleteDeformationFilesButton.enabled = True
          self.deleteDeformationFilesButton.setToolTip("Remove selected deformation field files")

  def onTransformTypeChanged(self, value):
    self.transformType = value


    if value == "Displacement Field":
        self.deformationFileSelector.show()
        self.browseDeformationFilesButton.show()
        self.viewMoreDeformationButton.show()
        self.deleteDeformationFilesButton.show()
        self.deformationFieldLabel.show()

        self.selectorTransformsFile.hide()
        self.deleteTransformsButton.hide()
        self.transformsFileLabel.hide()
        

        self.columnXSelector.hide()
        self.columnXSelectorLabel.hide()
        self.columnYSelector.hide()
        self.columnYSelectorLabel.hide()
        self.columnZSelector.hide()
        self.columnZSelectorLabel.hide()
        self.translationsLabel.hide()

        
    else:
        self.deformationFileSelector.hide()
        self.browseDeformationFilesButton.hide()
        self.viewMoreDeformationButton.hide()
        self.deleteDeformationFilesButton.hide()
        self.deformationFieldLabel.hide()

        self.selectorTransformsFile.show()
        self.deleteTransformsButton.show()
        self.transformsFileLabel.show()

        self.columnXSelector.show()
        self.columnXSelectorLabel.show()
        self.columnYSelector.show()
        self.columnYSelectorLabel.show()
        self.columnZSelector.show()
        self.columnZSelectorLabel.show()
        self.translationsLabel.show()


  def onBrowseDeformationFiles(self):
      fileDialog = qt.QFileDialog()
      fileDialog.setFileMode(qt.QFileDialog.ExistingFiles)
      fileDialog.setNameFilter("Deformation Fields (*.h5 *.hdf5)")

      if fileDialog.exec():
          selectedFiles = fileDialog.selectedFiles()
          selectedFiles = sorted(list(selectedFiles))
          self.deformationFileSelector.addPaths(selectedFiles)
          self.deformationFieldPaths = selectedFiles
          self._appliedState = None
          self.transformationAppliedLabel.setVisible(False)
          
  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()
    # Remove the panel ratio event filter so it doesn't linger after reload
    if getattr(self, "_panelRatioFilter", None):
      mainWindow = slicer.util.mainWindow()
      if mainWindow:
        mainWindow.removeEventFilter(self._panelRatioFilter)
      self._panelRatioFilter = None
    self.releasePanelConstraint()

  def enter(self):
    """
    Called each time the user opens this module.
    """
    # Make sure parameter node exists and observed
    self.initializeParameterNode()
    # Re-apply the 30% : 70% panel split when returning to this module
    qt.QTimer.singleShot(0, self.applyPanelRatio)

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    if self.customParamNode and self.hasObserver(
        self.customParamNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode):
      self.removeObserver(self.customParamNode, vtk.vtkCommand.ModifiedEvent,
                          self.updateGUIFromParameterNode)
    self.releasePanelConstraint()

  def onSceneStartClose(self, caller, event):
    """
    Called just before the scene is closed.
    """
    # Parameter node will be reset, do not use it anymore
    self.setParameterNode(None)

  def onSceneEndClose(self, caller, event):
    """
    Called just after the scene is closed.
    """
    # If this module is shown while the scene is closed then recreate a new parameter node immediately
    if self.parent.isEntered:
      self.initializeParameterNode()

  def initializeParameterNode(self):
    """
    Ensure parameter node exists and observed.
    """
    # Parameter node stores all user choices in parameter values, node selections, etc.
    # so that when the scene is saved and reloaded, these settings are restored.

    # getParameterNode() is a function of ScriptedLoadableModuleLogic that returns the parameter
    # node, or creates a new one. The parameter node is of type vtkMRMLScriptedModuleNode.
    # see: https://readthedocs.org/projects/slicer/downloads/pdf/latest
    # This line basically gives setParameterNode an empty node to work with and then expects it
    # to be filled with default values through the function logic.setDefaultParameters.
    self.setParameterNode(self.logic.getParameterNode())

  def setParameterNode(self, inputParameterNode):
    """
    Set and observe parameter node.
    Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
    """
    # NOTE: In certain situations the parameter node is set to None (ex. briefly on module reload)

    # If a parameter node is provided (i.e. not None), then create a Custom Parameter Node with it
    if inputParameterNode:
      # A parameter node is new if it is being used for the first time (no parameters are set)
      isNewParamNode = inputParameterNode.GetParameterNamesAsCommaSeparatedList() == ""

      inputParameterNode = CustomParameterNode(inputParameterNode)

      # We only want to set the default parameters when the parameter node is new
      if isNewParamNode:
        self.logic.setDefaultParameters(inputParameterNode)

    # Unobserve previously selected parameter node
    if self.customParamNode is not None:
      self.removeObserver(self.customParamNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    self.customParamNode = inputParameterNode

    # Changes of parameter node are observed so that whenever parameters are changed by a script
    # or any other module those are reflected immediately in the GUI. No observation if None.
    if self.customParamNode is not None:
      self.addObserver(self.customParamNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """
    
    if self.customParamNode is None or self._updatingGUIFromParameterNode:
      return
    
    # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
    self._updatingGUIFromParameterNode = True

    self.selector3DSegmentationFiles.blockSignals(True)
    self.selector3DSegmentationFiles.clear()
    self.selector3DSegmentationFiles.addPaths(self.customParamNode.files3DSegmentations)
    self.selector3DSegmentationFiles.blockSignals(False)

    self.selectorTransformsFile.currentPath = self.customParamNode.transformsFilePath
    self.selector2DImagesFiles.blockSignals(True)
    self.selector2DImagesFiles.clear()
    self.selector2DImagesFiles.addPaths(self.customParamNode.files2DImages)
    self.selector2DImagesFiles.blockSignals(False)

    if self.customParamNode.sequenceNode2DImages and not self.isPrewarpedMode():
      self.selectorTransformsFile.enabled = True
      self.selectorTransformsFile.setToolTip("Load a Transforms file corresponding to the Region of Interest's coordinate changes.")
    elif not self.isPrewarpedMode():
      self.selectorTransformsFile.enabled = False
      self.selectorTransformsFile.setToolTip("Load a valid Cine Images Folder to enable loading a Transforms file.")
    else:
      self.selectorTransformsFile.enabled = False
      self.selectorTransformsFile.setToolTip("Load a valid Cine Images Folder to enable loading a Transforms file.")

    # Images alone are enough to enable playback
    inputsProvided = bool (self.customParamNode.sequenceNode2DImages)

    self.updatePlaybackButtons(inputsProvided)

    self.sequenceSlider.setMaximum(self.customParamNode.totalImages)

    if self.customParamNode.sequenceBrowserNode and self.customParamNode.sequenceBrowserNode.GetPlaybackActive():
      imageDict = self.getSliceDict()
      imageNum = self.customParamNode.sequenceBrowserNode.GetSelectedItemNumber() + 1
      self.sequenceSlider.setValue(imageNum)
      self.currentFrameInputBox.setValue(imageNum)
      
      # Check whether the full overlay path is possible
      hasSegmentation = bool(self.customParamNode.node3DSegmentation)
      hasTransforms = bool(self.customParamNode.sequenceNodeTransforms or 
                          self.customParamNode.deformedMaskSequenceNode)

      if hasSegmentation and hasTransforms:
      
        # Trigger visualization with all current parameters
        # Passes both standard transform and new deformation field settings
        # transformType determines whether Translation or Displacement Field is used
        self.logic.visualize(
            sequenceBrowser=self.customParamNode.sequenceBrowserNode,
            sequenceNode2DImages=self.customParamNode.sequenceNode2DImages,
            segmentationLabelMapID=self.customParamNode.node3DSegmentationLabelMap,
            sequenceNodeTransforms=self.customParamNode.sequenceNodeTransforms,
            opacity=self.customParamNode.opacity,
            overlayAsOutline=self.customParamNode.overlayAsOutline,
            overlayThickness=self.customParamNode.overlayThickness,
            show=False,
            customParamNode=self.customParamNode,
            deformedMaskSequenceNode=self.customParamNode.deformedMaskSequenceNode,
            transformType=self.getEffectiveTransformType()
        )
      
      else:
        # Images-only path
        self.logic.visualizeImagesOnly(
            sequenceBrowser=self.customParamNode.sequenceBrowserNode,
            sequenceNode2DImages=self.customParamNode.sequenceNode2DImages
        )
      self.editSliceView(imageDict)
                           
    elif not self.customParamNode.sequenceBrowserNode:
      self.sequenceSlider.setValue(1)
      self.currentFrameInputBox.setValue(1)

    self.playbackSpeedBox.value = self.customParamNode.fps

    self.opacitySlider.value = self.customParamNode.opacity

    self.opacityPercentageLabel.text = str(int(self.customParamNode.opacity * 100)) + "%"

    self.overlayOutlineOnlyBox.checked = self.customParamNode.overlayAsOutline

    
    # Only disable Apply if images are loaded — re-enable so user can trigger playback
    self.applyTransformButton.enabled = inputsProvided

    # Keep transforms inputs disabled (with tooltip) whenever pre-warped mode is active.
    # This runs on every GUI refresh, so no other code path can leave them re-enabled.
    self.updateTransformsInputsState()

    self._updatingGUIFromParameterNode = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self.customParamNode is None or self._updatingGUIFromParameterNode:
      return

    # Raise the guard BEFORE StartModify so EndModify cannot re-enter
    self._updatingGUIFromParameterNode = True
    # Modify all properties in a single batch
    wasModified = self.customParamNode.StartModify()

    try:

        shNode = slicer.mrmlScene.GetSubjectHierarchyNode()

        if caller == "selector2DImagesFiles" and event == "pathsChanged":
          # Remember if all inputs were previously provided
          inputsProvided = len(self.customParamNode.files3DSegmentations) > 0 or self.selectorTransformsFile.currentPath != ''
          # Since the transformation information is relative to the 2D images loaded into 3D Slicer,
          # if the path changes, we want to remove any transforms related information. The user should
          # reselect the transforms file they wish to use with the 2D images.
          if self.customParamNode.transformsFilePath:
            self.customParamNode.transformsFilePath = ""
            self.customParamNode.sequenceNodeTransforms = None

          if len(self.selector2DImagesFiles.paths) == 0:
            # Remove the Images folder stored in customParamNode
            self.customParamNode.files2DImages = []

            # Remove the unused Image Nodes Sequence node, containing each image node, if it exists
            nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLScalarVolumeNode", "Image Nodes Sequence")
            nodes.UnRegister(None)
            if nodes.GetNumberOfItems() == 2:
              nodeToRemove = nodes.GetItemAsObject(0)
              slicer.mrmlScene.RemoveNode(nodeToRemove.GetDisplayNode())
              slicer.mrmlScene.RemoveNode(nodeToRemove.GetStorageNode())
              slicer.mrmlScene.RemoveNode(nodeToRemove)

            # Remove the unused Image Nodes Sequence node, containing the whole image sequence if it exists
            nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLSequenceNode", "Image Nodes Sequence")
            nodes.UnRegister(None)
            if nodes.GetNumberOfItems() == 1:
              nodeToRemove = nodes.GetItemAsObject(0)
              slicer.mrmlScene.RemoveNode(nodeToRemove)

            # Remove the unused Transforms Nodes Sequence containing each linear transform node, if it exists
            nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLLinearTransformNode", "Transform Nodes Sequence")
            nodes.UnRegister(None)
            if nodes.GetNumberOfItems() == 2:
              nodeToRemove = nodes.GetItemAsObject(0)
              slicer.mrmlScene.RemoveNode(nodeToRemove)
              
            # Remove all nodes previously created by transforms data inside the scene if all inputs were previously provided
            if inputsProvided:
              # Remove the Image Nodes Sequence node
              nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLScalarVolumeNode", "Image Nodes Sequence")
              nodes.UnRegister(None)
              nodeToRemove = nodes.GetItemAsObject(0)
              slicer.mrmlScene.RemoveNode(nodeToRemove)
              
              # Remove the unused Sequence Browser if it exists
              nodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLSequenceBrowserNode")
              nodes.UnRegister(None)
              if nodes.GetNumberOfItems() == 1:
                sequenceBrowserNodeToDelete = nodes.GetItemAsObject(0)
                slicer.mrmlScene.RemoveNode(sequenceBrowserNodeToDelete)
              
              # Remove the unused Transforms Nodes Sequence, if it exists
              nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLSequenceNode", "Transform Nodes Sequence")
              nodes.UnRegister(None)
              if nodes.GetNumberOfItems() == 1:
                nodeToRemove = nodes.GetItemAsObject(0)
                slicer.mrmlScene.RemoveNode(nodeToRemove)
              
              # Remove the unused Transforms Nodes Sequence containing each linear transform node, if it exists
              nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLLinearTransformNode", "Transform Nodes Sequence")
              nodes.UnRegister(None)
              if nodes.GetNumberOfItems() == 1:
                nodeToRemove = nodes.GetItemAsObject(0)
                slicer.mrmlScene.RemoveNode(nodeToRemove.GetStorageNode())
                slicer.mrmlScene.RemoveNode(nodeToRemove)
                
              # Remove the image nodes of each slice view used to preserve the slice views
              nodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLScalarVolumeNode")
              nodes.UnRegister(None)
              for node in nodes:
                if node.GetName() == 'Image Nodes Sequence':
                  break
                if node.GetName() == node.GetAttribute('Sequences.BaseName'):
                  slicer.mrmlScene.RemoveNode(node.GetDisplayNode())
                  slicer.mrmlScene.RemoveNode(node)

              # Remove the Volume Rendering Node, if it exists
              nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLLinearTransformNode", "Transform Nodes Sequence")
            # Remove all nodes created
            else:
              slicer.mrmlScene.Clear()

          else:
            # Set a param to hold the list of paths to the cine images
            self.customParamNode.files2DImages = self.selector2DImagesFiles.paths

            # Delete nodes if sequence is actively playing
            activePlay = self.customParamNode.sequenceBrowserNode and \
                        hasattr(self.customParamNode.sequenceBrowserNode, 'GetPlaybackActive') and \
                        self.customParamNode.sequenceBrowserNode.GetPlaybackActive()
            if activePlay:
              # Remove the unused Sequence Browser if it exists
              nodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLSequenceBrowserNode")
              nodes.UnRegister(None)
              if nodes.GetNumberOfItems() == 1:
                sequenceBrowserNodeToDelete = nodes.GetItemAsObject(0)
                slicer.mrmlScene.RemoveNode(sequenceBrowserNodeToDelete)
              
              # Remove the image nodes of each slice view used to preserve the slice views
              nodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLScalarVolumeNode")
              nodes.UnRegister(None)
              for node in nodes:
                if node.GetName() == node.GetAttribute('Sequences.BaseName'):
                  slicer.mrmlScene.RemoveNode(node.GetDisplayNode())
                  slicer.mrmlScene.RemoveNode(node)

              # Remove the unused Image Nodes Sequence node, containing the whole image sequence if it exists
              nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLSequenceNode", "Image Nodes Sequence")
              nodes.UnRegister(None)
              if nodes.GetNumberOfItems() == 1:
                nodeToRemove = nodes.GetItemAsObject(0)
                slicer.mrmlScene.RemoveNode(nodeToRemove)
                
              # Remove the unused Image Nodes Sequence node, containing each image node, if it exists
              nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLScalarVolumeNode", "Image Nodes Sequence")
              nodes.UnRegister(None)
              if nodes.GetNumberOfItems() == 1:
                nodeToRemove = nodes.GetItemAsObject(0)
                slicer.mrmlScene.RemoveNode(nodeToRemove)
                
              # Remove the unused Transforms Nodes Sequence containing each linear transform node, if it exists
              nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLLinearTransformNode", "Transform Nodes Sequence")
              nodes.UnRegister(None)
              if nodes.GetNumberOfItems() == 1:
                nodeToRemove = nodes.GetItemAsObject(0)
                slicer.mrmlScene.RemoveNode(nodeToRemove)
              
              # Remove the unused Transforms Nodes Sequence, if it exists
              nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLSequenceNode", "Transform Nodes Sequence")
              nodes.UnRegister(None)
              if nodes.GetNumberOfItems() == 1:
                nodeToRemove = nodes.GetItemAsObject(0)
                slicer.mrmlScene.RemoveNode(nodeToRemove)

            # Load the images into 3D Slicer
            imagesSequenceNode, cancelled = \
              self.logic.loadImagesIntoSequenceNode(shNode, self.selector2DImagesFiles.paths)

            if cancelled:
              # Unset the param which holds the list of paths to the 2D images
              self.customParamNode.files2DImages = []
            else:
              if imagesSequenceNode:
                # Set a param to hold a sequence node which holds the cine images
                self.customParamNode.sequenceNode2DImages = imagesSequenceNode
                # Track the number of total images within the parameter totalImages
                self.customParamNode.totalImages = imagesSequenceNode.GetNumberOfDataNodes()
                self.transformationAppliedLabel.setVisible(False)  
                self.currentFrameInputBox.setMaximum(self.customParamNode.totalImages)  # allows for image counter to go above 99, if there are more than 99 images
                self.totalFrameLabel.setText(f"of {self.customParamNode.totalImages}")

                if not activePlay:
                  # Remove the unused Image Nodes Sequence node, containing each image node, if it exists
                  nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLScalarVolumeNode", "Image Nodes Sequence")
                  nodes.UnRegister(None)
                  if nodes.GetNumberOfItems() == 2:
                    nodeToRemove = nodes.GetItemAsObject(0)
                    slicer.mrmlScene.RemoveNode(nodeToRemove.GetDisplayNode())
                    slicer.mrmlScene.RemoveNode(nodeToRemove.GetStorageNode())
                    slicer.mrmlScene.RemoveNode(nodeToRemove)

                  # Remove the unused Image Nodes Sequence node, containing the whole image sequence if it exists
                  nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLSequenceNode", "Image Nodes Sequence")
                  nodes.UnRegister(None)
                  if nodes.GetNumberOfItems() == 2:
                    nodeToRemove = nodes.GetItemAsObject(0)
                    slicer.mrmlScene.RemoveNode(nodeToRemove)

                  # Remove the unused Transforms Nodes Sequence containing each linear transform node, if it exists
                  nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLLinearTransformNode", "Transform Nodes Sequence")
                  nodes.UnRegister(None)
                  if nodes.GetNumberOfItems() == 2:
                    nodeToRemove = nodes.GetItemAsObject(0)
                    slicer.mrmlScene.RemoveNode(nodeToRemove)
                
              else:
                self.totalFrameLabel.setText(f"of 0")
                slicer.util.warningDisplay("No image files were found within the selected files.", "Input Error")

        if caller == "selector3DSegmentationFiles" and event == "pathsChanged":
            segPaths = sorted(list(self.selector3DSegmentationFiles.paths))
            previousPaths = list(self.customParamNode.files3DSegmentations)

            if len(segPaths) > 1:
                # ---- Entering pre-warped mode ----
                # Warn before clearing an already-loaded transforms file
                if self.customParamNode.transformsFilePath or self.selectorTransformsFile.currentPath:
                    if not slicer.util.confirmYesNoDisplay(
                            "You have loaded multiple segmentation files (one per cine image).\n\n"
                            "In this mode each frame uses its own pre-warped mask, so the "
                            "Transforms file is not used and will be cleared.\n\nContinue?",
                            "Pre-Warped Segmentations"):
                        # User declined — revert the selection
                        self.selector3DSegmentationFiles.blockSignals(True)
                        self.selector3DSegmentationFiles.clear()
                        self.selector3DSegmentationFiles.addPaths(previousPaths)
                        self.selector3DSegmentationFiles.blockSignals(False)
                        return
                    self.customParamNode.transformsFilePath = ""
                    self.customParamNode.sequenceNodeTransforms = None
                    self.selectorTransformsFile.blockSignals(True)
                    self.selectorTransformsFile.setCurrentPath('')
                    self.selectorTransformsFile.blockSignals(False)

                # Early feedback if the count already provably mismatches
                if self.customParamNode.totalImages > 0 and \
                  len(segPaths) != self.customParamNode.totalImages:
                    slicer.util.warningDisplay(
                        f"Please load either exactly one segmentation, or {self.customParamNode.totalImages}"
                        " segmentations (one per cine image).",
                        "Segmentation Count Mismatch")
                    # Not clearing the selection — the user may still be adding files
                    # or about to change the cine set. Hard enforcement happens at Apply.

                self.customParamNode.files3DSegmentations = segPaths
                self.customParamNode.path3DSegmentation = ""   # single-file path unused in this mode
                self.customParamNode.node3DSegmentation = 0
                self.customParamNode.node3DSegmentationLabelMap = 0

            elif len(segPaths) == 1:
                # ---- Single-file mode: existing behavior, path taken from the list ----
                self.customParamNode.files3DSegmentations = segPaths
                currentPath = segPaths[0]
                fileName = os.path.basename(currentPath)

                if re.match('.*\\.dcm', currentPath):  # if getting a dcm -> try install dcmrtstruct2nii
                    try:
                        from dcmrtstruct2nii import dcmrtstruct2nii, list_rt_structs
                    except ModuleNotFoundError:
                        if slicer.util.confirmOkCancelDisplay("To load a DICOM RT structure, the dcmrtstruct2nii module is required."
                                                              "Please click 'OK' to install it", "Missing Python packages"):
                            messageBox = qt.QMessageBox()
                            messageBox.setIcon(qt.QMessageBox.Information)
                            messageBox.setWindowTitle("Package Installation")
                            messageBox.setText("Installing 'dcmrtstruct2nii'...")
                            messageBox.setStandardButtons(qt.QMessageBox.NoButton)
                            messageBox.show()
                            slicer.app.processEvents()

                            slicer.util.pip_install('dcmrtstruct2nii')
                            from dcmrtstruct2nii import dcmrtstruct2nii, list_rt_structs
                            messageBox.setText(f"Package 'dcmrtstruct2nii' installed successfully. {fileName} will now load.")
                            slicer.app.processEvents()
                            qt.QTimer.singleShot(3000, messageBox.accept)
                            while messageBox.isVisible():
                                slicer.app.processEvents()
                            messageBox.hide()
                        else:
                            # User declined install — clear the selection
                            self.customParamNode.files3DSegmentations = []
                            self.selector3DSegmentationFiles.blockSignals(True)
                            self.selector3DSegmentationFiles.clear()
                            self.selector3DSegmentationFiles.blockSignals(False)
                            return

                    from dcmrtstruct2nii import dcmrtstruct2nii, list_rt_structs
                    structs = list_rt_structs(currentPath)
                    if len(structs) == 0:
                        slicer.util.warningDisplay(f"{fileName} does not contain any RT structures.",
                                                   "No RT Structures Found")
                        return

                    def onOK():
                        nonlocal currentPath
                        structure = structSelectorComboBox.currentText
                        dicomPath = dicomPathSelector.currentPath
                        outputPath = outputPathSelector.currentPath
                        structures = [structure]
                        segmentationPath = os.path.join(outputPath, 'mask_' + structure + '.nii.gz')
                        try:
                            messageBox = qt.QMessageBox()
                            messageBox.setIcon(qt.QMessageBox.Information)
                            messageBox.setWindowTitle("Converting DICOM RT-STRUCT")
                            messageBox.setText(f"Converting {structure} to a loadable format...")
                            messageBox.setStandardButtons(qt.QMessageBox.NoButton)
                            messageBox.show()
                            slicer.app.processEvents()
                            dcmrtstruct2nii(rtstruct_file=currentPath, dicom_file=dicomPath,
                                            output_path=outputPath, structures=structures,
                                            convert_original_dicom=False)
                            currentPath = segmentationPath
                            self.customParamNode.files3DSegmentations = [segmentationPath]
                            messageBox.setText(f"Converted DICOM RT_STRUCT successfully. Mask {structure} will now load.")
                            slicer.app.processEvents()
                            qt.QTimer.singleShot(3000, messageBox.accept)
                        except Exception as e:
                            slicer.util.warningDisplay(f"Failed to convert {fileName} to a loadable format.\n{e}",
                                                       "Failed to Convert File")
                            self.customParamNode.path3DSegmentation = ""
                            self.customParamNode.files3DSegmentations = []
                            self.selector3DSegmentationFiles.blockSignals(True)
                            self.selector3DSegmentationFiles.clear()
                            self.selector3DSegmentationFiles.blockSignals(False)
                            return
                        finally:
                            structSelectorDialog.accept()
                            structSelectorDialog.hide()

                    structSelectorDialogLayout = qt.QFormLayout()
                    structSelectorComboBox = qt.QComboBox()
                    structSelectorComboBox.addItems(structs)
                    structSelectorDialogLayout.addRow("Select the target segmentation:", structSelectorComboBox)
                    dicomPathSelector = ctk.ctkPathLineEdit()
                    dicomPathSelector.filters = ctk.ctkPathLineEdit.Dirs
                    structSelectorDialogLayout.addRow("DICOM images directory", dicomPathSelector)
                    outputPathSelector = ctk.ctkPathLineEdit()
                    outputPathSelector.filters = ctk.ctkPathLineEdit.Dirs
                    structSelectorDialogLayout.addRow("Output segmentation directory", outputPathSelector)
                    structSelectorDialogLayout.addWidget(qt.QLabel("Note: DICOM RT-STRUCT files are not directly loadable. Please provide the paths above to convert the segmentation into a loadable format."))

                    okButton = qt.QPushButton("OK")
                    okButton.setDefault(True)
                    structSelectorDialogLayout.addWidget(okButton)

                    structSelectorDialog = qt.QDialog()
                    structSelectorDialog.setLayout(structSelectorDialogLayout)
                    structSelectorDialog.setModal(True)
                    okButton.connect("clicked()", onOK)

                    structSelectorDialog.show()
                    while structSelectorDialog.isVisible():
                        slicer.app.processEvents()
                    if structSelectorDialog.result() == qt.QDialog.Rejected:
                        self.customParamNode.path3DSegmentation = ""
                        self.customParamNode.files3DSegmentations = []
                        self.selector3DSegmentationFiles.blockSignals(True)
                        self.selector3DSegmentationFiles.clear()
                        self.selector3DSegmentationFiles.blockSignals(False)
                        return
                    structSelectorDialog.hide()

                # Remove the image nodes of each slice view used to preserve the slice views
                nodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLScalarVolumeNode")
                nodes.UnRegister(None)
                for node in nodes:
                    if node.GetName() == node.GetAttribute('Sequences.BaseName'):
                        slicer.mrmlScene.RemoveNode(node.GetDisplayNode())
                        slicer.mrmlScene.RemoveNode(node)

                # Remove the label map node and the nodes it referenced, all created by the previous node
                nodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLLabelMapVolumeNode")
                nodes.UnRegister(None)
                if nodes.GetNumberOfItems() == 1:
                    nodeToRemove = nodes.GetItemAsObject(0)
                    slicer.mrmlScene.RemoveNode(nodeToRemove.GetDisplayNode())
                    if nodeToRemove.GetNumberOfDisplayNodes() == 1:
                        slicer.mrmlScene.RemoveNode(nodeToRemove.GetDisplayNode().GetNodeReference('volumeProperty'))
                        slicer.mrmlScene.RemoveNode(nodeToRemove.GetDisplayNode())
                    slicer.mrmlScene.RemoveNode(nodeToRemove.GetStorageNode())
                    slicer.mrmlScene.RemoveNode(nodeToRemove)

                # Remove the 3D segmentation node and the nodes it referenced, all created by the previous node
                nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLScalarVolumeNode", "3D Segmentation")
                nodes.UnRegister(None)
                if nodes.GetNumberOfItems() == 1:
                    nodeToRemove = nodes.GetItemAsObject(0)
                    slicer.mrmlScene.RemoveNode(nodeToRemove.GetDisplayNode())
                    slicer.mrmlScene.RemoveNode(nodeToRemove.GetStorageNode())
                    slicer.mrmlScene.RemoveNode(nodeToRemove)

                # Remove previous node values stored in variables
                self.customParamNode.node3DSegmentation = 0
                self.customParamNode.node3DSegmentationLabelMap = 0

                # Loads segmentation files
                fileFormats = ['.*\\.mha', '.*\\.dcm', '.*\\.nrrd', '.*\\.nii', '.*\\.hdr', '.*\\.img', '.*\\.nhdr']
                validFormat = any(re.match(format, currentPath) for format in fileFormats)
                if validFormat:
                    # Set a param to hold the path to the 3D segmentation file
                    self.customParamNode.path3DSegmentation = currentPath

                    segmentationNode = slicer.util.loadVolume(currentPath,
                                                              {"singleFile": True, "show": False})

                    # Check if Segmentation file has less than 30 values:
                    if np.unique(slicer.util.arrayFromVolume(segmentationNode)).size > 30:
                        slicer.util.warningDisplay("This file contains more than 30 unique values. ")

                    # Get array from volume
                    segArray = arrayFromVolume(segmentationNode)
                    uniqueLabels = np.unique(segArray)

                    # Check for multi-label (more than just 0 and 1)
                    nonZeroLabels = uniqueLabels[uniqueLabels != 0]

                    if len(nonZeroLabels) > 1:
                        # Remap to consecutive label values (e.g., 1, 2, 3, ...)
                        remapDict = {label: i + 1 for i, label in enumerate(nonZeroLabels)}
                        for oldVal, newVal in remapDict.items():
                            segArray[segArray == oldVal] = newVal
                        # Push updated array back into the segmentation node
                        updateVolumeFromArray(segmentationNode, segArray)

                    remappedLabels = list(range(1, len(nonZeroLabels) + 1))
                    self.addAdditionalOverlayColorButtons(remappedLabels, segmentationNode)

                    # Continue with existing logic
                    self.logic.clearSliceForegrounds()
                    segmentationNode.SetName("3D Segmentation")
                    nodeID = shNode.GetItemByDataNode(segmentationNode)
                    self.customParamNode.node3DSegmentation = nodeID

                    # Create a label map of the 3D segmentation
                    volumesModuleLogic = slicer.modules.volumes.logic()
                    segmentationLabelMap = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode', "3D Segmentation Label Map")
                    volumesModuleLogic.CreateLabelVolumeFromVolume(slicer.mrmlScene, segmentationLabelMap, segmentationNode)

                    labelMapID = shNode.GetItemByDataNode(segmentationLabelMap)
                    self.customParamNode.node3DSegmentationLabelMap = labelMapID

                    # Apply any pending colors that were stored before the label map was created
                    self.applyPendingLabelColors()

                else:
                    self.customParamNode.path3DSegmentation = ''
                    self.customParamNode.files3DSegmentations = []
                    slicer.util.warningDisplay("Not a valid file format."
                                               "The file was not loaded into 3D Slicer.", "Input Error")
                    self.selector3DSegmentationFiles.blockSignals(True)
                    self.selector3DSegmentationFiles.clear()
                    self.selector3DSegmentationFiles.blockSignals(False)

            else:
                # ---- Cleared ----
                self.customParamNode.files3DSegmentations = []
                self.customParamNode.path3DSegmentation = ""
                self.customParamNode.node3DSegmentation = 0
                self.customParamNode.node3DSegmentationLabelMap = 0
                # remove leftover per-frame mask sequence if one exists
                nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLSequenceNode", "Per-Frame Mask Sequence")
                nodes.UnRegister(None)
                for i in range(nodes.GetNumberOfItems()):
                    slicer.mrmlScene.RemoveNode(nodes.GetItemAsObject(i))
                self.customParamNode.deformedMaskSequenceNode = None

            self.updateTransformsInputsState()

                              
        if caller == "applyTransformsButton" and event == "clicked":

          if self.isPrewarpedMode():
              self.applyPrewarpedMode(shNode)
              return  # try/finally still runs EndModify + GUI refresh

          hasSegmentation = bool(self.customParamNode.path3DSegmentation)
          if not hasSegmentation:
            # Create a sequence browser and register only the image sequence.
            # No transforms, no label maps needed.
            sequenceBrowserNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLSequenceBrowserNode", "Sequence Browser")
            sequenceBrowserNode.AddSynchronizedSequenceNode(
                self.customParamNode.sequenceNode2DImages)

            # Observe the browser so the frame counter / slider stay in sync
            self.addObserver(sequenceBrowserNode, vtk.vtkCommand.ModifiedEvent,
                             self.updateGUIFromParameterNode)

            # Store it so the rest of the UI knows playback is ready
            self.customParamNode.sequenceBrowserNode = sequenceBrowserNode

            # Clean up any leftover browser node from a previous Apply press
            nodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLSequenceBrowserNode")
            nodes.UnRegister(None)
            if nodes.GetNumberOfItems() == 2:
              oldBrowser = nodes.GetItemAsObject(0)
              slicer.mrmlScene.RemoveNode(oldBrowser)

            # Show first frame and reset playback controls
            self.resetVisuals()

          elif self.transformTypeDropdown.currentText == "Translation":


            # Set a param to hold the path to the transformations .csv file

            numImages = self.customParamNode.totalImages


            if self.selectorTransformsFile.currentPath:
              

              # If even one line cannot be read correctly/is missing our playback cannot be successful. We
              # will validate the tranformations input first. If the input is valid, we get a list
              # containing all of the transformations read from the file.
              headers = []
              headers.append(self.columnXSelector.currentText)
              headers.append(self.columnYSelector.currentText)
              headers.append(self.columnZSelector.currentText)
              transformsList = \
                self.logic.validateTransformsInput(self.selectorTransformsFile.currentPath, numImages,headers)
              
            else:
              # No file provided — use identity transform (0,0,0) for each frame
              self.customParamNode.transformsFilePath = ""
              transformsList = [[0.0, 0.0, 0.0] for _ in range(numImages)]
            if transformsList:
              # Create transform nodes from the transform data and place them into a sequence node
              transformsSequenceNode = \
                self.logic.createTransformNodesFromTransformData(shNode, transformsList, numImages)

              if not transformsSequenceNode:
                # If cancelled unset param to hold path to the transformations .csv file
                self.customParamNode.transformsFilePath = ""
              else:
                # Set a param to hold the sequence node which holds the transform nodes
                self.customParamNode.sequenceNodeTransforms = transformsSequenceNode
                # Create a sequence browser node
                sequenceBrowserNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", \
                                                                        "Sequence Browser")
                sequenceBrowserNode.AddSynchronizedSequenceNode(self.customParamNode.sequenceNode2DImages)
                sequenceBrowserNode.AddSynchronizedSequenceNode(self.customParamNode.sequenceNodeTransforms)
                # We need to observe the changes to the sequence browser so that our GUI will update as
                # the sequence progresses
                self.addObserver(sequenceBrowserNode, vtk.vtkCommand.ModifiedEvent, \
                                self.updateGUIFromParameterNode)
                # Set a param to hold the sequence browser node
                self.customParamNode.sequenceBrowserNode = sequenceBrowserNode
                
                # Since the code above added another set of image nodes, transforms nodes and
                # sequence browser nodes, remove the unused sequence browser node, image nodes,
                # and transforms nodes, if they exist
                nodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLSequenceBrowserNode")
                nodes.UnRegister(None)
                # Ensure that there is an extra sequence browser node, since we need exactly
                # one sequence browser node at a time
                if nodes.GetNumberOfItems() == 2:
                  sequenceBrowserNodeToDelete = nodes.GetItemAsObject(0)
                    
                  # Remove the unused sequence browser node
                  slicer.mrmlScene.RemoveNode(sequenceBrowserNodeToDelete)

                  # Remove the unused Transforms Nodes Sequence, if it exists
                  nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLSequenceNode", "Transform Nodes Sequence")
                  nodes.UnRegister(None)
                  if nodes.GetNumberOfItems() == 2:
                    nodeToRemove = nodes.GetItemAsObject(0)
                    slicer.mrmlScene.RemoveNode(nodeToRemove)
                  
                  # Remove the unused Transforms Nodes Sequence containing each linear transform node, if it exists
                  nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLLinearTransformNode", "Transform Nodes Sequence")
                  nodes.UnRegister(None)
                  if nodes.GetNumberOfItems() == 2:
                    nodeToRemove = nodes.GetItemAsObject(0)
                    slicer.mrmlScene.RemoveNode(nodeToRemove.GetStorageNode())
                    slicer.mrmlScene.RemoveNode(nodeToRemove)
                
                  # Remove the unused Image Nodes Sequence, containing each image node, if it exists
                  nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLScalarVolumeNode", "Image Nodes Sequence")
                  nodes.UnRegister(None)
                  if nodes.GetNumberOfItems() == 2:
                    nodeToRemove = nodes.GetItemAsObject(0)
                    slicer.mrmlScene.RemoveNode(nodeToRemove)
                    
                  # Remove the image nodes of each slice view used to preserve the slice views
                  nodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLScalarVolumeNode")
                  nodes.UnRegister(None)
                  for node in nodes:
                    if node.GetName() == 'Image Nodes Sequence':
                      break
                    if node.GetName() == node.GetAttribute('Sequences.BaseName'):
                      slicer.mrmlScene.RemoveNode(node.GetDisplayNode())
                      slicer.mrmlScene.RemoveNode(node)
                self.overlayThicknessSlider.enabled = True
                # Build the orientation map once before any visualize() calls.
                # This permanently assigns each orientation to a view for this session.
                layoutManager = slicer.app.layoutManager()
                self.logic.buildOrientationMap(
                    self.customParamNode.sequenceBrowserNode,
                    self.customParamNode.sequenceNode2DImages,
                    layoutManager
                )


                # Load first image of the sequence when all required inputs are satisfied
                self.resetVisuals()
                
                
            else:
              # If the user inputted file in the Tranforms File input is not accepted, remove the nodes created
              # from the previously inputted transforms file, if it exists. Also, remove filepath in Transforms
              # File in the `Inputs` section since the input is invalid.

              # Remove the unused Transforms Nodes Sequence, if it exists
              nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLSequenceNode", "Transform Nodes Sequence")
              nodes.UnRegister(None)
              if nodes.GetNumberOfItems() == 1:
                nodeToRemove = nodes.GetItemAsObject(0)
                slicer.mrmlScene.RemoveNode(nodeToRemove)
              
              # Remove the unused Transforms Nodes Sequence containing each linear transform node, if it exists
              nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLLinearTransformNode", "Transform Nodes Sequence")
              nodes.UnRegister(None)
              if nodes.GetNumberOfItems() == 1:
                nodeToRemove = nodes.GetItemAsObject(0)
                slicer.mrmlScene.RemoveNode(nodeToRemove.GetStorageNode())
                slicer.mrmlScene.RemoveNode(nodeToRemove)

              # Remove filepath for the Transforms File in the `Inputs` section
              self.customParamNode.transformsFilePath = ''
              self.selectorTransformsFile.currentPath = ''

          #Deformation Field
          else:
            if len(self.deformationFieldPaths) > 0 and len(self.deformationFieldPaths) != self.customParamNode.totalImages:
                slicer.util.errorDisplay("Number of deformation field files must match number of cine images.", "Input Error")
                return
            # No DVFs provided — use identity transforms so the static segmentation
            # is displayed identically to Translation mode with no CSV file.
            elif len(self.deformationFieldPaths) == 0:
                numImages = self.customParamNode.totalImages
                transformsList = [[0.0, 0.0, 0.0] for _ in range(numImages)]
                transformsSequenceNode = self.logic.createTransformNodesFromTransformData(
                    shNode, transformsList, numImages
                )
                if not transformsSequenceNode:
                    return
                self.customParamNode.sequenceNodeTransforms = transformsSequenceNode

                sequenceBrowserNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", "Sequence Browser")
                sequenceBrowserNode.AddSynchronizedSequenceNode(self.customParamNode.sequenceNode2DImages)
                sequenceBrowserNode.AddSynchronizedSequenceNode(self.customParamNode.sequenceNodeTransforms)
                sequenceBrowserNode.SetSelectedItemNumber(0)
                sequenceBrowserNode.SetPlaybackRateFps(10)

                self.addObserver(sequenceBrowserNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
                self.customParamNode.sequenceBrowserNode = sequenceBrowserNode

                # Clean up any leftover browser node from a previous Apply press
                nodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLSequenceBrowserNode")
                nodes.UnRegister(None)
                if nodes.GetNumberOfItems() == 2:
                    oldBrowser = nodes.GetItemAsObject(0)
                    slicer.mrmlScene.RemoveNode(oldBrowser)

                self.overlayThicknessSlider.enabled = True
                layoutManager = slicer.app.layoutManager()
                self.logic.buildOrientationMap(
                    self.customParamNode.sequenceBrowserNode,
                    self.customParamNode.sequenceNode2DImages,
                    layoutManager
                )
                # resetVisuals() calls visualize() internally — no second call needed
                self.resetVisuals()
                return

            else: 
              # Create the SequenceNode to store the masks
              deformedMaskSequenceNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceNode", "Deformed Mask Sequence")
              self.customParamNode.deformedMaskSequenceNode = deformedMaskSequenceNode

              mask = sitk.ReadImage(self.customParamNode.path3DSegmentation)
              # Compute combined bounding box across all labels
              stats = sitk.LabelShapeStatisticsImageFilter()
              stats.Execute(mask)

              x_min = min(stats.GetBoundingBox(l)[0] for l in stats.GetLabels())
              y_min = min(stats.GetBoundingBox(l)[1] for l in stats.GetLabels())
              z_min = min(stats.GetBoundingBox(l)[2] for l in stats.GetLabels())
              x_max = max(stats.GetBoundingBox(l)[0] + stats.GetBoundingBox(l)[3] for l in stats.GetLabels())
              y_max = max(stats.GetBoundingBox(l)[1] + stats.GetBoundingBox(l)[4] for l in stats.GetLabels())
              z_max = max(stats.GetBoundingBox(l)[2] + stats.GetBoundingBox(l)[5] for l in stats.GetLabels())

              # Add margin to volume bounds
              margin = 10
              vol_size = mask.GetSize()
              crop_start = [max(0, x_min - margin), max(0, y_min - margin), max(0, z_min - margin)]
              crop_size  = [min(vol_size[0], x_max + margin) - crop_start[0],
                            min(vol_size[1], y_max + margin) - crop_start[1],
                            min(vol_size[2], z_max + margin) - crop_start[2]]

              # Crop mask to bounding box region
              croppedMask = sitk.RegionOfInterest(mask, crop_size, crop_start)

              # Create full-size empty volume to paste results into
              emptyVolume = sitk.Image(mask.GetSize(), mask.GetPixelID())
              emptyVolume.CopyInformation(mask)
              
              transforms = [sitk.ReadTransform(path) for path in self.deformationFieldPaths]
              # Create a progress/loading bar to display the progress of the deformation process
              progressDialog = qt.QProgressDialog("Applying Transformation", "Cancel",
                                                  0, len(transforms))
              progressDialog.minimumDuration = 0

              for i, tx in enumerate(transforms):
                  # If the 'Cancel' button was pressed, remove the partially-built sequence node and return to a default state
                  if progressDialog.wasCanceled:
                      slicer.mrmlScene.RemoveNode(deformedMaskSequenceNode)
                      self.customParamNode.deformedMaskSequenceNode = None
                      return
                  try:
                      deformedCrop = sitk.Resample(croppedMask, croppedMask, tx, sitk.sitkNearestNeighbor)

                      # Paste deformed crop back into full-size volume
                      deformedMask = sitk.Paste(emptyVolume, deformedCrop, deformedCrop.GetSize(), [0,0,0], crop_start)

                      # Create volume node directly in memory without saving to disk
                      volumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", f"DeformedMask_{i}")
                      
                      # Convert SimpleITK image to numpy array and update the volume node
                      deformedMaskArray = sitk.GetArrayFromImage(deformedMask)
                      slicer.util.updateVolumeFromArray(volumeNode, deformedMaskArray)
                      
                      # Copy the image properties from the original mask.
                      # SimpleITK reports geometry in LPS; Slicer stores RAS.
                      # RAS = diag(-1,-1,1) * LPS, so negate the X and Y
                      # components of both the origin and the direction matrix.
                      lpsOrigin = mask.GetOrigin()
                      volumeNode.SetOrigin(-lpsOrigin[0], -lpsOrigin[1], lpsOrigin[2])
                      volumeNode.SetSpacing(mask.GetSpacing())

                      direction = mask.GetDirection()
                      vtkMatrix = vtk.vtkMatrix4x4()
                      for row in range(3):
                          sign = -1.0 if row < 2 else 1.0
                          for col in range(3):
                              vtkMatrix.SetElement(row, col, sign * direction[row * 3 + col])
                      volumeNode.SetIJKToRASDirectionMatrix(vtkMatrix)
                      
                      deformedMaskSequenceNode.SetDataNodeAtValue(volumeNode, str(i))
                      # Clean up: remove the standalone node from the scene now that it's stored in the sequence
                      shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
                      itemID = shNode.GetItemByDataNode(volumeNode)
                      if itemID:
                          shNode.RemoveItem(itemID)

                  except Exception as e:
                      slicer.util.errorDisplay(f"Failed to apply deformation field to mask {i}: {e}")
                      return
                  
                  #  Update how far we are in the progress bar
                  progressDialog.setValue(i + 1)
                  slicer.util.forceRenderAllViews()
                  slicer.app.processEvents()


              # Playback setup
              sequenceBrowserNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", "Sequence Browser")
              sequenceBrowserNode.AddSynchronizedSequenceNode(self.customParamNode.sequenceNode2DImages)
              sequenceBrowserNode.AddSynchronizedSequenceNode(deformedMaskSequenceNode)

              sequenceBrowserNode.SetRecording(deformedMaskSequenceNode, False)
              sequenceBrowserNode.SetPlayback(deformedMaskSequenceNode, True)
              sequenceBrowserNode.SetSelectedItemNumber(0)
              sequenceBrowserNode.SetPlaybackRateFps(10)
              self.overlayThicknessSlider.enabled = True

              layoutManager = slicer.app.layoutManager()
              for name in layoutManager.sliceViewNames():
                  sliceWidget = layoutManager.sliceWidget(name)
                  sliceCompositeNode = sliceWidget.mrmlSliceCompositeNode()

                  currentItemIndex = sequenceBrowserNode.GetSelectedItemNumber()
                  currentLabelNode = deformedMaskSequenceNode.GetDataNodeAtValue(str(currentItemIndex))

                  if currentLabelNode:
                      sliceCompositeNode.SetLabelVolumeID(currentLabelNode.GetID())
                      sliceCompositeNode.SetLabelOpacity(self.customParamNode.opacity)
                      sliceWidget.mrmlSliceNode().SetUseLabelOutline(self.customParamNode.overlayAsOutline)

              self.addObserver(sequenceBrowserNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

              # Register sequence browser (for playback control in the UI)
              self.customParamNode.sequenceBrowserNode = sequenceBrowserNode

              # Done—reset visuals to show new playback
              self.resetVisuals()

              self.updateGUIFromParameterNode()

    finally:
      appliedNow = (caller == "applyTransformsButton" and event == "clicked")
      hasSegmentation = bool(self.customParamNode.node3DSegmentation)
      hasTransforms = bool(self.customParamNode.sequenceNodeTransforms or
                           self.customParamNode.deformedMaskSequenceNode)
      hasImages = bool(self.customParamNode.sequenceNode2DImages)
      if appliedNow and hasSegmentation and hasTransforms:
        self._appliedState = "overlay"    
      elif appliedNow and hasImages:
        self._appliedState = "images"      
      else:
        self._appliedState = None          
      self.customParamNode.EndModify(wasModified)
      self._updatingGUIFromParameterNode = False
      self.updateGUIFromParameterNode()  # refresh UI now that loading is done

  def applyPrewarpedMode(self, shNode):
    segFiles = sorted(self.customParamNode.files3DSegmentations)
    numImages = self.customParamNode.totalImages

    # Hard enforcement: exactly one mask per cine image
    if len(segFiles) != numImages:
        slicer.util.errorDisplay(
            f"Number of segmentation files ({len(segFiles)}) must match the "
            f"number of cine images ({numImages}).\n"
            "Load either exactly one segmentation, or one segmentation file for each cine image.",
            "Input Error")
        return

    # Remove leftovers from a previous Apply
    for className, name in [("vtkMRMLSequenceNode", "Per-Frame Mask Sequence"),
                            ("vtkMRMLScalarVolumeNode", "3D Segmentation"),
                            ("vtkMRMLLabelMapVolumeNode", "3D Segmentation Label Map")]:
        nodes = slicer.mrmlScene.GetNodesByClassByName(className, name)
        nodes.UnRegister(None)
        for i in range(nodes.GetNumberOfItems()):
            slicer.mrmlScene.RemoveNode(nodes.GetItemAsObject(i))

    # Load all masks as individual frames into a sequence node.
    masksSequenceNode, cancelled = self.logic.loadMasksIntoSequenceNode(shNode, segFiles)
    if cancelled or masksSequenceNode is None:
        return
    self.customParamNode.deformedMaskSequenceNode = masksSequenceNode

    # Load the first mask separately as the display anchor: visualize() drives
    # color table / outline / thickness through this label map, and
    # _applyTransformToLabelMap swaps its image data every frame.
    segmentationNode = slicer.util.loadVolume(segFiles[0], {"singleFile": True, "show": False})
    segmentationNode.SetName("3D Segmentation")
    self.customParamNode.node3DSegmentation = shNode.GetItemByDataNode(segmentationNode)

    volumesModuleLogic = slicer.modules.volumes.logic()
    segmentationLabelMap = slicer.mrmlScene.AddNewNodeByClass(
        'vtkMRMLLabelMapVolumeNode', "3D Segmentation Label Map")
    volumesModuleLogic.CreateLabelVolumeFromVolume(
        slicer.mrmlScene, segmentationLabelMap, segmentationNode)
    self.customParamNode.node3DSegmentationLabelMap = shNode.GetItemByDataNode(segmentationLabelMap)

    # Color buttons based on the first mask's labels
    segArray = arrayFromVolume(segmentationNode)
    nonZeroLabels = np.unique(segArray)
    nonZeroLabels = nonZeroLabels[nonZeroLabels != 0]
    self.addAdditionalOverlayColorButtons(
        list(range(1, len(nonZeroLabels) + 1)), segmentationNode)
    self.applyPendingLabelColors()
    self.logic.clearSliceForegrounds()

    # Playback setup — mirrors the Displacement Field path
    sequenceBrowserNode = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLSequenceBrowserNode", "Sequence Browser")
    sequenceBrowserNode.AddSynchronizedSequenceNode(self.customParamNode.sequenceNode2DImages)
    sequenceBrowserNode.AddSynchronizedSequenceNode(masksSequenceNode)
    sequenceBrowserNode.SetRecording(masksSequenceNode, False)
    sequenceBrowserNode.SetPlayback(masksSequenceNode, True)
    sequenceBrowserNode.SetSelectedItemNumber(0)
    sequenceBrowserNode.SetPlaybackRateFps(self.customParamNode.fps)

    self.addObserver(sequenceBrowserNode, vtk.vtkCommand.ModifiedEvent,
                     self.updateGUIFromParameterNode)
    self.customParamNode.sequenceBrowserNode = sequenceBrowserNode

    # Clean up any leftover browser from a previous Apply
    nodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLSequenceBrowserNode")
    nodes.UnRegister(None)
    if nodes.GetNumberOfItems() == 2:
        slicer.mrmlScene.RemoveNode(nodes.GetItemAsObject(0))

    self.overlayThicknessSlider.enabled = True
    self.logic.buildOrientationMap(sequenceBrowserNode,
                                   self.customParamNode.sequenceNode2DImages,
                                   slicer.app.layoutManager())
    self.resetVisuals()

  def onTransformsFilePathChange(self):
    
    def clearColumnSeletors(self):
      self.columnXSelector.clear()
      self.columnXSelector.enabled = False
      self.columnYSelector.clear()
      self.columnYSelector.enabled = False
      self.columnZSelector.clear()
      self.columnZSelector.enabled = False
    def addItemToColumnSeletors(self,headers):
      self.columnXSelector.enabled = True
      self.columnYSelector.enabled = True
      self.columnZSelector.enabled = True
      
      self.columnXSelector.addItems(headers)     
      self.columnYSelector.addItems(headers)
      self.columnZSelector.addItems(headers)
      
      self.columnXSelector.setCurrentIndex(0)
      self.columnYSelector.setCurrentIndex(1)
      self.columnZSelector.setCurrentIndex(2)
      
      self.transformationAppliedLabel.setVisible(False)
      self.applyTransformButton.enabled = True

    def onSequenceChange(self):
      """
      Allows for the reuploading of transforms file during active sequence
      """
      # Changes transforms file path to new one
      if self.customParamNode.transformsFilePath != self.selectorTransformsFile.currentPath:
        self.customParamNode.transformsFilePath = self.selectorTransformsFile.currentPath

      # Check if sequence is actively playing
      activePlay = self.customParamNode.sequenceBrowserNode and \
        hasattr(self.customParamNode.sequenceBrowserNode, 'GetPlaybackActive') and \
        self.customParamNode.sequenceBrowserNode.GetPlaybackActive()

      if activePlay:
        # Stop sequence
        self.customParamNode.sequenceBrowserNode.SetPlaybackActive(False)

        # Removes existing transforms nodes and sequence nodes
        nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLLinearTransformNode", "Transform Nodes Sequence")
        nodes.UnRegister(None)
        for node in nodes:
          slicer.mrmlScene.RemoveNode(node)

        nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLSequenceNode", "Transform Nodes Sequence")
        nodes.UnRegister(None)
        for node in nodes:
            slicer.mrmlScene.RemoveNode(node)

    self._appliedState = None
    onSequenceChange(self)

    clearColumnSeletors(self)
      
    addItemToColumnSeletors(self, self.logic.getColumnNamesFromTransformsInput(self.selectorTransformsFile.currentPath))
    
  def onPlayButton(self):
    """
    Begin the playback when a user clicks the "Play" button and pause when user clicks the "Pause" button.
    """
    hasSegmentation = bool(self.customParamNode.node3DSegmentation)
    hasTransforms = bool(self.customParamNode.sequenceNodeTransforms or
                        self.customParamNode.deformedMaskSequenceNode)
    # In images-only mode, visualizeImagesOnly handles all views uniformly
    # Not letting onPlayButton touch individual slice views to fix the disconnected playback on the red
    if not hasSegmentation and not hasTransforms:
        if self.customParamNode.sequenceBrowserNode.GetPlaybackActive():
            # pause
            self.customParamNode.sequenceBrowserNode.SetPlaybackActive(False)
        else:
            # play
            self.customParamNode.sequenceBrowserNode.SetPlaybackActive(True)
        return
    layoutManager = slicer.app.layoutManager()
    self.customParamNode.sequenceBrowserNode.SetPlaybackItemSkippingEnabled(False) # Fixes image skipping bug on slower machines
    proxy2DImageNode = self.customParamNode.sequenceBrowserNode.GetProxyNode(self.customParamNode.sequenceNode2DImages)
    sliceWidget = self.logic.getSliceWidget(layoutManager, proxy2DImageNode)
    sliceView = sliceWidget.sliceView()
    
    ## Pause sequence
    if self.customParamNode.sequenceBrowserNode.GetPlaybackActive():
      # if we are playing, click this button will pause the playback
      self.customParamNode.sequenceBrowserNode.SetPlaybackActive(False)
      self.updatePlaybackButtons(True)
      # Synchronize `sequenceSlider` and `currentFrameInputBox` if either is modified by the user
      self.sequenceSlider.setValue(self.currentFrameInputBox.value)
      self.currentFrameInputBox.setValue(self.sequenceSlider.value)
      self.customParamNode.sequenceBrowserNode.SetSelectedItemNumber(self.currentFrameInputBox.value - 1)
      
      # Add an observer to the 'Current Alignment' Text to preserve the text when the sequence is paused
      sliceView.cornerAnnotation().AddObserver(vtk.vtkCommand.ModifiedEvent, lambda caller, event: caller.SetText(vtk.vtkCornerAnnotation.UpperLeft, 'Current Alignment'))
      sliceView.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.UpperLeft, "Current Alignment")

      # Rename the text in the bottom left part of slice view, and preserve the text
      for color in self.logic.backgrounds:
        background = getattr(self.logic, f"{color.lower()}Background")
        if background is not None:
          imageFileNameText = slicer.mrmlScene.GetNodeByID(f"vtkMRMLSliceCompositeNode{color}").GetNodeReference('backgroundVolume').GetAttribute('Sequences.BaseName')
          sliceView = slicer.app.layoutManager().sliceWidget(color).sliceView()
          sliceView.cornerAnnotation().SetText(0, imageFileNameText)
          # Add an observer to the Text displaying the image file name to preserve the text when the sequence is paused
          sliceView.cornerAnnotation().AddObserver(vtk.vtkCommand.ModifiedEvent, lambda caller, event, text=imageFileNameText: caller.SetText(0, text))
    ## Play sequence
    else:
      # Remove any observer in each sliceview before playing the sequence
      for color in self.logic.backgrounds:
        sliceViewWindow = slicer.app.layoutManager().sliceWidget(color).sliceView()
        if sliceViewWindow.cornerAnnotation().HasObserver(vtk.vtkCommand.ModifiedEvent):
          sliceViewWindow.cornerAnnotation().RemoveAllObservers()

      # If the image to be played is changed when paused, start the playback at that image number
      self.customParamNode.sequenceBrowserNode.SetSelectedItemNumber(self.currentFrameInputBox.value - 1)
      # if we are not playing, click this button will start the playback
      self.customParamNode.sequenceBrowserNode.SetPlaybackRateFps(self.customParamNode.fps/2)
      self.customParamNode.sequenceBrowserNode.SetPlaybackActive(True)

  def applyInitialColorToLabel(self, labelValue, colorHex, segmentationNode):
    """Apply an initial color to a specific label in the color table"""
   
    
    # Convert hex color to RGB values (0-1 range)
    color = qt.QColor(colorHex)
    r = color.red() / 255.0
    g = color.green() / 255.0
    b = color.blue() / 255.0
    
    
    # Check if the label map has been created yet
    if not hasattr(self.customParamNode, 'node3DSegmentationLabelMap') or not self.customParamNode.node3DSegmentationLabelMap:
   
        # Store the color to apply later when the label map is created
        if not hasattr(self, 'pendingLabelColors'):
            self.pendingLabelColors = {}
        self.pendingLabelColors[labelValue] = (r, g, b)
        return
    
    # Get the label map node that's actually being displayed
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    labelMapNode = shNode.GetItemDataNode(self.customParamNode.node3DSegmentationLabelMap)
    
    if not labelMapNode:
        
        # Store the color to apply later
        if not hasattr(self, 'pendingLabelColors'):
            self.pendingLabelColors = {}
        self.pendingLabelColors[labelValue] = (r, g, b)
        return
        
    displayNode = labelMapNode.GetDisplayNode()
    
    if displayNode:
        colorNode = displayNode.GetColorNode()

        # Clone the color node if it's not editable
        if colorNode.GetType() != slicer.vtkMRMLColorTableNode.User:
  

            colorNodeCopy = slicer.vtkMRMLColorTableNode()
            colorNodeCopy.SetTypeToUser()

            originalCount = colorNode.GetNumberOfColors()
            colorNodeCopy.SetNumberOfColors(originalCount)

            for i in range(originalCount):
                rgba = [0, 0, 0, 0]
                colorNode.GetColor(i, rgba)
                colorNodeCopy.SetColor(i, f"Label {i}", *rgba)

            slicer.mrmlScene.AddNode(colorNodeCopy)
            displayNode.SetAndObserveColorNodeID(colorNodeCopy.GetID())
            colorNode = colorNodeCopy

        # Ensure color table is big enough
        if labelValue >= colorNode.GetNumberOfColors():
            colorNode.SetNumberOfColors(labelValue + 1)

        # Set the initial color
        colorNode.SetColor(labelValue, f"Label {labelValue}", r, g, b, 1.0)
  

        # Force apply the color table to the display node
        displayNode.SetAndObserveColorNodeID(colorNode.GetID())
        displayNode.Modified()
        colorNode.Modified()

  def applyPendingLabelColors(self):
    """Apply any colors that were stored before the label map was created"""
    if not hasattr(self, 'pendingLabelColors') or not self.pendingLabelColors:
        return
        
    
    # Get the label map node
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    labelMapNode = shNode.GetItemDataNode(self.customParamNode.node3DSegmentationLabelMap)
    
    if not labelMapNode:
       return
        
    displayNode = labelMapNode.GetDisplayNode()
    if not displayNode:
        return
        
    colorNode = displayNode.GetColorNode()

    # Clone the color node if it's not editable
    if colorNode.GetType() != slicer.vtkMRMLColorTableNode.User:

        colorNodeCopy = slicer.vtkMRMLColorTableNode()
        colorNodeCopy.SetTypeToUser()

        originalCount = colorNode.GetNumberOfColors()
        colorNodeCopy.SetNumberOfColors(originalCount)

        for i in range(originalCount):
            rgba = [0, 0, 0, 0]
            colorNode.GetColor(i, rgba)
            colorNodeCopy.SetColor(i, f"Label {i}", *rgba)

        slicer.mrmlScene.AddNode(colorNodeCopy)
        displayNode.SetAndObserveColorNodeID(colorNodeCopy.GetID())
        colorNode = colorNodeCopy

    # Apply all pending colors
    maxLabel = max(self.pendingLabelColors.keys()) if self.pendingLabelColors else 0
    if maxLabel >= colorNode.GetNumberOfColors():
        colorNode.SetNumberOfColors(maxLabel + 1)

    for labelValue, (r, g, b) in self.pendingLabelColors.items():

        colorNode.SetColor(labelValue, f"Label {labelValue}", r, g, b, 1.0)

    # Force apply the color table to the display node
    
    displayNode.Modified()
    colorNode.Modified()
    
    # Clear the pending colors since they've been applied
    self.pendingLabelColors = {}


  def changeLabelColor(self, labelValue, segmentationNode, checked=None):
    currentColor = qt.QColor(0, 179, 0)

    colorDialog = qt.QColorDialog()
    colorDialog.setCurrentColor(currentColor)
    colorDialog.setOption(qt.QColorDialog.ShowAlphaChannel, False)

    if colorDialog.exec_() == qt.QDialog.Accepted:
        selected = colorDialog.selectedColor()
        if selected.isValid():
            rgb = [selected.redF(), selected.greenF(), selected.blueF()]

            button = self.labelColorButtons.get(labelValue)
            if button:
                button.setStyleSheet(f"background-color: {selected.name()};")

            # Get the label map node actually being displayed
            shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
            labelMapNode = shNode.GetItemDataNode(self.customParamNode.node3DSegmentationLabelMap)
            displayNode = labelMapNode.GetDisplayNode()

            if displayNode:
                colorNode = displayNode.GetColorNode()

                # Clone color node if not editable
                if colorNode.GetType() != slicer.vtkMRMLColorTableNode.User:
                    colorNodeCopy = slicer.vtkMRMLColorTableNode()
                    colorNodeCopy.SetTypeToUser()

                    originalCount = colorNode.GetNumberOfColors()
                    colorNodeCopy.SetNumberOfColors(originalCount)

                    for i in range(originalCount):
                        rgba = [0, 0, 0, 0]
                        colorNode.GetColor(i, rgba)
                        colorNodeCopy.SetColor(i, f"Label {i}", *rgba)

                    slicer.mrmlScene.AddNode(colorNodeCopy)
                    displayNode.SetAndObserveColorNodeID(colorNodeCopy.GetID())
                    colorNode = colorNodeCopy

                # Ensure color table is big enough
                if labelValue >= colorNode.GetNumberOfColors():
                    colorNode.SetNumberOfColors(labelValue + 1)

                # Set the new color at the button label index
                colorNode.SetColor(labelValue, f"Label {labelValue}", *rgb, 1.0)

                # Also write to the actual voxel values in the volume
                # because the slice view renderer looks up color by voxel value,
                # not by button label index (e.g. voxels are 255 but button is label 1)
                labelArray = slicer.util.arrayFromVolume(labelMapNode)
                uniqueNonZero = sorted([int(l) for l in np.unique(labelArray) if l != 0])
                voxelToButtonLabel = {voxelVal: idx + 1 for idx, voxelVal in enumerate(uniqueNonZero)}

                for voxelVal, buttonLabel in voxelToButtonLabel.items():
                    if buttonLabel == labelValue:
                        # This voxel value corresponds to the button the user clicked
                        # Write the new color at the voxel value index too
                        if voxelVal >= colorNode.GetNumberOfColors():
                            colorNode.SetNumberOfColors(voxelVal + 1)
                        colorNode.SetColor(voxelVal, f"Label {voxelVal}", *rgb, 1.0)

                displayNode.SetAndObserveColorNodeID(colorNode.GetID())



                # Update nodes
                colorNode.Modified()
                displayNode.Modified()
                segmentationNode.Modified()

                # Refresh all slice views
                layoutManager = slicer.app.layoutManager()
                for sliceViewName in layoutManager.sliceViewNames():
                    sliceWidget = layoutManager.sliceWidget(sliceViewName)
                    if sliceWidget:
                        sliceCompositeNode = sliceWidget.mrmlSliceCompositeNode()
                        if sliceCompositeNode and sliceCompositeNode.GetLabelVolumeID() == labelMapNode.GetID():
                            oldLabelVolumeID = sliceCompositeNode.GetLabelVolumeID()
                            sliceCompositeNode.SetLabelVolumeID(None)
                            sliceCompositeNode.SetLabelVolumeID(oldLabelVolumeID)
                            sliceCompositeNode.Modified()

                # Update existing 3D rendering transfer functions to match new label colors
                volumeRenderingLogic = slicer.modules.volumerendering.logic()
                volumeRenderingDisplayNode = volumeRenderingLogic.GetFirstVolumeRenderingDisplayNode(labelMapNode)

                if volumeRenderingDisplayNode:
                    volumePropertyNode = volumeRenderingDisplayNode.GetVolumePropertyNode()
                    if volumePropertyNode:
                        vtkVP = volumePropertyNode.GetVolumeProperty()

                        # Get the EXISTING transfer functions and modify in place
                        # (VTK ignores SetColor() if you pass a new object)
                        ctf = vtkVP.GetRGBTransferFunction()
                        otf = vtkVP.GetScalarOpacity()

                        ctf.RemoveAllPoints()
                        otf.RemoveAllPoints()

                        labelArray = slicer.util.arrayFromVolume(labelMapNode)
                        uniqueLabels = np.unique(labelArray)

                        # Build a mapping from actual voxel value → button label index
                        # The button is always built counting from 1 (first organ = 1, second = 2, etc.)
                        # But the voxel value in the file can be anything (1, 255, etc.)
                        # Example: voxels [0, 255] → {255: 1}
                        # Example: voxels [0, 1, 2, 3] → {1: 1, 2: 2, 3: 3}
                        uniqueNonZero = sorted([int(l) for l in uniqueLabels if l != 0])
                        voxelToButtonLabel = {voxelVal: idx + 1 for idx, voxelVal in enumerate(uniqueNonZero)}

                        ctf.AddRGBPoint(0, 0.0, 0.0, 0.0)
                        otf.AddPoint(0, 0.0)

                        for label in uniqueLabels:
                            if label == 0:
                                continue
                            labelInt = int(label)

                            # Use the button label index to look up the color the user picked
                            colorIdx = voxelToButtonLabel.get(labelInt, labelInt)

                            rgba = [0.0, 0.0, 0.0, 0.0]
                            if colorIdx < colorNode.GetNumberOfColors():
                                colorNode.GetColor(colorIdx, rgba)
                            ctf.AddRGBPoint(label, rgba[0], rgba[1], rgba[2])
                            otf.AddPoint(label, self.customParamNode.opacity)

                        volumePropertyNode.Modified()
                        volumeRenderingDisplayNode.Modified()
                else:
                    # Create volume rendering if it doesn't exist
                    volumeRenderingDisplayNode = volumeRenderingLogic.CreateDefaultVolumeRenderingNodes(labelMapNode)
                    if volumeRenderingDisplayNode:
                        volumePropertyNode = volumeRenderingDisplayNode.GetVolumePropertyNode()
                        if volumePropertyNode:
                            vtkVP = volumePropertyNode.GetVolumeProperty()

                            # VTK ignores SetColor() on a new object
                            ctf = vtkVP.GetRGBTransferFunction()
                            otf = vtkVP.GetScalarOpacity()

                            ctf.RemoveAllPoints()
                            otf.RemoveAllPoints()

                            labelArray = slicer.util.arrayFromVolume(labelMapNode)
                            uniqueLabels = np.unique(labelArray)

                            # Build a mapping from actual voxel value → button label index
                            # The button is always built counting from 1 (first organ = 1, second = 2, etc.)
                            # But the voxel value in the file can be anything (1, 255, etc.)
                            # Example: voxels [0, 255] → {255: 1}
                            # Example: voxels [0, 1, 2, 3] → {1: 1, 2: 2, 3: 3}
                            uniqueNonZero = sorted([int(l) for l in uniqueLabels if l != 0])
                            voxelToButtonLabel = {voxelVal: idx + 1 for idx, voxelVal in enumerate(uniqueNonZero)}

                            ctf.AddRGBPoint(0, 0.0, 0.0, 0.0)
                            otf.AddPoint(0, 0.0)

                            for label in uniqueLabels:
                                if label == 0:
                                    continue
                                labelInt = int(label)

                                # Use the button label index to look up the color the user picked
                                colorIdx = voxelToButtonLabel.get(labelInt, labelInt)

                                rgba = [0.0, 0.0, 0.0, 0.0]
                                if colorIdx < colorNode.GetNumberOfColors():
                                    colorNode.GetColor(colorIdx, rgba)
                                ctf.AddRGBPoint(label, rgba[0], rgba[1], rgba[2])
                                otf.AddPoint(label, self.customParamNode.opacity)

                            volumePropertyNode.Modified()
                            volumeRenderingDisplayNode.Modified()

                        volumeRenderingDisplayNode.SetVisibility(True)

                # Force render updates
                slicer.util.forceRenderAllViews()
                labelMapNode.Modified()





  def addAdditionalOverlayColorButtons(self, labelValues, segmentationNode):
    # Initialize the labelColorButtons dictionary if it doesn't exist
    if not hasattr(self, 'labelColorButtons'):
        self.labelColorButtons = {}
    
    # Define unique colors for each label
    predefinedColors = [
        "#00B300",  # Green (label 1)
        "#FF4500",  # Red-Orange (label 2)
        "#1E90FF",  # Dodger Blue (label 3)
        "#FFD700",  # Gold (label 4)
        "#FF1493",  # Deep Pink (label 5)
        "#ADFF2F",  # Green Yellow (label 6)
        "#B8860B",  # Dark Goldenrod (label 7)
        "#FF6347",  # Tomato (label 8)
        "#40E0D0",  # Turquoise (label 9)
        "#8A2BE2",  # Blue Violet (label 10)
        "#DC143C",  # Crimson (label 11)
        "#7CFC00",  # Lawn Green (label 12)
        "#20B2AA",  # Light Sea Green (label 13)
        "#FF8C00",  # Dark Orange (label 14)
        "#C71585",  # Medium Violet Red (label 15)
        "#4682B4",  # Steel Blue (label 16)
        "#D2691E",  # Chocolate (label 17)
        "#9ACD32",  # Yellow Green (label 18)
        "#BA55D3",  # Medium Orchid (label 19)
        "#00CED1",  # Dark Turquoise (label 20)
        "#FF69B4",  # Hot Pink (label 21)
        "#556B2F",  # Dark Olive Green (label 22)
        "#5F9EA0",  # Cadet Blue (label 23)
        "#A0522D",  # Sienna (label 24)
        "#6A5ACD",  # Slate Blue (label 25)
        "#00FA9A",  # Medium Spring Green (label 26)
        "#FFB6C1",  # Light Pink (label 27)
        "#9932CC",  # Dark Orchid (label 28)
        "#FA8072",  # Salmon (label 29)
        "#2E8B57",  # Sea Green (label 30)        

    ]
    
    
    
    for label in labelValues:
        
        i = label - 1  # index for layout math
        row = i // 5 # 5 buttons per row
        col = (i % 5) * 2  # label and button side by side

        labelText = qt.QLabel(f"Label {label} Color:")
        labelText.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
        self.overlayColoursLayout.addWidget(labelText, row, col)

        button = qt.QPushButton()
        button.setFixedSize(24, 24)
        
        # Assign unique color based on label index
        colorIndex = (label - 1) % len(predefinedColors)
        color = predefinedColors[colorIndex]
        button.setStyleSheet(f"background-color: {color};")
        
        button.clicked.connect(functools.partial(self.changeLabelColor, label, segmentationNode))
        self.overlayColoursLayout.addWidget(button, row, col + 1)

        self.labelColorButtons[label] = button
        
        # Apply this color to the color table immediately
        self.applyInitialColorToLabel(label, color, segmentationNode)


  def onStopButton(self):
    """
    Stop the playback, after the current image's visualization completes.
    """
    self.customParamNode.sequenceBrowserNode.SetPlaybackActive(False)
    self.customParamNode.sequenceBrowserNode.SetSelectedItemNumber(0)
    self.sequenceSlider.setValue(1)
    self.currentFrameInputBox.setValue(1)
    self.customParamNode.sequenceBrowserNode.SetSelectedItemNumber(1)

    # Remove all observers
    for color in self.logic.backgrounds:
      sliceViewWindow = slicer.app.layoutManager().sliceWidget(color).sliceView()
      if sliceViewWindow.cornerAnnotation().HasObserver(vtk.vtkCommand.ModifiedEvent):
        sliceViewWindow.cornerAnnotation().RemoveAllObservers()
    # Reset slice views to what they look when inputs are just loaded
    self.resetVisuals()

  def getSliceDict(self):
    # This dictionary creates a snapshot in time, before displaying any new images to remember the FOV & XYZ coordinates of all slice views
    imageDict = {'Yellow': None, 'Red': None, 'Green': None}
    layoutManager = slicer.app.layoutManager()
    for name in layoutManager.sliceViewNames(): 
      sliceWidgetBackground = layoutManager.sliceWidget(name).mrmlSliceCompositeNode().GetBackgroundVolumeID()
      # Checks if the current slice we're checking is displaying an image
      if sliceWidgetBackground is not None: 
        sliceNode = slicer.mrmlScene.GetNodeByID(f'vtkMRMLSliceNode{name}')
        imageDict[name] = [sliceNode.GetFieldOfView(), sliceNode.GetXYZOrigin()]   
    return imageDict
  
  def editSliceView(self, imageDict):
    # Loop over all the slice views, and find the one that has changed FOV or XYZ coordinates
    sliceOfNewImage = None
    layoutManager = slicer.app.layoutManager()
    for name in layoutManager.sliceViewNames():
      currentSliceNode =  slicer.mrmlScene.GetNodeByID(f'vtkMRMLSliceNode{name}')
      currentSliceNodeFOV = currentSliceNode.GetFieldOfView()
      currentSliceNodeXYZ = currentSliceNode.GetXYZOrigin()
      if imageDict[name] != None and (currentSliceNodeFOV != imageDict[name][0] or currentSliceNodeXYZ != imageDict[name][1]):
        sliceOfNewImage = name
        
    # Apply FOV and XYZ values to the newly loaded image from imageDict
    if sliceOfNewImage != None:
      sliceNode = slicer.mrmlScene.GetNodeByID(f'vtkMRMLSliceNode{sliceOfNewImage}')
      sliceNode.SetXYZOrigin(imageDict[sliceOfNewImage][1][0], imageDict[sliceOfNewImage][1][1], imageDict[sliceOfNewImage][1][2])
      sliceNode.SetFieldOfView(imageDict[sliceOfNewImage][0][0], imageDict[sliceOfNewImage][0][1], imageDict[sliceOfNewImage][0][2])

  def updateViewMoreIcon(self):
    # Changes icon image between black icon and white icon depending on if user is using light or dark mode
    isDarkMode = slicer.app.palette().color(qt.QPalette.Window).lightness() < 128

    if isDarkMode != self.isDarkMode:
      self.isDarkMode = isDarkMode
      iconPath = os.path.join(self.mediaIconsPath, 'ViewMore.png' if isDarkMode else 'ViewMore2.png')
      icon = qt.QIcon(iconPath)
      self.viewMoreButton.setIcon(icon)
      self.viewMoreButton.setIconSize(qt.QSize(24, 19))
      if hasattr(self, 'viewMoreSegButton'):
            self.viewMoreSegButton.setIcon(icon)
            self.viewMoreSegButton.setIconSize(qt.QSize(24, 19))

  def onMultiFileBrowse(self):
    # Opens a file dialogue for the user to select cine images
    fileDialog = qt.QFileDialog()
    fileDialog.setFileMode(qt.QFileDialog.ExistingFiles)  # Allow selection of multiple files

    # Create a filter for only supported file formats
    supportedFormats = ["*.mha", "*.dcm", "*.nrrd", "*.nii", "*.hdr", "*.img", "*.nhdr", "*.mhd", "*.raw", "*.nii.gz"]
    filterString = "Supported Files ({})".format(" ".join(supportedFormats))
    fileDialog.setNameFilter(filterString)

    if fileDialog.exec():
      selectedFiles = fileDialog.selectedFiles()
      selectedFiles = sorted(list(selectedFiles))
      self.selector2DImagesFiles.addPaths(selectedFiles)
  
  def onBrowseSegmentationFiles(self):
    fileDialog = qt.QFileDialog()
    fileDialog.setFileMode(qt.QFileDialog.ExistingFiles)
    supportedFormats = ["*.mha", "*.dcm", "*.nrrd", "*.nii", "*.hdr", "*.img", "*.nhdr", "*.nii.gz"]
    fileDialog.setNameFilter("Supported Files ({})".format(" ".join(supportedFormats)))
    if fileDialog.exec():
        self.selector3DSegmentationFiles.addPaths(sorted(list(fileDialog.selectedFiles())))

  def onDeleteImagesButton(self):
    # Removes the cine images from the multi file selector
    self.selector2DImagesFiles.clear()
    self.customParamNode.files2DImages = []

  def onOverlayThicknessChange(self):
    # Allows the user to adjust the thickness of the overlay
    self.customParamNode.overlayThickness = int(self.overlayThicknessSlider.value)
    thickness = self.customParamNode.overlayThickness

    # Translation path: static segmentation label map
    if self.customParamNode.node3DSegmentationLabelMap:
      shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
      labelMapNode = shNode.GetItemDataNode(self.customParamNode.node3DSegmentationLabelMap)
      if labelMapNode and labelMapNode.GetDisplayNode():
        labelMapNode.GetDisplayNode().SetSliceIntersectionThickness(thickness)

    # Displacement Field path: the proxy node of the deformed mask sequence
    if self.customParamNode.deformedMaskSequenceNode and self.customParamNode.sequenceBrowserNode:
      proxyNode = self.customParamNode.sequenceBrowserNode.GetProxyNode(
          self.customParamNode.deformedMaskSequenceNode)
      if proxyNode and proxyNode.GetDisplayNode():
        proxyNode.GetDisplayNode().SetSliceIntersectionThickness(thickness)

    slicer.util.forceRenderAllViews()


  def onViewMoreClicked(self, selector):
    # Opens up a dialog displaying selected files when the user clicks "View More"
    dialog = qt.QDialog()
    dialog.setWindowTitle("Selected Files")
    dialog.setMinimumSize(400, 300)
    layout = qt.QVBoxLayout(dialog)

    tableWidget = qt.QTableWidget()
    tableWidget.setColumnCount(1)
    tableWidget.setHorizontalHeaderLabels(["File"])
    tableWidget.horizontalHeader().setStretchLastSection(True)
    tableWidget.verticalHeader().setVisible(False)
    tableWidget.setShowGrid(False)
    tableWidget.setAlternatingRowColors(True)

    # Populate the table
    for path in selector.paths:
        rowPosition = tableWidget.rowCount
        tableWidget.insertRow(rowPosition)
        tableWidget.setItem(rowPosition, 0, qt.QTableWidgetItem(os.path.basename(path)))

    layout.addWidget(tableWidget)

    # Add an "OK" button
    okButton = qt.QPushButton("OK")
    okButton.clicked.connect(lambda: dialog.done(qt.QDialog.Accepted))
    layout.addWidget(okButton)

    isDarkMode = slicer.app.palette().color(qt.QPalette.Window).lightness() < 128

    # Apply grey/darker grey pattern
    if isDarkMode:
      # Dark mode styling
      dialog.setStyleSheet("""
          QDialog, QTableWidget { background-color: #2e2e2e; color: white; }
          QTableWidget::item { padding: 5px; }
          QTableWidget::item:selected { background-color: #3a3a3a; }
          QHeaderView::section { background-color: #2e2e2e; color: white; padding: 5px; border: none; }
          QPushButton { background-color: #3a3a3a; color: white; padding: 5px 15px; }
          QPushButton:hover { background-color: #4a4a4a; }
      """)
    else:
      # Light mode styling
      dialog.setStyleSheet("""
          QDialog, QTableWidget { background-color: #f0f0f0; color: #333333; }
          QTableWidget::item { padding: 5px; }
          QTableWidget::item:selected { background-color: #e0e0e0; }
          QHeaderView::section { background-color: #f0f0f0; color: #333333; padding: 5px; border: none; }
          QPushButton { background-color: #e0e0e0; color: #333333; padding: 5px 15px; }
          QPushButton:hover { background-color: #d0d0d0; }
      """)

    dialog.exec()
      
  def onResetButton(self):
    """
    Hard reset of UI + visuals without triggering Apply.
    Also removes all dynamically-created color selection buttons.
    """

    # 0) Stop playback safely
    if getattr(self.customParamNode, "sequenceBrowserNode", None):
        try:
            self.customParamNode.sequenceBrowserNode.SetPlaybackActive(False)
            self.customParamNode.sequenceBrowserNode.SetSelectedItemNumber(0)
        except Exception:
            pass

    # 1) Block signals while we clear pickers (prevents handlers from firing)
    widgets = []
    for w in ["selector2DImagesFiles", "selector3DSegmentationFiles", "selectorTransformsFile", "deformationFileSelector"]:
        if hasattr(self, w) and getattr(self, w) is not None:
            widgets.append(getattr(self, w))
    prev_sig = [w.blockSignals(True) for w in widgets]

    # 2) Clear inputs (pickers + derived UI)
    if hasattr(self, "selector2DImagesFiles"): self.selector2DImagesFiles.clear()
    if hasattr(self, "selector3DSegmentationFiles"): self.selector3DSegmentationFiles.clear()
    if hasattr(self, "selectorTransformsFile"): self.selectorTransformsFile.setCurrentPath('')
    if hasattr(self, "deformationFileSelector"): self.deformationFileSelector.clear()

    # Column selectors off
    if hasattr(self, "columnXSelector"):
        self.columnXSelector.clear(); self.columnXSelector.enabled = False
    if hasattr(self, "columnYSelector"):
        self.columnYSelector.clear(); self.columnYSelector.enabled = False
    if hasattr(self, "columnZSelector"):
        self.columnZSelector.clear(); self.columnZSelector.enabled = False

    # Status label + buttons
    if hasattr(self, "transformationAppliedLabel"): self.transformationAppliedLabel.setVisible(False)
    if hasattr(self, "applyTransformButton"): self.applyTransformButton.enabled = True

    # 3) delete color selector buttons 

    if hasattr(self, "overlayColoursLayout") and self.overlayColoursLayout is not None:
        while self.overlayColoursLayout.count():
            item = self.overlayColoursLayout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
    # If you track them in a dict, clear it
    if hasattr(self, "labelColorButtons") and isinstance(self.labelColorButtons, dict):
        self.labelColorButtons.clear()
    # Also clear any pending color cache
    if hasattr(self, "pendingLabelColors") and isinstance(self.pendingLabelColors, dict):
        self.pendingLabelColors.clear()

    # 4) Wipe state so next run is clean
    if self.customParamNode:
        self.customParamNode.files2DImages = []
        self.customParamNode.files3DSegmentations = []
        self.deformationFieldPaths = []
        self.customParamNode.totalImages = 0
        self.customParamNode.path3DSegmentation = ""
        self.customParamNode.node3DSegmentation = 0
        self.customParamNode.node3DSegmentationLabelMap = 0
        self.customParamNode.transformsFilePath = ""
        self.customParamNode.sequenceNode2DImages = None
        self.customParamNode.sequenceNodeTransforms = None

        # Remove the per-frame mask sequence node from the scene (not just the reference),
        # otherwise it lingers and the name-based cleanup on the next Apply gets confused
        nodes = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLSequenceNode", "Per-Frame Mask Sequence")
        nodes.UnRegister(None)
        for i in range(nodes.GetNumberOfItems()):
            slicer.mrmlScene.RemoveNode(nodes.GetItemAsObject(i))
        self.customParamNode.deformedMaskSequenceNode = None

        self.customParamNode.sequenceBrowserNode = None
        # reset overlay look
        self.customParamNode.overlayAsOutline = True
        self.customParamNode.overlayThickness = 4
        self.customParamNode.opacity = 1.0

    # 5) Clear overlays/volumes in slice views (visual reset)
    layoutManager = slicer.app.layoutManager()
    for name in layoutManager.sliceViewNames():
        sliceWidget = layoutManager.sliceWidget(name)
        if not sliceWidget:
            continue
        comp = sliceWidget.mrmlSliceCompositeNode()
        comp.SetLabelVolumeID(None)
        comp.SetForegroundVolumeID(None)
        # do not clear background here; we just reset UI — background will be set when user loads images

    # remove any overlay foreground artifacts the logic might have added
    if hasattr(self, "logic") and hasattr(self.logic, "clearSliceForegrounds"):
        try:
            self.logic.clearSliceForegrounds()
        except Exception:
            pass
        
    # Remove 3D volume rendering nodes to clear 3D view on reset
    try:
        nodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLVolumeRenderingDisplayNode")
        nodes.UnRegister(None)
        for i in range(nodes.GetNumberOfItems()):
            slicer.mrmlScene.RemoveNode(nodes.GetItemAsObject(i))
    except Exception:
        pass

    # 6) Reset simple UI knobs
    if hasattr(self, "overlayOutlineOnlyBox"): self.overlayOutlineOnlyBox.checked = True
    if hasattr(self, "overlayThicknessSlider"):
        self.overlayThicknessSlider.value = 4
        self.overlayThicknessSlider.enabled = False
    if hasattr(self, "opacitySlider"): self.opacitySlider.value = 1.0
    if hasattr(self, "playbackSpeedBox"): self.playbackSpeedBox.value = 5.0
    if hasattr(self, "sequenceSlider"): self.sequenceSlider.setValue(0)
    if hasattr(self, "currentFrameInputBox"): self.currentFrameInputBox.setValue(0)
    if hasattr(self, "totalFrameLabel"): self.totalFrameLabel.setText("of 0")

    # 7) One-time fit so Red/Yellow/Green FOVs match
    for name in layoutManager.sliceViewNames():
        layoutManager.sliceWidget(name).fitSliceToBackground()
    slicer.app.processEvents()

    # 8) Unblock signals so browsing works again
    for w, was in zip(widgets, prev_sig):
        w.blockSignals(was)

    # 9) Final UI refresh
    if hasattr(self, "updatePlaybackButtons"):
        self.updatePlaybackButtons(False)
    if hasattr(self, "updateGUIFromParameterNode"):
        self.updateGUIFromParameterNode()

    # Re-enable transforms inputs now that pre-warped mode is cleared
    self.updateTransformsInputsState()

    self.resetVisuals()



  def onIncrement(self):
    """
    Move forward in the playback one step.
    """
    imageDict = self.getSliceDict()   
    self.customParamNode.sequenceBrowserNode.SelectNextItem()
    self.sequenceSlider.setValue(self.customParamNode.sequenceBrowserNode.GetSelectedItemNumber() + 1)
    self.currentFrameInputBox.setValue(self.sequenceSlider.value)
    self.logic.visualize(
        sequenceBrowser=self.customParamNode.sequenceBrowserNode,
        sequenceNode2DImages=self.customParamNode.sequenceNode2DImages,
        segmentationLabelMapID=self.customParamNode.node3DSegmentationLabelMap,
        sequenceNodeTransforms=self.customParamNode.sequenceNodeTransforms,
        opacity=self.customParamNode.opacity,
        overlayAsOutline=self.customParamNode.overlayAsOutline,
        overlayThickness=self.customParamNode.overlayThickness,
        show=False,
        customParamNode=self.customParamNode,
        deformedMaskSequenceNode=self.customParamNode.deformedMaskSequenceNode,
        transformType=self.getEffectiveTransformType()
    )
    self.editSliceView(imageDict)

  def onDecrement(self):
    """
    Move backwards in the playback one step.
    """
    imageDict = self.getSliceDict()   
    self.customParamNode.sequenceBrowserNode.SelectNextItem(-1)
    self.sequenceSlider.setValue(self.customParamNode.sequenceBrowserNode.GetSelectedItemNumber() + 1)
    self.currentFrameInputBox.setValue(self.sequenceSlider.value)
    self.logic.visualize(
        sequenceBrowser=self.customParamNode.sequenceBrowserNode,
        sequenceNode2DImages=self.customParamNode.sequenceNode2DImages,
        segmentationLabelMapID=self.customParamNode.node3DSegmentationLabelMap,
        sequenceNodeTransforms=self.customParamNode.sequenceNodeTransforms,
        opacity=self.customParamNode.opacity,
        overlayAsOutline=self.customParamNode.overlayAsOutline,
        overlayThickness=self.customParamNode.overlayThickness,
        show=False,
        customParamNode=self.customParamNode,
        deformedMaskSequenceNode=self.customParamNode.deformedMaskSequenceNode,
        transformType=self.getEffectiveTransformType()
    )
    self.editSliceView(imageDict)


  def onSkipImages(self):
    """
    Called when the user clicks & drags the slider either forwards or backwards, or manually edits the spinBox's value
    """
    imageDict = self.getSliceDict()  
    num = self.currentFrameInputBox.value
    self.resetVisuals(False)
    self.sequenceSlider.setValue(num)
    self.customParamNode.sequenceBrowserNode.SetSelectedItemNumber(num - 1)
    self.logic.visualize(
        sequenceBrowser=self.customParamNode.sequenceBrowserNode,
        sequenceNode2DImages=self.customParamNode.sequenceNode2DImages,
        segmentationLabelMapID=self.customParamNode.node3DSegmentationLabelMap,
        sequenceNodeTransforms=self.customParamNode.sequenceNodeTransforms,
        opacity=self.customParamNode.opacity,
        overlayAsOutline=self.customParamNode.overlayAsOutline,
        overlayThickness=self.customParamNode.overlayThickness,
        show=False,
        customParamNode=self.customParamNode,
        deformedMaskSequenceNode=self.customParamNode.deformedMaskSequenceNode,
        transformType=self.getEffectiveTransformType()
    )
    self.editSliceView(imageDict)
    
    
  def updatePlaybackButtons(self, inputsProvided):
    """
    Function to update which playback buttons are enabled or disabled according to the state.
    :param inputsProvided: True if all the 3 inputs have been provided: The 2D images folder,
    the 3D segmentation, and the transforms file.
    """
    iconSize = qt.QSize(14, 14)
    mediaIconsPath = os.path.join(os.path.dirname(slicer.util.modulePath(self.__module__)),
                                  'Resources', 'Icons', 'media-control-icons')
    pause_icon = qt.QIcon(os.path.join(mediaIconsPath, 'pause.png'))
    play_icon = qt.QIcon(os.path.join(mediaIconsPath, 'play.png'))
    self.playSequenceButton.setIconSize(iconSize)
    
    # Reset file deletion and tooltips
    self.deleteImagesButton.enabled = True
    self.deleteSegmentationButton.enabled = True
    self.deleteTransformsButton.enabled = True
    self.deleteImagesButton.setToolTip("Remove Cine Images.")
    self.deleteSegmentationButton.setToolTip("Remove Segmentation File.")
    self.deleteTransformsButton.setToolTip("Remove Transforms File.")
    
    if inputsProvided:

      self.divisionFrameLabel.enabled = True
      self.totalFrameLabel.enabled = True
      self.playbackSpeedBox.enabled = True
      # Only show this label when browser actually exists
      hasSequenceBrowser = bool(self.customParamNode.sequenceBrowserNode)
      
      if self._appliedState == "overlay":
        self.transformationAppliedLabel.setText("Transformation applied! Press Play ▶")
      elif self._appliedState == "images":
        self.transformationAppliedLabel.setText("Ready! Press Play ▶")
      self.transformationAppliedLabel.setVisible(bool(self._appliedState))
      
      if hasSequenceBrowser and self.customParamNode.sequenceBrowserNode.GetPlaybackActive():
        # If we are playing
        self.sequenceSlider.setToolTip("Pause the player to enable this feature.")
        self.previousFrameButton.setToolTip("Move to the previous frame.")
        self.nextFrameButton.setToolTip("Move to the next frame.")
        self.playSequenceButton.setToolTip("Pause playback at current frame.")
        self.stopSequenceButton.setToolTip("Return to the first frame.")
        self.deleteImagesButton.setToolTip("Pause the player to enable this feature.")
        self.deleteSegmentationButton.setToolTip("Pause the player to enable this feature.")
        self.deleteTransformsButton.setToolTip("Pause the player to enable this feature.")
        self.columnXSelector.setToolTip("Pause the player to enable this feature.")
        self.columnYSelector.setToolTip("Pause the player to enable this feature.")
        self.columnZSelector.setToolTip("Pause the player to enable this feature.")

        # Set the play button to be a pause button
        self.playSequenceButton.setIcon(pause_icon)
        self.playSequenceButton.enabled = True
        
        # Enable file deletion
        self.deleteImagesButton.enabled = False
        self.deleteSegmentationButton.enabled = False
        self.deleteTransformsButton.enabled = False

        self.stopSequenceButton.enabled = True
        self.nextFrameButton.enabled = False
        self.previousFrameButton.enabled = False
        self.currentFrameInputBox.enabled = False
        self.sequenceSlider.enabled = False
        self.columnXSelector.enabled = False
        self.columnYSelector.enabled = False
        self.columnZSelector.enabled = False
      elif hasSequenceBrowser:
        self.sequenceSlider.setToolTip("Select the next frame for playback.")
        self.deleteImagesButton.setToolTip("Remove Cine images.")
        self.deleteSegmentationButton.setToolTip("Remove Segmentation file.")
        self.deleteTransformsButton.setToolTip("Remove Transforms file.")
        
        # If we are paused
        self.playSequenceButton.setIcon(play_icon)
        self.currentFrameInputBox.enabled = True
        self.sequenceSlider.enabled = True
        self.playSequenceButton.setToolTip("Play playback at current frame.")

        
        # Enable file deletion
        self.deleteImagesButton.enabled = True
        self.deleteSegmentationButton.enabled = True
        self.deleteTransformsButton.enabled = True

        # Enable column selectors — but never in pre-warped mode,
        # where transforms inputs must stay disabled
        if not self.isPrewarpedMode():
          self.columnXSelector.enabled = True
          self.columnYSelector.enabled = True
          self.columnZSelector.enabled = True
          self.columnXSelector.setToolTip("")
          self.columnYSelector.setToolTip("")
          self.columnZSelector.setToolTip("")

        if self.atLastImage():
          self.playSequenceButton.enabled = False
          self.stopSequenceButton.enabled = True
          self.nextFrameButton.enabled = False
          self.previousFrameButton.enabled = True
        elif self.atFirstImage():
          self.playSequenceButton.enabled = True
          self.nextFrameButton.enabled = True
          self.previousFrameButton.enabled = False
          self.stopSequenceButton.enabled = False
        else:
          self.playSequenceButton.enabled = True
          self.nextFrameButton.enabled = True
          self.previousFrameButton.enabled = True
          self.stopSequenceButton.enabled = True

      else:
         # Images loaded but Apply not pressed yet — no browser exists
          self.applyTransformButton.enabled = True
          self.transformationAppliedLabel.setVisible(False)
          self.playSequenceButton.enabled = False
          self.stopSequenceButton.enabled = False
          self.nextFrameButton.enabled = False
          self.previousFrameButton.enabled = False
          self.sequenceSlider.enabled = False
          self.currentFrameInputBox.enabled = False
    else:
      # If inputs are missing
      self.playSequenceButton.enabled = False
      self.stopSequenceButton.enabled = False
      self.nextFrameButton.enabled = False
      self.previousFrameButton.enabled = False
      self.currentFrameInputBox.enabled = False
      self.sequenceSlider.enabled = False
      self.divisionFrameLabel.enabled = False
      self.totalFrameLabel.enabled = False
      self.playbackSpeedBox.enabled = False
      self.transformationAppliedLabel.setVisible(False)
      self.applyTransformButton.enabled = inputsProvided

      # Add empty frame input box value
      self.currentFrameInputBox.setSpecialValueText(' ')

  def onPlaybackSpeedChange(self):
    """
    This function uses the playback speed input to update the fps of the sequence browser
    """
    if self.customParamNode.fps == 0.1:
      self.customParamNode.fps = self.playbackSpeedBox.value - 0.1
    else:
      self.customParamNode.fps = self.playbackSpeedBox.value
    if self.customParamNode.sequenceBrowserNode:
      self.customParamNode.sequenceBrowserNode.SetPlaybackRateFps(self.customParamNode.fps)

  def onOpacityChange(self):
    """
    This function updates the opacity of the label map layer in the slice views according to the
    value in the opacity slider GUI widget.
    """
    self.customParamNode.opacity = self.opacitySlider.value

    layoutManager = slicer.app.layoutManager()
    for name in layoutManager.sliceViewNames():
      sliceCompositeNode = layoutManager.sliceWidget(name).mrmlSliceCompositeNode()
      sliceCompositeNode.SetLabelOpacity(self.opacitySlider.value)

  def onOverlayOutlineChange(self):
    """
    This function updates whether the label map layer overlay is shown as outlined or as a filled
    region within the slice views, according to the value within the overlay outline checkbox.
    """
    self.customParamNode.overlayAsOutline = self.overlayOutlineOnlyBox.checked

    layoutManager = slicer.app.layoutManager()
    for name in layoutManager.sliceViewNames():
      sliceNode = layoutManager.sliceWidget(name).mrmlSliceNode()
      sliceNode.SetUseLabelOutline(self.overlayOutlineOnlyBox.checked)

  def atFirstImage(self):
    """
    Returns whether we are at the first image of the playback sequence.
    """
    return self.customParamNode.sequenceBrowserNode.GetSelectedItemNumber() == 0

  def atLastImage(self):
    """
    Returns whether we are at the last image of the playback squence.
    """
    return self.customParamNode.sequenceBrowserNode.GetSelectedItemNumber() == (self.customParamNode.totalImages - 1)

  def resetVisuals(self, reset=True):
    """
    Resets the visual state of the 3D Slicer views. This function is called when one of the main
    inputs is changed.
    """
    # Clear slice views
    layoutManager = slicer.app.layoutManager()
    for name in layoutManager.sliceViewNames():
      sliceWidget = layoutManager.sliceWidget(name)
      # Remove 2D slice from being shown in the 3D view
      sliceNode = sliceWidget.mrmlSliceNode()
      sliceNode.SetSliceVisible(False)
      # Remove any data being shown in the slice view
      sliceCompositeNode = sliceWidget.mrmlSliceCompositeNode()
      sliceCompositeNode.SetBackgroundVolumeID("None")
      sliceCompositeNode.SetForegroundVolumeID("None")
      sliceCompositeNode.SetLabelVolumeID("")
      # set `self.redBackground`, `self.greenBackground`, `self.yellowBackground` to None
      setattr(self.logic, f"{name.lower()}Background", None)
      # Remove all observers to remove text in the slice views
      view = slicer.app.layoutManager().sliceWidget(name).sliceView()
      if view.cornerAnnotation().HasObserver(vtk.vtkCommand.ModifiedEvent):
        view.cornerAnnotation().RemoveAllObservers()
      # Remove all text annotations in each slice view corner
      view.cornerAnnotation().ClearAllTexts()

    # Clear segmentation label map from 3D view (only if the label map exists)
    if self.customParamNode.node3DSegmentationLabelMap:
      shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
      shNode.SetItemDisplayVisibility(self.customParamNode.node3DSegmentationLabelMap, 0)

    # After the visual reset we also want to setup our slice views for playback if all three
    # inputs have been provided
    inputsProvided = self.customParamNode.sequenceNode2DImages and \
                     (self.customParamNode.sequenceNodeTransforms or self.customParamNode.deformedMaskSequenceNode) and \
                     self.customParamNode.node3DSegmentation
    if inputsProvided and reset:
      # Reset the Sequence back to the first image
      self.customParamNode.sequenceBrowserNode.SetPlaybackActive(False)
      self.customParamNode.sequenceBrowserNode.SetSelectedItemNumber(0)
      self.sequenceSlider.setValue(1)
      self.currentFrameInputBox.setValue(1)
      
      # remove the currentFrameInputBox value
      self.currentFrameInputBox.setSpecialValueText('')
      
      # Check whether the full overlay path is possible
      hasSegmentation = bool(self.customParamNode.node3DSegmentation)
      hasTransforms = bool(self.customParamNode.sequenceNodeTransforms or 
                     self.customParamNode.deformedMaskSequenceNode)
      
      if hasSegmentation and hasTransforms:
        self.logic.visualize(
                                    sequenceBrowser=self.customParamNode.sequenceBrowserNode,
                                    sequenceNode2DImages=self.customParamNode.sequenceNode2DImages,
                                    segmentationLabelMapID=self.customParamNode.node3DSegmentationLabelMap,
                                    sequenceNodeTransforms=self.customParamNode.sequenceNodeTransforms,
                                    opacity=self.customParamNode.opacity,
                                    overlayAsOutline=self.customParamNode.overlayAsOutline,
                                    overlayThickness=self.customParamNode.overlayThickness,
                                    show=False,
                                    customParamNode=self.customParamNode,
                                    deformedMaskSequenceNode=self.customParamNode.deformedMaskSequenceNode,
                                    transformType=self.getEffectiveTransformType()
                                )
        shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
        originalSegNode = shNode.GetItemDataNode(self.customParamNode.node3DSegmentation)
        proxy2DImageNode = self.customParamNode.sequenceBrowserNode.GetProxyNode(
            self.customParamNode.sequenceNode2DImages)
        if proxy2DImageNode.GetImageData().GetDataDimension() != 2:
            self.logic.centerOnSeg(originalSegNode)
      else:
        # new images-only path
        self.logic.visualizeImagesOnly(
            sequenceBrowser=self.customParamNode.sequenceBrowserNode,
            sequenceNode2DImages=self.customParamNode.sequenceNode2DImages
        )
    
    # Images alone are enough to enable Apply
    inputsProvided = bool(self.customParamNode.sequenceNode2DImages)
    self.applyTransformButton.enabled = inputsProvided

    slicer.util.forceRenderAllViews()
    slicer.app.processEvents()





#
# TrackTest
#


class TrackTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear()
    self.logic = TrackLogic()
    self.data_folder_path = os.path.join(os.path.dirname(slicer.util.modulePath(self.__module__)),
                                          'Data')
    self.csv_file_path = os.path.join(self.data_folder_path, 'Transforms.csv')
    self.cine_images_folder_path = os.path.join(self.data_folder_path, '2D Cine Images')
    
    if not os.path.exists(self.csv_file_path):
        self.cine_files_paths = None
        self.csv_file_path = None
        self.cine_images_folder_path = None
        self.delayDisplay(f'CSV file not found: {self.csv_file_path}', None, 2000)
        return
    
    if not os.path.exists(self.cine_images_folder_path):
        self.cine_files_paths = None
        self.csv_file_path = None
        self.cine_images_folder_path = None
        self.delayDisplay(f'Cine images folder not found: {self.cine_images_folder_path}', None, 2000)
        return
    
    self.cine_files_paths = [os.path.join(self.cine_images_folder_path, f) for f in os.listdir(self.cine_images_folder_path)]
    self.csv_headers = ['X', 'Y', 'Z']  

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    # check if folder exists
    if self.cine_images_folder_path is None or self.csv_file_path is None or self.cine_files_paths is None or not os.path.exists(self.cine_images_folder_path) or not os.path.exists(self.csv_file_path) or not os.path.exists(self.cine_files_paths):
        self.delayDisplay('Data is not available for testing',None,2000)
        return
    
    self.test_loadImagesIntoSequenceNode()
    self.test_validateTransformsInput()
    self.delayDisplay('Test passed')
    

  def test_loadImagesIntoSequenceNode(self):
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    if self.cine_files_paths is None:
        return
    imagesSequenceNode, cancelled = \
        self.logic.loadImagesIntoSequenceNode(shNode, self.cine_files_paths)
    total_num_images = imagesSequenceNode.GetNumberOfDataNodes()
    self.assertEqual(total_num_images, 71)
    
  def test_validateTransformsInput(self):
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    if  self.cine_files_paths is None or self.csv_file_path is None or self.csv_headers is None:
        return
    imagesSequenceNode, cancelled = \
        self.logic.loadImagesIntoSequenceNode(shNode, self.cine_files_paths)
    total_num_images = imagesSequenceNode.GetNumberOfDataNodes()
    transformationList = self.logic.validateTransformsInput(self.csv_file_path, total_num_images, self.csv_headers)
    self.assertTrue(transformationList is not None)
    self.assertEqual(len(transformationList), total_num_images)
    # test transformationList to be a list of lists with number in each list
    for transform in transformationList:
      self.assertTrue(isinstance(transform, list))
      for num in transform:
        self.assertTrue(isinstance(num, (float)))



#
# Panel ratio event filter
#


class _PanelRatioEventFilter(qt.QObject):
  """
  Watches the main window for resize events and re-applies the module panel
  width ratio (30% panel : 70% slice views) after each resize.
  """

  def __init__(self, applyRatioCallback, parent=None):
    super().__init__(parent)
    self._applyRatioCallback = applyRatioCallback

  def eventFilter(self, obj, event):
    if event.type() == qt.QEvent.Resize:
      # Defer until the resize has been processed so widths are up to date
      qt.QTimer.singleShot(0, self._applyRatioCallback)
    return False  # never consume the event
  