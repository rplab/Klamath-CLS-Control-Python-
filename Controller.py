"""
Last Modified: 4/12/2022

This file contains all the controller classes. There are three, one for each of the main GUI elements.

Classes:

MainController - Creates instances of controllers and hardware command classes to allow the same instances to be passed to one another.

CLSController - The main controller for CLS acquisitions. Creates an instance of AcquisitionSettings
                from CLSAcquisitionParameters to set up a CLS experiment. Most of the logic goes into
                creating the region_settings_list in acquisition_settings. A pseudo pointer object named
                region_settings is created in the controller to correctly track and update list elements.

SPIMGalvoController - Interacts with the spim_commands class within the HardwareCommands file. It controls
                      the setting of properties for the NIDAQ that controls the galvo mirrors for laser scanning.


Future Changes:
- As always, some logic could probably be made more clear.

- Not sure how to deal with new instances of region_settings when needed. When a
new instance of region_settings is created, should the GUI be the initial values?
Not sure what is best.

- All classes (other than RegionSettings) should probably be made into singletons, since we only want one instance of each.
Probably not a big deal either way.

- Error handling could be much better.
"""

import numpy as np
from pathlib import Path
import configparser
import os
import copy
from PyQt5 import QtCore, QtGui, QtWidgets
import QtDesignerGUI
import CLSAcquisitionParameters
import HardwareCommands
from CLSAcquisition import Acquisition
from pycromanager import Studio, Core


class MainController(object):
    acquisition_settings_section = 'Acquisition Settings'
    spim_galvo_section = 'SPIM Galvo Settings'
    config_file_name = 'CLSConfig.cfg'
    config = configparser.RawConfigParser()

    def __init__(self, studio: Studio, core: Core):
        self.main_window = QtDesignerGUI.MainWindow()
        MainController.config = MainController.initialize_config_file()

        self.studio = studio
        self.core = core

        self.mm_hardware_commands = HardwareCommands.MMHardwareCommands(self.studio, self.core)
        self.spim_commands = HardwareCommands.SPIMGalvoCommands()

        self.spim_controller = SPIMController(self.studio, self.core, self.mm_hardware_commands, self.spim_commands)
        self.cls_controller = CLSController(self.studio, self.core, self.mm_hardware_commands, self.spim_commands)

        #initialize main window and event handlers. This flag is set to disable the
        #buttons on the top right of the window.
        self.main_window.setWindowFlags(QtCore.Qt.WindowTitleHint)
        self.main_window.spim_galvo_button.clicked.connect(self.spim_galvo_button_clicked)
        self.main_window.cls_button.clicked.connect(self.cls_button_clicked)
        self.main_window.exit_button.clicked.connect(self.exit_button_clicked)

    def cls_button_clicked(self):
        self.cls_controller.cls_dialog.show()
        self.cls_controller.cls_dialog.activateWindow()

    def spim_galvo_button_clicked(self):
        self.spim_controller.spim_dialog.show()
        self.spim_controller.spim_dialog.activateWindow()

    def exit_button_clicked(self):
        self.spim_commands.exit()
        quit()
    
    def initialize_config_file():
        config = configparser.RawConfigParser()
        if os.path.exists(MainController.config_file_name):
            config.read(MainController.config_file_name)

        return config

    def read_from_config():
        config = configparser.RawConfigParser()
        try:
            config.read('CLSCongif.cfg')
            return config
        except:
            print("couldn't read config file")
            return
        try:
            section = 'Acquisition Settings'
            settings = self.cls_controller.acquisition_settings
            settings.time_points_boolean = config.getboolean(section, 'time_bool')
            settings.time_points_interval = config.getint(section, 'time_int')
            settings.num_time_points = config.getint(section, 'num_time')
            settings.z_scan_speed = config.getfloat(section, 'scan_speed')
            settings.lightsheet_mode_boolean = config.getboolean(section, 'lsrm_bool')
        except:
            print('No Acquisition Settings Section')

        for sample_index in range(self.cls_controller.acquisition_settings.sample_dimension):
            for region_index in range(self.cls_controller.acquisition_settings.region_dimension):
                try:
                    section = 'Sample ' + str(sample_index) + ' Region ' + str(region_index)
                    region = CLSAcquisitionParameters.RegionSettings()
                    region.x_position = config.getint(section, 'x_pos')
                    region.y_position = config.getint(section, 'y_pos')
                    region.z_position = config.getint(section, 'z_pos')
                    region.z_stack_boolean = config.getboolean(section, 'z_bool')
                    region.z_start_position = config.getint(section, 'z_start')
                    region.z_end_position = config.getint(section, 'z_end')
                    region.step_size = config.getint(section, 'step')
                    region.snap_boolean = config.getboolean(section, 'snap_bool')
                    region.snap_exposure_time = config.getint(section, 'snap_exp')
                    region.video_boolean = config.getboolean(section, 'video_bool')
                    region.video_duration_in_seconds = config.getint(section, 'video_dur')
                    region.video_exposure_time = config.getint(section, 'video_exp')
                    settings.region_settings_list[sample_index][region_index] = region
                    if sample_index == region_index == 0:
                        self.cls_controller.region_settings = region
                    print('Region read at sample index ' + str(sample_index) + ', region index ' + str(region_index))
                except:
                    None
        
        try:
            section = 'SPIM Galvo Settings'
            spim = self.spim_commands
            spim.focus = config.getfloat(section, 'focus')
            spim.continuous_scan_offset = config.getfloat(section, 'cont_offset')
            spim.continuous_scan_width = config.getfloat(section, 'widtj')
            spim.ligthsheet_readout_current_position = config.getfloat(section, 'lsrm_pos')
            spim.lightsheet_readout_upper = config.getfloat(section, 'lsrm_upper')
            spim.lightsheet_readout_lower = config.getfloat(section, 'lsrm_lower')
            spim.lightsheet_readout_framerate = config.getfloat(section, 'framerate')
            spim.lightsheet_readout_laser_delay = config.getfloat(section, 'laser_delay')
            spim.lightsheet_readout_cam_delay = config.getfloat(section, 'cam_delay')
        except:
            'No SPIM Galvo Settings Section'




