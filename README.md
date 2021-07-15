# CoWIN Vaccination Slot Autobooking

This is a Python application for automating the vaccine slot booking process on the [CoWIN](https://www.cowin.gov.in/) portal. The main feature that sets it apart from all the other booking scripts is that it doesn't need the user to manually enter the OTP when the auth token expires (every 15 minutes currently).

## Features
* Automated OTP SMS Fetching
* Web server written with [Flask](https://flask.palletsprojects.com)
* Telegram notification support on successful booking
* Clean, well-designed components

## Getting Started
### Requirements
#### 0. Secret token to enable third party usage of CoWIN API
* To be able to actually generate the OTP using your mobile number, the app also needs to access the Protected APIs.
* This needs a **secret token** which is to be obtained from the Govt. See [Registration and Setup Process for Accessing CO-WIN Protectedapis](https://apisetu.gov.in/document-central/cowin/Registration%20and%20Setup%20Process%20for%20Accessing%20CO-WIN%20Protectedapis.html)
* Set this in `auth.secret` key of the config.

#### 1. Externally visible hostname
* You will need a web server with valid domain name (running on something like an AWS/Azure/GCP/etc. VM instance).
* Alternatively, you can use something like [ngrok](https://ngrok.com/) to expose connections from your personal pc to the internet. The Free tier should be enough for this app.

#### 2. SMS Push App
* You can set up any automation app like Tasker, Automate, or Macrodroid to push the OTP SMS to the computer running this app.
* Recommended: Import [CoWIN_OTP_Pusher.macro](CoWIN_OTP_Pusher.macro) after installing [MacroDroid](https://www.macrodroid.com/) your phone.
	* You will need to set the various variables and modify the macro accordingly:
		1. Server endpoint URL (`endpoint` local variable)
		2. Server authentication key (`authKey` local variable) - should match whatever you put in [config.toml](sample_config.toml) (this is NOT the same as the secret token from step 0)
		3. If you use an SMS App other than Google Messages, you will need to modify the trigger and actions by selecting your SMS app there.

#### 3. Telegram Bot (optional)
For telegram functionality, you need to set up a bot. See [Bots](https://core.telegram.org/bots) for instructions.

### Running
1. Clone this repo to desired PC (this will need to be running 24x7).
2. Install [Python](https://python.org/) (version >=3.9)
3. Install [poetry](https://python-poetry.org/)
4. Run `poetry install --no-root`
5. Rename `sample_config.toml` into `config.toml` and set all the necessary fields.
6. Run `poetry run python main.py`

## Acknowledgements
Most of the knowledge about the CoWIN API flow was obtained from studying the repo https://github.com/yashwanthm/cowin-vaccine-booking/

## Contributing
This app was made to fulfill a personal need and I have no further plans to develop it. However, I believe the app has a lot of potential and there are a lot of TODOs scattered around the codebase. You are free to study the codebase and make modifications to it.
However, **DO NOT** try to contact me anywhere outside of Github for further clarifications or requests. Use the issue tracker for that.
