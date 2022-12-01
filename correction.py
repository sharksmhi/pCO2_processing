# correction of pCO2 data from CONTROS HydroC CO2 instrument
# correct for baseline drift and the sensors sensitivity

import numpy as np
import pandas as pd
import datetime as dt
import scipy.stats as stats


class Correction:

    constants = {
        "normal_temperature": 273.15,
        "normal_pressure": 1013.25,
    }

    # expected data structure
    # each parameter as pandas dataframe with at least timestamp and value:
    # example with added columns for indication of zero_state (bool, on/off)
    #             timestamp  value  zero_state
    # 0 2009-10-12 10:10:00      4           1
    # 1 2009-10-12 10:10:11      5           1
    # 2 2009-10-12 10:10:31      3           1
    #
    #

    def __init__(self):
        pass

    def raw_signal_conversion(self, raw_signal, reference_signal):

        """
        Normalize the raw signal to the reference signal and correct for NDIR sensor temperature
        The result is a temperature corrected two-beam signal (two_beam_signal)
        The NDIR sensor temperature should be constant and is given by the calibration data
        two_beam_signal = (raw_signal/reference_signal)*NDIR_specific_temp_fT_sensor
        Temperature not needed for drift corrected since it is cancelled out at the division of 2b/2bz.

        The normalization should be done both on the signal for the real measurements and for
        the zeroing signals
        """

        # returns single float value when two floats are supplied
        if all([type(raw_signal) == float, type(reference_signal) == float]):
            return (
                raw_signal / reference_signal
            )  # * T_sensor # temperature cancels out in next step

        # returns list of values when two lists are supplied
        two_beam_signal = []
        for raw_signal, reference_signal in zip(raw_signal, reference_signal):
            if any((raw_signal <= 0, reference_signal <= 0)):
                twobeamsignal = np.nan
            else:
                twobeamsignal = (
                    raw_signal / reference_signal
                )  # * T_sensor # temperature cancels out in next step
            two_beam_signal.append(twobeamsignal)

        return two_beam_signal

    def get_zero_correction(self, timenumeric, slope, intercept):
        # calculate zero signal at given timestamp
        return slope * timenumeric + intercept

    def get_drift_corrected_signal(self, two_beam_signal, zero_correction):
        # change name to zero_two_beam_signal
        return two_beam_signal / zero_correction

    def get_processed_signal(self, drift_corrected_signal, calibration_data):

        return calibration_data["NDIR_specific_scalefactor_F"] * (
            1 - drift_corrected_signal
        )

    def get_xco2wet(self, processed_signal, Tgas, p_NDIR, calibration_data):
        k1 = calibration_data["k1"]
        k2 = calibration_data["k2"]
        k3 = calibration_data["k3"]

        xco2wet = (
            k3 * processed_signal * processed_signal * processed_signal
            + k2 * processed_signal * processed_signal
            + k1 * processed_signal
        ) * (
            (self.constants["normal_pressure"] * (Tgas + 274.15))
            / (self.constants["normal_temperature"] * p_NDIR)
        )

        return xco2wet

    def get_pco2(self, xco2wet, p_in):

        return xco2wet * (p_in / self.constants["normal_pressure"])

    def calibration_regression(self, timestamp):
        """
        This should be corrected to regress over instrument runtime and not timestamp
        according to intstruction from 4H Jena and Fietzek et al 2014:
        not clear here if this should be done using the zero two beam signal or processed signal
        k1 = slope_k1 * processed_signal + intercept_k1
        k2 = slope_k2 * processed_signal + intercept_k2
        k3 = slope_k3 * processed_signal + intercept_k3
        """
        raise NameError("Calibration regression function not implemented")
        # calibration
        y1 = [self.calibration_data["k1_pre"], self.calibration_data["k1_post"]]
        y2 = [self.calibration_data["k2_pre"], self.calibration_data["k2_post"]]
        y3 = [self.calibration_data["k3_pre"], self.calibration_data["k3_post"]]

        x = [
            self.calibration_data["timestamp_pre"],
            self.calibration_data["timestamp_post"],
        ]

        # calculate regression coeffictient for k1, k2, k3 (factors from of calibration polynomial)
        slope_k1, intercept_k1, rk1, p_k1, std_err_k1 = stats.linregress(x, y1)
        slope_k2, intercept_k2, rk2, p_k2, std_err_k2 = stats.linregress(x, y2)
        slope_k3, intercept_k3, rk3, p_k3, std_err_k3 = stats.linregress(x, y3)

        k1 = slope_k1 * timestamp + intercept_k1
        k2 = slope_k2 * timestamp + intercept_k2
        k3 = slope_k3 * timestamp + intercept_k3

        return k1, k2, k3
