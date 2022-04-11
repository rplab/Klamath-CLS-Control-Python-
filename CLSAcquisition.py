"""Main acquisition script. This class takes all the data initialized using the CLSDialog and SPIMGalvo windows
and performs an image acquisition based on said data. It extends the Thread class so that the use isn't completely
locked out from Micro-Manager while the acquisition runs.


"""

from HardwareCommands import MMHardwareCommands, SPIMGalvoCommands
import threading
import time
import os
from CLSAcquisitionParameters import AcquisitionSettings, RegionSettings
import QtDesignerGUI
from pycromanager import Studio, Core
import numpy as np


class Acquisition(threading.Thread):
    def __init__(self, studio: Studio, core: Core, acquisition_dialog: QtDesignerGUI.AcquisitionDialog,
                 acquisition_settings: AcquisitionSettings, mm_hardware_commands: MMHardwareCommands,
                 spim_commands: SPIMGalvoCommands):
        super().__init__()
        self.studio = studio
        self.core = core
        self.acquisition_dialog = acquisition_dialog
        self.acquisition_settings = acquisition_settings
        self.mm_hardware_commands = mm_hardware_commands
        self.spim_commands = spim_commands
        self.abort_dialog = QtDesignerGUI.AbortDialog()
        self.acquisition_dialog.show()
        self.region_settingsArray = self.acquisition_settings.region_settings_list
        self.channel_order_list = self.acquisition_settings.channel_order_list
        self.directory = self.initial_dir_check(self.acquisition_settings.directory)
        self.abort_boolean = False

        self.acquisition_dialog.abort_button.clicked.connect(self.abort_button_clicked)
        self.abort_dialog.abort_button.clicked.connect(self.abort_confirm_button_clicked)
        self.abort_dialog.cancel_button.clicked.connect(self.cancel_button_clicked)

    def initial_dir_check(self, directory: str):
        path = directory + "/Acquisition"
        i = 1
        if os.path.isdir(path):
            path += str(i)
        while os.path.isdir(path):
            path = path.removesuffix(str(i))
            i += 1
            path += str(i)
        return path

    def snap_acquisition(self, fish_num, region_num, num_time_points, region_settings: RegionSettings):
        if self.acquisition_settings.lightsheet_mode_boolean:
            framerate = min(int(np.round(1 / self.spim_commands.lightsheet_readout_framerate) * 10 ** 3), 40)
            self.spim_commands.lightsheet_readout_framerate = framerate
            self.mm_hardware_commands.initialize_plc_for_continuous_lsrm(self.spim_commands.lightsheet_readout_framerate)
            self.spim_commands.plc_triggered_lightsheet_readout()
            self.mm_hardware_commands.set_lsrm_camera_properties(self.spim_commands.lightsheet_readout_ili)
        else:
            self.mm_hardware_commands.set_default_camera_properties(region_settings.snap_exposure_time)
            self.spim_commands.continuous_scan()

        for channel in self.channel_order_list:
            if channel in region_settings.snap_channel_list:
                if channel == "BF":
                    self.mm_hardware_commands.set_default_camera_properties(region_settings.snap_exposure_time)
                    self.spim_commands.continuous_scan()

                self.acquisition_dialog.acquisition_label.setText("Initializing " + channel + " snap")
                path = self.directory + "/Fish" + str(fish_num + 1) + "/Pos" + str(
                    region_num + 1) + "/snap/" + channel + "/Timepoint" + str(num_time_points + 1)
                data = self.studio.data().create_single_plane_tiff_series_datastore(path)

                self.acquisition_dialog.acquisition_label.setText("Acquiring " + channel + " snap")

                self.core.set_config(self.acquisition_settings.channel_group_name, channel)
                image = self.studio.live().snap(False).get(0)
                data.put_image(image)

                self.acquisition_dialog.acquisition_label.setText("Saving " + channel + " snap")
                data.close()
                self.core.clear_circular_buffer()

                if self.abort_boolean:
                    data.close()
                    self.abort_acquisition()
                    return

    def vide_acquisition(self, fish_num, region_num, num_time_points, region_settings: RegionSettings):
        for channel in self.channel_order_list:
            if channel in region_settings.video_channel_list:
                if self.acquisition_settings.lightsheet_mode_boolean:
                    framerate = min(int(np.round(1 / region_settings.video_exposure_time) * 10 ** 3), 40)
                    self.spim_commands.lightsheet_readout_framerate = framerate
                    self.mm_hardware_commands.initialize_plc_for_continuous_lsrm(self.spim_commands.lightsheet_readout_framerate)
                    self.spim_commands.plc_triggered_lightsheet_readout()
                    self.mm_hardware_commands.set_lsrm_camera_properties(self.spim_commands.lightsheet_readout_ili)
                else:
                    framerate = int(np.round(1 / region_settings.video_exposure_time) * 10 ** 3)
                    self.mm_hardware_commands.set_default_camera_properties(region_settings.video_exposure_time)
                    self.spim_commands.continuous_scan()

                self.acquisition_dialog.acquisition_label.setText("Initializing " + channel + " video")
                path = self.directory + "/Fish" + str(fish_num + 1) + "/Pos" + str(
                    region_num + 1) + "/video/" + channel + "/Timepoint" + str(num_time_points + 1)
                data = self.studio.data().create_single_plane_tiff_series_datastore(path)

                num_images = framerate * region_settings.video_duration_in_seconds
                cur_frame = 0
                timeout = 0
                sequence_boolean = False

                self.acquisition_dialog.acquisition_label.setText("Acquiring " + channel + " video")

                self.core.set_config(self.acquisition_settings.channel_group_name, channel)
                self.core.start_sequence_acquisition(int(num_images), np.double(0), True)

                while self.core.get_remaining_image_count() > 0 or self.core.is_sequence_running():
                    if self.abort_boolean:
                        data.close()
                        self.abort_acquisition()
                        return

                    if timeout > 500:
                        self.core.stop_sequence_acquisition()
                        self.core.clear_circular_buffer()
                        self.acquisition_dialog.acquisition_label.setText(
                            "Timepoint " + str(num_time_points + 1) + " " + channel + " video failed, camera timeout")
                        self.studio.logs().log_message(
                            "Timepoint " + str(num_time_points + 1) + " " + channel + " video failed, camera timeout")

                    if self.core.get_remaining_image_count() > 0:
                        tagged = self.core.pop_next_tagged_image()
                        image = self.studio.data().convert_tagged_image(tagged)
                        coords = image.get_coords().copy_builder().t(cur_frame).build()
                        image = image.copy_at_coords(coords)
                        data.put_image(image)
                        cur_frame += 1
                        timeout = 0

                        if not self.core.is_sequence_running() and not sequence_boolean:
                            self.acquisition_dialog.acquisition_label.setText("Saving " + channel + " video")
                            sequence_boolean = True
                    else:
                        self.core.sleep(5)
                        timeout += 1

                self.core.stop_sequence_acquisition()
                data.close()
                self.core.clear_circular_buffer()

                if self.abort_boolean:
                    data.close()
                    self.abort_acquisition()
                    return

    def z_stack_acquisition(self, fish_num, region_num, num_time_points, region_settings: RegionSettings):
        z_start = region_settings.z_start_position
        z_end = region_settings.z_end_position
        step_size = region_settings.step_size
        num_frames = int(np.round(np.abs(z_end - z_start) / step_size))

        self.mm_hardware_commands.move_stage(region_settings.x_position, region_settings.y_position, z_start)

        if self.acquisition_settings.lightsheet_mode_boolean:
            if self.mm_hardware_commands.z_scan_speed == 0.015:
                self.spim_commands.lightsheet_readout_framerate = 15
            if self.mm_hardware_commands.z_scan_speed == 0.030:
                self.spim_commands.lightsheet_readout_framerate = 30

            self.spim_commands.plc_triggered_lightsheet_readout()
            self.mm_hardware_commands.set_lsrm_camera_properties(self.spim_commands.lightsheet_readout_ili)
        else:
            self.mm_hardware_commands.set_dslm_camera_properties()
            self.spim_commands.continuous_scan()

        self.mm_hardware_commands.initialize_plc_for_scan(step_size)

        for channel in self.channel_order_list:
            if channel in region_settings.z_stack_channel_list:
                self.acquisition_dialog.acquisition_label.setText("Initializing " + channel + " z stack")
                path = self.directory + "/Fish" + str(fish_num + 1) + "/Pos" + str(
                    region_num + 1) + "/zStack/" + channel + "/Timepoint" + str(num_time_points + 1)
                data = self.studio.data().create_single_plane_tiff_series_datastore(path)

                # This buffer is so the stage overshoots a little bit to ensure enough images are captured
                # during the sequence acquisition to end naturally. This sucks, but I think it's necessary
                # with how the acquisition is currently performed.
                scan_buffer = 8
                if z_start <= z_end:
                    self.mm_hardware_commands.scan_setup(z_start - scan_buffer, z_end + scan_buffer)
                else:
                    self.mm_hardware_commands.scan_setup(z_start + scan_buffer, z_end - scan_buffer)

                sequence_boolean = False
                timeout = 0
                cur_frame = 0

                self.acquisition_dialog.acquisition_label.setText("Acquiring " + channel + " z stack")
                self.core.set_config(self.acquisition_settings.channel_group_name, channel)
                self.core.start_sequence_acquisition(int(num_frames), np.double(0), False)
                self.mm_hardware_commands.scan_start()

                while self.core.get_remaining_image_count() > 0 or self.core.is_sequence_running():
                    while cur_frame < num_frames:
                        if self.abort_boolean:
                            self.abort_acquisition()
                            data.close()
                            return

                        if timeout > 500:
                            self.core.stop_sequence_acquisition()
                            self.core.clear_circular_buffer()
                            if cur_frame < num_frames:
                                self.acquisition_dialog.acquisition_label.setText("Timepoint " + str(
                                    num_time_points + 1) + " " + channel + " z stack failed, not enough images acquired")
                                self.studio.logs().log_message("Timepoint " + str(num_time_points + 1) + " " + channel
                                                               + " z stack failed, not enough images acquired")

                        if self.core.get_remaining_image_count() > 0:
                            tagged = self.core.pop_next_tagged_image()
                            image = self.studio.data().convert_tagged_image(tagged)
                            coords = image.get_coords().copy_builder().z(cur_frame).build()
                            image = image.copy_at_coords(coords)
                            data.put_image(image)
                            cur_frame += 1
                            timeout = 0

                            # This is executed if sequence is over but still images to be saved
                            # in sequence buffer
                            if not self.core.is_sequence_running() and not sequence_boolean:
                                self.acquisition_dialog.acquisition_label.setText("Saving " + channel + " z stack")
                                sequence_boolean = True
                        else:
                            self.core.sleep(5)
                            timeout += 1

                    self.core.stop_sequence_acquisition()

                data.close()
                self.core.clear_circular_buffer()
                self.core.wait_for_device(self.mm_hardware_commands.xy_stage_name)
                self.core.wait_for_device(self.mm_hardware_commands.z_stage_name)
                self.core.wait_for_device(self.mm_hardware_commands.cam_name)

                if self.abort_boolean:
                    data.close()
                    self.abort_acquisition()
                    return

    def abort_button_clicked(self):
        self.abort_dialog.show()

    def abort_confirm_button_clicked(self):
        self.abort_boolean = True
        self.abort_dialog.close()

    def cancel_button_clicked(self):
        self.abort_dialog.close()

    def abort_acquisition(self):
        self.core.stop_sequence_acquisition()
        self.core.clear_circular_buffer()
        self.mm_hardware_commands.reset_joystick()
        self.mm_hardware_commands.set_default_camera_properties(self.mm_hardware_commands.default_exposure)
        self.acquisition_dialog.acquisition_label.setText("Aborted")

    def run(self):
        self.core.stop_sequence_acquisition()
        self.core.clear_circular_buffer()
        self.core.set_shutter_open(False)
        self.core.set_auto_shutter(True)

        for num_time_points in range(self.acquisition_settings.num_time_points):
            start = time.time_ns()

            self.acquisition_dialog.time_point_label.setText("Time point " + str(num_time_points + 1))
            self.acquisition_dialog.acquisition_label.setText("Initializing Acquisition")

            if self.abort_boolean:
                self.abort_acquisition()
                return

            for fish_num in range(self.acquisition_settings.fish_dimension):
                for region_num in range(self.acquisition_settings.region_dimension):
                    region_settings = self.acquisition_settings.region_settings_list[fish_num][region_num]
                    if region_settings != 0:
                        x_pos = region_settings.x_position
                        y_pos = region_settings.y_position
                        z_pos = region_settings.z_position

                        self.acquisition_dialog.fish_label.setText("Fish " + str(fish_num + 1))
                        self.acquisition_dialog.region_label.setText("Region " + str(region_num + 1))

                        self.acquisition_dialog.acquisition_label.setText("Moving to start position...")
                        self.mm_hardware_commands.move_stage(x_pos, y_pos, z_pos)

                        if region_settings.snap_boolean:
                            self.snap_acquisition(fish_num, region_num, num_time_points, region_settings)

                        if region_settings.video_boolean:
                            self.vide_acquisition(fish_num, region_num, num_time_points, region_settings)

                        if region_settings.z_stack_boolean:
                            self.z_stack_acquisition(fish_num, region_num, num_time_points, region_settings)

            # If timePointsBoolean false, causes time points loop to end
            if not self.acquisition_settings.time_points_boolean:
                num_time_points = self.acquisition_settings.num_time_points

            if self.abort_boolean:
                self.abort_acquisition()
                return

            time_points_left = self.acquisition_settings.num_time_points - num_time_points
            if self.acquisition_settings.time_points_boolean and time_points_left > 1:
                self.acquisition_dialog.acquisition_label.setText("Moving back to start position...")

                x_pos = self.region_settingsArray[0][0].x_position
                y_pos = self.region_settingsArray[0][0].y_position
                z_pos = self.region_settingsArray[0][0].z_position
                self.mm_hardware_commands.move_stage(x_pos, y_pos, z_pos)

                end = time.time_ns()
                duration_ms = np.round((end - start) / np.power(10, 6))
                delay = self.acquisition_settings.time_points_interval * 60 * 1000

                while delay - duration_ms > 0:
                    end = time.time_ns()
                    duration_ms = np.round((end - start) / np.power(10, 6))

                    time_left_seconds = int(np.round((delay - duration_ms) / 1000))
                    num_minutes_left = int(np.floor(time_left_seconds / 60))
                    num_seconds_left = int(time_left_seconds % 60)
                    if num_minutes_left != 0:
                        self.acquisition_dialog.acquisition_label.setText(
                            "next time point: " + str(num_minutes_left) + " minutes " + str(
                                num_seconds_left) + " seconds")
                    else:
                        self.acquisition_dialog.acquisition_label.setText(
                            "next time point: " + str(num_seconds_left) + " seconds")

                    if self.abort_boolean:
                        self.abort_acquisition()
                        return

        self.mm_hardware_commands.set_default_camera_properties(self.mm_hardware_commands.default_exposure)
        self.core.set_config(self.acquisition_settings.channel_group_name, "BF")
        self.mm_hardware_commands.reset_joystick()

        self.acquisition_dialog.acquisition_label.setText("Your acquisition was successful!")
