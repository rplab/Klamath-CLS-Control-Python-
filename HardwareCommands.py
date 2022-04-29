'''HardwareCommands

This file contains classes with methods that interact directly with the hardware of the microscope, 
as well as some properties for said devices. There are two classes:

-MMHardwareCommands: Interacts with all hardware devices connected through Micro-Manager
-SPIMGalvoCommands: Interacts with the NIDAQ to control galvo mirrors and triggering of LSRM

Future changes:
- Perhaps put all properties into separate classes? Reason to do this would be to make commands 
  more generically usable. Could be useful in future development of image acquisitions. Would
  also be more true to the nature of MVC.


'''


import numpy as np
import PyDAQmx as pydaq
import nidaqmx
from nidaqmx.stream_writers import AnalogMultiChannelWriter
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
        
        #Camera properties names
        self.cam_name = self.core.get_camera_device()
        self.default_sensor_mode = "AREA"
        self.lsrm_sensor_mode = "PROGRESSIVE"
        self.default_trigger_polarity = "NEGATIVE"
        self.scan_trigger_polarity= "POSITIVE"

        #Camera properties
        self.default_cam_delay = 0
        self.lsrm_cam_delay = 0
        self.trigger_delay_units = 'MILLISECONDS'
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
        
        #Stage properties
        self.xy_stage_name = self.core.get_xy_stage_device()
        self.z_stage_name = self.core.get_focus_device()
        self.scan_properties = "2 SCAN Y=0 Z=0 F=0"
        self.scan_start_command = "2 SCAN"
        self.x_stage_speed = 1.0
        self.y_stage_speed = 1.0
        self.z_stage_speed = 0.5
    
    def set_property(self, device, prop, value):
        self.core.set_property(device, prop, value)

    def initialize_plc_for_scan(self, step_size, z_scan_speed):
        """
        The PLC (programmable logic card) is used to create logic circuits through software.
        The circuit here creates a pulse matching the stage speed and step size during 
        a z-stack. This pulse is sent to the camera as an external trigger. 

        For a full realization of this circuit, lease see the developer guide.
        """

        #factor of 4 in frame interval is because the plc clock runs at 4 khz, so 4 clock
        #ticks is 1 ms
        trigger_pulse_width = self.dslm_exposure * 4
        frame_interval = np.ceil((step_size / z_scan_speed) * 4)
        
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

    def initialize_plc_for_continuous_lsrm(self, framerate):
        # Same as the last PLC function except it pulses on its own.

        trigger_pulse_width = 4
        frame_interval = np.ceil(1.0 / framerate * 1000 * 4)

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

        self.set_property(self.plc_name, self.prop_position, self.addr_constant)
        self.set_property(self.plc_name, self.prop_cell_type, self.val_constant)
        self.set_property(self.plc_name, self.prop_cell_config, 1)

    def set_dslm_camera_properties(self, z_scan_speed):
        self.studio.live().set_live_mode_on(False)
        exposure = 1.0/z_scan_speed - 3
        self.set_property(self.cam_name, self.sensor_mode_prop, self.default_sensor_mode)
        self.set_property(self.cam_name, self.trigger_polarity_prop, self.scan_trigger_polarity)
        self.set_property(self.cam_name, self.trigger_delay_units_prop, self.trigger_delay_units)
        self.set_property(self.cam_name, self.trigger_delay_prop, self.default_cam_delay)
        self.set_property(self.cam_name, self.trigger_source_prop, self.scan_trigger_source)
        self.set_property(self.cam_name, self.trigger_active_prop, self.dslm_trigger_active)
        self.core.set_exposure(exposure)

    def set_lsrm_camera_properties(self, ili):
        """
        This is fundamentally different from DSLM properties in two ways. 
        The sensor mode is set to progressive and we need to set an internal
        line interval. Please read my lightsheet readout mode guide for a 
        full explanation of this mode.
        """

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
        """
        SCAN is a module on the ASI stage. Please read the ASI manual for more details
        The '2' in all of the commands is the address of the Z Stage card as opposed to the
        XY Stage, which is '1'. An ASI stage scan is achieved by doing the following:

        1. Scan properties are set as "2 SCAN Y=0 Z=0 F=0". This is simply
           to tell the stage what axis will be scaning.
        2. Positions are set with SCANR X=[StartPosition] Y=[EndPosition]
           where positions are in units of mm. SCANR means raster scan.
        3. "2 SCAN" is sent. When the stage reaches the first position, the TTL 
           port goes high. This is what triggers the PLC to pulse. Once it reaches
           the end, TTL goes low and the stage resets to the start position.
        """
        start_z = np.round(start_z) / 1000.
        end_z = np.round(end_z) / 1000.
        scan_r_properties = "2 SCANR X=" + str(start_z) + " Y=" + str(end_z)
        self.set_property(self.tiger, self.serial, self.scan_properties)
        self.set_property(self.tiger, self.serial, scan_r_properties)

    def scan_start(self):
        self.set_property(self.tiger, self.serial, self.scan_start_command)
    
    def move_stage(self, x_position, y_position, z_position):
        self.set_xy_stage_speed(self.x_stage_speed, self.y_stage_speed)
        self.set_z_stage_speed(self.z_stage_speed)
       
        #Reason for this is to ensure capillaries dpn't hit the objective. These conditions
        #should be changed to match the geometry of the holder.
        current_x_position = self.get_x_position()
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
        #The joystick tends to bug out after the SCAN command. This resets
        #the joystick so that it works correctly. See the ASI documentation 
        #for more details.
        self.set_property(self.tiger, self.serial, "J X+ Y+ Z+");

