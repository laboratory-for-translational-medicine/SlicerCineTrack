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

import ctk
import qt
import vtk

import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import *
from slicer import vtkMRMLSequenceNode
from slicer import vtkMRMLSequenceBrowserNode
from utils.Helper import SpinBox, Slider
from utils.TrackLogic import TrackLogic

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
    self.parent.categories = ["Tracking"]
    self.parent.dependencies = []
    self.parent.contributors = ["James McCafferty (laboratory-for-translational-medicine)",
                                "Fabyan Mikhael (laboratory-for-translational-medicine)",
                                "HaPhan Tran (laboratory-for-translational-medicine)",
                                "Mubariz Afzal (laboratory-for-translational-medicine)",
                                "Teo Mesrkhani (laboratory-for-translational-medicine)",
                                "Jacqueline Banh (laboratory-for-translational-medicine)",
                                "Nicholas Caro Lopez (laboratory-for-translational-medicine)",
                                "Venkat Guru Prasad (laboratory-for-translational-medicine)",
                                ]
    self.parent.helpText = """From the input dropdown, select valid 2D cine images in the Cine
    Images Folder, a target to track in the 3D Segmentation File, and a transforms file containing information
    about the X,Y,Z coordinates of exactly where the target is. <br> <br>
    For more information see <a href="https://slicertrack.github.io/">the online documentation</a>"""
    self.parent.acknowledgementText = """
This extension was developed by the Laboratory for Translational Medicine.
"""

#
# Custom Parameter Node
#


