# Pi Camera Motion Detection with Telegram Integration

This project leverages the Raspberry Pi Camera Module to detect motion using OpenCV and sends captured images or video clips to a Telegram bot when motion is detected. The bot also allows you to control the camera, take snapshots, start and stop motion detection, and reboot the Raspberry Pi.

## Features

- **Motion Detection**: Detect motion in the camera feed and send a snapshot and video clip (if motion persists ~5s or more) to a Telegram chat.
- **Snapshot Mode**: Take a snapshot when requested via a command and send it to Telegram.
- **Camera Control**: Start and stop the Pi camera stream remotely.
- **Reboot**: Reboot the Raspberry Pi using a command.
- **User Authentication**: Restrict access to certain users via Telegram user IDs.

## Requirements

- Raspberry Pi with Pi Camera Module. Tested with Camera Module v2. See https://www.raspberrypi.com/documentation/accessories/camera.html
- Raspberry Pi Bookworm OS installed.

Install picamera2
'''bash
sudo apt install python3-picamera2 --no-install-recommends
'''

Use virtual environment.
python -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt

## Configuration

Create a `config.json` file with the following structure:

```json
{
  "TOKEN": "YOUR_BOT_API_TOKEN",
  "RESTRICTED_USERS": [123456789, 987654321],
  "HFLIP": 1,
  "VFLIP": 0,
  "MIN_CONTOUR_AREA": 5000,
  "SEND_INTERVAL": 5
}
```

- `TOKEN`: The API token for your Telegram bot (you can get it from BotFather).
- `RESTRICTED_USERS`: A list of user IDs allowed to interact with the bot.
- `HFLIP`: Whether to horizontally flip the camera feed (1/0).
- `VFLIP`: Whether to vertically flip the camera feed (1/0).
- `MIN_CONTOUR_AREA`: Minimum contour area for motion detection (adjust based on your environment).
- `SEND_INTERVAL`: Time in seconds between sending photos when motion is detected.

## Usage

### 1. Start the Camera

To start the Pi camera and begin motion detection, use the `/start` command. This will initialize the camera and start capturing frames.

```
/start
```

### 2. Stop the Camera

To stop the camera and end the motion detection, use the `/stop` command.

```
/stop
```

### 3. Take a Snapshot

To take a snapshot, use the `/snapshot` command. The bot will capture the current camera frame and send it to the Telegram chat.

```
/snapshot
```

### 4. Start Motion Detection

To enable motion detection, use the `/start_motion_detect` command. The bot will start monitoring for motion and send a photo when motion is detected.

```
/start_motion_detect
```

### 5. Stop Motion Detection

To disable motion detection, use the `/stop_motion_detect` command.

```
/stop_motion_detect
```

### 6. Reboot the Raspberry Pi
Create a pi_cam.service in /etc/systemd/system/ to run python script upon boot up
sudo systemctl enable pi_cam.service
sudo systemctl start pi_cam.service


To reboot the Raspberry Pi remotely, use the `/reboot` command.
```
/reboot
```

### 7. Help Command

To see a list of all available commands, use the `/help` command.
```
/help
```

## How It Works

### Motion Detection

The program uses OpenCV's background subtraction technique (`cv2.createBackgroundSubtractorMOG2`) to detect motion in the camera feed. When motion is detected, it captures an image and sends it to the configured Telegram chat. Optionally, it records a video if the motion persists.

### Telegram Bot

The Telegram bot listens for commands (e.g., `/start`, `/stop`, `/snapshot`, etc.). Only authorized users (defined in `config.json`) can interact with the bot.

### Camera Control

The Picamera2 library is used to interface with the Raspberry Pi Camera Module. The camera can be configured to capture still images or video, and it supports transformations like horizontal and vertical flipping.

## Example Workflow

1. **Start the Camera**:
   - Send `/start` to the bot. The camera begins capturing frames.

2. **Enable Motion Detection**:
   - Send `/start_motion_detect` to the bot. The bot starts monitoring for motion in the camera feed.

3. **Motion Detected**:
   - When motion is detected, the bot captures an image and sends it to the chat.

4. **Stop Motion Detection**:
   - Send `/stop_motion_detect` to stop the motion detection.

5. **Stop the Camera**:
   - Send `/stop` to stop the camera and release resources.
