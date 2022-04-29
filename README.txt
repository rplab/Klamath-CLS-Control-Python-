Conventional Light Sheet Control Software (for use with Micro-Manager)

Jonah Sokoloff
Parthasarathy Lab
University of Oregon

First Written: March 2022
Last Modified: 4/12/2022

This program was created for two main reasons:

1. To create custom imaging acquisitions for the conventioanl light sheet setup
2. To bridge the NIDAQ galvo mirror software and Micro-Manager to allow for better
   hardware control

Most of the acquisition code itself is adapted from a java plugin I wrote for MM 
called "Continuous Stage Acquisition" which was mostly created to take image acquisitions
with continuous stage movement during z-stacks. With the creation of Pycro-Manager,
a dynamic python-to-MM-API translation module, it seemed reasonable to finally create this bridge.

This program is built on the Model-View-Controller framework, a modern standard for desktop applications
and web developemnt. 

Files:

AppStart.py - Application launch file. Requires Micro-Manager to be open and have port access enabled
              (see pycromanager documentation).

Controller.py - Contains all controller classes, one for each main GUI element.

QtDesignerGUI.py - Contains all GUI elements. An instance of each element is created in its respective controller.

GeneratedUI folder - All GUI files in here were created in QtDesigner and then converted to Python files.

HardwareCommands.py - Contains all device properties and methods that interact directly with hardware.

CLSAcquisiiton.py - Main acquisition script.

CLSAcquisitionParameters.py - The model file. Contains two classes that store data for use in acquisition.

