import os, logging, re, vtk, slicer

from numpy import deprecate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from Pro import ProTry
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
    self.parent.dependencies = [] # add here list of module names that this module requires
    self.parent.contributors = ["James McCafferty (laboratory-for-translational-medicine)", "Fabyan Mikhael (laboratory-for-translational-medicine)"]
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """"""
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """
This file was originally developed by James McCafferty.
"""

    # Additional initialization step after application startup is complete
    slicer.app.connect("startupCompleted()", registerSampleData)

#
# Register sample data sets in Sample Data module
#
def registerSampleData():
  """
  Add data sets to Sample Data module.
  """
  # It is always recommended to provide sample data for users to make it easy to try the module,
  # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

  import SampleData
  iconsPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons')

  # To ensure that the source code repository remains small (can be downloaded and installed quickly)
  # it is recommended to store data sets that are larger than a few MB in a Github release.

  # Track1
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='Track',
    sampleName='Track1',
    # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
    # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
    thumbnailFileName=os.path.join(iconsPath, 'Track1.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
    fileNames='Track1.nrrd',
    # Checksum to ensure file integrity. Can be computed by this command:
    #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
    checksums = 'SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95',
    # This node name will be used when the data set is loaded
    nodeNames='Track1'
  )

  # Track2
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='Track',
    sampleName='Track2',
    thumbnailFileName=os.path.join(iconsPath, 'Track2.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
    fileNames='Track2.nrrd',
    checksums = 'SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97',
    # This node name will be used when the data set is loaded
    nodeNames='Track2'
  )

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

    #NOT USED
    VTKObservationMixin.__init__(self)  # needed for parameter node observation

    self.logic = None

    #NOT USED
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False


  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/Track.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = TrackLogic()


        
    
    playing = [False]
    yellow = slicer.app.layoutManager().sliceWidget("Yellow").sliceLogic()
    green = slicer.app.layoutManager().sliceWidget("Green").sliceLogic()

    def UpdateSlices():
        yellow.SetSliceOffset(105+self.ui.SequenceSlider.value)
        green.SetSliceOffset(41+self.ui.SequenceSlider.value)

    def _PlaySeq_():
      if self.ui.SequenceSlider.value < self.ui.SequenceSlider.maximum and playing[0]:
        self.ui.SequenceSlider.value += 1
        self.ui.SequenceFrame.text = f"{float(self.ui.SequenceSlider.value):.1f}s"
        UpdateSlices()
        qt.QTimer.singleShot(100, _PlaySeq_)
      else:
        playing[0] = False

    def PlaySeq():
      if playing[0]: return
      playing[0] = True
      _PlaySeq_()
      self.ui.PlaySequenceButton.enabled = False
      self.ui.StopSequenceButton.enabled = True

    def StopSeq():
      playing[0] = False
      self.ui.PlaySequenceButton.enabled = True
      self.ui.StopSequenceButton.enabled = False


    self.ui.PlaySequenceButton.clicked.connect(PlaySeq)
    self.ui.StopSequenceButton.clicked.connect(StopSeq)
    self.ui.SequenceSlider.valueChanged.connect(lambda _: UpdateSlices())
    



    # # These connections ensure that we update parameter node when scene is closed
    # # Uncomment these if you need to run any code at the closing events
    # self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    # self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)


    """
      -Whenever the user selects a path to the data folder, it will run the OnPathChange function,
      preparing the data by splitting it into two orientations and saving them as .mha
      -The processed .mha files are then loaded with the .loaddata()
      -Finally the images are displayed by using .organize()
    """
    def OnPathChange(path):
      maximum = self.logic.ShowData(path)
      self.ui.PlaySequenceButton.enabled = True
      self.ui.SequenceSlider.enabled = True
      self.ui.SequenceSlider.maximum = 35 

    self.ui.TrackingFolder.currentPathChanged.connect(lambda path: OnPathChange(path))


    #NOT USED
    #Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()

    self.observedMarkupNode = None
    self.markupsObserverTag = None


  #NOT USED
  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()

  #NOT USED
  def enter(self):
    """
    Called each time the user opens this module.
    """
    # Make sure parameter node exists and observed
    self.initializeParameterNode()

  #NOT USED
  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

  #NOT USED
  def onSceneStartClose(self, caller, event):
    """
    Called just before the scene is closed.
    """
    # Parameter node will be reset, do not use it anymore
    self.setParameterNode(None)

  #NOT USED
  def onSceneEndClose(self, caller, event):
    """
    Called just after the scene is closed.
    """
    # If this module is shown while the scene is closed then recreate a new parameter node immediately
    if self.parent.isEntered:
      self.initializeParameterNode()

  #NOT USED
  def initializeParameterNode(self):
    """
    Ensure parameter node exists and observed.
    """
    # Parameter node stores all user choices in parameter values, node selections, etc.
    # so that when the scene is saved and reloaded, these settings are restored.

    self.setParameterNode(self.logic.getParameterNode())

    # Select default input nodes if nothing is selected yet to save a few clicks for the user
    if not self._parameterNode.GetNodeReference("InputVolume"):
      firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
      if firstVolumeNode:
        self._parameterNode.SetNodeReferenceID("InputVolume", firstVolumeNode.GetID())

  #NOT USED
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

  #NOT USED
  def updateGUIFromParameterNode(self,x=0,y=0):
    if self._parameterNode is None:
      return
    # self.ui.applyButton.enabled = self._parameterNode.GetNodeReference("InputVolume")

  #NOT USED
  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    self._parameterNode.SetNodeReferenceID("InputVolume", self.ui.inputSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("OutputVolume", self.ui.outputSelector.currentNodeID)
    self._parameterNode.SetParameter("Threshold", str(self.ui.imageThresholdSliderWidget.value))
    self._parameterNode.SetParameter("Invert", "true" if self.ui.invertOutputCheckBox.checked else "false")
    self._parameterNode.SetNodeReferenceID("OutputVolumeInverse", self.ui.invertedOutputSelector.currentNodeID)

    self._parameterNode.EndModify(wasModified)

  #NOT USED
  def onEnableAutoUpdate(self, autoUpdate):
    if self.markupsObserverTag:
      self.observedMarkupNode.RemoveObserver(self.markupsObserverTag)
      self.observedMarkupNode = None
      self.markupsObserverTag = None
    if autoUpdate and self.ui.inputSelector.currentNode:
      self.observedMarkupNode = self.ui.inputSelector.currentNode()
      self.markupsObserverTag = self.observedMarkupNode.AddObserver(
      slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onMarkupsUpdated)
  
  #NOT USED
  def onMarkupsUpdated(self, caller=None, event=None):
    self.onApplyButton()

  #NOT USED
  def onApplyButton(self):
    self.logic.process(self.ui.inputSelector.currentNode(),
      self.ui.invertedOutputSelector.currentNode(),
      self.ui.imageThresholdSliderWidget.value,
      not self.ui.invertOutputCheckBox.checked)
    self.ui.centerOfMassValueLabel.text = str(self.logic.centerOfMass)

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

  #NOT USED
  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Threshold"):
      parameterNode.SetParameter("Threshold", "100.0")
    if not parameterNode.GetParameter("Invert"):
      parameterNode.SetParameter("Invert", "false")

  # creates a sequence nodes from all nodes in the scene with
  # as a regex pattern
  def createSequenceNode(self, name, pattern):
    seq = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceNode")
    seq.SetName(name)

    for value, node in enumerate(slicer.util.getNodes()):
        if pattern.search(node) != None:
          seq.SetDataNodeAtValue(slicer.util.getNode(node), f'{value}')

    return seq

  def ShowData(self, path) -> int:
    """Prepares the data by splitting the different orientations, then loading them and finally displaying them"""
    ProTry(path)
    max = self.LoadData(path)
    self.organize()
    return max

  def LoadData(self, path) -> int:
    dicomDataDir = path+"/output"
    print("di", dicomDataDir, " -- ", path)
    pathlist = sorted(os.listdir(dicomDataDir))
    for s in pathlist:
        filename = os.path.join(dicomDataDir, s)
        print(filename)
        if 'seg' in s:
          slicer.util.loadVolume(filename, properties={'labelmap':True})
        if 'img' in s:
          slicer.util.loadVolume(filename, properties={'labelmap':False})
    return len(pathlist)

  def organize(self):

    orientations = [
      { "label" : "Sagittal", "slicerName" : "Sagittal", "viewColor" : "Yellow" },
      { "label": "Coronal", "slicerName" : "Coronal", "viewColor" : "Green" },
      { "label": "Transverse", "slicerName" : "Axial", "viewColor" : "Red" }
    ]

    sequences = []

    # Create the sequences
    for orientation in orientations:
      label = orientation["label"]
      img_seq_name = f"Image Sequence {label}"
      seg_seq_name = f"Segmentation Sequence {label}"
      img = self.createSequenceNode(img_seq_name, re.compile(f'.*img_{label}.*'))
      seg = self.createSequenceNode(seg_seq_name, re.compile(f'.*seg_{label}.*'))
      sequences.append(img)
      sequences.append(seg)

    # sync the sequences
    seqBrowser = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode")
    for i in sequences:
      seqBrowser.AddSynchronizedSequenceNodeID(i.GetID())

    for orientation in orientations:
      view = slicer.app.layoutManager().sliceWidget(orientation["viewColor"])
      label = orientation["label"]

      img_seq_name = f"Image Sequence {label}"
      seg_seq_name = f"Segmentation Sequence {label}"
      
      img_vol_node = slicer.util.getNode(img_seq_name)
      seg_vol_node = slicer.util.getNode(seg_seq_name)
      
      view.sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(img_vol_node.GetID())
      view.sliceLogic().GetSliceCompositeNode().SetLabelVolumeID(seg_vol_node.GetID())

#NOT USED for now - Create Tests for any new feature if you can
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

    self.delayDisplay("Starting the test")

    # Get/create input data

    import SampleData
    registerSampleData()
    inputVolume = SampleData.downloadSample('Track1')
    self.delayDisplay('Loaded test data set')

    inputScalarRange = inputVolume.GetImageData().GetScalarRange()
    self.assertEqual(inputScalarRange[0], 0)
    self.assertEqual(inputScalarRange[1], 695)

    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    threshold = 100

    # Test the module logic

    logic = TrackLogic()

    # Test algorithm with non-inverted threshold
    logic.process(inputVolume, outputVolume, threshold, True)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], threshold)

    # Test algorithm with inverted threshold
    logic.process(inputVolume, outputVolume, threshold, False)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], inputScalarRange[1])

    self.delayDisplay('Test passed')
