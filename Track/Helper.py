import qt
import slicer
from slicer.ScriptedLoadableModule import *

class Helper(ScriptedLoadableModule):
    def __init__(self):
        pass

class Slider(qt.QSlider):
    def __init__(self, parent=None):
        super().__init__(qt.Qt.Horizontal, parent)
    
    def mousePressEvent(self, event):
        sliderThumbRect = self.sliderPosition
        clickValue = qt.QStyle.sliderValueFromPosition(self.minimum, self.maximum, event.pos().x(), self.width)
        if abs(clickValue - sliderThumbRect) > 1: # Checks if sliderThumbRect was not pressed by the user
            self.setValue(clickValue)
        else:
            self.mouseMoveEvent(event)
        
    def mouseMoveEvent(self, event):
    # Reimplements the default scrolling functionality of QSlider
        self.setValue(qt.QStyle.sliderValueFromPosition(self.minimum, self.maximum, event.pos().x(), self.width))
        event.accept()
    
    def mouseReleaseEvent(self, event):
    # Handle mouse release events (when done dragging)
        self.sliderReleased.emit()

class SpinBox(qt.QSpinBox):
    # Custom signals for up and down button interactions
    upButtonClicked = qt.Signal()
    downButtonClicked = qt.Signal()
    
    # Inherit everything previously defined in QSpinBox
    def __init__(self, parent=None):
        super().__init__(parent)
    
    # Overrides the predefined stepBy() method of QSpinBox  
    def stepBy(self, steps):
        if steps > 0:
            self.upButtonClicked.emit() # emit upButtonClicked if value on QSpinBox increased
        elif steps < 0:
            self.downButtonClicked.emit() # emit downButtonClicked if value on QSpinBox decreased