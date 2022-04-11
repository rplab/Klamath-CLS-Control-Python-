'''HardwareCommands

This file contains classes with methods that interact directly with the hardware of the microscope, 
as well as some properties for said devices. There are two classes:

-MMHardwareCommands: Interacts with all hardware devices connected through Micro-Manager
-SPIMGalvoCommands: Interacts with the NIDAQ to control galvo mirrors and triggering of LSRM

Future changes:
- Perhaps put all properties into separate classes? Reason to do this would be to make commands 
more generically usable. Could be useful in future development of imaging techniques.


'''


import numpy as np
import PyDAQmx as pydaq
import numpy as np
from pycromanager import Studio, Core

class MMHardwareCommands(object):
    def __init__(self, studio: Studio, core: Core):
        self.studio = studio
        self.core = core

        #PLC property names and properties
        self.plc_name = "PLogic:E:36"
        self.prop_position = "PointerPosition"
        self.prop_cell_type = "EditCellCellType"
        self.prop_cell_config = "EditCellConfig"
        self.prop_cell_input_1 = "EditCellInput1"
        self.prop_cell_input_2 = "EditCellInput2"
        self.val_constant = "0 - constant"
        self.val_output = "2 - output (push-pull)"
        self.val_and = "5 - 2-input AND"
        self.val_or = "6 - 2-input OR"
        self.val_one_shot = "8 - one shot"
        self.val_delay = "9 - delay"
        self.addr_clk = 192
        self.addr_bnc_1 = 33
        self.addr_bnc_2 = 34
        self.addr_stage_ttl = 46
        self.addr_delay_1 = 1
        self.addr_or = 2
        self.addr_and = 3
        self.addr_delay_2 = 4
        self.addr_one_shot = 5
        self.addr_constant = 6
        
        #Camera property names
        self.sensor_mode_prop = "SENSOR MODE"
        self.trigger_polarity_prop = "TriggerPolarity"
        self.trigger_delay_units_prop = 'OUTPUT TRIGGER DELAY UNITS'
        self.trigger_delay_prop = 'TRIGGER DELAY'
        self.trigger_source_prop = "TRIGGER SOURCE"
        self.trigger_active_prop = "TRIGGER ACTIVE"
        self.ili_prop = "INTERNAL LINE INTERVAL"
        
        #Camera properties
        self.cam_name = self.core.get_camera_device()
        self.default_sensor_mode = "AREA"
        self.lsrm_sensor_mode = "PROGRESSIVE"
        self.default_trigger_polarity = "NEGATIVE"
        self.scan_trigger_polarity= "POSITIVE"
        self.trigger_delay_units = 'MILLISECONDS'
        self.default_cam_delay = 0
        self.lsrm_cam_delay = 0
        self.default_trigger_source = "INTERNAL"
        self.scan_trigger_source = "EXTERNAL"
        self.default_trigger_active = "EDGE"
        self.dslm_trigger_active = "SYNCREADOUT"
        self.default_exposure = 20
        self.dslm_exposure = 20
        self.lsrm_exposure = 0
        self.lsrm_num_lines = 30
        
        #Stage property names
        self.z_speed_property = "MotorSpeed-S(mm/s)"
        self.x_speed_property = "MotorSpeedX-S(mm/s)"
        self.y_speed_property = "MotorSpeedY-S(mm/s)"
        self.tiger = "TigerCommHub"
        self.serial = "SerialCommand"
        
        #Stage Properties
        self.xy_stage_name = self.core.get_xy_stage_device()
        self.z_stage_name = self.core.get_focus_device()
        self.scan_properties = "2 SCAN Y=0 Z=0 F=0"
        self.scan_start_command = "2 SCAN"
        self.x_stage_speed = 1.0
        self.y_stage_speed = 1.0
        self.z_move_speed = 0.5
        self.z_scan_speed = 0.030
    
    def set_property(self, device, prop, value):
        self.core.set_property(device, prop, value)

    def initialize_plc_for_scan(self, step_size):
        trigger_pulse_width = self.dslm_exposure * 4
        frame_interval = np.round((step_size / self.z_scan_speed) * 4)
        
        self.set_property(self.plc_name, self.prop_position, self.addr_delay_1)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_delay)
        self.set_property(self.plc_name, self.prop_cell_config, 0)
        self.set_property(self.plc_name, self.prop_cell_input_1, self.addr_stage_ttl)
        self.set_property(self.plc_name, self.prop_cell_input_2, self.addr_clk)

        self.set_property(self.plc_name, self.prop_position, self.addr_or)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_or)
        self.set_property(self.plc_name, self.prop_cell_config, 0)
        self.set_property(self.plc_name, self.prop_cell_input_1, self.addr_delay_1)
        self.set_property(self.plc_name, self.prop_cell_input_2, self.addr_delay_2)

        self.set_property(self.plc_name, self.prop_position, self.addr_and)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_and)
        self.set_property(self.plc_name, self.prop_cell_config, 0)
        self.set_property(self.plc_name, self.prop_cell_input_1, self.addr_or)
        self.set_property(self.plc_name, self.prop_cell_input_2, self.addr_stage_ttl)

        self.set_property(self.plc_name, self.prop_position, self.addr_delay_2)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_delay)
        self.set_property(self.plc_name, self.prop_cell_config, frame_interval)
        self.set_property(self.plc_name, self.prop_cell_input_1, self.addr_and)
        self.set_property(self.plc_name, self.prop_cell_input_2, self.addr_clk)

        self.set_property(self.plc_name, self.prop_position, self.addr_one_shot)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_one_shot)
        self.set_property(self.plc_name, self.prop_cell_config, trigger_pulse_width)
        self.set_property(self.plc_name, self.prop_cell_input_1, self.addr_delay_2)
        self.set_property(self.plc_name, self.prop_cell_input_2, self.addr_clk)

        self.set_property(self.plc_name, self.prop_position, self.addr_bnc_1)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_output)
        self.set_property(self.plc_name, self.prop_cell_config, self.addr_one_shot)
        self.set_property(self.plc_name, self.prop_cell_input_1, 0)
        self.set_property(self.plc_name, self.prop_cell_input_2, 0)

        self.set_property(self.plc_name, self.prop_position, self.addr_bnc_2)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_output)
        self.set_property(self.plc_name, self.prop_cell_config, self.addr_one_shot)
        self.set_property(self.plc_name, self.prop_cell_input_1, 0)
        self.set_property(self.plc_name, self.prop_cell_input_2, 0)

    def initialize_plc_for_continuous_lsrm(self, framerate):
        trigger_pulse_width = 20
        frame_interval = round((1.0 / framerate)*1000 * 4)

        self.set_property(self.plc_name, self.prop_position, self.addr_delay_1)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_delay)
        self.set_property(self.plc_name, self.prop_cell_config, 0)
        self.set_property(self.plc_name, self.prop_cell_input_1, self.addr_constant)
        self.set_property(self.plc_name, self.prop_cell_input_2, self.addr_clk)

        self.set_property(self.plc_name, self.prop_position, self.addr_or)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_or)
        self.set_property(self.plc_name, self.prop_cell_config, 0)
        self.set_property(self.plc_name, self.prop_cell_input_1, self.addr_delay_1)
        self.set_property(self.plc_name, self.prop_cell_input_2, self.addr_delay_2)

        self.set_property(self.plc_name, self.prop_position, self.addr_and)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_and)
        self.set_property(self.plc_name, self.prop_cell_config, 0)
        self.set_property(self.plc_name, self.prop_cell_input_1, self.addr_or)
        self.set_property(self.plc_name, self.prop_cell_input_2, self.addr_constant)

        self.set_property(self.plc_name, self.prop_position, self.addr_delay_2)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_delay)
        self.set_property(self.plc_name, self.prop_cell_config, frame_interval)
        self.set_property(self.plc_name, self.prop_cell_input_1, self.addr_and)
        self.set_property(self.plc_name, self.prop_cell_input_2, self.addr_clk)

        self.set_property(self.plc_name, self.prop_position, self.addr_one_shot)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_one_shot)
        self.set_property(self.plc_name, self.prop_cell_config, trigger_pulse_width)
        self.set_property(self.plc_name, self.prop_cell_input_1, self.addr_delay_2)
        self.set_property(self.plc_name, self.prop_cell_input_2, self.addr_clk)

        self.set_property(self.plc_name, self.prop_position, self.addr_bnc_1)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_output)
        self.set_property(self.plc_name, self.prop_cell_config, self.addr_one_shot)
        self.set_property(self.plc_name, self.prop_cell_input_1, 0)
        self.set_property(self.plc_name, self.prop_cell_input_2, 0)

        self.set_property(self.plc_name, self.prop_position, self.addr_bnc_2)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_output)
        self.set_property(self.plc_name, self.prop_cell_config, self.addr_one_shot)
        self.set_property(self.plc_name, self.prop_cell_input_1, 0)
        self.set_property(self.plc_name, self.prop_cell_input_2, 0)

        self.set_property(self.plc_name, self.prop_position, self.addr_constant)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_constant)
        self.set_property(self.plc_name, self.prop_cell_config, 1)

    def set_dslm_camera_properties(self):
        self.studio.live().set_live_mode_on(False)
        exposure = 1.0/self.z_scan_speed - 3
        self.set_property(self.cam_name, self.sensor_mode_prop, self.default_sensor_mode)
        self.set_property(self.cam_name, self.trigger_polarity_prop, self.scan_trigger_polarity)
        self.set_property(self.cam_name, self.trigger_delay_units_prop, self.trigger_delay_units)
        self.set_property(self.cam_name, self.trigger_delay_prop, self.default_cam_delay)
        self.set_property(self.cam_name, self.trigger_source_prop, self.scan_trigger_source)
        self.set_property(self.cam_name, self.trigger_active_prop, self.dslm_trigger_active)
        self.core.set_exposure(exposure)

    def set_lsrm_camera_properties(self, ili):
        self.studio.live().set_live_mode_on(False)
        line_interval = ili * 10**3
        self.set_property(self.cam_name, self.sensor_mode_prop, self.lsrm_sensor_mode)
        self.set_property(self.cam_name, self.trigger_polarity_prop, self.scan_trigger_polarity)
        self.set_property(self.cam_name, self.trigger_delay_units_prop, self.trigger_delay_units)
        self.set_property(self.cam_name, self.trigger_delay_prop, self.lsrm_cam_delay)
        self.set_property(self.cam_name, self.trigger_source_prop, self.scan_trigger_source)
        self.set_property(self.cam_name, self.trigger_active_prop, self.default_trigger_active)
        self.set_property(self.cam_name, self.ili_prop, line_interval)
        self.core.set_exposure(line_interval * self.lsrm_num_lines)

    def set_default_camera_properties(self, exposure):
        self.studio.live().set_live_mode_on(False)
        self.set_property(self.cam_name, self.sensor_mode_prop, self.default_sensor_mode)
        self.set_property(self.cam_name, self.trigger_polarity_prop, self.default_trigger_polarity)
        self.set_property(self.cam_name, self.trigger_delay_units_prop, self.trigger_delay_units)
        self.set_property(self.cam_name, self.trigger_delay_prop, self.default_cam_delay)
        self.set_property(self.cam_name, self.trigger_source_prop, self.default_trigger_source)
        self.set_property(self.cam_name, self.trigger_active_prop, self.default_trigger_active)
        self.core.set_exposure(exposure)

    def set_z_stage_speed(self, z_speed):
        self.set_property(self.z_stage_name, self.z_speed_property, z_speed)

    def set_xy_stage_speed(self, x_speed, y_speed):
        self.set_property(self.xy_stage_name, self.x_speed_property, x_speed)
        self.set_property(self.xy_stage_name, self.y_speed_property, y_speed)

    def scan_setup(self, start_z, end_z):
        start_z = np.round(start_z) / 1000.
        end_z = np.round(end_z) / 1000.
        scan_r_properties = "2 SCANR X=" + str(start_z) + " Y=" + str(end_z)
        self.set_property(self.tiger, self.serial, self.scan_properties)
        self.set_property(self.tiger, self.serial, scan_r_properties)

    def scan_start(self):
        self.set_z_stage_speed(self.z_scan_speed)
        self.set_property(self.tiger, self.serial, self.scan_start_command)
    
    def move_stage(self, x_position, y_position, z_position):
        self.set_xy_stage_speed(self.x_stage_speed, self.y_stage_speed)
        self.set_z_stage_speed(self.z_move_speed)
       
        #Reason for this is to ensure capillaries dpn't hit the objective. These conditions
        #should be changed to match the geometry of the holder.
        current_x_position = self.core.get_x_position()
        if current_x_position > x_position:
            self.core.set_position(self.z_stage_name, z_position)
            self.core.wait_for_device(self.z_stage_name)
            self.core.set_xy_position(x_position, y_position)
            self.core.wait_for_device(self.xy_stage_name)
        else:
            self.core.set_xy_position(x_position, y_position)
            self.core.wait_for_device(self.xy_stage_name)
            self.core.set_position(self.z_stage_name, z_position)
            self.core.wait_for_device(self.z_stage_name)

    def get_x_position(self):
        x_pos =  int(np.round(self.core.get_x_position(self.xy_stage_name)))
        return x_pos

    def get_y_position(self):
        y_pos =  int(np.round(self.core.get_y_position(self.xy_stage_name)))
        return y_pos

    def get_z_position(self):
        z_pos =  int(np.round(self.core.get_position(self.z_stage_name)))
        return z_pos
    
    def reset_joystick(self):
        self.set_property(self.tiger, self.serial, "J X+ Y+ Z+");

