#!/usr/bin/env python3
# Using flake8 for linting
import os
import wx
import time
import pandas as pd
import requests
import wx.grid as wxgrid
import lib.tritime as libtt
import lib.trireport as libtr

from io import BytesIO
from threading import Thread
from datetime import datetime


# If we have a URL (http:// or https://), download the image from the URL
def download_image(self, url, width=64, height=64):
    # This method is a hot mess and needs to be cleaned up.
    image = wx.Image()
    image.LoadFile('unknown_badge.png', wx.BITMAP_TYPE_PNG)
    valid_image = False
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # Convert the image data into a wx.Bitmap
            image_data = BytesIO(response.content)
            image = wx.Image(image_data)
            image = image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
            valid_image = True
        else:
            print('img not ok')
            image.LoadFile('unknown_badge.png', wx.BITMAP_TYPE_PNG)
            valid_image = False
    except:  # noqa
        print('exception loading unknown png')
        image.LoadFile('unknown_badge.png', wx.BITMAP_TYPE_PNG)
        print('exception loaded')
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
        self.export_btn = wx.Button(self, label='Export Data')
        self.export_btn.Bind(wx.EVT_BUTTON, self.export_data)
        self.greeting_label = wx.StaticText(self, -1, 'Welcome to TriTime')
        self.clock_display = wx.StaticText(self, -1, 'HH:mm:ss AP')
        tc = wx.Font(28, wx.FONTFAMILY_TELETYPE,
                     wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.clock_display.SetFont(tc)
        self.badge_num_input.SetFont(tc)

        vbox = wx.BoxSizer(wx.VERTICAL)
        btn_size = (100, 100)
        self.in_btn = wx.Button(self, label='In', size=btn_size)
        self.in_btn.Bind(wx.EVT_BUTTON, self.punch_in)
        self.out_btn = wx.Button(self, label='Out', size=btn_size)
        self.out_btn.Bind(wx.EVT_BUTTON, self.punch_out)
        self.check_time = wx.Button(self, label='Check Time', size=btn_size)
        self.check_time.Bind(wx.EVT_BUTTON, self.check_time_total)

        self.add_user_btn = wx.Button(self, label='Add User', size=btn_size)
        self.add_user_btn.Bind(wx.EVT_BUTTON, self.add_user)
        self.find_user_btn = wx.Button(self, label='Search', size=btn_size)
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

        spacer_size = 20
        # This lets us put a space to the left of everything by putting our
        # other boxes in a horizontal box witha spacer at the beginning.
        outerhbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox_inout = wx.BoxSizer(wx.HORIZONTAL)
        hbox_inout.Add(self.in_btn)
        hbox_inout.AddSpacer(spacer_size)
        hbox_inout.Add(self.out_btn)
        hbox_inout.AddSpacer(spacer_size)
        hbox_inout.Add(self.check_time)
        hbox_inout.AddSpacer(spacer_size)
        hbox_inout.Add(self.active_badge_sizer, flag=wx.EXPAND)
        hbox_inout.AddSpacer(spacer_size)

        hbox_usermanage = wx.BoxSizer(wx.HORIZONTAL)
        hbox_usermanage.Add(self.add_user_btn)
        hbox_usermanage.AddSpacer(spacer_size)
        hbox_usermanage.Add(self.find_user_btn)
        hbox_usermanage.AddSpacer(spacer_size)

        hbox_top = wx.BoxSizer(wx.HORIZONTAL)
        hbox_top.Add(self.clock_display)
        hbox_top.AddStretchSpacer(20)
        hbox_top.Add(self.export_btn)

        vbox.AddSpacer(spacer_size)
        vbox.Add(hbox_top, 1, wx.EXPAND)
        vbox.AddSpacer(spacer_size)
        vbox.Add(self.badge_num_input)
        vbox.AddSpacer(spacer_size)
        vbox.Add(self.greeting_label, 0, wx.EXPAND)
        vbox.AddSpacer(spacer_size)
        vbox.Add(hbox_inout)
        vbox.AddSpacer(spacer_size)
        vbox.Add(hbox_usermanage)
        vbox.AddSpacer(spacer_size)
        vbox.Add(self.check_time_grid, wx.EXPAND)
        vbox.AddSpacer(spacer_size)

        outerhbox.AddSpacer(spacer_size)
        outerhbox.Add(vbox)
        # Add sizer to panel
        self.SetSizer(outerhbox)
        # self.ShowFullScreen(True)
        self.Layout()
        self.Update()
        self.Bind(wx.EVT_KEY_DOWN, self.on_key)

        self.Bind(wx.EVT_CLOSE, self.on_app_shutdown)

        self.clock_thread_run = True
        self.clock_thread = Thread(target=self.update_clock)
        self.clock_thread.start()

        self.update_active_badges()

    def on_app_shutdown(self, event):
        self.clock_thread_run = False
        self.clock_thread.join()
        self.Destroy()

    # TODO: This is a stub for exporting data; it will be implemented later
    def export_data(self, event):
        libtr.export_to_excel()

    def update_clock(self):
        while self.clock_thread_run:
            time.sleep(0.1)
            current_time = time.strftime("%I:%M:%S %p")
            # Use wx.CallAfter to update the StaticText in the main thread
            wx.CallAfter(self.clock_display.SetLabel, current_time)

    def on_key(self, event):
        """
        Check for ESC key press and exit is ESC is pressed
        """
        key_code = event.GetKeyCode()
        print(f'Key Code: {key_code}')
        if key_code == wx.WXK_ESCAPE:
            self.GetParent().Close()
        else:
            event.Skip()

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

    def create_badge_card(self, badge_num, parent=None, bind_method=None):
        parent = self if parent is None else parent
        bind_method = self.punch_out if bind_method is None else bind_method
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
            img, should_cache = download_image(parent, img_url)
            if should_cache:
                if not os.path.exists('cached_photos'):
                    os.makedirs('cached_photos')
                img.SaveFile(f'cached_photos/{badge_num}.png',
                             wx.BITMAP_TYPE_PNG)
        img = wx.Bitmap(img)
        bmp = wx.StaticBitmap(parent, -1, img)
        vbox = wx.BoxSizer(wx.VERTICAL)
        btn = wx.Button(parent, label=badge_name)
        btn.Bind(wx.EVT_BUTTON, lambda event: bind_method(event, badge_num))
        vbox.Add(bmp, flag=wx.CENTER)
        vbox.Add(btn, flag=wx.CENTER)
        return vbox

    # Draws an individual badge on the grid with a button to punch them out
    def add_badge_to_grid(self, badge_num):
        vbox = self.create_badge_card(badge_num)
        self.active_badge_sizer.Add(vbox)
        self.Layout()
        self.Update()

    # Reset the badge number input and set the focus back to it
    def clear_input(self):
        self.badge_num_input.SetValue('')
        self.in_btn.Disable()
        self.out_btn.Disable()
        self.check_time.Disable()
        self.check_time_grid.Hide()
        self.badge_num_input.SetFocus()

    def lookup_alt(self, badges, badge_num):
        for real_badge_num, badge in badges.items():
            if 'alt_keys' not in badge:
                continue
            if badge_num in badge['alt_keys']:
                return real_badge_num
        return badge_num

    # This method fires whenever the badge number input changes; it will
    # update the greeting label and enable/disable the buttons as needed.
    def on_badge_num_change(self, event):
        self.in_btn.Disable()
        self.out_btn.Disable()
        self.check_time.Disable()
        self.check_time_grid.Hide()
        badge_num = event.GetString()
        badges = libtt.get_badges()
        valid_badges = badges.keys()
        badge_num = self.lookup_alt(badges, badge_num)
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
        badge = self.lookup_alt(libtt.get_badges(), badge)
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
        submit_btn = wx.Button(self.add_user_dlg, label='Submit',
                               size=(80, 80))
        submit_btn.Bind(wx.EVT_BUTTON, lambda event: self.submit_user(
            event, badge_num_input, display_name_input, photo_url_input
        ))
        spacer_size = 20
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(badge_num_label)
        vbox.Add(badge_num_input)
        vbox.AddSpacer(spacer_size)
        vbox.Add(display_name_label)
        vbox.Add(display_name_input)
        vbox.AddSpacer(spacer_size)
        vbox.Add(photo_url_label)
        vbox.Add(photo_url_input)
        vbox.AddSpacer(spacer_size)
        vbox.Add(submit_btn)
        vbox.AddSpacer(spacer_size)
        self.add_user_dlg.SetSizerAndFit(vbox)
        self.add_user_dlg.Layout()
        self.add_user_dlg.Update()
        self.add_user_dlg.ShowModal()
        self.add_user_dlg.Destroy()

    def submit_user(self, event, badge_num_input, display_name_input,
                    photo_url_input):
        badge_num = badge_num_input.GetValue()
        display_name = display_name_input.GetValue()
        photo_url = photo_url_input.GetValue()
        # Don't allow submit unless a name and number are in
        if not all([badge_num, display_name]):
            errmsg = 'Please fill in the badge number and display name fields'
            wx.MessageBox(errmsg, 'Error', wx.OK | wx.ICON_ERROR)
            if badge_num == '':
                badge_num_input.SetFocus()
            elif display_name == '':
                display_name_input.SetFocus()
            return
        badges = libtt.get_badges()
        badges[badge_num] = {
            'display_name': display_name,
            'photo_url': photo_url,
            'status': 'out'
        }
        libtt.store_badges(badges)
        self.add_user_dlg.EndModal(True)

    def set_badge_input(self, event, badge_num):
        self.badge_num_input.SetValue(badge_num)
        self.badge_num_input.SetFocus()
        self.find_user_dlg.EndModal(True)

    def find_user_input_change(self, event):
        search_text = event.GetString().lower()
        print(search_text)
        matches = {}
        self.find_user_badge_sizer.Clear(True)
        for num, b in self.find_user_badges.items():
            if search_text in b['display_name'].lower():
                matches[num] = b
                vbox = self.create_badge_card(num,
                                              self.find_user_dlg,
                                              self.set_badge_input)
                self.find_user_badge_sizer.Add(vbox)
        print(matches)
        self.find_user_dlg.Fit()
        self.find_user_dlg.Layout()
        self.find_user_dlg.Update()
        pass

    def find_user(self, event):
        self.find_user_badges = libtt.get_badges()
        self.find_user_dlg = wx.Dialog(self, title='Find User')
        search_input = wx.TextCtrl(self.find_user_dlg, size=(200, -1))
        search_input.Bind(wx.EVT_TEXT, self.find_user_input_change)
        self.find_user_badge_sizer = wx.GridSizer(4, 20, 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(20)
        vbox.Add(search_input)
        vbox.AddSpacer(20)
        vbox.Add(self.find_user_badge_sizer, flag=wx.EXPAND)
        vbox.AddSpacer(20)
        self.find_user_dlg.SetSizerAndFit(vbox)
        self.find_user_dlg.Layout()
        self.find_user_dlg.Update()
        self.find_user_dlg.ShowModal()
        self.find_user_dlg.Destroy()
        del self.find_user_badges
        print('finding user dialog')


# here's how we fire up the wxPython app
if __name__ == '__main__':
    app = wx.App()
    frame = MainWindow(parent=None, id=-1)
    frame.Show()
    app.MainLoop()
