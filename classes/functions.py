import os


def make_folder(folder):
    if not os.path.exists(folder):
        os.mkdir(folder)
