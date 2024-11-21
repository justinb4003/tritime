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
[releases](https://github.com/justinb4003/tritime/releases) section. There are
automated builds created when anything is checked into the ```release```
branch.

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
