# TriTime

A timeclock app intended for FRC teams.

![image](https://github.com/user-attachments/assets/392d3b41-88d3-40d3-8917-6a61930a9216)

## Overview

Standalone app that can store data locally or use an Azure CosmosDB for
storage.

The idea being a very simple time tracking app suitable for FRC teams built on
technology that's simple, easy, and useful. With that I've chosen Python for the
language and wxWidgets for the GUI toolkit. I find wx especially pleasing to
work with because it renders as a native app on whatever platform you're on, so
if a student is working in Windows their app is a Windows app. If they're on
macOS it's a macOS app. It also operates in a fairly straight forward manner.

## Installation

Releases can be found in this repository in the
[releases](https://github.com/justinb4003/tritime/releases) section. Currently there are builds for Windows x64, Linux md64, and Linux arm64. They're static binaries, so just unpack the ```zip```/```tar.gz``` and run the ```tritime``` or ```tritime.exe``` inside.

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

## CI/CD (Automated builds and releases)

In the ```.github/workflows``` folder are Github Actions definitions that will
build and release the project when checkins occur. Changes comitted to the
```main``` branch will execute a build to verify it hasn't broken. Changes
comitted to the ```release``` branch will execute a build, tag the code with
an automatic version number, and create a Github release.

They  use ```pyinstaller``` to create a single executable that has a Python
interpreter built into it. Currently only Linux amd64, arm64 and Windows x64 builds are
created. It might be possible to do an OS X build but I haven't gotten around to it. I'd also like the arm64 build to be faster; it's like 30 minutes now.
