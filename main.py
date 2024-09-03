#!/usr/bin/env python3
# Using flake8 for linting
import os
import wx
import requests
import wx.grid as wxgrid
import lib.tritime as libtt

from io import BytesIO
from datetime import datetime


# If we have a URL (http:// or https://), download the image from the URL
def download_image(self, url, width=64, height=64):
    response = requests.get(url)
    try:
        response.raise_for_status()  # Ensure the request was successful

        # Convert the image data into a wx.Bitmap
        image_data = BytesIO(response.content)
        image = wx.Image(image_data).Scale(width, height,
                                           wx.IMAGE_QUALITY_HIGH)
        valid_image = True
    except:  # noqa -- doesn't matter the error -- just return a default image
        print('Using unknown image')
        image = wx.Image()
        image.LoadFile('unknown_badge.png', wx.BITMAP_TYPE_PNG)
        valid_image = False
    return image, valid_image


class MainWindow(wx.Frame):

    # Set up the main window for the application; this is where most controls
    # get laid out.
    def __init__(self, parent, id):
        wx.Frame.__init__(self, parent, id,
                          'TriTime', size=(1024, 800))
        self.badge_num_input = wx.TextCtrl(self, -1, '',
                                           size=(300, -1),
                                           style=wx.TE_PROCESS_ENTER)
        self.badge_num_input.Bind(wx.EVT_TEXT, self.on_badge_num_change)
        self.badge_num_input.Bind(wx.EVT_TEXT_ENTER, self.on_badge_num_enter)
        self.greeting_label = wx.StaticText(self, -1, 'Welcome to TriTime')

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.in_btn = wx.Button(self, label='In')
        self.in_btn.Bind(wx.EVT_BUTTON, self.punch_in)
        self.out_btn = wx.Button(self, label='Out')
        self.out_btn.Bind(wx.EVT_BUTTON, self.punch_out)
        self.check_time = wx.Button(self, label='Check Time')
        self.check_time.Bind(wx.EVT_BUTTON, self.check_time_total)

        self.add_user_btn = wx.Button(self, label='Add User')
        self.add_user_btn.Bind(wx.EVT_BUTTON, self.add_user)
        self.find_user_btn = wx.Button(self, label='Search')
        self.find_user_btn.Bind(wx.EVT_BUTTON, self.find_user)

        self.check_time_grid = wxgrid.Grid(self)
        self.check_time_grid.CreateGrid(0, 3)
        # Set the column labels
        self.check_time_grid.SetColLabelValue(0, "Time In")
        self.check_time_grid.SetColLabelValue(1, "Time Out")
        self.check_time_grid.SetColLabelValue(2, "Hours")
        self.check_time_grid.HideRowLabels()

        # Disable all of the buttons; they will enable when a valid badge is
        # entered.
        for b in [self.in_btn, self.out_btn, self.check_time]:
            b.Disable()

        # Create a grid that lets us show everybody punched in
        self.active_badge_sizer = wx.GridSizer(4, 20, 10)

        spacer = wx.SizerItem(20, 20)

        # This lets us put a space to the left of everything by putting our
        # other boxes in a horizontal box witha spacer at the beginning.
        outerhbox = wx.BoxSizer(wx.HORIZONTAL)

        hbox_inout = wx.BoxSizer(wx.HORIZONTAL)
        hbox_inout.Add(self.in_btn)
        hbox_inout.Add(spacer)
        hbox_inout.Add(self.out_btn)
        hbox_inout.Add(spacer)
        hbox_inout.Add(self.check_time)
        hbox_inout.Add(spacer)
        hbox_inout.Add(self.active_badge_sizer, flag=wx.EXPAND)
        hbox_inout.Add(spacer)

        hbox_usermanage = wx.BoxSizer(wx.HORIZONTAL)
        hbox_usermanage.Add(self.add_user_btn)
        hbox_usermanage.Add(spacer)
        hbox_usermanage.Add(self.find_user_btn)
        hbox_usermanage.Add(spacer)

        vbox.Add(spacer)
        vbox.Add(self.badge_num_input)
        vbox.Add(spacer)
        vbox.Add(self.greeting_label, 0, wx.EXPAND)
        vbox.Add(spacer)
        vbox.Add(hbox_inout)
        vbox.Add(spacer)
        vbox.Add(hbox_usermanage)
        vbox.Add(spacer)
        vbox.Add(self.check_time_grid, wx.EXPAND)
        vbox.Add(spacer)

        outerhbox.Add(spacer)
        outerhbox.Add(vbox)
        # Add sizer to panel
        self.SetSizer(outerhbox)
        self.Layout()
        self.Update()

        self.update_active_badges()

    # Remove all of the active badges from the grid; this was easier than
    # trying to remove the one-by-one.
    def clear_active_badges(self):
        self.active_badge_sizer.Clear(True)
        self.Layout()
        self.Update()

    # Draw every punched in badge on the grid with a button to punch them out
    def update_active_badges(self):
        self.clear_active_badges()
        badges = libtt.get_badges()
        for bnum, badge in badges.items():
            if badge['status'] == 'in':
                self.add_badge_to_grid(bnum)

    # Draws an individual badge on the grid with a button to punch them out
    def add_badge_to_grid(self, badge_num):
        badges = libtt.get_badges()
        badge = badges[badge_num]
        badge_name = badge['display_name']
        cached_image_filename = f'cached_photos/{badge_num}.png'
        # If we already have a file downloaded (cached) for this badge just
        # use that.
        if os.path.exists(cached_image_filename):
            img = wx.Image()
            img.LoadFile(cached_image_filename, wx.BITMAP_TYPE_PNG)
        # Otherwise we can download the image from the URL
        else:
            img_url = badge['photo_url']
            img, should_cache = download_image(self, img_url)
            if should_cache:
                if not os.path.exists('cached_photos'):
                    os.makedirs('cached_photos')
                img.SaveFile(f'cached_photos/{badge_num}.png',
                             wx.BITMAP_TYPE_PNG)
        img = wx.Bitmap(img)
        bmp = wx.StaticBitmap(self, -1, img)
        vbox = wx.BoxSizer(wx.VERTICAL)
        btn = wx.Button(self, label=badge_name)
        btn.Bind(wx.EVT_BUTTON, lambda event: self.punch_out(event, badge_num))
        vbox.Add(bmp, flag=wx.CENTER)
        vbox.Add(btn, flag=wx.CENTER)
        self.active_badge_sizer.Add(vbox)
        self.Layout()
        self.Update()

    # Reset the badge number input and set the focus back to it
    def clear_input(self):
        self.badge_num_input.SetValue('')
        self.badge_num_input.SetFocus()

    # This method fires whenever the badge number input changes; it will
    # update the greeting label and enable/disable the buttons as needed.
    def on_badge_num_change(self, event):
        badge_num = event.GetString()
        badges = libtt.get_badges()
        valid_badges = badges.keys()
        print(f'Badge Number: {badge_num}')
        if badge_num in valid_badges:
            badge_data = badges[badge_num]
            self.greeting_label.SetLabel(
                f'Welcome {badge_data["display_name"]}'
            )
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
            self.in_btn.Disable()
            self.out_btn.Disable()
            self.check_time.Disable()
            self.check_time_grid.Hide()

    # If the 'Enter' key is pressed in the badge input box this method fires
    # We'll use this to punch in or out the badge depending on what the status
    # of their badge is.
    def on_badge_num_enter(self, event):
        badge_num = event.GetString()
        badges = libtt.get_badges()
        valid_badges = badges.keys()
        if badge_num in valid_badges:
            badge_data = badges[badge_num]
            if badge_data['status'] == 'in':
                self.punch_out(event)
            elif badge_data['status'] == 'out':
                self.punch_in(event)

    # Buttons to punch in will call this method; we pass off all the data
    # manipulation to the libtt module.
    def punch_in(self, event):
        badge = self.badge_num_input.GetValue()
        print(f'Punch In {badge}')
        badges = libtt.punch_in(badge, datetime.now())
        libtt.store_badges(badges)
        self.add_badge_to_grid(badge)
        self.clear_input()

    # Buttons to punch out will call this method; we pass off all the data
    # manipulation to the libtt module.
    def punch_out(self, event, badge_num=None):
        bni = self.badge_num_input
        badge = bni.GetValue() if badge_num is None else badge_num
        print(f'Punch Out {badge}')
        badges = libtt.punch_out(badge, datetime.now())
        libtt.store_badges(badges)
        libtt.tabulate_badge(badge)
        self.update_active_badges()
        self.clear_input()

    # Adds up all of the time a badge has been punched in.
    def check_time_total(self, event):
        badge = self.badge_num_input.GetValue()
        print(f'Check Time {badge}')
        # Create a grid
        punch_data = libtt.read_punches(badge)
        punch_data.reverse()
        curr_rows = self.check_time_grid.GetNumberRows()
        new_rows = len(punch_data) + 1
        if new_rows > curr_rows:
            self.check_time_grid.AppendRows(new_rows-curr_rows)
        elif new_rows < curr_rows:
            self.check_time_grid.DeleteRows(new_rows, curr_rows-new_rows)

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
            self.check_time_grid.SetCellValue(row_index+1, 0, instr)
            self.check_time_grid.SetCellValue(row_index+1, 1, outstr)
            self.check_time_grid.SetCellValue(row_index+1, 2, duration)

        self.check_time_grid.SetCellValue(0, 2,
                                          str(round(total_duration/3600, 2)))

        # Fit the grid to the size of the window
        self.check_time_grid.Show()
        self.check_time_grid.Layout()
        self.check_time_grid.Update()
        self.check_time_grid.AutoSize()
        self.Layout()
        self.Update()

    def add_user(self, event):
        print('adding user dialog')
        # Create a dialog that has inputs for a badge number, display name,
        # and photo URL.  When the dialog is submitted, add the user to the
        # database and update the active badges grid.
        spacer = wx.SizerItem(20, 20)
        self.add_user_dlg = wx.Dialog(self, title='Add User')
        badge_num_label = wx.StaticText(self.add_user_dlg,
                                        label='Badge Number')
        badge_num_input = wx.TextCtrl(self.add_user_dlg, size=(200, -1))
        display_name_label = wx.StaticText(self.add_user_dlg,
                                           label='Display Name')
        display_name_input = wx.TextCtrl(self.add_user_dlg, size=(200, -1))
        photo_url_label = wx.StaticText(self.add_user_dlg,
                                        label='Photo URL')
        photo_url_input = wx.TextCtrl(self.add_user_dlg, size=(400, -1))
        submit_btn = wx.Button(self.add_user_dlg, label='Submit')
        submit_btn.Bind(wx.EVT_BUTTON, lambda event: self.submit_user(
            event, badge_num_input, display_name_input, photo_url_input
        ))
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(badge_num_label)
        vbox.Add(badge_num_input)
        vbox.Add(spacer)
        vbox.Add(display_name_label)
        vbox.Add(display_name_input)
        vbox.Add(spacer)
        vbox.Add(photo_url_label)
        vbox.Add(photo_url_input)
        vbox.Add(spacer)
        vbox.Add(submit_btn)
        vbox.Add(spacer)
        self.add_user_dlg.SetSizerAndFit(vbox)
        self.add_user_dlg.Layout()
        self.add_user_dlg.Update()
        self.add_user_dlg.ShowModal()
        # self.add_user_dlg.Destroy()

    def submit_user(self, event, badge_num_input, display_name_input,
                    photo_url_input):
        badge_num = badge_num_input.GetValue()
        display_name = display_name_input.GetValue()
        photo_url = photo_url_input.GetValue()
        # if any of the inputs are empty, don't add the user
        if not all([badge_num, display_name, photo_url]):
            # TODO: Add a dialog that tells the user to fill in all fields
            return
        badges = libtt.get_badges()
        badges[badge_num] = {
            'display_name': display_name,
            'photo_url': photo_url,
            'status': 'out'
        }
        libtt.store_badges(badges)
        self.add_user_dlg.EndModal(True)

    def find_user(self, event):
        print('finding user dialog')


# here's how we fire up the wxPython app
if __name__ == '__main__':
    app = wx.App()
    frame = MainWindow(parent=None, id=-1)
    frame.Show()
    app.MainLoop()
