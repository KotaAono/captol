# Captol
Captol is a python-based GUI application for reconstructing screen-sharing documents.

## Demo

### Extract
1. Select a folder to save screenshots.
2. Select an area to clip. You can edit areas from write buttons. <br>
"Edit" -> "Direct Draw" allows you to specify an area by dragging.
3. Set the clip area.
4. Clip! "Auto" mode detects screen switching and automatically takes screenshots

### Merge
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
python -m captol --create-shortcut (or -c)
```

## Environment
* Windows 10