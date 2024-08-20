#!/usr/bin/env python3
# Using flake8 for linting
import wx
import wx.grid as wxgrid

from datetime import date, time, datetime

import lib.tritime as libtt

badges = libtt.get_badges()


class MainWindow(wx.Frame):
    entered_badge = None

    def __init__(self, parent, id):
        wx.Frame.__init__(self, parent, id,
                          'TriTime', size=(1024, 800))
        self.badge_num_input = wx.TextCtrl(self, -1, 'Badge Number')
        self.badge_num_input.Bind(wx.EVT_TEXT, self.on_badge_num_change)
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
        self.check_time_grid.SetColLabelValue(2, "Duration (s)")
        self.check_time_grid.HideRowLabels()
        for b in [self.in_btn, self.out_btn, self.check_time]:
            b.Disable()

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.in_btn)
        hbox.Add(wx.SizerItem(20, 20))
        hbox.Add(self.out_btn)
        hbox.Add(wx.SizerItem(20, 20))
        hbox.Add(self.check_time)
        hbox.Add(wx.SizerItem(20, 20))
        hbox.Add(self.check_time_grid)

        vbox.Add(self.badge_num_input, 0, wx.EXPAND)
        vbox.Add(self.greeting_label, 0, wx.EXPAND)
        vbox.Add(hbox)
        # Add sizer to panel
        self.SetSizer(vbox)
        self.Layout()
        self.Update()

        # Add panel to frame

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
            self.in_btn.Enable()
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
            gridrows = self.check_time_grid.GetNumberRows()
            if gridrows > 0:
                # Delete all the rows
                self.check_time_grid.DeleteRows(0, gridrows)

    def punch_in(self, event):
        print(f'Punch In {self.entered_badge}')
        libtt.punch_in(self.entered_badge, datetime.now())
        self.clear_input()

    def punch_out(self, event):
        print(f'Punch Out {self.entered_badge}')
        libtt.punch_out(self.entered_badge, datetime.now())
        libtt.tabulate_badge(self.entered_badge)
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
            instr = ''
            outstr = ''
            duration = ''
            if 'ts_in' in row_data:
                instr = str(row_data['ts_in'])
            if 'ts_out' in row_data:
                outstr = str(row_data['ts_out'])
            if 'duration' in row_data:
                d = row_data['duration']
                total_duration += d if d is not None else 0
                duration = str(d)
            self.check_time_grid.SetCellValue(row_index, 0, instr)
            self.check_time_grid.SetCellValue(row_index, 1, outstr)
            self.check_time_grid.SetCellValue(row_index, 2, duration)

        self.check_time_grid.SetCellValue(new_rows - 1, 2, str(total_duration))

        # Fit the grid to the size of the window
        self.check_time_grid.Layout()
        self.check_time_grid.Update()
        self.check_time_grid.AutoSize()


# here's how we fire up the wxPython app
if __name__ == '__main__':
    bdata = libtt.get_badges()
    libtt.store_badges(bdata)
    app = wx.App()
    frame = MainWindow(parent=None, id=-1)
    frame.Show()
    app.MainLoop()
