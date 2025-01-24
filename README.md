# TriTime

A timeclock app intended for FRC teams.

## Overview

Standalone app that can store data locally, running disconnected, as a complete
timeclock solution for an FRC team.

The idea being a very simple time tracking app suitable for FRC teams built on
technology with a low barrier to entry.

## Installation

Releases can be found in this repository in the
[releases](https://github.com/justinb4003/tritime/releases) section. Currently
there are builds for Windows x64 and Linux amd64. They're static
binaries, so just unpack the ```zip```/```tar.gz``` and run the ```tritime``` or
```tritime.exe``` inside.

## Usage

Every user of the app will have a unique badge number that you assign them.
There's an ```Add User...``` button on the main screen of the app that can be used to input them.

The app does not offer a way to generate them; that's up to you. You could give
everybody a 4 digit number and have them type it in on the keypad, or print out
badges and use a simple USB scanner to scan the number instead of using the
keyboard. Or you can generate a QR code for every user that just contains their
name; or maybe name and some kind of numeric id. It's entirely up to you.
Depending on your school and team setup you might already have a badge with a
barcode on it for every student as part of a student ID.

You can also hack on the ```badges.json``` file directly (this needs to be added
to the UI) and offer more than one code for users. This feature was inspired by
a former student on 4003 turned mentor who always has a 12oz can of Mountain Dew
in reach, so the barcode on that might as well be available to him as a sign in
badge.

Once your users are assigned the general usage is you enter your unique id into the input window and if you hit enter at the end of the input (something you can configure a scanner to do) the default option of In or Out will be activated.

Users are that are in the 'In' status will show up on the screen and tapping their name punches them out. You can also just use the badge input as done for signing in to punch out.

There is an ```Export Data``` button on the main screen to provide a summary of time in the system in an Excel spreadsheet format.

## Development

To create your own development environment you will want to do the following:

### Clone the code

```git clone https://github.com/tritime.git```

### Create a Python virtual environment

```python3 -m venv --system-site-packages venv``` for Linux.

```py -3 -m venv venv``` for Windows.

### Activate your virtual environment

```source venv/bin/activate``` for Linux.

```./venv/Scripts/Activate``` for Windows

### Install dependencies

```pip install -r requirements.txt```

**NOTE:** The wxWidgets package can take a long time to install on some Linux
systems and may require you to install development tools to build it. To avoid
this it may be best to install a distribution produced package (```apt install
python3-wxgtk4.0``` on Debian or Ubuntu for example). This is the reason for
the ```--system-site-pakages``` in the creation of the virtual enviornment.

### Run the app

```python main.py```