class SPIMGalvoCommands(object):
    """
    NIDAQmx more or less takes the visual task creating of Labview and makes it programmatic. PyDAQ simple takes the C-based 
    NIDaqMX methods and changes them into python methods. NIDaqMX has the most awful documentation ever made (in my humble opinion),
    which unfortunately makes PyDAQmx just as bad. In all of these functions, we create a task, create channels on the NIDAQ to perform
    said task with, and then send data to those channels. I'll go through each of the methods more in-depth:

    Methods: 

    continuous_scan() - Creates two analog output channels, one for each galvo mirror. The offset mirror is the mirror
                        that creates the light sheet. A triangle wave signal is sent to the mirror to scan continuously.
                        The sampling rate is set to 500 times the number of samples so that it's scanned at 500 hz.
    
    continuous_scan_not_scanning() - Same as continuous_scan except not scanning. Used to align the laser.

    lightsheet_readout_not_scanning() - same as previous method except usesligthsheet_readout_current_position
                                        to set lower and upper values of scanning range.
    
    lightsheet_readout() - Creates two analog channels in a retriggerable task so that laser scanning can be externally triggered.
                           Currently, mirrors and camera are triggered simultaneously by the PLC. Scanning frequency in this mode
                           is significantly lower than in continuous_scan() to work with the Hamamatsu Lightsheet Readout Mode.
                           Please read my guide on LSRM for more information on this.
    
    exit() - Just makes sure all tasks end the analog outputs go to zero volts.
    """


    def __init__(self):
        self.scan_output = nidaqmx.Task()
        self.cam_output = nidaqmx.Task()

        self.cam_channel = "Dev1/ao0"
        self.focus_channel = "Dev1/ao2"
        self.offset_channel = "Dev1/ao3"
        self.pulse_channel = "Dev1/Ctr0"
        self.retrigger_channel = 'PFI0'

        self.focus = 0
        self.continuous_scan_offset = 0
        self.continuous_scan_width = 0
        self.continuous_scan_num_samples = 600
        self.continuous_scan_frequency = 500
        self.continuous_scan_sampling_rate = self.continuous_scan_num_samples * self.continuous_scan_frequency

        self.ligthsheet_readout_current_position = 0
        self.lightsheet_readout_upper = 0.
        self.lightsheet_readout_lower = 0.
        self.lightsheet_readout_framerate = 15
        self.lightsheet_readout_laser_delay = 0.500
        self.lightsheet_readout_cam_delay = 0.
        self.lightsheet_readout_delay_buffer = 100
        self.lightsheet_readout_num_samples = 2048 + self.lightsheet_readout_delay_buffer
        self.lightsheet_readout_sampling_rate = self.lightsheet_readout_num_samples
        self.lightsheet_readout_ili = 1.0/float(self.lightsheet_readout_sampling_rate)

        self.continuous_scan_not_scanning()

    def continuous_scan(self):
        self.reset_tasks()

        self.scan_output.ao_channels.add_ao_voltage_chan(self.focus_channel)
        self.scan_output.ao_channels.add_ao_voltage_chan(self.offset_channel)
        self.scan_output.timing.cfg_samp_clk_timing(self.continuous_scan_sampling_rate, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan=self.continuous_scan_num_samples)

        self.cam_output.co_channels.add_co_pulse_chan_time(self.pulse_channel, low_time=0.001, high_time=0.001)
        self.cam_output.timing.cfg_implicit_timing(samps_per_chan=1)
        self.cam_output.triggers.start_trigger.cfg_dig_edge_start_trig(self.retrigger_channel)
        self.cam_output.triggers.start_trigger.retriggerable = True

        scan = np.linspace(-1*self.continuous_scan_width/2, self.continuous_scan_width/2, int(self.continuous_scan_num_samples/2)) + self.continuous_scan_offset
        scan = np.concatenate((scan,scan[::-1]),0)
        focus = self.focus*np.ones(self.continuous_scan_num_samples)

        writer = AnalogMultiChannelWriter(self.scan_output.out_stream)
        writer.write_many_sample(np.array([focus, scan]))

        self.scan_output.start()
        self.cam_output.start()

    def continuous_scan_not_scanning(self):
        self.reset_tasks()

        self.scan_output.ao_channels.add_ao_voltage_chan(self.focus_channel)
        self.scan_output.ao_channels.add_ao_voltage_chan(self.offset_channel)
        self.scan_output.timing.cfg_samp_clk_timing(self.continuous_scan_sampling_rate, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan=self.continuous_scan_num_samples)

        scan = np.zeros(self.continuous_scan_num_samples) + self.continuous_scan_offset
        focus = self.focus*np.ones(self.continuous_scan_num_samples)

        writer = AnalogMultiChannelWriter(self.scan_output.out_stream)
        writer.write_many_sample(np.array([focus, scan]))

        self.scan_output.start()
    
    def lightsheet_readout_not_scanning(self):
        self.reset_tasks()

        self.scan_output.ao_channels.add_ao_voltage_chan(self.focus_channel)
        self.scan_output.ao_channels.add_ao_voltage_chan(self.offset_channel)
        self.scan_output.timing.cfg_samp_clk_timing(self.continuous_scan_sampling_rate, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan=self.continuous_scan_num_samples)
        
        scan = np.zeros(self.continuous_scan_num_samples) + self.ligthsheet_readout_current_position
        focus = self.focus*np.ones(self.continuous_scan_num_samples)

        writer = AnalogMultiChannelWriter(self.scan_output.out_stream)
        writer.write_many_sample(np.array([focus, scan]))

        self.scan_output.start()

    def lightsheet_readout(self):
        self.reset_tasks()

        self.lightsheet_readout_sampling_rate = self.lightsheet_readout_num_samples * (self.lightsheet_readout_framerate + 1)
        self.lightsheet_readout_ili = 1.0/float(self.lightsheet_readout_sampling_rate)

        self.scan_output.ao_channels.add_ao_voltage_chan(self.focus_channel)
        self.scan_output.ao_channels.add_ao_voltage_chan(self.offset_channel)
        self.scan_output.timing.cfg_samp_clk_timing(self.lightsheet_readout_sampling_rate, sample_mode=nidaqmx.constants.AcquisitionType.FINITE, samps_per_chan=self.lightsheet_readout_num_samples)
        self.scan_output.triggers.start_trigger.cfg_dig_edge_start_trig(self.retrigger_channel)
        self.scan_output.triggers.start_trigger.retriggerable = True
        self.scan_output.triggers.start_trigger.delay_units = nidaqmx.constants.DigitalWidthUnits.SECONDS
        self.scan_output.triggers.start_trigger.delay = self.lightsheet_readout_laser_delay/1000 + 20 * 10**-9
        
        self.cam_output.co_channels.add_co_pulse_chan_time(self.pulse_channel, initial_delay=self.lightsheet_readout_cam_delay/1000, low_time=.001, high_time=.001).co_enable_initial_delay_on_retrigger = True
        self.cam_output.timing.cfg_implicit_timing(samps_per_chan=1)
        self.cam_output.triggers.start_trigger.cfg_dig_edge_start_trig(self.retrigger_channel)
        self.cam_output.triggers.start_trigger.retriggerable = True

        scan = np.linspace(self.lightsheet_readout_lower, self.lightsheet_readout_upper, self.lightsheet_readout_num_samples-self.lightsheet_readout_delay_buffer)
        buffer = self.lightsheet_readout_lower * np.ones(self.lightsheet_readout_delay_buffer)
        scan = np.concatenate((scan, buffer),0)
        focus = self.focus * np.ones(self.lightsheet_readout_num_samples)

        writer = AnalogMultiChannelWriter(self.scan_output.out_stream)
        writer.write_many_sample(np.array([focus, scan]))

        self.scan_output.start()
        self.cam_output.start()

    def reset_tasks(self):
        self.scan_output.close()
        self.cam_output.close()

        self.scan_output = nidaqmx.Task()
        self.cam_output = nidaqmx.Task()

    def exit(self):
        self.focus = 0
        self.continuous_scan_offset = 0
        self.continuous_scan_width = 0
        self.continuous_scan()
        self.scan_output.close()
        self.cam_output.close()
    
    



