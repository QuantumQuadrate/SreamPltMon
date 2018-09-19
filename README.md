# Stream Plot Monitor
The purpose of this code is to run in unison with origin data stream. Makes a real-time plot of the incoming data.

# Installation
1. Clone the repo to the same directory as origin-master
2. Update the config.cfg file with data stream details. (see config section)
3. Run StreamPltMon.py

# Config

The idea is that the source code will remain unchanged, and the config file will change from lab to lab based on the streams that they use.

Updating config.cfg:
Use the posted config.cfg file as a skeleton/example
* The section title will need to be the exact same as the name of origin streams that are to be monitored.
* num_of_columns should be filled with a number corresponding to the number of different variables that are being monitored.
* title, xlabel, ylabel should be filled with the title, x-axis label, and y-axis label for the plot.
* points should be filled with the number of data points you want the plot to retain over time.
* current_key should be filled out with the exact stream_id for the desired stream
* description can be anything, it's only purpose is to fill out the name of the text file that the code will be writing to and reading from.
* data_labels is meant to fill out the first row of the text file as though it was the column titles. Makes for easier reading of the text file.

Note: the variable associated with time is being converted in the source code to units of minutes.
