import matplotlib.pyplot as plt
import numpy as np
import itertools
import math
import time

#To fix - still energy left at 0% - 2.85V at end due to IR voltage drop
#This requires a more precise cell cycling profile generated with a SMU
#0% SoC is defined as when the cell drops below 2.5V under a 3A load.

import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__)))
fName = "test_data//CellDataFileTestMJ1.txt"

class SoC_OCV:

	def __init__(self):
		"""
		Inititialize Soc_OCV object. Take file 'Test/CellDataFileTestMJ1.txt' which holds all voltage, current, soc, and other data from 
		a single solar cell test.

		Includes 0.050 cell and 0.035 cable, from tests done on single cell.
		This is the Resistance present when the chg-discharge curve was done, not the pack resistance
		Should be eplicitly tested on the setup. This is a rough estimate of what I expect it was, as we never measured it.
		"""
		IR = 0.085 
		four_parallel_IR = ((IR - 0.035) / 4) + 0.035

		#read data from txt files generated during discharge test
		with open(fName) as f_in:
			#fill matrices with data from file (all are lists)
			voltage, current, soc = np.loadtxt(itertools.islice(f_in, 1, None, 2), delimiter = '\t', usecols = (1,3,9), unpack = True)

		#Estimate the ocv of the cell, only taking the internal resistance into account (assuming no voltage relaxation or recovery)
		v_ocv = voltage + IR * current

		self.points = list(zip(soc, v_ocv))
		self.points.sort(key=lambda tup: tup[1]) 
		self.soc = np.array([x for (x, y) in self.points])
		self.v_ocv =  np.array([y for (x, y) in self.points])
		
    
	def get_soc_and_v_ocv(self) -> list:
		""" 
		Get SOC and OCV lists. Need to use two variables for both returns

		Args: 
			None
			
		Return: 
			soc: State of Charge data points in numpy array format
			v_ocv: Open Circuit Voltage data points in numpy array format
		"""
		return self.soc, self.v_ocv
	
  
	def get_cell_ocv(self, soc: float or int) -> float:
		""" 
		Get Open Circuit Voltage (OCV) corresponding to State of Charge (SOC) passed through.
		Uses Binary search first to check if SOC value is already present in storage,
		if yes, return OCV corresponding SOC value,
		if no, trace back 1 index and use linear interpolation with linear search to find	
		SOC value between existing SOC values.

		Args:
			soc: Currect State of Charge of the battery pack. Min = 0.0, Max = 100.00

		Return:
			self.v_ocv[mid_soc]: Open Circuit Voltage corresponding to the State of Charge of the battery pack. 
							Based on the SOC-OCV graph created through multiple test data 
		"""

		if (soc > self.soc[-1] or soc < self.soc[0]):
			raise Exception("The soc value is out of predicted range")
		max_soc = len(self.soc) - 1
		min_soc = 0
		while min_soc <= max_soc:
			mid_soc = math.floor((max_soc + min_soc) / 2)
			if self.soc[mid_soc] < soc:
				min_soc = mid_soc + 1
			elif self.soc[mid_soc] > soc:
				max_soc = mid_soc - 1
			else:
				return self.v_ocv[mid_soc]
		min_soc = max_soc - 1

		if min_soc >= 0:
			return self.__find_not_in_search__(soc, min_soc, True)
		else:
			min_soc = 0
			return self.__find_not_in_search__(soc, min_soc, True)
	
  
	def __find_not_in_search__(self, value_used_to_find: int, min: int, is_soc: bool) -> float or int:
		"""
		Hidden function used in the get_cell_ocv or correct_soc functions. Function is called when the soc or ocv values are not
		present in the soc or ocv list. Therefore, the function uses linear interpolation to map a given soc value to a ocv value, or
		a given ocv value to a soc value.

		Args:
			value_used_to_find: The value (soc or ocv) which will be mapped to its repective soc or ocv value.
			min: the minimum value to start the looping (do no need to loop all the way). Time efficient
			is_soc: boolean value (True or False) stating if the value passed to value_used_to_find is a soc value.
		Return:
			ocv: If the value_used_to_find is a soc value, then map it to a ocv value and return ocv value. 
			soc: If the value_used_to_find is a ocv value, then map it to a soc value and return soc value. 
		"""

		ocv0 = 0
		ocv1 = 0
		soc0 = 0
		soc1 = 0

		# Guess: Length of soc array is equal to the ocv array
		for index in range(min, len(self.soc)):
				if (self.soc[index] < value_used_to_find):
					soc0 = self.soc[index]
					ocv0 = self.v_ocv[index]
				elif ((self.soc[index] > value_used_to_find)):
					soc1 = self.soc[index]	
					ocv1 = self.v_ocv[index]
					break

		if is_soc:
			ocv = round(((value_used_to_find - soc0)*(ocv1 - ocv0) / (soc1 - soc0)) + ocv0, 6)
			return ocv
		else:
			soc = round(soc1 - ((ocv1 - value_used_to_find)*(soc1 - soc0) / (ocv1 - ocv0)), 6)
			return soc		
	
  
	def plot_graph(self):
		"""
		Plot matplotlib graph using SOC and OCV data lists created when object was initialized. Once function is called,
		a matplotlib graph will show up as a pop-up on the screen. Save it where ever you wish.

		Args:
			None
		Return:
			None
		"""
		plt.plot(self.soc, self.v_ocv, c = 'r')
		plt.title("SOC vs. OCV values based on test data")
		plt.xlabel("State of Charge (SOC)")
		plt.ylabel("Open Circuit Voltage (OCV)")
		plt.grid(True)
		plt.show()

    
	def correct_soc(self, ocv: float or int, current: int or float) -> int or float:
		""" 
		Correct state of charge (soc) corresponding to open circuit voltage (ocv) passed through.
		Uses Binary search first to check if ocv value is already present in ocv list,
		if yes, return soc corresponding ocv value,
		if no, trace back 1 index and use linear interpolation with linear search to find	
		ocv value between existing ocv values.

		Args:
			ocv: open circuit voltage of the battery pack. Min = 0.0, Max = 100.00
			current: amount of current in the pack. 

		Return:
			self.soc[mid_ocv]: soc corresponding to the ocv of the battery pack. Based on the SOC-OCV graph created through multiple test data
			self.__find_not_in_search__(ocv, min_ocv, False): uses hidden function to return expected soc value based on graph
		"""
		if current < 3:
			# 
			if ocv > self.v_ocv[-1] or ocv < self.v_ocv[0]:
				#raise Exception(f"The open circuit voltage value is out of predicted range. open circuit voltage is: {ocv}")
				return f"The open circuit voltage value is out of predicted range. open circuit voltage is: {ocv}"
			
			max_ocv = len(self.v_ocv) - 1
			min_ocv = 0

			while min_ocv <= max_ocv:
				mid_ocv = math.floor((max_ocv + min_ocv) / 2)
				if self.v_ocv[mid_ocv] < ocv:
					min_ocv = mid_ocv + 1
				elif self.v_ocv[mid_ocv] > ocv:
					max_ocv = mid_ocv - 1
				else:
					return self.soc[mid_ocv]
		
			min_ocv = max_ocv - 1

			if min_ocv < 0:
				min_ocv = 0

			return self.__find_not_in_search__(ocv, min_ocv, False)

		else:
			raise Exception(f'Current is too high. current is: {current}')

      
