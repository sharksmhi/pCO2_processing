import warnings
import logging
import os
import pandas as pd

warnings.filterwarnings("ignore")
import datahandler
import json
from read_data import Cruise
from read_data import ProcessData

# ### Load information about cruise start and stop
#
# Denna information sparas i regressionlinear_regression_log.
#
# Nedan visas vad som ligger i linear_regression_log. Om du vill ha med annan data i analysen eller ändra hur många perioder en cruise ska delas upp i gör du det genom att ändra i linear_regression_log. Det beskrivs i nästa avsnitt.

logger = logging.getLogger(__file__)

linear_regression_log = json.load(open("./linear_regression_log.json"))
datahandler.print_linear_regression_log(linear_regression_log)

# %%
data_path = "D:/data/ferrybox/"#"C:/LenaV/python3/w_pCO2/data"#"./example_data"
path_co2 = "/DeviceData/CO2FT_A"
path = (
    data_path
    + path_co2
)
processed_data = 0
for year, year_log in linear_regression_log.items():
        path = data_path + str(year) + path_co2
        for cruise_key, my_expedition in year_log.items():
            for cruise_period in my_expedition["regression_periods"]:
                print(cruise_period)
                logger.info(cruise_period)
            try:
                cruise = Cruise(path, cruise_period, data_save_path="C:/LenaV/python3/w_pCO2/processed_data")
                measurement_data, ZeroCycle = cruise.get_data_package()
                #data = ProcessData(path=path, regression_period=regression_period)
            except AssertionError as e:
                print(e)
                continue
            process = ProcessData(data_save_path="C:/LenaV/python3/w_pCO2/processed_data", measurements = measurement_data, zerocycles = ZeroCycle, regression_period = cruise_period)
            process.process_data()
            if process.valid:
                processed_data += 1
            else:
                print(f"invalid data for {year}, {cruise_key}, {cruise_period}")