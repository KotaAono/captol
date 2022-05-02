# Captol
Captol is a python-based GUI application for reconstructing screen-shared documents.

## Demo
<img src="https://user-images.githubusercontent.com/88641432/165248360-bf9e38e5-f1cb-44e5-a033-441989d16e34.png" height=300><img src="https://user-images.githubusercontent.com/88641432/165248729-9b462d20-0496-46ce-816a-f98e8e9165e8.png" height=300>

### Extract (left)
1. Select a folder to save screenshots.
2. Select an area to clip. You can edit areas from right buttons. <br>
"Edit" -> "Direct Draw" allows you to specify an area by dragging.
3. Set the clip area.
4. Screenshot! "Auto" mode detects screen switching and automatically takes screenshots.

### Merge (right)
1. Select images to be converted to pdf.
2. Click to Convert!
3. Select pdf to set password.
4. Enter password and clic "Lock" or "Unlock".

## Installation
* Captol
```
pip install git+https://github.com/blue-no/captol.git
```

* QPDF: https://github.com/qpdf/qpdf<br>
This is required when converting images to pdf. Install it and make a path.

## Usage
* Start with CLI. "-d" or "--devel-mode" option allows you to start in developer mode.
```
python -m captol
```
* Start with GUI<br>
You can create shortcuts by executing the following command. After that you can click on the shortcut icon to launch this app.
```
python -m captol --create-shortcut
```

## Requirement
* Windows 10
* Python 3.6+
* img2pdf
* OpenCV-Python 4.0+
* Pillow 8.3
* ttkbootstrap 1.7