class CLSController(object):
    """Future Changes:
    - As always, some logic could probably be made more clear.
    - Not sure how to deal with new instances of region_settings when needed. When a
      new instance of region_settings is created, should the GUI update to initial values?
      Not sure what is best.
    - There's gotta be a better way to validate user entries. Finding a nice way to do this (potentially with
      an entirely different class) would make the program much cleaner/clearer.
    - In general, write_to_config() is called when set_table() is called and both iterate through region_list
      separately. Could combine them so it only iterates through once.
    """

    def __init__(self, studio: Studio, core: Core, mm_hardware_commands: HardwareCommands.MMHardwareCommands,
                 spim_commands: HardwareCommands.SPIMGalvoCommands):
        self.studio = studio
        self.core = core
        self.mm_hardware_commands = mm_hardware_commands
        self.spim_commands = spim_commands
        self.cls_dialog = QtDesignerGUI.CLSDialog()
        self.acquisition_settings_dialog = QtDesignerGUI.CLSAcquisitionSettingsDialog()
        self.acquisition_dialog = QtDesignerGUI.AcquisitionDialog()
        self.acquisition_settings = CLSAcquisitionParameters.AcquisitionSettings()
        self.region_settings = CLSAcquisitionParameters.RegionSettings()
        self.region_settings_copy = copy.deepcopy(self.region_settings)
        self.start_path = 'G:'
        self.num_images_per = 0

        self.sample_num = 0
        self.region_num = 0

        self.cls_dialog.sample_label.setText("Sample " + str(self.sample_num + 1))
        self.cls_dialog.region_label.setText("Region " + str(self.region_num + 1))

        # initialize item models
        self.cls_dialog.region_table_view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.region_table_model = QtGui.QStandardItemModel()
        self.cls_dialog.region_table_view.setModel(self.region_table_model)
        self.z_stack_available_model = QtGui.QStandardItemModel()
        self.cls_dialog.z_stack_available_list_view.setModel(self.z_stack_available_model)
        self.z_stack_used_model = QtGui.QStandardItemModel()
        self.cls_dialog.z_stack_used_list_view.setModel(self.z_stack_used_model)
        self.snap_available_model = QtGui.QStandardItemModel()
        self.cls_dialog.snap_available_list_view.setModel(self.snap_available_model)
        self.snap_used_model = QtGui.QStandardItemModel()
        self.cls_dialog.snap_used_list_view.setModel(self.snap_used_model)
        self.video_available_model = QtGui.QStandardItemModel()
        self.cls_dialog.video_available_list_view.setModel(self.video_available_model)
        self.video_used_model = QtGui.QStandardItemModel()
        self.cls_dialog.video_used_list_view.setModel(self.video_used_model)
        self.channel_order_model = QtGui.QStandardItemModel()
        self.acquisition_settings_dialog.channel_order_list_view.setModel(self.channel_order_model)

        headers = ["sample #", "reg #", "x", "y", "z", "z stack", "start",
                   "end", "step", "chans", "snap", "exp", "chans", "video",
                   "dur", "exp", "chans", "# images"]
        self.region_table_model.setHorizontalHeaderLabels(headers)
        self.cls_dialog.region_table_view.resizeColumnsToContents()

        core_channel_vector = self.core.get_available_configs(self.acquisition_settings.channel_group_name)
        self.core_channel_list = []
        for i in range(core_channel_vector.size()):
            channel = core_channel_vector.get(i)
            self.core_channel_list.append(channel)

        self.acquisition_settings.channel_order_list = copy.deepcopy(self.core_channel_list)

        for channel in self.core_channel_list:
            item = QtGui.QStandardItem(channel)
            self.z_stack_available_model.appendRow(QtGui.QStandardItem(item))
            self.snap_available_model.appendRow(QtGui.QStandardItem(item))
            self.video_available_model.appendRow(QtGui.QStandardItem(item))
            self.channel_order_model.appendRow(QtGui.QStandardItem(item))

        # initialize cls_dialog line edit event handlers and validators
        self.cls_dialog.x_line_edit.textEdited.connect(self.x_line_edit_event)
        self.cls_dialog.x_line_edit.setValidator(QtGui.QIntValidator())

        self.cls_dialog.y_line_edit.textEdited.connect(self.y_line_edit_event)
        self.cls_dialog.y_line_edit.setValidator(QtGui.QIntValidator())

        self.cls_dialog.z_line_edit.textEdited.connect(self.z_line_edit_event)
        self.cls_dialog.z_line_edit.setValidator(QtGui.QIntValidator())

        self.cls_dialog.start_z_line_edit.textEdited.connect(self.start_z_line_edit_event)
        self.cls_dialog.start_z_line_edit.setValidator(QtGui.QIntValidator())

        self.cls_dialog.end_z_line_edit.textEdited.connect(self.end_z_line_edit_event)
        self.cls_dialog.end_z_line_edit.setValidator(QtGui.QIntValidator())

        self.cls_dialog.step_size_line_edit.textEdited.connect(self.step_size_line_edit_event)
        validator = QtGui.QIntValidator()
        validator.setBottom(0)
        self.cls_dialog.step_size_line_edit.setValidator(validator)

        self.cls_dialog.snap_exposure_line_edit.textEdited.connect(self.snap_exposure_line_edit_event)
        validator = QtGui.QIntValidator()
        validator.setBottom(10)
        self.cls_dialog.snap_exposure_line_edit.setValidator(validator)

        self.cls_dialog.video_duration_line_edit.textEdited.connect(self.video_duration_line_edit_event)
        validator = QtGui.QIntValidator()
        validator.setBottom(1)
        self.cls_dialog.video_duration_line_edit.setValidator(validator)

        self.cls_dialog.video_exposure_line_edit.textEdited.connect(self.video_exposure_line_edit_event)
        validator = QtGui.QIntValidator()
        validator.setBottom(10)
        self.cls_dialog.video_exposure_line_edit.setValidator(validator)

        self.cls_dialog.go_to_button.clicked.connect(self.go_to_button_clicked)
        self.cls_dialog.set_region_button.clicked.connect(self.set_region_button_clicked)
        self.cls_dialog.next_region_button.clicked.connect(self.next_region_button_clicked)
        self.cls_dialog.previous_region_button.clicked.connect(self.previous_region_button_clicked)
        self.cls_dialog.next_sample_button.clicked.connect(self.next_sample_button_clicked)
        self.cls_dialog.previous_sample_button.clicked.connect(self.previous_sample_button_clicked)
        self.cls_dialog.remove_region_button.clicked.connect(self.remove_region_button_clicked)
        self.cls_dialog.copy_region_button.clicked.connect(self.copy_button_clicked)
        self.cls_dialog.paste_region_button.clicked.connect(self.paste_button_clicked)
        self.cls_dialog.set_z_start_button.clicked.connect(self.set_z_start_button_clicked)
        self.cls_dialog.set_z_end_button.clicked.connect(self.set_z_end_button_clicked)
        self.cls_dialog.acquisition_setup_button.clicked.connect(self.acquisition_setup_button_clicked)
        self.cls_dialog.z_stack_check_box.clicked.connect(self.z_stack_check_clicked)
        self.cls_dialog.snap_check_box.clicked.connect(self.snap_check_clicked)
        self.cls_dialog.video_check_box.clicked.connect(self.video_check_clicked)
        self.cls_dialog.z_stack_available_list_view.doubleClicked.connect(self.z_stack_available_list_move)
        self.cls_dialog.z_stack_used_list_view.doubleClicked.connect(self.z_stack_used_list_move)
        self.cls_dialog.snap_available_list_view.doubleClicked.connect(self.snap_available_list_move)
        self.cls_dialog.snap_used_list_view.doubleClicked.connect(self.snap_used_list_move)
        self.cls_dialog.video_available_list_view.doubleClicked.connect(self.video_available_list_move)
        self.cls_dialog.video_used_list_view.doubleClicked.connect(self.video_used_list_move)

        # initialize clsAcquisitionSettingsDialog line edits event handlers and validators
        self.acquisition_settings_dialog.num_time_points_line_edit.textEdited.connect(
            self.num_time_points_line_edit_event)
        self.acquisition_settings_dialog.num_time_points_line_edit.setValidator(QtGui.QIntValidator().setBottom(0))
        self.acquisition_settings_dialog.time_points_interval_line_edit.textEdited.connect(
            self.time_points_interval_line_edit_event)
        self.acquisition_settings_dialog.time_points_interval_line_edit.setValidator(QtGui.QIntValidator().setBottom(0))
        self.acquisition_settings_dialog.browse_button.clicked.connect(self.browse_button_clicked)
        self.acquisition_settings_dialog.channel_order_move_up_button.clicked.connect(
            self.channel_move_up_button_clicked)
        self.acquisition_settings_dialog.channel_order_move_down_button.clicked.connect(
            self.channel_move_down_button_clicked)
        self.acquisition_settings_dialog.start_acquisition_button.clicked.connect(self.start_acquisition_button_clicked)
        self.acquisition_settings_dialog.time_points_check_box.clicked.connect(self.time_points_check_clicked)
        self.acquisition_settings_dialog.lsrm_check_box.clicked.connect(self.lsrm_check_clicked)
        self.acquisition_settings_dialog.stage_speed_combo_box.activated.connect(self.stage_speed_combo_box_clicked)


        self.initialize_from_config()

    def write_to_config(self):
        config = MainController.config
        section = MainController.acquisition_settings_section
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, 'time_bool', str(self.acquisition_settings.time_points_boolean))
        config.set(section, 'time_int', str(self.acquisition_settings.time_points_interval))
        config.set(section, 'num_time', str(self.acquisition_settings.num_time_points))
        config.set(section, 'scan_speed', str(self.acquisition_settings.z_scan_speed))
        config.set(section, 'lsrm_bool', str(self.acquisition_settings.lightsheet_mode_boolean))

        
        for sample_index in range(self.acquisition_settings.sample_dimension):
            for region_index in range(self.acquisition_settings.region_dimension):
                section = 'Sample ' + str(sample_index) + ' Region ' + str(region_index)
                if config.has_section(section):
                    config.remove_section(section)
                region = self.acquisition_settings.region_settings_list[sample_index][region_index]
                if region != 0:
                    section = 'Sample ' + str(sample_index) + ' Region ' + str(region_index)
                    config.add_section(section)
                    config.set(section, 'x_pos', str(region.x_position))
                    config.set(section, 'y_pos', str(region.y_position))
                    config.set(section, 'z_pos', str(region.z_position))
                    config.set(section, 'z_bool', str(region.z_stack_boolean))
                    config.set(section, 'z_start', str(region.z_start_position))
                    config.set(section, 'z_end', str(region.z_end_position))
                    config.set(section, 'step', str(region.step_size))
                    config.set(section, 'snap_bool', str(region.snap_boolean))
                    config.set(section, 'snap_exp', str(region.snap_exposure_time))
                    config.set(section, 'video_bool', str(region.video_boolean))
                    config.set(section, 'video_dur', str(region.video_duration_in_seconds))
                    config.set(section, 'video_exp', str(region.video_exposure_time))

        with open(MainController.config_file_name, 'w') as configfile:
            config.write(configfile)
        
    def initialize_from_config(self):
        config = MainController.config
        section = MainController.acquisition_settings_section
        if config.has_section(section):
            try:
                self.acquisition_settings.time_points_boolean = config.getboolean(section, 'time_bool')
                self.acquisition_settings.time_points_interval = config.getint(section, 'time_int')
                self.acquisition_settings.num_time_points = config.getint(section, 'num_time')
                self.acquisition_settings.z_scan_speed = config.getfloat(section, 'scan_speed')
                self.acquisition_settings.lightsheet_mode_boolean = config.getboolean(section, 'lsrm_bool')
            except:
                print('section line missing')
        
        #Initialize gui elements based on config file
        self.acquisition_settings_dialog.time_points_check_box.setChecked(self.acquisition_settings.time_points_boolean)
        self.acquisition_settings_dialog.num_time_points_line_edit.setEnabled(self.acquisition_settings.time_points_boolean)
        self.acquisition_settings_dialog.time_points_interval_line_edit.setEnabled(self.acquisition_settings.time_points_boolean)
        self.acquisition_settings_dialog.start_acquisition_button.setEnabled(False)
        self.acquisition_settings_dialog.num_images_per_line_edit.setEnabled(False)
        self.acquisition_settings_dialog.total_images_line_edit.setEnabled(False)
        self.acquisition_settings_dialog.memory_line_edit.setEnabled(False)
        self.acquisition_settings_dialog.lsrm_check_box.setChecked(self.acquisition_settings.lightsheet_mode_boolean)
        if self.acquisition_settings.z_scan_speed == 0.015:
            self.acquisition_settings_dialog.stage_speed_combo_box.setCurrentText('15 um/s')
        if self.acquisition_settings.z_scan_speed == 0.030:
            self.acquisition_settings_dialog.stage_speed_combo_box.setCurrentText('30 um/s')

        for sample_index in range(self.acquisition_settings.sample_dimension):
            for region_index in range(self.acquisition_settings.region_dimension):
                section = 'Sample ' + str(sample_index) + ' Region ' + str(region_index)
                if config.has_section(section):
                    try:
                        region = CLSAcquisitionParameters.RegionSettings()
                        region.x_position = config.getint(section, 'x_pos')
                        region.y_position = config.getint(section, 'y_pos')
                        region.z_position = config.getint(section, 'z_pos')
                        region.z_stack_boolean = config.getboolean(section, 'z_bool')
                        region.z_start_position = config.getint(section, 'z_start')
                        region.z_end_position = config.getint(section, 'z_end')
                        region.step_size = config.getint(section, 'step')
                        region.snap_boolean = config.getboolean(section, 'snap_bool')
                        region.snap_exposure_time = config.getint(section, 'snap_exp')
                        region.video_boolean = config.getboolean(section, 'video_bool')
                        region.video_duration_in_seconds = config.getint(section, 'video_dur')
                        region.video_exposure_time = config.getint(section, 'video_exp')
                        self.acquisition_settings.region_settings_list[sample_index][region_index] = region

                        if sample_index == region_index == 0:
                            self.region_settings = region
                        print('Region read at sample index ' + str(sample_index) + ', region index ' + str(region_index))
                    except:
                        'section line missing'

        #Initialize gui elements baseed on config file
        initial_bool = self.acquisition_settings.region_settings_list[0][0] != 0
        self.cls_dialog.go_to_button.setEnabled(initial_bool)
        self.cls_dialog.remove_region_button.setEnabled(initial_bool)
        self.cls_dialog.next_region_button.setEnabled(initial_bool)
        self.cls_dialog.next_sample_button.setEnabled(initial_bool)
        self.cls_dialog.previous_sample_button.setEnabled(False)
        self.cls_dialog.previous_region_button.setEnabled(False)

        self.set_table()
        self.update_cls_dialog()

    def update_cls_dialog(self):
        # Updates all the GUI elements (apart from the table) to reflect the
        # values in the current region_settings instance.

        self.cls_dialog.sample_label.setText("Sample " + str(self.sample_num + 1))
        self.cls_dialog.region_label.setText("Region " + str(self.region_num + 1))

        self.cls_dialog.x_line_edit.setText(str(self.region_settings.x_position))
        self.cls_dialog.y_line_edit.setText(str(self.region_settings.y_position))
        self.cls_dialog.z_line_edit.setText(str(self.region_settings.z_position))

        z_stack_boolean = self.region_settings.z_stack_boolean
        self.cls_dialog.z_stack_check_box.setChecked(z_stack_boolean)
        self.cls_dialog.set_z_start_button.setEnabled(z_stack_boolean)
        self.cls_dialog.set_z_end_button.setEnabled(z_stack_boolean)
        self.cls_dialog.start_z_line_edit.setEnabled(z_stack_boolean)
        self.cls_dialog.end_z_line_edit.setEnabled(z_stack_boolean)
        self.cls_dialog.step_size_line_edit.setEnabled(z_stack_boolean)
        self.cls_dialog.z_stack_available_list_view.setEnabled(z_stack_boolean)
        self.cls_dialog.z_stack_used_list_view.setEnabled(z_stack_boolean)

        snap_boolean = self.region_settings.snap_boolean
        self.cls_dialog.snap_check_box.setChecked(snap_boolean)
        self.cls_dialog.snap_exposure_line_edit.setEnabled(snap_boolean)
        self.cls_dialog.snap_available_list_view.setEnabled(snap_boolean)
        self.cls_dialog.snap_used_list_view.setEnabled(snap_boolean)

        video_boolean = self.region_settings.video_boolean
        self.cls_dialog.video_check_box.setChecked(video_boolean)
        self.cls_dialog.video_duration_line_edit.setEnabled(video_boolean)
        self.cls_dialog.video_exposure_line_edit.setEnabled(video_boolean)
        self.cls_dialog.video_available_list_view.setEnabled(video_boolean)
        self.cls_dialog.video_used_list_view.setEnabled(video_boolean)

        self.cls_dialog.start_z_line_edit.setText(str(self.region_settings.z_start_position))
        self.cls_dialog.end_z_line_edit.setText(str(self.region_settings.z_end_position))
        self.cls_dialog.step_size_line_edit.setText(str(self.region_settings.step_size))

        self.cls_dialog.snap_exposure_line_edit.setText(str(self.region_settings.snap_exposure_time))

        self.cls_dialog.video_duration_line_edit.setText(str(self.region_settings.video_duration_in_seconds))
        self.cls_dialog.video_exposure_line_edit.setText(str(self.region_settings.video_exposure_time))

        self.z_stack_used_model.clear()
        for channel in self.region_settings.z_stack_channel_list:
            item = QtGui.QStandardItem(channel)
            self.z_stack_used_model.appendRow(item)

        self.z_stack_available_model.clear()
        for element in self.core_channel_list:
            for channel in self.region_settings.z_stack_channel_list:
                if element == channel:
                    break
            else:
                item = QtGui.QStandardItem(element)
                self.z_stack_available_model.appendRow(item)

        self.snap_used_model.clear()
        for channel in self.region_settings.snap_channel_list:
            item = QtGui.QStandardItem(channel)
            self.snap_used_model.appendRow(item)

        self.snap_available_model.clear()
        for element in self.core_channel_list:
            for channel in self.region_settings.snap_channel_list:
                if element == channel:
                    break
            else:
                item = QtGui.QStandardItem(element)
                self.snap_available_model.appendRow(item)

        self.video_used_model.clear()
        for channel in self.region_settings.video_channel_list:
            item = QtGui.QStandardItem(channel)
            self.video_used_model.appendRow(item)

        self.video_available_model.clear()
        for element in self.core_channel_list:
            for channel in self.region_settings.video_channel_list:
                if element == channel:
                    break
            else:
                item = QtGui.QStandardItem(element)
                self.video_available_model.appendRow(item)

    def set_table(self):
        self.num_images_per = 0
        self.region_table_model.clear()
        headers = ["sample #", "reg #", "x", "y", "z", "z stack", "start",
                   "end", "step", "chans", "snap", "exp", "chans", "video",
                   "dur", "exp", "chans", "# images"]
        self.region_table_model.setHorizontalHeaderLabels(headers)

        for sample_index in range(self.acquisition_settings.sample_dimension):
            for region_index in range(self.acquisition_settings.region_dimension):
                region = self.acquisition_settings.region_settings_list[sample_index][region_index]
                if region != 0:
                    num_z_stack_images = 0
                    num_snap_images = 0
                    num_video_images = 0
                    if region.z_stack_boolean:
                        num_z_stack_images = len(region.z_stack_channel_list) * np.round(
                            np.abs(region.z_start_position - region.z_end_position))
                    if region.snap_boolean:
                        num_snap_images = len(region.snap_channel_list)
                    if region.video_boolean:
                        num_video_images = len(region.video_channel_list) * int(
                            np.round(1000 / region.video_exposure_time * region.video_duration_in_seconds))
                    total_images = num_z_stack_images + num_video_images + num_snap_images

                    row_list = [str(sample_index + 1),
                                str(region_index + 1),
                                str(region.x_position),
                                str(region.y_position),
                                str(region.z_position),
                                str(region.z_stack_boolean),
                                str(region.z_start_position),
                                str(region.z_end_position),
                                str(region.step_size),
                                ','.join(region.z_stack_channel_list),
                                str(region.snap_boolean),
                                str(self.region_settings.snap_exposure_time),
                                ','.join(region.snap_channel_list),
                                str(region.video_boolean),
                                str(region.video_duration_in_seconds),
                                str(region.video_exposure_time),
                                ','.join(region.video_channel_list),
                                str(total_images)]

                    self.num_images_per += total_images
                    row_list = [QtGui.QStandardItem(element) for element in row_list]
                    self.region_table_model.appendRow(row_list)

        self.acquisition_settings_dialog.num_images_per_line_edit.setText(str(self.num_images_per))
        self.calculate_num_images()
        self.cls_dialog.region_table_view.resizeColumnsToContents()

    def calculate_num_images(self):
        if self.acquisition_settings.time_points_boolean:
            total_images = self.num_images_per * self.acquisition_settings.num_time_points
            self.acquisition_settings_dialog.total_images_line_edit.setText(str(total_images))
            memory = (total_images * 8.08) / 1000
            self.acquisition_settings_dialog.memory_line_edit.setText(("%.3f" % memory))
        else:
            self.acquisition_settings_dialog.total_images_line_edit.setText(str(self.num_images_per))
            memory = (self.num_images_per * 8.08) / 1000
            self.acquisition_settings_dialog.memory_line_edit.setText(("%.3f" % memory))

    def go_to_button_clicked(self):
        x_pos = self.region_settings.x_position
        y_pos = self.region_settings.y_position
        z_pos = self.region_settings.z_position

        self.mm_hardware_commands.move_stage(x_pos, y_pos, z_pos)

    def set_region_button_clicked(self):
        # Gets current stage position and creates element of region_settings_list
        # with current settings in GUI. Currently, this method and the pastRegionButton
        # are the only ways to initialize an element in the region_settings_list.

        x_pos = self.mm_hardware_commands.get_x_position()
        y_pos = self.mm_hardware_commands.get_y_position()
        z_pos = self.mm_hardware_commands.get_z_position()

        self.region_settings.x_position = x_pos
        self.region_settings.y_position = y_pos
        self.region_settings.z_position = z_pos
        self.acquisition_settings.update_region_settings_list(self.region_settings, self.sample_num, self.region_num)

        self.cls_dialog.next_region_button.setEnabled(True)
        self.cls_dialog.next_sample_button.setEnabled(True)
        self.cls_dialog.remove_region_button.setEnabled(True)
        self.cls_dialog.go_to_button.setEnabled(True)

        self.set_table()
        self.update_cls_dialog()
        self.write_to_config()

    def previous_region_button_clicked(self):
        self.region_num -= 1

        self.region_settings = self.acquisition_settings.region_settings_list[self.sample_num][self.region_num]

        if self.region_num == 0:
            self.cls_dialog.previous_region_button.setEnabled(False)

        self.cls_dialog.remove_region_button.setEnabled(True)
        self.cls_dialog.next_region_button.setEnabled(True)
        self.cls_dialog.go_to_button.setEnabled(True)

        self.update_cls_dialog()

    def next_region_button_clicked(self):
        self.region_num += 1

        region = self.acquisition_settings.region_settings_list[self.sample_num][self.region_num]

        # Worth noting that the region_settings list is initialized as a 2D list
        # with all elements equal to 0. Thus, this region != 0 statement is just
        # to check if the index has been initialized with a region_settings object.
        if region != 0:
            self.region_settings = region
            self.cls_dialog.go_to_button.setEnabled(True)
        else:
            self.region_settings = CLSAcquisitionParameters.RegionSettings()
            self.cls_dialog.next_region_button.setEnabled(False)
            self.cls_dialog.remove_region_button.setEnabled(False)
            self.cls_dialog.go_to_button.setEnabled(False)

        self.cls_dialog.previous_region_button.setEnabled(True)

        self.update_cls_dialog()

    def previous_sample_button_clicked(self):
        self.sample_num -= 1
        self.region_num = 0

        self.region_settings = self.acquisition_settings.region_settings_list[self.sample_num][self.region_num]

        if self.sample_num == 0:
            self.cls_dialog.previous_sample_button.setEnabled(False)

        self.cls_dialog.previous_region_button.setEnabled(False)
        self.cls_dialog.next_region_button.setEnabled(True)
        self.cls_dialog.next_sample_button.setEnabled(True)
        self.cls_dialog.remove_region_button.setEnabled(True)
        self.cls_dialog.go_to_button.setEnabled(True)

        self.update_cls_dialog()

    def next_sample_button_clicked(self):
        self.sample_num += 1
        self.region_num = 0

        region = self.acquisition_settings.region_settings_list[self.sample_num][self.region_num]
        if region != 0:
            self.region_settings = region
            self.cls_dialog.go_to_button.setEnabled(True)
            if self.acquisition_settings.region_settings_list[self.sample_num][self.region_num + 1] != 0:
                self.cls_dialog.next_region_button.setEnabled(True)
        else:
            self.region_settings = CLSAcquisitionParameters.RegionSettings()
            self.cls_dialog.next_region_button.setEnabled(False)
            self.cls_dialog.remove_region_button.setEnabled(False)
            self.cls_dialog.next_sample_button.setEnabled(False)
            self.cls_dialog.go_to_button.setEnabled(False)

        self.cls_dialog.previous_region_button.setEnabled(False)
        self.cls_dialog.previous_sample_button.setEnabled(True)

        self.update_cls_dialog()

    def remove_region_button_clicked(self):
        # Removes current region from region_settings_list. See remove_region_settings() 
        # in AcquisitionSettings class for more details.

        self.acquisition_settings.remove_region_settings(self.sample_num, self.region_num)
        if self.acquisition_settings.region_settings_list[self.sample_num][self.region_num] != 0:
            self.region_settings = self.acquisition_settings.region_settings_list[self.sample_num][self.region_num]
            self.cls_dialog.go_to_button.setEnabled(True)
        else:
            self.region_settings = CLSAcquisitionParameters.RegionSettings()
            self.cls_dialog.next_region_button.setEnabled(False)
            self.cls_dialog.remove_region_button.setEnabled(False)
            self.cls_dialog.go_to_button.setEnabled(False)
            if self.region_num == 0:
                self.cls_dialog.next_sample_button.setEnabled(False)
                self.cls_dialog.previous_region_button.setEnabled(False)
                if self.sample_num == 0:
                    self.cls_dialog.previous_sample_button.setEnabled(False)

        self.set_table()
        self.update_cls_dialog()
        self.write_to_config()

    def copy_button_clicked(self):
        # Creates new object with fields of the same value as region_settings_copy
        self.region_settings_copy = copy.deepcopy(self.region_settings)

    def paste_button_clicked(self):
        # Initializes new region at current index with values from region_settings_copy.
        # Currently the only method other than set_region_button_clicked to initialize
        # region in region_settings_list

        self.region_settings = copy.deepcopy(self.region_settings_copy)
        self.acquisition_settings.update_region_settings_list(self.region_settings, self.sample_num, self.region_num)

        self.cls_dialog.next_region_button.setEnabled(True)
        self.cls_dialog.next_sample_button.setEnabled(True)
        self.cls_dialog.remove_region_button.setEnabled(True)
        self.cls_dialog.go_to_button.setEnabled(True)

        self.set_table()
        self.update_cls_dialog()
        self.write_to_config()

    def set_z_start_button_clicked(self):
        # gets current z stage position and sets it as z_start_position

        z_pos = self.mm_hardware_commands.get_z_position()
        self.region_settings.z_start_position = z_pos
        self.cls_dialog.start_z_line_edit.setText(str(z_pos))

        self.set_table()
        self.write_to_config()

    def set_z_end_button_clicked(self):
        z_pos = self.mm_hardware_commands.get_z_position()
        self.region_settings.z_end_position = z_pos
        self.cls_dialog.end_z_line_edit.setText(str(z_pos))

        self.set_table()
        self.write_to_config()

    def acquisition_setup_button_clicked(self):
        self.acquisition_settings_dialog.show()
        self.acquisition_settings_dialog.activateWindow()

    def z_stack_check_clicked(self):
        # Enables/disables zStack GUI elements when checkbox is clicked.
        # Also sets z_stack_boolean in region_settings.

        z_stack_boolean = self.cls_dialog.z_stack_check_box.isChecked()
        self.region_settings.z_stack_boolean = z_stack_boolean
        self.cls_dialog.z_stack_check_box.setChecked(z_stack_boolean)
        self.cls_dialog.set_z_start_button.setEnabled(z_stack_boolean)
        self.cls_dialog.set_z_end_button.setEnabled(z_stack_boolean)
        self.cls_dialog.start_z_line_edit.setEnabled(z_stack_boolean)
        self.cls_dialog.end_z_line_edit.setEnabled(z_stack_boolean)
        self.cls_dialog.step_size_line_edit.setEnabled(z_stack_boolean)
        self.cls_dialog.z_stack_available_list_view.setEnabled(z_stack_boolean)
        self.cls_dialog.z_stack_used_list_view.setEnabled(z_stack_boolean)

        self.set_table()
        self.write_to_config()

    def snap_check_clicked(self):
        # Same as z_stack_check_clicked but for snap

        snap_boolean = self.cls_dialog.snap_check_box.isChecked()
        self.region_settings.snap_boolean = snap_boolean
        self.cls_dialog.snap_check_box.setChecked(snap_boolean)
        self.cls_dialog.snap_exposure_line_edit.setEnabled(snap_boolean)
        self.cls_dialog.snap_available_list_view.setEnabled(snap_boolean)
        self.cls_dialog.snap_used_list_view.setEnabled(snap_boolean)

        self.set_table()
        self.write_to_config()

    def video_check_clicked(self):
        # Same as z_stack_check_clicked but for video

        video_boolean = self.cls_dialog.video_check_box.isChecked()
        self.region_settings.video_boolean = video_boolean
        self.cls_dialog.video_check_box.setChecked(video_boolean)
        self.cls_dialog.video_duration_line_edit.setEnabled(video_boolean)
        self.cls_dialog.video_exposure_line_edit.setEnabled(video_boolean)
        self.cls_dialog.video_available_list_view.setEnabled(video_boolean)
        self.cls_dialog.video_used_list_view.setEnabled(video_boolean)

        self.set_table()
        self.write_to_config()

    def x_line_edit_event(self):
        # Sets x_position in region_settings
        try:
            self.region_settings.x_position = int(self.cls_dialog.x_line_edit.text())
        except ValueError:
            return 'not a number'

        self.set_table()
        self.write_to_config()

    def y_line_edit_event(self):
        try:
            self.region_settings.y_position = int(self.cls_dialog.y_line_edit.text())
        except ValueError:
            return 'not a number'

        self.set_table()

    def z_line_edit_event(self):
        try:
            self.region_settings.z_position = int(self.cls_dialog.z_line_edit.text())
        except ValueError:
            return 'not a number'

        self.set_table()
        self.write_to_config()

    def start_z_line_edit_event(self):
        try:
            self.region_settings.z_start_position = int(self.cls_dialog.start_z_line_edit.text())
        except ValueError:
            return 'not a number'

        self.set_table()
        self.write_to_config()

    def end_z_line_edit_event(self):
        try:
            self.region_settings.z_end_position = int(self.cls_dialog.end_z_line_edit.text())
        except ValueError:
            return 'not a number'

        self.set_table()
        self.write_to_config()

    def step_size_line_edit_event(self):
        try:
            self.region_settings.step_size = int(self.cls_dialog.step_size_line_edit.text())
        except ValueError:
            return 'not a number'

        self.set_table()
        self.write_to_config()

    def snap_exposure_line_edit_event(self):
        try:
            self.region_settings.snap_exposure_time = int(self.cls_dialog.snap_exposure_line_edit.text())
        except ValueError:
            return 'not a number'

        self.set_table()
        self.write_to_config()

    def video_duration_line_edit_event(self):
        try:
            self.region_settings.video_duration_in_seconds = int(self.cls_dialog.video_duration_line_edit.text())
        except ValueError:
            return 'not a number'

        self.set_table()
        self.write_to_config()

    def video_exposure_line_edit_event(self):
        try:
            self.region_settings.video_exposure_time = int(self.cls_dialog.video_exposure_line_edit.text())
        except ValueError:
            return 'not a number'

        self.set_table()
        self.write_to_config()

    def z_stack_available_list_move(self):
        #on double click, switches channel fro, available list to used list
        channel_index = self.cls_dialog.z_stack_available_list_view.selectedIndexes()[0].row()
        channel = self.z_stack_available_model.item(channel_index).text()
        self.z_stack_available_model.removeRow(channel_index)

        item = QtGui.QStandardItem(channel)
        self.z_stack_used_model.appendRow(item)
        self.region_settings.z_stack_channel_list.append(channel)

        self.set_table()

    def snap_available_list_move(self):
        channel_index = self.cls_dialog.snap_available_list_view.selectedIndexes()[0].row()
        channel = self.snap_available_model.item(channel_index).text()
        self.snap_available_model.removeRow(channel_index)

        item = QtGui.QStandardItem(channel)
        self.snap_used_model.appendRow(item)
        self.region_settings.snap_channel_list.append(channel)

        self.set_table()

    def video_available_list_move(self):
        channel_index = self.cls_dialog.video_available_list_view.selectedIndexes()[0].row()
        channel = self.video_available_model.item(channel_index).text()
        self.video_available_model.removeRow(channel_index)

        item = QtGui.QStandardItem(channel)
        self.video_used_model.appendRow(item)
        self.region_settings.video_channel_list.append(channel)

        self.set_table()

    def z_stack_used_list_move(self):
        channel_index = self.cls_dialog.z_stack_used_list_view.selectedIndexes()[0].row()
        channel = self.z_stack_used_model.item(channel_index).text()
        self.z_stack_used_model.removeRow(channel_index)
        self.region_settings.z_stack_channel_list.remove(channel)

        item = QtGui.QStandardItem(channel)
        self.z_stack_available_model.appendRow(item)

        self.set_table()

    def snap_used_list_move(self):
        channel_index = self.cls_dialog.snap_used_list_view.selectedIndexes()[0].row()
        channel = self.snap_used_model.item(channel_index).text()
        self.snap_used_model.removeRow(channel_index)
        self.region_settings.snap_channel_list.remove(channel)

        item = QtGui.QStandardItem(channel)
        self.snap_available_model.appendRow(item)

        self.set_table()

    def video_used_list_move(self):
        channel_index = self.cls_dialog.video_used_list_view.selectedIndexes()[0].row()
        channel = self.video_used_model.item(channel_index).text()
        self.video_used_model.removeRow(channel_index)
        self.region_settings.video_channel_list.remove(channel)

        item = QtGui.QStandardItem(channel)
        self.video_available_model.appendRow(item)

        self.set_table()

    def browse_button_clicked(self):
        browse = QtDesignerGUI.browseDialog()
        path = str(browse.getExistingDirectory(browse, 'Select Directory', self.start_path))
        self.acquisition_settings_dialog.save_location_line_edit.setText(path)

        if path != '':
            self.start_path = str(Path(path).parent)
            self.acquisition_settings.directory = path
            self.acquisition_settings_dialog.start_acquisition_button.setEnabled(True)

    def channel_move_up_button_clicked(self):
        channel_index = self.acquisition_settings_dialog.channel_order_list_view.selectedIndexes()[0].row()
        if channel_index > 0:
            channel = self.channel_order_model.takeRow(channel_index)
            self.channel_order_model.insertRow(channel_index - 1, channel)
            new_index = self.channel_order_model.indexFromItem(channel[0])
            self.acquisition_settings_dialog.channel_order_list_view.setCurrentIndex(new_index)

            self.acquisition_settings.channel_order_list = []
            for index in range(0, self.channel_order_model.rowCount()):
                item = self.channel_order_model.item(index, 0).text()
                self.acquisition_settings.channel_order_list.append(item)

    def channel_move_down_button_clicked(self):
        channel_index = self.acquisition_settings_dialog.channel_order_list_view.selectedIndexes()[0].row()
        if channel_index < self.channel_order_model.rowCount() - 1:
            channel = self.channel_order_model.takeRow(channel_index)
            self.channel_order_model.insertRow(channel_index + 1, channel)
            new_index = self.channel_order_model.indexFromItem(channel[0])
            self.acquisition_settings_dialog.channel_order_list_view.setCurrentIndex(new_index)

            self.acquisition_settings.channel_order_list = []
            for index in range(0, self.channel_order_model.rowCount()):
                item = self.channel_order_model.item(index, 0).text()
                self.acquisition_settings.channel_order_list.append(item)

    def start_acquisition_button_clicked(self):
        acquisition = Acquisition(self.studio, self.core, self.acquisition_dialog, self.acquisition_settings,
                                  self.mm_hardware_commands, self.spim_commands)
        self.acquisition_settings_dialog.start_acquisition_button.setEnabled(False)
        acquisition.start()

    def time_points_check_clicked(self):
        time_points_boolean = self.acquisition_settings_dialog.time_points_check_box.isChecked()
        self.acquisition_settings.time_points_boolean = time_points_boolean
        self.acquisition_settings_dialog.num_time_points_line_edit.setEnabled(time_points_boolean)
        self.acquisition_settings_dialog.time_points_interval_line_edit.setEnabled(time_points_boolean)
        self.calculate_num_images()

    def lsrm_check_clicked(self):
        self.acquisition_settings.lightsheet_mode_boolean = self.acquisition_settings_dialog.lsrm_check_box.isChecked()

    def stage_speed_combo_box_clicked(self):
        if self.acquisition_settings_dialog.stage_speed_combo_box.currentText() == '30 um/s':
            self.acquisition_settings.z_scan_speed = 0.030

        if self.acquisition_settings_dialog.stage_speed_combo_box.currentText() == '15 um/s':
            self.acquisition_settings.z_scan_speed = 0.015

    def num_time_points_line_edit_event(self):
        try:
            self.acquisition_settings.num_time_points = int(self.acquisition_settings_dialog.num_time_points_line_edit.text())
            self.calculate_num_images()
                
        except ValueError:
            return 'not a number'

    def time_points_interval_line_edit_event(self):
        try:
            self.acquisition_settings.time_points_interval = int(self.acquisition_settings_dialog.time_points_interval_line_edit.text())
        except ValueError:
            return 'not a number'


