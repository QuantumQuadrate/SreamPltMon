#!/usr/bin/env python

import csv
import os
import sys
import os.path
import ConfigParser
import pprint
import logging
import time
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from origin.client.origin_subscriber import Subscriber
import multiprocessing
from multiprocessing import Queue, Process, Manager
import traceback

'''
TODO link storage_time and rep_rate to GUI
'''
storage_time = 10
rep_rate = 1
length = storage_time/rep_rate
'''
If adding an new stream, append "directory" with keyword
and list of variables.
'''
directory = {"0004":["measurement_time","Chamber","Near_Terminal","Coils"],
"0013":["measurement_time","X1","X2","Y1","Y2","Z1","Z2"]}
'''
The "descriptions" dictionary is used to fill out file names
to which this code will write data. Append if adding new stream.
'''
descriptions = {"0004":"1","0013":"2"}
keys = directory.keys()
for key in keys:
    with open("{}_{}.csv".format(key,descriptions[key]),"w+") as appendfile:
        fileappend = csv.writer(appendfile)
        fileappend.writerow(directory[key])
        for row in range(length):
            fileappend.writerow([1])

def hybrid_callback(stream_id, data, state, log, ctrl, plotter=None, master_dict=None):
    """
    custom callback function for use with the hybrid monitor.
    :param stream_id: ID of the stream being monitore
    :param data: data from server
    :param state: see subscriber documentation
    :param log: log object
    :param ctrl: ctrl signals, not currently in use
    :param foo: arbitrary kwarg to be expanded on if necessary
    :return: state, unchanged
    """
    if master_dict is None:
        print 'No master dictionary.'
    try:
        log.info("Stream Id {} : Data : [{}]".format(stream_id,data))
        #if animator == None:
        #    print "Error: No Animator"
    #else:
        #for streams in descriptons:
        if stream_id == '0004':
            current_key = keys[0]
            description = descriptions['0004']
            current_data = np.zeros(len(directory["0004"]), dtype = float)
            for i, column in enumerate(directory["0004"]):
                current_data[i] = data[column]
            master_dict['Hybrid_Temp']['queue'].put(current_data)

        elif stream_id == '0013':
            current_key = keys[1]
            description = descriptions['0013']
            current_data = np.zeros(len(directory["0013"]), dtype = float)
            for i, column in enumerate(directory["0013"]):
                current_data[i] = data[column]
            master_dict['Hybrid_Power']['queue'].put(current_data)

        else:
            print 'Error: wrong stream_id'
            return state

        with open("{}_{}.csv".format(current_key,description), "r") as infile:
            filereader = csv.reader(infile)
            lines = infile.readlines()

        with open("{}_{}.csv".format(current_key,description), "w") as outfile:
            filewriter = csv.writer(outfile)
            for pos, line in enumerate(lines):
                if pos != 1:
                    outfile.write(line)
        with open("{}_{}.csv".format(current_key,description),"a") as appendfile:
            fileappend = csv.writer(appendfile)
            fileappend.writerow(current_data)
            #print current_data


    except KeyError as Kerr:
        traceback.print_tb(sys.exc_info()[2])
        log.error("KeyError in Callback function")
    del current_key

    #from real_time_update.py import animationthingy

    return state

