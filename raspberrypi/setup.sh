#!/bin/bash

set -e

sudo apt install rpi-imager

echo "Make sure to enable SSH"

rpi-imager

echo "Now ssh into your raspberry pi:"
echo "'ssh pi@raspberrypi.local'"
echo "Then run the following command to install pi-hole:"
echo "'sudo curl -sSL https://install.pi-hole.net | bash'"