class SPIMController(object):
    """
    As stated above, this class interacts with the SPIMGalvoDialog GUI and the
    SPIMGalvoCommands class. The SPIMGalvoCommands class sets up the DAQ controlled galvo
    mirrors both for general use in Micro-Manager and for image acquisitions.

    Notes:

    One pattern to note is that the lightsheet_readout() method is called
    before set_lsrm_camera_properties(). This is because the LSRM method calculates the new
    internal line interval (ili) based on the current framerate set, and the camera properties
    uses ili as an argument to correctly initialize LSRM.

    One more thing to note: Currently, continuous LSRM is triggered entirely by the PLC in the
    ASI Tiger Console. The initialize_plc_for_continuous_lsrm() method sets the PLC to constantly
    pulse at a frequency matching the current framerate in spimGalvoCommands. This same pulse
    is then sent to the camera and the NIDAQ as a shared external trigger.

    Future Changes:
    - Changes in combo box/check box could use switch statements instead of if statements. Might be
      useful if more modes are added. Could even use enum.
    - Probably want to combine laser delay and cam delay. Currently, adjusting cam delay misses the
      trigger, which halves the framerate. Need to think more about this.
    - Could change combo box stuff to ENUMs
    """

    def __init__(self, studio: Studio, core: Core, mm_hardware_commands: HardwareCommands.MMHardwareCommands,
                 spim_commands: HardwareCommands.SPIMGalvoCommands):
        self.studio = studio
        self.core = core
        self.spim_dialog = QtDesignerGUI.SPIMGalvoDialog()
        self.spim_dialog.set_dslm_gui()
        self.mm_hardware_commands = mm_hardware_commands
        self.spim_commands = spim_commands
        self.mm_hardware_commands.set_default_camera_properties(self.mm_hardware_commands.default_exposure)
        self.spim_commands.continuous_scan_not_scanning()

        # sets step sizes for spimGalvo buttons and min/max values to prevent
        # setting voltage too high. Could be changed, as a 2 volt max in either
        # direction is probably a bit low. Could be changed to +-3 or 4.
        self.small_step = 0.01
        self.big_step = 0.1
        self.delay_step = .01

        self.galvo_min = -4.0
        self.galvo_max = 4.0
        self.width_min = 0.
        self.width_max = 2 * self.galvo_max
        self.framerate_min = 1
        self.framerate_max = 40
        self.delay_min = 0
        self.delay_max = 2
        self.num_lines_max = 80

        # Initialize event handlers and validators
        self.spim_dialog.offset_line_edit.textEdited.connect(self.offset_line_edit_event)
        validator = QtGui.QDoubleValidator()
        validator.setRange(self.galvo_min, self.galvo_max, 3)
        self.spim_dialog.offset_line_edit.setValidator(validator)

        self.spim_dialog.width_line_edit.textEdited.connect(self.width_line_edit_event)
        validator = QtGui.QDoubleValidator()
        validator.setRange(self.width_min, self.width_min, 3)
        self.spim_dialog.width_line_edit.setValidator(validator)

        self.spim_dialog.focus_line_edit.textEdited.connect(self.focus_line_edit_event)
        validator = QtGui.QDoubleValidator()
        validator.setRange(self.galvo_min, self.galvo_max, 3)
        self.spim_dialog.focus_line_edit.setValidator(validator)

        self.spim_dialog.lsrm_lower_line_edit.textEdited.connect(self.lsrm_lower_line_edit_event)
        validator = QtGui.QDoubleValidator()
        validator.setRange(self.galvo_min, 0, 3)
        self.spim_dialog.lsrm_lower_line_edit.setValidator(validator)

        self.spim_dialog.lsrm_upper_line_edit.textEdited.connect(self.lsrm_upper_line_edit_event)
        validator = QtGui.QDoubleValidator()
        validator.setRange(0, self.galvo_max, 3)
        self.spim_dialog.lsrm_upper_line_edit.setValidator(validator)

        self.spim_dialog.laser_delay_line_edit.textEdited.connect(self.laser_delay_line_edit_event)
        validator = QtGui.QIntValidator()
        validator.setRange(self.delay_min, self.delay_max)
        self.spim_dialog.laser_delay_line_edit.setValidator(validator)

        self.spim_dialog.num_lines_line_edit.textEdited.connect(self.num_lines_line_edit_event)
        validator = QtGui.QIntValidator()
        validator.setRange(0, self.num_lines_max)
        self.spim_dialog.num_lines_line_edit.setValidator(validator)

        self.spim_dialog.offset_big_neg_button.clicked.connect(self.offset_big_neg_button_clicked)
        self.spim_dialog.offset_small_neg_button.clicked.connect(self.offset_small_neg_button_clicked)
        self.spim_dialog.offset_small_pos_button.clicked.connect(self.offset_small_pos_button_clicked)
        self.spim_dialog.offset_big_pos_button.clicked.connect(self.offset_big_pos_button_clicked)
        self.spim_dialog.focus_big_neg_button.clicked.connect(self.focus_big_neg_button_clicked)
        self.spim_dialog.focus_small_neg_button.clicked.connect(self.focus_small_neg_button_clicked)
        self.spim_dialog.focus_small_pos_button.clicked.connect(self.focus_small_pos_button_clicked)
        self.spim_dialog.focus_big_pos_button.clicked.connect(self.focus_big_pos_button_clicked)
        self.spim_dialog.width_big_neg_button.clicked.connect(self.width_big_neg_button_clicked)
        self.spim_dialog.width_small_neg_button.clicked.connect(self.width_small_neg_button_clicked)
        self.spim_dialog.width_small_pos_button.clicked.connect(self.width_small_pos_button_clicked)
        self.spim_dialog.width_big_pos_button.clicked.connect(self.width_big_pos_button_clicked)
        self.spim_dialog.lsrm_set_lower_button.clicked.connect(self.set_lower_limit_button_clicked)
        self.spim_dialog.lsrm_set_upper_button.clicked.connect(self.set_upper_limit_button_clicked)
        self.spim_dialog.framerate_neg_button.clicked.connect(self.framerate_neg_button_clicked)
        self.spim_dialog.framerate_pos_button.clicked.connect(self.framerate_pos_button_clicked)
        self.spim_dialog.cam_delay_neg_button.clicked.connect(self.cam_delay_neg_button_clicked)
        self.spim_dialog.cam_delay_pos_button.clicked.connect(self.cam_delay_pos_button_clicked)
        self.spim_dialog.laser_delay_neg_button.clicked.connect(self.laser_delay_neg_button_clicked)
        self.spim_dialog.laser_delay_pos_button.clicked.connect(self.laser_delay_pos_button_clicked)
        self.spim_dialog.scanning_mode_combo_box.activated.connect(self.scanning_mode_combo_box_clicked)
        self.spim_dialog.scanning_check_box.stateChanged.connect(self.scanning_check_box_stage_changed)

        self.initialize_from_config()

    def write_to_config(self):
        config = MainController.config
        section = MainController.spim_galvo_section
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, 'focus', self.spim_commands.focus)
        config.set(section, 'cont_offset', self.spim_commands.continuous_scan_offset)
        config.set(section, 'width', self.spim_commands.continuous_scan_width)
        config.set(section, 'lsrm_pos', self.spim_commands.ligthsheet_readout_current_position)
        config.set(section, 'lsrm_upper', self.spim_commands.lightsheet_readout_upper)
        config.set(section, 'lsrm_lower', self.spim_commands.lightsheet_readout_lower)
        config.set(section, 'framerate', self.spim_commands.lightsheet_readout_framerate)
        config.set(section, 'laser_delay', self.spim_commands.lightsheet_readout_laser_delay)
        config.set(section, 'cam_delay', self.spim_commands.lightsheet_readout_cam_delay)
        config.set(section, 'num_lines', self.mm_hardware_commands.lsrm_num_lines)

        with open(MainController.config_file_name, 'w') as configfile:
            config.write(configfile)

    def initialize_from_config(self):
        config = MainController.config
        section = MainController.spim_galvo_section

        if config.has_section(section):
            try:
                section = 'SPIM Galvo Settings'
                self.spim_commands.focus = config.getfloat(section, 'focus')
                self.spim_commands.continuous_scan_offset = config.getfloat(section, 'cont_offset')
                self.spim_commands.continuous_scan_width = config.getfloat(section, 'width')
                self.spim_commands.ligthsheet_readout_current_position = config.getfloat(section, 'lsrm_pos')
                self.spim_commands.lightsheet_readout_upper = config.getfloat(section, 'lsrm_upper')
                self.spim_commands.lightsheet_readout_lower = config.getfloat(section, 'lsrm_lower')
                self.spim_commands.lightsheet_readout_framerate = config.getfloat(section, 'framerate')
                self.spim_commands.lightsheet_readout_laser_delay = config.getfloat(section, 'laser_delay')
                self.spim_commands.lightsheet_readout_cam_delay = config.getfloat(section, 'cam_delay')
                self.mm_hardware_commands.lsrm_num_lines = config.getint(section, 'num_lines')
            except:
                print('section line missing')

        #initialize line edits from config file
        self.spim_dialog.offset_line_edit.setText("%.3f" % self.spim_commands.continuous_scan_offset)
        self.spim_dialog.width_line_edit.setText("%.3f" % self.spim_commands.continuous_scan_width)
        self.spim_dialog.focus_line_edit.setText("%.3f" % self.spim_commands.focus)
        self.spim_dialog.lsrm_lower_line_edit.setText("%.3f" % self.spim_commands.lightsheet_readout_lower)
        self.spim_dialog.lsrm_upper_line_edit.setText("%.3f" % self.spim_commands.lightsheet_readout_upper)
        self.spim_dialog.framerate_line_edit.setText("%.0f" % self.spim_commands.lightsheet_readout_framerate)
        self.spim_dialog.cam_delay_line_edit.setText("%.3f" % self.spim_commands.lightsheet_readout_cam_delay)
        self.spim_dialog.laser_delay_line_edit.setText("%.3f" % self.spim_commands.lightsheet_readout_laser_delay)
        self.spim_dialog.num_lines_line_edit.setText("%.0f" % self.mm_hardware_commands.lsrm_num_lines)

    def set_scanning_mode(self):
        # Sets current scanning mode. More modes could be added if more modes
        # are developed.

        if self.spim_dialog.scanning_check_box.isChecked():
            if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Lightsheet Readout Mode':
                self.spim_commands.lightsheet_readout()

            if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Normal DLSM':
                self.spim_commands.continuous_scan()
        else:
            if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Lightsheet Readout Mode':
                self.spim_commands.lightsheet_readout_not_scanning()
                
            if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Normal DLSM':
                self.spim_commands.continuous_scan_not_scanning()

    def scanning_mode_combo_box_clicked(self):
        # If scanning mode is changed, camera properties must be changed as well,
        # since LSRM requires special properties.

        self.set_scanning_mode()

        if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Lightsheet Readout Mode':
            if self.spim_dialog.scanning_check_box.isChecked():
                self.mm_hardware_commands.initialize_plc_for_continuous_lsrm(self.spim_commands.lightsheet_readout_framerate)
                self.mm_hardware_commands.set_lsrm_camera_properties(self.spim_commands.lightsheet_readout_ili)

            self.spim_dialog.set_lsrm_gui()
            self.spim_dialog.offset_line_edit.setText("%.3f" % self.spim_commands.ligthsheet_readout_current_position)

        if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Normal DLSM':
            #if box isn't checked, camera properties don't have to change because it will already
            #be in the correct default mode.
            if self.spim_dialog.scanning_check_box.isChecked():
                self.mm_hardware_commands.set_default_camera_properties(self.mm_hardware_commands.default_exposure)

            self.spim_dialog.set_dslm_gui()
            self.spim_dialog.offset_line_edit.setText("%.3f" % self.spim_commands.continuous_scan_offset)

        self.studio.live().set_live_mode_on(True)

    def scanning_check_box_stage_changed(self):
        self.set_scanning_mode()
        if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Lightsheet Readout Mode':
            if self.spim_dialog.scanning_check_box.isChecked():
                self.mm_hardware_commands.initialize_plc_for_continuous_lsrm(self.spim_commands.lightsheet_readout_framerate)
                self.mm_hardware_commands.set_lsrm_camera_properties(self.spim_commands.lightsheet_readout_ili)
            else:
                self.mm_hardware_commands.set_default_camera_properties(self.mm_hardware_commands.default_exposure)

        self.studio.live().set_live_mode_on(True)

    def offset_big_neg_button_clicked(self):
        #Since offset line edit acts as both offset for continuous_scan and
        #current position for lsrm, some extra logic is needed to ensure it's
        #changing the correct attributes.

        offset = 0

        if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Lightsheet Readout Mode':
            offset = self.spim_commands.ligthsheet_readout_current_position
            offset = max(offset - self.big_step, self.galvo_min)
            self.spim_commands.ligthsheet_readout_current_position = offset

        if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Normal DLSM':
            offset = self.spim_commands.continuous_scan_offset
            offset = max(offset - self.big_step, self.galvo_min)
            self.spim_commands.continuous_scan_offset = offset

        self.spim_dialog.offset_line_edit.setText("%.3f" % offset)

        self.set_scanning_mode()
        self.write_to_config()

    def offset_small_neg_button_clicked(self):
        offset = 0

        if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Lightsheet Readout Mode':
            offset = self.spim_commands.ligthsheet_readout_current_position
            offset = max(offset - self.small_step, self.galvo_min)
            self.spim_commands.ligthsheet_readout_current_position = offset

        if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Normal DLSM':
            offset = self.spim_commands.continuous_scan_offset
            offset = max(offset - self.small_step, self.galvo_min)
            self.spim_commands.continuous_scan_offset = offset

        self.spim_dialog.offset_line_edit.setText("%.3f" % offset)

        self.set_scanning_mode()
        self.write_to_config()

    def offset_small_pos_button_clicked(self):
        offset = 0

        if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Lightsheet Readout Mode':
            offset = self.spim_commands.ligthsheet_readout_current_position
            offset = min(offset + self.small_step, self.galvo_max)
            self.spim_commands.ligthsheet_readout_current_position = offset

        if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Normal DLSM':
            offset = self.spim_commands.continuous_scan_offset
            offset = min(offset + self.small_step, self.galvo_max)
            self.spim_commands.continuous_scan_offset = offset

        self.spim_dialog.offset_line_edit.setText("%.3f" % offset)

        self.set_scanning_mode()
        self.write_to_config()

    def offset_big_pos_button_clicked(self):
        offset = 0

        if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Lightsheet Readout Mode':
            offset = self.spim_commands.ligthsheet_readout_current_position
            offset = min(offset + self.big_step, self.galvo_max)
            self.spim_commands.ligthsheet_readout_current_position = offset

        if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Normal DLSM':
            offset = self.spim_commands.continuous_scan_offset
            offset = min(offset + self.big_step, self.galvo_max)
            self.spim_commands.continuous_scan_offset = offset

        self.spim_dialog.offset_line_edit.setText("%.3f" % offset)

        self.set_scanning_mode()
        self.write_to_config()

    def focus_big_neg_button_clicked(self):
        focus = self.spim_commands.focus
        focus = max(focus - self.big_step, self.galvo_min)

        self.spim_commands.focus = focus
        self.spim_dialog.focus_line_edit.setText("%.3f" % focus)

        self.set_scanning_mode()
        self.write_to_config()

    def focus_small_neg_button_clicked(self):
        focus = self.spim_commands.focus
        focus = max(focus - self.small_step, self.galvo_min)

        self.spim_commands.focus = focus
        self.spim_dialog.focus_line_edit.setText("%.3f" % focus)

        self.set_scanning_mode()
        self.write_to_config()

    def focus_small_pos_button_clicked(self):
        focus = self.spim_commands.focus
        focus = min(focus + self.small_step, self.galvo_max)

        self.spim_commands.focus = focus
        self.spim_dialog.focus_line_edit.setText("%.3f" % focus)

        self.set_scanning_mode()
        self.write_to_config()

    def focus_big_pos_button_clicked(self):
        focus = self.spim_commands.focus
        focus = min(focus + self.big_step, self.galvo_max)

        self.spim_commands.focus = focus
        self.spim_dialog.focus_line_edit.setText("%.3f" % focus)

        self.set_scanning_mode()
        self.write_to_config()

    def width_big_neg_button_clicked(self):
        width = self.spim_commands.continuous_scan_width
        width = max(width - self.big_step, self.width_min)

        self.spim_commands.continuous_scan_width = width
        self.spim_dialog.width_line_edit.setText("%.3f" % width)

        self.set_scanning_mode()
        self.write_to_config()

    def width_small_neg_button_clicked(self):
        width = self.spim_commands.continuous_scan_width
        width = max(width - self.small_step, self.width_min)

        self.spim_commands.continuous_scan_width = width
        self.spim_dialog.width_line_edit.setText("%.3f" % width)

        self.set_scanning_mode()
        self.write_to_config()

    def width_small_pos_button_clicked(self):
        width = self.spim_commands.continuous_scan_width
        width = min(width + self.small_step, self.width_max)

        self.spim_commands.continuous_scan_width = width
        self.spim_dialog.width_line_edit.setText("%.3f" % width)

        self.set_scanning_mode()
        self.write_to_config()

    def width_big_pos_button_clicked(self):
        width = self.spim_commands.continuous_scan_width
        width = min(width + self.big_step, self.width_max)

        self.spim_commands.continuous_scan_width = width
        self.spim_dialog.width_line_edit.setText("%.3f" % width)

        self.set_scanning_mode()
        self.write_to_config()

    def set_lower_limit_button_clicked(self):
        current_position = float(self.spim_commands.ligthsheet_readout_current_position)
        if current_position <= 0:
            self.spim_commands.lightsheet_readout_lower = current_position
            self.spim_dialog.lsrm_lower_line_edit.setText("%.3f" % current_position)

        self.set_scanning_mode()
        self.write_to_config()

    def set_upper_limit_button_clicked(self):
        current_position = float(self.spim_commands.ligthsheet_readout_current_position)
        if current_position >= 0:
            self.spim_commands.lightsheet_readout_upper = current_position
            self.spim_dialog.lsrm_upper_line_edit.setText("%.3f" % current_position)

        self.set_scanning_mode()
        self.write_to_config()

    def framerate_neg_button_clicked(self):
        #framerate change changes ili, and so both plc and camera must also be updated
        framerate = self.spim_commands.lightsheet_readout_framerate
        framerate = max(framerate - 1, self.framerate_min)

        self.spim_commands.lightsheet_readout_framerate = framerate
        self.spim_dialog.framerate_line_edit.setText("%.0f" % framerate)

        self.set_scanning_mode()

        self.mm_hardware_commands.initialize_plc_for_continuous_lsrm(self.spim_commands.lightsheet_readout_framerate)
        self.mm_hardware_commands.set_lsrm_camera_properties(self.spim_commands.lightsheet_readout_ili)
        self.studio.live().set_live_mode_on(True)

        self.write_to_config()

    def framerate_pos_button_clicked(self):
        framerate = self.spim_commands.lightsheet_readout_framerate
        framerate = min(framerate + 1, self.framerate_max)

        self.spim_commands.lightsheet_readout_framerate = framerate
        self.spim_dialog.framerate_line_edit.setText("%.0f" % framerate)

        self.set_scanning_mode()
        self.mm_hardware_commands.initialize_plc_for_continuous_lsrm(self.spim_commands.lightsheet_readout_framerate)
        self.mm_hardware_commands.set_lsrm_camera_properties(self.spim_commands.lightsheet_readout_ili)
        self.studio.live().set_live_mode_on(True)

        self.write_to_config()

    def cam_delay_neg_button_clicked(self):     
        cam_delay = self.spim_commands.lightsheet_readout_cam_delay
        cam_delay = max(cam_delay - self.delay_step, self.delay_min)

        self.spim_commands.lightsheet_readout_cam_delay = cam_delay
        self.spim_dialog.cam_delay_line_edit.setText("%.3f" % cam_delay)

        self.set_scanning_mode()
        self.write_to_config()

    def cam_delay_pos_button_clicked(self):
        cam_delay = self.spim_commands.lightsheet_readout_cam_delay
        cam_delay = min(cam_delay + self.delay_step, self.delay_max)

        self.spim_commands.lightsheet_readout_cam_delay = cam_delay
        self.spim_dialog.cam_delay_line_edit.setText("%.3f" % cam_delay)

        self.set_scanning_mode()
        self.write_to_config()

    def laser_delay_neg_button_clicked(self):
        laser_delay = self.spim_commands.lightsheet_readout_laser_delay
        laser_delay = max(laser_delay - self.delay_step, self.delay_min)

        self.spim_commands.lightsheet_readout_laser_delay = laser_delay
        self.spim_dialog.laser_delay_line_edit.setText("%.3f" % laser_delay)

        self.set_scanning_mode()
        self.write_to_config()

    def laser_delay_pos_button_clicked(self):
        laser_delay = self.spim_commands.lightsheet_readout_laser_delay
        laser_delay = min(laser_delay + self.delay_step, self.delay_max)

        self.spim_commands.lightsheet_readout_laser_delay = laser_delay
        self.spim_dialog.laser_delay_line_edit.setText("%.3f" % laser_delay)

        self.set_scanning_mode()
        self.write_to_config()

    def offset_line_edit_event(self):
        offset = self.spim_dialog.offset_line_edit.text()
        try:
            if float(offset) <= self.galvo_min:
                offset = self.galvo_min
                self.spim_dialog.offset_line_edit.setText("%.3f" % offset)
            if float(offset) >= self.galvo_max:
                offset = self.galvo_max
                self.spim_dialog.offset_line_edit.setText("%.3f" % offset)

            if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Lightsheet Readout Mode':
                self.spim_commands.ligthsheet_readout_current_position = float(offset)
            if self.spim_dialog.scanning_mode_combo_box.currentText() == 'Normal DLSM':
                self.spim_commands.continuous_scan_offset = float(offset)

        except ValueError:
            return 'not a number'

        self.set_scanning_mode()
        self.write_to_config()

    def width_line_edit_event(self):
        width = self.spim_dialog.width_line_edit.text()
        try:
            if float(width) <= self.width_min:
                width = self.width_min
                self.spim_dialog.width_line_edit.setText("%.3f" % width)
            if float(width) >= self.width_max:
                width = self.width_max
                self.spim_dialog.width_line_edit.setText("%.3f" % width)
            self.spim_commands.continuous_scan_width = float(width)

        except ValueError:
            return 'not a number'

        self.set_scanning_mode()
        self.write_to_config()

    def focus_line_edit_event(self):
        focus = self.spim_dialog.focus_line_edit.text()
        try:
            if float(focus) <= self.galvo_min:
                focus = self.galvo_min
                self.spim_dialog.focus_line_edit.setText("%.3f" % focus)
            if float(focus) >= self.galvo_max:
                focus = self.galvo_max
                self.spim_dialog.focus_line_edit.setText("%.3f" % focus)

            self.spim_commands.focus = float(focus)

        except ValueError:
            return 'not a number'

        self.set_scanning_mode()
        self.write_to_config()

    def lsrm_lower_line_edit_event(self):
        lsrm_lower = self.spim_dialog.lsrm_lower_line_edit.text()
        try:
            if float(lsrm_lower) <= self.galvo_min:
                lsrm_lower = self.galvo_min
                self.spim_dialog.lsrm_lower_line_edit.setText("%.3f" % lsrm_lower)
            if float(lsrm_lower) >= 0:
                lsrm_lower = 0
                self.spim_dialog.lsrm_lower_line_edit.setText("%.3f" % lsrm_lower)

            self.spim_commands.lightsheet_readout_lower = float(lsrm_lower)

        except ValueError:
            return 'not a number'

        self.set_scanning_mode()
        self.write_to_config()

    def lsrm_upper_line_edit_event(self):
        lsrm_upper = self.spim_dialog.lsrm_upper_line_edit.text()
        try:
            if float(lsrm_upper) <= 0:
                lsrm_upper = 0
                self.spim_dialog.lsrm_upper_line_edit.setText("%.3f" % lsrm_upper)
            if float(lsrm_upper) >= self.galvo_max:
                lsrm_upper = self.galvo_max
                self.spim_dialog.lsrm_upper_line_edit.setText("%.3f" % lsrm_upper)

            self.spim_commands.lightsheet_readout_upper = float(lsrm_upper)

        except ValueError:
            return 'not a number'

        self.set_scanning_mode()
        self.write_to_config()

    def laser_delay_line_edit_event(self):
        laser_delay = self.spim_dialog.laser_delay_line_edit.text()
        try:
            if int(laser_delay) <= self.delay_min:
                laser_delay = self.delay_min
                self.spim_dialog.laser_delay_line_edit.setText("%.0f" % laser_delay)
            if int(laser_delay) >= self.delay_max:
                laser_delay = self.delay_max
                self.spim_dialog.laser_delay_line_edit.setText("%.0f" % laser_delay)

            self.spim_commands.lightsheet_readout_laser_delay = int(laser_delay)

        except ValueError:
            return 'not a number'

        self.set_scanning_mode()
        self.write_to_config()

    def num_lines_line_edit_event(self):
        num_lines = self.spim_dialog.num_lines_line_edit.text()
        try:
            if int(num_lines) <= 0:
                num_lines = 0
                self.spim_dialog.num_lines_line_edit.setText("%.0f" % num_lines)
            if int(num_lines) >= self.num_lines_max:
                num_lines = self.num_lines_max
                self.spim_dialog.num_lines_line_edit.setText("%.0f" % num_lines)

            self.mm_hardware_commands.lsrm_num_lines = int(num_lines)
            self.mm_hardware_commands.set_lsrm_camera_properties(self.spim_commands.lightsheet_readout_ili)
            self.studio.live().set_live_mode_on(True)

        except ValueError:
            return 'not a number'

        self.write_to_config()