class SPIMGalvoCommands(object):
    """The NIDAQ and PyDAQmx have notably awful documentation (in my opinion). PyDAQ simple takes the C NIDAQ
    methods and changes them into python methods. NIDAQmx more or less takes the visual task creating of Labview
    and makes programmatic. In all of these functions, we create a task, create channels on the NIDAQ to perform
    said task with, and then send data to those channels. I'll go through each of the methods more in-depth:

    continuous_scan: Creates three analog output channels: One for each of the galvo mirrors and one that sends a
                    constant 5v signal to the PLC. The reason for the PLC signal is pretty jank, but basically I
                    needed a way to both use the PLC to trigger the camera and lasers for light sheet readout mode,
                    and I needed

    """
    def __init__(self):
        self.analog_output = pydaq.Task()
        self.timer = pydaq.Task()

        self.focus_channel = "Dev1/ao2"
        self.offset_channel = "Dev1/ao3"
        self.retrigger_channel = "PFI12"
        self.pulse_channel = "Dev1/Ctr0"

        self.focus = 0
        self.continuous_scan_offset = 0
        self.continuous_scan_width = 0
        self.continuous_scan_num_samples = 600
        self.continuous_scan_sampling_rate = self.continuous_scan_num_samples * 500

        self.ligthsheet_readout_current_position = 0
        self.lightsheet_readout_upper = 0
        self.lightsheet_readout_lower = 0
        self.lightsheet_readout_framerate = 30
        self.lightsheet_readout_laser_delay = 0
        self.lightsheet_readout_numLines = 2048
        self.lightsheet_readout_num_samples = self.lightsheet_readout_numLines * 2
        self.lightsheet_readout_sampling_rate = self.lightsheet_readout_num_samples * self.lightsheet_readout_framerate
        self.lightsheet_readout_ili = 1.0/float(self.lightsheet_readout_sampling_rate/2)

        self.continuous_scan_not_scanning()

    def continuous_scan(self):
        self.analog_output.StopTask()
        self.analog_output.ClearTask()
        self.timer.StopTask()
        self.timer.ClearTask()

        self.analog_output = pydaq.Task()
        self.timer = pydaq.Task()

        self.analog_output.CreateAOVoltageChan(self.focus_channel, "", -10.0, 10.0, pydaq.DAQmx_Val_Volts, None)
        self.analog_output.CreateAOVoltageChan(self.offset_channel, "", -10.0, 10.0, pydaq.DAQmx_Val_Volts, None)
        self.analog_output.CfgSampClkTiming(None, self.continuous_scan_sampling_rate, pydaq.DAQmx_Val_Rising, pydaq.DAQmx_Val_ContSamps, self.continuous_scan_num_samples)

        scan = np.linspace(-1*self.continuous_scan_width/2, self.continuous_scan_width/2, int(self.continuous_scan_num_samples/2)) + self.continuous_scan_offset
        scan = np.concatenate((scan,scan[::-1]),0)
        focus = self.focus*np.ones(self.continuous_scan_num_samples)

        temp = (pydaq.c_byte*4)()
        actual_written = pydaq.cast(temp, pydaq.POINTER(pydaq.c_long))
        write_data = np.concatenate((focus, scan),0)
        self.analog_output.WriteAnalogF64(self.continuous_scan_num_samples, True, -1, pydaq.DAQmx_Val_GroupByChannel, write_data, actual_written, None)

    def continuous_scan_not_scanning(self):
        self.analog_output.StopTask()
        self.analog_output.ClearTask()
        self.timer.StopTask()
        self.timer.ClearTask()

        self.analog_output = pydaq.Task()
        self.timer = pydaq.Task()

        self.analog_output.CreateAOVoltageChan(self.focus_channel, "", -10.0, 10.0, pydaq.DAQmx_Val_Volts, None)
        self.analog_output.CreateAOVoltageChan(self.offset_channel, "", -10.0, 10.0, pydaq.DAQmx_Val_Volts, None)
        self.analog_output.CfgSampClkTiming(None, self.continuous_scan_sampling_rate, pydaq.DAQmx_Val_Rising, pydaq.DAQmx_Val_ContSamps, self.continuous_scan_num_samples)

        scan = np.zeros(self.continuous_scan_num_samples) + self.continuous_scan_offset
        focus = self.focus*np.ones(self.continuous_scan_num_samples)

        temp = (pydaq.c_byte*4)()
        actual_written = pydaq.cast(temp, pydaq.POINTER(pydaq.c_long))
        write_data = np.concatenate((focus, scan),0)
        self.analog_output.WriteAnalogF64(self.continuous_scan_num_samples, True, -1, pydaq.DAQmx_Val_GroupByChannel, write_data, actual_written, None)

    def continuous_lightsheet_readout(self):
        self.analog_output.StopTask()
        self.analog_output.ClearTask()
        self.timer.StopTask()
        self.timer.ClearTask()

        self.analog_output = pydaq.Task()
        self.timer = pydaq.Task()

        self.lightsheet_readout_sampling_rate = self.lightsheet_readout_num_samples * self.lightsheet_readout_framerate
        #ili must be calculated like this to compensate for the number of samples for the laser to travel
        #one pixel row(line). Originally, I had numSamples = 2048 = number of pixel rows. Fundamentally, this is fine.
        #However, I wanted the laser delay parameter to have smaller steps, and so I doubled the number of samples.
        #This could be changed.
        self.lightsheet_readout_ili = 1.0/float(self.lightsheet_readout_sampling_rate/2)

        self.analog_output.CreateAOVoltageChan(self.focus_channel, "", -10.0, 10.0, pydaq.DAQmx_Val_Volts, None)
        self.analog_output.CreateAOVoltageChan(self.offset_channel, "", -10.0, 10.0, pydaq.DAQmx_Val_Volts, None)
        self.analog_output.CfgDigEdgeStartTrig(self.retrigger_channel, pydaq.DAQmx_Val_Rising)
        self.analog_output.CfgSampClkTiming(None, self.lightsheet_readout_sampling_rate, pydaq.DAQmx_Val_Rising, pydaq.DAQmx_Val_FiniteSamps, self.lightsheet_readout_num_samples)
        self.analog_output.SetStartTrigRetriggerable(True)

        #pulseHighTime = 0.002
        #pulseLowTime = (1.0/self.lightsheet_readout_framerate) - pulseHighTime
        #self.timer.CreateCOPulseChanTime(self.pulse_channel, "timer", pydaq.DAQmx_Val_Seconds, pydaq.DAQmx_Val_Low, 0.0, pulseLowTime, pulseHighTime)
        #self.timer.CfgImplicitTiming(pydaq.DAQmx_Val_ContSamps, 0)

        num_delay = 100
        num_end_delay = num_delay - self.lightsheet_readout_laser_delay
        scan_start_delay = np.zeros(self.lightsheet_readout_laser_delay) + self.lightsheet_readout_upper
        focus_start_delay = np.zeros(self.lightsheet_readout_laser_delay) + self.focus
        scan_end_delay = np.zeros(num_end_delay) + self.lightsheet_readout_upper
        focus_end_delay = np.zeros(num_end_delay) + self.focus

        scan = np.linspace(self.lightsheet_readout_lower, self.lightsheet_readout_upper, self.lightsheet_readout_num_samples-(num_delay))
        scan = np.concatenate((scan_start_delay, scan, scan_end_delay), 0)
        focus = self.focus * np.ones(self.lightsheet_readout_num_samples-num_delay)
        focus = np.concatenate((focus_start_delay, focus, focus_end_delay), 0)

        temp = (pydaq.c_byte*4)()
        actual_written = pydaq.cast(temp, pydaq.POINTER(pydaq.c_long))
        write_data = np.concatenate((focus, scan),0)
        self.analog_output.WriteAnalogF64(self.lightsheet_readout_num_samples, False, -1, pydaq.DAQmx_Val_GroupByChannel, write_data, actual_written, None)

        #self.timer.StartTask()
        self.analog_output.StartTask()
    
    #Literally the same function as continuousScanNotScanning() except uses ligthsheet_readout_current_position
    #so that continuous_scan_offset isn't changed. Used to set lower and upper bounds for LSRM.
    def continuous_lightsheet_readout_not_scanning(self):
        self.analog_output.StopTask()
        self.analog_output.ClearTask()
        self.timer.StopTask()
        self.timer.ClearTask()

        self.analog_output = pydaq.Task()
        self.timer = pydaq.Task()

        self.analog_output.CreateAOVoltageChan(self.focus_channel, "", -10.0, 10.0, pydaq.DAQmx_Val_Volts, None)
        self.analog_output.CreateAOVoltageChan(self.offset_channel, "", -10.0, 10.0, pydaq.DAQmx_Val_Volts, None)
        self.analog_output.CfgSampClkTiming(None, self.continuous_scan_sampling_rate, pydaq.DAQmx_Val_Rising, pydaq.DAQmx_Val_ContSamps, self.continuous_scan_num_samples)

        scan = np.zeros(self.continuous_scan_num_samples) + self.ligthsheet_readout_current_position
        focus = self.focus*np.ones(self.continuous_scan_num_samples)
        plc = np.ones(self.continuous_scan_num_samples) * 5

        temp = (pydaq.c_byte*4)()
        actual_written = pydaq.cast(temp, pydaq.POINTER(pydaq.c_long))
        write_data = np.concatenate((focus, scan, plc),0)
        self.analog_output.WriteAnalogF64(self.continuous_scan_num_samples, True, -1, pydaq.DAQmx_Val_GroupByChannel, write_data, actual_written, None)

    def plc_triggered_lightsheet_readout(self):
        self.analog_output.StopTask()
        self.analog_output.ClearTask()
        self.timer.StopTask()
        self.timer.ClearTask()

        self.analog_output = pydaq.Task()
        self.timer = pydaq.Task()

        self.lightsheet_readout_sampling_rate = self.lightsheet_readout_num_samples * self.lightsheet_readout_framerate
        self.lightsheet_readout_ili = 1.0/float(self.lightsheet_readout_sampling_rate/2)

        self.analog_output = pydaq.Task()
        self.analog_output.CreateAOVoltageChan(self.focus_channel, "", -10.0, 10.0, pydaq.DAQmx_Val_Volts, None)
        self.analog_output.CreateAOVoltageChan(self.offset_channel, "", -10.0, 10.0, pydaq.DAQmx_Val_Volts, None)
        self.analog_output.CfgDigEdgeStartTrig(self.retrigger_channel, pydaq.DAQmx_Val_Rising)
        self.analog_output.CfgSampClkTiming(None, self.lightsheet_readout_sampling_rate, pydaq.DAQmx_Val_Rising, pydaq.DAQmx_Val_FiniteSamps, self.lightsheet_readout_num_samples)
        self.analog_output.SetStartTrigRetriggerable(True)

        num_delay = 100
        num_end_delay = num_delay - self.lightsheet_readout_laser_delay
        scan_start_delay = np.zeros(self.lightsheet_readout_laser_delay) + self.lightsheet_readout_upper
        focus_start_delay = np.zeros(self.lightsheet_readout_laser_delay) + self.focus
        scan_end_delay = np.zeros(num_end_delay) + self.lightsheet_readout_upper
        focus_end_delay = np.zeros(num_end_delay) + self.focus

        scan = np.linspace(self.lightsheet_readout_lower, self.lightsheet_readout_upper, self.lightsheet_readout_num_samples-num_delay)
        scan = np.concatenate((scan_start_delay, scan, scan_end_delay), 0)
        focus = self.focus * np.ones(self.lightsheet_readout_num_samples-num_delay)
        focus = np.concatenate((focus_start_delay, focus, focus_end_delay), 0)

        temp = (pydaq.c_byte*4)()
        actual_written = pydaq.cast(temp, pydaq.POINTER(pydaq.c_long))
        write_data = np.concatenate((focus, scan),0)
        self.analog_output.WriteAnalogF64(self.lightsheet_readout_num_samples, False, -1, pydaq.DAQmx_Val_GroupByChannel, write_data, actual_written, None)

        self.analog_output.StartTask()

    def exit(self):
        
        self.focus = 0
        self.continuous_scan_offset = 0
        self.continuous_scan_width = 0
        self.continuous_scan()
        
        self.analog_output.StopTask()
        self.analog_output.ClearTask()
        self.timer.StopTask()
        self.timer.ClearTask()
    
    