class test_SoC_OCV:
	def __init__(self):
		self.SoCOCV = SoC_OCV()
		self.voltage_array = np.array([])
		self.current_array = np.array([])
		self.v_ocv = np.array([])
	
	def test(self):
		ocv1 = self.SoCOCV.get_cell_ocv(100)
		ocv2 = self.SoCOCV.get_cell_ocv(75)
		ocv3 = self.SoCOCV.get_cell_ocv(25)
		ocv4 = self.SoCOCV.get_cell_ocv(0)
		print("Get OCV test:")
		print(f"soc = 100, ocv = {ocv1}")
		print(f"soc = 75, ocv = {ocv2}")
		print(f"soc = 25, ocv = {ocv3}")
		print(f"soc = 0, ocv = {ocv4}")
		print('')
		print("Correct SOC test:")
		print(f"ocv = {ocv1}, soc = {self.SoCOCV.correct_soc(ocv1, 1)}")
		print(f"ocv = {ocv2}, soc = {self.SoCOCV.correct_soc(ocv2, 1)}")
		print(f"ocv = {ocv3}, soc = {self.SoCOCV.correct_soc(ocv3, 1)}")
		print(f"ocv = {ocv4}, soc = {self.SoCOCV.correct_soc(ocv4, 1)}")

	def test_plot_graph(self):
		self.SoCOCV.plot_graph()
	
	def test_multiple_correct_soc(self, test_file: str):
		with open(test_file) as f_in:
			if np.size(self.voltage_array) == 0 and np.size(self.current_array) == 0:
				self.voltage_array, self.current_array = np.loadtxt(itertools.islice(f_in, 3, None), delimiter='\t', usecols=(1,3), unpack=True)
			else:
				temp_voltage, temp_current = np.loadtxt(itertools.islice(f_in, 3, None), delimiter='\t', usecols=(1,3), unpack=True)
				self.voltage_array = np.concatenate((self.voltage_array, temp_voltage))
				self.current_array = np.concatenate((self.current_array, temp_current))
		
		self.v_ocv = self.voltage_array + (0.085 * self.current_array)
		print(f"Size of test: {len(self.v_ocv)}")

		for i in range(len(self.v_ocv)):
			soc = self.SoCOCV.correct_soc(self.v_ocv[i], self.current_array[i])