class animationthingy():

    def __init__(self, master_dict):

        points = 1000 # This is the maximum number of data points that you want to plot
        # If a new stream is to be plotted, add another global q (queue) variable
        '''In the case that you want to plot another data stream, update master_dict{} in the following way:
        1) Append name of new stream to "streams".
        2) Append new blank array to the "data_arrays" list with np.full().
        Be sure to make sure that the number of columns in this new blank
        array matches the number of variables that are coming through its
        respective queue.
        3) Append new queue to "queues".
        4) Append "num_of_columns" with an integer that represents the
        number of variables that are coming through the respective queue.
        5) Append "titles" with the new graph title.
        6) If needed (some graphes share x axis), append "xlabels" with new x axis label.
        7) Append "ylabels" with new y axis label.
        '''
        self.master_dict = master_dict
        self.fig, self.axarr = plt.subplots(len(master_dict.keys()), sharex=True)
        self.ani = animation.FuncAnimation(self.fig,self.animate,interval=2000)
        plt.show()

    def shift(self, l, n):
        l = np.append(l[n:],[l[n-1]],axis=0)
        return l

    def update_list(self, targetlist, new_data):
        targetlist = self.shift(targetlist, 1)
        targetlist[-1] = new_data
        return targetlist

    def animate(self,i):
        for key in self.master_dict.keys():
            self.master_dict[key]['data_array'] = self.update_list(self.master_dict[key]['data_array'], self.master_dict[key]['queue'].get())
        for key in self.master_dict.keys():
            self.axarr[key].clear()

        self.colors = ['red','orange','green','cyan','blue','purple','magenta']

        for index1 in range(len(self.master_dict.keys())):
            for index2 in range(self.master_dict[index1]['num_of_columns']):
                if index2 != 0:
                    self.axarr[index1].scatter((self.master_dict[index1]['data_array'][:,0]/(2**32)-time.time())/60,
                    self.master_dict[index1]['data_array'][:,index2],
                    marker='o',
                    color=self.colors[index2],
                    label=self.master_dict[index1]['data_labels'][index2-1])
                    self.axarr[index1].axhline(np.nanmean(self.master_dict[index1]['data_array'][:,index2]),
                    color=self.colors[index2])

        self.axarr[i].set_xlabel(self.master_dict['xlabels'][0])

        for i in range(len(self.master_dict.keys())):
            self.axarr[i].legend(loc='upper left', prop={'size':7})
            self.axarr[i].set_ylabel(self.master_dict['ylabels'][i])
            self.axarr[i].set_title(self.master_dict['titles'][i])

if __name__ == '__main__':

    multiprocessing.freeze_support()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # first find ourselves
    fullBasePath = os.path.abspath(os.getcwd() + "/Origin-master")
    #fullBasePath = os.path.dirname(os.path.dirname(fullBinPath))
    fullCfgPath = os.path.join(fullBasePath, "config")
    q1 = Queue()
    q2 = Queue()
    qlist =[q1,q2]

    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            configfile = os.path.join(fullCfgPath, "origin-server-test.cfg")
        else:
            configfile = os.path.join(fullCfgPath, sys.argv[1])
    else:
        configfile = os.path.join(fullCfgPath, "origin-server.cfg")

    config = ConfigParser.ConfigParser()
    config.read(configfile)
    sub = Subscriber(config, logger)
    logger.info("streams")
    print('')
    pprint.pprint(sub.known_streams.keys())

    plot_configfile = os.path.join(os.getcwd(), "Hybrid_config.cfg")
    plot_config = ConfigParser.ConfigParser()
    plot_config.read(plot_configfile)
    plot_dict = {}
    sections = plot_config.sections()
    for section in sections:
        plot_dict[section] = {}
        options = plot_config.options(section)
        for option in options:
            plot_dict[section][option] = plot_config.get(section, option)

        m = multiprocessing.Manager()
        plot_dict[section]['queue'] = m.Queue()

    # TODO : Make stream names compatible with GUI input
    streams = ['Hybrid_Temp', 'Hybrid_Beam_Balances']
#    stream = raw_input("stream to subscribe to: ")
    processes = []
    data_plot = Process(target=animationthingy, args = (plot_dict,))
    data_plot.start()
    for stream in streams:
        # Make sure stream is on the server
        if stream not in sub.known_streams:
            print("stream not recognized")
            sub.close()
            sys.exit(1)

        print("subscribing to stream: %s" % (stream,))
        # subscribe to the stream
        sub.subscribe(stream, callback=hybrid_callback, master_dict=plot_dict)


    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        sub.close()
        logger.info('closing')
        for proc in processes:
            proc.join()
