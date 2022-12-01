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
                    if len(linear_regression_log[year][id]["regression_periods"]) != 0:
                        for index, existing_regression_period in enumerate(
                            linear_regression_log[year][id]["regression_periods"]
                        ):
                            print(index, existing_regression_period, regression_period)
                            if regression_period == existing_regression_period:
                                linear_regression_log[year][id][
                                    "regression_periods"
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
                        ]["regression_periods"]
                    )
                ):
                    linear_regression_log[year][id]["regression_periods"].append(
                        regression_period
                    )
                elif action == "add":
                    print("{} is already in regression log".format(regression_period))
                    print("current log for {} cruise {}".format(year, id))
            except KeyError:
                linear_regression_log[year][id]["regression_periods"] = [
                    regression_period
                ]
        except KeyError:
            linear_regression_log[year][id] = {
                "regression_periods": [regression_period]
            }
    except KeyError:
        linear_regression_log[year] = {}
        linear_regression_log[year][id] = {"regression_periods": [regression_period]}


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
    """
def convert_to_timestamp(timestring, format="%Y.%m.%d %H:%M:%S"):

    return dt.datetime.strptime(timestring, format).timestamp()"""


def get_valid_data(
    dataframe,
    validation_dict={"Q_flag": ["0: Operate"], "state": ["Measure"]},
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


def _read_file_to_pandas(file_obj, header_line_no):
    data = pd.read_csv(
        open(os.path.normpath(file_obj.path)),
        sep="\t",
        skiprows=list(range(0, header_line_no - 1)) + [header_line_no],
        parse_dates=[0],
        infer_datetime_format=True,
    )
    # skiprows=list(range(0, 33)) + [34],
    return data


def _read_to_timestamp_dict(
    file_obj,
    parameter,
    data_dict,
    qc_flags,
    file_encoding="cp1252",
    comment_id="$",
    column_separator="\t",
):

    header = []
    header_line = []
    with codecs.open(os.path.normpath(file_obj.path), encoding=file_encoding) as fid:
        i = 0
        for line in fid:

            if "\x00" in line:
                print("\x00 format error in {} on line {}".format(file_obj.path, i))
                continue
            if line.startswith(comment_id):
                header.append(line)
            else:
                if not header_line:
                    header_line = header[-2]
                    header_line = re.split(column_separator, header_line.strip("\n\r"))
                    header_line = [item.strip("$") for item in header_line]
                split_line = re.split(column_separator, line.strip("\n\r"))
                split_line = [item.strip() for item in split_line]
                timestring = split_line[header_line.index("Timestamp")]
                timestamp = convert_to_timestamp(timestring)
                info = add_parameter_to_timestamp_in_dict(
                    data_dict, timestamp, "timestring", timestring
                )

                if isinstance(parameter, str):
                    value = split_line[header_line.index("Quality")]
                    info = add_parameter_to_timestamp_in_dict(
                        data_dict,
                        timestamp,
                        "{}_Quality".format(parameter),
                        qc_flags.get(int(value), "{}: unknown".format(str(value))),
                    )
                    value = float(split_line[header_line.index(parameter)])
                    info = add_parameter_to_timestamp_in_dict(
                        data_dict, timestamp, parameter, value
                    )

                else:
                    zero_parameters = parameter
                    value = split_line[header_line.index("Quality")]
                    info = add_parameter_to_timestamp_in_dict(
                        data_dict,
                        timestamp,
                        "{}_Quality".format("Signal_Raw"),
                        qc_flags.get(int(value), "{}: unknown".format(str(value))),
                    )
                    for zero_parameter in zero_parameters:
                        if zero_parameter != "ZeroCycle":
                            value = float(split_line[header_line.index(zero_parameter)])
                            info = add_parameter_to_timestamp_in_dict(
                                data_dict, timestamp, zero_parameter, value
                            )
            i = i + 1


def add_parameter_to_timestamp_in_dict(data_dict, timestamp, key, value):
    if timestamp not in data_dict.keys():
        data_dict[timestamp] = {}
    if key not in data_dict[timestamp].keys():
        data_dict[timestamp][key] = value
        return True, "{} added to datadict".format(key)
    elif value != data_dict[timestamp][key]:
        try:
            mean_value = (float(data_dict[timestamp][key])+ value)/2
        except ValueError:
            mean_value = value
        message = "{}: {} already added at {} ({}) but with different value, {}. Using mean value {}".format(key, value, timestamp, dt.datetime.fromtimestamp(timestamp), data_dict[timestamp][key], mean_value)
        data_dict[timestamp][key] = mean_value
        # TODO: return warning/log when key, value already added at timestamp
        return False, message


def _read_to_dataframe(
    file_obj, file_encoding="cp1252", comment_id="$", column_separator="\t"
):

    header_line = []
    header = []
    comment = []
    data = []
    with codecs.open(os.path.normpath(file_obj.path), encoding=file_encoding) as fid:
        for line in fid:
            if "\x00" in line:
                continue
            if line.startswith(comment_id) and len(data) == 0:
                header.append(line)
            elif line.startswith(comment_id):
                comment.append(line)
            else:
                if not header_line:
                    header_line = header[-2]
                    header_line = re.split(column_separator, header_line.strip("\n\r"))
                    header_line = [item.strip("$") for item in header_line]
                split_line = re.split(column_separator, line.strip("\n\r"))
                split_line = [item.strip() for item in split_line]
                data.append(split_line)

    df = _read_file_to_pandas(file_obj=file_obj, header_line_no=len(header) - 1)
    return header[-2], df


def _add_cycle_details(data, cycle_no, cycle_name=""):

    data.rename(columns={"$Timestamp": "timestamp"}, inplace=True)
    cycle_runtime = data["timestamp"] - data["timestamp"].values[0]
    data["{}cycle_runtime".format(cycle_name)] = cycle_runtime
    data["{}cycle".format(cycle_name)] = cycle_no

    return data


def _get_cycle_runtime(data):

    cycle_runtime = data["timestamp"] - data["timestamp"].values[0]

    return cycle_runtime


def _mean_of_cycle(data, setup_time=30, data_dict={}):
    """
    Calculates mean of raw and reference signal during a zero cycle
    setup_time in seconds
    """

    row_selection = (data.zerocycle_runtime >= setup_time) & (data.State_Zero == 1)

    cycle = data.loc[row_selection].agg(
        {
            "timestamp": "max",
            "Signal_Raw": "mean",
            "Signal_Ref": "mean",
            "Longitude": "mean",
            "Latitude": "mean",
        }
    )

    timestamp = cycle.timestamp
    Signal_Raw = cycle.Signal_Raw
    Signal_Ref = cycle.Signal_Ref

    if data_dict:
        if timestamp not in data_dict.keys():
            data_dict["timestamp"] = {}
        if "Signal_Raw_Z" not in data_dict["timestamp"].keys():
            data_dict["timestamp"]["Signal_Raw_Z"] = Signal_Raw
        if "Signal_Ref_Z" not in data_dict["timestamp"].keys():
            data_dict["timestamp"]["Signal_Ref_Z"] = Signal_Ref

    return (
        data.loc[row_selection]
        .agg(
            {
                "timestamp": "max",
                "Signal_Raw": "mean",
                "Signal_Ref": "mean",
                "Longitude": "mean",
                "Latitude": "mean",
            }
        )
        .to_frame()
        .transpose()
    )


def _concat_dataframes_in_cruise(data_list):

    dataframe = pd.concat(data_list)
    runtime = dataframe["timestamp"] - dataframe["timestamp"].values[0]
    dataframe["runtime"] = runtime  # .astype("timedelta64[s]")
    dataframe["month"] = dataframe["timestamp"].dt.month_name()

    return dataframe


def _mean_of_zero_cycles(zero_data, setup_time=30):

    row_selection = (zero_data.cycle_runtime >= setup_time) & (
        zero_data.State_Zero == 1
    )

    return (
        zero_data.loc[row_selection]
        .groupby("cycle")
        .agg({"timestamp": "max", "Signal_Raw": "mean", "Signal_Ref": "mean"})
    ).reset_index()


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
