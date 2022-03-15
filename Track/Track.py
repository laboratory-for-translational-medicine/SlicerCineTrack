import os, logging, re, vtk, slicer
import qt, csv
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
    with open("D:\Desktop\SlicerTrack\Track\Data\Transforms.csv", 'r') as read_transforms:
        csv_reader = csv.reader(read_transforms)
        next(csv_reader)
        self.csv = list(csv_reader)

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


        
    
    info = {"playing": False, "fps": 1}
    yellow = slicer.app.layoutManager().sliceWidget("Yellow").sliceLogic()
    green  = slicer.app.layoutManager().sliceWidget("Green").sliceLogic()
    red    = slicer.app.layoutManager().sliceWidget("Red").sliceLogic()


    def UpdateSlices():
        def _move_slice_(slice_widget):
          bounds = [0] * 6
          slice_widget.GetLowestVolumeSliceBounds(bounds)
          offset = min(bounds[4] + self.ui.SequenceSlider.value, bounds[5])
          slice_widget.SetSliceOffset(offset)
        _move_slice_(yellow)
        _move_slice_(green)
        _move_slice_(red)
        val = self.ui.SequenceSlider.value
        # if val < len(self.csv):
          # transformMatrix = vtk.vtkMatrix4x4()
          # row = self.csv[val]
          # transformMatrix.SetElement(int(float(row[0])),int(float(row[1])), int(float(row[2])))
          # a = min(5 + val,10)
          # transformMatrix.SetElement(a,a,a)
          # self.logic.transformNode.SetMatrixTransformToParent(transformMatrix)
          # slicer.app.processEvents()

        self.ui.SequenceFrame.text = f"{float(self.ui.SequenceSlider.value):.1f}s"

    def _PlaySeq_():
      if self.ui.SequenceSlider.value < self.ui.SequenceSlider.maximum and info["playing"]:
        self.ui.SequenceSlider.value += self.ui.Fps.value
        self.ui.SequenceSlider.value = min(self.ui.SequenceSlider.value,self.ui.SequenceSlider.maximum)
        self.ui.SequenceFrame.text = f"{float(self.ui.SequenceSlider.value):.1f}s"
        UpdateSlices()
        qt.QTimer.singleShot(100, _PlaySeq_)
      else:
        info["playing"] = False
        self.ui.PlaySequenceButton.enabled = True
        self.ui.StopSequenceButton.enabled = False

    def PlaySeq():
      if info["playing"]: return
      info["playing"] = True
      _PlaySeq_()
      self.ui.PlaySequenceButton.enabled = False
      self.ui.StopSequenceButton.enabled = True

    def StopSeq():
      info["playing"] = False
      self.ui.PlaySequenceButton.enabled = True
      self.ui.StopSequenceButton.enabled = False


    self.ui.PlaySequenceButton.clicked.connect(PlaySeq)
    self.ui.StopSequenceButton.clicked.connect(StopSeq)
    self.ui.SequenceSlider.valueChanged.connect(lambda _: UpdateSlices())
    
    def ChangeFrame(amount: int):
      value = max(0, self.ui.SequenceSlider.value + amount)
      value = min(value,self.ui.SequenceSlider.maximum)
      self.ui.SequenceSlider.value = value
      # print(self.ui.SequenceSlider.value ,value)
      UpdateSlices()
    self.ui.IncrementFrame.clicked.connect(lambda: ChangeFrame(+1))
    self.ui.DecrementFrame.clicked.connect(lambda: ChangeFrame(-1))

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
      self.logic.ClearNodes()
      self.logic.ShowData(path)
      self.ui.PlaySequenceButton.enabled = True
      self.ui.SequenceSlider.enabled = True
      self.ui.IncrementFrame.enabled = True
      self.ui.DecrementFrame.enabled = True

      def _bounds_(slice_widget):
        bounds = [0] * 6
        slice_widget.GetLowestVolumeSliceBounds(bounds)
        return int(bounds[5]-bounds[4]) - 1
      maximum = max(_bounds_(red), _bounds_(green), _bounds_(yellow))
      self.ui.SequenceSlider.maximum =maximum

    self.ui.TrackingFolder.currentPathChanged.connect(lambda path: OnPathChange(path))


    #NOT USED
    #Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()

    self.observedMarkupNode = None
    self.markupsObserverTag = None


  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()
    self.logic.ClearNodes()

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
    self.nodes = []
    self.transformNode = None

  #NOT USED
  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Threshold"):
      parameterNode.SetParameter("Threshold", "100.0")
    if not parameterNode.GetParameter("Invert"):
      parameterNode.SetParameter("Invert", "false")


  def createSequenceNode(self, name, pattern):
    """creates a sequence nodes from all nodes in the scene with a regex pattern"""
    seq = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceNode")
    seq.SetName(name)

    for value, node in enumerate(slicer.util.getNodes()):
        if pattern.search(node) != None:
          seq.SetDataNodeAtValue(slicer.util.getNode(node), f'{value}')

    return seq

  def ShowData(self, path) -> int:
    """Prepares the data by splitting the different orientations, then loading them and finally displaying them"""
    import time
    start = time.time()
    ProTry(path)

    # FOR DEVELOPMENT ONLY
    Loaded = bool(qt.QSettings().value('Modules/SlicerTrack'))
    print("var: ", Loaded)
    if not Loaded or slicer.util.confirmOkCancelDisplay("Force load (dev)?"):
      qt.QSettings().setValue('Modules/SlicerTrack', True)
      self._loadData_(path)
      # self._organize_()
    #######################
    # self.LoadData(path)
    # self.organize()
    print(f"finished ShowData() in {time.time() - start}s")
    return max

  def _loadData_(self, path) -> int:
    import time
    dicomDataDir = path
    print("di", dicomDataDir, " -- ", path)
    pathlist = sorted(os.listdir(dicomDataDir))
    start = time.time()
    for s in pathlist:
        filename = os.path.join(dicomDataDir, s)
        if "Volume" in s:
          node = slicer.util.loadVolume(filename)
          self.nodes.append(node)
        elif "Segmentation_nrrd" in s:
          node = slicer.util.loadSegmentation(filename)
          self.nodes.append(node)
          # Create transform and apply to sample volume
          transformNode = slicer.vtkMRMLTransformNode()
          self.transformNode = transformNode
          slicer.mrmlScene.AddNode(transformNode)
          node.SetAndObserveTransformNodeID(transformNode.GetID())
          import math, time
          transformMatrix = vtk.vtkMatrix4x4()
          for xPos in range(-300,300):
            transformMatrix.SetElement(0,3, xPos)
            transformMatrix.SetElement(1,3, math.sin(xPos)*10)
            transformNode.SetMatrixTransformToParent(transformMatrix)
            slicer.app.processEvents()
            time.sleep(0.02)

    print(f"loaded in {time.time() - start}s")
    return len(pathlist)
  def _organize_(self):

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
      img = self.createSequenceNode(img_seq_name, re.compile('Volume.*'))
      sequences.append(img)
      self.nodes.append(img)

    # sync the sequences
    seqBrowser = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode")
    for i in sequences:
      seqBrowser.AddSynchronizedSequenceNodeID(i.GetID())

    for orientation in orientations:
      view = slicer.app.layoutManager().sliceWidget(orientation["viewColor"])
      label = orientation["label"]

      img_seq_name = f"Image Sequence {label}"
      
      img_vol_node = slicer.util.getNode(img_seq_name)
      
      view.sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(img_vol_node.GetID())


  def LoadData(self, path) -> int:
    import time
    dicomDataDir = path+"/output"
    print("di", dicomDataDir, " -- ", path)
    pathlist = sorted(os.listdir(dicomDataDir))
    start = time.time()
    for s in pathlist:
        filename = os.path.join(dicomDataDir, s)
        print(filename)
        if 'seg' in s:
          node = slicer.util.loadVolume(filename, properties={'labelmap':True})
          self.nodes.append(node)
        if 'img' in s:
          node = slicer.util.loadVolume(filename, properties={'labelmap':False})
          self.nodes.append(node)
    print(f"loaded in {time.time() - start}s")
    return len(pathlist)

  def ClearNodes(self):
    for node in self.nodes:
      slicer.mrmlScene.RemoveNode(node)

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
      self.nodes.append(img)
      self.nodes.append(seg)

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
