#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from fileinput import filename
import os
import datetime as dt
import re


def filelist(directory, file_type, sep=" "):

    #print(directory)
    # list files
    earliest_date = dt.datetime.strptime("21000101", "%Y%m%d")
    latest_date = dt.datetime.strptime("19000101", "%Y%m%d")
    file_list = []
    i = 0
    for obj in os.scandir(directory):
        if not obj.is_file():
            continue
        file_obj = obj
        file_name = file_obj.name.replace(".txt", "")
        # if space is not used as separator try under score.
        # FIX: Filename formats need to be consistent!
        file_name_split = re.split(' |_',file_name)
        try:
            file_date = dt.datetime.strptime(file_name_split[-2], "%Y%m%d")
            file_date_string = file_name_split[-2]
        except ValueError:
            try:
                file_date = dt.datetime.strptime(file_name_split[-1], "%Y%m%d")
                file_date_string = file_name_split[-1]
            except ValueError:
                print(file_name)
                exit()
                continue
        try:
            file_time = dt.datetime.strptime(
                file_date_string + file_name_split[-1], "%Y%m%d%H%M%S"
            )
        except ValueError:
            file_time = file_date
        i += 1
        file_list.append(
            {
                "file_date": file_date,
                "file_name": file_name,
                "file_obj": file_obj,
                "file_time": file_time,
                "file_type": file_type,
                "file_path": file_obj.path
            }
        )

        earliest_date = min(earliest_date, file_date)
        latest_date = max(latest_date, file_date)
    if len(file_list) == 0:
        pass#print("{} files in list".format(len(file_list)))
    else:
        pass#print("{} files in list".format(len(file_list)))
        #print("from {} to {}".format(earliest_date.strftime("%Y-%m-%d"), latest_date.strftime("%Y-%m-%d")))
    return file_list


def _add_files_to_cruise(cruise_start, cruise_stop, cruise_dict, filelist, filetype):

    if "{}_files".format(filetype) not in cruise_dict.keys():
        cruise_dict["{}_files".format(filetype)] = []
    start = dt.datetime.fromisoformat(cruise_start)
    stop = dt.datetime.fromisoformat(cruise_stop)
    for file in filelist:
        if start <= file["file_date"] <= stop:
            cruise_dict["{}_files".format(filetype)].append(file)

    if len(cruise_dict["{}_files".format(filetype)]) == 0:
        "no {} files within period".format(filetype)
        return False

    return cruise_dict
