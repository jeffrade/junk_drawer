#!/bin/bash

set -e

sudo apt update

if [ ! "$(command -v gnome-disks)" ]; then
 sudo apt install gnome-disk-utility
fi

echo "Run gnome-disks if you need to format your sd card"

if [ ! "$(command -v rpi-imager)" ]; then
 sudo apt install rpi-imager
fi

echo "Make sure to enable SSH"

rpi-imager

echo "Now ssh into your raspberry pi:"
echo "'ssh pi@raspberrypi.local'"
echo "Then run the following command to install pi-hole:"
echo "'sudo curl -sSL https://install.pi-hole.net | bash'"
echo "See more at https://github.com/pi-hole/pi-hole/#one-step-automated-install"
