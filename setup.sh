#!/bin/bash

# Copyright (c) 2024, Vince Thongam 
# All rights reserved.

# This source code is licensed under the GPL-3.0 license found in the
# LICENSE file in the root directory of this source tree.
# If you don't have the source tree alternately this file can be found at <https://github.com/Vincenzo675/termux-sriparna>

yes no | pkg update -y 
yes no | pkg upgrade -y 
yes no | pkg install termux-api -y

# Workaround to check for Termux Api App Installation 
if timeout 5 termux-api-start&&termux-toast "Working ..."; then
        :
else
        echo "Termux API app is not installed."
        # Open F-Droid link
        termux-open-url "https://f-droid.org/packages/com.termux.api/"       
        exit 1
fi

# List of packages to install
packages=("termux-api" "python" "openssl" "libexpat" "ffmpeg" "flac" "dialog")

# Hack to bypass dpkg lock
yes no | dpkg --configure -a 

install_package() {
    # Hack pass default 'N' to userinput
    yes no | pkg install -y $1
}

for pkg in "${packages[@]}"; do
    echo "Installing $pkg..."
    install_package "$pkg"
done

# Termux:Widget implementation 
echo 
echo "Creating shortcut widgets ..."
echo
mkdir -p ~/.termux/widget/dynamic_shortcuts
mkdir -p /data/data/com.termux/files/home/.shortcuts
chmod 700 -R /data/data/com.termux/files/home/.shortcuts
echo "sriparna" > /data/data/com.termux/files/home/.shortcuts/Sriparna
echo "sriparna-gui" > /data/data/com.termux/files/home/.shortcuts/Sriparna-Gui
chmod +x /data/data/com.termux/files/home/.shortcuts/Sriparna
chmod +x /data/data/com.termux/files/home/.shortcuts/Sriparna-Gui
mkdir -p /data/data/com.termux/files/home/.shortcuts/icons
chmod -R a-x,u=rwX,go-rwx /data/data/com.termux/files/home/.shortcuts/icons
cp logo.png /data/data/com.termux/files/home/.shortcuts/icons/Sriparna.png
cp logo.png /data/data/com.termux/files/home/.shortcuts/icons/Sriparna-Gui.png
cp /data/data/com.termux/files/home/.shortcuts/Sriparna ~/.termux/widget/dynamic_shortcuts
cp /data/data/com.termux/files/home/.shortcuts/Sriparna-Gui ~/.termux/widget/dynamic_shortcuts
echo
echo -e "Shortcut widget is created!\nLong click on Termux:Widget app and select Termux shortcut\nThere you will get two scripts, drag them to your homescreen\nYou can directly run these scripts by clicking on them !"
echo
echo "Setup script is successful !"
echo 
sleep 5
