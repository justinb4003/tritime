#i!/usr/bin/env python3

# TODO: Finish settings dialog next

import os
import wx
import sys
import wx.adv
import json
import time
import requests
import wx.grid as wxgrid
import lib.tritime as libtt
import lib.trireport as libtr
import lib.libazure as libaz

from version import VERSION
from lib.libazure import TriTimeEvent
from functools import wraps
from io import BytesIO
from threading import Thread, Timer
from datetime import datetime

# Create a custom event type for debounced events
wxEVT_DEBOUNCED_TEXT = wx.NewEventType()
EVT_DEBOUNCED_TEXT = wx.PyEventBinder(wxEVT_DEBOUNCED_TEXT, 1)


_app_settings: dict[str, any] = {}


def default_app_settings() -> dict[str, any]:
    return {
        'allow_all_out': True,
        'show_active_badges': True,
        'auto_out_time': '20:30',
        'pay_period_days': 14,
    }


def modifies_settings(func):
    @wraps
    def wrapper(*args, **kwargs):
        func(*args, **kwargs)
        store_app_settings()
    return wrapper


def debounce(wait_time):
    """
    Decorator that will debounce a function for the specified amount of time.
    If the decorated function is called multiple times, only the last call
    will be executed after the wait_time has elapsed.
    """
    def decorator(fn):
        timer = None

        @wraps(fn)
        def debounced(*args, **kwargs):
            nonlocal timer

            if timer is not None:
                timer.cancel()

            timer = Timer(wait_time, lambda: fn(*args, **kwargs))
            timer.start()

        return debounced
    return decorator

def system_id() -> str:
    return os.environ.get('SYSTEM_ID', '')


def get_app_settings():
    try:
        with open('app_settings.json', 'r') as f:
            obj = json.loads(f.read())
    except json.decoder.JSONDecodeError:
        obj = None
    except FileNotFoundError:
        obj = None
    return obj


def store_app_settings():
    json_str = json.dumps(_app_settings)
    with open('app_settings.json', 'w') as f:
        f.write(json_str)


def is_json(myjson):
    try:
        json.loads(myjson)
    except ValueError:
        return False
    return True


# If we have a URL (http:// or https://), download the image from the URL
def download_image(url, width=64, height=64):
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
            image.LoadFile('unknown_badge.png', wx.BITMAP_TYPE_PNG)
            valid_image = False
    except:  # noqa
        image.LoadFile('unknown_badge.png', wx.BITMAP_TYPE_PNG)
        valid_image = False
    return image, valid_image

class DebouncedTextEvent(wx.PyCommandEvent):
    """Custom event for debounced text changes"""
    def __init__(self, event_type, id, text=""):
        super().__init__(event_type, id)
        self._text = text

    def GetText(self):
        return self._text

class DebouncedTextCtrl(wx.TextCtrl):
    """
    A TextCtrl subclass that provides debounced text change events.
    Regular EVT_TEXT events fire immediately, while EVT_DEBOUNCED_TEXT
    events fire after the specified delay with no intermediate input.
    """
    def __init__(self, parent, id=wx.ID_ANY, value="", delay=0.5, *args, **kwargs):
        super().__init__(parent, id, value, *args, **kwargs)
        self.delay = delay
        self._timer = None

        # Bind to the regular text event
        self.Bind(wx.EVT_TEXT, self._on_text)

    def _on_text(self, event):
        """Handle the text change event with debouncing"""
        # Cancel any pending timer
        if self._timer is not None:
            self._timer.cancel()

        # Create new timer for delayed event
        self._timer = Timer(self.delay, self._fire_debounced_event)
        self._timer.start()

        # Allow the regular event to propagate
        event.Skip()

    def _fire_debounced_event(self):
        """Fire the custom debounced event"""
        evt = DebouncedTextEvent(wxEVT_DEBOUNCED_TEXT, self.GetId(), self.GetValue())
        evt.SetEventObject(self)
        wx.PostEvent(self, evt)


