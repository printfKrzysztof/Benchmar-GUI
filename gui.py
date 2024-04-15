import customtkinter as ctk
import serial
import threading
import time
MAX_ARGS = 4

crc16_tab = [
    0x0000, 0xc0c1, 0xc181, 0x0140, 0xc301, 0x03c0, 0x0280, 0xc241,
    0xc601, 0x06c0, 0x0780, 0xc741, 0x0500, 0xc5c1, 0xc481, 0x0440,
    0xcc01, 0x0cc0, 0x0d80, 0xcd41, 0x0f00, 0xcfc1, 0xce81, 0x0e40,
    0x0a00, 0xcac1, 0xcb81, 0x0b40, 0xc901, 0x09c0, 0x0880, 0xc841,
    0xd801, 0x18c0, 0x1980, 0xd941, 0x1b00, 0xdbc1, 0xda81, 0x1a40,
    0x1e00, 0xdec1, 0xdf81, 0x1f40, 0xdd01, 0x1dc0, 0x1c80, 0xdc41,
    0x1400, 0xd4c1, 0xd581, 0x1540, 0xd701, 0x17c0, 0x1680, 0xd641,
    0xd201, 0x12c0, 0x1380, 0xd341, 0x1100, 0xd1c1, 0xd081, 0x1040,
    0xf001, 0x30c0, 0x3180, 0xf141, 0x3300, 0xf3c1, 0xf281, 0x3240,
    0x3600, 0xf6c1, 0xf781, 0x3740, 0xf501, 0x35c0, 0x3480, 0xf441,
    0x3c00, 0xfcc1, 0xfd81, 0x3d40, 0xff01, 0x3fc0, 0x3e80, 0xfe41,
    0xfa01, 0x3ac0, 0x3b80, 0xfb41, 0x3900, 0xf9c1, 0xf881, 0x3840,
    0x2800, 0xe8c1, 0xe981, 0x2940, 0xeb01, 0x2bc0, 0x2a80, 0xea41,
    0xee01, 0x2ec0, 0x2f80, 0xef41, 0x2d00, 0xedc1, 0xec81, 0x2c40,
    0xe401, 0x24c0, 0x2580, 0xe541, 0x2700, 0xe7c1, 0xe681, 0x2640,
    0x2200, 0xe2c1, 0xe381, 0x2340, 0xe101, 0x21c0, 0x2080, 0xe041,
    0xa001, 0x60c0, 0x6180, 0xa141, 0x6300, 0xa3c1, 0xa281, 0x6240,
    0x6600, 0xa6c1, 0xa781, 0x6740, 0xa501, 0x65c0, 0x6480, 0xa441,
    0x6c00, 0xacc1, 0xad81, 0x6d40, 0xaf01, 0x6fc0, 0x6e80, 0xae41,
    0xaa01, 0x6ac0, 0x6b80, 0xab41, 0x6900, 0xa9c1, 0xa881, 0x6840,
    0x7800, 0xb8c1, 0xb981, 0x7940, 0xbb01, 0x7bc0, 0x7a80, 0xba41,
    0xbe01, 0x7ec0, 0x7f80, 0xbf41, 0x7d00, 0xbdc1, 0xbc81, 0x7c40,
    0xb401, 0x74c0, 0x7580, 0xb541, 0x7700, 0xb7c1, 0xb681, 0x7640,
    0x7200, 0xb2c1, 0xb381, 0x7340, 0xb101, 0x71c0, 0x7080, 0xb041,
    0x5000, 0x90c1, 0x9181, 0x5140, 0x9301, 0x53c0, 0x5280, 0x9241,
    0x9601, 0x56c0, 0x5780, 0x9741, 0x5500, 0x95c1, 0x9481, 0x5440,
    0x9c01, 0x5cc0, 0x5d80, 0x9d41, 0x5f00, 0x9fc1, 0x9e81, 0x5e40,
    0x5a00, 0x9ac1, 0x9b81, 0x5b40, 0x9901, 0x59c0, 0x5880, 0x9841,
    0x8801, 0x48c0, 0x4980, 0x8941, 0x4b00, 0x8bc1, 0x8a81, 0x4a40,
    0x4e00, 0x8ec1, 0x8f81, 0x4f40, 0x8d01, 0x4dc0, 0x4c80, 0x8c41,
    0x4400, 0x84c1, 0x8581, 0x4540, 0x8701, 0x47c0, 0x4680, 0x8641,
    0x8201, 0x42c0, 0x4380, 0x8341, 0x4100, 0x81c1, 0x8081, 0x4040
]

def crc16(buf):
    crc = 0xFFFF
    for byte in buf:
        crc = (crc >> 8) ^ crc16_tab[(crc ^ byte) & 0xFF]
    return crc

def code_frame(frame, command, arg_count, args):
    assert arg_count <= MAX_ARGS, "Too many arguments"
    if arg_count > MAX_ARGS:
        return "ERR_FRM_WRONG_COMMAND"
    frame[0] = 0xFF
    frame[1] = command
    frame[2] = arg_count
    for i in range(arg_count):
        frame[3 + i] = args[i]
    crc = crc16(frame[:7])
    frame[7] = (crc >> 8) & 0xFF
    frame[8] = crc & 0xFF
    return 0

