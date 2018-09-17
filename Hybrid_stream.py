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
import ast
import math
from numpy import genfromtxt

'''
TODO link storage_time and rep_rate to GUI
'''
'''
If adding an new stream, append "directory" with keyword
and list of variables.
'''
'''
The "descriptions" dictionary is used to fill out file names
to which this code will write data. Append if adding new stream.
'''

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

        for key in master_dict.keys():
            if stream_id == master_dict[key]['current_key']:
                current_data = np.zeros(len(master_dict[key]['data_labels']), dtype = float)
                for i, column in enumerate(master_dict[key]['data_labels']):
                    current_data[i] = data[column]

                with open("{}_{}.csv".format(master_dict[key]['current_key'], master_dict[key]['description']), "r") as infile:
                    filereader = csv.reader(infile)
                    lines = infile.readlines()

                with open("{}_{}.csv".format(master_dict[key]['current_key'], master_dict[key]['description']), "w") as outfile:
                    filewriter = csv.writer(outfile)
                    for pos, line in enumerate(lines):
                        if pos != 1:
                            outfile.write(line)
                with open("{}_{}.csv".format(master_dict[key]['current_key'], master_dict[key]['description']),"a") as appendfile:
                    fileappend = csv.writer(appendfile)
                    fileappend.writerow(current_data)

    except KeyError as Kerr:
        traceback.print_tb(sys.exc_info()[2])
        log.error("KeyError in Callback function")

    return state

class animationthingy():

    def __init__(self, dict):

        self.master_dict = dict
        self.fig, self.axarr = plt.subplots(len(self.master_dict.keys()), sharex=True)
        self.ani = animation.FuncAnimation(self.fig,self.animate,interval=100)
        plt.show()

    def shift(self, l, n):
        l = np.append(l[n:],[l[n-1]],axis=0)
        return l

    def update_list(self, targetlist, new_data):
        targetlist = self.shift(targetlist, 1)
        targetlist[-1] = new_data
        return targetlist

    def animate(self,i):
        self.colors = ['red','orange','green','cyan','blue','purple','magenta']

        for index1, key in enumerate(self.master_dict.keys()):
            self.axarr[index1].clear()
            df = genfromtxt("{}_{}.csv".format(self.master_dict[key]['current_key'], self.master_dict[key]['description']), delimiter=',')
            for index2 in range(self.master_dict[key]['num_of_columns']):
                if index2 != 0:
                    self.axarr[index1].scatter((df[:,0]/(2**32)-time.time())/60,
                    df[:,index2],
                    color=self.colors[index2],
                    label=self.master_dict[key]['data_labels'][index2])
                    self.axarr[index1].axhline(np.nanmean(df[:,index2]),
                    color=self.colors[index2])
            self.axarr[index1].legend(loc='upper left', prop={'size':7})
            self.axarr[index1].set_ylabel(self.master_dict[key]['ylabel'])
            self.axarr[index1].set_title(self.master_dict[key]['title'])

        self.axarr[1].set_xlabel(self.master_dict['StreamOne']['xlabel'])

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
    m = multiprocessing.Manager()
    for section in sections:
        plot_dict[section] = {}
        options = plot_config.options(section)
        for option in options:
            if option == 'data_labels':
                plot_dict[section][option] = ast.literal_eval(plot_config.get(section, option))
            elif option == 'num_of_columns':
                plot_dict[section][option] = int(plot_config.get(section, option))
            elif option == 'points':
                plot_dict[section][option] = ast.literal_eval(plot_config.get(section, option))
            else:
                plot_dict[section][option] = plot_config.get(section, option)

    for key in plot_dict.keys():
        with open("{}_{}.csv".format(plot_dict[key]['current_key'], plot_dict[key]['description']),"w+") as appendfile:
            fileappend = csv.writer(appendfile)
            fileappend.writerow(plot_dict[key]['data_labels'])
            for row in range(plot_dict[key]['points']):
                fileappend.writerow(np.full(len(plot_dict[key]['data_labels']), np.nan, dtype = float))
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
