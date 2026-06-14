# START_VERSION_BLOCK
VERSION_MAJOR = 0
VERSION_MINOR = 1
VERSION_BUILD = 11
VERSION_ALPHA = 1
# END_VERSION_BLOCK

__version__ = "{}.{}.{}{}".format(VERSION_MAJOR, VERSION_MINOR, VERSION_BUILD,
                                   "a{}".format(VERSION_ALPHA) if VERSION_ALPHA else "")

if __name__ == "__main__":
    print(__version__)
