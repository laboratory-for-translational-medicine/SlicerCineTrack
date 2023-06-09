import csv
import os
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
                                "Mubariz Afzal (laboratory-for-translational-medicine)"]
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """"""
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """
This file was originally developed by James McCafferty.
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

    self.inputsFormLayout.addRow("2D Time-Series Images Folder:", self.selector2DImagesFolder)

    # 3D segmentation file selector
    self.selector3DSegmentation = ctk.ctkPathLineEdit()
    self.selector3DSegmentation.filters = ctk.ctkPathLineEdit.Files | ctk.ctkPathLineEdit.Executable | ctk.ctkPathLineEdit.NoDot | ctk.ctkPathLineEdit.NoDotDot | ctk.ctkPathLineEdit.Readable
    self.selector3DSegmentation.settingKey = '3DSegmentation'

    self.inputsFormLayout.addRow("3D Segmentation File:", self.selector3DSegmentation)

    # Transforms file selector
    self.selectorTransformsFile = ctk.ctkPathLineEdit()
    self.selectorTransformsFile.filters = ctk.ctkPathLineEdit.Files | ctk.ctkPathLineEdit.NoDot | ctk.ctkPathLineEdit.NoDotDot | ctk.ctkPathLineEdit.Readable
    self.selectorTransformsFile.settingKey = 'TransformsFile'
    self.selectorTransformsFile.enabled = False

    self.inputsFormLayout.addRow("Transforms File (.csv):", self.selectorTransformsFile)

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
    self.sequenceSlider = qt.QSlider(qt.Qt.Horizontal)
    self.sequenceSlider.enabled = False
    self.sequenceSlider.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
    self.sequenceSlider.setMinimum(1)
    self.sequenceSlider.setSingleStep(1)
    self.sliderLayout.addWidget(self.sequenceSlider)

    # Current image/frame spinbox
    self.currentFrameInputBox = qt.QSpinBox()
    self.currentFrameInputBox.enabled = False
    self.currentFrameInputBox.minimum = 1
    self.currentFrameInputBox.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Maximum)
    self.sliderLayout.addWidget(self.currentFrameInputBox)

    # The labels should be changed in the future such that we show: Image __ of __

    # self.divisionFrameLabel = qt.QLabel("/")
    # self.divisionFrameLabel.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Maximum)
    # self.sliderLayout.addWidget(self.divisionFrameLabel)
    # this label will show total number of images
    # self.totalFrameLabel = qt.QLabel("0")
    # self.totalFrameLabel.enabled = True
    # self.totalFrameLabel.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    # self.sliderLayout.addWidget(self.totalFrameLabel)

    # Playback control layout
    self.controlWidget = qt.QWidget()
    self.controlWidget.setMinimumHeight(30)
    self.controlLayout = qt.QHBoxLayout()
    self.controlLayout.setAlignment(qt.Qt.AlignLeft)
    self.controlWidget.setLayout(self.controlLayout)
    self.sequenceFormLayout.addWidget(self.controlWidget)
    # self.controlWidget.setStyleSheet("color: red")

    iconSize = qt.QSize(14, 14)
    buttonSize = qt.QSize(60, 30)
    mediaIconsPath = os.path.join(os.path.dirname(slicer.util.modulePath(self.__module__)),
                                  'Resources', 'Icons', 'media-control-icons')

    # Previous frame/image button
    self.previousFrameButton = qt.QPushButton()
    icon = qt.QIcon(os.path.join(mediaIconsPath, 'previous.png'))
    self.previousFrameButton.setIcon(icon)
    self.previousFrameButton.setIconSize(iconSize)
    self.previousFrameButton.enabled = False
    self.previousFrameButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.previousFrameButton.setFixedSize(buttonSize)
    self.controlLayout.addWidget(self.previousFrameButton)

    # Next frame/image button
    self.nextFrameButton = qt.QPushButton()
    icon = qt.QIcon(os.path.join(mediaIconsPath, 'next.png'))
    self.nextFrameButton.setIcon(icon)
    self.nextFrameButton.setIconSize(iconSize)
    self.nextFrameButton.enabled = False
    self.nextFrameButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.nextFrameButton.setFixedSize(buttonSize)
    self.controlLayout.addWidget(self.nextFrameButton)

    # Play button
    self.playSequenceButton = qt.QPushButton()
    icon = qt.QIcon(os.path.join(mediaIconsPath, 'play.png'))
    self.playSequenceButton.setIcon(icon)
    self.playSequenceButton.setIconSize(iconSize)
    self.playSequenceButton.enabled = False
    self.playSequenceButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.playSequenceButton.setFixedSize(buttonSize)
    self.controlLayout.addWidget(self.playSequenceButton)

    # Stop button
    self.stopSequenceButton = qt.QPushButton()
    icon = qt.QIcon(os.path.join(mediaIconsPath, 'stop.png'))
    self.stopSequenceButton.setIcon(icon)
    self.stopSequenceButton.setIconSize(iconSize)
    self.stopSequenceButton.enabled = False
    self.stopSequenceButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.stopSequenceButton.setFixedSize(buttonSize)
    self.controlLayout.addWidget(self.stopSequenceButton)

    # Playback speed label and spinbox
    self.playbackSpeedLabel = qt.QLabel("Playback Speed:")
    self.playbackSpeedLabel.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.playbackSpeedLabel.setContentsMargins(20, 0, 10, 0)
    self.controlLayout.addWidget(self.playbackSpeedLabel)

    self.playbackSpeedBox = qt.QDoubleSpinBox()
    self.playbackSpeedBox.minimum = 0.1
    self.playbackSpeedBox.maximum = 10.0
    self.playbackSpeedBox.value = 1.0
    self.playbackSpeedBox.setSingleStep(0.5)
    self.playbackSpeedBox.suffix = " fps"
    self.playbackSpeedBox.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.controlLayout.addWidget(self.playbackSpeedBox)

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
    self.currentFrameInputBox.connect("valueChanged(int)",
                                lambda: self.sequenceSlider.setValue(self.currentFrameInputBox.value))
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
      lambda: self.updateParameterNodeFromGUI("selectorTransformsFile", "currentPathChanged"))

    # These connections will reset the visuals when one of the main inputs are modified
    self.selector2DImagesFolder.connect("currentPathChanged(QString)", self.resetVisuals)
    self.selector3DSegmentation.connect("currentPathChanged(QString)", self.resetVisuals)
    self.selectorTransformsFile.connect("currentPathChanged(QString)", self.resetVisuals)

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
    else:
      self.selectorTransformsFile.enabled = False

    # True if the 2D images, transforms and 3D segmentation have been provided
    inputsProvided = self.customParamNode.sequenceNode2DImages and \
                     self.customParamNode.sequenceNodeTransforms and \
                     self.customParamNode.node3DSegmentation

    self.updatePlaybackButtons(inputsProvided)

    self.sequenceSlider.setMaximum(self.customParamNode.totalImages)

    if self.customParamNode.sequenceBrowserNode and self.customParamNode.sequenceBrowserNode.GetPlaybackActive():
      imageNum = self.customParamNode.sequenceBrowserNode.GetSelectedItemNumber() + 1
      self.sequenceSlider.setValue(imageNum)
      self.currentFrameInputBox.setValue(imageNum)
    elif not self.customParamNode.sequenceBrowserNode:
      self.sequenceSlider.setValue(0)
      self.currentFrameInputBox.setValue(0)

    self.playbackSpeedBox.value = self.customParamNode.fps

    self.opacitySlider.value = self.customParamNode.opacity

    self.opacityPercentageLabel.text = str(int(self.customParamNode.opacity * 100)) + "%"

    self.overlayOutlineOnlyBox.checked = self.customParamNode.overlayAsOutline

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

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
      # If the sequence node holding the 2D images exists, then delete it because the folder path
      # has changed, so we may need to upload new 2D images
      if self.customParamNode.sequenceNode2DImages:
        slicer.mrmlScene.RemoveNode(self.customParamNode.sequenceNode2DImages)
        self.customParamNode.sequenceNode2DImages = None
        # Reset our total images
        self.customParamNode.totalImages = 0
        # Also remove the sequence browser node
        if self.customParamNode.sequenceBrowserNode:
          slicer.mrmlScene.RemoveNode(self.customParamNode.sequenceBrowserNode)
          self.customParamNode.sequenceBrowserNode = None

      # Since the transformation information is relative to the 2D images loaded into 3D Slicer,
      # if the path changes, we want to remove any transforms related information. The user should
      # reselect the transforms file they wish to use with the 2D images.
      if self.customParamNode.transformsFilePath:
        self.customParamNode.transformsFilePath = ""
        if self.customParamNode.sequenceNodeTransforms:
          slicer.mrmlScene.RemoveNode(self.customParamNode.sequenceNodeTransforms)
          self.customParamNode.sequenceNodeTransforms = None

      # Set a param to hold the path to the folder containing the 2D time-series images
      self.customParamNode.folder2DImages = self.selector2DImagesFolder.currentPath

      # Load the images into 3D Slicer
      imagesSequenceNode, cancelled = \
        self.logic.loadImagesIntoSequenceNode(shNode, self.selector2DImagesFolder.currentPath)

      if cancelled:
        # Unset the param which holds the path to the folder containing the 2D images
        self.customParamNode.folder2DImages = ""
      else:
        if imagesSequenceNode:
          # Set a param to hold a sequence node which holds the 2D time-series images
          self.customParamNode.sequenceNode2DImages = imagesSequenceNode
          # Track the number of total images within the parameter totalImages
          self.customParamNode.totalImages = imagesSequenceNode.GetNumberOfDataNodes()
        else:
          slicer.util.warningDisplay("No image files were found within the folder: "
                                    f"{self.selector2DImagesFolder.currentPath}", "Input Error")

    if caller == "selector3DSegmentation" and event == "currentPathChanged":
      # If a 3D segmentation node already exists, delete it before we load the new one
      if self.customParamNode.node3DSegmentation:
        nodeID = self.customParamNode.node3DSegmentation
        shNode.RemoveItem(nodeID)
        self.customParamNode.node3DSegmentation = 0
        # Remove the label map if it exists
        if self.customParamNode.node3DSegmentationLabelMap:
          labelMapID = self.customParamNode.node3DSegmentationLabelMap
          shNode.RemoveItem(labelMapID)
          self.customParamNode.node3DSegmentationLabelMap = 0
        # Also remove the sequence browser node
        if self.customParamNode.sequenceBrowserNode:
          slicer.mrmlScene.RemoveNode(self.customParamNode.sequenceBrowserNode)
          self.customParamNode.sequenceBrowserNode = None

      # Set a param to hold the path to the 3D segmentation file
      self.customParamNode.path3DSegmentation = self.selector3DSegmentation.currentPath

      # Segmentation file should end with .mha
      if re.match('.*\.mha', self.selector3DSegmentation.currentPath):
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
        slicer.util.warningDisplay("The provided 3D segmentation was not of the .mha file type. "
                                   "The file was not loaded into 3D Slicer.", "Input Error")

    if caller == "selectorTransformsFile" and event == "currentPathChanged":
      # If a sequence node holding the transformations exists, delete it, since a new file that
      # may have new transformations has been provided
      if self.customParamNode.sequenceNodeTransforms:
        shNode.RemoveNode(self.customParamNode.sequenceNodeTransforms)
        self.customParamNode.sequenceNodeTransforms = None
        # Also remove the sequence browser node
        if self.customParamNode.sequenceBrowserNode:
          slicer.mrmlScene.RemoveNode(self.customParamNode.sequenceBrowserNode)
          self.customParamNode.sequenceBrowserNode = None

      # Set a param to hold the path to the transformations .csv file
      self.customParamNode.transformsFilePath = self.selectorTransformsFile.currentPath

      numImages = self.customParamNode.totalImages
      # If even one line cannot be read correctly/is missing our playback cannot be successful. We
      # will validate the tranformations input first. If the input is valid, we get a list
      # containing all of the transformations read from the file.
      transformsList = \
        self.logic.validateTransformsInput(self.selectorTransformsFile.currentPath, numImages)

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
      else:
        slicer.util.warningDisplay("An error was encountered while reading the .csv file: "
                                   f"{self.selectorTransformsFile.currentPath}",
                                   "Validation Error")

    self.customParamNode.EndModify(wasModified)

  def onPlayButton(self):
    """
    Begin the playback when a user clicks the "Play" button and pause when user clicks the "Pause" button.
    """
    if self.customParamNode.sequenceBrowserNode.GetPlaybackActive():
      # if we are playing, click this button will pause the playback
      self.customParamNode.sequenceBrowserNode.SetPlaybackActive(False)
      # Synchronize `sequenceSlider` and `currentFrameInputBox` if either is modified by the user
      self.sequenceSlider.setValue(self.currentFrameInputBox.value)
      self.currentFrameInputBox.setValue(self.sequenceSlider.value)
      self.customParamNode.sequenceBrowserNode.SetSelectedItemNumber(self.currentFrameInputBox.value - 1)
      print(self.customParamNode.sequenceBrowserNode.GetSelectedItemNumber())
    else:
      # If the image to be played is changed when paused, start the playback at that image number
      self.customParamNode.sequenceBrowserNode.SetSelectedItemNumber(self.currentFrameInputBox.value - 1)
      # if we are not playing, click this button will start the playback
      self.customParamNode.sequenceBrowserNode.SetPlaybackRateFps(self.customParamNode.fps)
      self.customParamNode.sequenceBrowserNode.SetPlaybackActive(True)

  def onStopButton(self):
    """
    Stop the playback, after the current image's visualization completes.
    """
    self.customParamNode.sequenceBrowserNode.SetPlaybackActive(False)
    self.customParamNode.sequenceBrowserNode.SetSelectedItemNumber(0)

  def onIncrement(self):
    """
    Move forward in the playback one step.
    """
    self.customParamNode.sequenceBrowserNode.SelectNextItem()

  def onDecrement(self):
    """
    Move backwards in the playback one step.
    """
    self.customParamNode.sequenceBrowserNode.SelectNextItem(-1)

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
      if self.customParamNode.sequenceBrowserNode.GetPlaybackActive():
        # If we are playing
        
        # Set the play button to be a pause button
        self.playSequenceButton.enabled = True
        self.playSequenceButton.setIcon(pause_icon)
        self.playSequenceButton.enabled = True

        self.stopSequenceButton.enabled = True
        self.nextFrameButton.enabled = False
        self.previousFrameButton.enabled = False
        self.currentFrameInputBox.enabled = False
        self.sequenceSlider.enabled = False
      else:
        # If we are paused
        self.playSequenceButton.setIcon(play_icon)
        self.currentFrameInputBox.enabled = True
        self.sequenceSlider.enabled = True
        
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
      # If inputs are missing
      self.playSequenceButton.enabled = False
      self.stopSequenceButton.enabled = False
      self.nextFrameButton.enabled = False
      self.previousFrameButton.enabled = False
      self.currentFrameInputBox.enabled = False
      self.sequenceSlider.enabled = False

  def onPlaybackSpeedChange(self):
    """
    This function uses the playback speed input to update the fps of the sequence browser
    """
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

  def resetVisuals(self):
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

    # Clear segmentation label map from 3D view (only if the label map exists)
    if self.customParamNode.node3DSegmentationLabelMap:
      shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
      shNode.SetItemDisplayVisibility(self.customParamNode.node3DSegmentationLabelMap, 0)

    # After the visual reset we also want to setup our slice views for playback if all three
    # inputs have been provided
    inputsProvided = self.customParamNode.sequenceNode2DImages and \
                     self.customParamNode.sequenceNodeTransforms and \
                     self.customParamNode.node3DSegmentation
    if inputsProvided:
      self.logic.setupSliceViews(self.customParamNode.sequenceBrowserNode,
                                 self.customParamNode.sequenceNode2DImages,
                                 self.customParamNode.node3DSegmentationLabelMap,
                                 self.customParamNode.sequenceNodeTransforms,
                                 self.customParamNode.opacity,
                                 self.customParamNode.overlayAsOutline)

    slicer.util.forceRenderAllViews()
    slicer.app.processEvents()

#
# TrackLogic
#


class TrackLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)
    self.timer = qt.QTimer()

  def setDefaultParameters(self, customParameterNode):
    """
    Initialize parameter node with default settings.
    """
    customParameterNode.totalImages = 0
    customParameterNode.fps = 1.0  # frames (i.e. images) per second
    customParameterNode.opacity = 1.0  # 100 %
    customParameterNode.overlayAsOutline = True

  def loadImagesIntoSequenceNode(self, shNode, path):
    """
    Loads the 2D time-series images located within the provided path into 3D Slicer. They are
    placed within a sequence node and the loaded image nodes are deleted thereafter.
    :param shNode: node representing the subject hierarchy
    :param path: path to folder containing the 2D images to be imported
    """
    # NOTE: This represents a node within the MRML scene, not within the subject hierarchy
    imagesSequenceNode = None

    # Find all the image file names within the provided dir
    imageFiles = []
    for item in os.listdir(path):
      if re.match('[0-9]{5}\.mha', item):  # five numbers followed by .mha
        imageFiles.append(item)
    imageFiles.sort()

    # We only want to create a sequence node if image files were found within the provided path
    if len(imageFiles) != 0:
      imagesSequenceNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceNode",
                                                              "Image Nodes Sequence")

      # Create a progress/loading bar to display the progress of the images loading process
      progressDialog = qt.QProgressDialog("Loading 2D Images Into 3D Slicer", "Cancel",
                                          0, len(imageFiles))
      progressDialog.minimumDuration = 0

      for fileIndex in range(len(imageFiles)):
        # If the 'Cancel' button was pressed, we want to return to a default state
        if progressDialog.wasCanceled:
          # Remove sequence node
          slicer.mrmlScene.RemoveNode(imagesSequenceNode)
          return None, True

        filepath = os.path.join(path, imageFiles[fileIndex])
        loadedImageNode = slicer.util.loadVolume(filepath, {"singleFile": True, "show": False})
        # Place image node into sequence
        imagesSequenceNode.SetDataNodeAtValue(loadedImageNode, str(fileIndex))
        # Remove loaded image node
        imageID = shNode.GetItemByDataNode(loadedImageNode)
        shNode.RemoveItem(imageID)

        #  Update how far we are in the progress bar
        progressDialog.setValue(fileIndex + 1)

        # This render step is needed for the progress bar to visually update in the GUI
        slicer.util.forceRenderAllViews()
        slicer.app.processEvents()

      print(f"{len(imageFiles)} 2D time-series images were loaded into 3D Slicer")

      # We do the following to clear the view of the slices. I expected {"show": False} to
      # prevent anything from being shown at all, but the first loaded image will appear in the
      # foreground. This seems to be a bug in 3D Slicer.
      self.clearSliceForegrounds()

    return imagesSequenceNode, False

  def validateTransformsInput(self, filepath, numImages):
    """
    Checks to ensure that the data in the provided transformation file is valid and matches the
    number of 2D images that have been loaded into 3D Slicer.
    :param filepath: path to the transforms file (which should be a .csv file)
    :param numImages: the number of 2D time-series images that have already been loaded
    """
    # NOTE: The current logic of this function will only ensure that the first {numImages}
    # transformations found within the CSV file are valid, so playback can occur. The playback will
    # still occur if later transformations after the first {numImages} transformations are corrupt.
    transformationsList = []

    # Check that the transforms file is a .csv type
    if re.match('.*\.csv', filepath):
      with open(filepath, "r") as f:
        # Using a DictReader allows us to recognize the CSV header
        reader = csv.DictReader(f)
        for row in reader:
          # Extract floating point values from row
          try:
            transformationsList.append([float(row['X']), float(row['Y']), float(row['Z'])])
          except:
            # If there was an error reading the values, break out because we can't/shouldn't
            # perform the playback if the transformation data is corrupt or missing.
            break

    if len(transformationsList) < numImages:
      return None
    else:
      return transformationsList

  def createTransformNodesFromTransformData(self, shNode, transforms, numImages):
    """
    For every image and it's matching transformation, create a transform node which will hold
    the transformation data for that image wthin 3D Slicer. Place them in a sequence node.
    :param shNode: node representing the subject hierarchy
    :param transforms: list of transforms extrapolated from the transforms .csv file
    :param numImages: number of 2D images loaded into 3D Slicer
    """
    # NOTE: This represents a node within the MRML scene, not within the subject hierarchy
    transformsSequenceNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceNode",
                                                                "Transform Nodes Sequence")

    # Create a progress/loading bar to display the progress of the node creation process
    progressDialog = qt.QProgressDialog("Creating Transform Nodes From Transformation Data", "Cancel",
                                        0, numImages)
    progressDialog.minimumDuration = 0

    # NOTE: It is very important that we loop using the number of 2D images loaded, versus the size
    # of the transforms array/list. This is because we may provide a CSV with more transforms than
    # needed, but we only need to create as many transform nodes as there are 2D images.
    for i in range(numImages):
      # If the 'Cancel' button was pressed, we want to return to a default state
      if progressDialog.wasCanceled:
        # Remove sequence node
        shNode.RemoveNode(transformsSequenceNode)
        return None

      # 3D Slicer uses the RAS (Right, Anterior, Superior) basis for their coordinate system.
      # However, the transformation data we use was generated outside of 3D Slicer, using DICOM
      # images, which corresponds to the LPS (Left, Prosterier, Superior) basis. In order to use
      # this data, we must convert it from LPS to RAS, in order to correctly transform the images
      # we load into 3D Slicer. See the following links for more detail:
      # https://www.slicer.org/wiki/Coordinate_systems#Anatomical_coordinate_system
      # https://github.com/Slicer/Slicer/blob/main/Libs/MRML/Core/vtkITKTransformConverter.h#L246
      # This is a simple conversion. It can be mathematically represented as:
      # /ΔLR\   /-1  0  0  0\   /X\
      # |ΔPA| = | 0 -1  0  0| * |Y|
      # |ΔIS|   | 0  0  1  0|   |Z|
      # \ 0 /   \ 0  0  0  1/   \0/
      # Where X, Y, and Z represent the transformation in LPS.

      # 3D Slicer works with 4x4 transform matrices internally
      LPSToRASMatrix = vtk.vtkMatrix4x4()
      LPSToRASMatrix.SetElement(0, 0, -1)
      LPSToRASMatrix.SetElement(1, 1, -1)

      # Convert transform from LPS to RAS
      currentTransform = transforms[i]
      currentTransform.append(0) # Needs to be 4x1 to multiply with a 4x4
      convertedTransform = [0, 0, 0, 0]
      LPSToRASMatrix.MultiplyPoint(currentTransform, convertedTransform)

      # Create a transform matrix from the converted transform
      transformMatrix = vtk.vtkMatrix4x4()
      transformMatrix.SetElement(0, 3, convertedTransform[0])  # LR translation
      transformMatrix.SetElement(1, 3, convertedTransform[1])  # PA translation
      transformMatrix.SetElement(2, 3, convertedTransform[2])  # IS translation

      # Create a LinearTransform node to hold our transform matrix
      transformNode = \
             slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", f"Transform {i + 1}")
      transformNode.ApplyTransformMatrix(transformMatrix)

      # Add the transform node to the transforms sequence node
      transformsSequenceNode.SetDataNodeAtValue(transformNode, str(i))
      # Remove the transform node
      transformNodeID = shNode.GetItemByDataNode(transformNode)
      shNode.RemoveItem(transformNodeID)

      # Update how far we are in the progress bar
      progressDialog.setValue(i + 1)

      # This render step is needed for the progress bar to visually update in the GUI
      slicer.util.forceRenderAllViews()
      slicer.app.processEvents()

    print(f"{numImages} transforms were loaded into 3D Slicer as transform nodes")

    return transformsSequenceNode

  def clearSliceForegrounds(self):
    """
    Clear each slice view from having anything visible in the foreground. This often happens
    inadvertently when using loadVolume() with "show" set to False.
    """
    layoutManager = slicer.app.layoutManager()
    for viewName in layoutManager.sliceViewNames():
      layoutManager.sliceWidget(viewName).mrmlSliceCompositeNode().SetForegroundVolumeID("None")

  def setupSliceViews(self, sequenceBrowser, sequenceNode2DImages, segmentationLabelMapID, \
                      sequenceNodeTransforms, opacity, overlayAsOutline):
    """
    Visualizes the image data (2D images and 3D segmentation overlay) within the slice views and
    enables the alignment of the 3D segmentation label map according to the transformation data.
    :param: sequenceBrowser: sequence browser node used to control the playback operation
    :param sequenceNode2DImages: sequence node containing the 2D images
    :param segmentationLabelMapID: subject hierarchy ID of the 3D segmentation label map
    :param sequenceNodeTransforms: sequence node containing the transforms
    :param opacity: opacity value of overlay layer (3D segmentation label map layer)
    :param overlayAsOutline: whether to show the overlay as an outline or a filled region
    """
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    layoutManager = slicer.app.layoutManager()

    # The proxy image node represents the current selected image within the sequence
    proxy2DImageNode = sequenceBrowser.GetProxyNode(sequenceNode2DImages)
    # The proxy transform node represents the current selected transform within the sequence
    proxyTransformNode = sequenceBrowser.GetProxyNode(sequenceNodeTransforms)
    labelMapNode = shNode.GetItemDataNode(segmentationLabelMapID)

    # We loop through the first images that have unique orientations so that we can appropriately
    # view them within each slice view. We do this specifically so that fitSliceToBackground() can
    # work correctly (by setting the correct slice offset for the images of each orientation).
    orientations = []
    while len(orientations) < 3:
      sliceWidget = self.getSliceWidget(layoutManager, proxy2DImageNode)

      if sliceWidget.sliceOrientation not in orientations:
        orientations.append(sliceWidget.sliceOrientation)

        # Make the 2D image visible in the slice view
        sliceCompositeNode = sliceWidget.mrmlSliceCompositeNode()
        sliceCompositeNode.SetBackgroundVolumeID(proxy2DImageNode.GetID())

        # Make the 3D segmentation label map visible as a label map layer in the slice view
        sliceCompositeNode.SetLabelVolumeID(labelMapNode.GetID())
        sliceCompositeNode.SetLabelOpacity(opacity)

        # Fit the 2D image in the slice view for a neater look
        sliceWidget.fitSliceToBackground()

        # Display the label map overlay as an outline
        sliceNode = sliceWidget.mrmlSliceNode()
        sliceNode.SetUseLabelOutline(overlayAsOutline)

        # NOTE: We have currently disabled visibility within in the 3D view due to slowness
        # Make the 2D image visible in the 3D view
        #sliceNode.SetSliceVisible(True)

        # Go to the next image in the sequence (this changes proxy2DImageNode to the next image)
        sequenceBrowser.SelectNextItem()
      else:
        break

    sequenceBrowser.SelectFirstItem()

    # NOTE: We have currently disabled visibility within in the 3D view due to slowness
    # Make the 3D segmentation visible in the 3D view
    #tmpIdList = vtk.vtkIdList() # The nodes you want to display need to be in a vtkIdList
    #tmpIdList.InsertNextId(segmentationLabelMapID)
    #threeDViewNode = layoutManager.activeMRMLThreeDViewNode()
    #shNode.ShowItemsInView(tmpIdList, threeDViewNode)

    # Enable alignment of the 3D segmentation label map according to the transform data so that
    # the 3D segmentation label map overlays upon the ROI of the 2D images
    labelMapNode.SetAndObserveTransformNodeID(proxyTransformNode.GetID())

    # Render changes
    slicer.util.forceRenderAllViews()
    slicer.app.processEvents()

  def getSliceWidget(self, layoutManager, imageNode):
    """
    This function helps to determine the slice widget that corresponds to the orientation of the
    provided image. (i.e. the slice widget that would display the image)
    :param layoutManager: node representing the MRML layout manager
    :param imageNode: node representing the 2D image
    """
    # Determine the orientation of the image
    tmpMatrix = vtk.vtkMatrix4x4()
    imageNode.GetIJKToRASMatrix(tmpMatrix)
    scanOrder = imageNode.ComputeScanOrderFromIJKToRAS(tmpMatrix)

    if scanOrder == "LR" or scanOrder == "RL":
      imageOrientation = "Sagittal"
    elif scanOrder == "AP" or scanOrder == "PA":
      imageOrientation = "Coronal"
    elif scanOrder == "IS" or scanOrder == "SI":
      imageOrientation = "Axial"
    else:
      print(f"Error: Unexpected image scan order {scanOrder}.")
      exit(1)

    # Find the slice widget that has the same orientation as the image
    sliceWidget = None
    for name in layoutManager.sliceViewNames():
      if layoutManager.sliceWidget(name).sliceOrientation == imageOrientation:
        sliceWidget = layoutManager.sliceWidget(name)

    if not sliceWidget:
      print(f"Error: A slice with the {imageOrientation} orientation was not found.")
      exit(1)

    return sliceWidget

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
    self.test_Track1()

  def test_Track1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    # TODO: replace this with our own test
    # self.delayDisplay("Starting the test")

    # # Get/create input data

    # import SampleData
    # registerSampleData()
    # inputVolume = SampleData.downloadSample('Track1')
    # self.delayDisplay('Loaded test data set')

    # inputScalarRange = inputVolume.GetImageData().GetScalarRange()
    # self.assertEqual(inputScalarRange[0], 0)
    # self.assertEqual(inputScalarRange[1], 695)

    # outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    # threshold = 100

    # # Test the module logic

    # logic = TrackLogic()

    # # Test algorithm with non-inverted threshold
    # logic.process(inputVolume, outputVolume, threshold, True)
    # outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    # self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    # self.assertEqual(outputScalarRange[1], threshold)

    # # Test algorithm with inverted threshold
    # logic.process(inputVolume, outputVolume, threshold, False)
    # outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    # self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    # self.assertEqual(outputScalarRange[1], inputScalarRange[1])

    # self.delayDisplay('Test passed')