if __name__ == '__main__':
	testing = test_SoC_OCV()
	# testing.test()

	test_file1 = "test_data//LGMJ1_1_1P_Discharge.txt"
	test_file2 = "test_data//LGMJ1_2_1P_Discharge.txt"
	test_file3 = "test_data//LGMJ1_3_1P_Discharge.txt"
	test_file4 = "test_data//LGMJ1_4_1P_Discharge.txt"
	test_file5 = "test_data//LGMJ1_5_1P_Discharge.txt"

	start_time = time.time()
	testing.test_multiple_correct_soc(test_file1)
	first_test_time = time.time()
	print(f"time taken for first test: {first_test_time - start_time}\n")
	testing.test_multiple_correct_soc(test_file2)
	second_test_time = time.time()
	print(f"time taken for second test: {second_test_time - first_test_time}\n")
	testing.test_multiple_correct_soc(test_file3)
	third_test_time = time.time()
	print(f"time taken for third test: {third_test_time - second_test_time}\n")
	testing.test_multiple_correct_soc(test_file4)
	fourth_test_time = time.time()
	print(f"time taken for fourth test: {fourth_test_time - third_test_time}\n")
	testing.test_multiple_correct_soc(test_file5)
	fifth_test_time = time.time()
	print(f"time taken for final test: {fifth_test_time - fourth_test_time}\n")

	testing.test_multiple_correct_soc(test_file1)
	testing.test_multiple_correct_soc(test_file2)
	testing.test_multiple_correct_soc(test_file3)
	testing.test_multiple_correct_soc(test_file4)
	testing.test_multiple_correct_soc(test_file5)
	sixth_test_time = time.time()
	print(f"time taken for final test: {sixth_test_time - fifth_test_time}\n")

	testing.test_multiple_correct_soc(test_file1)
	testing.test_multiple_correct_soc(test_file2)
	testing.test_multiple_correct_soc(test_file3)
	testing.test_multiple_correct_soc(test_file4)
	testing.test_multiple_correct_soc(test_file5)
	testing.test_multiple_correct_soc(test_file1)
	testing.test_multiple_correct_soc(test_file2)
	testing.test_multiple_correct_soc(test_file3)
	testing.test_multiple_correct_soc(test_file4)
	testing.test_multiple_correct_soc(test_file5)
	testing.test_multiple_correct_soc(test_file1)
	testing.test_multiple_correct_soc(test_file2)
	testing.test_multiple_correct_soc(test_file3)
	testing.test_multiple_correct_soc(test_file4)
	testing.test_multiple_correct_soc(test_file5)
	testing.test_multiple_correct_soc(test_file1)
	testing.test_multiple_correct_soc(test_file2)
	testing.test_multiple_correct_soc(test_file3)
	testing.test_multiple_correct_soc(test_file4)
	testing.test_multiple_correct_soc(test_file5)
	seventh_test_time = time.time()
	print(f"time taken for final test: {seventh_test_time - sixth_test_time}\n")
	