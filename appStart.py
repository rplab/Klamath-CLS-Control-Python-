"""Initialization file. This entire app uses camel case because
I like it more than the python "_" convention. Sorry not sorry.
Also, the Micro-Manager API is in camel case and I wrote my original
code in java, so translating it all would've been annoying. A large amount
of this code is translated/adapted from a Micro-Manager plugin
"Continuous Stage Acquisition" I wrote to be able to use custom acquisition
scripts with a GUI.

"""

from pycromanager import Studio, Core
import Controller
from PyQt5.QtWidgets import QApplication
from pycromanager import Studio, Core
import sys

core = Core()
studio = Studio()

app = QApplication(sys.argv)
controller = Controller.MainController(studio, core)
controller.main_window.show()
app.exec_()