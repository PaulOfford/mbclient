# MbClient

## Introduction

We must start by defining the term "microblogging".  Microblogging is the creation and sharing of small pieces of information (known as posts) using computers.  On this occasion, the computers involved communicate over the air waves using an Amateur Radio data mode called JS8.

In this microblogging world, one computer acts as a blog server that sends the posts to one or more clients.  To do this, the server runs an application called MbServer. There can be multiple blog servers providing different blogs.

MbClient provides a simple way to requests posts an MbServer.  Important features are:

* Point and click access to blogs and posts for easy use
* Caching of posts so that you can get once but read at any time
* Scanning for blog servers, so you can easily discover those operating within radio reach

## YouTube Videos

Here are some YouTube videos you might find useful:

* Microblogging Playlist - https://www.youtube.com/playlist?list=PLSTO76Gp9qydUZA8euqe7O9Fd_O0U8yST
* The original concept from Julian OH8STN - https://youtu.be/szZlPL2h534
* Offgrid Microblogging by The Tech Prepper; live demonstration of microblogging while operating portable - https://youtu.be/Dr56Y-BgNUE

## Off Grid
Although you will need Internet access to install MbClient, once that's done the application can operate completely off grid.  The User Guide is part of the installation package and so is always available.

## Prerequisites
MbClient requires very little to run.  It needs:

* A computer with one of the following**:
  * Windows 10 or later
  * Linux
  * macOS
* JS8Call version 2.2 or later
* Python 3.9 or later

** The build and test environment is Windows 11 and the default settings are set for this environment.  It hasn't been tested on Linux or macOS but it should work.

MbClient only uses modules included in the Python Standard Library, and so we don't need to install additional modules.

## Install and Run on Windows
The full installation instructions are in the User Guide, which is part of the MbClient zip package:

* Browse to https://github.com/PaulOfford/mbclient
* Click on the green Code button
* Choose __Download ZIP__
* Once the zip file download completes, extract the `mbclient-main` file to a location of your choice e.g. `C:\Users\_your_userid_\MyApps`
* Open a Command Prompt window and navigate to the mbclient-main directory
* Check that you have Python installed with the command `python3 -V`
  * You need Python 3.9 or later
* Check that the tkinter module is installed by running the command `python3 -m tkinter`
  * You should get a small widget pop-up with a Click and Quit button
* If you don't have tkinter installed, install it with:
`sudo apt install python3-tk`
* After installation, test again with `python3 -m tkinter`
* Start MbClient with `.\mbclient.bat`

## Install and Run on Linux
These instructions are based on installing and running MbClient on Linux Mint Cinnamon 22.3:

* Browse to https://github.com/PaulOfford/mbclient
* Click on the green Code button
* Choose __Download ZIP__
* Once the zip file download completes, extract the `mbclient-main` file to a location of your choice e.g. `/home/_your_userid_/MyApps`
* Open a terminal window and navigate to the mbclient-main directory
* Check that you have Python installed with the command `python3 -V`
  * You need Python 3.9 or later
* Check that the tkinter module is installed by running the command `python3 -m tkinter`
  * You should get a small widget pop-up with a Click and Quit button
* If you don't have tkinter installed, install it with:
`sudo apt install python3-tk`
* After installation, test again with `python3 -m tkinter`
* Navigate to the `mbclient-main\mbclient`
* Edit `db_root.py` with a text editor and change the database path to a suitable loacation, e.g. `db_path = '/home/_your_userid_/'`
* Start MbClient with `python3 run_mbclient.py`

## User Guide
Once MbClient is installed, you can view the User Guide at any time like this:

* Start MbClient
* Click on Help in the top menu
* Choose User Guide

