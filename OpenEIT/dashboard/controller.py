import logging
import queue
import os
import OpenEIT.reconstruction
import OpenEIT.backend

# import dash
# from dash.dependencies import Output, Event
# import dash_core_components as dcc
# import dash_html_components as html
# import plotly.plotly as py
# import plotly.graph_objs as go
# from flask import request

# logger = logging.getLogger(__name__)

# PORT = 8050

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG) # or DEBUG
_LOGGER.addHandler(logging.StreamHandler())


class PlaybackStrategy:

    def rewind(self):
        raise NotImplementedError

    def step(self):
        raise NotImplementedError

    def step_back(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


class FilePlayback(PlaybackStrategy):
    """
    This playback strategy allows to directly feed data from files to
    the reconstruction process.
    """

    def __init__(self, file_handle, controller):
        res = []
        for line in file_handle:
            data = OpenEIT.backend.parse_line(line)
            if data is not None:
                res.append(data)
        self._file_data = res
        self._file_marker = 0
        self._queue = controller._data_queue

    def close(self):
        pass

    def rewind(self):
        self._file_marker = 0

    def step(self):
        if self._file_marker < len(self._file_data):
            self._queue.put(self._file_data[self._file_marker])
            self._file_marker += 1
            return True
        return False

    def step_back(self):
        if self._file_marker > 0:
            self._file_marker -= 1
            self._queue.put(self._file_data[self._file_marker])
            return True
        return False

class FilePlaybackDash(PlaybackStrategy):
    """
    This playback strategy allows to directly feed data from files to
    the reconstruction process.
    """
    # FilePlaybackDash(filename,contents, self)
    def __init__(self, filename,contents, controller):

        content_string = str(contents, 'utf-8')
        string = ''.join(content_string)

        res = []
        for line in string.splitlines():
            data = OpenEIT.backend.parse_line(line)
            if data is not None:
                res.append(data)
        self._file_data = res
        self._file_marker = 0
        self._queue = controller._data_queue

    def close(self):
        pass

    def rewind(self):
        self._file_marker = 0

    def step(self):
        if self._file_marker < len(self._file_data):
            self._queue.put(self._file_data[self._file_marker])
            self._file_marker += 1
            print (self._file_marker)
            return True
        return False

    def step_back(self):
        if self._file_marker > 0:
            self._file_marker -= 1
            self._queue.put(self._file_data[self._file_marker])
            return True
        return False

class VirtualSerialPortPlayback(PlaybackStrategy):
    """
    This playback strategy is used for testing the serial-port
    handling without needing the hardware. It sets up a PTY and
    connects the serial handler to the slave end of the PTY.

    .. note:: This only works on POSIX systems (which support PTYs).
    """

    def __init__(self, file_handle, controller):
        self._data_file_array = file_handle.readlines()
        self._file_marker = 0
        self._master_fd, self._slave_fd = os.openpty()
        controller.serial_handler.connect(os.ttyname(self._slave_fd))
        self._pty_master = os.fdopen(self._master_fd, "w")

    def close(self):
        os.close(self._slave_fd)
        self._pty_master.close()

    def rewind(self):
        self._file_marker = 0

    def step(self):
        if self._file_marker < len(self._data_file_array):
            self._pty_master.write(self._data_file_array[self._file_marker])
            self._file_marker += 1
            return True
        return False

    def step_back(self):
        if self._file_marker > 0:
            self._file_marker -= 1
            self._pty_master.write(self._data_file_array[self._file_marker])
            return True
        return False

class Controller:

    def __init__(self):
        self._signal_connections = {}
        self.recording = False

        # setup the queues for the workers
        self._data_queue  = queue.Queue()
        self._image_queue = queue.Queue()

        self.choice = 'a'

        # instantiate the serial handler. It should be instantiated knowing what sort of data it is expecting. 
        self.serial_handler = OpenEIT.backend.SerialHandler(self._data_queue,self.choice)

        self.playback = None
        self._n_el = 8
        self._algorithm ='bp'
        self._mode='singlefrequency'
        self._fwsequence='e_conf.txt'  


    def configure(self, *, initial_port=None, virtual_tty=False,
                 read_file=False,n_el=8,algorithm='bp',mode='singlefrequency',fwsequence='e_conf.txt'):

        if initial_port is not None:
            if virtual_tty:
                with open(initial_port, "r") as file_handle:
                    self.playback = VirtualSerialPortPlayback(file_handle,
                                                              self)
                    self.emit("connection_state_changed", True)
            elif read_file:
                with open(initial_port, "r") as file_handle:
                    self.playback = FilePlaybackDash(file_handle, self)
                    self.emit("connection_state_changed", True)
            else:
                self.menuselect.set(initial_port)
                self.connect()

        self._n_el=int(n_el)
        self._algorithm=algorithm
        self._mode=mode
        self._fwsequence=fwsequence      
 
        self.image_reconstruct = OpenEIT.reconstruction.ReconstructionWorker(
            self._data_queue,
            self._image_queue,
            self._algorithm,
            self._n_el
        )

        if self._algorithm == 'jac' or self._algorithm == 'bp': 
            self.x,self.y,self.tri,self.el_pos = self.image_reconstruct.get_plot_params()
        if self._algorithm == 'greit':
            self.gx,self.gy,self.ds = self.image_reconstruct.get_greit_params()  
        self.image_reconstruct.start()


    @property
    def image_queue(self):
        return self._image_queue

    @property
    def data_queue(self):
        return self._data_queue

    @property
    def n_el(self):
        return self._n_el

    @property
    def algorithm(self):
        return self._algorithm

    def plot_params(self):
        return self.x,self.y,self.tri,self.el_pos

    def greit_params(self):
        self.gx,self.gy,self.ds = self.image_reconstruct.get_greit_params() 
        return self.gx,self.gy,self.ds   

    def baseline(self):

        self.image_reconstruct.baseline()

    def reset_baseline(self):
        self.image_reconstruct.reset_baseline()

    def register(self, signal, callable_):
        # TODO: supply a cookie for disconnecting
        self._signal_connections.setdefault(signal, []).append(callable_)

    def emit(self, signal, *args, **kwargs):
        for handler in self._signal_connections.get(signal, ()):
            handler(*args, **kwargs)

    def connect(self, port):
        self.serial_handler.connect(port)
        self.emit("connection_state_changed", True)

    def return_line(self):
        return self.serial_handler.return_last_line()

    def serial_write(self, text):
        self.serial_handler.write(text)

    def disconnect(self):
        if self.playback is not None:
            self.playback.close()
            self.playback = None

        self.serial_handler.disconnect()
        self.emit("connection_state_changed", False)

    def load_file(self, filename, contents):
        self.disconnect()
        self.playback = FilePlaybackDash(filename,contents, self)
        self.emit("connection_state_changed", True)

    def step_file(self):
        if self.playback is not None:
            print ('stepping file.')
            return self.playback.step()
        return False

    def step_file_back(self):
        if self.playback is not None:
            return self.playback.step_back()
        return False

    def run_file(self):
        if self.playback is not None:
            if self.playback.step():
                self.root.after(10, self.run_file)

    def reset_file(self):
        if self.playback is not None:
            self.playback.rewind()

    def start_recording(self):
        if self.serial_handler.recording:
            logger.info('it is already recording')
            return

        self.serial_handler.start_recording()
        self.emit("recording_state_changed", True)
        logger.info('started recording here')

    def stop_recording(self):
        if not self.serial_handler.recording:
            return

        self.serial_handler.stop_recording()
        self.emit("recording_state_changed", False)
        logger.info('stopped recording here')

    def shutdown(self):
        # stop recording to flush the buffers
        self.stop_recording()
