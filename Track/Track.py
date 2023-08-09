import os
from time import time
'''
os.system('PythonSlicer -m pip install pandas')
import pandas as pd
'''
a = time()
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

try:
  import openpyxl
except ModuleNotFoundError as e:
  slicer.util.pip_install('openpyxl')
  import openpyxl

try:
  import xlrd
except ModuleNotFoundError as e:
  slicer.util.pip_install('xlrd')
  import xlrd

print(f"Elapsed Time: {round(time()-a, 3)}s")

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
    self.inputsFormLayout.addRow("2D Cine Images Folder:", self.selector2DImagesFolder)
    
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
    self.selectorTransformsFile.enabled = False
    self.inputsFormLayout.addRow("Transforms File:", self.selectorTransformsFile)

    tooltipText = "Insert a Transforms file. Valid filetypes: .csv, .xls, .xlsx, .txt."
    self.selectorTransformsFile.setToolTip(tooltipText)
    browseButton = self.selectorTransformsFile.findChildren(qt.QToolButton)[0]
    browseButton.setToolTip(tooltipText)


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
    self.sequenceSlider.setToolTip("To enable this feature, load valid files in the inputs area above.")

    # The next three labels collectively will show Image __ of __
    self.divisionFrameLabel = qt.QLabel("Image ")
    self.divisionFrameLabel.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Maximum)
    self.sliderLayout.addWidget(self.divisionFrameLabel)
    
    # Current image/frame spinbox
    self.currentFrameInputBox = qt.QSpinBox()
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
    self.previousFrameButton.setToolTip("To enable this feature, load valid files in the inputs area above.")

    # Next frame/image button
    self.nextFrameButton = qt.QPushButton()
    icon = qt.QIcon(os.path.join(mediaIconsPath, 'next.png'))
    self.nextFrameButton.setIcon(icon)
    self.nextFrameButton.setIconSize(iconSize)
    self.nextFrameButton.enabled = False
    self.nextFrameButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.nextFrameButton.setFixedSize(buttonSize)
    self.controlLayout.addWidget(self.nextFrameButton)
    self.nextFrameButton.setToolTip("To enable this feature, load valid files in the inputs area above.")

    # Play button
    self.playSequenceButton = qt.QPushButton()
    icon = qt.QIcon(os.path.join(mediaIconsPath, 'play.png'))
    self.playSequenceButton.setIcon(icon)
    self.playSequenceButton.setIconSize(iconSize)
    self.playSequenceButton.enabled = False
    self.playSequenceButton.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
    self.playSequenceButton.setFixedSize(buttonSize)
    self.controlLayout.addWidget(self.playSequenceButton)
    self.playSequenceButton.setToolTip("To enable this feature, load valid files in the inputs area above.")

    # Stop button
    self.stopSequenceButton = qt.QPushButton()
    icon = qt.QIcon(os.path.join(mediaIconsPath, 'stop.png'))
    self.stopSequenceButton.setIcon(icon)
    self.stopSequenceButton.setIconSize(iconSize)
    self.stopSequenceButton.enabled = False
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
    self.playbackSpeedBox.maximum = 10.0
    self.playbackSpeedBox.value = 1.0
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
      self.selectorTransformsFile.setToolTip("Load a Transforms file corresponding to the Region of Interest's coordinate changes.")
    else:
      self.selectorTransformsFile.enabled = False
      self.selectorTransformsFile.setToolTip("Load a valid 2D Cine Images Folder to enable loading a Transforms file.")



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
      
      self.logic.visualize(self.customParamNode.sequenceBrowserNode,
                           self.customParamNode.sequenceNode2DImages,
                           self.customParamNode.node3DSegmentationLabelMap,
                           self.customParamNode.sequenceNodeTransforms,
                           self.customParamNode.opacity,
                           self.customParamNode.overlayAsOutline)
                           
    elif not self.customParamNode.sequenceBrowserNode:
      self.sequenceSlider.setValue(1)
      self.currentFrameInputBox.setValue(1)

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
      # Since the transformation information is relative to the 2D images loaded into 3D Slicer,
      # if the path changes, we want to remove any transforms related information. The user should
      # reselect the transforms file they wish to use with the 2D images.
      if self.customParamNode.transformsFilePath:
        self.customParamNode.transformsFilePath = ""
        self.customParamNode.sequenceNodeTransforms = None

      # Set a param to hold the path to the folder containing the 2D cine images
      self.customParamNode.folder2DImages = self.selector2DImagesFolder.currentPath

      # Load the images into 3D Slicer
      imagesSequenceNode, cancelled = \
        self.logic.loadImagesIntoSequenceNode(shNode, self.selector2DImagesFolder.currentPath)

      if cancelled:
        # Unset the param which holds the path to the folder containing the 2D images
        self.customParamNode.folder2DImages = ""
      else:
        if imagesSequenceNode:
          # Set a param to hold a sequence node which holds the 2D cine images
          self.customParamNode.sequenceNode2DImages = imagesSequenceNode
          # Track the number of total images within the parameter totalImages
          self.customParamNode.totalImages = imagesSequenceNode.GetNumberOfDataNodes()
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

    if caller == "selectorTransformsFile" and event == "currentPathChanged":
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

  def onPlayButton(self):
    """
    Begin the playback when a user clicks the "Play" button and pause when user clicks the "Pause" button.
    """
    layoutManager = slicer.app.layoutManager()
    proxy2DImageNode = self.customParamNode.sequenceBrowserNode.GetProxyNode(self.customParamNode.sequenceNode2DImages)
    sliceWidget = TrackLogic().getSliceWidget(layoutManager, proxy2DImageNode)
    # Fit the slice to the current background image
    sliceWidget.fitSliceToBackground()
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
      self.customParamNode.sequenceBrowserNode.SetPlaybackRateFps(self.customParamNode.fps)
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

  def onIncrement(self):
    """
    Move forward in the playback one step.
    """
    self.customParamNode.sequenceBrowserNode.SelectNextItem()
    self.sequenceSlider.setValue(self.customParamNode.sequenceBrowserNode.GetSelectedItemNumber() + 1)
    self.currentFrameInputBox.setValue(self.sequenceSlider.value)
    self.logic.visualize(self.customParamNode.sequenceBrowserNode,
                           self.customParamNode.sequenceNode2DImages,
                           self.customParamNode.node3DSegmentationLabelMap,
                           self.customParamNode.sequenceNodeTransforms,
                           self.customParamNode.opacity,
                           self.customParamNode.overlayAsOutline)


  def onDecrement(self):
    """
    Move backwards in the playback one step.
    """
    self.customParamNode.sequenceBrowserNode.SelectNextItem(-1)
    self.sequenceSlider.setValue(self.customParamNode.sequenceBrowserNode.GetSelectedItemNumber() + 1)
    self.currentFrameInputBox.setValue(self.sequenceSlider.value)
    self.logic.visualize(self.customParamNode.sequenceBrowserNode,
                           self.customParamNode.sequenceNode2DImages,
                           self.customParamNode.node3DSegmentationLabelMap,
                           self.customParamNode.sequenceNodeTransforms,
                           self.customParamNode.opacity,
                           self.customParamNode.overlayAsOutline)

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
      if self.customParamNode.sequenceBrowserNode.GetPlaybackActive():
        # If we are playing
        self.sequenceSlider.setToolTip("Pause the player to enable this feature.")
        self.previousFrameButton.setToolTip("Move to the previous frame.")
        self.nextFrameButton.setToolTip("Move to the next frame.")
        self.playSequenceButton.setToolTip("Play the current frame.")
        self.playSequenceButton.setToolTip("Stop playback at the current frame.")

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
      # Add empty frame input box value
      self.currentFrameInputBox.setSpecialValueText(' ')

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
    if inputsProvided:
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
    self.redBackground = None
    self.greenBackground = None
    self.yellowBackground = None
    self.backgrounds = {
      "Red": self.redBackground,
      "Green": self.greenBackground,
      "Yellow": self.yellowBackground
    }

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
    Loads the 2D cine images located within the provided path into 3D Slicer. They are
    placed within a sequence node and the loaded image nodes are deleted thereafter.
    :param shNode: node representing the subject hierarchy
    :param path: path to folder containing the 2D images to be imported
    """
    # NOTE: This represents a node within the MRML scene, not within the subject hierarchy
    imagesSequenceNode = None

    # Find all the image file names within the provided dir
    imageFiles = []
    for item in os.listdir(path):
      if re.match('.*\.mha', item): # Only look for .mha files
        imageFiles.append(item)
    imageFiles.sort()

    # We only want to create a sequence node if image files were found within the provided path
    if len(imageFiles) != 0:
      imagesSequenceNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceNode",
                                                              "Image Nodes Sequence")

      # Create a progress/loading bar to display the progress of the images loading process
      progressDialog = qt.QProgressDialog("Loading 2D images into 3D Slicer", "Cancel",
                                          0, len(imageFiles))
      progressDialog.minimumDuration = 0

      for fileIndex in range(len(imageFiles)):
        # If the 'Cancel' button was pressed, we want to return to a default state
        if progressDialog.wasCanceled:
          # Remove sequence node
          slicer.mrmlScene.RemoveNode(imagesSequenceNode)
          return None, True

        filepath = os.path.join(path, imageFiles[fileIndex])
        nodeName = (f"Image {fileIndex + 1} ({imageFiles[fileIndex]})").format(filepath)

        loadedImageNode = slicer.util.loadVolume(filepath, {"singleFile": True, "show": False})
        loadedImageNode.SetName(nodeName)
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

      print(f"{len(imageFiles)} 2D cine images were loaded into 3D Slicer")

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
    :param numImages: the number of 2D cine images that have already been loaded
    """
    # NOTE: The current logic of this function will only ensure that the first {numImages}
    # transformations found within the CSV file are valid, so playback can occur. The playback will
    # still occur if later transformations after the first {numImages} transformations are corrupt.
    transformationsList = []
    fileName = os.path.basename(filepath)
    fileExtension = os.path.splitext(filepath)[1]

    if re.match('.*\.(csv|xls|xlsx|txt)', filepath):
      # Check that the transforms file is a .csv type
      if filepath.endswith('.csv'):
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
              slicer.util.warningDisplay(f"An error was encountered while reading the {fileExtension} file: "
                                   f"{fileName}",
                                   "Validation Error")
              break
              
      # Check that the transforms file is a .txt type
      elif filepath.endswith('.txt'):
        with open(filepath, "r") as f:
          next(f)
          for line in f:
            values = line.strip().split(',')
            try:
              x, y, z = map(float, values)
              transformationsList.append([x, y, z])
            except:
              # If there was an error reading the values, break out because we can't/shouldn't
              # perform the playback if the transformation data is corrupt or missing.
              slicer.util.warningDisplay(f"An error was encountered while reading the {fileExtension} file: "
                                   f"{fileName}",
                                   "Validation Error")
              break

      # Check that the transforms file is a .xlsx type
      elif filepath.endswith('.xlsx'):
        wb = openpyxl.load_workbook(filepath)
        sheet = wb.active
        rows = iter(sheet.iter_rows(values_only=True))
        next(rows)  # Start from the second row, assuming first row is header
        for row in rows:
          try:
            [x, y, z] = row
            transformationsList.append([x,y,z])
          except:
            slicer.util.warningDisplay(f"An error was encountered while reading the {fileExtension} file: "
                                           f"{fileName}",
                                   "Validation Error")
            break
        
      # Check that the transforms file is a .xls type
      elif filepath.endswith('.xls'):
        workbook = xlrd.open_workbook(filepath)
        sheet = workbook.sheet_by_index(0)
        for row_idx in range(1, sheet.nrows):  # Start from the second row, assuming first row is header
          values = sheet.row_values(row_idx)
          try:
            x, y, z = map(float, values)
            transformationsList.append([x, y, z])
          except:
            # If there was an error reading the values, break out because we can't/shouldn't
            # perform the playback if the transformation data is corrupt or missing.
            slicer.util.warningDisplay(f"An error was encountered while reading the {fileExtension} file: "
                                     f"{fileName}",
                                     "Validation Error")
            break


      if len(transformationsList) == numImages:
        return transformationsList
      else:
        # Extension will not create transforms nodes if the number of 2d cine images and
        # the number of rows in the transforms file are not equal
        print(os.path.basename(filepath))
        slicer.util.warningDisplay(f"The Number of rows in the {fileExtension} file does not match with number of 2D Cine Images: "
                           f"{fileName}",
                           "Validation Error")
        
        return None

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

    # 3D Slicer works with 4x4 transform matrices internally
    LPSToRASMatrix = vtk.vtkMatrix4x4()
    LPSToRASMatrix.SetElement(0, 0, -1)
    LPSToRASMatrix.SetElement(1, 1, -1)

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

  def visualize(self, sequenceBrowser, sequenceNode2DImages, segmentationLabelMapID,
                    sequenceNodeTransforms, opacity, overlayAsOutline):
    """
    Visualizes the image data (2D images and 3D segmentation overlay) within the slice views and
    enables the alignment of the 3D segmentation label map according to the transformation data.
    :param sequenceBrowser: sequence browser node used to control the playback operation
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
    
    sliceWidget = self.getSliceWidget(layoutManager, proxy2DImageNode)

    name = sliceWidget.sliceViewName
        
    sliceCompositeNode = sliceWidget.mrmlSliceCompositeNode()

    volumesLogic = slicer.modules.volumes.logic()
  
    sliceCompositeNode.SetLabelVolumeID(labelMapNode.GetID())
    sliceCompositeNode.SetLabelOpacity(opacity)
    
    sliceCompositeNode.SetBackgroundVolumeID(labelMapNode.GetID())
    
    # Get the current slice node
    sliceNode = sliceWidget.mrmlSliceNode()

    # Display the label map overlay as an outline
    sliceNode.SetUseLabelOutline(overlayAsOutline)

    # Set the background volume for the current slice view
    sliceCompositeNode.SetBackgroundVolumeID(proxy2DImageNode.GetID())

    # Fit the slice to the current background image
    sliceWidget.fitSliceToBackground()

    # Translate the 3D segmentation label map using the transform data
    labelMapNode.SetAndObserveTransformNodeID(proxyTransformNode.GetID())
    
    sliceNode.SetSliceVisible(True)

    # Make the 3D segmentation visible in the 3D view
    tmpIdList = vtk.vtkIdList() # The nodes you want to display need to be in a vtkIdList
    tmpIdList.InsertNextId(segmentationLabelMapID)
    threeDViewNode = layoutManager.activeMRMLThreeDViewNode()
    shNode.ShowItemsInView(tmpIdList, threeDViewNode)

        

    # Preserve previous slices
    # If a background node for the specified orientation exists, update it with the current slice
    # Otherwise, create a new background node and set it as the background for the specified orientation
    
    if name in self.backgrounds:
      background = getattr(self, name.lower() + 'Background')
      if background is None:
        # Create a new background node for the orientation
        setattr(self, name.lower() + 'Background', volumesLogic.CloneVolume(slicer.mrmlScene,
                proxy2DImageNode, f"{proxy2DImageNode.GetAttribute('Sequences.BaseName')}"))
      else:
        # Background exists, just replace the data to represent the next image in the sequence
        background.SetAndObserveImageData(proxy2DImageNode.GetImageData())
        background.SetAttribute("Sequences.BaseName", proxy2DImageNode.GetAttribute("Sequences.BaseName"))
    
    # Add the image name to the slice view background variable
    currentSlice = getattr(self, name.lower() + 'Background')
    currentSlice.SetName(proxy2DImageNode.GetAttribute('Sequences.BaseName'))

    # Set the background volumes for each orientation, if they exist
    for color in self.backgrounds:
      sliceViewWindow = slicer.app.layoutManager().sliceWidget(color).sliceView()
      sliceViewWindow.cornerAnnotation().RemoveAllObservers()
      currentSlice = getattr(self, color.lower() + 'Background')
      sliceViewWindow.cornerAnnotation().ClearAllTexts()
      # Add desired text to slice views that have a background node
      if currentSlice is not None:
        slicer.mrmlScene.GetNodeByID(f"vtkMRMLSliceCompositeNode{color}").SetBackgroundVolumeID(currentSlice.GetID())
        imageFileNameText = slicer.mrmlScene.GetNodeByID(f"vtkMRMLSliceCompositeNode{color}").GetNodeReference('backgroundVolume').GetAttribute('Sequences.BaseName')
        # Place "Current Alignment" text in the slice view corner
        sliceViewWindow = slicer.app.layoutManager().sliceWidget(color).sliceView()
        sliceViewWindow.cornerAnnotation().SetText(0, imageFileNameText)
    
    for color in self.backgrounds:
      sliceViewWindow = slicer.app.layoutManager().sliceWidget(color).sliceView()
      if sliceViewWindow.cornerAnnotation().HasObserver(vtk.vtkCommand.ModifiedEvent):
        sliceViewWindow.cornerAnnotation().RemoveAllObservers()
      if sliceViewWindow.cornerAnnotation().HasObserver(vtk.vtkCornerAnnotation.UpperLeft):
        sliceViewWindow.cornerAnnotation().RemoveAllObservers()
    sliceView = sliceWidget.sliceView()
    sliceView.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.UpperLeft, "Current Alignment")
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
