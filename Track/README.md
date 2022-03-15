**Note**: I have marked any unused code with an "#NOT USED" comment before it.

**Note**: there is some memory issues whenever you are developing. This occurs whenever you
load data, and happen to need to click the reload button, and then load data again.
The previously loaded data stays in memory and this can cause the memory usage to keep increasing. I tried removing the previously loaded data but could not get it to work. 
*For now just close and reopen 3D slicer if you happen to reload 4 or 5 times*

**Note**: For now, an offset is necessary is the lower and upper bounds of the slicerWidgets are 
not correct

**Note**: The axial orientation does not show properly (no data with axial axis)

*Everything below is talking about the code in Track.py*

The module starts off with the buttons disabled. 

Once you load in data the OnPathChange() function is called,
which loads and shows the data as well as enabling the buttons.
- it also calculates the offset as 3d slicer's sliceWidget does not start at 1 for frame 1

If you want to select an element on the ui via code, first name it something unique
on the qt editor (under the objectName property)
- you can then access it by doing self.ui.<object name>
- for example, an objectName of fps can be accessed with self.ui.fps

To connect an event on any object: self.ui.<object name>.<event>.connect(callback)
- if you need to figure out possible events, an easy way is to go on the qt editor,
select Signal/Slot editor on the bottom right, Add a signal, select the sender as the object
you want to inspect, and then the signal list will show all possible <event> names.

For the events that I have used, I create a function right before using the .connect(callback) function.
- If i needed to have a more generalized, I would customize it per event by using a lambda
    - for example if I have a ChangeFrame function, instead of passing it directly, I can do: 
    .connect(lambda: ChangeFrame(+1)) and .connect(lambda: ChangeFrame(-1))

The logic class contains:
- Processing data by splitting it into the 3 orientation slices
- saves them to an output folder
- Then loads them into the 3d slicer scene