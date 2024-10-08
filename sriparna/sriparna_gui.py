# Copyright (c) 2024, Vince Thongam
# All rights reserved.

# This source code is licensed under the GPL-3.0 license found in the
# LICENSE file in the root directory of this source tree.
# If you don't have the source tree alternately this file can be found at
# <https://github.com/Vincenzo675/termux-sriparna>

import os
import re
import sys
import subprocess
import random
import string
import time
from datetime import datetime
from dateutil import tz
from geopy.geocoders import Nominatim
import speech_recognition as sr
from g4f.client import Client
from g4f.Provider import RetryProvider, Bing, ChatgptAi, OpenaiChat
import json
import python_weather
import asyncio
import g4f.debug
import dialog

g4f.debug.logging = False

client = Client(provider=RetryProvider([ChatgptAi, OpenaiChat, Bing], shuffle=False))


def load_app_mappings(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {}


python_version = "{}.{}".format(sys.version_info.major, sys.version_info.minor)
appjson_path = "/data/data/com.termux/files/usr/lib/python{}/site-packages/sriparna/apps.json".format(
    python_version
)

# Check if the given path exists, if not, fallback to using "apps.json"
if os.path.exists(appjson_path):
    app_mappings = load_app_mappings(appjson_path)
else:
    app_mappings = load_app_mappings("apps.json")

# Generate random 5-character strings for input and output file paths
random_chars = "".join(
    random.choices(string.ascii_letters + string.digits + string.punctuation, k=5)
)
input_file_path = f"/data/data/com.termux/files/home/{random_chars}.amr"
output_file_path = f"/data/data/com.termux/files/home/{random_chars}.wav"

# Python Dialog Setup
d = dialog.Dialog(dialog="dialog")
d.set_background_title("Welcome to Termux-Sriparna")
sys_width = 0
sys_height = 0


def record_audio():
    subprocess.call(
        "termux-api-start &> /dev/null", shell=False
    )  # fix freezing problem
    if os.path.exists(input_file_path):
        os.remove(input_file_path)

    code, tag = d.radiolist(
        "Select an option:",
        choices=[
            ("Start recording", "Start recording", False),
            ("Term", "Enter Terminal Mode", False),
            ("Live", "Enter live assistant mode (Slower)", False),
            ("About", "About", False),
            ("Exit", "Exit", False),
        ],
        height=sys_height,
        width=sys_width,
        no_tags=True,
        no_cancel=True,
    )
    if code == d.ESC:
        d.infobox("Why you want to escape?")
        time.sleep(1)
        main()
    elif code == d.OK:
        if tag == "Start recording":
            d.infobox("Starting recording...")
            subprocess.run(
                ["termux-microphone-record", "-q"],
                stdout=subprocess.DEVNULL,
                check=True,
            )
            subprocess.run(
                ["termux-microphone-record", "-e", "awr_wide", "-f", input_file_path],
                stdout=subprocess.DEVNULL,
                check=True,
            )

            code = d.yesno(
                "Do you want to stop recording ?",
                width=sys_width,
                height=sys_height,
                no_collapse=True,
            )
            if code == d.OK:
                subprocess.run(
                    ["termux-microphone-record", "-q"],
                    stdout=subprocess.DEVNULL,
                    check=True,
                )
                d.infobox("Recording finished.")
                time.sleep(1)
                d.infobox("Working on it ...")
                time.sleep(2)

            elif code == d.CANCEL:
                d.infobox("No worries, I am still listening ...")
                time.sleep(2)

            elif code == d.ESC:
                d.infobox("Why you want to escape?")
                time.sleep(2)

        elif tag == "Exit":
            d.infobox("Goodbye! See you soon ...")
            time.sleep(2)
            subprocess.call("clear", shell=False)
            sys.exit()
        elif tag == "Term":
            d.infobox("Entering Terminal mode ...")
            time.sleep(3)
            subprocess.call("clear && sriparna", shell=False)
            sys.exit()
        elif tag == "Live":
            pass
            # To be implemented
        elif tag == "About":
            d.msgbox(
                "Hello user, my name is Sriparna\nI am a voice assistant written in python"
            )
            main()


def convert_to_wav(input_file, output_file):
    subprocess.run(
        [
            "ffmpeg",
            "-i",
            input_file,
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            "16000",
            output_file,
            "-y",
            "-loglevel",
            "quiet",
        ],
        check=True,
    )


def recognize_speech(audio_file):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            return text
        except sr.UnknownValueError:
            return "Could not understand audio"
        except sr.RequestError as e:
            return "Error: " + str(e)


def get_contact_info():
    contacts_json = subprocess.check_output(["termux-contact-list"])
    contacts = json.loads(contacts_json)
    contact_info = {}
    for contact in contacts:
        name = contact["name"].lower().replace(" ", "")
        number = contact["number"]
        contact_info[name] = number
    return contact_info


async def get_weather_from_coordinates(latitude, longitude):
    geolocator = Nominatim(user_agent="http")
    location = geolocator.reverse((latitude, longitude))
    # print(location.address)
    city = location.address.split(",")[0]
    async with python_weather.Client() as weather_client:
        weather = await weather_client.get(city)
        weather_info = f"Current weather in {city} is:\n\n"
        weather_info += f"Type: {weather.kind} {weather.kind.emoji}\n"
        weather_info += f"Temperature: {weather.temperature}°C\n"
        weather_info += f"Feels Like: {weather.feels_like}°C\n"
        weather_info += f"Description: {weather.description}\n"
        weather_info += f"Humidity: {weather.humidity}%\n"
        weather_info += f"Wind Speed: {weather.wind_speed} km/h\n"
        weather_info += f"Wind Direction: {weather.wind_direction}\n"
        weather_info += f"Visibility: {weather.visibility} km\n"
        weather_info += f"Pressure: {weather.pressure} hPa\n"
        weather_info += f"Precipitation: {weather.precipitation} mm\n"
        weather_info += f"UV Index: {weather.ultraviolet}\n"
        return weather_info


def voice_assistant(text):
    # Check if the text contains any mention of checking battery status
    if any(
        keyword in text.lower()
        for keyword in [
            "battery percentage",
            "battery status",
            "battery health",
            "my battery",
        ]
    ):
        # Run the command to get battery status using termux-battery-status
        battery_status_output = subprocess.check_output(
            ["termux-battery-status"]
        ).decode("utf-8")
        battery_status_json = json.loads(battery_status_output)
        battery_percentage = battery_status_json.get("percentage", "unknown")
        return f"Your battery percentage is {battery_percentage}%"

    # Check if the text contains any commands to open apps
    for app, intent in app_mappings.items():
        if f"open {app.lower()}" in text.lower():
            # Search for the app and open it if found
            subprocess.run(
                ["am", "start", "-n", intent], stdout=subprocess.DEVNULL, check=True
            )
            return f"Opening {app}"

    # Check if the text contains a command to call a mobile number
    call_pattern = r"call\s*(\+?\s*\d+(?:\s*\d+)*)"
    match = re.search(call_pattern, text.lower())
    if match:
        # Remove spaces from the number
        number = match.group(1).replace(" ", "")
        if "plus" in text.lower():
            subprocess.run(
                ["termux-telephony-call", f"+{number}"],
                stdout=subprocess.DEVNULL,
                check=True,
            )
            return f"Calling {number}"
        else:
            subprocess.run(
                ["termux-telephony-call", number], stdout=subprocess.DEVNULL, check=True
            )
            return f"Calling {number}"

    # Check if the text contains a command to call a contact
    call_name_pattern = r"call\s*(.*)"
    match_name = re.search(call_name_pattern, text.lower())
    if match_name:
        contact_info = get_contact_info()
        name = (
            match_name.group(1).lower().replace(" ", "")
        )  # Remove spaces from the name
        for contact_name in contact_info.keys():
            if name == contact_name:
                number = contact_info[contact_name]
                subprocess.run(
                    ["termux-telephony-call", number],
                    stdout=subprocess.DEVNULL,
                    check=True,
                )
                return f"Calling {name}"
        return f"No contact found with name {name}"

    if (
        "flash on" in text.lower()
        or "torch on" in text.lower()
        or "on the flash" in text.lower()
        or "on the torch" in text.lower()
    ):
        subprocess.run(["termux-torch", "on"], check=True)
        return "Flashlight turned on."
    elif (
        "flash off" in text.lower()
        or "torch off" in text.lower()
        or "off the flash" in text.lower()
        or "off the torch" in text.lower()
    ):
        subprocess.run(["termux-torch", "off"], check=True)
        return "Flashlight turned off."

    # Check if the text contains any queries regarding current time
    if any(
        keyword in text.lower()
        for keyword in [
            "what is the time",
            "what's the time",
            "time now",
            "current time",
            "what time",
        ]
    ):
        try:
            # Get local time zone
            local_timezone = tz.tzlocal()
            # Get current time
            current_time = datetime.now(local_timezone)
            # Format the current time
            formatted_time = current_time.strftime("It is %I:%M:%S %p")
            return formatted_time
        except Exception:
            return "Sorry, I couldn't fetch the local time."

    # Check if the text contains any queries regarding current date
    if any(
        keyword in text.lower()
        for keyword in [
            "what is the date",
            "what's the date",
            "date today",
            "today's date",
            "what day",
            "which day",
        ]
    ):
        try:
            # Get local time zone
            local_timezone = tz.tzlocal()
            # Get current time
            current_time = datetime.now(local_timezone)
            # Format the current date
            formatted_date = current_time.strftime("Today's date is: %B %d, %Y (%A)")
            return formatted_date
        except Exception:
            return "Sorry, I couldn't fetch the local date."

    # Check if the text contains any type of query asking about the current
    # weather conditions
    if any(
        keyword in text.lower()
        for keyword in [
            "weather alike",
            "weather conditions",
            "current weather",
            "weather forecast",
            "how is the weather",
        ]
    ):
        try:
            # Fetch GPS coordinates
            gps_output = subprocess.check_output(
                ["termux-location", "-p", "gps"]
            ).decode("utf-8")
            gps_json = json.loads(gps_output)
            latitude = gps_json.get("latitude")
            longitude = gps_json.get("longitude")
            if latitude and longitude:
                # Get weather information from coordinates
                return asyncio.run(get_weather_from_coordinates(latitude, longitude))

        except subprocess.TimeoutExpired:
            return "Unable to fetch GPS coordinates. Is your location turned off ?"

    stream = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": text}],
        stream=True,
    )
    typed_text = ""
    for chunk in stream:
        if chunk.choices[0].delta.content:
            response = chunk.choices[0].delta.content
            typed_text += response
            d.infobox(typed_text, width=sys_width, height=sys_height)
            time.sleep(0.05)
    d.infobox(typed_text, width=sys_width, height=sys_height)
    time.sleep(4)


def main():
    while True:
        try:
            record_audio()
            convert_to_wav(input_file_path, output_file_path)
            text = recognize_speech(output_file_path)
            d.infobox(f"You said: {text}")
            time.sleep(4)
            os.remove(output_file_path)
            os.remove(input_file_path)
            response = voice_assistant(text)
            if response:
                d.msgbox(f"Response: {response}")

        except Exception as e:
            d.msgbox(f"Something went wrong.\nPlease try again.\nException Caught: {e}")
            record_audio()
            convert_to_wav(input_file_path, output_file_path)
            text = recognize_speech(output_file_path)
            d.infobox(f"You said: {text}")
            time.sleep(4)
            os.remove(output_file_path)
            os.remove(input_file_path)
            response = voice_assistant(text)
            if response:
                d.msgbox(f"Response: {response}")


if __name__ == "__main__":
    main()
