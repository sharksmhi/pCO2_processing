#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from csv import excel_tab
import filehandler
import datahandler
from correction import Correction

# import modules
import numpy as np
import pandas as pd
import datetime as dt
import scipy.stats as stats
import json
import os

# input


class RawData:

    def __init__(self):
        """
        Class to read and hold rawdata from selected file
        """

        self.metadata = {
            "METADATA": {},
            "QUALITYBITS": {},
            "INFOBITS": {},
            "FORMATS": {},
            "DATASETS": {},
        }

    def _readfile(self, file_path):
        comment = "$"
        self.metadata = []
        with open(file_path, "r") as f:
            for i, line in enumerate(f):
                if line.startswith(comment):
                    self.metadata.append(line.replace("$", ""))
                else:
                    self.header_line = i - 2
                    f.close()
                    break
        try:
            self.data = pd.read_csv(
                open(file_path),
                sep="\t",
                header=self.header_line,
                skiprows=[self.header_line + 1],
                parse_dates=["$Timestamp"],
                infer_datetime_format=True,
                dtype={"Quality": "int"},
            )
        except ValueError as e:
            print(file_path)
            data = pd.read_csv(
                open(file_path),
                sep="\t",
                header=self.header_line,
                skiprows=[self.header_line + 1])
            print(f'data.head():\n{data.head()}')
            print(f'data.dtypes: {data.dtypes}')
            print(data.loc[data['Quality'].apply(pd.isna)])
            raise e

        self.data.rename(columns={"$Timestamp": "timestamp"}, inplace=True)
        self.data["timestamp"].apply(pd.to_datetime).dt.strftime("%Y-%m-%d %H:%M:%S")
        self.data["timenumeric"] = self.data["timestamp"].apply(
            lambda x: x.value
        )

    def _get_metadata(self):

        for key in self.metadata:
            continue

    def _set_qc_flags(self):

        self.data["Q_flag"] = self.data["Quality"].copy()

