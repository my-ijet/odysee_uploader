# Odysee uploader

# Dependencies 
python, playwright

playwright install chromium

# Usage
Place files in upload directory


file names format: "timestamp(10) [space] Title.ext"
```
"1720184445 Warhammer40K.webm"
"1720184445 Warhammer40K.webp"
"1720184445 Warhammer40K.description"
```
You can change some constants in main.py

"auth" file should contain login and password each at separate line
~~~
LOGIN
PASSSWORD
~~~
"tags" file can contain tags in one line, each separated by comma
~~~
fantasy,space,overcome
~~~

"state.json" file contains auth information