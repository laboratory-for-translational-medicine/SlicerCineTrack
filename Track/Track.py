import os, logging, re, vtk, slicer, ctk
import qt, csv
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
    self.parent.dependencies = [] # add here list of module names that this module requires
    self.parent.contributors = ["James McCafferty (laboratory-for-translational-medicine)", "Fabyan Mikhael (laboratory-for-translational-medicine)"]
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

    #NOT USED
    VTKObservationMixin.__init__(self)  # needed for parameter node observation

    self.logic = None
    transformationsPath = os.path.join(os.path.dirname(__file__), 'Data/Transforms.csv')
    with open(transformationsPath, 'r') as read_transforms:
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

    # UI using xml method
    # uiWidget = slicer.util.loadUI(self.resourcePath('UI/Track.ui'))
    # self.layout.addWidget(uiWidget)
    # self.ui = slicer.util.childWidgetVariables(uiWidget)

    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    # uiWidget.setMRMLScene(slicer.mrmlScene)

    #
    # Begin GUI construction
    #

    #
    # Inputs Area
    # 

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

    self.inputsFormLayout.addRow("2D Time Series Images Folder:", self.Folder2DTimeSeries)

    # 3D volumne file selector
    self.Path3DVolume = ctk.ctkPathLineEdit()
    self.Path3DVolume.filters = ctk.ctkPathLineEdit.Files | ctk.ctkPathLineEdit.Executable | ctk.ctkPathLineEdit.NoDot | ctk.ctkPathLineEdit.NoDotDot |  ctk.ctkPathLineEdit.Readable
    self.Path3DVolume.settingKey = 'Path3DVolume'

    self.inputsFormLayout.addRow("3D Volume file:", self.Path3DVolume)

    # Transformations file selector 
    self.TransformationsFile = ctk.ctkPathLineEdit()
    self.TransformationsFile.filters = ctk.ctkPathLineEdit.Files | ctk.ctkPathLineEdit.NoDot | ctk.ctkPathLineEdit.NoDotDot |  ctk.ctkPathLineEdit.Readable
    self.TransformationsFile.settingKey = 'TransformationsFile'

    self.inputsFormLayout.addRow("Transformations File (.csv):", self.TransformationsFile)

    #
    # Sequence Area
    # 

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
    self.PlaySequenceButton.enabled = False
    self.PlaySequenceButton.setSizePolicy(qt.QSizePolicy.Minimum,qt.QSizePolicy.Minimum)
    self.controlLayout.addWidget(self.PlaySequenceButton)
    
    # Play button
    self.PauseSequenceButton = qt.QPushButton("Pause")
    self.PauseSequenceButton.enabled = False
    self.PauseSequenceButton.setSizePolicy(qt.QSizePolicy.Minimum,qt.QSizePolicy.Minimum)
    self.controlLayout.addWidget(self.PauseSequenceButton)

    # Play button
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
    self.DecrementFrame = qt.QPushButton("<-")
    self.DecrementFrame.enabled = False
    self.DecrementFrame.setSizePolicy(qt.QSizePolicy.Maximum,qt.QSizePolicy.Minimum)
    self.changeFrameLayout.addWidget(self.DecrementFrame)

    # Increase Frame
    self.IncrementFrame = qt.QPushButton("->")
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
    # End GUI construction
    #

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = TrackLogic()


        
    # this is the variables that will be used to store parameters
    info = {"playing": False, "fps": 1}

    # Each of these three corresponds to the three windows in the GUI
    yellow = slicer.app.layoutManager().sliceWidget("Yellow").sliceLogic()
    green  = slicer.app.layoutManager().sliceWidget("Green").sliceLogic()
    red    = slicer.app.layoutManager().sliceWidget("Red").sliceLogic()

    # this will store the transformation of the mask/segmentation
    transformMatrix = vtk.vtkMatrix4x4()
    def UpdateSlices():
        """This method updates the offset of all three sliceWidget windows"""
        def _move_slice_(slice_widget):
          """This inner function will set offset of one window passed in"""
          bounds = [0] * 6 #buffer to hold min-max of the 3 axes 
          slice_widget.GetLowestVolumeSliceBounds(bounds)
          #calculate the offset needed to get to the current "Frame"
          offset = min(bounds[4] + self.SequenceSlider.value, bounds[5]) 
          slice_widget.SetSliceOffset(offset) # set it.

        #We can now update each window
        _move_slice_(yellow)
        _move_slice_(green)
        _move_slice_(red)

        #attempting to move the segmentation mask only if the frame we are on
        #has a corresponding row in the csv file
        val = self.SequenceSlider.value
        if val < len(self.csv):
          row = self.csv[val]
          transformMatrix.SetElement(0,3, int(float(row[0])))
          transformMatrix.SetElement(1,3, int(float(row[1])))
          transformMatrix.SetElement(2,3, int(float(row[2])))
        
          self.logic.transformNode.SetMatrixTransformToParent(transformMatrix)
          slicer.app.processEvents()

        #changing the seconds label as we have updated the slices
        self.SequenceFrame.text = f"{float(self.SequenceSlider.value):.1f}s"

    def _PlaySeq_():
      """This will continously move the slider to the next frame / second"""
      # we need to make sure we have not hit the max frame and that we are actually still playing
      if self.SequenceSlider.value < self.SequenceSlider.maximum and info["playing"]:
        self.SequenceSlider.value += self.Fps.value
        self.SequenceSlider.value = min(self.SequenceSlider.value,self.SequenceSlider.maximum)
        self.SequenceFrame.text = f"{float(self.SequenceSlider.value):.1f}s"
        UpdateSlices()
        qt.QTimer.singleShot(100, _PlaySeq_) #this is used to repeat the function to loop
      else:
        #we then change the information accordingly and enable/disable the correct buttons
        info["playing"] = False
        self.PlaySequenceButton.enabled = True
        self.StopSequenceButton.enabled = False

    def PlaySeq():
      """This method will play the sequence, making sure that it will only play it once even if you double click"""
      if info["playing"]: return
      info["playing"] = True
      _PlaySeq_()
      self.PlaySequenceButton.enabled = False
      self.StopSequenceButton.enabled = True

    def StopSeq():
      info["playing"] = False
      self.PlaySequenceButton.enabled = True
      self.StopSequenceButton.enabled = False

    #connecting the events to their respective functions
    self.PlaySequenceButton.clicked.connect(PlaySeq)
    self.StopSequenceButton.clicked.connect(StopSeq)
    self.SequenceSlider.valueChanged.connect(lambda _: UpdateSlices())
    
    def ChangeFrame(amount: int):
      """This method will change the frame of the sequence, making sure the value is within range"""
      value = max(0, self.SequenceSlider.value + amount)
      value = min(value,self.SequenceSlider.maximum)
      self.SequenceSlider.value = value
      # we can then update the slices so it displays the correct frame
      UpdateSlices()
    self.IncrementFrame.clicked.connect(lambda: ChangeFrame(+1))
    self.DecrementFrame.clicked.connect(lambda: ChangeFrame(-1))

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
      """When we have changed path, we need to load data and display it"""
      self.logic.ClearNodes()
      self.logic.ShowData(path)

      #after loading data, set orientations
      slicer.app.layoutManager().sliceWidget("Yellow").mrmlSliceNode().SetOrientationToAxial()
      slicer.app.layoutManager().sliceWidget("Green").mrmlSliceNode().SetOrientationToAxial()
      slicer.app.layoutManager().sliceWidget("Red").mrmlSliceNode().SetOrientationToAxial()

      #enabling buttons since we have loaded data
      self.PlaySequenceButton.enabled = True
      self.SequenceSlider.enabled = True
      self.IncrementFrame.enabled = True
      self.DecrementFrame.enabled = True

      def _bounds_(slice_widget):
        """This function will return the upper bound of the sliceWidget passed in"""
        bounds = [0] * 6
        slice_widget.GetLowestVolumeSliceBounds(bounds)
        return int(bounds[5]-bounds[4]) - 1
      #we pick the lowest offset max. This will be our max frame value
      maximum = max(_bounds_(red), _bounds_(green), _bounds_(yellow))
      self.SequenceSlider.maximum =maximum

    # will replace with new input selector
    self.Folder2DTimeSeries.currentPathChanged.connect(lambda path: OnPathChange(path))


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
    # self.applyButton.enabled = self._parameterNode.GetNodeReference("InputVolume")

  #NOT USED
  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    self._parameterNode.SetNodeReferenceID("InputVolume", self.inputSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("OutputVolume", self.outputSelector.currentNodeID)
    self._parameterNode.SetParameter("Threshold", str(self.imageThresholdSliderWidget.value))
    self._parameterNode.SetParameter("Invert", "true" if self.invertOutputCheckBox.checked else "false")
    self._parameterNode.SetNodeReferenceID("OutputVolumeInverse", self.invertedOutputSelector.currentNodeID)

    self._parameterNode.EndModify(wasModified)

  #NOT USED
  def onEnableAutoUpdate(self, autoUpdate):
    if self.markupsObserverTag:
      self.observedMarkupNode.RemoveObserver(self.markupsObserverTag)
      self.observedMarkupNode = None
      self.markupsObserverTag = None
    if autoUpdate and self.inputSelector.currentNode:
      self.observedMarkupNode = self.inputSelector.currentNode()
      self.markupsObserverTag = self.observedMarkupNode.AddObserver(
      slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onMarkupsUpdated)
  
  #NOT USED
  def onMarkupsUpdated(self, caller=None, event=None):
    self.onApplyButton()

  #NOT USED
  def onApplyButton(self):
    self.logic.process(self.inputSelector.currentNode(),
      self.invertedOutputSelector.currentNode(),
      self.imageThresholdSliderWidget.value,
      not self.invertOutputCheckBox.checked)
    self.centerOfMassValueLabel.text = str(self.logic.centerOfMass)

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
    # ProTry(path)

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
    volumes = []
    for s in pathlist:
        filename = os.path.join(dicomDataDir, s)
        if "Stack" in s:
          node = slicer.util.loadVolume(filename)
          self.nodes.append(node)
          volumes.append(node)
          print(f"loaded {filename}")
        elif "Segmentation_nrrd" in s:
          node = slicer.util.loadSegmentation(filename)
          self.nodes.append(node)
          # Create transform and apply to sample volume
          transformNode = slicer.vtkMRMLTransformNode()
          self.transformNode = transformNode
          slicer.mrmlScene.AddNode(transformNode)
          node.SetAndObserveTransformNodeID(transformNode.GetID())
          
    axis = ["Yellow", "Green", "Red"]
    for volume in volumes:
      widget = axis.pop()
      compositeNode = slicer.app.layoutManager().sliceWidget(widget).sliceLogic().GetSliceCompositeNode()
      compositeNode.SetBackgroundVolumeID(volume.GetID())
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
