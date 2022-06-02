import asyncio
import datetime
import os
import secrets

import pytube.request
import telebot.types
from dotenv import load_dotenv
from pytube import YouTube
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.util import antiflood
from ufile import Ufile
from unit_prettifier import UnitPrettifier

load_dotenv()

bot = telebot.TeleBot(os.getenv('API_TOKEN'))

pytube.request.default_range_size = 524288


# Handle '/start' and '/help'
@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    bot.reply_to(message, """Hi there, I am here to help you download YouTube videos.\nJust send me a link!""")


class _RateLimiter:
    last_update_at: datetime.datetime = None
    value: int = 0

    def should_update(self):
        if not self.last_update_at:
            self.last_update_at = datetime.datetime.now()
        if self.last_update_at + datetime.timedelta(milliseconds=500) >= datetime.datetime.now():
            return False
        self.last_update_at = datetime.datetime.now()
        return True


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call: telebot.types.CallbackQuery):
    link = call.message.caption.split("\n")[0]
    yt = YouTube(link)
    message = f"{link}\n\n{yt.title}\n{yt.channel_url}\n\n#$PROGRESS$#"

    if call.data == "cb_audio":
        ys = yt.streams.get_audio_only()
    elif call.data == "cb_max":
        ys = yt.streams.get_highest_resolution()
    elif call.data == "cb_min":
        ys = yt.streams.get_lowest_resolution()
    else:
        ys = yt.streams.get_by_resolution(call.data[3:])
    if not ys:
        ys = yt.streams.get_highest_resolution()

    ys_audio = yt.streams.get_audio_only()

    is_highres_video = int(call.data.split("_")[1][:-1]) > 720

    def progress_callback(message_a: str, done_bytes: int, total_: int):
        percentage = done_bytes / total_ * 100

        pretty_done = UnitPrettifier.prettify_bytes(done_bytes)
        pretty_total = UnitPrettifier.prettify_bytes(total_)
        progress_text = f"{message_a}!\n" \
                        f"Progress: |{'█'*int(percentage/10)}{' -'*int(10-percentage/10)}| " \
                        f"{percentage:.2f}% " \
                        f"({pretty_done[0]:.2f}{pretty_done[1]}/{pretty_total[0]:.2f}{pretty_total[1]})"
        antiflood(bot.edit_message_caption, message.replace("#$PROGRESS$#", progress_text),
                  call.message.chat.id, call.message.message_id)

    def progress_callback_download_from_youtube(_, __, remaining_bytes: int):
        total = ys.filesize + ys_audio.filesize
        progress_callback("Downloading from YouTube", ys.filesize - remaining_bytes, total)

    def progress_callback_download_from_youtube_high_res_2(_, __, remaining_bytes: int):
        total = ys.filesize + ys_audio.filesize
        progress_callback("Downloading from YouTube", total - remaining_bytes, total)

    async def progress_callback_sending_file_to_user(done_bytes: int, total_: int):
        progress_callback("Sending the file to you!", done_bytes, total_)

    def complete_callback(_, path):
        progress_text = f"Download Completed!\nSending the file to you right now!"

        bot.edit_message_caption(message.replace("#$PROGRESS$#", progress_text), call.message.chat.id,
                                 call.message.message_id)

        ufile = Ufile(progress_callback=progress_callback_sending_file_to_user, progress_update_ms=10000)
        url = asyncio.run(ufile.upload_file(path))

        antiflood(bot.edit_message_caption,
                  message.replace("#$PROGRESS$#", f"You can download your file using the link below!\n{url}"),
                  call.message.chat.id, call.message.message_id)
        os.remove(path)

    def progress_callback_download_from_youtube_high_res_merge(_, path):
        progress_text = f"Processing your video!"

        antiflood(bot.edit_message_caption,
                  message.replace("#$PROGRESS$#", progress_text),
                  call.message.chat.id, call.message.message_id)

        video_format = ys.default_filename.split('.')[-1]
        path_token = '.'.join(path.split('.')[:-1])
        video_path = f"{path_token}.{video_format}"
        os.system(f'ffmpeg -loglevel panic -y -i {video_path} -i {path_token}.m4a -c:v copy '
                  f'-c:a copy {path_token}A.{video_format}')
        os.remove(video_path)
        os.remove(path)
        complete_callback(_, f"{path_token}A.{video_format}")

    bot.edit_message_caption(message.replace("#$PROGRESS$#", "Download Started!"), call.message.chat.id,
                             call.message.message_id)
    is_success = False
    max_try = 10

    yt.register_on_progress_callback(progress_callback_download_from_youtube)

    if not is_highres_video:
        yt.register_on_complete_callback(complete_callback)

    file_token = secrets.token_hex(8)
    file_extension = ys.default_filename.split('.')[-1]
    if call.data == "cb_audio" and file_extension == "mp4":
        file_extension = 'm4a'

    while not is_success and max_try > 0:
        # noinspection PyBroadException
        try:
            ys.download(output_path="downloads/",
                        max_retries=10,
                        filename=f"{file_token}.{file_extension}")
            is_success = True
        except Exception:
            max_try -= 1
    if not is_success:
        bot.edit_message_caption(message.replace("#$PROGRESS$#",
                                                 "Download Failed :(\nPlease retry in a few minutes!"),
                                 call.message.chat.id, call.message.message_id)
        return

    if is_highres_video:
        yt.register_on_progress_callback(progress_callback_download_from_youtube_high_res_2)
        yt.register_on_complete_callback(progress_callback_download_from_youtube_high_res_merge)
        ys_audio.download("downloads/", max_retries=10, filename=f"{file_token}.m4a")


@bot.message_handler(func=lambda message: True)
def message_handler(message: telebot.types.Message):
    yt = YouTube(message.text)
    qualities = list(filter(lambda y: y, set(list(map(lambda x: x.resolution, yt.streams)))))
    qualities.insert(0, "Max Quality")
    qualities.append("Lowest Quality")
    qualities.append("Audio")

    qualities = list(map(lambda x: InlineKeyboardButton(x,
                                                        callback_data=f"cb_{x.split(' ')[0].lower()}"),
                         qualities))

    markup = InlineKeyboardMarkup()
    markup.add(*qualities)

    bot.send_photo(message.chat.id, yt.thumbnail_url,
                   caption=f"{message.text}\n\n{yt.title}\n{yt.channel_url}\n\n"
                           f"Please Select the Desired Quality!",
                   reply_markup=markup)


bot.infinity_polling()
