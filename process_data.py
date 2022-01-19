from read_data import ProcessData
import os

# november cruise, high sea 13/11 flag data 2021-11-13T07:00 to 2021-11-13T15:59
path_co2 = "/CO2FT_A"
path = (
    "//winfs-proj/proj/havgem/EXPRAPP/Exprap2021/Svea_v49-50_december/data/Ferrybox/Working/DeviceData"
    + path_co2
)
cruise_start = "2021-12-06"
cruise_stop = "2021-12-18"


pco2Data = ProcessData(path=path, start=cruise_start, stop=cruise_stop)

pco2Data.save_raw_data(path="./processed_data")

pco2Data.process_data()

path = os.path.abspath("c:/LenaV/python3/w_pCO2/processed_data")
pco2Data.save_df_data(path=path, df_name="measurements_df_processed")
pco2Data.save_processed_data(path=path)
