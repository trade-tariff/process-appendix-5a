import os


def make_folder(folder):
    if not os.path.exists(folder):
        os.mkdir(folder)

def do_boolean(s):
    try:
        s = str(s).strip().lower()
    except Exception as e:
        s = ""
    if s in ("false", "0", "n", "no", "none", "null", ""):
        return False
    else:
        return True