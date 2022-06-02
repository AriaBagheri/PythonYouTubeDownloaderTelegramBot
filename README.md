---
title: PythonYouTubeDownloaderTelegramBot
---

I always struggled to find bots on telegram to download large YouTube videos as the upload-limit for telegram bots is 50MB. 
Here I used one of my own libraries [python-ufile](https://github.com/AriaBagheri/python_ufile) to increase this limit to 5GB which should be more than enough to download most of the videos found on YouTube. 
Enjoy! 

Note: Links generated with this bot will expire after 30 days!

- Free software: MIT license
- Documentation: 
  - Download the project from GitHub (git clone https://github.com/AriaBagheri/PythonYouTubeDownloaderTelegramBot.git)
  - Install the dependencies (pip install -r requirements) 
  - Make a telegram bot in @BotFather (Refer to this [guide](https://core.telegram.org/bots#6-botfather))
  - put the obtained API token in .env file next to main.py
  - run main.py 
  - and text /start to your telegram bot
  - Enjoy!

# Features

Downloads YouTube videos as audio file
Downloads YouTube videos with any quality without the 50 MB limit! (Limits at 5GB because of ufile.io!)

# Credits

This package was coded in it\'s entirety by Aria Bagheri. But you can always contribute if you want! Just fork the project, have a go at it, and then submit a pull request!
Special thanks to ufile.io for providing free hosting of files. And to myself for coding the python-ufile library :)
