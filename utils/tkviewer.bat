@echo off
chcp 65001
echo Activate conda
call C:\Users\hnlPublic\anaconda3\Scripts\activate.bat C:\Users\hnlPublic\anaconda3\envs\appdev38
echo Launch viewer
C:/Users/hnlPublic/anaconda3/envs/appdev38/python.exe ^
C:/Users/hnlPublic/Desktop/その他/MyApps/captol/tkviewer.py ^
C:/Users/hnlPublic/Desktop/その他/MyApps/captol/uitk.py
