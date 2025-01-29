import os
import json
import libcamera
import cv2
import asyncio
from picamera2 import Picamera2
import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from functools import wraps
import subprocess
import time

with open("config.json", 'r') as f:
    config = json.load(f)

"""RESTRICT USERS"""
def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in config["RESTRICTED_USERS"]:
            print(f"Unauthorized access: {user_id}.")
            return
        return func(update, context, *args, **kwargs)
    return wrapped

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Global flag to control thread execution
picam2 = None
run_thread = None
motion_detect_mode = False
snapshot_mode = False
start_flag = asyncio.Event()
start_flag.clear()

@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global picam2, run_thread, start_flag
    if picam2 is None:
        picam2 = Picamera2()
        picam2_config = picam2.create_still_configuration(main={"size": (1640, 1232)})
        picam2_config["transform"] = libcamera.Transform(hflip=config["HFLIP"], vflip=config["VFLIP"])
        picam2.configure(picam2_config)
        picam2.start()

    if not start_flag.is_set():
        start_flag.set()  # Reset the exit flag
        run_thread = asyncio.create_task(picam_process(context, update.message.chat_id))
        text = "Pi camera started"
    else:
        text = "Pi camera already started."
    await context.bot.send_message(chat_id=update.message.chat_id, text=text, parse_mode=ParseMode.HTML)

@restricted    
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global picam2, start_flag, run_thread
    start_flag.clear()  # Signal the thread to exit
    if run_thread:
        await run_thread  # Wait for the thread to finish
        run_thread = None
    if picam2:
        picam2.stop()
        picam2 = None
    text = "Pi camera stopped."
    await context.bot.send_message(chat_id=update.message.chat_id, text=text, parse_mode=ParseMode.HTML)

@restricted
async def reboot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        subprocess.call('sudo reboot now', shell=True)
    except Exception as e:
        await context.bot.send_message(chat_id=update.message.chat_id, text=str(e), parse_mode=ParseMode.HTML)
        
@restricted
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not run_thread:
        status = "<b>Pi camera not yet started</b>"
    else:
        status = "<b>Pi camera Started</b>"
    
    text = """
    <b>Pi Camera Commands</b> 
<i>/start</i>: start pi camera
<i>/stop</i>: stop pi camera
<i>/snapshot</i>: snapshot
<i>/start_motion_detect</i>: start motion detect
<i>/stop_motion_detect</i>: stop motion detect
<i>/reboot</i>: reboot rpi
"""
    chat_id = update.message.chat_id
    await context.bot.send_message(chat_id=chat_id, text=status+text, parse_mode=ParseMode.HTML)                                                           
    await context.bot.send_message(chat_id=chat_id, text='/start')
    await context.bot.send_message(chat_id=chat_id, text='/stop')
    await context.bot.send_message(chat_id=chat_id, text='/snapshot')
    await context.bot.send_message(chat_id=chat_id, text='/start_motion_detect')
    await context.bot.send_message(chat_id=chat_id, text='/stop_motion_detect')
    await context.bot.send_message(chat_id=chat_id, text='/reboot')

async def picam_process(context, chat_id):
    global picam2, start_flag, motion_detect_mode, snapshot_mode
    send_enable = True
    fgbg = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=16, detectShadows=False)
    min_contour_area = config["MIN_CONTOUR_AREA"]
    
    output_video = 'output_video.mp4'  # Define output video path
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(output_video, fourcc, 10, (410, 308))
    start_recording = False
    expected_video_frames = 0
    no_motion_counter = 0

    counter = 0
    while start_flag.is_set():
        try:
            counter = (counter + 1) % 18000
            if counter == 0:
                picam2.set_controls({"AeEnable": True, "AeMeterMode": "center"})
            frame = picam2.capture_array()
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            frame_small = cv2.resize(frame_bgr, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
            fgmask = fgbg.apply(frame_small)
            _, fgmask_thresh = cv2.threshold(fgmask, 128, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(fgmask_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if snapshot_mode:
                cv2.imwrite("frame.jpg", frame_bgr)
                await context.bot.send_photo(chat_id=chat_id, photo="frame.jpg")
                snapshot_mode = False

            if motion_detect_mode:
                motion_detected = False
                for contour in contours:
                    if cv2.contourArea(contour) > min_contour_area:
                        await context.bot.send_message(chat_id=chat_id, text=f"contour: {cv2.contourArea(contour)}")
                        cv2.imwrite("frame.jpg", frame_bgr)
                        motion_detected = True
                        start_recording = True
                        expected_video_frames = 0
                current_time = time.time()
                
                if send_enable:
                    if motion_detected:
                        await context.bot.send_photo(chat_id=chat_id, photo="frame.jpg")
                        last_capture_time = time.time()
                        send_enable = False
                else:
                    current_time = time.time()
                    if (current_time - last_capture_time) >= config["SEND_INTERVAL"]:
                        send_enable = True

                if start_recording:
                    video_writer.write(frame_small)
                    expected_video_frames +=1
                    if motion_detected:
                        no_motion_counter = 0
                    else:
                        if no_motion_counter < 50:
                            no_motion_counter += 1
                        else:
                            start_recording = False
                            if expected_video_frames > 100: # ~ 10sec
                                await context.bot.send_message(chat_id=chat_id, text='Processing video to send')
                                video_writer.release()
                                await context.bot.send_video(chat_id=chat_id,video=output_video)
                                video_writer = cv2.VideoWriter(output_video, fourcc, 10, (410, 308))            
        except Exception as e:
            print(f"Error: {e}")
            
        await asyncio.sleep(0.1)  # Asynchronous sleep, allowing other tasks to run

@restricted    
async def start_motion_detect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global motion_detect_mode
    if not run_thread:
        text = "<b> Pi camera has not started!</b>"
    else:
        motion_detect_mode = True
        text="Start motion detection"
    await context.bot.send_message(chat_id=update.message.chat_id, text=text, parse_mode=ParseMode.HTML)

@restricted    
async def stop_motion_detect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global motion_detect_mode
    text = ""
    if run_thread:
        motion_detect_mode = False
        text="Stop motion detection"
    await context.bot.send_message(chat_id=update.message.chat_id, text=text, parse_mode=ParseMode.HTML)

@restricted    
async def snapshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global snapshot_mode
    if not run_thread:
        text = "<b> Pi camera has not started!</b>"
    else:
        snapshot_mode = True
        text="Taking snapshot"
    await context.bot.send_message(chat_id=update.message.chat_id, text=text, parse_mode=ParseMode.HTML)


if __name__ == '__main__':
    """Run bot."""
    application = Application.builder().token(config["TOKEN"]).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("snapshot", snapshot))
    application.add_handler(CommandHandler("start_motion_detect", start_motion_detect))
    application.add_handler(CommandHandler("stop_motion_detect", stop_motion_detect))
    application.add_handler(CommandHandler("reboot", reboot))
    application.run_polling(allowed_updates=Update.ALL_TYPES)
