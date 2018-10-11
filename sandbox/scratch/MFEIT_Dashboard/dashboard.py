
import sys
import json
if sys.version_info[0] < 3:
	import Tkinter
	from Tkinter import *
	import Tkinter as Tk
	import tkFont
	import tkFileDialog as filedialog
else:
	import tkinter as Tkinter
	from tkinter import *
	import tkinter as Tk
	from tkinter import filedialog
	# from tkinter import tkFont

import matplotlib as mpl
mpl.use("TkAgg")
# mpl.use('Qt4Agg')

# import tkFont
# import tkFileDialog as filedialog

import Serialhandler
import serial.tools.list_ports
import Reconstruction as eit
import re 
import numpy as np
import time
import pickle 

class Gui(object):

	def __init__(self):

		self.root = Tkinter.Tk()  
		self.root.wm_title("Multi Frequency Test Bench Dashboard")
		self.top 	   = None 
		self.topplot   = None
		self.topcanvas = None
		self.topcbar   = None
		self.topcbaxes = None

		self.baseline_bool 		= False 
		self.baseline_frequency = 500
		self.spectrum_amps     	= [] 
		self.spectrum_freqs    	= []
		self.current_frequency 	= 0 
		self.pixel_x 			= 0
		self.pixel_y 			= 0
		self.spect 	     		= None 
		self.spectplot   		= None
		self.spectcanvas 		= None
		self.spectcbar   		= None
		self.spectcbaxes 		= None
		self.spectrumplot 		= None

		menu = Tkinter.Menu(self.root)
		self.root.config(menu=menu)

		filemenu = Menu(menu)
		menu.add_cascade(label="File", menu=filemenu)
		filemenu.add_command(label="Exit", command=self.root.quit)
		viewmenu = Menu(menu)
		menu.add_cascade(label = "View",menu = viewmenu)
		viewmenu.add_command(label="Dedicated Reconstruction Window",command = self.Eitwin)
		viewmenu.add_separator()
		viewmenu.add_command(label="MF EIT Spectrogram Window",command = self.Spectrogram)
		helpmenu = Menu(menu)
		menu.add_cascade(label="Help", menu=helpmenu)
		helpmenu.add_command(label="About...", command=self.About)

		self.root.protocol("WM_DELETE_WINDOW", self.quit)
		# make Esc exit the program
		self.root.bind('<Escape>', lambda e: self.root.destroy())

		# Matplotlibbing. 
		fig 				= mpl.figure.Figure(figsize=(5, 4), dpi=100)
		# pos = [left, bottom, width, height]
		image_position 		= [0.1, 0.25, 0.7, 0.7]
		histogram_position 	= [0.1, 0.08, 0.8, 0.1]	
		colorbar_position 	= [0.85, 0.25, 0.03, 0.7]
		self.imageplt 		= fig.add_axes(image_position)
		self.histplt 		= fig.add_axes(histogram_position)
		self.cbaxes 	 	= fig.add_axes(colorbar_position)  
		
		# 180,225,270,315,0,45,90,135
		# 1,2,3,4,5,6,7,8
		# Add text for electrode locations. 
		self.imageplt.annotate('180d(AFE1)',
            xy=(0.4, 0.9), xycoords='axes fraction')
		self.imageplt.annotate('225d(AFE2)',
            xy=(0.15, 0.75), xycoords='axes fraction')
		self.imageplt.annotate('270d(AFE3)',
            xy=(0.0, 0.5), xycoords='axes fraction')
		self.imageplt.annotate('315d(AFE4)',
            xy=(0.2, 0.2), xycoords='axes fraction')
		self.imageplt.annotate('0d(AFE5)',
            xy=(0.5, 0.1), xycoords='axes fraction')
		self.imageplt.annotate('45d(AFE6)',
            xy=(0.75, 0.25), xycoords='axes fraction')
		self.imageplt.annotate('90d(AFE7)',
            xy=(0.9, 0.5), xycoords='axes fraction')
		self.imageplt.annotate('135d(AFE8)',
            xy=(0.8, 0.8), xycoords='axes fraction')

		ypadding = 10
		xpadding = 20
		# 
		# 
		self.file_marker = 0
		self.file_name = ''
		self.data_file_array = []
		# Will this often need to be changed? 
		scale_max					= 90000
		self.sliders = [0,scale_max,0,scale_max]

		min_cbar 					= 0
		max_cbar 					= scale_max
		scale_tick_interval 		= float(scale_max/10)
		# intialize the reconstruction library. 
		self.image_reconstruct 		= eit.Reconstruction()
		self.img 					= self.image_reconstruct.img 

		self.plot = self.imageplt.imshow(self.img,interpolation='nearest') 

		# self.imageplt.set_position(image_position) # set a new position
		# self.histplt.set_position(histogram_position)
		self.cbar = mpl.pyplot.colorbar(self.plot,cax = self.cbaxes)
		# self.cbar = mpl.pyplot.colorbar(self.imageplt,cax = self.cbaxes)
		self.cbar.set_clim([min_cbar,max_cbar])
		# 
		self.canvas 	= mpl.backends.backend_tkagg.FigureCanvasTkAgg(fig, master=self.root)
		
		self.canvas.show()
		self.canvas.get_tk_widget().pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
		toolbar = mpl.backends.backend_tkagg.NavigationToolbar2TkAgg(self.canvas, self.root)
		toolbar.update()
		self.canvas._tkcanvas.pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
		# canvas.mpl_connect('key_press_event', on_key_event)

		self.use_blit = False
		# cache the background, in the init. 
		if self.use_blit: # cache the background. 
			self.background 	= self.canvas.copy_from_bbox(self.imageplt.bbox)
			self.histbackground = self.canvas.copy_from_bbox(self.histplt.bbox)
			self.cbbackground 	= self.canvas.copy_from_bbox(self.cbaxes.bbox)
		self.total_rendering_time = 0.0
		self.total_processing_time = 0.0
		# ---------------
		# defining frames
		# ---------------
		bottomframe0 = Frame(self.root)
		bottomframe1 = Frame(self.root)
		bottomframe2 = Frame(self.root)
		bottomframe3 = Frame(self.root)

		bottomframe0.pack(side=TOP)
		bottomframe1.pack(side=TOP)
		bottomframe2.pack(side=TOP)
		bottomframe3.pack(side=TOP)
		
		# This is the text box... 
		self.msg=Tkinter.Text(
		    bottomframe0, height=1.0, bg="light cyan", state=Tkinter.NORMAL)   
		self.msg.grid(row=1, column=0, columnspan=3)
		self.msg.pack(fill="x", expand=True)

		# sliders. 
		self.w1 = Tkinter.Scale(bottomframe0, from_=self.sliders[0], to=self.sliders[1], length = 600,tickinterval=scale_tick_interval, orient=HORIZONTAL, label = 'MIN')
		self.w1.set(scale_max/10)
		self.w1.pack(fill="x", expand=True)
		self.w2 = Tkinter.Scale(bottomframe0, from_=self.sliders[2], to=self.sliders[3],length= 600,tickinterval=scale_tick_interval, orient=HORIZONTAL, label = 'MAX')
		self.w2.set(9*scale_max/10)
		self.w2.pack(fill="x", expand=True)

		# Text entry boxes for min and max range of each slider bar. 
		# 
		# 
		cbarbut = Tkinter.Button(bottomframe0, text='Update HIST', command=self.update_hist)
		cbarbut.pack(side=Tkinter.RIGHT, padx=3, pady=ypadding)

		cbarbut = Tkinter.Button(bottomframe0, text='Update CBAR', command=self.update_cbar)
		cbarbut.pack(side=Tkinter.RIGHT, padx=3, pady=ypadding)


		self.hist_update = False 

		self.min_slider_l = Tkinter.Entry(bottomframe0)
		self.min_slider_h = Tkinter.Entry(bottomframe0)
		self.max_slider_l = Tkinter.Entry(bottomframe0)
		self.max_slider_h = Tkinter.Entry(bottomframe0)
		self.max_slider_h.pack(side=Tkinter.RIGHT, padx=3, pady=ypadding)
		self.max_slider_h_label = Tkinter.Label(bottomframe0, text="max_h:").pack(side=Tkinter.RIGHT)
		self.max_slider_l.pack(side=Tkinter.RIGHT, padx=3, pady=ypadding)
		self.max_slider_l_label = Tkinter.Label(bottomframe0, text="max_l:").pack(side=Tkinter.RIGHT)		
		self.min_slider_h.pack(side=Tkinter.RIGHT, padx=3, pady=ypadding)
		self.min_slider_h_label = Tkinter.Label(bottomframe0, text="min_h:").pack(side=Tkinter.RIGHT)
		self.min_slider_l.pack(side=Tkinter.RIGHT, padx=3, pady=ypadding)
		self.min_slider_l_label = Tkinter.Label(bottomframe0, text="min_l:").pack(side=Tkinter.RIGHT)
		self.min_slider_l.bind("<Return>", self.evaluate)
		self.min_slider_h.bind("<Return>", self.evaluate)
		self.max_slider_l.bind("<Return>", self.evaluate)
		self.max_slider_h.bind("<Return>", self.evaluate)

		# The x, y point for the spectrogram
		# self.point_x = Tkinter.Entry(bottomframe1)
		# self.point_y = Tkinter.Entry(bottomframe1)
		# self.point_y.pack(side=Tkinter.RIGHT, padx=3, pady=ypadding)
		# self.point_y_label = Tkinter.Label(bottomframe1, text="point y:").pack(side=Tkinter.RIGHT)
		# self.point_x.pack(side=Tkinter.RIGHT, padx=3, pady=ypadding)
		# self.point_x_label = Tkinter.Label(bottomframe1, text="point x:").pack(side=Tkinter.RIGHT)

		# # should it actually be 'evaluate'? 
		# self.point_x.bind("<Return>", self.xypoints)
		# self.point_y.bind("<Return>", self.xypoints)

		full_ports = list(serial.tools.list_ports.comports())
		portnames = [item[0] for item in full_ports]
		if len(portnames) > 0 :


			self.menuselect = StringVar(self.root)
			self.menuselect.set(portnames[0])
			# apply has been deprecated. 
			# listboxdataconnect = apply(OptionMenu, (self.root, self.menuselect) + tuple(portnames ))
			
			listboxdataconnect = OptionMenu(*(self.root, self.menuselect) + tuple(portnames ))
			listboxdataconnect.pack(in_=bottomframe1, side=Tkinter.LEFT , padx=3, pady=ypadding)


			self.baseline_freq_entry = Tkinter.Entry(bottomframe1)
			self.baseline_freq_entry.pack(side=Tkinter.RIGHT, padx=3, pady=ypadding)
			# self.baseline_freq_entry.bind("<Return>", self.baseline)

			self.baselinebut = Tkinter.Button(master = bottomframe1, text="Baseline", command=self.baseline) 
			self.baselinebut.pack(side=Tkinter.RIGHT, padx=3, pady=ypadding)

			self.recorddata = Tkinter.Button(
			    master=bottomframe1, text='Record', command=self.record)
			self.recorddata.pack(side=Tkinter.RIGHT, padx=3, pady=ypadding)


			self.buttonconnect = Tkinter.Button(
			    master=bottomframe1, text='Connect', command=self.connect)
			self.buttonconnect.pack(side=Tkinter.RIGHT, padx=3, pady=ypadding)


		else:
		    # no serial port detected. 
		    print ('no serial port found, hope that\'s OK')
		    self.text = "no serial port found, hope that's OK"
		    if expertMode is False:
		        tkMessageBox.showwarning(
		            "No serial port",
		            "No device detected\nCheck cable and connection" 
		        )

		readfilerunbut = Tkinter.Button(bottomframe2, text='Run', command=self.run_file)
		readfilerunbut.pack(side=Tkinter.RIGHT, padx=3, pady=ypadding)

		readfilestartbut = Tkinter.Button(bottomframe2, text='Step', command=self.step_file)
		readfilestartbut.pack(side=Tkinter.RIGHT, padx=3, pady=ypadding)

		readfilebut = Tkinter.Button(bottomframe2, text='ReadFromFile', command=self.load_file)
		readfilebut.pack(side=Tkinter.RIGHT, padx=3, pady=ypadding)
		
		# start Serial handler off in a separate process. 
		self.s = Serialhandler.Serialhandler()
		self.s.start()
		self.s.join()
		self.text = 'hi'
		self.root.after(200,self.process_data)
		self.root.mainloop()    
 
	def connect(self): 
		port_selection = self.menuselect.get()
		self.s.connect(port_selection)
		# connect should return true or false depending on if it succesfully connected. 
		if self.s.connectGui == True: # Disconnect and reset. 
			connectbuttontext = 'Disconnect'
			self.get_data()
			self.root.after(500, self.update_textbox)
		else: # Connect and start streaming. 
			connectbuttontext = 'Connect'
			# GUI Update. 
		self.buttonconnect.config(text=connectbuttontext)

	def update_cbar(self): # update the color bar with the min/maxes set as the slider. 
		# Try to update this on the toplevel axes if they exist, as well. 

		# get slider values. 
		min_cbar = self.w1.get()
		max_cbar = self.w2.get()
		if min_cbar < max_cbar: 
			# redraw the cbar with new limits 
			self.cbar = mpl.pyplot.colorbar(self.plot,cax = self.cbaxes)
			self.cbar.set_clim([min_cbar,max_cbar])
			# if top window exists. 
			if self.top is not None:
				if self.top.winfo_exists():
					self.topcbar = mpl.pyplot.colorbar(self.topplot,cax = self.topcbaxes)
					self.topcbar.set_clim([min_cbar,max_cbar])

			if self.spect is not None:
				if self.spect.winfo_exists():
					self.spectcbar = mpl.pyplot.colorbar(self.spectplot,cax = self.spectcbaxes)
					self.spectcbar.set_clim([min_cbar,max_cbar])
			self.update_figure()
		else: 
			print ('min has to be less than max for this to work. ')
			self.text = 'min has to be less than max for this to work. '

	def record(self):

		if self.s.connectGui == True and not self.s.isRecording: # Connect  
			recordbuttontext = 'Record'
			self.s.record_toggle()
		else: # 
			recordbuttontext = 'Stop'
			self.s.record_toggle()
			# perform GUI Update Commands. 
		self.recorddata.config(text=recordbuttontext)

	def update_textbox(self): 
		self.msg.delete('1.0',END)
		self.msg.insert(END,self.text)
		self.root.after(500, self.update_textbox)

	def update_figure(self): 
		 
		start_time = time.time()
		# self.top is not None or 
		if self.top is not None:
			if self.top.winfo_exists(): # check if top window is open. 
				print ('top window update')
				self.topplot.set_array(self.img)
				self.topcanvas.draw()
				self.topcanvas.flush_events()
		elif self.spect is not None:
			if self.spect.winfo_exists(): # check if spect window is open. 
				# self.spectplot.set_array(self.img)
				# Create a Rectangle patch
				# rect = mpl.patches.Rectangle((self.pixel_x,self.pixel_y),1,1,linewidth=0.5,edgecolor='r',facecolor='none', fill=False)
				# Add the patch to the Axes
				self.spectrumplt.cla()
				# self.spectimageplt.add_patch(rect)
				self.spectrum_amps = self.image_reconstruct.get_frequency_data(self.pixel_x,self.pixel_y)
				# these are example values which in future I should get from the actual data... 
				self.spectrum_freqs = self.image_reconstruct.get_freq_values()
				# Now plot the spectrum and label the axis. 
				self.spectrumplot = self.spectrumplt.plot(self.spectrum_freqs,self.spectrum_amps,marker="o",linestyle='--',color='r')
				self.spectrumplt.grid(True)
				self.spectcanvas.draw()
				self.spectcanvas.flush_events()

		else: # Update the main window plot. 
			self.plot.set_array(self.img)
			self.canvas.draw()
			self.canvas.flush_events() 

		# We need time comparisons now. 	
		# print("render: %s seconds ---" % (time.time() - start_time))
		self.total_rendering_time += (time.time() - start_time)	
		
		# self.text += ' render time:' + str(self.total_rendering_time)
		# if self.file_marker >= (len(self.data_file_array)-2):
		# 	print 'total rendering time: ',self.total_rendering_time
		# 	self.text += ' total: '+ str(self.total_rendering_time)
		# simplest thing to do with textbox is to keep everything the same no. of characters. 
		# 
		# What do I want it to say? 
		# when playing bak a file. 
		# reading file... 1/84 total render: 3.443. total reconstruct: 5.442
		# Done. 
		# 
		# realtime buffer... 324873  total render: total reconstruct: 
		# 

	def get_data(self): 
		if self.s.connectGui == True:
			self.s.getserialdata()
			self.root.after(300, self.get_data)

	def process_data(self):
		bytebuffer = self.s.get_len_bytes()
		if bytebuffer > 0: 
			line = self.s.sendline()
			self.current_frequency = self.s.getfrequency()
			if self.baseline_bool == True: 
				print ('wait for it')
				if self.current_frequency == self.baseline_frequency:
					print ('baselining')
					self.image_reconstruct.set_baseline()
					self.baseline_bool = False
			self.parse_data(line)
			self.update_figure()

		self.text = 'time render: %.2f time math: %.2f byte buffer: %d' %(self.total_rendering_time, self.total_processing_time,bytebuffer)
		self.root.after(80, self.process_data)

	def parse_data(self,line):
		start_time = time.time()
		try: 
			data 	 	= map(float, line ) # leave out the final empty element. 
			data 		= [1.0 if x==0 else x for x in data] # remove zeros. nothing should be zero. 
			self.img = self.image_reconstruct.eit_reconstruction(data)
			# only store this if spect window is open? 
			# print (type(self.current_frequency),self.current_frequency)
			# This is also where we add to the frequency array. 
			self.image_reconstruct.store_frequency_data(self.current_frequency,self.img)

		except (RuntimeError, TypeError, NameError) as err:
		# except: # could consider descriptive error here. 
			print ('reconstruction error: ',err)
		self.total_processing_time += (time.time() - start_time)

	# Take a baseline to be subtracted later. 		
	def baseline(self):
		# b = self.baseline_freq_entry.get()
		# if self.baseline_freq_entry.get() is not None:
		self.baseline_frequency = self.baseline_freq_entry.get()
		print ('baseline frequency: ',self.baseline_frequency)
		self.baseline_bool = True


	def load_file(self):
		self.file_name  = filedialog.askopenfile()
		self.data_file_array = self.file_name.readlines()
		self.file_name.close()
		self.file_marker = 0
		self.update_textbox()
		
	# This steps one at a time. Needs to be modified now we moved the data parsing elsewhere. 
	def step_file(self):

		if self.file_marker < len(self.data_file_array):
			self.text = 'time render: %.2f time math: %.2f reading file... %i / %i' %(self.total_rendering_time, self.total_processing_time,self.file_marker,len(self.data_file_array))
			# Send the data in line by line. 
			data = self.data_file_array[self.file_marker]

			indices = [i for i, s in enumerate(data) if ':' in s]
			othercommaindices = [i for i, s in enumerate(data) if ';' in s]
			self.current_frequency = data[(indices[0]+1):othercommaindices[0]]
	
			# line = data[indices[0]+1:-1].replace(" ","").split(',')[0:-1]
			line = data[othercommaindices[0]+1:-1].replace(" ","").split(',')[0:-1]
			
			if len(line) == 28: 
				self.parse_data(line)
				self.update_figure()
			else:
				self.text = 'error in line of stored data %d' %(self.file_marker)
			self.file_marker += 1

	def run_file(self):
		for i in range(len(self.data_file_array)):
			if self.file_marker < len(self.data_file_array):
				self.text = 'time render: %.2f time math: %.2f reading file... %i / %i' %(self.total_rendering_time, self.total_processing_time,self.file_marker,len(self.data_file_array))
				# Send the data in line by line. 
				data = self.data_file_array[self.file_marker]
				indices = [i for i, s in enumerate(data) if ':' in s]

				othercommaindices = [i for i, s in enumerate(data) if ';' in s]
				self.current_frequency = data[(indices[0]+1):othercommaindices[0]]
	
				line = data[othercommaindices[0]+1:-1].replace(" ","").split(',')[0:-1]
				if len(line) == 28: 
					self.parse_data(line)
					self.update_figure()
				else:
					self.text = 'error in line of stored data %d' %(self.file_marker)
				self.file_marker += 1

	def About(self):
		print ('Open Source Biomedical Imaging Project')


	def Eitwin(self):

		self.top = Tkinter.Toplevel(master = self.root)
		self.top.title('EIT Reconstruction Window')
		fig 				= mpl.figure.Figure(figsize=(5, 4), dpi=100)
		# pos = [left, bottom, width, height]
		image_position 		= [0.1, 0.25, 0.7, 0.7]	
		colorbar_position 	= [0.85, 0.25, 0.03, 0.7]
		self.topimageplt 	= fig.add_axes(image_position)
		self.topcbaxes 	 	= fig.add_axes(colorbar_position)  
		
		# 180,225,270,315,0,45,90,135
		# 1,2,3,4,5,6,7,8
		# Add text for electrode locations. 
		self.topimageplt.annotate('180d(AFE1)',
            xy=(0.4, 0.9), xycoords='axes fraction')
		self.topimageplt.annotate('225d(AFE2)',
            xy=(0.15, 0.75), xycoords='axes fraction')
		self.topimageplt.annotate('270d(AFE3)',
            xy=(0.0, 0.5), xycoords='axes fraction')
		self.topimageplt.annotate('315d(AFE4)',
            xy=(0.2, 0.2), xycoords='axes fraction')
		self.topimageplt.annotate('0d(AFE5)',
            xy=(0.5, 0.1), xycoords='axes fraction')
		self.topimageplt.annotate('45d(AFE6)',
            xy=(0.75, 0.25), xycoords='axes fraction')
		self.topimageplt.annotate('90d(AFE7)',
            xy=(0.9, 0.5), xycoords='axes fraction')
		self.topimageplt.annotate('135d(AFE8)',
            xy=(0.8, 0.8), xycoords='axes fraction')

		self.topplot = self.topimageplt.imshow(self.img,interpolation='nearest') 

		self.topcbar = mpl.pyplot.colorbar(self.topplot,cax = self.topcbaxes)
		# self.cbar = mpl.pyplot.colorbar(self.imageplt,cax = self.cbaxes)
		scale_max					= 90000
		min_cbar 					= 0
		max_cbar 					= scale_max
		self.topcbar.set_clim([min_cbar,max_cbar])
		# 
		self.topcanvas 	= mpl.backends.backend_tkagg.FigureCanvasTkAgg(fig, master=self.top)
		self.topcanvas.show()
		self.topcanvas.get_tk_widget().pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
		toolbar = mpl.backends.backend_tkagg.NavigationToolbar2TkAgg(self.topcanvas, self.top)
		toolbar.update()
		self.topcanvas._tkcanvas.pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
	
	def Spectrogram(self):
		self.spect = Tkinter.Toplevel(master = self.root)
		self.spect.title('Multi-Frequency Spectrogram Exploration')
		fig 				= mpl.figure.Figure(figsize=(5, 4), dpi=100)
		# pos = [left, bottom, width, height]
		image_position 		= [0.1, 0.1, 0.3, 0.3]	
		colorbar_position 	= [0.45, 0.1, 0.03, 0.3]
		spectrum_position   = [0.1, 0.5, 0.8, 0.45]	

		# these are the equivalent of axes. 
		self.spectimageplt 	= fig.add_axes(image_position)
		self.spectcbaxes 	= fig.add_axes(colorbar_position)  
		self.spectrumplt 	= fig.add_axes(spectrum_position) 

		# 180,225,270,315,0,45,90,135
		# 1,2,3,4,5,6,7,8
		# Add text for electrode locations. 
		self.spectimageplt.annotate('180d(AFE1)',
            xy=(0.4, 0.9), xycoords='axes fraction')
		self.spectimageplt.annotate('225d(AFE2)',
            xy=(0.15, 0.75), xycoords='axes fraction')
		self.spectimageplt.annotate('270d(AFE3)',
            xy=(0.0, 0.5), xycoords='axes fraction')
		self.spectimageplt.annotate('315d(AFE4)',
            xy=(0.2, 0.2), xycoords='axes fraction')
		self.spectimageplt.annotate('0d(AFE5)',
            xy=(0.5, 0.1), xycoords='axes fraction')
		self.spectimageplt.annotate('45d(AFE6)',
            xy=(0.75, 0.25), xycoords='axes fraction')
		self.spectimageplt.annotate('90d(AFE7)',
            xy=(0.9, 0.5), xycoords='axes fraction')
		self.spectimageplt.annotate('135d(AFE8)',
            xy=(0.8, 0.8), xycoords='axes fraction')

		self.spectplot = self.spectimageplt.imshow(self.img,interpolation='nearest') 
		self.spectcbar = mpl.pyplot.colorbar(self.spectplot,cax = self.spectcbaxes)
		
		# Create a Rectangle patch
		rect = mpl.patches.Rectangle((self.pixel_x,self.pixel_y),1,1,linewidth=0.5,edgecolor='r',facecolor='none', fill=False)
		# Add the patch to the Axes
		self.spectimageplt.add_patch(rect)

		self.spectrum_amps = self.image_reconstruct.get_frequency_data(self.pixel_x,self.pixel_y)		
		self.spectrum_freqs = self.image_reconstruct.get_freq_values()

		# Now plot the spectrum and label the axis. 
		self.spectrumplot = self.spectrumplt.plot(self.spectrum_freqs,self.spectrum_amps,marker="o",linestyle='--',color='r')
		self.spectrumplt.set_xlabel('Excitation frequencies(Hz)')
		self.spectrumplt.set_ylabel('Amplitudes')
		self.spectrumplt.grid(True)
		# ax.grid(True,linestyle='-',color='0.75')
		self.spectrumplt.set_title('Spectrogram')
		# self.spectrumplt.show()
		# self.cbar = mpl.pyplot.colorbar(self.imageplt,cax = self.cbaxes)
		scale_max					= 90000
		min_cbar 					= 0
		max_cbar 					= scale_max
		self.spectcbar.set_clim([min_cbar,max_cbar])
		self.spectcanvas 	= mpl.backends.backend_tkagg.FigureCanvasTkAgg(fig, master=self.spect)
		self.spectcanvas.show()
		self.spectcanvas.mpl_connect('button_press_event',self.onclick)
		self.spectcanvas.get_tk_widget().pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
		toolbar = mpl.backends.backend_tkagg.NavigationToolbar2TkAgg(self.spectcanvas, self.spect)
		toolbar.update()
		self.spectcanvas._tkcanvas.pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
	
		# The x, y point for the spectrogram
		self.point_x = Tkinter.Entry(self.spect,width=10)
		self.point_y = Tkinter.Entry(self.spect,width = 10)
		self.point_x.place(relx=0.7,rely=0.65)
		self.point_y.place(relx=0.7,rely=0.75)
		self.point_x_label = Tkinter.Label(self.spect, text="point x:").place(relx=0.6,rely=0.65)
		self.point_y_label = Tkinter.Label(self.spect, text="point y:").place(relx=0.6,rely=0.75)
		self.point_x.bind("<Return>", self.xypoints)
		self.point_y.bind("<Return>", self.xypoints)
		writespectfilebut = Tkinter.Button(self.spect, text='WriteSpectrumToFile', command=self.write_spectrum_file)
		writespectfilebut.place(relx=0.6,rely=0.85)

	def write_spectrum_file(self):
		# TODO: 
		timestr = time.strftime("%Y%m%d-%H%M%S")
		with open("spectrum"+timestr+".txt", "w") as outfile:
			json.dump(self.spectrum_amps, outfile)
		# Should also write the whole dict to a file as well. 
		d = self.image_reconstruct.get_freq_dict()
		# outfile = timestr+'.npz'
		# np.savez(outfile, d=d)
		with open(timestr+'.pkl', 'wb') as output:
			# Pickle dictionary using protocol 0.
			pickle.dump(d, output)

	def onclick(self,event):
		if event.xdata is not None:		
			self.pixel_x = int(event.xdata)
			self.pixel_y = int(event.ydata)
		print ("pixel x/y:",self.pixel_x,self.pixel_y)
		# This is also when we should update the location of the rectangle.
		self.spectimageplt.cla()
		# self.spectplot.set_array(self.img)
		self.spectplot = self.spectimageplt.imshow(self.img,interpolation='nearest') 
		# rect.remove()
		# Create a Rectangle patch
		rect = mpl.patches.Rectangle((self.pixel_x,self.pixel_y),1,1,linewidth=0.5,edgecolor='r',facecolor='none', fill=False)
		# Add the patch to the Axes
		self.spectimageplt.add_patch(rect)
		self.spectcanvas.draw()
		self.spectcanvas.flush_events() 


	def xypoints(self,event): 
		# 
		self.pixel_x = self.point_x.get()
		self.pixel_y = self.point_y.get()
		print ('x/y point', self.pixel_x,self.pixel_y)
		# should add in the rectangle location update. 
		self.spectimageplt.cla()	
		# rect.remove()
		self.spectplot = self.spectimageplt.imshow(self.img,interpolation='nearest') 
		# self.spectplot.set_array(self.img)
		# Create a Rectangle patch
		rect = mpl.patches.Rectangle((self.pixel_x,self.pixel_y),1,1,linewidth=0.5,edgecolor='r',facecolor='none', fill=False)
		# Add the patch to the Axes
		self.spectimageplt.add_patch(rect)
		self.spectcanvas.draw()
		self.spectcanvas.flush_events() 



	def quit(self):
		self.root.quit()     # stops mainloop
		self.root.destroy()  # this is necessary on Windows to prevent
		# Fatal Python Error: PyEval_RestoreThread: NULL tstate
		exit()

	def evaluate(self,event): 
		# 
		sliders = [self.min_slider_l.get(),self.min_slider_h.get(),self.max_slider_l.get(),self.max_slider_h.get()]
		i = 0 
		for value in sliders: 
			if value is not "":
				self.sliders[i]= int(value)
			i = i+1
		print ('slider values', self.sliders )
		# # re-initialize the sliders ranges. 
		self.w1.configure(from_=self.sliders[0], to=self.sliders[1])
		self.w2.configure(from_=self.sliders[2], to=self.sliders[3])

	def update_hist(self):

		self.plot.set_array(self.img)
		self.histplt.cla()
		flatimg = self.img.flatten()
		n,bins,patches = self.histplt.hist(flatimg,bins='auto', facecolor='g')
		self.hist_update = False
		self.canvas.draw()
		self.canvas.flush_events()

if __name__ == "__main__":  
	Gui()






