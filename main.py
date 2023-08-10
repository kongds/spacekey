import os
import sys
import time
import Quartz
import threading
import subprocess
from pynput import keyboard
from pynput.keyboard._darwin import KeyCode
from pynput.keyboard import Key, Controller

keycon = Controller()
#DEBUG = True
DEBUG = False

# not map t
app_key_map = {
    'i': '/Applications/iTerm.app',
    'e': '/Applications/Emacs.app',
    'r': '/Applications/Safari.app',
    'g': '/Applications/WeChat.app',
    'm': '/System/Applications/Music.app',
    'n': '/Applications/NeteaseMusic.app',
}

cond_key_map = {
    'd': lambda: [42, 'ctrl'] if front_app == 'Emacs' else 'toggle_input'
}

key_key_map = {
    'k': [Key.backspace.value.vk,],
    'j': [Key.enter.value.vk,],
    'h': [Key.esc.value.vk,],
    'o': [11, 'ctrl'], # B 11 from https://github.com/caseyscarborough/keylogger/blob/088f486e16c0bf8bd5a141d02ec59da43aa042c6/keylogger.c#L115
    'l': [3, 'ctrl'], # F 3
    'f': [3, 'ctrl', 'alt', 'cmd', 'shift'], # f8
    '': [4, 'cmd'], # cmd 1

    # "1": [18, 'shift'],
    # "2": [19, 'shift'],
    # "3": [20, 'shift'],
    # "4": [21, 'shift'],
    # "6": [22, 'shift'],
    # "5": [23, 'shift'],
    # "=": [24, 'shift'],
    # "9": [25, 'shift'],
    # "7": [26, 'shift'],
    # "-": [27, 'shift'],
    # "8": [28, 'shift'],
    # "0": [29, 'shift'],
    # "]": [30, 'shift'],
    # "[": [33, 'shift'],
    # "'": [39, 'shift'],
    # ";": [41, 'shift'],
    # "\\": [42, 'shift'],
    # ",": [43, 'shift'],
    # "/": [44, 'shift'],
    # ".": [47, 'shift'],
    # "`": [50, 'shift'],

}

disable_apps = []

front_app = None
spacedown = False
spaceotherkey = False
disable_p_once = False
disable_r_once = False
cmd_down = False
disable_space = False

wait_space_up_cmds = []

def get_front_app():
    global front_app
    for l in subprocess.check_output('lsappinfo').decode('utf8').split('\n'):
        if '(in front)' in l:
            front_app = l.split('"')[1]


menu_hide = False
def set_menu_visible(hide=False, force=False):
    global menu_hide
    if force: menu_hide = not hide
    if hide:
        if not menu_hide:
            os.system("osascript -e 'tell application \"System Events\"' -e 'set autohide menu bar of dock preferences to true' -e 'end tell'")
        menu_hide = True
    else:
        if menu_hide:
            os.system("osascript -e 'tell application \"System Events\"' -e 'set autohide menu bar of dock preferences to false' -e 'end tell'")
        menu_hide = False


hide_apps = {'微信': 'g', '音乐': 'm', '网易云音乐': 'n'}

def spaceit(key_char):
    global spacedown
    begin = time.time()
    if key_char in app_key_map:
        if key_char == 'e' and hide_menu_for_emacs:
            set_menu_visible(hide=True)

        os.system('open ' + app_key_map[key_char])
        if  front_app in hide_apps and hide_apps[front_app] != key_char:
            os.system(f"osascript -e 'tell application \"Finder\"' -e 'set visible of process \"{front_app}\" to false' -e 'end tell'")

        if key_char not in 'ei' and not os.path.exists('/Users/royokong/.eaf-showing'):
            set_menu_visible(hide=False, force=True)
        print('open app', time.time() - begin)
    elif key_char in cond_key_map:
        key_cmd = cond_key_map[key_char]()
        if type(key_cmd) is str:
            # toggle input simulate key strike
            # if we press space, it will make the key down
            if key_cmd == 'toggle_input' and spacedown and\
               'toggle_input' not in wait_space_up_cmds:
                wait_space_up_cmds.append(key_cmd)
            else:
                os.system(key_cmd)
    else:
        return True

