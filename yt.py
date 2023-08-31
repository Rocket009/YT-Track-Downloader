from googleapiclient.discovery import build
from pytube import YouTube
import argparse
import re
from pprint import pprint
from pydub import AudioSegment
from pathlib import Path
import os
import shutil
import tqdm

parser = argparse.ArgumentParser(prog="YT Track Downloader", description="Downloads Tracks based on Chapters in YouTube Video")
parser.add_argument("link", type=str, help="The YouTube link to download")
parser.add_argument("-o", "--offset", type=float, required=False, help="An offset in seconds to shift all the Tracks. If negitive will shift back positive will shift forward", default=0, dest="offset")
parser.add_argument("-f", "--folder-name", type=str, required=False, help="The name of the folder that the Tracks will be saved in", default="", dest="folder_name")
parser.add_argument("-s", "--save-video", action="store_true", required=False, default=False, dest="save_video", help="Keeps the original video file")
parser.add_argument("-p", "--padding", type=float, required=False, help="Number of seconds to cut before next song", dest="padding", default=0)
parser.add_argument("-k", "--api-key", type=str, help="Set a custom YouTube API key to use", required=False, default="", dest="api")
args = parser.parse_args()
video = YouTube(args.link)

if args.api != "":
    os.environ["YT_API_KEY"] = args.api
    api_key = args.api
else:
    try:
        api_key = os.environ["YT_API_KEY"]
    except KeyError:
        print("YT_API_KEY environment variable is not set.\nEther set it through the -k flag or manualy set it.")
        exit(1)

youtube = build('youtube', 'v3', developerKey=api_key)

def time_formater(time:str):
    digits = time.split(":")
    for index, s in enumerate(digits):
        if not s.isdigit():
            digits[index] = re.sub('\D', '', s)
    # in the form 00:00
    if len(digits) == 2:
        ftime = (int(digits[0]) * 60 * 1000) + (int(digits[1]) * 1000)
    # in the form 00:00:00
    elif len(digits) == 3:
        ftime = (int(digits[0]) * 60 ** 2 * 1000) + (int(digits[1]) * 60 * 1000) + (int(digits[2]) * 1000)
    else:
        raise Exception("Time Formatter Error\nTime was not in the form 00:00 or 00:00:00")
    return ftime


def getVideoTimelineById(videoId):
    request = youtube.videos().list(part="id,snippet", id = videoId)
    response = request.execute()
    des = response['items'][0]['snippet']['description']
    pattern = re.compile(r"((?:(?:[01]?\d|2[0-3]):)?(?:[0-5]?\d):(?:[0-5]?\d))(.+)")

    # find all matches to groups
    timeline = []
    for match in pattern.finditer(des):
        group2 = match.group(2)
        counter = 0
        for c in group2:
            if c.isalpha():
                break
            counter += 1
        timeline.append({"time": match.group(1), "label": group2[counter:]})
    return timeline

print("Downloading video file...")
org_path = Path(video.streams.get_audio_only().download())
print("Download Complete")
song = AudioSegment.from_file(str(org_path))
if args.folder_name == "":
    path = Path(org_path.parent, org_path.stem.replace(" ", "_"))
else:
    path = Path(org_path.parent, re.sub('[^\w_.)( -]', '', args.folder_name))
if path.exists():
    shutil.rmtree(str(path))
path.mkdir()
stamps = getVideoTimelineById(video.video_id)
lasttime = 0
if time_formater(stamps[0]["time"]) > 0:
    startindex = 0
else:
    startindex = 1
for index in tqdm.trange(len(stamps), desc="Generating Tracks"):
    s = stamps[index]
    try:
        st = stamps[index + startindex]["time"]
    except IndexError:
        nexttime = video.length * 1000
    else:
        nexttime = time_formater(st)
    try:
        extract = song[(args.padding * 1000) + lasttime:nexttime + (args.offset * 1000)]
        lasttime = nexttime
        lfilename = str(path.absolute()) + "\\" + re.sub('[^\w_.)( -]', '', s["label"]) + ".mp3"
        extract.export(lfilename, format="mp3")
    except:
        print(f"Error on track: {s['label']}")
        continue
if org_path.is_file() and not args.save_video:
    os.remove(str(org_path))
print("All done!")
