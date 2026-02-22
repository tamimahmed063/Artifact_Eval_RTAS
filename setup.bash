#!/bin/bash

conda create -n ae_79 python=3.12.12 -y

source $(conda info --base)/etc/profile.d/conda.sh
conda activate ae_79

pip install -r requirements.txt

sudo mkdir -p /usr/share/fonts/truetype/arial
sudo wget -q -O /usr/share/fonts/truetype/arial/arial.ttf "https://github.com/matomo-org/travis-scripts/raw/master/fonts/Arial.ttf"
sudo wget -q -O /usr/share/fonts/truetype/arial/arialbd.ttf "https://github.com/matomo-org/travis-scripts/raw/master/fonts/Arial_Bold.ttf"
sudo wget -q -O /usr/share/fonts/truetype/arial/ariali.ttf "https://github.com/matomo-org/travis-scripts/raw/master/fonts/Arial_Italic.ttf"
sudo wget -q -O /usr/share/fonts/truetype/arial/arialbi.ttf "https://github.com/matomo-org/travis-scripts/raw/master/fonts/Arial_Bold_Italic.ttf"
sudo fc-cache -f -v

rm -rf ~/.cache/matplotlib

alias python=python3