def on_press(key):
    global spacedown
    global disable_p_once, spaceotherkey, cmd_down
    if DEBUG:
        print('p', key)

    if key in [Key.cmd, Key.cmd_r, Key.cmd_l]:
        cmd_down = True
    elif key == Key.space and not cmd_down and not disable_space:
        if not disable_p_once:
            spacedown = True
            spaceotherkey = False
            # print('space')
        else:
            disable_p_once = False
    elif spacedown and hasattr(key, 'char'):
        # on_press, on_release should not block
        threading.Thread(target=spaceit, args=(key.char,)).start()
        spaceotherkey = True

kill_self = False
restar_listener = True
def on_release(key):
    global spacedown, restar_listener, kill_self
    global disable_r_once, disable_p_once, cmd_down

    if DEBUG:
        print('r', key)
    if hasattr(key, 'vk') and key.vk == 0 and key.char != 'a':
        try:
            import datetime
            current_time = datetime.datetime.now()
            print(current_time, 'restart listener')
            # kill_self = True
            # restar_listener = True
        except AttributeError:
            pass

    if key in [Key.cmd, Key.cmd_r, Key.cmd_l]:
        cmd_down = False
    elif key == Key.space and not cmd_down and not disable_space:
        if not disable_r_once:
            spacedown = False
            if not spaceotherkey:
                disable_p_once = True
                disable_r_once = True
                keycon.press(Key.space)
                keycon.release(Key.space)
                #keycon.press(Key.backspace)
                #keycon.release(Key.backspace)
        else:
            disable_r_once = False

        for cmd in wait_space_up_cmds:
            threading.Thread(target=os.system, args=(cmd,)).start()
        wait_space_up_cmds.clear()
    elif spacedown == True:
        if DEBUG:
            print('{0} released'.format(key), disable_space, key, type(key))

def darwin_intercept(event_type, event):
    length, chars = Quartz.CGEventKeyboardGetUnicodeString(
        event, 100, None, None)
    if chars == ' ' and not cmd_down and not disable_space:
        return None
    elif spacedown:
        if chars in key_key_map or \
           (chars in cond_key_map and type(cond_key_map[chars]()) is list):
            key_cmd = key_key_map[chars] if chars in key_key_map else cond_key_map[chars]()
            key = key_cmd[0]
            Quartz.CGEventSetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode, key)
            event_flags = 0
            for mod in key_cmd[1:]:
                if mod == "shift":
                    event_flags += Quartz.kCGEventFlagMaskShift
                elif mod == "caps":
                    event_flags += Quartz.kCGEventFlagMaskAlphaShift
                elif mod == "alt":
                    event_flags += Quartz.kCGEventFlagMaskAlternate
                elif mod == "ctrl":
                    event_flags += Quartz.kCGEventFlagMaskControl
                elif mod == "cmd":
                    event_flags += Quartz.kCGEventFlagMaskCommand
            Quartz.CGEventSetFlags(event, event_flags)

            return event
        return None
    return event

listener = None
hide_menu_for_emacs = True

while not kill_self:
    if restar_listener:
        restar_listener = False
        front_app = None
        spacedown = False
        spaceotherkey = False
        disable_p_once = False
        disable_r_once = False
        cmd_down = False
        disable_space = False

        if listener is not None:
            listener.stop()
        listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release,
            darwin_intercept=darwin_intercept)
        listener.start()

    time.sleep(0.2)
    display_list = subprocess.check_output('m1ddc display list'.split()).decode('utf-8')
    if len(display_list) == 0: #or 'DELL U2412M' in display_list:
        hide_menu_for_emacs = False
    else:
        hide_menu_for_emacs = True

    get_front_app()

    if front_app == 'Emacs' and hide_menu_for_emacs:
        set_menu_visible(hide=True)
    elif not os.path.exists('/Users/royokong/.eaf-showing'):
        #set_menu_visible(hide=False)
        pass

    if front_app in disable_apps:
        disable_space = True
    else:
        disable_space = False

if listener is not None:
    listener.stop()
