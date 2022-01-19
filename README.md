# Module to correct output from HydroC CO2 instrument


## TODO

* There are data in StateMeasurement with Q-flag 0 that is clearly wrong. How to identify automatically?
* QC-ferrybox hur hanterar vi efter-efterprocessering av data och uppdatering till WISKI?
* First QC - checking zeroing data from expedition and keep track of drift over time. 
    * Save dates for start and stop of one "expedition" to be able to re-run efficiently. For example if there are stops during an expedition it might need to be processed in with two separete linear regressions. 

## Processing


- **read_data.py**

    **Reformats pCO2 data from R/V Svea 's ferrybox as delivered in one folder per parameter.**
    >Needs to be adapted if data format from Svea is altered.
    *Corrects* 

    - State values that are float >0 to 1 (due to mean values for instrument processing).

    *Adds:*

    - zerocycle_runtime (float, seconds) and zerocycle (integer, cycle number)
    - flushcycle_runtime (float, seconds) and flushcycle (integer, cycle number)
    - State_Measure (when StateZero and StateFlush are == 0, could also be set to not >0)
    - State_Wash between 05:00-07:00 and 17:00-19:00 every day
    - cruise_runtime (float, seconds)

    *Calculates:*

    - two beam signal to validata zero signal and check drift
    - linear regression of mean two beam signal for zerocycles
    - drift corrected signal using linear regression
    - pCO2 from the drift corrected signal

    *Saves*
    
    - Data from all steps to txt file named with start and stop data. Choice of which data to be included


    *Requires:*
    - *filehandler.py*

        Lists files to include in processing for a given cruise (startdate-stopdate)
    - *datahandler.py*

        orders data by timestamp
    - *correction.py*

        transfrom raw signal to two_beam signal


# Required data

## Raw data

| Parameter | Description | format |
| :- | :- | :- |
| Timestamp | | |
| Date | date and time recorded by the sensor |
| p_NDIR | Pressure in the gas stream behind NDIR unit | float
| p_in | Pressure in the gas stream behind membrane | float
| Zero | 1: sensor measures zero gas; 0: sensor does'nt measure zero gas | bool |
| Flush | 1: sensor is flushing after the zero, 0: no flushing | bool |
| external_pump | Status of the external pump: 1: on, 0: off | bool |
| Signal_raw ($S_{raw}$) | Raw detector signal (digits) | float
| Signal ref ($S_{ref}$) | Raw reference signal | float
| T_sensor | Temperature of the NDIR unit | float
| T_control | Probe temperature for the temperature control (for keeping the whole sensor at a stable temperature) | float
| T_gas | Temperature of the gas stream behind the NDIR unit | float
| %rH_gas | Relative humidity of the gas stream behind the NDIR unit | float
| water temp membrane | Water temperature next to the sensor's membrane, measured with an oxygen optode | float
| - | - | - |

## Sensor specific coefficients

| Variable | Value | Notes |
| :- | :- | :- |
| F |60625 | NDIR unit specific scale facotor |
| $T_{sensor}$ | 35.8 | Temperature of the initial CO₂ sensor at pre-calibration |
| $f(T_{sensor})$ | 10019.24 | NDIR unit specific temperature compensation factor |


## Calculated data

| Parameter | Description | format |
| :- | :- | :- |
| Timestamp | |
| Date | date and time recorded by the sensor |
| Runtime | Seconds of operation since last calibration, this is calculated from the Date in raw data |
| Signal_proc | Signal corrected for T-influences and drift (this is based on the data from the pre-calibration and estimated drift) | float
| Conc_estimate | Fraction of CO₂ (estimate) in headspace, valid until 1000 ppm | float
| pCO2_corr | Partial pressure of CO₂, p_in and T_sensor corrected | float
| xCO2_corr | Fraction of CO₂ in headspace at 100% rH, p and T corrected | float

## Other data of interest

| Parameter | Description | format |
| :- | :- | :- |
| SST | Sea surface temperature measured by the ship's thermosalinograph | float
| SSS | Sea surface salinity measured by the ship's thermosalinograph | float
