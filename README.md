# Welcome to the Server portion of the NG-06 Capstone Project

This repository contains the frontend and backend portion of the server for the NG-06 Capstone Project for TMU. It provides a viewing interface for the user to view frames sent into an object detection model. 

To set up this project on your local machine, follow the steps outlined below.

## Project Setup
### Prerequisites
This project requires the following:
- Python 3.12+
- Node.js 24.13.0+
- OBS
- Vue Extension for VS Code

If you do not have the required dependencies, follow the steps below, otherwise skip to [First Setup](#first-setup).

> Note: The steps below assume you are running Windows.

#### 1. Python Installation
Python can be installed from the official downloads page [here](https://www.python.org/downloads/). Select the appropriate version from the list and follow the instructions on the installer.

#### 2. Node.js Installation
The frontend uses Vue.js as its framework, which requires npm (and Node.js) to run. There are multiple ways to install Node.js, but the easiest is through the Node Version Manager:
 
 > Detailed steps about this process can be found on [Microsoft Learn](https://learn.microsoft.com/en-us/windows/dev-environment/javascript/nodejs-on-windows). The steps below are a summary of this process.

 1. The NVM installer can be found [here](https://github.com/coreybutler/nvm-windows/releases). Follow the steps on the installer to complete the process.
 2. Open up a new Terminal window (CMD Prompt, Powershell, etc.) with administrative permissions.
 3. Enter `nvm install lts` to install the latest long-term-support version of Node.js. Wait for it and its corresponding version of npm to install.
 4. Enter `nvm ls`. You should see your Node.js and npm installations listed- if yes, then the installation was successful.

 #### 3. OBS Installation
 Similar to Python, OBS has an installer found on its website [here](https://cdn-fastly.obsproject.com/downloads/OBS-Studio-32.0.4-Windows-x64-Installer.exe) (this initiates the download of the latest installer for Windows). Follow the steps on the installer to complete the process. 

 #### 4. Vue Extension Installation
 Go to the extension panel on VS Code and look for `Vue (Official)`. The publisher is vue.js.org. Alternatively, you can find the link to the extension [here](https://marketplace.visualstudio.com/items?itemName=Vue.volar). Click install, and you should be good to go. This extension is required for TypeScript to recognize the .vue files in the project.

### First Setup
1. Clone the repository to your intended directory:
```git bash
git clone https://github.com/SK917/drone-anomaly-server.git
```
2. We will setup the backend first. Go to the `server` directory:
```bash
cd server
```
3. Create a virtual environment (venv) to manage the requirements for the project; this ensures that the project remains stable in case different team members have different Python setups.
```bash
python -m venv venv
```
4. Activate the venv:
```bash
venv\Scripts\activate
```
5. Install the required plugins with this command:
```bash
python -m pip install -r requirements.txt
```
6. The backend should now be setup. Now, switch to the `client` directory to setup the frontend:
```bash
deactivate #deactivates the venv
cd ..\client

#Or open a new terminal instance and:
cd client
```
7. Install the required dependencies and plugins by using the following command:
```bash
npm install
```
8. We have finished setup steps for both the frontend and backend, and now we need to configure OBS. Open up the application, then go to `File -> Settings`.

9. Go to the `Stream` tab, and enter this information (leave everything else as is):
```
Service: WHIP
Server: http://127.0.0.1:8000/whip
```
10. Go to the `Output` tab and select `Output Mode: Advanced`. Under the `Stream` suboption:
```
Audio Track: 1
Audio Encoder: FFmpeg Opus
Video Encoder: QuickSync H.264
Rescale Output: Disabled [1280x720]

Rate Control: CBR
Bitrate: 5000 Kbps
Target Usage: TU4 (Medium Quality)
Profile: Main
Keyframe Interval: 0 s
Latency: Normal
B Frames: 0
```
11. Verify your settings match the above, hit `Apply` and then `OK` to close the window. 
> Before continuing, verify that you have an mp4 file containing the correct objects / anomalies on your machine that you can stream to the server.
12. Add a new `Source -> Media Source`. Select your MP4 file. Checking the `Loop` option will make it loop indefinitely if that is needed. After adding the source, resize the window so that it fills your stream's screen.

After completing these steps, you have successfully setup the project! We can now try and run it.

## Running the Project
It is recommended to have two terminal windows active - one for the frontend and one for the backend.

### 1. Run the Backend
1. Navigate to `..\drone-anomaly-server\server`.

2. Activate the venv: `venv\Scripts\activate`

3. Run the server:
```bash
python hybrid_server.py
```
> Note: You may see multiple versions of the server in this repository. The one listed here is the most up-to-date one.

If you are running it for the first time, the server may run some initial setup tasks. When this is done, you will see the server running at http://localhost:8000. It has the following endpoints:

| Endpoint | Description|
|----------|------------|
| /detections | JSON Detections data |
| /stats | Stream stats |
| /annotated-frame.jpg | The latest frame processed by the server
| /whip | OBS Endpoint |
| /video-view | Beta frontend view |
| / | Beta detections list view |

Next, start OBS by clicking the `Start Streaming` button. After this, we can start up the frontend.

### 2. Run the Frontend
1. Navigate to `..\drone-anomaly-server\client`

2. Run the frontend:
```bash
npm run dev
```

The frontend uses the default Vue.js endpoint of http://localhost:5173. Currently, there are no additional endpoints, but we are looking to add some in the future.

If you visit the frontend now, you should be able to see your video streaming, as well as the list of detections picked up by our object detection model.

### Stopping the Project
To shut down the project, simply:
1. Kill the frontend process by using `Ctrl + C` (then select Y to close the process) or close the terminal instance.
2. Stop streaming on OBS by hitting the `Stop Streaming` button.
3. Kill the backend process in a similar way to the frontend (see step 1). If your venv is still activated, enter the `deactivate` command to turn it off.

## Updating the Project
> Whenever the project is updated, if it affects this documentation, the README must be updated.

### Updating the Frontend
Sometimes, new dependencies will be installed on the frontend. To adapt them into your local version, simply do the following:

1. Verify that the frontend isn't running.

2. Run `npm install` to install the new plugins.

3. Run `npm run dev` to start up the site again.

That's it!

### Updating the Backend
Any new dependencies required for the venv must be noted in the `requirements.txt` file for teammates to easily install.

1. Verify that the backend ins't running, and activate your venv by using `venv\Scripts\activate`.

2. Use `pip freeze > requirements.txt` to update the requirements.txt file.

To install new dependencies noted by a team member, make sure the venv is activated and then:
```bash
python -m pip install -r requirements.txt
```

This installs any missing dependencies that are noted in `requirements.txt`.

### Updating OBS Streaming Settings
If there are any changes made to the OBS settings needed to stream to the backend, please make note of them in the README's [First Setup](#first-setup) section, on steps 9 and 10.







