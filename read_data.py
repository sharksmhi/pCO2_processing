#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import filehandler
import datahandler
from correction import Correction

# import modules
import numpy as np
import pandas as pd
import datetime as dt
import scipy.stats as stats
import json

# input


class ProcessData:
    """
    {parameter: [
            {
                'file_date': dt.datetime,
                'file_name': string,
                'file_obj': DirEntry,
                'file_time': dt.datetime,
                'file_type': string,
            }
        ]}
    """

    parameters = [
        "ZeroCycle",
        "State_Zero",
        "State_Flush",
        "Signal_Raw",
        "Signal_Ref",
        "T_Gas",
        "P_In",
        "P_NDIR",
        "PCO2_Corr",
        "Signal_Proc",
    ]

    qc_flags = {
        0: "0: Operate",
        8: "8: undefined",
        10: "10: standby and undefined",
        16: "16: meas delay",
        64: "64: wash",
        128: "128: standby",
        256: "256: empty",
        512: "512: error",
        1024: "1024: undefined 1024",
        2048: "2048: simulated data",
        1040: "1040: meas delay + undefined?",
        4096: "4096: unknown",
        12288: "12416: operate zeroing startup?",
        12416: "12416: standby zeroing startup?",
        16384: "16384: operate flushing?",
        16512: "16512: standby flushing?",
        17408: "17408: unknown",
        28672: "28672: operate switch from zero to flush?",
        28800: "28800: standby switch from zero to flush?",
    }

    def __init__(
        self,
        path,
        regression_period,
        calibration_date="2021-07-06",
        instrumentID="CO2FT-0918-001",
        only_zero_data=False,
    ):
        self.path = path
        self.start = regression_period[0]
        self.stop = regression_period[1]
        self.cruise_dict = {}
        self.calibration = json.load(open("./calibration_data.json"))[instrumentID][
            calibration_date
        ]
        self.only_zero_data = only_zero_data

        self._add_files()
        print("start reading files from {} to {}".format(self.start, self.stop))
        self._read_files()
        if not self.only_zero_data:
            self._reformat_to_columnformat(source="measurements")
            # add information about zeroing, flushing, and washing
            self._add_states()
        self._reformat_to_columnformat(source="zerocycles")

        if not self.only_zero_data:
            # combine measurements and zero readings and sort by timestamp
            self.rawdata_df = pd.concat(
                [
                    self.zerocycles_df,
                    self.measurements_df,
                ],
                ignore_index=True,
            ).sort_values(by=["timestamp"])

        print("#" * 50)
        print("FINISHED. Set up with calibration data from {}".format(calibration_date))
        print("#" * 50)

    def _add_files(self):

        # Sort filepaths after cruise based on cruise dates
        # TODO: add cruise info to folder and/or files to simplify and avoid errors
        # Aim: add SVEPA info on cruise number and ship ID to files/folders.

        for parameter in self.parameters:
            # list files
            if parameter != "ZeroCycle" and not self.only_zero_data:
                filelist = filehandler.filelist(
                    "{}/CO2FT_A_{}".format(self.path, parameter), parameter
                )
            else:
                filelist = filehandler.filelist(self.path, "ZeroCyle")
            # Sort files into cruise by date
            print("add files witin period to list")
            filehandler._add_files_to_cruise(
                cruise_start=self.start,
                cruise_stop=self.stop,
                cruise_dict=self.cruise_dict,
                filelist=filelist,
                filetype=parameter,
            )

    def _read_files(self):
        # read datafiles from between start and stop time
        # Read files for the separate parameters
        # store the data sorted by time in a dictionary with keys for each timestep
        # Zercycle data is in a slightly different format
        # Zerocycle raw data is read and a mean value for each zero cycle is calculated
        self.cruise_dict["timeseries"] = {}
        self.cruise_dict["timeseries"]["measurements"] = {}
        self.cruise_dict["timeseries"]["zerocycles"] = {}

        # read the separate files for each parameter
        for parameter in self.parameters:
            print(parameter)
            if len(self.cruise_dict["{}_files".format(parameter)]) != 0:
                i = 0
                if parameter != "ZeroCycle" and not self.only_zero_data:
                    for file in self.cruise_dict["{}_files".format(parameter)]:
                        datahandler._read_to_timestamp_dict(
                            file_obj=file["file_obj"],
                            parameter=parameter,
                            data_dict=self.cruise_dict["timeseries"]["measurements"],
                            qc_flags=self.qc_flags,
                        )
                        i += 1
                    print(
                        "{} {} files read from cruise from {} to {}".format(
                            parameter, i, self.start, self.stop
                        )
                    )

                else:
                    for file in self.cruise_dict["{}_files".format("ZeroCycle")]:
                        datahandler._read_to_timestamp_dict(
                            file_obj=file["file_obj"],
                            parameter=self.parameters,
                            data_dict=self.cruise_dict["timeseries"]["zerocycles"],
                            qc_flags=self.qc_flags,
                        )
                        i += 1
                    print(
                        "{} {} files read from cruise from {} to {}".format(
                            parameter, i, self.start, self.stop
                        )
                    )
            else:
                raise ValueError("no {} files found in {}".format(parameter, self.path))

    def _reformat_to_columnformat(self, source):

        # source is "zerocycles" or "measurement".
        # "zerocycles" contains data from only the zero cycle with resolution /sec
        # "measurement" contains data from only the zero cycle with resolution /minute

        column_dict = {}
        column_dict["timestamp"] = []

        for timestamp, data in self.cruise_dict["timeseries"][source].items():
            column_dict["timestamp"].append(timestamp)
            for parameter in data.keys():
                if parameter not in column_dict.keys():
                    column_dict[parameter] = []
                column_dict[parameter].append(data.get(parameter, np.nan))

        # the measurement data State Zero and State Flush needs correction
        # values sometimes contains State_X values > 0 and < 1. Set all these to 1.
        if source == "measurements":
            column_dict["State_Flush"] = [
                val if val == 0 else 1 for val in column_dict["State_Flush"]
            ]
            column_dict["State_Zero"] = [
                val if val == 0 else 1 for val in column_dict["State_Zero"]
            ]

        setattr(self, source + "_df", pd.DataFrame.from_dict(column_dict))

        dataframe = getattr(self, source + "_df")
        # 4. Format fixes
        if "Q_flag" not in dataframe.columns:
            dataframe["Q_flag"] = dataframe["Signal_Raw_Quality"]
        dataframe.drop(list(dataframe.filter(regex="_Quality")), axis=1, inplace=True)

        dataframe["datetime_objects"] = [
            datahandler.get_datetime_object(float(x)) for x in dataframe["timestamp"]
        ]

    def _add_cycle_info(
        self, cycle_name, cycle_parameter_name, dataframe_name, get_mean=True
    ):
        dataframe = getattr(self, dataframe_name)
        # get lists of indices for start and stop of each cycle
        # from the cycle_parameter_name column
        start = list(dataframe.index[dataframe[cycle_parameter_name].diff() == 1])
        stop = list(dataframe.index[dataframe[cycle_parameter_name].diff() == -1])
        if start[0] > stop[0]:
            start.insert(0, 0)

        # add columns for storing cycle no and cycle runtime
        dataframe[cycle_name] = np.nan
        dataframe["{}_runtime".format(cycle_name)] = np.nan

        # add cycle information
        for cycle_no, (start, stop) in enumerate(zip(start, stop)):
            dataframe.loc[start:stop, "{}_runtime".format(cycle_name)] = (
                dataframe.loc[start:stop, "timestamp"]
                - dataframe.loc[start, "timestamp"]
            )
            dataframe.loc[start:stop, cycle_name] = int(cycle_no)

    def _add_zero_cycle_details(self):

        # get lists of indices for start and stop of each cycle
        # from the cycle_parameter_name column
        self._add_cycle_info(
            cycle_name="zerocycle",
            cycle_parameter_name="State_Zero",
            dataframe_name="zerocycles_df",
        )

        self._add_cycle_info(
            cycle_name="flushcycle",
            cycle_parameter_name="State_Flush",
            dataframe_name="zerocycles_df",
        )

        self.zerocycles_df["two_beam_signal"] = Correction().raw_signal_conversion(
            self.zerocycles_df["Signal_Raw"],
            self.zerocycles_df["Signal_Ref"],
        )

    def _add_states(self, dataframe_name="measurements_df"):
        dataframe = getattr(self, dataframe_name)

        # introduce State_Measure when no flush or zero
        dataframe["State_Measure"] = 1
        dataframe.loc[
            (dataframe["State_Flush"] > 0) | (dataframe["State_Zero"] > 0),
            "State_Measure",
        ] = 0

        dataframe["State_Wash"] = 0
        dataframe["hour"] = dataframe.timestamp.apply(
            lambda x: dt.datetime.fromtimestamp(x).hour
        )
        # TODO: Add wash state
        dataframe.loc[
            ((dataframe["hour"] <= 19) & (dataframe["hour"] >= 17))
            | ((dataframe["hour"] <= 7) & (dataframe["hour"] >= 5)),
            "State_Wash",
        ] = 1

        dataframe["cruise_runtime"] = (
            dataframe["timestamp"] - dataframe["timestamp"].values[0]
        )

        for state in ["State_Measure", "State_Wash", "State_Flush", "State_Zero"]:
            dataframe.loc[
                dataframe[state] == 1,
                "state",
            ] = state

    def zerocycles_linearregression(self):

        self._add_zero_cycle_details()
        x = []
        y = []
        cycle_no = []
        cycle_means = []
        cycle_all_used = []
        for cycle, cycle_data in self.zerocycles_df.groupby("zerocycle"):
            if np.isnan(cycle):
                continue
            row_selection = (
                (cycle_data.zerocycle_runtime >= 30)  # only use data after 30 sec
                & (cycle_data.State_Zero == 1)  # only use data in zeroing cycle
                & (cycle_data.Q_flag == "0: Operate")  # only flagged as operate
                & ~np.isnan(cycle_data.Signal_Raw)  # skip rows without signal
            )
            times = cycle_data.loc[row_selection, "timestamp"]
            if (
                cycle_data.loc[row_selection]
                .dropna(subset=["timestamp", "two_beam_signal"])
                .empty
            ):
                print("selection empty! In cycle no {}".format(cycle))
                continue

            used_zeros_df = cycle_data.loc[row_selection].dropna(
                subset=["timestamp", "two_beam_signal"]
            )
            cycle_mean_df = used_zeros_df.mean().to_frame().transpose()

            cycle_means.append(cycle_mean_df)
            cycle_all_used.append(used_zeros_df)
            y.append(np.mean(cycle_data["two_beam_signal"]))
            x.append(np.mean(times))
            cycle_no.append(cycle)

        try:
            self.zerocycles_usedvalues_df = pd.concat(cycle_all_used)
        except ValueError as err:
            print(
                "{}. No valid zeroing data within {}-{}. Conditions for valid zero data are: \n-cycle time >30 se\n-State_Zer True\n-Q_flag: '0: Operate'\nSignal Raw not missing".format(
                    err, self.start, self.stop
                )
            )
            raise
        self.zerocycles_mean_df = pd.concat(cycle_means)
        self.zerocycles_mean_df["timestring"] = self.zerocycles_mean_df[
            "timestamp"
        ].apply(lambda x: datahandler.get_datetime_string(x))
        self.zerocycles_mean_df["Q_flag"] = "undefined zeroing mean"
        self.zerocycles_stats = stats.linregress(x, y)

    def process_data(self, dataframe_name="measurements_df", recalculate=False):

        dataframe = getattr(self, dataframe_name).copy()

        # apply conversion from raw signal to two beam signal on all data
        if ("two_beam_signal" not in dataframe.columns) or recalculate:
            dataframe["two_beam_signal"] = Correction().raw_signal_conversion(
                dataframe["Signal_Raw"], dataframe["Signal_Ref"]
            )

        # 2. Collect data from zero cycles
        # and calculate linear regression constants on two beam signal for zerocorrection
        if not hasattr(self, "zerocycles_mean_df"):
            self.zerocycles_linearregression()

        # 3. calculate pCO2 on signals corrected by the zeroings

        # zero signal at each timestamp from regression
        dataframe["two_beam_signal_zero"] = Correction().get_zero_correction(
            dataframe["timestamp"],
            self.zerocycles_stats.slope,
            self.zerocycles_stats.intercept,
        )

        # zero corrected signal
        dataframe["drift_corrected_signal"] = Correction().get_drift_corrected_signal(
            dataframe["two_beam_signal"],
            dataframe["two_beam_signal_zero"],  #
        )
        # processed_signal
        dataframe["processed_signal"] = Correction().get_processed_signal(
            dataframe["drift_corrected_signal"], self.calibration
        )
        # xco2wet
        dataframe["xco2wet"] = Correction().get_xco2wet(
            dataframe["processed_signal"],
            dataframe["T_Gas"],
            dataframe["P_NDIR"],
            self.calibration,
        )
        # pco2
        dataframe["pco2"] = Correction().get_pco2(
            xco2wet=dataframe["xco2wet"], p_in=dataframe["P_In"]
        )

        setattr(self, dataframe_name + "_processed", dataframe)

    def get_valid_data(
        self,
        dataframe,
        validation_dict={"Q_flag": ["0: Operate"], "states": ["Measure"]},
    ):
        combined_filter = bool(len(dataframe))
        for key, value in validation_dict.items():
            print(key)
            for validation_value in value:
                print(validation_value)
                pandas_logical = dataframe[key] == validation_value
                combined_filter = combined_filter & pandas_logical

        return dataframe.loc[combined_filter, :]

    def save_processed_data(self, path):

        self.processed_data = self.get_valid_data(
            self.measurements_df_processed,
            validation_dict={"Q_flag": ["0: Operate"], "state": ["State_Measure"]},
        )
        self.processed_data["k1"] = self.calibration["k1"]
        self.processed_data["k2"] = self.calibration["k2"]
        self.processed_data["k3"] = self.calibration["k3"]
        self.processed_data["calibration date"] = self.calibration["calibration date"]
        self.processed_data["zero_correction_slope"] = self.zerocycles_stats.slope
        self.processed_data[
            "zero_correction_intercept"
        ] = self.zerocycles_stats.intercept

        pd.DataFrame(self.processed_data).to_csv(
            open(
                "{}/{}-{}_processed_data.txt".format(path, self.start, self.stop),
                "w",
            ),
            sep="\t",
            index=False,
        )

    def save_raw_data(self, path):
        # save to textfile
        self.rawdata_df.to_csv(
            open("{}/{}-{}_all_raw_data.txt".format(path, self.start, self.stop), "w"),
            sep="\t",
            index=False,
        )

    def save_df_data(self, path, df_name):
        # save to textfile
        getattr(self, df_name).to_csv(
            open("{}/{}-{}_{}.txt".format(path, self.start, self.stop, df_name), "w"),
            sep="\t",
            index=False,
        )


