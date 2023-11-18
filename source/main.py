# Проект DCAudio - веб-приложение для удалённого управления воспроизведением аудио-файлов
# Артём Ларионенко (t.me/lrrrtm)
# 5132704/20001

import asyncio
import fnmatch
import json
import eyed3
import flet as ft
import sounddevice as sd
import os
from pygame import mixer
import schedule
import re


async def main(page: ft.Page):
    # ------------------------- ГЛОБАЛЬНЫЕ ПАРАМЕТРЫ ------------------------

    global folder_now
    global CUR_PLAYLIST
    global CUR_TRACK_ID

    CUR_PLAYLIST = []
    CUR_TRACK_ID = -1
    folder_now = "C:/Users/Lario/OneDrive/Рабочий стол/music_open"
    page.title = "CROD Audio"
    mixer.init()

    # ------------------------------- ФУНКЦИИ -------------------------------

    async def check_cable_connection():
        devices = sd.query_devices()
        for device in devices:
            if "analog" in device["name"].lower() and "output" in device["name"].lower():
                return True
        return False

    async def start_main_screen(e):
        with open("current_params.json", "r") as file:
            data = file.readline()
            data = json.loads(data)
            await update_view(data)
        current_playlist_col.visible = True
        track_name_artist_col.visible = True
        control_buttons_row.visible = True
        main_screen_btns_row.visible = True
        check_connection_col.visible = False
        volume_control_row.visible = True
        timer_btn.visible = True
        to_main_screen_btn.visible = False
        page.appbar.title = ft.Text("Основной экран")
        await page.update_async()

    async def update_view(msg):
        global CUR_PLAYLIST, CUR_TRACK_ID, folder_now
        if msg['status'] != "":
            volume_slider.value = msg['current_volume']
            folder_now = msg['current_folder']
            CUR_TRACK_ID = msg['current_track_id']
            CUR_PLAYLIST = msg['current_playlist']
            track_name_artist_text.value = msg['track_name']
            current_status_btn.text = msg['status']
            pick_playlist_btn.text = re.split(r'//|/|\\', folder_now)[-1]
            current_playlist_col.controls.clear()

            for cur_track in CUR_PLAYLIST:
                audio = eyed3.load(cur_track)
                try:
                    track_name = ft.Text(f"{audio.tag.title} - {audio.tag.artist}")
                    if track_name is None:
                        track_name = ft.Text(re.split(r'//|/|\\', cur_track)[-1])
                except AttributeError:
                    track_name = ft.Text(re.split(r'//|/|\\', cur_track)[-1])
                current_playlist_col.controls.append(track_name)
        page.snack_bar = ft.SnackBar(
            content=ft.Text(f"Подключение выполнено успешно!"))
        page.snack_bar.open = True

    async def explorer_changing(e):
        global folder_now
        try:
            os.listdir(folder_now + f"/{e.control.value}")
            folder_now += f"/{e.control.value}"
            source_text.value = f"Путь: {folder_now}".replace("//", "/")
            await page.update_async()
            await show_folders("e")
        except PermissionError:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("К данной директории нет доступа, выберите другую директорию"))
            page.snack_bar.open = True
            await page.update_async()

    async def show_folders(e):
        all_list = os.listdir(folder_now)
        folders_list = [folder for folder in all_list if os.path.isdir(os.path.join(folder_now, folder))]
        col_list = ft.Column(height=400)

        for folder in folders_list:
            col_list.controls.append(
                ft.Radio(value=f"/{folder}",
                         label=folder)
            )
        folders_explorer.content = col_list
        await page.update_async()

    async def find_mp3_files(folder):
        mp3_files = []
        for root, dirs, files in os.walk(folder):
            for file in fnmatch.filter(files, '*.mp3'):
                mp3_files.append(os.path.join(root, file))
        return mp3_files

    async def after_folder_picked(e):
        global CUR_PLAYLIST
        CUR_PLAYLIST = await find_mp3_files(folder_now)
        if len(CUR_PLAYLIST) > 0:
            await open_main_screen("e")
            pick_playlist_btn.text = re.split(r'//|/|\\', folder_now)[-1]
            await send_data()
            await update_data()
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Обнаружено треков: {len(CUR_PLAYLIST)}")
            )
            page.snack_bar.open = True
            track_name_artist_text.value = f"Нажмите на клавишу переключения, чтобы запустить проигрывание"
            current_playlist_col.controls.clear()

            for cur_track in CUR_PLAYLIST:
                audio = eyed3.load(cur_track)
                try:
                    track_name = ft.Text(f"{audio.tag.title} - {audio.tag.artist}")
                    if track_name is None:
                        track_name = ft.Text(re.split(r'//|/|\\', cur_track)[-1])
                except AttributeError:
                    track_name = ft.Text(re.split(r'//|/|\\', cur_track)[-1])
                current_playlist_col.controls.append(track_name)
        else:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("В данной директории нет файлов mp3, выберите другую директорию"))
            page.snack_bar.open = True
        await page.update_async()

    async def go_up_explorer(e):
        global folder_now
        folder_now = "/".join(folder_now.split("/")[:-2])
        source_text.value = f"Путь: {folder_now}".replace("//", "/")
        await page.update_async()
        await show_folders("e")

    async def open_explorer_screen(e):
        volume_control_row.visible = False
        current_playlist_col.visible = False
        track_name_artist_col.visible = False
        control_buttons_row.visible = False
        main_screen_btns_row.visible = False
        folders_explorer_col.visible = True
        pick_folder_text.visible = True
        source_text.visible = True
        explorer_btns_row.visible = True
        timer_btn.visible = False
        page.appbar.leading = to_main_screen_btn
        to_main_screen_btn.visible = True
        page.appbar.title = ft.Text("Выбор папки")
        await show_folders("e")
        await page.update_async()

    async def continue_playing(e):
        mixer.music.unpause()
        current_status_btn.text = "Играет"
        current_status_btn.bgcolor = ft.colors.GREEN
        await send_data()
        await page.update_async()
        await update_data()

    async def pause_playing(e):
        mixer.music.pause()
        current_status_btn.text = "Пауза"
        current_status_btn.bgcolor = ft.colors.YELLOW
        await send_data()
        await page.update_async()
        await update_data()

    async def next_track(e):
        global CUR_PLAYLIST, CUR_TRACK_ID
        if CUR_TRACK_ID == len(CUR_PLAYLIST) - 1:
            CUR_TRACK_ID = -1
        mixer.music.load(CUR_PLAYLIST[CUR_TRACK_ID + 1])
        mixer.music.set_volume(volume_slider.value / 100)
        CUR_TRACK_ID += 1
        audio_info = eyed3.load(CUR_PLAYLIST[CUR_TRACK_ID])
        try:
            track_name_artist_text.value = f"{audio_info.tag.title} - {audio_info.tag.artist}"
        except AttributeError:
            track_name_artist_text.value = f"{CUR_PLAYLIST[CUR_TRACK_ID].split('/')[-1]}"
        mixer.music.play(fade_ms=1000)
        current_status_btn.text = "Играет"
        current_status_btn.bgcolor = ft.colors.GREEN

        await update_data()
        await send_data()
        await page.update_async()

    async def change_volume(e):
        volume = volume_slider.value / 100
        print(f"VOLUME CHANGED TO {volume}")
        mixer.music.set_volume(volume)
        await update_data()
        await send_data()

    async def previous_track(e):
        global CUR_PLAYLIST, CUR_TRACK_ID
        if CUR_TRACK_ID == 0:
            CUR_TRACK_ID = len(CUR_PLAYLIST)
        mixer.music.load(CUR_PLAYLIST[CUR_TRACK_ID - 1])
        CUR_TRACK_ID -= 1
        audio_info = eyed3.load(CUR_PLAYLIST[CUR_TRACK_ID])
        track_name_artist_text.value = f"{audio_info.tag.title} - {audio_info.tag.artist}"
        mixer.music.play(fade_ms=1000)
        current_status_btn.text = "Играет"
        current_status_btn.bgcolor = ft.colors.GREEN

        await send_data()
        await update_data()
        await page.update_async()

    async def get_update(msg):
        print("RECIEVED UPDATE")
        global CUR_PLAYLIST, CUR_TRACK_ID, folder_now

        volume_slider.value = msg['current_volume']
        folder_now = msg['current_folder']
        CUR_TRACK_ID = msg['current_track_id']
        CUR_PLAYLIST = msg['current_playlist']
        track_name_artist_text.value = msg['track_name']
        player_status = msg['status']

        current_status_btn.text = player_status
        pick_playlist_btn.text = folder_now.split("/")[-1]
        current_playlist_col.controls.clear()
        for cur_track in CUR_PLAYLIST:
            audio = eyed3.load(cur_track)
            try:
                track_name = ft.Text(f"{audio.tag.title} - {audio.tag.artist}")
                if track_name is None:
                    track_name = ft.Text(re.split(r'//|/|\\', cur_track)[-1])
            except AttributeError:
                track_name = ft.Text(re.split(r'//|/|\\', cur_track)[-1])
            #track_name = ft.Text(f"{audio.tag.title} - {audio.tag.artist}")
            current_playlist_col.controls.append(track_name)
        await page.update_async()
    await page.pubsub.subscribe_async(get_update)

    async def send_data():
        print("UPDATE SENT")
        data = {
            "current_folder": folder_now,
            "current_track_id": CUR_TRACK_ID,
            "current_playlist": CUR_PLAYLIST,
            "current_volume": volume_slider.value,
            "track_name": track_name_artist_text.value,
            "status": current_status_btn.text

        }
        if data['current_track_id'] != -1:
            await page.pubsub.send_others_async(data)

    async def update_data():
        data = {
            "current_folder": folder_now,
            "current_track_id": CUR_TRACK_ID,
            "current_playlist": CUR_PLAYLIST,
            "current_volume": volume_slider.value,
            "track_name": track_name_artist_text.value,
            "status": current_status_btn.text

        }
        jsonStr = json.dumps(data)
        with open("current_params.json", "w") as file:
            file.write(jsonStr)

    async def open_main_screen(e):
        volume_control_row.visible = True
        current_playlist_col.visible = True
        track_name_artist_col.visible = True
        control_buttons_row.visible = True
        main_screen_btns_row.visible = True
        folders_explorer_col.visible = False
        pick_folder_text.visible = False
        source_text.visible = False
        explorer_btns_row.visible = False
        timer_btn.visible = True
        to_main_screen_btn.visible = False
        add_timer_btn.visible = False
        timers_list_col.visible = False
        page.appbar.title = ft.Text("Основной экран")
        await page.update_async()

    def stop_music_by_schedule():
        mixer.music.pause()

    def start_music_by_schedule():
        mixer.music.play(fade_ms=1000)

    async def add_timer(time, task):
        schedule.every().day.at(time).do(task)

    async def remove_timer(task):
        schedule.cancel_job(task)

    async def open_timers_screen(e):
        page.appbar.title = ft.Text("Таймеры")
        timer_btn.visible = False
        volume_control_row.visible = False
        current_playlist_col.visible = False
        track_name_artist_col.visible = False
        control_buttons_row.visible = False
        main_screen_btns_row.visible = False
        timer_btn.visible = False
        add_timer_btn.visible = True
        timers_list_col.visible = True
        to_main_screen_btn.visible = True
        page.appbar.leading = to_main_screen_btn

        with open("timers.json", "r") as file:
            timers = file.readline()
            timers = json.loads(timers)['data']
            timers_list_col.controls.clear()
            for timer in timers:
                timers_list_col.controls.append(
                    ft.Card(
                        content=ft.Row(
                            [
                                ft.Container(
                                    ft.Column(
                                        [
                                            ft.Text(timer['time'], size=24),
                                            ft.Text(f"Действие: {timer['task']}"),
                                        ],
                                        alignment="center",
                                    ),
                                    margin=ft.margin.only(right=30)
                                ),
                                ft.IconButton(icon=ft.icons.EDIT_ROUNDED),
                                ft.IconButton(icon=ft.icons.DELETE_ROUNDED),
                                ft.Switch(value=bool(timer['status']))
                            ],
                            alignment="center"
                        ),
                        width=400,
                        height=130
                    )
                )

        await page.update_async()

    # -------------------- СОЗДАНИЕ ЭЛЕМЕНТОВ УПРАВЛЕНИЯ --------------------

    to_main_screen_btn = ft.IconButton(
        icon=ft.icons.ARROW_BACK_ROUNDED,
        visible=False,
        on_click=open_main_screen
    )
    timer_btn = ft.FilledTonalButton(
        icon=ft.icons.TIMER_ROUNDED,
        visible=False,
        on_click=open_timers_screen,
        text="Таймеры"
    )
    add_timer_btn = ft.FilledTonalButton(
        icon=ft.icons.ADD_ALARM_ROUNDED,
        visible=False,
        text="Создать"
    )
    page.appbar = ft.AppBar(
        title=ft.Text("Инциализация"),
        bgcolor=ft.colors.SURFACE_VARIANT,
        actions=[timer_btn, add_timer_btn]
    )

    track_name_artist_text = ft.Text("Папка с музыкой не выбрана, воспроизведение невозможно")

    check_connection_text = ft.Text("Для инициализации нажмите на кнопку")

    check_connection_btn = ft.OutlinedButton(
        text="Инициализироваться",
        icon=ft.icons.CABLE_ROUNDED,
        on_click=start_main_screen,
        height=50,
        width=300
    )
    timers_list_col = ft.Column(
        visible=False,
        alignment="center",
        scroll=ft.ScrollMode.ALWAYS,
        expand=True
    )
    check_connection_col = ft.Column(
        controls=[
            check_connection_text,
            check_connection_btn
        ],
        visible=False,
        alignment="center",
    )
    track_name_artist_col = ft.Column(
        controls=[
            track_name_artist_text
        ],
        alignment="center",
        visible=False
    )
    control_buttons_row = ft.Row(
        controls=[
            ft.IconButton(icon=ft.icons.SKIP_PREVIOUS_ROUNDED,
                          icon_size=60,
                          on_click=previous_track
                          ),
            ft.IconButton(icon=ft.icons.PLAY_CIRCLE_FILL_ROUNDED,
                          icon_size=72,
                          on_click=continue_playing
                          ),
            ft.IconButton(icon=ft.icons.PAUSE_CIRCLE_FILLED_ROUNDED,
                          icon_size=72,
                          on_click=pause_playing
                          ),
            ft.IconButton(icon=ft.icons.SKIP_NEXT_ROUNDED,
                          icon_size=60,
                          on_click=next_track
                          ),

        ],
        alignment="center",
        visible=False
    )
    pick_playlist_btn = ft.FilledButton(
        text="Выбор папки",
        visible=True,
        on_click=open_explorer_screen,
        height=50, width=200, icon=ft.icons.FOLDER_OPEN_ROUNDED
    )
    current_status_btn = ft.FilledButton(
        text="Не запущено",
        disabled=True,
        height=50,
        width=150
    )
    main_screen_btns_row = ft.Row(
        [
            pick_playlist_btn,
            current_status_btn
        ],
        visible=False,
        alignment="center"
    )
    pick_folder_text = ft.Text("Выберите папку, в которой находится плейлист",
                        visible=False
                        )
    source_text = ft.Text(f"Путь: {folder_now}",
                          visible=False
                          )

    folders_explorer = ft.RadioGroup(
        on_change=explorer_changing
    )
    pick_explorer_btn = ft.FilledButton(text="Выбрать",
                               on_click=after_folder_picked,
                               icon=ft.icons.FOLDER_OPEN_ROUNDED,
                               height=50,
                               width=200
                               )
    pick_explorer_btn.bgcolor = ft.colors.GREEN_ACCENT

    up_explorer_btn = ft.IconButton(on_click=go_up_explorer,
                                icon=ft.icons.ARROW_UPWARD_ROUNDED,
                                height=50,
                                bgcolor=ft.colors.SURFACE_VARIANT)
    explorer_btns_row = ft.Row(
        [
            up_explorer_btn,
            pick_explorer_btn
        ],
        visible=False,
        alignment="center"
    )

    folders_explorer_col = ft.Column(
        [
            folders_explorer,
        ],
        alignment="center",
        visible=False,
    )

    current_playlist_col = ft.Column(
        visible=False,
        expand=True,
        spacing=20,
        scroll=ft.ScrollMode.ALWAYS
    )

    volume_slider = ft.Slider(
        min=0,
        max=100,
        divisions=100,
        label="{value}%",
        on_change=change_volume,
        value=50,
        expand=True
    )

    volume_control_row = ft.Row(
        [
            ft.IconButton(
                icon=ft.icons.VOLUME_UP_ROUNDED,
                icon_size=24,
                disabled=True
            ),
            volume_slider
        ],
        alignment="center",
        visible=False,
    )

    if await check_cable_connection():
        track_name_artist_col.visible = True
        control_buttons_row.visible = True
        volume_control_row.visible = True
        main_screen_btns_row.visible = True
        await page.update_async()
    else:
        check_connection_col.visible = True
        await page.update_async()

    await page.add_async(
        current_playlist_col,
        pick_folder_text,
        source_text,
        track_name_artist_col,
        control_buttons_row,
        main_screen_btns_row,
        check_connection_col,
        folders_explorer_col,
        explorer_btns_row,
        volume_control_row,
        timers_list_col
    )

    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"

    await page.update_async()

    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

# ---------------------------- ПАРАМЕТРЫ ЗАПУСКА ----------------------------

DEFAULT_FLET_PATH = ''
DEFAULT_FLET_PORT = 8502

if __name__ == "__main__":
    flet_path = os.getenv("FLET_PATH", DEFAULT_FLET_PATH)
    flet_port = int(os.getenv("FLET_PORT", DEFAULT_FLET_PORT))
    ft.app(name=flet_path, target=main, view=None, port=flet_port)
