# Datahandler for Contros pCO2 sensor, output provided by 4HJena

# read output from CONTROS HydroC CO2 instrument
# pandas dataframes are used to hold data

# import modules
from email import message
import pandas as pd
import datetime as dt
import numpy as np
import codecs
import re
import os


def modify_linear_regression_log(linear_regression_log, year, id, start, stop, action):

    """
    action arguments:
        - remove an exisiting period, all other arguments must match a row
        - add a new row to the linear_regression_log, does not add if the given start and stop already exists.
    """
    regression_period = [start, stop]
    try:
        linear_regression_log[year]
        try:
            linear_regression_log[year][id]
            try:
                if action == "remove":
                    if len(linear_regression_log[year][id]["cruise_period"]) != 0:
                        for index, existing_regression_period in enumerate(
                            linear_regression_log[year][id]["cruise_period"]
                        ):
                            print(index, existing_regression_period, regression_period)
                            if regression_period == existing_regression_period:
                                linear_regression_log[year][id][
                                    "cruise_period"
                                ].pop(index)
                                print(
                                    "removed {} from {}".format(
                                        regression_period, year, id
                                    )
                                )
                            else:
                                print("nothing to remove")
                    else:
                        print("nothing to remove")
                if action == "add" and not any(
                    (
                        regression_period == existing_regression_period
                        for existing_regression_period in linear_regression_log[year][
                            id
                        ]["cruise_period"]
                    )
                ):
                    linear_regression_log[year][id]["cruise_period"].append(
                        regression_period
                    )
                elif action == "add":
                    print("{} is already in regression log".format(regression_period))
                    print("current log for {} cruise {}".format(year, id))
            except KeyError:
                linear_regression_log[year][id]["cruise_period"] = [
                    regression_period
                ]
        except KeyError:
            linear_regression_log[year][id] = {
                "cruise_period": [regression_period]
            }
    except KeyError:
        linear_regression_log[year] = {}
        linear_regression_log[year][id] = {"cruise_period": [regression_period]}


def print_linear_regression_log(linear_regression_log):
    print("Year      Cruise      Number  Period")
    for year in linear_regression_log.items():
        for cruise in year[1].items():
            for key, periods in cruise[1].items():
                for number, period in enumerate(periods):
                    print(
                        "{}      {}       {}       {}".format(
                            year[0], cruise[0], number + 1, period
                        )
                    )


def _add_runtime(group):
    group["runtime"] = group - group.iloc[0]
    return group


def add_flag(df, start, stop, flag_string=""):

    start_timestamp = convert_to_timestamp(start)
    stop_timestamp = convert_to_timestamp(stop)

    selection = (df["timestamp"] <= stop_timestamp) & (
        df["timestamp"] >= start_timestamp
    )

    df["Quality"].loc[selection] = flag_string

    return df


def get_valid_data(
    dataframe,
    validation_dict={"Q_flag": ["0: Operate"], "state": ["State_Measure"]},
    condition="or",
):
    combined_filter = bool(len(dataframe))
    for key, value in validation_dict.items():
        for validation_value in value:
            boolean = dataframe[key] == validation_value
            if condition == "and":
                combined_filter = combined_filter & boolean
            elif condition == "or":
                combined_filter = combined_filter | boolean

    return dataframe.loc[combined_filter, :]


def convert_to_timestamp(timestring, format="%Y.%m.%d %H:%M:%S"):

    return dt.datetime.strptime(timestring + " UTC", format + " %Z").timestamp()


def get_numeric_time(datetime_timestamp):

    if type(datetime_timestamp) == pd.Timestamp:
        return datetime_timestamp.replace(tzinfo=dt.timezone.utc).timestamp()
    else:
        return np.nan


def get_datetime_object(timestamp, format="%Y-%m-%d %H:%M:%S"):

    return dt.datetime.strptime(
        dt.datetime.utcfromtimestamp(timestamp).strftime(format), format
    )

def get_datetime_string(timestamp, format="%Y-%m-%d %H:%M:%S"):

    return get_datetime_object(timestamp, format).strftime("%Y.%m.%d %H:%M:%S")


if __name__ == "__main__":

    data_dict = {
        "timestamp": [
            dt.datetime(2009, 10, 12, 10, 10),
            dt.datetime(2009, 10, 12, 10, 10, 11),
            dt.datetime(2009, 10, 12, 10, 10, 31),
            dt.datetime(2009, 10, 12, 10, 10, 35),
        ],
        "value": [4, 5, 3, 2],
        "zero_state": [1, 1, 1, 0],
    }
    data = pd.DataFrame.from_dict(data=data_dict)

    # filter only zero cycle data
    data = data.loc[data.zero_state == 1, :]