@parameterNodeWrapper
class CustomParameterNode:
  folder2DImages: str
  sequenceNode2DImages: vtkMRMLSequenceNode
  path3DSegmentation: str
  node3DSegmentation: int  # subject hierarchy id
  node3DSegmentationLabelMap: int  # subject hierarchy id
  transformsFilePath: str
  sequenceNodeTransforms: vtkMRMLSequenceNode
  sequenceBrowserNode: vtkMRMLSequenceBrowserNode
  totalImages: int
  fps: float
  opacity: float
  overlayAsOutline: bool

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

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    # uiWidget = slicer.util.loadUI(self.resourcePath('UI/Track.ui'))
    # self.layout.addWidget(uiWidget)
    # self.ui = slicer.util.childWidgetVariables(uiWidget)

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

    # File and folder selectors for our input data

    # 2D time series image data folder selector
    self.selector2DImagesFolder = ctk.ctkPathLineEdit()
    self.selector2DImagesFolder.filters = ctk.ctkPathLineEdit.Dirs | ctk.ctkPathLineEdit.Executable | ctk.ctkPathLineEdit.NoDot | ctk.ctkPathLineEdit.NoDotDot | ctk.ctkPathLineEdit.Readable
    self.selector2DImagesFolder.options = ctk.ctkPathLineEdit.ShowDirsOnly
    self.selector2DImagesFolder.settingKey = '2DImagesFolder'
    self.inputsFormLayout.addRow("Cine Images Folder:", self.selector2DImagesFolder)
    
    tooltipText = "Insert 2D images in .mha format."
    self.selector2DImagesFolder.setToolTip(tooltipText)
    browseButton = self.selector2DImagesFolder.findChildren(qt.QToolButton)[0]
    browseButton.setToolTip(tooltipText)

    # 3D segmentation file selector
    self.selector3DSegmentation = ctk.ctkPathLineEdit()
    self.selector3DSegmentation.filters = ctk.ctkPathLineEdit.Files | ctk.ctkPathLineEdit.Executable | ctk.ctkPathLineEdit.NoDot | ctk.ctkPathLineEdit.NoDotDot | ctk.ctkPathLineEdit.Readable
    self.selector3DSegmentation.settingKey = '3DSegmentation'
    self.inputsFormLayout.addRow("3D Segmentation File:", self.selector3DSegmentation)
    
    tooltipText = "Insert a 3D segmentation file in .mha format."
    self.selector3DSegmentation.setToolTip(tooltipText)
    browseButton = self.selector3DSegmentation.findChildren(qt.QToolButton)[0]
    browseButton.setToolTip(tooltipText)
    

    # Transforms file selector
    self.selectorTransformsFile = ctk.ctkPathLineEdit()
    self.selectorTransformsFile.filters = ctk.ctkPathLineEdit.Files | ctk.ctkPathLineEdit.NoDot | ctk.ctkPathLineEdit.NoDotDot | ctk.ctkPathLineEdit.Readable
    self.selectorTransformsFile.settingKey = 'TransformsFile'
    self.inputsFormLayout.addRow("Transforms File:", self.selectorTransformsFile)

    tooltipText = "Insert a Transforms file. Valid filetypes: .csv, .xls, .xlsx, .txt."
    self.selectorTransformsFile.setToolTip(tooltipText)
    browseButton = self.selectorTransformsFile.findChildren(qt.QToolButton)[0]
    browseButton.setToolTip(tooltipText)

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

    
    ## Widget and Layout setup for columns selectors

    self.columnSelectorsLayout = qt.QHBoxLayout()
    self.columnSelectorsLayout.addWidget(self.columnXSelectorLabel)
    self.columnSelectorsLayout.addWidget(self.columnXSelector)
    self.columnSelectorsLayout.addWidget(self.columnYSelectorLabel)
    self.columnSelectorsLayout.addWidget(self.columnYSelector)
    self.columnSelectorsLayout.addWidget(self.columnZSelectorLabel)
    self.columnSelectorsLayout.addWidget(self.columnZSelector)
    
    self.inputsFormLayout.addRow('Translation: ',self.columnSelectorsLayout)
    
    # Layout for apply transformation button
    self.applyTransformButton = qt.QPushButton("Apply Transformation")
    self.applyTransformButton.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    
    self.columnTransformsLayout = qt.QHBoxLayout()
    self.columnTransformsLayout.addWidget(self.applyTransformButton)
    self.inputsFormLayout.addRow(' ',self.columnTransformsLayout)
    
    # Playback speed label and spinbox
    self.transformationAppliedLabel = qt.QLabel("Transformation Applied")
    self.transformationAppliedLabel.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.transformationAppliedLabel.setContentsMargins(20, 0, 10, 0)
    self.columnTransformsLayout.addWidget(self.transformationAppliedLabel)
        
    
    # self.inputsFormLayout.addRow(' ',self.applyTranformButton)    

    ## Sequence Area

    sequenceCollapsibleButton = ctk.ctkCollapsibleButton()
    sequenceCollapsibleButton.text = "Sequence"
    self.layout.addWidget(sequenceCollapsibleButton)

    # Layout within the dummy collapsible button
    self.sequenceFormLayout = qt.QFormLayout(sequenceCollapsibleButton)

    # Sequence layout
    self.sliderWidget = qt.QWidget()
    self.sliderWidget.setMinimumHeight(50)
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
    buttonSize = qt.QSize(60, 30)
    mediaIconsPath = os.path.join(os.path.dirname(slicer.util.modulePath(self.__module__)),
                                  'Resources', 'Icons', 'media-control-icons')

    # Previous frame/image button
    self.previousFrameButton = qt.QPushButton()
    icon = qt.QIcon(os.path.join(mediaIconsPath, 'previous.png'))
    self.previousFrameButton.setIcon(icon)
    self.previousFrameButton.setIconSize(iconSize)
    self.previousFrameButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.previousFrameButton.setFixedSize(buttonSize)
    self.controlLayout.addWidget(self.previousFrameButton)
    self.previousFrameButton.setToolTip("To enable this feature, load valid files in the inputs area above.")

    # Next frame/image button
    self.nextFrameButton = qt.QPushButton()
    icon = qt.QIcon(os.path.join(mediaIconsPath, 'next.png'))
    self.nextFrameButton.setIcon(icon)
    self.nextFrameButton.setIconSize(iconSize)
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
    self.playbackSpeedLabel.setContentsMargins(20, 0, 10, 0)
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

    # Visual controls layout
    self.visualControlsWidget = qt.QWidget()
    self.visualControlsWidget.setMinimumHeight(30)
    self.visualControlsLayout = qt.QHBoxLayout()
    self.visualControlsLayout.setAlignment(qt.Qt.AlignLeft)
    self.visualControlsWidget.setLayout(self.visualControlsLayout)
    self.sequenceFormLayout.addWidget(self.visualControlsWidget)

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
    self.opacityLabel = qt.QLabel("Overlay Opacity:")
    self.opacityLabel.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    self.opacityLabel.setContentsMargins(20, 0, 10, 0)
    self.visualControlsLayout.addWidget(self.opacityLabel)

    self.opacitySlider = ctk.ctkDoubleSlider()
    self.opacitySlider.orientation = qt.Qt.Horizontal
    self.opacitySlider.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    self.opacitySlider.minimum = 0
    self.opacitySlider.maximum = 1.0
    self.opacitySlider.singleStep = 0.01
    self.opacitySlider.value = 1.0
    self.visualControlsLayout.addWidget(self.opacitySlider)

    self.opacityPercentageLabel = qt.QLabel("100%")
    self.opacityPercentageLabel.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    self.opacityPercentageLabel.setContentsMargins(10, 0, 0, 0)
    self.visualControlsLayout.addWidget(self.opacityPercentageLabel)

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
                                lambda: self.currentFrameInputBox.setValue(self.sequenceSlider.value))
    self.sequenceSlider.connect("sliderReleased()", self.onSkipImages)
    self.currentFrameInputBox.connect("valueChanged(int)",
                                lambda: self.sequenceSlider.setValue(self.currentFrameInputBox.value))
    self.currentFrameInputBox.connect("upButtonClicked()", self.onIncrement)
    self.currentFrameInputBox.connect("downButtonClicked()", self.onDecrement)
    self.currentFrameInputBox.connect("editingFinished()", self.onSkipImages)
    self.playbackSpeedBox.connect("valueChanged(double)", self.onPlaybackSpeedChange)
    self.opacitySlider.connect("valueChanged(double)", self.onOpacityChange)
    self.overlayOutlineOnlyBox.connect("toggled(bool)", self.onOverlayOutlineChange)

    # These connections ensure that whenever user changes some settings on the GUI, that is saved
    # in the MRML scene (in the selected parameter node).
    self.selector2DImagesFolder.connect("currentPathChanged(QString)", \
      lambda: self.updateParameterNodeFromGUI("selector2DImagesFolder", "currentPathChanged"))
    self.selector3DSegmentation.connect("currentPathChanged(QString)", \
      lambda: self.updateParameterNodeFromGUI("selector3DSegmentation", "currentPathChanged"))
    self.selectorTransformsFile.connect("currentPathChanged(QString)", \
      self.onTransformsFilePathChange)
    self.applyTransformButton.connect("clicked(bool)", \
      lambda: self.updateParameterNodeFromGUI("applyTransformsButton", "clicked"))

    # These connections will reset the visuals when one of the main inputs are modified
    self.selector2DImagesFolder.connect("currentPathChanged(QString)", self.resetVisuals)
    self.selector3DSegmentation.connect("currentPathChanged(QString)", self.resetVisuals)
    # comment out this line because we only reset visuals when click apply transform button now
    # self.selectorTransformsFile.connect("currentPathChanged(QString)", self.resetVisuals)
    
    # self.applyTransformButton.connect("clicked(bool)", self.resetVisuals)
    

    #
    # End logic
    #

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()

  def enter(self):
    """
    Called each time the user opens this module.
    """
    # Make sure parameter node exists and observed
    self.initializeParameterNode()

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
    self.removeObserver(self.customParamNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

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

    self.selector2DImagesFolder.currentPath = self.customParamNode.folder2DImages
    self.selector3DSegmentation.currentPath = self.customParamNode.path3DSegmentation
    self.selectorTransformsFile.currentPath = self.customParamNode.transformsFilePath

    if self.customParamNode.sequenceNode2DImages:
      self.selectorTransformsFile.enabled = True
      self.selectorTransformsFile.setToolTip("Load a Transforms file corresponding to the Region of Interest's coordinate changes.")
    else:
      self.selectorTransformsFile.enabled = False
      self.selectorTransformsFile.setToolTip("Load a valid Cine Images Folder to enable loading a Transforms file.")



    # True if the 2D images, transforms and 3D segmentation have been provided
    inputsProvided = self.customParamNode.sequenceNode2DImages and \
                     self.customParamNode.sequenceNodeTransforms and \
                     self.customParamNode.node3DSegmentation

    self.updatePlaybackButtons(inputsProvided)

    self.sequenceSlider.setMaximum(self.customParamNode.totalImages)

    if self.customParamNode.sequenceBrowserNode and self.customParamNode.sequenceBrowserNode.GetPlaybackActive():
      imageDict = self.getSliceDict()
      imageNum = self.customParamNode.sequenceBrowserNode.GetSelectedItemNumber() + 1
      self.sequenceSlider.setValue(imageNum)
      self.currentFrameInputBox.setValue(imageNum)
      
      self.logic.visualize(self.customParamNode.sequenceBrowserNode,
                           self.customParamNode.sequenceNode2DImages,
                           self.customParamNode.node3DSegmentationLabelMap,
                           self.customParamNode.sequenceNodeTransforms,
                           self.customParamNode.opacity,
                           self.customParamNode.overlayAsOutline)
      self.editSliceView(imageDict)
                           
    elif not self.customParamNode.sequenceBrowserNode:
      self.sequenceSlider.setValue(1)
      self.currentFrameInputBox.setValue(1)

    self.playbackSpeedBox.value = self.customParamNode.fps

    self.opacitySlider.value = self.customParamNode.opacity

    self.opacityPercentageLabel.text = str(int(self.customParamNode.opacity * 100)) + "%"

    self.overlayOutlineOnlyBox.checked = self.customParamNode.overlayAsOutline

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False
    
    # Disable the "Apply Transformation" button to assure the user the Transformation is applied
    self.applyTransformButton.enabled = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self.customParamNode is None or self._updatingGUIFromParameterNode:
      return

    # Modify all properties in a single batch
    wasModified = self.customParamNode.StartModify()

    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    if caller == "selector2DImagesFolder" and event == "currentPathChanged":
      # Since the transformation information is relative to the 2D images loaded into 3D Slicer,
      # if the path changes, we want to remove any transforms related information. The user should
      # reselect the transforms file they wish to use with the 2D images.
      if self.customParamNode.transformsFilePath:
        self.customParamNode.transformsFilePath = ""
        self.customParamNode.sequenceNodeTransforms = None

      # Set a param to hold the path to the folder containing the cine images
      self.customParamNode.folder2DImages = self.selector2DImagesFolder.currentPath

      # Load the images into 3D Slicer
      imagesSequenceNode, cancelled = \
        self.logic.loadImagesIntoSequenceNode(shNode, self.selector2DImagesFolder.currentPath)

      if cancelled:
        # Unset the param which holds the path to the folder containing the 2D images
        self.customParamNode.folder2DImages = ""
      else:
        if imagesSequenceNode:
          # Set a param to hold a sequence node which holds the cine images
          self.customParamNode.sequenceNode2DImages = imagesSequenceNode
          # Track the number of total images within the parameter totalImages
          self.customParamNode.totalImages = imagesSequenceNode.GetNumberOfDataNodes()
          self.currentFrameInputBox.setMaximum(self.customParamNode.totalImages) # allows for image counter to go above 99, if there are more than 99 images
          self.totalFrameLabel.setText(f"of {self.customParamNode.totalImages}")

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
          slicer.util.warningDisplay("No image files were found within the folder: "
                                    f"{self.selector2DImagesFolder.currentPath}", "Input Error")

    if caller == "selector3DSegmentation" and event == "currentPathChanged":
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
              
      if re.match('.*\.mha', self.selector3DSegmentation.currentPath):
        # If a 3D segmentation node already exists, delete it before we load the new one
        if self.customParamNode.node3DSegmentation:
          nodeID = self.customParamNode.node3DSegmentation

        # Set a param to hold the path to the 3D segmentation file
        self.customParamNode.path3DSegmentation = self.selector3DSegmentation.currentPath

        # Segmentation file should end with .mha
        segmentationNode = slicer.util.loadVolume(self.selector3DSegmentation.currentPath,
                                                  {"singleFile": True, "show": False})
        self.logic.clearSliceForegrounds()
        segmentationNode.SetName("3D Segmentation")
        # Set a param to hold the 3D segmentation node ID
        nodeID = shNode.GetItemByDataNode(segmentationNode)
        self.customParamNode.node3DSegmentation = nodeID

        # Create a label map of the 3D segmentation that will be used to define the mask overlayed
        # on the 2D images during playback
        volumesModuleLogic = slicer.modules.volumes.logic()
        segmentationLabelMap = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode',
                                                                  "3D Segmentation Label Map")
        volumesModuleLogic.CreateLabelVolumeFromVolume(slicer.mrmlScene, segmentationLabelMap,
                                                       segmentationNode)
        # Set a param to hold the 3D segmentation label map ID
        labelMapID = shNode.GetItemByDataNode(segmentationLabelMap)
        self.customParamNode.node3DSegmentationLabelMap = labelMapID
      else:
        # Remove filepath for the Segmentation File in the `Inputs` section
        self.customParamNode.path3DSegmentation = ''
        self.selector3DSegmentation.currentPath = ''
        slicer.util.warningDisplay("The provided 3D segmentation was not of the .mha file type. "
                                   "The file was not loaded into 3D Slicer.", "Input Error")
    
          
                           
    if caller == "applyTransformsButton" and event == "clicked":
      # Set a param to hold the path to the transformations .csv file
      self.customParamNode.transformsFilePath = self.selectorTransformsFile.currentPath

      numImages = self.customParamNode.totalImages
      # If even one line cannot be read correctly/is missing our playback cannot be successful. We
      # will validate the tranformations input first. If the input is valid, we get a list
      # containing all of the transformations read from the file.
      headers = []
      headers.append(self.columnXSelector.currentText)
      headers.append(self.columnYSelector.currentText)
      headers.append(self.columnZSelector.currentText)

      transformsList = \
        self.logic.validateTransformsInput(self.selectorTransformsFile.currentPath, numImages,headers)

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
        
    self.customParamNode.EndModify(wasModified)
  def onTransformsFilePathChange(self):
    
    #TODO - Move these helper functions to another module
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
      
    clearColumnSeletors(self)
      
    addItemToColumnSeletors(self, self.logic.getColumnNamesFromTransformsInput(self.selectorTransformsFile.currentPath))
    
  def onPlayButton(self):
    """
    Begin the playback when a user clicks the "Play" button and pause when user clicks the "Pause" button.
    """
    layoutManager = slicer.app.layoutManager()
    self.customParamNode.sequenceBrowserNode.SetPlaybackItemSkippingEnabled(False) # Fixes image skipping bug on slower machines
    proxy2DImageNode = self.customParamNode.sequenceBrowserNode.GetProxyNode(self.customParamNode.sequenceNode2DImages)
    sliceWidget = TrackLogic().getSliceWidget(layoutManager, proxy2DImageNode)
    sliceView = sliceWidget.sliceView()
    
    ## Pause sequence
    if self.customParamNode.sequenceBrowserNode.GetPlaybackActive():
      # if we are playing, click this button will pause the playback
      self.customParamNode.sequenceBrowserNode.SetPlaybackActive(False)
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
  
  def onIncrement(self):
    """
    Move forward in the playback one step.
    """
    imageDict = self.getSliceDict()   
    self.customParamNode.sequenceBrowserNode.SelectNextItem()
    self.sequenceSlider.setValue(self.customParamNode.sequenceBrowserNode.GetSelectedItemNumber() + 1)
    self.currentFrameInputBox.setValue(self.sequenceSlider.value)
    self.logic.visualize(self.customParamNode.sequenceBrowserNode,
                           self.customParamNode.sequenceNode2DImages,
                           self.customParamNode.node3DSegmentationLabelMap,
                           self.customParamNode.sequenceNodeTransforms,
                           self.customParamNode.opacity,
                           self.customParamNode.overlayAsOutline)
    self.editSliceView(imageDict)

  def onDecrement(self):
    """
    Move backwards in the playback one step.
    """
    imageDict = self.getSliceDict()   
    self.customParamNode.sequenceBrowserNode.SelectNextItem(-1)
    self.sequenceSlider.setValue(self.customParamNode.sequenceBrowserNode.GetSelectedItemNumber() + 1)
    self.currentFrameInputBox.setValue(self.sequenceSlider.value)
    self.logic.visualize(self.customParamNode.sequenceBrowserNode,
                           self.customParamNode.sequenceNode2DImages,
                           self.customParamNode.node3DSegmentationLabelMap,
                           self.customParamNode.sequenceNodeTransforms,
                           self.customParamNode.opacity,
                           self.customParamNode.overlayAsOutline)
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
    self.logic.visualize(self.customParamNode.sequenceBrowserNode,
                         self.customParamNode.sequenceNode2DImages,
                         self.customParamNode.node3DSegmentationLabelMap,
                         self.customParamNode.sequenceNodeTransforms,
                         self.customParamNode.opacity,
                         self.customParamNode.overlayAsOutline)
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
    if inputsProvided:

      self.divisionFrameLabel.enabled = True
      self.totalFrameLabel.enabled = True
      self.playbackSpeedBox.enabled = True
      self.transformationAppliedLabel.setVisible(True)
      
      if self.customParamNode.sequenceBrowserNode.GetPlaybackActive():
        # If we are playing
        self.sequenceSlider.setToolTip("Pause the player to enable this feature.")
        self.previousFrameButton.setToolTip("Move to the previous frame.")
        self.nextFrameButton.setToolTip("Move to the next frame.")
        self.playSequenceButton.setToolTip("Play the current frame.")
        self.playSequenceButton.setToolTip("Stop playback at the current frame.")

        # Set the play button to be a pause button
        self.playSequenceButton.setIcon(pause_icon)
        self.playSequenceButton.enabled = True

        self.stopSequenceButton.enabled = True
        self.nextFrameButton.enabled = False
        self.previousFrameButton.enabled = False
        self.currentFrameInputBox.enabled = False
        self.sequenceSlider.enabled = False
      else:
        self.sequenceSlider.setToolTip("Select the next frame for playback.")
        
        # If we are paused
        self.playSequenceButton.setIcon(play_icon)
        self.currentFrameInputBox.enabled = True
        self.sequenceSlider.enabled = True

        if self.atLastImage():
          #self.nextFrameButton.setToolTip("Move to the previous frame.") - may add a different tooltip at last image
          self.playSequenceButton.enabled = False
          self.stopSequenceButton.enabled = True
          self.nextFrameButton.enabled = False
          self.previousFrameButton.enabled = True
        elif self.atFirstImage():
          #self.previousFrameButton.setToolTip("Move to the previous frame.") - may add a different tooltip at first image
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
      self.applyTransformButton.enabled = False

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
                     self.customParamNode.sequenceNodeTransforms and \
                     self.customParamNode.node3DSegmentation
    if inputsProvided and reset:
      # Reset the Sequence back to the first image
      self.customParamNode.sequenceBrowserNode.SetPlaybackActive(False)
      self.customParamNode.sequenceBrowserNode.SetSelectedItemNumber(0)
      self.sequenceSlider.setValue(1)
      self.currentFrameInputBox.setValue(1)
      
      # remove the currentFrameInputBox value
      self.currentFrameInputBox.setSpecialValueText('')
      
      self.logic.visualize(self.customParamNode.sequenceBrowserNode,
                                 self.customParamNode.sequenceNode2DImages,
                                 self.customParamNode.node3DSegmentationLabelMap,
                                 self.customParamNode.sequenceNodeTransforms,
                                 self.customParamNode.opacity,
                                 self.customParamNode.overlayAsOutline)
    
    self.applyTransformButton.enabled = False

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

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_load_inputs()

  def test_load_inputs(self):
    """ Test if we can load all inputs
    """
    data_folder_path = os.path.join(os.path.dirname(slicer.util.modulePath(self.__module__)),
                                  'Data')
    csv_file_path = os.path.join(data_folder_path, 'Transforms.csv')
    cine_images_folder_path = os.path.join(data_folder_path, '2D Cine Images')

    self.logic = TrackLogic()
    self.delayDisplay("Starting test - loading inputs")
    csv_headers = ['X', 'Y', 'Z']  #default headers in the csv file
    
    # load cine images
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    imagesSequenceNode, cancelled = \
        self.logic.loadImagesIntoSequenceNode(shNode,cine_images_folder_path)
    total_num_images = imagesSequenceNode.GetNumberOfDataNodes()
    self.assertEqual(total_num_images, 71)
    transformationList = self.logic.validateTransformsInput(csv_file_path, total_num_images, csv_headers)
    self.assertTrue(transformationList is not None)
    
    self.delayDisplay('Test passed')