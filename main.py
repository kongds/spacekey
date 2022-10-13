import os
import time
import Quartz
import subprocess
from pynput import keyboard
from pynput.keyboard import Key, Controller

keycon = Controller()

app_key_map = {
    'i': '/Applications/iTerm.app',
    'e': '/Applications/Emacs.app',
    'r': '/Applications/Safari.app',
    'g': '/Applications/WeChat.app',
    'm': '/System/Applications/Music.app',
    'n': '/Applications/NeteaseMusic.app',
    #'f': '"/Applications/Alfred 4.app"'
}

key_key_map = {
    'k': [Key.backspace.value.vk,],
    'j': [Key.enter.value.vk,],
    'h': [Key.esc.value.vk,],
    'o': [11, 'ctrl'], # B 11 from https://github.com/caseyscarborough/keylogger/blob/088f486e16c0bf8bd5a141d02ec59da43aa042c6/keylogger.c#L115
    'l': [3, 'ctrl'], # F 3
    'f': [3, 'ctrl', 'alt', 'cmd', 'shift'], # f8
    'u': [42, 'ctrl'], # ctrl \
    '': [4, 'cmd'], # cmd 1
}
               #'f': [Key.f18.value.vk, 'ctrl'],}

disable_apps = []

front_app = None
spacedown = False
spaceotherkey = False
disable_p_once = False
disable_r_once = False
cmd_down = False
disable_space = False

def get_front_app():
    global front_app
    for l in subprocess.check_output('lsappinfo').decode('utf8').split('\n'):
        if '(in front)' in l:
            front_app = l.split('"')[1]

def spaceit(key_char):
    global spacedown
    if key_char in app_key_map:
        get_front_app()
        os.system('open ' + app_key_map[key_char])
        if  front_app in ['微信', 'iTerm2', '音乐', '网易云音乐']:
            # hide wechat
            os.system(f"osascript -e 'tell application \"Finder\"' -e 'set visible of process \"{front_app}\" to false' -e 'end tell'")
    else:
        return True

def on_press(key):
    global spacedown
    global disable_p_once, spaceotherkey, cmd_down
    print('p', key)

    if key in [Key.cmd, Key.cmd_r, Key.cmd_l]:
        cmd_down = True
    elif key == Key.space and not cmd_down and not disable_space:
        if not disable_p_once:
            spacedown = True
            spaceotherkey = False
            print('space')
        else:
            disable_p_once = False
    elif spacedown:
        try:
            spaceit(key.char)
            spaceotherkey = True
        except AttributeError:
            pass

def on_release(key):
    global spacedown
    print('r', key)
    global disable_r_once, disable_p_once, cmd_down

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
    elif spacedown == True:
        print('{0} released'.format(
        key))

def darwin_intercept(event_type, event):
    length, chars = Quartz.CGEventKeyboardGetUnicodeString(
        event, 100, None, None)
    if chars == ' ' and not cmd_down and not disable_space:
        return None
    elif spacedown:
        if chars in key_key_map:
            key = key_key_map[chars][0]
            Quartz.CGEventSetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode, key)
            event_flags = 0
            for mod in key_key_map[chars][1:]:
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

# Collect events until released
# with keyboard.Listener(
#         on_press=on_press,
#         on_release=on_release,
#         darwin_intercept=darwin_intercept) as listener:
#     listener.join()


# ...or, in a non-blocking fashion:
listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release,
    darwin_intercept=darwin_intercept)
listener.start()

while True:
    time.sleep(2)

    get_front_app()
    if front_app in disable_apps:
        disable_space = True
    else:
        disable_space = False
