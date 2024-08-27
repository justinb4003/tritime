#!/usr/bin/env python3
# Using flake8 for linting
import os
import wx
import requests
import base64
import wx.grid as wxgrid
import lib.tritime as libtt

from io import BytesIO
from datetime import datetime

# TODO: This shold peridoically refresh the badges if we're connected to a
# networked system; ie: backed with a database like CosmosDB.
badges = libtt.get_badges()
active_badges = {}


def download_image(self, url, width=64, height=64):
    response = requests.get(url)
    try:
        response.raise_for_status()  # Ensure the request was successful

        # Convert the image data into a wx.Bitmap
        image_data = BytesIO(response.content)
        image = wx.Image(image_data).Scale(width, height,
                                           wx.IMAGE_QUALITY_HIGH)
        valid_image = True
    except requests.exceptions.RequestException as e:
        print(e)
        image = wx.Image()
        image.LoadFile('unknown_badge.png', wx.BITMAP_TYPE_PNG)
        valid_image = False
    return image, valid_image


class MainWindow(wx.Frame):
    entered_badge = None

    def __init__(self, parent, id):
        wx.Frame.__init__(self, parent, id,
                          'TriTime', size=(1024, 800))
        self.badge_num_input = wx.TextCtrl(self, -1, '',
                                           style=wx.TE_PROCESS_ENTER)
        self.badge_num_input.Bind(wx.EVT_TEXT, self.on_badge_num_change)
        self.badge_num_input.Bind(wx.EVT_TEXT_ENTER, self.on_badge_num_enter)
        self.greeting_label = wx.StaticText(self, -1, 'Welcome to TriTime')

        # Add badge_num_input to a sizer
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.in_btn = wx.Button(self, label='In')
        self.in_btn.Bind(wx.EVT_BUTTON, self.punch_in)
        self.out_btn = wx.Button(self, label='Out')
        self.out_btn.Bind(wx.EVT_BUTTON, self.punch_out)
        self.check_time = wx.Button(self, label='Check Time')
        self.check_time.Bind(wx.EVT_BUTTON, self.check_time_season)
        self.check_time_grid = wxgrid.Grid(self)
        self.check_time_grid.CreateGrid(0, 3)
        # Set the column labels
        self.check_time_grid.SetColLabelValue(0, "Time In")
        self.check_time_grid.SetColLabelValue(1, "Time Out")
        self.check_time_grid.SetColLabelValue(2, "Duration (hrs)")
        self.check_time_grid.HideRowLabels()
        # self.check_time_grid.Hide()
        for b in [self.in_btn, self.out_btn, self.check_time]:
            b.Disable()

        self.active_badge_sizer = wx.GridSizer(4, 20, 10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.in_btn)
        hbox.Add(wx.SizerItem(20, 20))
        hbox.Add(self.out_btn)
        hbox.Add(wx.SizerItem(20, 20))
        hbox.Add(self.check_time)
        hbox.Add(wx.SizerItem(20, 20))
        hbox.Add(self.check_time_grid, wx.EXPAND)
        hbox.Add(wx.SizerItem(20, 20))
        hbox.Add(self.active_badge_sizer, border=10, flag=wx.EXPAND)

        vbox.Add(self.badge_num_input, 0, wx.EXPAND)
        vbox.Add(self.greeting_label, 0, wx.EXPAND)
        vbox.Add(hbox, border=5)
        # Add sizer to panel
        self.SetSizer(vbox)
        self.Layout()
        self.Update()

        self.update_active_badges()

    def clear_active_badges(self):
        print('clearing')
        self.active_badge_sizer.Clear(True)
        self.Layout()
        self.Update()

    def update_active_badges(self):
        self.clear_active_badges()
        for bnum, badge in badges.items():
            if badge['status'] == 'in':
                self.add_badge_to_grid(bnum)

    def clear_input(self):
        self.badge_num_input.SetValue('')
        self.badge_num_input.SetFocus()

    def on_badge_num_change(self, event):
        badge_num = event.GetString()
        valid_badges = badges.keys()
        print(f'Badge Number: {badge_num}')
        if badge_num in valid_badges:
            badge_data = badges[badge_num]
            self.greeting_label.SetLabel(
                f'Welcome {badge_data["display_name"]}'
            )
            self.entered_badge = badge_num
            status = badge_data['status']
            if status != 'in':
                self.in_btn.Enable()
            if status != 'out':
                self.out_btn.Enable()
            self.check_time.Enable()
        else:
            self.greeting_label.SetLabel(
                'Scan badge'
            )
            self.entered_badge = None
            self.in_btn.Disable()
            self.out_btn.Disable()
            self.check_time.Disable()
            self.check_time_grid.Hide()
            """
            gridrows = self.check_time_grid.GetNumberRows()
            if gridrows > 0:
                # Delete all the rows
                self.check_time_grid.DeleteRows(0, gridrows)
            """
            pass

    def on_badge_num_enter(self, event):
        badge_num = event.GetString()
        valid_badges = badges.keys()
        print(f'Badge Number: {badge_num}')
        if badge_num in valid_badges:
            badge_data = badges[badge_num]
            if badge_data['status'] == 'in':
                self.punch_out(event)
            elif badge_data['status'] == 'out':
                self.punch_in(event)

    # TODO: Maybe cache these locally, or offer an 'oops' image if the
    # network connection is down.
    def add_badge_to_grid(self, badge_num):
        badge = badges[badge_num]
        badge_name = badge['display_name']
        cached_image_filename = f'cached_photos/{badge_num}.png'
        if os.path.exists(cached_image_filename):
            img = wx.Image()
            img.LoadFile(cached_image_filename, wx.BITMAP_TYPE_PNG)
        else:
            img_url = badge['photo_url']
            img, should_cache = download_image(self, img_url)
            if should_cache:
                img.SaveFile(f'cached_photos/{badge_num}.png',
                             wx.BITMAP_TYPE_PNG)
        img = wx.Bitmap(img)
        bmp = wx.StaticBitmap(self, -1, img)
        vbox = wx.BoxSizer(wx.VERTICAL)
        btn = wx.Button(self, label=badge_name)
        btn.Bind(wx.EVT_BUTTON, lambda event: self.punch_out(event, badge_num))
        vbox.Add(bmp, flag=wx.CENTER)
        vbox.Add(btn, flag=wx.CENTER)
        active_badges[badge_num] = vbox
        self.active_badge_sizer.Add(vbox)
        self.Layout()
        self.Update()

    # TODO: This is not working; UGH!
    def remove_badge_from_grid(self, badge_num):
        print('removing')
        # Now remove from grid?
        vbox = active_badges[badge_num]
        self.active_badge_sizer.Detach(vbox)
        vbox.Destroy()
        del active_badges[badge_num]
        self.active_badge_sizer.Layout()
        self.Layout()

    def punch_in(self, event):
        global badges
        print(f'Punch In {self.entered_badge}')
        badges = libtt.punch_in(self.entered_badge, datetime.now())
        self.add_badge_to_grid(self.entered_badge)
        self.clear_input()

    def punch_out(self, event, badge_num=None):
        global badges
        badge_num = self.entered_badge if badge_num is None else badge_num
        print(f'Punch Out {badge_num}')
        badges = libtt.punch_out(badge_num, datetime.now())
        libtt.tabulate_badge(badge_num)
        self.update_active_badges()
        self.clear_input()

    def check_time_season(self, event):
        print(f'Check Time {self.entered_badge}')
        # Create a grid
        punch_data = libtt.read_punches(self.entered_badge)
        curr_rows = self.check_time_grid.GetNumberRows()
        new_rows = len(punch_data) + 1
        if new_rows > curr_rows:
            self.check_time_grid.AppendRows(new_rows - curr_rows)
        elif new_rows < curr_rows:
            self.check_time_grid.DeleteRows(new_rows, curr_rows - new_rows)

        # Populate the grid with data
        total_duration = 0
        for row_index, row_data in enumerate(punch_data):
            instr = 'N/A - Error'
            outstr = 'N/A - Error'
            duration = ''
            if 'ts_in' in row_data:
                instr = str(row_data['ts_in'])
            if 'ts_out' in row_data:
                outstr = str(row_data['ts_out'])
            if 'duration' in row_data:
                d = row_data['duration']
                if d is None:
                    d = 0
                total_duration += d
                duration = str(round(d/3600, 2))
            self.check_time_grid.SetCellValue(row_index, 0, instr)
            self.check_time_grid.SetCellValue(row_index, 1, outstr)
            self.check_time_grid.SetCellValue(row_index, 2, duration)

        self.check_time_grid.SetCellValue(new_rows-1, 2,
                                          str(round(total_duration/3600, 2)))

        # Fit the grid to the size of the window
        self.check_time_grid.Show()
        self.check_time_grid.Layout()
        self.check_time_grid.Update()
        self.check_time_grid.AutoSize()
        self.Layout()
        self.Update()


# here's how we fire up the wxPython app
if __name__ == '__main__':
    bdata = libtt.get_badges()
    libtt.store_badges(bdata)
    app = wx.App()
    frame = MainWindow(parent=None, id=-1)
    frame.Show()
    app.MainLoop()
