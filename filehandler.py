#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import datetime as dt


def filelist(directory, file_type, sep=" "):

    print(directory)
    # list files
    file_list = []
    i = 0
    for obj in os.scandir(directory):
        if not obj.is_file():
            continue
        file_obj = obj
        file_name = file_obj.name
        # if space is not used as separator try under score.
        # FIX: Filename formats need to be consistent!
        if file_name.split(sep)[0] == file_name:
            sep = "_"
        file_name_split = file_name.replace(".txt", "").split(sep)
        for string in file_name_split:
            try:
                file_date = dt.datetime.strptime(string, "%Y%m%d")
                file_date_string = string
            except ValueError:
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
            }
        )
    print("{} files in list".format(len(file_list)))

    return file_list


def _add_files_to_cruise(cruise_start, cruise_stop, cruise_dict, filelist, filetype):

    if "{}_files".format(filetype) not in cruise_dict.keys():
        cruise_dict["{}_files".format(filetype)] = []
    start = dt.datetime.fromisoformat(cruise_start)
    stop = dt.datetime.fromisoformat(cruise_stop)
    for file in filelist:
        if start <= file["file_date"] <= stop:
            cruise_dict["{}_files".format(filetype)].append(file)

    return cruise_dict