"""
# reformat to dataframe and save to txt file
column_dict_measurements = {}
column_dict_measurements["timestamp"] = []

# reformat measurements
for timestamp, data in cruise_data["timeseries"]["measurements"].items():
    column_dict_measurements["timestamp"].append(timestamp)
    for parameter in data.keys():
        if parameter not in column_dict_measurements.keys():
            column_dict_measurements[parameter] = []
        column_dict_measurements[parameter].append(data.get(parameter, np.nan))

column_dict_zerocycle = {}
column_dict_zerocycle["timestamp"] = []

# reformat zero readings
for timestamp, data in cruise_data["timeseries"]["zero_cycle"].items():
    column_dict_zerocycle["timestamp"].append(timestamp)
    for parameter in data.keys():
        if parameter not in column_dict_zerocycle.keys():
            column_dict_zerocycle[parameter] = []
        column_dict_zerocycle[parameter].append(data.get(parameter, np.nan))

column_dict_measurements["State_Flush"] = [
    val if val == 0 else 1 for val in column_dict_measurements["State_Flush"]
]
column_dict_measurements["State_Zero"] = [
    val if val == 0 else 1 for val in column_dict_measurements["State_Zero"]
]

# combine measurements and zero readings and sort by timestamp
rawdata_df = pd.concat(
    [
        pd.DataFrame.from_dict(column_dict_zerocycle),
        pd.DataFrame.from_dict(column_dict_measurements),
    ],
    ignore_index=True,
).sort_values(by=["timestamp"])

# save to textfile
rawdata_df.to_csv(
    open(
        "processed_data/{}-{}_all_raw_data.txt".format(cruise_start, cruise_stop), "w"
    ),
    sep="\t",
    index=False,
)
"""
if __name__ == "__main__":

    path = "./data/CO2FT_A"
    path_co2 = "/CO2FT_A"
    path = "//winfs-proj/proj/havgem/EXPRAPP/Exprap2021/Svea_v45_november/efter resan/data/Ferrybox/Working/DeviceData/CO2FT_A"
    path = (
        "//winfs-proj/proj/havgem/EXPRAPP/Exprap2021/Svea_v49-50_december/data/Ferrybox/Working/DeviceData"
        + path_co2
    )
    cruise_start = "2021-12-06"
    cruise_stop = "2021-12-18"