class MainWindow(wx.Frame):

    def return_focus(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            self.badge_num_input.SetFocus()
            return result
        return wrapper

    # Set up the main window for the application; this is where most controls
    # get laid out.
    def __init__(self, parent, id):
        sysid = system_id()
        wx.Frame.__init__(self, parent, id,
                          f'TriTime ({sysid}) v{VERSION}', size=(1024, 800))
        if hasattr(sys, 'frozen'):
            self.Maximize(True)
        bni_style = wx.TE_PROCESS_ENTER | wx.TE_MULTILINE
        self.badge_num_input = DebouncedTextCtrl(self, -1, '',
                                                 delay=0.2,
                                                 style=bni_style)
        self.badge_num_input.Bind(EVT_DEBOUNCED_TEXT, self.on_badge_num_change)
        self.badge_num_input.Bind(wx.EVT_TEXT_ENTER, self.on_badge_num_enter)
        self.badge_clear_btn = wx.Button(self, label='Clear', size=(80, 100))
        self.badge_clear_btn.Bind(wx.EVT_BUTTON, self.clear_badge_input)
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
        self.check_time.Bind(wx.EVT_BUTTON, self.check_time_dialog)

        self.add_user_btn = wx.Button(self, label='Add User', size=btn_size)
        self.add_user_btn.Bind(wx.EVT_BUTTON, self.add_user)
        self.find_user_btn = wx.Button(self, label='Search', size=btn_size)
        self.find_user_btn.Bind(wx.EVT_BUTTON, self.find_user)
        self.punch_all_out_btn = wx.Button(self, label='Punch All Out!',
                                           size=btn_size)
        self.punch_all_out_btn.Bind(wx.EVT_BUTTON, self.punch_all_out)
        self.punch_all_out_btn.Hide()

        self.edit_settings_btn = wx.Button(self, label='Settings...',
                                           size=btn_size)
        self.edit_settings_btn.Bind(wx.EVT_BUTTON, self.edit_settings)

        # Disable all of the buttons; they will enable when a valid badge is
        # entered.
        for b in [self.in_btn, self.out_btn]:
            b.Disable()

        if _app_settings['allow_all_out'] is False:
            self.punch_all_out_btn.Disable()

        # Create a grid that lets us show everybody punched in
        self.active_badge_sizer = wx.WrapSizer(wx.HORIZONTAL)
        self.badge_scroller = wx.ScrolledWindow(self)
        self.badge_scroller.Bind(wx.EVT_LEFT_DOWN, self.on_panel_click)
        self.badge_scroller.SetScrollRate(10, 10)
        self.badge_scroller.SetMinSize((600, 300))
        self.badge_scroller.SetSizer(self.active_badge_sizer)

        spacer_size = 20
        # This lets us put a space to the left of everything by putting our
        # other boxes in a horizontal box witha spacer at the beginning.
        outerhbox = wx.BoxSizer(wx.HORIZONTAL)
        vbox_buttons = wx.BoxSizer(wx.VERTICAL)

        hbox_inout = wx.BoxSizer(wx.HORIZONTAL)
        hbox_inout.Add(self.in_btn)
        hbox_inout.AddSpacer(spacer_size)
        hbox_inout.Add(self.out_btn)
        hbox_inout.AddSpacer(spacer_size)
        hbox_inout.Add(self.check_time)
        hbox_inout.AddSpacer(spacer_size)

        hbox_usermanage = wx.BoxSizer(wx.HORIZONTAL)
        hbox_usermanage.Add(self.add_user_btn)
        hbox_usermanage.AddSpacer(spacer_size)
        hbox_usermanage.Add(self.find_user_btn)
        hbox_usermanage.AddSpacer(spacer_size)
        hbox_usermanage.Add(self.punch_all_out_btn)
        hbox_usermanage.AddSpacer(spacer_size)

        hbox_system = wx.BoxSizer(wx.HORIZONTAL)
        hbox_system.Add(self.edit_settings_btn)
        hbox_system.AddSpacer(spacer_size)

        vbox_buttons.Add(hbox_inout)
        vbox_buttons.AddSpacer(spacer_size)
        vbox_buttons.Add(hbox_usermanage)
        vbox_buttons.AddSpacer(spacer_size)
        vbox_buttons.Add(hbox_system)
        vbox_buttons.AddSpacer(spacer_size)

        hbox_top = wx.BoxSizer(wx.HORIZONTAL)
        hbox_top.Add(self.clock_display)
        hbox_top.AddStretchSpacer(20)
        hbox_top.Add(self.export_btn)


        hbox_buttons_checkgrid = wx.BoxSizer(wx.HORIZONTAL)
        hbox_buttons_checkgrid.Add(vbox_buttons)
        hbox_buttons_checkgrid.Add(self.badge_scroller, 1, wx.EXPAND)

        hbox_badgde_input = wx.BoxSizer(wx.HORIZONTAL)
        hbox_badgde_input.Add(self.badge_num_input, 1, wx.EXPAND)
        hbox_badgde_input.AddSpacer(spacer_size)
        hbox_badgde_input.Add(self.badge_clear_btn)

        vbox.AddSpacer(spacer_size)
        vbox.Add(hbox_top, 0, wx.EXPAND)
        vbox.AddSpacer(spacer_size)
        vbox.Add(hbox_badgde_input, 1, wx.EXPAND)
        vbox.AddSpacer(spacer_size)
        vbox.Add(self.greeting_label, 0, wx.EXPAND)
        vbox.AddSpacer(spacer_size)
        vbox.Add(hbox_buttons_checkgrid, 2, wx.EXPAND)
        vbox.AddSpacer(spacer_size)

        # TODO: Add check time grid back somewhere

        outerhbox.AddSpacer(spacer_size)
        outerhbox.Add(vbox, 1, wx.EXPAND)
        outerhbox.AddSpacer(spacer_size)
        self.outerhbox = outerhbox
        # Add sizer to panel
        self.SetSizerAndFit(outerhbox)
        self.Layout()
        self.Update()

        self.Bind(wx.EVT_CLOSE, self.on_app_shutdown)
        self.clock_thread_run = True
        self.clock_thread = Thread(target=self.update_clock)
        self.clock_thread.start()

        self.update_active_badges()
        self.badge_num_input.SetFocus()
        self.Bind(wx.EVT_LEFT_DOWN, self.on_panel_click)

    @return_focus
    def on_panel_click(self, event):
        return

    def on_app_shutdown(self, event):
        self.shutdown()

    def shutdown(self):
        if azure_enabled():
            libaz.stop()
        self.clock_thread_run = False
        self.clock_thread.join()
        self.Destroy()

    @return_focus
    def export_data(self, event):
        # Configure file dialog options
        wildcard = (
            "Excel files (*.xlsx)|*.xlsx|"
            "CSV files (*.csv)|*.csv|"
            "Parquet files (*.parquet)|*.parquet"
        )

        # Default directory and filename for export
        dialog = wx.FileDialog(
            self, message="Export data",
            defaultDir="",
            defaultFile="export.xlsx",
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )

        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            # Get the chosen filename and path
            filepath = dialog.GetPath()
            wx.MessageBox(f"File chosen: {filepath}", "Export Complete")
        dialog.Destroy()
        libtr.export_to_excel(filepath)

    def update_clock(self):
        while self.clock_thread_run:
            time.sleep(0.1)
            current_time = time.strftime("%I:%M:%S %p")
            curr_hour = datetime.now().hour
            curr_mins = datetime.now().minute
            # Use wx.CallAfter to update the StaticText in the main thread
            wx.CallAfter(self.clock_display.SetLabel, current_time)
            notused = """
            auto_out_time = _app_settings.get('auto_out_time', None)
            if auto_out_time is not None:
                out_hour, out_min = map(int, auto_out_time.split(':'))
                if out_hour > curr_hour and out_min > curr_mins:
                    self.punch_all_out(None)
            """

    # Remove all of the active badges from the grid; this was easier than
    # trying to remove the one-by-one.
    def clear_active_badges(self):
        self.active_badge_sizer.Clear(True)
        self.Layout()
        self.Update()

    # Draw every punched in badge on the grid with a button to punch them out
    def update_active_badges(self):
        self.Freeze()
        self.clear_active_badges()
        if _app_settings['show_active_badges'] is False:
            return
        badges = libtt.get_badges()
        # Sort by the display name
        badges = dict(sorted(badges.items(), key=lambda x: x[1]['display_name']))
        for bnum, badge in badges.items():
            if badge['status'] == 'in':
                self.add_badge_to_grid(bnum)
        self.Thaw()

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
            img = wx.Image()
            img.LoadFile('unknown_badge.png', wx.BITMAP_TYPE_PNG)
        img = wx.Bitmap(img)
        bmp = wx.StaticBitmap(parent, -1, img)
        vbox = wx.BoxSizer(wx.VERTICAL)
        btn = wx.Button(parent, label=badge_name, size=(-1, 80))
        btn.Bind(wx.EVT_BUTTON, lambda event: bind_method(event, badge_num))
        vbox.Add(bmp, flag=wx.CENTER)
        vbox.AddSpacer(10)
        vbox.Add(btn, flag=wx.CENTER)
        return vbox

    # Draws an individual badge on the grid with a button to punch them out
    def add_badge_to_grid(self, badge_num):
        vbox = self.create_badge_card(badge_num,
                                        self.badge_scroller,
                                        self.punch_out)
        self.active_badge_sizer.Add(vbox, 0, wx.ALL, border=10)
        self.Layout()
        self.Update()

    # Reset the badge number input and set the focus back to it
    def clear_input(self):
        self.badge_num_input.SetValue('')
        self.in_btn.Disable()
        self.out_btn.Disable()
        self.badge_num_input.SetFocus()

    # Users can be identified by more than one code; this method will look up
    # the "real" badge number if an alternate is entered.
    def lookup_alt(self, badges, badge_num):
        for real_badge_num, badge in badges.items():
            if 'alt_keys' not in badge:
                continue
            if badge_num in badge['alt_keys']:
                return real_badge_num
        return badge_num

    @return_focus
    def clear_badge_input(self, event):
        self.badge_num_input.SetValue('')

    # This method fires whenever the badge number input changes; it will
    # update the greeting label and enable/disable the buttons as needed.
    def on_badge_num_change(self, event):
        self.in_btn.Disable()
        self.out_btn.Disable()
        badge_num = self.get_entered_badge(
            badge=event.GetString().strip()
        )
        badges = libtt.get_badges()
        valid_badges = badges.keys()
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
        else:
            self.greeting_label.SetLabel(
                'Scan badge'
            )

    # If the 'Enter' key is pressed in the badge input box this method fires
    # We'll use this to punch in or out the badge depending on what the status
    # of their badge is. Usually. We also use this to permit the app to
    # reconfigure itself with JSON entered into the badge input.
    # The use case there is putting the JSON data into a QR code that can
    # reconfig the whole system in a jiffy!
    @return_focus
    def on_badge_num_enter(self, event, badge_num=None):
        print('enter event handler hit')
        if badge_num is None:
            badge_num = self.get_entered_badge()

        if badge_num == 'quit':
            self.shutdown()

        if badge_num == 'fixbadges':
            libtt.fix_badges()
            return

        if badge_num == 'publishdata':
            if azure_enabled():
                libaz.publish_data()

        if badge_num == 'debug':
            import wx.lib.inspection
            wx.lib.inspection.InspectionTool().Show()
            return

        # if is_json(badge_num):
        if False:  # We can skip this for now.
            print(f' this is json: {badge_num}')
            # Process as an app_settings.json config
            global _app_settings
            _app_settings = json.loads(badge_num)
            store_app_settings()
            return

        # Otherwise we'll just handle it like a badge input
        badges = libtt.get_badges()
        valid_badges = badges.keys()
        if badge_num in valid_badges:
            badge_data = badges[badge_num]
            if badge_data['status'] == 'in':
                self.punch_out(event)
            elif badge_data['status'] == 'out':
                self.punch_in(event)

    def get_entered_badge(self, badge=None) -> str:
        if badge is None:
            badge = self.badge_num_input.GetValue()
        badge = badge.strip()
        badge = self.lookup_alt(libtt.get_badges(), badge)
        return badge

    # Buttons to punch in will call this method; we pass off all the data
    # manipulation to the libtt module.
    @return_focus
    def punch_in(self, event):
        badge = self.get_entered_badge()
        dt = datetime.now()
        badges = libtt.punch_in(badge, dt)
        if azure_enabled():
            msg = TriTimeEvent(
                system_id=system_id(),
                badge_num=badge,
                event_type='punch_in',
                ts=dt,
                details={}
            )
            libaz.message_queue.put(msg)
        libtt.store_badges(badges)
        self.add_badge_to_grid(badge)
        self.clear_input()

    # Buttons to punch out will call this method; we pass off all the data
    # manipulation to the libtt module.
    @return_focus
    def punch_out(self, event, badge_num=None):
        badge_num = self.get_entered_badge(badge_num) if badge_num is None else badge_num
        bni = self.badge_num_input
        badge = bni.GetValue() if badge_num is None else badge_num
        badge = self.lookup_alt(libtt.get_badges(), badge)
        dt = datetime.now()
        badges = libtt.punch_out(badge, dt)
        libtt.store_badges(badges)
        libtt.tabulate_badge(badge)
        if azure_enabled():
            msg = TriTimeEvent(
                system_id=system_id(),
                badge_num=badge_num,
                event_type='punch_out',
                ts=dt,
                details={}
            )
            libaz.message_queue.put(msg)
        self.update_active_badges()
        self.clear_input()

    # Adds up all of the time a badge has been punched in.
    @return_focus
    def check_time_dialog(self, event):
        # Create a dialog that has inputs for a badge number, display name,
        # and photo URL.  When the dialog is submitted, add the user to the
        # database and update the active badges grid.
        def badge_change(event):
            badge = event.GetString().strip()
            badge = self.lookup_alt(libtt.get_badges(), badge)
            # Create a grid
            punch_data = libtt.read_punches(badge)
            punch_data.reverse()
            curr_rows = check_time_grid.GetNumberRows()
            new_rows = len(punch_data) + 1
            if new_rows > curr_rows:
                check_time_grid.AppendRows(new_rows-curr_rows)
            elif new_rows < curr_rows:
                check_time_grid.DeleteRows(new_rows, curr_rows-new_rows)

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
                check_time_grid.SetCellValue(row_index+1, 0, instr)
                check_time_grid.SetCellValue(row_index+1, 1, outstr)
                check_time_grid.SetCellValue(row_index+1, 2, duration)

            check_time_grid.SetCellValue(0, 2,
                                        str(round(total_duration/3600, 2)))

            check_time_grid.Show()
            check_time_grid.Layout()
            check_time_grid.Update()
            check_time_grid.AutoSize()
            checktime_dlg.SetSizerAndFit(vbox)
            checktime_dlg.Layout()
            checktime_dlg.Update()


        checktime_dlg = wx.Dialog(self, title='Checking Time...')
        check_time_grid = wxgrid.Grid(checktime_dlg)
        check_time_grid.CreateGrid(0, 3)
        # Set the column labels
        check_time_grid.SetColLabelValue(0, 'Time In')
        check_time_grid.SetColLabelValue(1, 'Time Out')
        check_time_grid.SetColLabelValue(2, 'Hours')
        check_time_grid.HideRowLabels()

        main_app_badge = self.get_entered_badge()
        badge_input = wx.TextCtrl(checktime_dlg, size=(200, -1))
        badge_input.Bind(wx.EVT_TEXT, badge_change)
        submit_btn = wx.Button(checktime_dlg, label='Close',
                               size=(80, 80))
        submit_btn.Bind(wx.EVT_BUTTON,
                        lambda event: checktime_dlg.EndModal(True))
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(20)
        vbox.Add(badge_input)
        vbox.AddSpacer(20)
        vbox.Add(check_time_grid, flag=wx.EXPAND)
        vbox.AddSpacer(20)
        vbox.Add(submit_btn)

        badge_input.SetValue(main_app_badge)


        # Fit the grid to the size of the window
        checktime_dlg.SetSizerAndFit(vbox)
        checktime_dlg.Layout()
        checktime_dlg.Update()

        checktime_dlg.ShowModal()
        checktime_dlg.Destroy()
        return

    @return_focus
    def add_user(self, event):
        # Create a dialog that has inputs for a badge number, display name,
        # and photo URL.  When the dialog is submitted, add the user to the
        # database and update the active badges grid.
        self.settings_dlg = wx.Dialog(self, title='Add User')
        badge_num_label = wx.StaticText(self.settings_dlg,
                                        label='Badge Number')
        badge_num_input = wx.TextCtrl(self.settings_dlg, size=(200, -1))
        display_name_label = wx.StaticText(self.settings_dlg,
                                           label='Display Name')
        display_name_input = wx.TextCtrl(self.settings_dlg, size=(200, -1))
        photo_url_label = wx.StaticText(self.settings_dlg,
                                        label='Photo URL')
        photo_url_input = wx.TextCtrl(self.settings_dlg, size=(400, -1))
        submit_btn = wx.Button(self.settings_dlg, label='Save and Close',
                               size=(120, 80))
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
        self.settings_dlg.SetSizerAndFit(vbox)
        self.settings_dlg.Layout()
        self.settings_dlg.Update()
        self.settings_dlg.ShowModal()
        self.settings_dlg.Destroy()

    def submit_user(self, event, badge_num_input, display_name_input,
                    photo_url_input):
        badge_num = self.get_entered_badge()
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
        libtt.create_user(badge_num, display_name, photo_url)
        self.settings_dlg.EndModal(True)

    def set_badge_input(self, event, badge_num):
        self.badge_num_input.ChangeValue(badge_num)
        self.badge_num_input.SetFocus()
        self.find_user_dlg.EndModal(True)
        # If we want to auto-punch after people are selected
        # in the search window we want to execute this.
        if True:
            evt = wx.CommandEvent(wx.EVT_TEXT_ENTER.typeId)
            evt.SetEventObject(self.badge_num_input)
            wx.PostEvent(self.badge_num_input, evt)

    def update_find_user_search(self, search_text):
        matches = {}
        self.find_user_badge_sizer.Clear(True)
        for num, b in self.find_user_badges.items():
            if search_text in b['display_name'].lower():
                matches[num] = b
                vbox = self.create_badge_card(num,
                                              self.scrolled_window,
                                              self.set_badge_input)
                self.find_user_badge_sizer.Add(vbox, 0, wx.ALL, border=10)
        self.find_user_dlg.Fit()
        self.find_user_dlg.Layout()
        self.find_user_dlg.Update()

    def find_user_input_change(self, event):
        search_text = event.GetString().lower()
        self.update_find_user_search(search_text)

    @return_focus
    def find_user(self, event):
        self.update_active_badges()
        badges = libtt.get_badges()
        badges = dict(sorted(badges.items(), key=lambda x: x[1]['display_name']))
        self.find_user_badges = badges
        if len(self.find_user_badges) == 0:
            wx.MessageBox('There are no users in the system.',
                          'Error', wx.OK | wx.ICON_ERROR)
            return
        self.find_user_dlg = wx.Dialog(self, title='Find User')

        search_input = wx.TextCtrl(self.find_user_dlg, size=(200, -1))
        search_input.Bind(wx.EVT_TEXT, self.find_user_input_change)
        self.scrolled_window = wx.ScrolledWindow(self.find_user_dlg)
        self.scrolled_window.SetScrollRate(10, 10)
        self.scrolled_window.SetMinSize((800, 600))
        self.find_user_badge_sizer = wx.WrapSizer(wx.HORIZONTAL)
        self.scrolled_window.SetSizer(self.find_user_badge_sizer)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.SetMinSize((600, -1))
        vbox.AddSpacer(20)
        vbox.Add(search_input)
        vbox.AddSpacer(20)
        vbox.Add(self.scrolled_window, flag=wx.EXPAND, border=10)
        vbox.AddSpacer(20)
        self.update_find_user_search('')
        self.find_user_dlg.SetSizerAndFit(vbox)
        self.find_user_dlg.Layout()
        self.find_user_dlg.Update()
        self.find_user_dlg.ShowModal()
        self.find_user_dlg.Destroy()

    @return_focus
    def punch_all_out(self, event):
        for badge_num, badge in libtt.get_badges().items():
            if badge['status'] == 'in':
                self.punch_out(None, badge_num)

    def add_azure_settings(self, dlg, vbox, spacer_size, keys, vfuncs):
        # create text inputs for machine name, system name, and endpoint then
        # add them to the fbox with a spacer_sized's spacer between them.
        machine_name_label = wx.StaticText(dlg, label='Machine Name')
        machine_name_input = wx.TextCtrl(dlg, size=(200, -1))
        system_name_label = wx.StaticText(dlg, label='System Name')
        system_name_input = wx.TextCtrl(dlg, size=(200, -1))
        endpoint_label = wx.StaticText(dlg, label='Endpoint')
        endpoint_input = wx.TextCtrl(dlg, size=(400, -1))
        keys.extend(['machine_name', 'system_name', 'endpoint'])
        vfuncs.extend([
            machine_name_input.GetValue,
            system_name_input.GetValue,
            endpoint_input.GetValue,
        ])
        vbox.Add(machine_name_label)
        vbox.Add(machine_name_input)
        vbox.AddSpacer(spacer_size)
        vbox.Add(system_name_label)
        vbox.Add(system_name_input)
        vbox.AddSpacer(spacer_size)
        vbox.Add(endpoint_label)
        vbox.Add(endpoint_input)
        vbox.AddSpacer(spacer_size)

    def submit_settings(self, event, keys: list, vfuncs: list):
        for k, v in zip(keys, vfuncs):
            _app_settings[k] = v()
        store_app_settings()
        self.settings_dlg.EndModal(True)

    @return_focus
    def edit_settings(self, event):
        self.settings_dlg = wx.Dialog(self, title='System Settings')
        allow_all_out_chk = wx.CheckBox(self.settings_dlg,
                                        label='Allow All Out')
        allow_all_out_chk.SetValue(_app_settings['allow_all_out'])
        show_active_badges_chk = wx.CheckBox(self.settings_dlg,
                                             label='Show Active Users')

        show_active_badges_chk.SetValue(_app_settings['show_active_badges'])

        auto_out_time_val = _app_settings['auto_out_time']
        auto_out_chk = wx.CheckBox(
            self.settings_dlg,
            label='Auto Punch Out'
        )
        auto_out_chk.SetValue(auto_out_time_val is not None)
        auto_out_time = wx.adv.TimePickerCtrl(self.settings_dlg)
        if auto_out_time_val is not None:
            auto_out_time.SetValue(
                datetime.strptime(auto_out_time_val, '%H:%M')
            )

        auto_out_chk.Bind(wx.EVT_CHECKBOX,
                          lambda event: auto_out_time.Enable(event.IsChecked()))
        submit_btn = wx.Button(self.settings_dlg, label='Submit',
                               size=(80, 80))
        # I'm not thrilled with this completely untyped way of doing this, but
        # it's a quick way to get the settings dialog working.
        keys = ['allow_all_out',
                'show_active_badges',
                'auto_out_time']
        # This is a list of functions that we'll call to get the values of the
        # controls in the dialog.
        control_values = [
            allow_all_out_chk.GetValue,
            show_active_badges_chk.GetValue,
            lambda: (auto_out_time.GetValue()
                                  .Format('%H:%M')
                     if auto_out_chk.IsChecked() else None),
        ]

        badges = libtt.get_badges()
        pic_download_gauge = wx.Gauge(self.settings_dlg, range=len(badges))
        download_status = wx.StaticText(self.settings_dlg, label='')
        cache_clear_btn = wx.Button(self.settings_dlg, label='Update Image Cache', size=(160, 100))
        cache_clear_btn.Bind(wx.EVT_BUTTON,
                             lambda event: self.update_image_cache(event,
                                                                   pic_download_gauge,
                                                                   download_status))

        spacer_size = 20
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(spacer_size)
        vbox.Add(cache_clear_btn)
        vbox.AddSpacer(spacer_size)
        vbox.Add(download_status)
        vbox.AddSpacer(5)
        vbox.Add(pic_download_gauge)
        vbox.AddSpacer(spacer_size)
        vbox.Add(allow_all_out_chk)
        vbox.AddSpacer(spacer_size)
        vbox.Add(show_active_badges_chk)
        vbox.AddSpacer(spacer_size)
        vbox.Add(auto_out_chk)
        vbox.AddSpacer(spacer_size)
        vbox.Add(auto_out_time)
        vbox.AddSpacer(spacer_size)

        auto_out_time.Enable(event.IsChecked())
        # Add extra settings here
        self.add_azure_settings(self.settings_dlg, vbox, spacer_size,
                                keys, control_values)
        # END Extra settings

        vbox.Add(submit_btn)
        vbox.AddSpacer(spacer_size)
        submit_btn.Bind(wx.EVT_BUTTON,
                        lambda event: self.submit_settings(event,
                                                           keys,
                                                           control_values))
        self.settings_dlg.SetSizerAndFit(vbox)
        self.settings_dlg.Layout()
        self.settings_dlg.Update()
        self.settings_dlg.ShowModal()
        self.settings_dlg.Destroy()

    def update_image_cache(self, event, gauge, status):
        import shutil
        shutil.rmtree('cached_photos')
        os.makedirs('cached_photos')
        self.download_all_images(gauge, status)

    def download_all_images(self, gauge: wx.Gauge, status: wx.StaticText):
        badges = libtt.get_badges()
        status.SetLabel(f'0 of {len(badges)} images downloaded')
        for idx, (badge_num, badge) in enumerate(badges.items()):
            time.sleep(0.1)
            img_url = badge['photo_url']
            img, should_cache = download_image(img_url)
            if should_cache:
                if not os.path.exists('cached_photos'):
                    os.makedirs('cached_photos')
                img.SaveFile(f'cached_photos/{badge_num}.png',
                             wx.BITMAP_TYPE_PNG)
            gauge.SetValue(idx)
            status.SetLabel(f'{idx+1} of {len(badges)} images downloaded')
            wx.Yield()
        return



def azure_enabled() -> bool:
    v = os.environ.get('AZURE_ENABLED', 'false')
    return v.lower() == 'true'

def azure_message_handler(frame: MainWindow, message: TriTimeEvent) -> None:
    # message: TriTimeEvent = TriTimeEvent.from_dict(payload)
    update_badges = False
    if message.event_type == 'punch_in':
        badges = libtt.punch_in(message.badge_num, message.ts)
        libtt.store_badges(badges)
        update_badges = True
    elif message.event_type == 'punch_out':
        badges = libtt.punch_out(message.badge_num, message.ts)
        libtt.store_badges(badges)
        libtt.tabulate_badge(message.badge_num)
        update_badges = True
    elif message.event_type == 'badges_sync':
        badge_data = message.details
        libtt.store_badges(badge_data)
        update_badges = True
    elif message.event_type == 'punch_data_sync':
        badge_num = message.badge_num
        punch_data = message.details
        libtt.write_punches(badge_num, punch_data)
    if update_badges:
        wx.CallAfter(frame.update_active_badges)

# Here's how we fire up the wxPython app
if __name__ == '__main__':
    import sys
    if hasattr(sys, 'frozen'):
        import pyi_splash
        pyi_splash.close()
    _app_settings = get_app_settings()
    if _app_settings is None:
        _app_settings = default_app_settings()
        store_app_settings()
    app = wx.App()
    frame = MainWindow(parent=None, id=-1)
    if azure_enabled():
        libaz.start(lambda payload: azure_message_handler(frame, payload))
    frame.Show()
    app.MainLoop()
