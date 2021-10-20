@echo off
chcp 65001
echo Activate conda
call C:/Users/hnlPublic/anaconda3/Scripts/activate
echo Activae appdev38 environment
call conda activate appdev38
echo Run application
python C:/Users/hnlPublic/Desktop/その他/MyApps/captol/uitk.py
