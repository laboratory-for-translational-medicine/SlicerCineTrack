import os
import re

import ctk
import qt
import vtk

import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin


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
    self._parameterNode = None
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
    self.selector3DSegmentation.filters = ctk.ctkPathLineEdit.Files | ctk.ctkPathLineEdit.Executable | ctk.ctkPathLineEdit.NoDot | ctk.ctkPathLineEdit.NoDotDot |  ctk.ctkPathLineEdit.Readable
    self.selector3DSegmentation.settingKey = '3DSegmentation'

    self.inputsFormLayout.addRow("3D Segmentation File:", self.selector3DSegmentation)

    # Transforms file selector
    self.selectorTransformsFile = ctk.ctkPathLineEdit()
    self.selectorTransformsFile.filters = ctk.ctkPathLineEdit.Files | ctk.ctkPathLineEdit.NoDot | ctk.ctkPathLineEdit.NoDotDot |  ctk.ctkPathLineEdit.Readable
    self.selectorTransformsFile.settingKey = 'TransformsFile'
    self.selectorTransformsFile.enabled = False

    self.inputsFormLayout.addRow("Transforms File (.csv):", self.selectorTransformsFile)

    ## Sequence Area

    sequenceCollapsibleButton = ctk.ctkCollapsibleButton()
    sequenceCollapsibleButton.text = "Sequence"
    self.layout.addWidget(sequenceCollapsibleButton)

    # Layout within the dummy collapsible button
    self.sequenceFormLayout = qt.QFormLayout(sequenceCollapsibleButton)
    
    # Control layout
    self.controlWidget = qt.QWidget()
    self.controlLayout = qt.QHBoxLayout()
    self.controlWidget.setLayout(self.controlLayout)
    self.sequenceFormLayout.addWidget(self.controlWidget)

    # Play button
    self.playSequenceButton = qt.QPushButton("Play")
    self.playSequenceButton.enabled = False
    self.playSequenceButton.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Minimum)
    self.controlLayout.addWidget(self.playSequenceButton)
    
    # Stop button
    self.stopSequenceButton = qt.QPushButton("Stop")
    self.stopSequenceButton.enabled = False
    self.stopSequenceButton.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Minimum)
    self.controlLayout.addWidget(self.stopSequenceButton)

    # Fps label and spinbox
    fpsLabel = qt.QLabel("FPS:")
    fpsLabel.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Minimum)
    self.controlLayout.addWidget(fpsLabel)

    self.fps = qt.QSpinBox()
    self.fps.minimum = 1
    self.fps.maximum = 24
    self.fps.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Minimum)
    self.controlLayout.addWidget(self.fps)

    # Increment and Decrement frame button
    self.changeFrameWidget = qt.QWidget()
    self.changeFrameLayout = qt.QHBoxLayout()
    self.changeFrameWidget.setLayout(self.changeFrameLayout)
    self.sequenceFormLayout.addRow(self.changeFrameWidget)

    # Decrease Frame
    self.decrementFrame = qt.QPushButton("⯇")
    self.decrementFrame.enabled = False
    self.decrementFrame.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Minimum)
    self.changeFrameLayout.addWidget(self.decrementFrame)

    # Increase Frame
    self.incrementFrame = qt.QPushButton("⯈")
    self.incrementFrame.enabled = False
    self.incrementFrame.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Maximum)
    self.changeFrameLayout.addWidget(self.incrementFrame)

    # Sequence Slider
    # self.sliderWidget = qt.QWidget()
    # self.sliderLayout = qt.QHBoxLayout()
    # self.sliderWidget.setLayout(self.sliderLayout)
    # self.sequenceFormLayout.addWidget(self.sliderWidget)
    
    # 0x1 is horizontal, for some reason qt.Horizontal doesn't work, so we use the literal here
    self.sequenceSlider = qt.QSlider(0x1)
    self.sequenceSlider.enabled = True
    self.sequenceSlider.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
    # self.sequenceSlider.setSizePolicy(qt.QSizePolicy.setHorizontalStretch(0))
    # self.sequenceSlider.setSizePolicy(qt.QSizePolicy.setVerticalStretch(0))
    self.changeFrameLayout.addWidget(self.sequenceSlider)

    self.sequenceFrame = qt.QLabel("0.0s")
    self.sequenceFrame.enabled = True
    self.sequenceFrame.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    self.changeFrameLayout.addWidget(self.sequenceFrame)

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

    # We create two custom events which will allow us to render/process changes in the GUI
    # seperately and effectively loop through our image sequence as a chain of events
    self.VisualizationEvent = vtk.vtkCommand.UserEvent + 1 # Custom event = UserEvent + offset
    self.AlignmentEvent = vtk.vtkCommand.UserEvent + 2

    self.addObserver(slicer.mrmlScene, self.VisualizationEvent, self.onVisualizationComplete)
    self.addObserver(slicer.mrmlScene, self.AlignmentEvent, self.onAlignmentComplete)

    self.playSequenceButton.connect("clicked(bool)", self.onPlayButton)
    self.stopSequenceButton.connect("clicked(bool)", self.onStopButton)
    self.incrementFrame.connect("clicked(bool)", self.onIncrement)
    self.decrementFrame.connect("clicked(bool)", self.onDecrement)

    # These connections ensure that whenever user changes some settings on the GUI, that is saved
    # in the MRML scene (in the selected parameter node).
    self.selector2DImagesFolder.connect("currentPathChanged(QString)", lambda: self.updateParameterNodeFromGUI("selector2DImagesFolder", "currentPathChanged"))
    self.selector3DSegmentation.connect("currentPathChanged(QString)", lambda: self.updateParameterNodeFromGUI("selector3DSegmentation", "currentPathChanged"))
    self.selectorTransformsFile.connect("currentPathChanged(QString)", lambda: self.updateParameterNodeFromGUI("selectorTransformsFile", "currentPathChanged"))

    #
    # End logic
    #

    #Make sure parameter node is initialized (needed for module reload)
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
    self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

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

    if inputParameterNode:
      self.logic.setDefaultParameters(inputParameterNode)

    # Unobserve previously selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.
    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    
    self._parameterNode = inputParameterNode
    if self._parameterNode is not None:
      self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """
    
    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
    self._updatingGUIFromParameterNode = True

    # We strictly only want to reset the visuals/state if the parameter node has been modified.
    # Whereas updateGUIFromParamterNode() can be called when the module is reloaded or reopened.
    if event == "ModifiedEvent":
      self.logic.resetState(self._parameterNode.GetParameter("3DSegmentationNode"))

    self.selector2DImagesFolder.currentPath = self._parameterNode.GetParameter("2DImagesFolder")
    self.selector3DSegmentation.currentPath = self._parameterNode.GetParameter("3DSegmentationPath")
    self.selectorTransformsFile.currentPath = self._parameterNode.GetParameter("TransformsFilePath")
    #self.ui.inputSelector.setCurrentNode(self._parameterNode.GetNodeReference("InputVolume"))
    #self.ui.outputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputVolume"))
    #self.ui.invertedOutputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputVolumeInverse"))
    #self.ui.imageThresholdSliderWidget.value = float(self._parameterNode.GetParameter("Threshold"))
    #self.ui.invertOutputCheckBox.checked = (self._parameterNode.GetParameter("Invert") == "true")

    if self._parameterNode.GetParameter("VirtualFolder2DImages"):
      self.selectorTransformsFile.enabled = True
    else:
      self.selectorTransformsFile.enabled = False

    # True if the 2D images, transforms and 3D segmentation have been provided
    inputsProvided = self._parameterNode.GetParameter("VirtualFolder2DImages") and \
                     self._parameterNode.GetParameter("VirtualFolderTransforms") and \
                     self._parameterNode.GetParameter("3DSegmentationNode")

    self.updatePlaybackButtons(inputsProvided)

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()

    if caller == "selector2DImagesFolder" and event == "currentPathChanged":
      # If the virtual folder holding the 2D images exists, then delete it (and the data inside)
      # because the folder path has changed, so we may need to upload new 2D images
      if self._parameterNode.GetParameter("VirtualFolder2DImages"):
        folderID = int(self._parameterNode.GetParameter("VirtualFolder2DImages"))
        shNode.RemoveItem(folderID) # this will remove any children nodes as well
        self._parameterNode.UnsetParameter("VirtualFolder2DImages")
        self.logic.totalImages = None

      # Since the transformation information is relative to the 2D images loaded into 3D Slicer,
      # if the path changes, we want to remove any transforms related information. The user should
      # reselect the transforms file they wish to use with the 2D images.
      if self._parameterNode.GetParameter("TransformsFilePath"):
        self._parameterNode.UnsetParameter("TransformsFilePath")
        if self._parameterNode.GetParameter("VirtualFolderTransforms"):
          folderID = int(self._parameterNode.GetParameter("VirtualFolderTransforms"))
          shNode.RemoveItem(folderID) # removes children nodes as well
          self._parameterNode.UnsetParameter("VirtualFolderTransforms")

      # Set a param to hold the path to the folder containing the 2D time-series images
      self._parameterNode.SetParameter("2DImagesFolder", self.selector2DImagesFolder.currentPath)

      # Load the images into 3D Slicer
      folderID = self.loadImagesIntoVirtualFolder(shNode, self.selector2DImagesFolder.currentPath)
      if folderID:
        # Set a param to hold the ID of a virtual folder within the subject hierarchy which holds
        # the 2D time-series images
        self._parameterNode.SetParameter("VirtualFolder2DImages", str(folderID))
        self.logic.totalImages = shNode.GetNumberOfItemChildren(folderID)
      else:
        slicer.util.warningDisplay("No image files were found within the folder: "
                                   f"{self.selector2DImagesFolder.currentPath}", "Input Error")

    if caller == "selector3DSegmentation" and event == "currentPathChanged":
      # If a 3D segmentation node already exists, delete it before we load the new one
      if self._parameterNode.GetParameter("3DSegmentationNode"):
        nodeID = int(self._parameterNode.GetParameter("3DSegmentationNode"))
        shNode.RemoveItem(nodeID)
        self._parameterNode.UnsetParameter("3DSegmentationNode")

      # Set a param to hold the path to the 3D segmentation file
      self._parameterNode.SetParameter("3DSegmentationPath", self.selector3DSegmentation.currentPath)

      # Segmentation file should end with .mha
      if re.match('.*\.mha', self.selector3DSegmentation.currentPath):
        segmentationNode = slicer.util.loadVolume(self.selector3DSegmentation.currentPath,
                                                  {"singleFile": True, "show": False})
        self.clearSliceForegrounds()
        segmentationNode.SetName("3D Segmentation")
        # Set a param to hold the 3D segmentation node ID within the subject hierarchy
        nodeID = shNode.GetItemByDataNode(segmentationNode)
        self._parameterNode.SetParameter("3DSegmentationNode", str(nodeID))
      else:
        slicer.util.warningDisplay("The provided 3D segmentation was not of the .mha file type. "
                                   "The file was not loaded into 3D Slicer.", "Input Error")

    if caller == "selectorTransformsFile" and event == "currentPathChanged":
      # If a virtual folder holding the transformations exists, delete it, since a new file that
      # may have new transformations has been provided
      if self._parameterNode.GetParameter("VirtualFolderTransforms"):
        folderID = int(self._parameterNode.GetParameter("VirtualFolderTransforms"))
        shNode.RemoveItem(folderID) # This will remove any children nodes as well
        self._parameterNode.UnsetParameter("VirtualFolderTransforms")

      # Set a param to hold the path to the transformations .csv file
      self._parameterNode.SetParameter("TransformsFilePath", self.selectorTransformsFile.currentPath)

      # It is implied that a VirtualFolder2DImages exists (since the selector is enabled)
      imagesVirtualFolderID = int(self._parameterNode.GetParameter("VirtualFolder2DImages"))
      numImages = shNode.GetNumberOfItemChildren(imagesVirtualFolderID)

      # If even one line cannot be read correctly/is missing our playback cannot be successful. We
      # will validate the tranformations input first. If the input is valid, we get a list
      # containing all of the transformations read from the file.
      transformsList = \
                   self.validateTransformsInput(self.selectorTransformsFile.currentPath, numImages)

      if transformsList:
        # Get all the images as a list of their IDs in the subject hierarchy
        imagesIDs = []
        shNode.GetItemChildren(imagesVirtualFolderID, imagesIDs)

        # Create transform nodes from the transform data and place them into a virtual folder
        transformsVirtualFolderID = \
           self.createTransformNodesFromTransformData(shNode, transformsList, imagesIDs, numImages)

        # Set a param to hold the ID of a virtual folder which holds the transform nodes
        self._parameterNode.SetParameter("VirtualFolderTransforms", str(transformsVirtualFolderID))
      else:
        slicer.util.warningDisplay("An error was encountered while reading the .csv file: "
                                   f"{self.selectorTransformsFile.currentPath}",
                                   "Validation Error")

    self._parameterNode.EndModify(wasModified)

  def createTransformNodesFromTransformData(self, shNode, transforms, imagesIDs, numImages):
    """
    For every image and it's matching transformation, create a transform node which will hold
    the transformation data for that image wthin 3D Slicer. Place them in a virtual folder.
    :param shNode: node representing the subject hierarchy
    :param transforms: list of transforms extrapolated from the transforms .csv file
    :param imagesIDs: list of 2D images by their subject hierarchy ID
    :param numImages: number of 2D images loaded into 3D Slicer
    """
    # Create a folder to hold the transform nodes
    sceneID = shNode.GetSceneItemID()
    transformsVirtualFolderID = shNode.CreateFolderItem(sceneID, "Transforms")

    for i in range(numImages):
      imageID = imagesIDs[i]
      imageNode = shNode.GetItemDataNode(imageID)
      currentTransform = transforms[i]

      # We use the direction matrix held within the metadata of the image file to understand
      # how the transformation data needs to be transformed, so that it can correctly translate
      # the 3D segmentation during playback. This is because the coordinate system used when
      # generating the transformation data is not necessarily the same as 3D Slicer's own. The
      # direction matrix helps us to convert between these coordinate systems.
      # Mathematically:
      # /ΔLR\   /x x x 0\   /X\
      # |ΔPA| = |x x x 0| * |Y|
      # |ΔIS|   |x x x 0|   |Z|
      # \ 0 /   \0 0 0 0/   \0/
      # Where x represents the direction matrix and X, Y, and Z represent the data from the
      # transforms .csv file.
      directionMatrix = vtk.vtkMatrix4x4() # Create an empty 4x4 matrix
      imageNode.GetIJKToRASDirectionMatrix(directionMatrix)
      currentTransform.append(0) # Needs to be 4x1 to multiply with a 4x4 
      convertedTransform = [0, 0, 0, 0]
      directionMatrix.MultiplyPoint(currentTransform, convertedTransform)

      # Create a transform matrix from the converted transform
      transformMatrix = vtk.vtkMatrix4x4()
      transformMatrix.SetElement(0, 3, convertedTransform[0]) # LR translation
      transformMatrix.SetElement(1, 3, convertedTransform[1]) # PA translation
      transformMatrix.SetElement(2, 3, convertedTransform[2]) # IS translation

      # Create a LinearTransform node to hold our transform matrix 
      transformNode = \
             slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", f"Transform {i + 1}")
      transformNode.ApplyTransformMatrix(transformMatrix)

      # Add the transform node to the transform nodes virtual folder
      transformNodeID = shNode.GetItemByDataNode(transformNode)
      shNode.SetItemParent(transformNodeID, transformsVirtualFolderID)

    print(f"{len(transforms)} transforms were loaded into 3D Slicer as transform nodes")
    return transformsVirtualFolderID

  def validateTransformsInput(self, filepath, numImages):
    """
    Checks to ensure that the data in the provided transformation file is valid and matches the
    number of 2D images that have been loaded into 3D Slicer.
    :param filepath: path to the transforms file (which should be a .csv file)
    :param numImages: the number of 2D time-series images that have already been loaded
    """
    transformationsList = []

    # Check that the transforms file is a .csv type
    if re.match('.*\.csv', filepath):
      with open(filepath, "r") as f:
        for line in f:
          # Remove any newlines or spaces
          line = line.strip().replace(' ', '')
          # Ignore empty lines and the header
          if line == '' or line == 'X,Y,Z':
            continue
          else:
            # Extract each floating point value from the line
            currentTransform = line.split(',')
            try:
              transformationsList.append( [float(currentTransform[0]),
                                           float(currentTransform[1]),
                                           float(currentTransform[2])] )
            except:
              # If there was an error reading the line, break out because we can't/shouldn't
              # perform the playback if the transformation data is corrupt or missing.
              break

    if len(transformationsList) != numImages:
      return None
    else:
      return transformationsList

  def loadImagesIntoVirtualFolder(self, shNode, path):
    """
    Loads the 2D time-series images located within the provided path into 3D Slicer. They are then
    placed within a virtual folder in the subject hierarchy for better organization.
    :param shNode: node representing the subject hierarchy
    :param path: path to folder containing the 2D images to be imported
    """
    folderID = None

    # Find all the image file names within the provided dir
    imageFiles = []
    for item in os.listdir(path):
      if re.match('[0-9]{5}\.mha', item): # five numbers followed by .mha
        imageFiles.append(item)
    imageFiles.sort()

    # We only want to create the virtual folder if image files were found within the provided path
    if len(imageFiles) != 0:
      sceneID = shNode.GetSceneItemID()
      folderID = shNode.CreateFolderItem(sceneID, "2D Time-Series Images")

      print(f"{len(imageFiles)} 2D time-series images will be loaded into 3D Slicer")

      for file in imageFiles:
        filepath = os.path.join(path, file)
        loadedImageNode = slicer.util.loadVolume(filepath, {"singleFile": True, "show": False})
        # Place image into the virtual folder
        imageID = shNode.GetItemByDataNode(loadedImageNode)
        shNode.SetItemParent(imageID, folderID)

      # We do the following to clear the view of the slices. I expected {"show": False} to
      # prevent anything from being shown at all, but the first loaded image will appear in the
      # foreground. This seems to be a bug in 3D Slicer.
      self.clearSliceForegrounds()

    return folderID

  def clearSliceForegrounds(self):
    """
    Clear each slice view from having anything visible in the foreground. This often happens
    inadvertently when using loadVolume() with "show" set to False.
    """
    layoutManager = slicer.app.layoutManager()
    for viewName in layoutManager.sliceViewNames():
      layoutManager.sliceWidget(viewName).mrmlSliceCompositeNode().SetForegroundVolumeID("None")

  def onPlayButton(self):
    """
    Begin the visualization and alignment playback when a user clicks the "Play" button.
    """
    self.logic.playing = True

    # The current image index is None if we haven't started playback. When it has any int value, it
    # means that image is currently shown in the slice view, so we start playing with the next one.
    if self.logic.currentImageIndex is None:
      self.logic.currentImageIndex = 0
    else:
      self.logic.currentImageIndex += 1

    self.logic.visualize(int(self._parameterNode.GetParameter("VirtualFolder2DImages")),
                         int(self._parameterNode.GetParameter("3DSegmentationNode")))

    # Invoke completion event and use artificial pause to let user recognize the visualization
    self.logic.timer.singleShot(self.logic.delay,
                                lambda: slicer.mrmlScene.InvokeEvent(self.VisualizationEvent))

    self.updatePlaybackButtons(True)

  def onStopButton(self):
    """
    Stop the playback, after the current image's visualization and alignment completes.
    """
    self.logic.playing = False

    self.updatePlaybackButtons(True)

  def onIncrement(self):
    """
    Move forward in the playback one step.
    """
    # The current image index is None if we haven't started playback. When it has any int value, it
    # means that image is currently shown in the slice view, so we start playing with the next one.
    if self.logic.currentImageIndex is None:
      self.logic.currentImageIndex = 0
    elif self.logic.currentImageIndex >= (self.logic.totalImages - 1):
      print("Error: Cannot increment beyond the last image")
      return
    else:
      self.logic.currentImageIndex += 1

    self.logic.visualize(int(self._parameterNode.GetParameter("VirtualFolder2DImages")),
                         int(self._parameterNode.GetParameter("3DSegmentationNode")))
    self.logic.align(int(self._parameterNode.GetParameter("3DSegmentationNode")),
                     int(self._parameterNode.GetParameter("VirtualFolderTransforms")))

    self.updatePlaybackButtons(True)

  def onDecrement(self):
    """
    Move backwards in the playback one step.
    """
    if self.logic.currentImageIndex <= 0:
      print("Error: Cannot decrement beyond the image at index 0")
      return
    else:
      self.logic.currentImageIndex -= 1

    self.logic.visualize(int(self._parameterNode.GetParameter("VirtualFolder2DImages")),
                         int(self._parameterNode.GetParameter("3DSegmentationNode")))
    self.logic.align(int(self._parameterNode.GetParameter("3DSegmentationNode")),
                     int(self._parameterNode.GetParameter("VirtualFolderTransforms")))

    self.updatePlaybackButtons(True)

  def onVisualizationComplete(self, caller, event):
    """
    Function invoked when the visualization of the image data (2D image + 3D segmentation) is
    complete.
    """
    self.logic.align(int(self._parameterNode.GetParameter("3DSegmentationNode")),
                     int(self._parameterNode.GetParameter("VirtualFolderTransforms")))

    # Invoke completion event and use artificial pause to let the user recognize the alignment
    self.logic.timer.singleShot(self.logic.delay,
                                lambda: slicer.mrmlScene.InvokeEvent(self.AlignmentEvent))


  def onAlignmentComplete(self, caller, event):
    """
    Function invoked when the alignment of the 3D segmentation using the transformation data is
    complete.
    """
    # Begin the next image's visualization, only if we are playing and not at the last image
    if self.logic.playing and not self.logic.atLastImage():
      self.logic.currentImageIndex += 1
      self.logic.visualize(int(self._parameterNode.GetParameter("VirtualFolder2DImages")),
                           int(self._parameterNode.GetParameter("3DSegmentationNode")))

      # Invoke completion event and use artificial pause to let user recognize the visualization
      self.logic.timer.singleShot(self.logic.delay,
                                  lambda: slicer.mrmlScene.InvokeEvent(self.VisualizationEvent))
    else:
      # We update here in case that the end of the playback was reached (last image)
      self.logic.playing = False
      self.updatePlaybackButtons(True)

  def updatePlaybackButtons(self, inputsProvided):
    """
    Function to update which playback buttons are enabled or disabled according to the state.
    :param inputsProvided: True if all the 3 inputs have been provided: The 2D images folder,
                           the 3D segmentation, and the transforms file.
    """
    if inputsProvided:
      if self.logic.playing:
        # If we are playing
        self.playSequenceButton.enabled = False
        self.stopSequenceButton.enabled = True
        self.incrementFrame.enabled = False
        self.decrementFrame.enabled = False
      else:
        # If we are paused
        if self.logic.atLastImage():
          self.playSequenceButton.enabled = False
          self.incrementFrame.enabled = False
          self.decrementFrame.enabled = True
        elif self.logic.atFirstImage():
          self.playSequenceButton.enabled = True
          self.incrementFrame.enabled = True
          self.decrementFrame.enabled = False
        else:
          self.playSequenceButton.enabled = True
          self.incrementFrame.enabled = True
          self.decrementFrame.enabled = True

        self.stopSequenceButton.enabled = False
    else:
      # If inputs are missing
      self.playSequenceButton.enabled = False
      self.stopSequenceButton.enabled = False
      self.incrementFrame.enabled = False
      self.decrementFrame.enabled = False

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
    self.playing = False
    self.currentImageIndex = None
    self.totalImages = None
    self.timer = qt.QTimer()
    self.delay = 1000 # milliseconds

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    # TODO: change this to our parameters
    #if not parameterNode.GetParameter("Threshold"):
    #  parameterNode.SetParameter("Threshold", "100.0")
    #if not parameterNode.GetParameter("Invert"):
    #  parameterNode.SetParameter("Invert", "false")

  def visualize(self, virtualFolderImagesID, segmentationID):
    """
    Visualizes the image data (2D image and 3D segmentation) within the 3D Slicer views (slice view
    and 3D view). No alignment is done at this step.
    :param virtualFolderImagesID: subject hierarchy ID of the virtual folder containing the 2D images
    :param segmentationID: subject hierarchy ID of the 3D segmentation
    :param completionEvent: event to invoke on visualization completion
    """
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    layoutManager = slicer.app.layoutManager()

    imageID = shNode.GetItemByPositionUnderParent(virtualFolderImagesID, self.currentImageIndex)
    imageNode = shNode.GetItemDataNode(imageID)
    segmentationNode = shNode.GetItemDataNode(segmentationID)

    # Make the 3D segmentation visible in the 3D view
    tmpIdList = vtk.vtkIdList() # The nodes you want to display need to be in a vtkIdList
    tmpIdList.InsertNextId(segmentationID)
    threeDViewNode = layoutManager.activeMRMLThreeDViewNode()
    shNode.ShowItemsInView(tmpIdList, threeDViewNode)

    # Note the orientation of the image
    tmpMatrix = vtk.vtkMatrix4x4()
    imageNode.GetIJKToRASMatrix(tmpMatrix)
    scanOrder = imageNode.ComputeScanOrderFromIJKToRAS(tmpMatrix)

    if scanOrder == "LR" or scanOrder == "RL":
      imageOrientation = "Sagittal"
    elif scanOrder == "AP" or scanOrder == "PA":
      imageOrientation = "Coronal"
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

    # Make the 2D image visible in the slice view
    sliceCompositeNode = sliceWidget.mrmlSliceCompositeNode()
    sliceCompositeNode.SetBackgroundVolumeID(imageNode.GetID())

    # Make the 3D segmentation visible as an overlay in the slice view
    sliceCompositeNode.SetForegroundVolumeID(segmentationNode.GetID())
    sliceCompositeNode.SetForegroundOpacity(0.2)

    # Fit the 2D image in the slice view for a neater look
    sliceWidget.fitSliceToBackground()

    # Make the 2D image visible in the 3D view
    sliceNode = sliceWidget.mrmlSliceNode()
    sliceNode.SetSliceVisible(True)

    # Display nothing within the axial slice view
    for name in layoutManager.sliceViewNames():
      if layoutManager.sliceWidget(name).sliceOrientation == "Axial":
        axialCompositeNode = layoutManager.sliceWidget(name).mrmlSliceCompositeNode()
        axialCompositeNode.SetBackgroundVolumeID("None")

    # Move 3D view camera/perspective to have a better view of the current image
    threeDViewController = layoutManager.threeDWidget(threeDViewNode.GetName()).threeDController()
    if imageOrientation == "Sagittal":
      threeDViewController.lookFromAxis(ctk.ctkAxesWidget.Left)
    elif imageOrientation == "Coronal":
      threeDViewController.lookFromAxis(ctk.ctkAxesWidget.Anterior)

    # Render changes
    slicer.util.forceRenderAllViews()
    slicer.app.processEvents()

  def align(self, segmentationID, virtualFolderTransformsID):
    """
    Aligns and translates the 3D segmentation according to the transformation data.
    :param segmentationID: subject hierarchy ID of the 3D segmentation
    :param virtualFolderTransformsID: subject hierarchy ID of the virtual folder containing the transforms
    :param completionEvent: event to invoke on alignment completion
    """
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()

    segmentationNode = shNode.GetItemDataNode(segmentationID)
    transformID = shNode.GetItemByPositionUnderParent(virtualFolderTransformsID, self.currentImageIndex)
    transformNode = shNode.GetItemDataNode(transformID)

    # Translate the 3D segmentation using the transform data so that the 3D segmentation overlays
    # upon the ROI of the 2D image.
    segmentationNode.SetAndObserveTransformNodeID(transformNode.GetID())

    # Render changes
    slicer.util.forceRenderAllViews()
    slicer.app.processEvents()

  def resetState(self, segmentationID):
    """
    Resets the visual state of the 3D Slicer views, as well as the logical state (restarts playback
    from the beginning). This function is called when a parameter/input is changed.
    :param segmentationID: subject hierarchy ID of the 3D segmentation (empty string if N/A)
    """
    self.playing = False
    self.currentImageIndex = None

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

    # Clear segmentation from 3D view (only needed if the segmentation exists)
    if segmentationID:
      shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
      shNode.SetItemDisplayVisibility(int(segmentationID), 0)

    slicer.util.forceRenderAllViews()
    slicer.app.processEvents()

  def atFirstImage(self):
    """
    Returns whether we are at the first image of the playback sequence.
    """
    # If no image has been shown yet (i.e the index is None) we default to True
    if self.currentImageIndex is None:
      return True
    else:
      return self.currentImageIndex == 0

  def atLastImage(self):
    """
    Returns whether we are at the last image of the playback squence.
    """
    # If no image has been shown yet (i.e. the index is None) we default to False
    if self.currentImageIndex is None:
      return False
    else:
      return self.currentImageIndex == (self.totalImages - 1)

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
