#!/bin/env python
import json
import os
import shutil
import glob
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

dir_upload = 'upload'
dir_uploaded = 'uploaded'
os.makedirs(dir_upload, exist_ok=True)
os.makedirs(dir_uploaded, exist_ok=True)

VIDEO_EXT = '.webm'
VIDEO_EXT_LEN = len(VIDEO_EXT)
THUMB_EXT = '.webp'
DESC_EXT = '.description'
with open('tags') as f:
    TAGS = f.readline().strip()

with open('auth') as f:
    login = f.readline().strip()
    password = f.readline().strip()

time_1s = 1000          # 1 seconds
time_1m = time_1s * 60  # 1 minute
page_try_wait_time = time_1s * 3
page_wait_login = time_1s * 3
wait_between_upload_seconds = 60 * 5

usr_state = 'state.json'
should_authenticate = False

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--start-maximized'])
    # browser = p.chromium.connect_over_cdp('http://localhost:9222')
    
    if os.path.exists(usr_state):
        print('Credentials found')
        with open(usr_state) as f:
            state = json.load(f)
            auth_token = next((c for c in state['cookies'] if c['name'] == 'auth_token'), None)
            if not auth_token:
                print('Auth token not found')
                should_authenticate = True
            else:
                expires = auth_token['expires']
                if datetime.fromtimestamp(expires) < datetime.now():
                    print('Auth token expired')
                    should_authenticate = True
    else:
        print('Credentials not found')
        should_authenticate = True
        
    if should_authenticate:
        page = browser.new_page()
        print('Logging in to odysee')
        page.goto('https://odysee.com/$/signin')
        page.fill('input#username', login)
        page.click('button[type=submit]')
        page.fill('input#password', password)
        page.click('button[type=submit]')
        
        page.wait_for_timeout(page_wait_login)
        print('Logged in. Saving credentials')
        browser.contexts[0].storage_state(path=usr_state)
        page.close()

    files_list = sorted(glob.glob(os.path.join(dir_upload, f'*{VIDEO_EXT}')), reverse=True)
    last_file = files_list[-1]
    
    for video_file_abs_path in files_list:
        base_dir = os.path.dirname(video_file_abs_path)
        video_file = os.path.basename(video_file_abs_path)
        datetime_upload = datetime.fromtimestamp(int(video_file[:10]))
        base_name = video_file[:-VIDEO_EXT_LEN]
        thumb_file_abs_path = os.path.join(base_dir,base_name + THUMB_EXT)

        description_abs_path = os.path.join(base_dir, base_name + DESC_EXT)
        with open(description_abs_path, 'r') as file:
            description = file.read()

        print(f'Found: {base_name}')
        print('│ Go to uploading')
        context = browser.new_context(storage_state=usr_state,
                                  viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        page.goto('https://odysee.com/$/upload', timeout=0) # open upload
        page.wait_for_load_state('domcontentloaded')
        
        print('│ Uploading video file')
        # Upload video file
        file_input = page.locator('#main-content > div > section input[type="file"]')
        file_input.set_input_files(video_file_abs_path)
        
        print('│ Filling in metadata:')
        print('│  title, ', end='')
        # fill in title
        page.locator('input[name="content_title"]').fill(base_name[11:])
        video_title_fixed = page.locator('input[name="content_name"]').input_value()[11:]
        page.locator('input[name="content_name"]').fill(video_title_fixed)
        
        print('description, ', end='')
        # fill in description
        page.locator('textarea[id="content_description"]').fill(description)
        
        print('thumbnail, ', end='')
        # upload thumbnail
        file_input = page.locator('#main-content > div > div > section input[type="file"]')
        file_input.set_input_files(thumb_file_abs_path)
        page.locator('div.ReactModalPortal button.button--primary').click()
        
        print('tags')
        # fill in tags
        page.locator('input.tag__input').fill(TAGS)
        page.keyboard.press('Enter')
        
        # fill in publish date
        for _ in range(5):
            try:
                page.locator('div.react-datetime-picker__inputGroup').locator('input[name="year"]').click(timeout=page_try_wait_time)
                print('│ Filling in publish date')
                page.keyboard.type(f"{datetime_upload.year:04}")
                page.keyboard.type(f"{datetime_upload.month:02}")
                page.keyboard.type(f"{datetime_upload.day:02}")
                page.keyboard.type(f"{datetime_upload.hour:02}")
                page.keyboard.type(f"{datetime_upload.minute:02}")
                break
            except Exception:
                print('│ Expanding "show more" - trying to click')
                page.keyboard.down('End')
                show_more_btn = page.locator('#main-content > div > div > section.card--enable-overflow') \
                                    .locator('div.publish-row.publish-row--more > button.button--link')
                show_more_btn.click()
        else:
            raise Exception('Failed to fill in publish date')
        
        print('│ Publishing')
        page.keyboard.down('End')
        page.locator('div.publish__actions button.button--primary').click() # publish button
        page.locator('div.ReactModalPortal button.button--primary').click() # accept
        
        print('│ Waiting for video to be uploaded...')
        # wait for video to be uploaded for eternity
        page.wait_for_selector('div.ReactModalPortal button.button--primary', timeout=0)

        print('│ Uploading complete. Saving to uploaded')
        # save to uploaded
        shutil.move(video_file_abs_path, dir_uploaded)
        shutil.move(thumb_file_abs_path, dir_uploaded)
        shutil.move(description_abs_path, dir_uploaded)
        print('╘═Done═╛')
        
        page.close()
        context.close()
        
        if video_file_abs_path != last_file:
            print(f'Waiting {wait_between_upload_seconds // 60} minutes...')
            time.sleep(wait_between_upload_seconds)