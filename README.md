# MbClient

## Introduction

We must start by defining the term "microblogging".  Microblogging is the creation and sharing of small pieces of information (known as posts) using computers.  On this occasion, the computers involved communicate over the air waves using an Amateur Radio data mode called JS8.

In this microblogging world, one computer acts as a blog server that sends the posts to one or more clients.  To do this, the server runs an application called MbServer. There can be multiple blog servers providing different blogs.

MbClient provides a simple way to requests posts an MbServer.  Important features are:

* Point and click access to blogs and posts for easy use
* Caching of posts so that you can get once but read at any time
* Scanning for blog servers, so you can easily discover those operating within radio reach

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

## Install and Run
The full installation instructions are in the User Guide, which is part of the MbClient zip package:

* Browse to https://github.com/PaulOfford/mbclient
* Click on the green Code button
* Choose __Download ZIP__
* Once the zip file download completes, extract it to a location of your choice
* Using File Explorer in Windows, or the equivalent in other operating systems, navigate to the folder where you extracted the zip to and then to the `docs` folder
* Double-click on UserGuide.html
* Go to the Installing and Running MbClient in the guide
* Follow the instructions there

## User Guide
Once MbClient is installed, you can view the User Guide at any time like this:

* Start MbClient
* Click on Help in the top menu
* Choose User Guide