class Cruise:

    parameters = [
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

    file_names = ["ZeroCycle"] + parameters

    """
    self.measurements_df
    self.zerocycles_df"""

    def __init__(self, path, cruise_period, data_save_path = False):

        self.path = path
        self.start = cruise_period[0]
        self.stop = cruise_period[1]
        self.cruise_dict = {}
        self.only_zero_data = False
        self._read_data()
        self._merge_measurement_data()
        if data_save_path:
            self._save_data(data_save_path)

    def _add_files(self):

        # Sort filepaths after cruise based on cruise dates
        # TODO: add cruise info to folder and/or files to simplify and avoid errors
        # Aim: add SVEPA info on cruise number and ship ID to files/folders.
        # log instead:
        # print("add filenames to filelist")
        # log instead:
        print("find files within period {} to {}".format(self.start, self.stop))
        files_found = False
        for filename in self.file_names:
            # list files
            # print(parameter, files_found)
            if filename != "ZeroCycle" and not self.only_zero_data:
                filelist = filehandler.filelist(
                    f"{self.path}/CO2FT_A_{filename}", filename
                )
                # print(parameter)
            else:
                filelist = filehandler.filelist(self.path, filename)
            # Sort files into cruise by date
            if filehandler._add_files_to_cruise(
                cruise_start=self.start,
                cruise_stop=self.stop,
                cruise_dict=self.cruise_dict,
                filelist=filelist,
                filetype=filename,
            ):
                files_found = True
            else:
                files_found = False
                # print("files found")

        if not files_found:
            print(
                "WARNING: no files found in period {} to {}".format(
                    self.start, self.stop
                )
            )
            self.valid = False

    def _read_data(self):

        self._add_files()
        for filename in self.file_names:
            assert (
                len(self.cruise_dict["{}_files".format(filename)]) > 0
            ), "no {} files found in {} for period {}-{}".format(
                filename, self.path, self.start, self.stop
            )
            parameter_dflist = []
            for file in self.cruise_dict["{}_files".format(filename)]:
                data = RawData()
                data._readfile(file["file_obj"].path)
                parameter_dflist.append(data.data)
            parameter_df = pd.concat(parameter_dflist)
            setattr(
                self, f"{filename}", parameter_df.reset_index().drop(columns=["index"])
            )
            # log instead:
            # print(f"filename: {filename}")

    def _merge_measurement_data(self):

        df_list = []

        for parameter in self.parameters:
            df = getattr(self, f"{parameter}")[
                ["timestamp", parameter, "Quality"]
            ]
            df.rename(columns={"Quality": f"Quality_{parameter}"}, inplace=True)
            #df.rename(columns={"Q_flag": f"Q_flag_{parameter}"}, inplace=True)
            df_list.append(df.set_index("timestamp"))

        merged_df = pd.concat(df_list, axis=1)
        merged_df.reset_index(level=0, inplace=True)
        if merged_df["timestamp"].dtype != "datetime64[ns]":
            raise TypeError
        #qc_cols = [col for col in merged_df.columns if "Q_flag" in col]
        qc_cols = [col for col in merged_df.columns if "Quality" in col]

        merged_df["flag_check"] = ""
        for index, series in merged_df[qc_cols].iterrows():
            if len(series.unique()) > 1:
                qc_flag = f"conflicting flags {', '.join(series.unique().astype(str))}"
            else:
                qc_flag = str(series.unique()[0].astype(str))
            merged_df.loc[index, "flag_check"] = qc_flag

        merged_df['Quality'] = merged_df['Quality_Signal_Raw'].copy()
        merged_df["timenumeric"] = merged_df["timestamp"].apply(
            lambda x: x.value
        )

        self.measurement_data = merged_df

    def _save_data(self, data_save_path):

        if not data_save_path:
            # log instead:
            # print('no save path given')
            return

        today = dt.datetime.today().strftime('%Y-%m-%d')

        if not os.path.exists(f"{data_save_path}/{today}"):
            os.mkdir(f"{data_save_path}/{today}")

        save_path = f"{data_save_path}/{today}/{self.start}_{self.stop}"


        self.ZeroCycle.to_csv(
            f"{save_path}_zeroings.txt",
            sep="\t",
            index=False,
        )
        print(f"zerocycle rawdata saved to {save_path}_zeroings.txt")
        self.measurement_data.to_csv(
            f"{save_path}_measurements.txt",
            sep="\t",
            index=False,
        )
        print(f"measurement rawdata saved to {save_path}_measurements.txt")

    def get_data_package(self):
        """
        Get a package of two dataframes
        1. measurements
        2. zerocycle (high res)
        """

        return self.measurement_data, self.ZeroCycle


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

    file_names = ["ZeroCycle"] + parameters

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
        12288: "12288: operate zeroing startup?",
        12416: "12416: standby zeroing startup?",
        16384: "16384: flush",
        16512: "16512: standby flushing?",
        17408: "17408: unknown",
        28672: "28672: operate switch from zero to flush?",
        28800: "28800: standby switch from zero to flush?",
    }

    def __init__(
        self,
        data_save_path,
        measurements,
        zerocycles,
        regression_period,
        calibration_date="2021-07-06",
        instrumentID="CO2FT-0918-001",
    ):

        self.data_save_path = data_save_path
        self.measurements_df = measurements
        self.zerocycles_df = zerocycles
        self.start = regression_period[0]
        self.stop = regression_period[1]
        self.cruise_dict = {}
        self.calibration_date = calibration_date
        with open("./calibration_data.json") as fid:
            self.calibration = json.load(fid)[instrumentID][calibration_date]
        self.valid = True

        self.check_format()

    def check_format(self):

        if self.measurements_df["timestamp"].dtype != "datetime64[ns]":
            raise TypeError
        if self.zerocycles_df["timestamp"].dtype != "datetime64[ns]":
            raise TypeError
        if "Q_flag" not in self.measurements_df.columns:
            self.measurements_df['Q_flag'] = self.measurements_df['Quality'].copy()
            self.measurements_df.replace({'Q_flag': self.qc_flags}, inplace = True)

    def _check_data_quality(self, dataframe):

        return self._check_operate_flag_exists(dataframe)

    def _check_operate_flag_exists(self, dataframe, operate_flag=0):
        if operate_flag in dataframe["Quality"].unique():
            return True
        print(f"{operate_flag} not in in dataframe")

        return False

    def _add_cycle_info(
        self, cycle_name, cycle_parameter_name, dataframe, get_mean=True
    ):
        # log instead:
        # print(f'adding info for {cycle_parameter_name}')
        dataframe.loc[dataframe[cycle_parameter_name] > 0, cycle_parameter_name] = int(1)
        dataframe.loc[dataframe[cycle_parameter_name] == 0, cycle_parameter_name] = int(0)
        # get lists of indices for start and stop of each cycle
        # from the cycle_parameter_name column
        start = list(dataframe.index[dataframe[cycle_parameter_name].diff() == 1])
        stop = list(dataframe.index[dataframe[cycle_parameter_name].diff() == -1])
        try:
            start[0]
        except IndexError as e:
            print(">0")
            print(dataframe.loc[dataframe[cycle_parameter_name] > 0])
            print("<0")
            print(dataframe.loc[dataframe[cycle_parameter_name] < 0])
            print(dataframe[cycle_parameter_name])
            print(start)
            print(stop)
            raise e
        if start[0] > stop[0]:
            start.insert(0, dataframe.index[0])

        # add columns for storing cycle no and cycle runtime
        dataframe[cycle_name] = np.nan
        dataframe["{}_runtime".format(cycle_name)] = np.nan
        # add cycle information
        for cycle_no, (cycle_start, cycle_stop) in enumerate(zip(start, stop)):
            if dataframe.loc[cycle_start:cycle_stop, "timestamp"].empty:
                continue
            timedeltas = (
                dataframe.loc[cycle_start:cycle_stop, "timestamp"]
            - dataframe.loc[cycle_start, "timestamp"]).astype("timedelta64[s]")
            dataframe.loc[
                cycle_start:cycle_stop, "{}_runtime".format(cycle_name)
            ] = timedeltas
            dataframe.loc[cycle_start:cycle_stop, cycle_name] = int(cycle_no)

    def _add_zero_cycle_details(self):
        # log instead:
        # print("adding zero cycle details")
        # get lists of indices for start and stop of each cycle
        # from the cycle_parameter_name column
        self._add_cycle_info(
            cycle_name="zerocycle",
            cycle_parameter_name="State_Zero",
            dataframe=self.zerocycles_df,
        )

        self._add_cycle_info(
            cycle_name="flushcycle",
            cycle_parameter_name="State_Flush",
            dataframe=self.zerocycles_df,
        )

        self.zerocycles_df["two_beam_signal"] = Correction().raw_signal_conversion(
            self.zerocycles_df["Signal_Raw"],
            self.zerocycles_df["Signal_Ref"],
        )

    def _add_states(self, dataframe):

        # Add State_flush if not 0 when Quality is "16384: flush"
        dataframe.loc[
            (dataframe["State_Flush"] > 0)
            & (dataframe["State_Zero"] == 0)
            & (dataframe["Q_flag"] == "16384: flush"),
            "State_Flush",
        ] = 1
        # log instead:
        # print("added state flush")
        # introduce State_Measure when no flush or zero
        dataframe["State_Measure"] = 1
        dataframe.loc[
            (dataframe["State_Flush"] > 0) | (dataframe["State_Zero"] > 0),
            "State_Measure",
        ] = 0

        # introduce State_Wash 2 hours after each wash cycle
        # log instead:
        # print("added state measure")
        dataframe["State_Wash"] = 0
        dataframe.loc[
            dataframe["Q_flag"] == "64: wash",
            "State_Wash",
        ] = 1

        self._add_cycle_info("washcycle", "State_Wash", dataframe, get_mean=False)

        wash_time_addition = dt.timedelta(minutes=120)
        for washcycle_endtime in dataframe.groupby("washcycle")["timestamp"].max():
            dataframe.loc[
                (dataframe["timestamp"] <= (washcycle_endtime + wash_time_addition))
                & (dataframe["timestamp"] >= washcycle_endtime),
                "State_Wash",
            ] = 1
        # log instead:
        # print("added state wash")
        # Introduce extended flush
        dataframe["State_ExtendedFlush"] = 0
        flush_time_addition = dt.timedelta(minutes=60)
        values_from_flush = dataframe["Q_flag"] == "16384: flush"
        dataframe.loc[values_from_flush, "timestamp"]
        datetimes_from_extended_flush = (
            dataframe.loc[values_from_flush, "timestamp"] + flush_time_addition
        )
        for datetimeobject in datetimes_from_extended_flush:
            dataframe.loc[
                dataframe["timestamp"] == datetimeobject, "State_Flush_plus60min"
            ] = 1

        for flushcycle_endtime in dataframe.groupby("flushcycle")["timestamp"].max():
            dataframe.loc[
                (dataframe["timestamp"] <= (flushcycle_endtime + flush_time_addition))
                & (dataframe["timestamp"] >= flushcycle_endtime),
                "State_ExtendedFlush",
            ] = 1
        # log instead:
        # print("added state extended flush")
        dataframe["cruise_runtime"] = (
            dataframe["timestamp"] - dataframe["timestamp"].values[0]
        )

        # from the columns for each state compile into one state column
        for state in [
            "State_Measure",
            "State_Wash",
            "State_ExtendedFlush",
            "State_Flush",
            "State_Zero",
        ]:
            dataframe.loc[
                dataframe[state] == 1,
                "state",
            ] = state

    def zerocycles_linearregression(self):

        self._add_zero_cycle_details()

        row_selection = (
            (self.zerocycles_df.zerocycle_runtime >= 30)
            & (self.zerocycles_df.State_Zero == 1)
            & (~np.isnan(self.zerocycles_df.Signal_Raw))
            & (self.zerocycles_df.Quality == 0)
        )

        if self.zerocycles_df.loc[row_selection].empty:
            print(f"selection of data for zeroings is empty. These are the criteria and available number of data:\nzerocycle runtime >= 30 (sec): {len(self.zerocycles_df.loc[(self.zerocycles_df.zerocycle_runtime >= 30)])}\nState_Zero == 1): {len(self.zerocycles_df.loc[(self.zerocycles_df.State_Zero == 1)])}\nRaw signal is not nan: {len(self.zerocycles_df.loc[(~np.isnan(self.zerocycles_df.Signal_Raw))])}\n\nQuality == 0: {len(self.zerocycles_df.loc[(self.zerocycles_df.Quality == 0)])}")
            self.valid = False
            return

        x = []
        y = []
        cycle_no = []
        cycle_means = []
        cycle_all_used = []
        # log instead:
        # print(f"looping through zerocycles")
        for cycle, cycle_data in self.zerocycles_df.loc[row_selection].groupby(
            "zerocycle"
        ):
            if np.isnan(cycle):
                continue
            if cycle_data.empty:
                continue

            timestamps = cycle_data["timestamp"]
            if cycle_data.dropna(subset=["timestamp", "two_beam_signal"]).empty:
                continue

            used_zeros_df = cycle_data.dropna(subset=["timestamp", "two_beam_signal"])
            cycle_mean_df = used_zeros_df.mean().to_frame().transpose()

            cycle_means.append(cycle_mean_df)
            cycle_all_used.append(used_zeros_df)
            y.append(np.mean(cycle_data["two_beam_signal"]))
            # x is in the format timestamp
            x.append(np.mean(timestamps))
            cycle_no.append(cycle)

        # log instead:
        # print(
        #    f"looped all cycles, found {cycle} cycles of which {len(cycle_no)} contained data"
        #)
        if len(cycle_all_used) == 0:
            self.valid = False
            return
        try:
            self.zerocycles_usedvalues_df = pd.concat(cycle_all_used)
        except ValueError as err:
            self.valid = False
            raise Exception(
                "{}. No valid zeroing data within {}-{}. Conditions for valid zero data are: \n-cycle time >30 se\n-State_Zero True\n-Q_flag: '0: Operate'\nSignal Raw not missing".format(
                    err, self.start, self.stop
                )
            ).with_traceback(err.__traceback__)

        self.zerocycles_mean_df = pd.concat(cycle_means)
        self.zerocycles_mean_df["timestamp"] = self.zerocycles_mean_df[
            "timenumeric"
        ].apply(pd.to_datetime)
        self.zerocycles_mean_df["timestring"] = self.zerocycles_mean_df[
            "timestamp"
        ].apply(
            pd.to_datetime
        )
        self.zerocycles_mean_df["Q_flag"] = "0: Operate"

        zerocycles_stats = stats.linregress(
            self.zerocycles_mean_df["timenumeric"],
            self.zerocycles_mean_df["two_beam_signal"],
        )
        self.zerocycles_slope = zerocycles_stats.slope
        self.zerocycles_intercept = zerocycles_stats.intercept

        self.zerocycles_mean_df["slope"] = self.zerocycles_slope
        self.zerocycles_mean_df["intercept"] = self.zerocycles_intercept

    def process_data(self, df=False, recalculate=False):
        # log instead:
        # print("check quality...")
        self.valid = self._check_data_quality(self.measurements_df)
        self.valid = self._check_data_quality(self.zerocycles_df)

        if not self.valid:
            print('bad quality')
            return

        self.measurements_df_processed = self.measurements_df.copy()

        self._add_cycle_info(
            "flushcycle", "State_Flush", self.measurements_df_processed
        )

        # apply conversion from raw signal to two beam signal on all data
        if (
            "two_beam_signal" not in self.measurements_df_processed.columns
        ) or recalculate:
            self.measurements_df_processed[
                "two_beam_signal"
            ] = Correction().raw_signal_conversion(
                self.measurements_df_processed["Signal_Raw"],
                self.measurements_df_processed["Signal_Ref"],
            )
        # log instead:
        # print("two_beam calculated for measurement data")
        # 2. Collect data from zero cycles
        # and calculate linear regression constants on two beam signal for zerocorrection
        if not hasattr(self, "zerocycles_mean_df"):
            self.zerocycles_linearregression()
            if not self.valid:
                # add log
                return

        # log instead:
        # print("zero cycle linear regression found")
        # log instead:
        # print("correcting signal for drift")

        self._add_corrected_signals(self.measurements_df_processed)
        self._add_corrected_signals(self.zerocycles_mean_df)
        common_parameters = ["pco2",
            "Q_flag",
            "timestamp",
        ]

        self.processed_data = pd.concat(
            [
                self.measurements_df_processed[common_parameters],
                self.zerocycles_mean_df[common_parameters],
            ],
            ignore_index=True,
        ).sort_values(by=["timestamp"])

        # add information wash cycle and extended flush cycle.
        # TODO: Move to process
        # log instead:
        # print("adding states")
        self._add_states(dataframe=self.measurements_df_processed)

        self.measurements_df_processed["k1"] = self.calibration["k1"]
        self.measurements_df_processed["k2"] = self.calibration["k2"]
        self.measurements_df_processed["k3"] = self.calibration["k3"]
        self.measurements_df_processed["calibration date"] = self.calibration["calibration date"]
        self.measurements_df_processed["zero_correction_slope"] = self.zerocycles_slope
        self.measurements_df_processed["zero_correction_intercept"] = self.zerocycles_intercept
        self.measurements_df_processed["cruise_id"] = f"{self.start}-{self.stop}"

        # log instead:
        # print("save...")
        self.save_df("measurements_df_processed", self.measurements_df_processed)
        self.save_df("zerocycles_mean_df_processed", self.zerocycles_mean_df)

    def _add_corrected_signals(self, dataframe):
        # 3. calculate pCO2 on signals corrected by the zeroings
        # zero signal at each timestamp from regression
        dataframe["two_beam_signal_zero"] = Correction().get_zero_correction(
            dataframe["timestamp"].apply(lambda x: x.value),
            self.zerocycles_slope,
            self.zerocycles_intercept,
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

    def save_df(self, df_name, dataframe):

        today = dt.datetime.today().strftime('%Y-%m-%d')

        if not os.path.exists(f"{self.data_save_path}/{today}"):
            os.mkdir(f"{self.data_save_path}/{today}")

        save_path = f"{self.data_save_path}/{today}/{self.start}_{self.stop}_{df_name}.txt"
        dataframe.to_csv(
            open(save_path, "w"),
            sep="\t",
            index=False,
        )

        print(f"{df_name} data saved to {self.data_save_path}/{today}")

    def load_df(self, df_name):

        path = "{}/{}-{}_{}.txt".format(
            self.data_save_path, self.start, self.stop, df_name
        )
        try:
            dataframe = pd.read_csv(open(path), sep="\t")
        except FileNotFoundError as e:
            print("no processed data from cruise {}-{}".format(self.start, self.stop))
            self.valid = False
            return pd.DataFrame()
        dataframe["datetime_objects"] = dataframe["timestamp"].apply(
            datahandler.get_datetime_object
        )
        return dataframe

    def save_df_data_from_attribute(self, path, df_name):
        # save to textfile
        getattr(self, df_name).to_csv(
            open("{}/{}-{}_{}.txt".format(path, self.start, self.stop, df_name), "w"),
            sep="\t",
            index=False,
        )

if __name__ == "__main__":

    path = "C:/LenaV/python3/w_pCO2/data/CO2FT_A/CO2FT_A_Signal_Raw/CO2FT_A_Signal_Raw_20201111.txt"
    path = "C:/LenaV/python3/w_pCO2/data/CO2FT_A//CO2FT_A_State_Zero\CO2FT_A_State_Zero_20210316.txt"
    data = RawData()
    data._readfile(path)
    print(data.data.head())

    path = "C:/LenaV/python3/w_pCO2/data/CO2FT_A/"
    cruise = Cruise(path, ["2021-03-16", "2021-03-22"])
    measurement_data, ZeroCycle = cruise.get_data_package()

    process = ProcessData(
        "C:/LenaV/python3/w_pCO2/processed_data/test/",
        measurement_data,
        ZeroCycle,
        ["2021-03-16", "2021-03-22"],
    )
    print("process ... ")
    process.process_data()
    exit()
    cruise._read_data()
    print(cruise.ZeroCycle.head())
    cruise._merge_measurement_data()
    cruise.measurement_data.to_csv(
        "C:/LenaV/python3/w_pCO2/processed_data/test/measurementsmerged_df.txt",
        sep="\t",
    )
    cruise.ZeroCycle.to_csv(
        "C:/LenaV/python3/w_pCO2/processed_data/test/zerodata_df.txt",
        sep="\t",
        index=False,
    )
