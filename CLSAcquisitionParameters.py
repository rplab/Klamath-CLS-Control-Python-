"""The "model" part of the CLS program. Holds settings to be used during
CLS Acquisition.

Worth noting that fish_num and region_num are the index trackers in the
CLSController class in Controller.py.

Future Changes:
- Currently uses fields but could be changed to a
  getter/setter design? Not sure if it really matters.

- Logic to control region_settings_list is a little funky: probably could
  be improved somehow.

- region_settings class currently contains no methods: could be made into dictionary
  if someone felt inclined."""


class AcquisitionSettings(object):
    def __init__(self):
        self.fish_dimension = 50
        self.region_dimension = 100
        self.region_settings_list = [[0 for i in range(self.region_dimension)] for j in range(self.fish_dimension)]

        self.channel_group_name = "Channel"
        self.channel_order_list = []

        self.directory = "G:\\"

        self.num_images = 0
        self.time_points_boolean = False
        self.time_points_interval = 0
        self.num_time_points = 1

        self.lightsheet_mode_boolean = False

    def update_region_settings_list(self, region_settings, fish_num, region_num):
        self.region_settings_list[fish_num][region_num] = region_settings
    
    def remove_region_settings(self, fish_num, region_num):
        """
        First, removes index from region_settings_list. If there exists an element of
        region_settings_list with the same fish_num index as the removed region but a
        higher region_num index, it moves down to replace the removed region. It
        wouldn't make sense for there to be a region 2 without a region 1, for example.

        If the region removed was the only region in the list with its fish_num index
        AND there exists a region at a greater fish_num than the removed region, the
        fish_num index of all the regions with a higher index than the region removed
        gets lowered by one. This is to prevent there from being a set of regions with
        fish_num = 1 when there aren't even any regions with fish_num = 0, for example.
        """

        self.region_settings_list[fish_num][region_num] = 0

        found_boolean = False
        for region_index in range(0, self.region_dimension-1):
            if self.region_settings_list[fish_num][region_index] != 0:
                found_boolean = True
                if region_index > region_num:
                    self.region_settings_list[fish_num][region_index-1] = self.region_settings_list[fish_num][region_index]
                    self.region_settings_list[fish_num][region_index] = 0
        if self.region_settings_list[fish_num + 1][0] != 0 and not found_boolean:
            self.region_settings_list[fish_num:self.fish_dimension] = self.region_settings_list[fish_num+1:self.fish_dimension+1]
            self.region_settings_list[self.fish_dimension] = [0] * self.region_dimension


class RegionSettings(object):
    def __init__(self):
        self.x_position = 0
        self.y_position = 0
        self.z_position = 0
        
        self.z_stack_boolean = False
        self.z_start_position = 0
        self.z_end_position = 0
        self.step_size = 1
        self.z_stack_channel_list = []

        self.snap_boolean = False
        self.snap_exposure_time = 20
        self.snap_channel_list = []
        
        self.video_boolean = False
        self.video_duration_in_seconds = 5
        self.video_exposure_time = 20
        self.video_channel_list = []
