from pathlib import Path

# provide absolute paths
PAN_DIR_SCR = str(Path(__file__).absolute().parent)
PAN_DIR_PARENT = PAN_DIR_SCR.replace("/SCR", "")
PAN_DIR_PARENT2 = PAN_DIR_SCR.replace("/panelification/SCR", "")

PAN_DIR_TMP = PAN_DIR_PARENT + "/TMP/"
PAN_DIR_PLOTS = PAN_DIR_PARENT + "/PLOTS/"
PAN_DIR_SCORES = PAN_DIR_PARENT + "/SCORES/"
PAN_DIR_DATA = PAN_DIR_PARENT + "/DATA/"
PAN_DIR_MODEL = PAN_DIR_PARENT + "/MODEL/"
PAN_DIR_MODEL2 = PAN_DIR_PARENT2 + "/models/"
PAN_DIR_OBS = PAN_DIR_PARENT + "/OBS/"
PAN_DIR_OBS_ARCH = PAN_DIR_PARENT + "/OBS_archive/"
