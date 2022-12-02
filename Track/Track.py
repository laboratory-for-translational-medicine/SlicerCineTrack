import csv
import logging
import os
import re
import time

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
    self.Folder2DTimeSeries = ctk.ctkPathLineEdit()
    self.Folder2DTimeSeries.filters = ctk.ctkPathLineEdit.Dirs | ctk.ctkPathLineEdit.Executable | ctk.ctkPathLineEdit.NoDot | ctk.ctkPathLineEdit.NoDotDot | ctk.ctkPathLineEdit.Readable
    self.Folder2DTimeSeries.options = ctk.ctkPathLineEdit.ShowDirsOnly
    self.Folder2DTimeSeries.settingKey = 'Folder2DTimeSeries'

    self.inputsFormLayout.addRow("2D Time-Series Images Folder:", self.Folder2DTimeSeries)

    # 3D volumne file selector
    self.Path3DVolume = ctk.ctkPathLineEdit()
    self.Path3DVolume.filters = ctk.ctkPathLineEdit.Files | ctk.ctkPathLineEdit.Executable | ctk.ctkPathLineEdit.NoDot | ctk.ctkPathLineEdit.NoDotDot |  ctk.ctkPathLineEdit.Readable
    self.Path3DVolume.settingKey = 'Path3DVolume'

    self.inputsFormLayout.addRow("3D Volume File:", self.Path3DVolume)

    # Transformations file selector 
    self.TransformationsFile = ctk.ctkPathLineEdit()
    self.TransformationsFile.filters = ctk.ctkPathLineEdit.Files | ctk.ctkPathLineEdit.NoDot | ctk.ctkPathLineEdit.NoDotDot |  ctk.ctkPathLineEdit.Readable
    self.TransformationsFile.settingKey = 'TransformationsFile'

    self.inputsFormLayout.addRow("Transformations File (.csv):", self.TransformationsFile)

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
    self.PlaySequenceButton = qt.QPushButton("Play")
    self.PlaySequenceButton.enabled = True
    self.PlaySequenceButton.setSizePolicy(qt.QSizePolicy.Minimum,qt.QSizePolicy.Minimum)
    self.controlLayout.addWidget(self.PlaySequenceButton)
    
    # Stop button
    self.StopSequenceButton = qt.QPushButton("Stop")
    self.StopSequenceButton.enabled = False
    self.StopSequenceButton.setSizePolicy(qt.QSizePolicy.Minimum,qt.QSizePolicy.Minimum)
    self.controlLayout.addWidget(self.StopSequenceButton)

    # Fps label and spinbox
    fpsLabel = qt.QLabel("FPS:")
    fpsLabel.setSizePolicy(qt.QSizePolicy.Fixed,qt.QSizePolicy.Minimum)
    self.controlLayout.addWidget(fpsLabel)

    self.Fps = qt.QSpinBox()
    self.Fps.minimum = 1
    self.Fps.maximum = 24
    self.Fps.setSizePolicy(qt.QSizePolicy.Fixed,qt.QSizePolicy.Minimum)
    self.controlLayout.addWidget(self.Fps)

    # Increment and Decrement frame button
    self.changeFrameWidget = qt.QWidget()
    self.changeFrameLayout = qt.QHBoxLayout()
    self.changeFrameWidget.setLayout(self.changeFrameLayout)
    self.sequenceFormLayout.addRow(self.changeFrameWidget)

    # Decrease Frame
    self.DecrementFrame = qt.QPushButton("⯇")
    self.DecrementFrame.enabled = False
    self.DecrementFrame.setSizePolicy(qt.QSizePolicy.Maximum,qt.QSizePolicy.Minimum)
    self.changeFrameLayout.addWidget(self.DecrementFrame)

    # Increase Frame
    self.IncrementFrame = qt.QPushButton("⯈")
    self.IncrementFrame.enabled = False
    self.IncrementFrame.setSizePolicy(qt.QSizePolicy.Maximum,qt.QSizePolicy.Maximum)
    self.changeFrameLayout.addWidget(self.IncrementFrame)

    # Sequence Slider
    # self.sliderWidget = qt.QWidget()
    # self.sliderLayout = qt.QHBoxLayout()
    # self.sliderWidget.setLayout(self.sliderLayout)
    # self.sequenceFormLayout.addWidget(self.sliderWidget)
    
    self.SequenceSlider = qt.QSlider(0x1)  #0x1 is Horizontal, for some reason qt.Horizontal doesn't work, so we have to put in the constant value here
    self.SequenceSlider.enabled = True
    self.SequenceSlider.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
    # self.SequenceSlider.setSizePolicy(qt.QSizePolicy.setHorizontalStretch(0))
    # self.SequenceSlider.setSizePolicy(qt.QSizePolicy.setVerticalStretch(0))
    self.changeFrameLayout.addWidget(self.SequenceSlider)

    self.SequenceFrame = qt.QLabel("0.0s")
    self.SequenceFrame.enabled = True
    self.SequenceFrame.setSizePolicy(qt.QSizePolicy.Maximum, qt.QSizePolicy.Fixed)
    self.changeFrameLayout.addWidget(self.SequenceFrame)

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

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).
    self.PlaySequenceButton.connect("clicked(bool)", self.onPlayButton)
    self.Folder2DTimeSeries.connect("currentPathChanged(QString)", self.updateParameterNodeFromGUI)
    self.Path3DVolume.connect("currentPathChanged(QString)", self.updateParameterNodeFromGUI)
    self.TransformationsFile.connect("currentPathChanged(QString)", self.updateParameterNodeFromGUI)

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
    
    # TODO: change this to our ui features
    # Update node selectors and sliders
    #self.ui.inputSelector.setCurrentNode(self._parameterNode.GetNodeReference("InputVolume"))
    #self.ui.outputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputVolume"))
    #self.ui.invertedOutputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputVolumeInverse"))
    #self.ui.imageThresholdSliderWidget.value = float(self._parameterNode.GetParameter("Threshold"))
    #self.ui.invertOutputCheckBox.checked = (self._parameterNode.GetParameter("Invert") == "true")

    # TODO: Change this to the 'Play' button
    # Update buttons states and tooltips
    #if self._parameterNode.GetNodeReference("InputVolume") and self._parameterNode.GetNodeReference("OutputVolume"):
    #    self.ui.applyButton.toolTip = "Compute output volume"
    #    self.ui.applyButton.enabled = True
    #else:
    #    self.ui.applyButton.toolTip = "Select input and output volume nodes"
    #    self.ui.applyButton.enabled = False

    # self.applyButton.enabled = self._parameterNode.GetNodeReference("InputVolume")

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

    # TODO: Change this to our parameters
    # TODO: Probably should add an outline on how we structure our parameter node for documentation
    #self._parameterNode.SetNodeReferenceID("InputVolume", self.inputSelector.currentNodeID)
    #self._parameterNode.SetNodeReferenceID("OutputVolume", self.outputSelector.currentNodeID)
    #self._parameterNode.SetParameter("Threshold", str(self.imageThresholdSliderWidget.value))
    #self._parameterNode.SetParameter("Invert", "true" if self.invertOutputCheckBox.checked else "false")
    #self._parameterNode.SetNodeReferenceID("OutputVolumeInverse", self.invertedOutputSelector.currentNodeID)

    self._parameterNode.EndModify(wasModified)

  def onPlayButton(self):
    """
    Begin playback when user clicks the "Play" button.
    """
    
    #with slicer.util.tryWithErrorDisplay("Failed to compute results.", waitCursor=True):
      # Compute output
      # TODO: change this to logic.play()
      #self.logic.process(self.ui.inputSelector.currentNode(), self.ui.outputSelector.currentNode(),
      #                   self.ui.imageThresholdSliderWidget.value, self.ui.invertOutputCheckBox.checked)

    return

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
    # TODO: remove these and set them in the parameter node
    #self.nodes = []
    #self.transformNode = None
    #self.folder2DTimeSeries = ""
    #self.path3DVolume = ""
    #self.transformationsFile = ""
    #self.current2DImage = None

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    # TODO: change this to our parameters
    #if not parameterNode.GetParameter("Threshold"):
    #  parameterNode.SetParameter("Threshold", "100.0")
    #if not parameterNode.GetParameter("Invert"):
    #  parameterNode.SetParameter("Invert", "false")


  def play(self):
    # TODO: update descriptions to our parameters
    """
    Begin playback of 2D time-series images.
    :param A:
    :param B:
    """
    
    # TODO: move logic from Temp module into this function

  # TODO: This is the legacy SlicerTrack logic. It should be removed once SlicerTrack is stable.
  # def createSequenceNode(self, name, pattern):
  #   """creates a sequence nodes from all nodes in the scene with a regex pattern"""
  #   seq = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceNode")
  #   seq.SetName(name)

  #   for value, node in enumerate(slicer.util.getNodes()):
  #       if pattern.search(node) != None:
  #         seq.SetDataNodeAtValue(slicer.util.getNode(node), f'{value}')

  #   return seq

  # def ShowData(self, path) -> int:
  #   """Prepares the data by splitting the different orientations, then loading them and finally displaying them"""
  #   import time
  #   start = time.time()
  #   # ProTry(path)

  #   # FOR DEVELOPMENT ONLY
  #   Loaded = bool(qt.QSettings().value('Modules/SlicerTrack'))
  #   print("var: ", Loaded)
  #   if not Loaded or slicer.util.confirmOkCancelDisplay("Force load (dev)?"):
  #     qt.QSettings().setValue('Modules/SlicerTrack', True)
  #     self._loadData_(path)
  #     # self._organize_()
  #   #######################
  #   # self.LoadData(path)
  #   # self.organize()
  #   print(f"finished ShowData() in {time.time() - start}s")
  #   return max

  # def _loadData_(self, path) -> int:
  #   import time
  #   dicomDataDir = path
  #   print("di", dicomDataDir, " -- ", path)
  #   pathlist = sorted(os.listdir(dicomDataDir))
  #   start = time.time()
  #   volumes = []
  #   for s in pathlist:
  #       filename = os.path.join(dicomDataDir, s)
  #       if "Stack" in s:
  #         node = slicer.util.loadVolume(filename)
  #         self.nodes.append(node)
  #         volumes.append(node)
  #         print(f"loaded {filename}")
  #       elif "Segmentation_nrrd" in s:
  #         node = slicer.util.loadSegmentation(filename)
  #         self.nodes.append(node)
  #         # Create transform and apply to sample volume
  #         transformNode = slicer.vtkMRMLTransformNode()
  #         self.transformNode = transformNode
  #         slicer.mrmlScene.AddNode(transformNode)
  #         node.SetAndObserveTransformNodeID(transformNode.GetID())
          
  #   axis = ["Yellow", "Green", "Red"]
  #   for volume in volumes:
  #     widget = axis.pop()
  #     compositeNode = slicer.app.layoutManager().sliceWidget(widget).sliceLogic().GetSliceCompositeNode()
  #     compositeNode.SetBackgroundVolumeID(volume.GetID())
  #   print(f"loaded in {time.time() - start}s")
  #   return len(pathlist)
  # def _organize_(self):

  #   orientations = [
  #     { "label" : "Sagittal", "slicerName" : "Sagittal", "viewColor" : "Yellow" },
  #     { "label": "Coronal", "slicerName" : "Coronal", "viewColor" : "Green" },
  #     { "label": "Transverse", "slicerName" : "Axial", "viewColor" : "Red" }
  #   ]

  #   sequences = []

  #   # Create the sequences
  #   for orientation in orientations:
  #     label = orientation["label"]
  #     img_seq_name = f"Image Sequence {label}"
  #     img = self.createSequenceNode(img_seq_name, re.compile('Volume.*'))
  #     sequences.append(img)
  #     self.nodes.append(img)

  #   # sync the sequences
  #   seqBrowser = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode")
  #   for i in sequences:
  #     seqBrowser.AddSynchronizedSequenceNodeID(i.GetID())

  #   for orientation in orientations:
  #     view = slicer.app.layoutManager().sliceWidget(orientation["viewColor"])
  #     label = orientation["label"]

  #     img_seq_name = f"Image Sequence {label}"
      
  #     img_vol_node = slicer.util.getNode(img_seq_name)
      
  #     view.sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(img_vol_node.GetID())


  # def LoadData(self, path) -> int:
  #   import time
  #   dicomDataDir = path+"/output"
  #   print("di", dicomDataDir, " -- ", path)
  #   pathlist = sorted(os.listdir(dicomDataDir))
  #   start = time.time()
  #   for s in pathlist:
  #       filename = os.path.join(dicomDataDir, s)
  #       print(filename)
  #       if 'seg' in s:
  #         node = slicer.util.loadVolume(filename, properties={'labelmap':True})
  #         self.nodes.append(node)
  #       if 'img' in s:
  #         node = slicer.util.loadVolume(filename, properties={'labelmap':False})
  #         self.nodes.append(node)
  #   print(f"loaded in {time.time() - start}s")
  #   return len(pathlist)

  # def ClearNodes(self):
  #   for node in self.nodes:
  #     slicer.mrmlScene.RemoveNode(node)

  # def organize(self):

  #   orientations = [
  #     { "label" : "Sagittal", "slicerName" : "Sagittal", "viewColor" : "Yellow" },
  #     { "label": "Coronal", "slicerName" : "Coronal", "viewColor" : "Green" },
  #     { "label": "Transverse", "slicerName" : "Axial", "viewColor" : "Red" }
  #   ]

  #   sequences = []

  #   # Create the sequences
  #   for orientation in orientations:
  #     label = orientation["label"]
  #     img_seq_name = f"Image Sequence {label}"
  #     seg_seq_name = f"Segmentation Sequence {label}"
  #     img = self.createSequenceNode(img_seq_name, re.compile(f'.*img_{label}.*'))
  #     seg = self.createSequenceNode(seg_seq_name, re.compile(f'.*seg_{label}.*'))
  #     sequences.append(img)
  #     sequences.append(seg)
  #     self.nodes.append(img)
  #     self.nodes.append(seg)

  #   # sync the sequences
  #   seqBrowser = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode")
  #   for i in sequences:
  #     seqBrowser.AddSynchronizedSequenceNodeID(i.GetID())

  #   for orientation in orientations:
  #     view = slicer.app.layoutManager().sliceWidget(orientation["viewColor"])
  #     label = orientation["label"]

  #     img_seq_name = f"Image Sequence {label}"
  #     seg_seq_name = f"Segmentation Sequence {label}"
      
  #     img_vol_node = slicer.util.getNode(img_seq_name)
  #     seg_vol_node = slicer.util.getNode(seg_seq_name)
      
  #     view.sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(img_vol_node.GetID())
  #     view.sliceLogic().GetSliceCompositeNode().SetLabelVolumeID(seg_vol_node.GetID())


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
