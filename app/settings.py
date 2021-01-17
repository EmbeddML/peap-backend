from os.path import normpath, dirname, join

PROJECT_DIRECTORY = normpath(join(dirname(__file__)))
DATA_DIRECTORY = join(PROJECT_DIRECTORY, "data")