def decode_frame(frame, command, arg_count, args):
    assert frame[2] <= MAX_ARGS, "Too many arguments"
    if frame[2] > MAX_ARGS:
        return "ERR_FRM_WRONG_COMMAND"
    if frame[0] != 0xFF:
        return "ERR_FRM_WRONG_START"
    command = frame[1] 
    arg_count = frame[2] 
    for i in range(arg_count):
        args[i] = frame[3 + i]
    crc = crc16(frame[:7])
    if crc != frame[7] >> 8 | frame[8]:
        return "ERR_FRM_WRONG_CRC"
    return 0

class SerialThread(threading.Thread):
    def __init__(self, app):
        super().__init__()
        self.stop_event = threading.Event()
        self.app = app
        self.last_command_time = 0
        self.ser = app.ser

    def run(self):
        while not self.stop_event.is_set():
            try:
                if time.time() - self.last_command_time > 0.5:
                    # Send command 5 frame every 500 ms
                    frame = bytearray(9)
                    command = 0x05
                    arg_count = 0
                    args = []
                    result = code_frame(frame, command, arg_count, args)
                    if result == 0:
                        self.ser.write(frame)
                        response = self.ser.readline().strip()
                        if response:
                            command_anw = 0
                            arg_count_anw = 0
                            args_anw = []
                            if decode_frame(response,command_anw,arg_count_anw,args_anw):   
                                self.app.change_state(True, True)
                                self.last_command_time = time.time()
            except:
                return 0

            if time.time() - self.last_command_time > 1:
                self.app.change_state(False, False)
        return 0
    def stop(self):
        self.stop_event.set()


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Communication App")
        self.connection_status = False
        self.serial_thread = None
        self.blocked_state = False
        self.create_widgets()
        try:
            self.ser = serial.Serial('/dev/ttyACM0', 38400, timeout=1)     
        except serial.SerialException:
            print("Serial port error")
        finally:
            print("Could not connect to target ")


    def create_widgets(self):

        self.frame = ctk.CTkFrame(self.root)
        self.frame.pack(padx=20, pady=20)

        self.connection_button = ctk.CTkButton(self.frame, text="Połącz", command=self.start_serial)
        self.connection_button.grid(row=1, column=1, pady=5)

        ctk.CTkLabel(self.frame, text="", width=5).grid(row=1, column=0)
        self.canvas = ctk.CTkCanvas(self.frame, width=40, height=40, highlightthickness=0, bg=self.frame._fg_color[1])
        self.canvas.grid(row=1, column=2, pady=5)

        # Draw a circle on the canvas
        self.circle = self.canvas.create_oval(10, 10, 30, 30, outline=None, fill="red")

        self.task_switch_button = ctk.CTkButton(self.frame, text="Czas zmiany wątków", command=self.send_command_1)
        self.task_switch_button.grid(row=2, column=1, pady=5)

        self.semaphore_button = ctk.CTkButton(self.frame, text="Test semaforów", command=self.send_command_2)
        self.semaphore_button.grid(row=4, column=1, pady=5)

    def start_serial(self):
        if self.connection_status is False:
            self.connection_button.configure(text="Rozłącz")
            if self.serial_thread is None or not self.serial_thread.is_alive():
                self.serial_thread = SerialThread(self)
                self.serial_thread.start()
            self.connection_status = True
        else:
            self.connection_button.configure(text="Połącz")
            if self.serial_thread and self.serial_thread.is_alive():
                self.serial_thread.stop()
                self.serial_thread.join()
            self.connection_status = False
            self.change_state(False, False)

    def change_state(self, diode_state, button_state):
        if diode_state is True:
            self.canvas.itemconfig(self.circle, fill="green")
        else:
            self.canvas.itemconfig(self.circle, fill="red")

        if button_state is True:
            self.task_switch_button._state = 'normal'
            self.semaphore_button._state = 'normal'
        else:
            self.task_switch_button._state = 'disabled'
            self.semaphore_button._state = 'disabled'
            

    def send_command_1(self):
        self.blocked_state = True
        self.change_state(True,False)
        if self.serial_thread and self.serial_thread.is_alive():
            self.serial_thread.stop()
            time.sleep(0.01)
            #self.serial_thread.join()
        
        frame = bytearray(9)
        command = 0x00
        arg_count = 0
        args = []
        result = code_frame(frame, command, arg_count, args)

        if result == 0:
            self.ser.write(frame)
            response = self.ser.readline().strip()
            if response:
                command_anw = 0
                arg_count_anw = 0
                args_anw = []
                if decode_frame(response,command_anw,arg_count_anw,args_anw):  
                    if command_anw == command and arg_count_anw > 0:
                        print("Sukces")
            else:
                print("error")
      
        self.serial_thread = SerialThread(self)
        self.serial_thread.start()
        self.blocked_state = False

    def send_command_2(self):
        self.blocked_state = True
        self.change_state(True)
        self.serial_thread.last_command_time = time.time()  # Prevent sending command 5
        frame = bytearray(9)
        command = 0x01
        arg_count = 0
        args = []
        result = code_frame(frame, command, arg_count, args)
        if result == 0:
            ser.write(frame)
            response = ser.readline().strip()
            if response:
                print("Received response to command 2")
        time.sleep(0.5)  # Wait for 500 ms without changing state
        self.blocked_state = False


if __name__ == "__main__":
    root = ctk.CTk()
    app = App(root)
    root.mainloop()
