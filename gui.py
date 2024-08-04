import customtkinter as ctk
import serial
import threading
import time
import struct
import argparse
import matplotlib.pyplot as plt
import random
import os
import shutil
import statistics


# Add this line at the beginning of your script to parse command-line arguments
parser = argparse.ArgumentParser(description='Program do benchmarkowania RTOS')
parser.add_argument('--port', help='Serial port')
args = parser.parse_args()

# Use the port argument provided from the command line
serial_port = args.port
MAX_ARGS = 4
MAX_SCORES = 400

# Values measured from a bear metal program!
TASK_SWITCH_TICKS = 14
TASK_SWITCH_TIME = float("{:.9f}".format(TASK_SWITCH_TICKS / 72.000))
MEASSURE_TICKS = 6
MEASSURE_TIME = float("{:.9f}".format(MEASSURE_TICKS / 72.000))  # Time in us

COLORS = [
    'blue',
    'green',
    'purple',
    'olive'
]

mutex = threading.Lock()  # Binary semaphore

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


def code_command_frame(frame, command, arg_count, args):
    if arg_count > MAX_ARGS:
        return "ERR_FRM_WRONG_ARG_COUNT"
    frame[0] = 0xFF
    frame[1] = command
    frame[2] = arg_count
    for i in range(arg_count):
        frame[3 + i] = args[i]
    crc = crc16(frame[:arg_count+3])
    frame[7] = ((crc >> 8) & 0xFF)
    frame[8] = (crc & 0xFF)
    return 0


def decode_command_frame(frame, args):
    if frame[0] != 0xFF:
        return "ERR_FRM_WRONG_START"
    if frame[2] >> 8 | frame[3] > MAX_SCORES:
        return "ERR_FRM_WRONG_ARG_COUNT"
    command = frame[1]
    arg_count = frame[2] << 8 | frame[3]
    for i in range(arg_count):
        args.append(frame[4 + i])
    crc = crc16(frame[:4+arg_count])
    if crc != (frame[404] << 8 | frame[405]):
        return "ERR_FRM_WRONG_CRC"
    return 0, command, arg_count


class App(ctk.CTk):
    def __init__(self, port):
        super().__init__()
        self.title("RTOS Benchmark")
        self.geometry(f"{950}x{350}")
        self.resizable(False, False)
        self.connection_status = False
        self.blocked_state = False
        self.create_widgets()
        self.ser = None

        while self.ser is None:
            try:
                self.ser = serial.Serial(port, 38400, timeout=59)
            except serial.SerialException:
                print("Serial port error")
                time.sleep(1)
            else:
                print("Connected to target")

    def create_widgets(self):

        self.frame = ctk.CTkFrame(self)
        self.frame.pack(padx=20, pady=20)

        ctk.CTkLabel(self.frame, text="", width=5).grid(row=1, column=0)

        self.current_label = ctk.CTkLabel(
            self.frame, text="Wprowadź parametry")
        self.current_label.grid(row=1, column=0, pady=5, padx=10)

        self.current_label = ctk.CTkLabel(
            self.frame, text="Wybierz test do przeprowadzenia")
        self.current_label.grid(row=1, column=1, pady=5, padx=10)

        self.canvas = ctk.CTkCanvas(
            self.frame, width=40, height=40, highlightthickness=0, bg=self.frame._fg_color[1])
        self.canvas.grid(row=1, column=2, pady=5)
        self.circle = self.canvas.create_oval(
            10, 10, 30, 30, outline=None, fill="red")

        self.score_label = ctk.CTkLabel(self.frame, text="Analiza")
        self.score_label.grid(row=1, column=3, pady=5, padx=10)

        button_width = 350  # Adjust the width as needed
        score_button_wdith = 70
        input_width = 275

        # Variable to track the selected radio button
        self.radio_var = ctk.Variable(value=1)

        self.radio_button1 = ctk.CTkRadioButton(
            self.frame, text="FreeRTOS", variable=self.radio_var, value=1, command=self.change_radio_button)
        self.radio_button1.grid(row=0, column=0, padx=10, pady=5)

        self.radio_button2 = ctk.CTkRadioButton(
            self.frame, text="EmbOS", variable=self.radio_var, value=2, command=self.change_radio_button)
        self.radio_button2.grid(row=0, column=1, padx=10, pady=5)

        self.radio_button3 = ctk.CTkRadioButton(
            self.frame, text="Zephyr", variable=self.radio_var, value=3, command=self.change_radio_button)
        self.radio_button3.grid(row=0, column=2, padx=10, pady=5)

        self.start_test_button = ctk.CTkButton(
            self.frame, command=self.start_tests, text="Start", width=score_button_wdith, fg_color="azure2", text_color="dimgray")
        self.start_test_button.grid(row=0, column=3, padx=10, pady=5)

        # Path creation for results
        self.radio_options = {
            1: "FreeRTOS",
            2: "EmbOS",
            3: "Zephyr"
        }
        self.system_string = "FreeRTOS"
        self.test_string = "custom"

        self.task_force_switch_input = ctk.CTkEntry(
            self.frame, placeholder_text="L. wątków; L. testów", width=input_width)
        self.task_force_switch_input.grid(row=3, column=0, pady=5, padx=10)
        self.task_force_switch_button = ctk.CTkButton(
            self.frame, text="Test wymuszonej zmiany wątków", command=self.task_force_switch_command, width=button_width)
        self.task_force_switch_button.grid(row=3, column=1, pady=5)
        self.task_force_switch_label = ctk.CTkLabel(
            self.frame, text="    -----    ")
        self.task_force_switch_label.grid(row=3, column=2, pady=5, padx=10)
        self.task_force_switch_score = ctk.CTkButton(
            self.frame, command=self.task_force_switch_analyze, text="Wyniki", width=score_button_wdith, fg_color="azure2", text_color="dimgray")
        self.task_force_switch_score.grid(row=3, column=3, pady=5, padx=10)

        self.task_force_switch_priority_input = ctk.CTkEntry(
            self.frame, placeholder_text="L. w. niski; L. w. wysoki ; L. testów", width=input_width)
        self.task_force_switch_priority_input.grid(
            row=4, column=0, pady=5, padx=10)
        self.task_force_switch_priority_button = ctk.CTkButton(
            self.frame, text="Test wymuszonej zmiany wątków (różne piorytety)", command=self.task_force_switch_priority_command, width=button_width, fg_color="darkorchid4")
        self.task_force_switch_priority_button.grid(row=4, column=1, pady=5)
        self.task_force_switch_priority_label = ctk.CTkLabel(
            self.frame, text="    -----    ")
        self.task_force_switch_priority_label.grid(
            row=4, column=2, pady=5, padx=10)
        self.task_force_switch_priority_score = ctk.CTkButton(
            self.frame, command=self.task_force_switch_priority_analyze, text="Wyniki", width=score_button_wdith, fg_color="azure2", text_color="dimgray")
        self.task_force_switch_priority_score.grid(
            row=4, column=3, pady=5, padx=10)

        self.task_switch_input = ctk.CTkEntry(
            self.frame, placeholder_text="L. wątków; L. testów", width=input_width)
        self.task_switch_input.grid(row=5, column=0, pady=5, padx=10)
        self.task_switch_button = ctk.CTkButton(
            self.frame, text="Test wywłaszczania wątków", command=self.task_switch_command, width=button_width, fg_color="brown")
        self.task_switch_button.grid(row=5, column=1, pady=5)
        self.task_switch_label = ctk.CTkLabel(self.frame, text="    -----    ")
        self.task_switch_label.grid(row=5, column=2, pady=5, padx=10)
        self.task_switch_score = ctk.CTkButton(self.frame, command=self.task_switch_analyze,
                                               text="Wyniki", width=score_button_wdith, fg_color="azure2", text_color="dimgray")
        self.task_switch_score.grid(row=5, column=3, pady=5, padx=10)

        self.task_switch_priority_input = ctk.CTkEntry(
            self.frame, placeholder_text="L. w. niski; L. w. wysoki ; L. testów", width=input_width)
        self.task_switch_priority_input.grid(row=6, column=0, pady=5, padx=10)
        self.task_switch_priority_button = ctk.CTkButton(
            self.frame, text="Test wywłaszczenia wątków (różne piorytety)", command=self.task_switch_priority_command, width=button_width, fg_color="chocolate1")
        self.task_switch_priority_button.grid(row=6, column=1, pady=5)
        self.task_switch_priority_label = ctk.CTkLabel(
            self.frame, text="    -----    ")
        self.task_switch_priority_label.grid(row=6, column=2, pady=5, padx=10)
        self.task_switch_priority_score = ctk.CTkButton(
            self.frame, command=self.task_switch_priority_analyze, text="Wyniki", width=score_button_wdith, fg_color="azure2", text_color="dimgray")
        self.task_switch_priority_score.grid(row=6, column=3, pady=5, padx=10)

        self.semaphore_input = ctk.CTkEntry(
            self.frame, placeholder_text="L. wątków; L. testów", width=input_width)
        self.semaphore_input.grid(row=7, column=0, pady=5, padx=10)
        self.semaphore_button = ctk.CTkButton(
            self.frame, text="Test semaforów", command=self.semaphore_command, width=button_width, fg_color="darkgoldenrod3")
        self.semaphore_button.grid(row=7, column=1, pady=5)
        self.semaphore_label = ctk.CTkLabel(self.frame, text="    -----    ")
        self.semaphore_label.grid(row=7, column=2, pady=5, padx=10)
        self.semaphore_score = ctk.CTkButton(self.frame, command=self.semaphore_analyze,
                                             text="Wyniki", width=score_button_wdith, fg_color="azure2", text_color="dimgray")
        self.semaphore_score.grid(row=7, column=3, pady=5, padx=10)

        self.queue_input = ctk.CTkEntry(
            self.frame, placeholder_text="L. testów", width=input_width)
        self.queue_input.grid(row=8, column=0, pady=5, padx=10)
        self.queue_button = ctk.CTkButton(
            self.frame, text="Test kolejki", command=self.queue_command, width=button_width,  fg_color="darkgreen")
        self.queue_button.grid(row=8, column=1, pady=5)
        self.queue_label = ctk.CTkLabel(self.frame, text="    -----    ")
        self.queue_label.grid(row=8, column=2, pady=5, padx=10)
        self.queue_score = ctk.CTkButton(self.frame, command=self.queue_analyze, text="Wyniki",
                                         width=score_button_wdith, fg_color="azure2", text_color="dimgray")
        self.queue_score.grid(row=8, column=3, pady=5, padx=10)

    def start_tests(self):

        with open(f"./results/{self.system_string}/summary.txt", "a") as summary_file:
            switch_times_global = []
            in_task_times_global = []

            # # TASK SWITCH
            # summary_file.write("Test wywłaszczenia wątków:\n")
            # # 5_5 part
            # summary_file.write("\t- test 5 wątków po 5 pomiarów:\n")
            # self.task_switch_input.delete(0, ctk.END)
            # self.task_switch_input.insert(0, "5; 10")
            # for i in range(2):
            #     task_times = []
            #     switch_times = []
            #     in_task_times = []
            #     self.test_string = f"5_5_{i}"
            #     if (self.task_switch_command() != 0):
            #         return False
            #     # System analyzed
            #     for j in range(5):
            #         filename = f"./results/{self.system_string}/task_switch/{self.test_string}/raw/{j}.txt"
            #         # Read task times from file
            #         with open(filename, "r") as file:
            #             for line in file:
            #                 task_times.append(int(line.strip()))
            #     time.sleep(1)

            #     task_times.sort()

            #     with open(f"./results/{self.system_string}/task_switch/{self.test_string}/sorted_times.txt", "w") as file:
            #         for timex in task_times:
            #             file.write(f"{timex}\n")

            #     for j in range(1, len(task_times), 2):
            #         if j + 2 < len(task_times):
            #             switch_times.append(task_times[j+1] - task_times[j])
            #             switch_times_global.append(
            #                 task_times[j+1] - task_times[j])
            #             in_task_times.append(task_times[j+2] - task_times[j+1])
            #             in_task_times_global.append(
            #                 task_times[j+2] - task_times[j+1])

            #     with open(f"./results/{self.system_string}/task_switch/{self.test_string}/switch_times.txt", "w") as file:
            #         for timex in switch_times:
            #             file.write(f"{timex}\n")

            #     with open(f"./results/{self.system_string}/task_switch/{self.test_string}/in_task_times.txt", "w") as file:
            #         for timex in in_task_times:
            #             file.write(f"{timex}\n")

            # mean_switch_time = statistics.mean(
            #     switch_times_global) if switch_times_global else 0
            # stdev_switch_time = statistics.stdev(
            #     switch_times_global) if len(switch_times_global) > 1 else 0
            # max_switch_time = max(
            #     switch_times_global) if switch_times_global else 0
            # min_switch_time = min(
            #     switch_times_global) if switch_times_global else 0

            # # Calculating statistics for in_task_times_global
            # mean_in_task_time = statistics.mean(
            #     in_task_times_global) if in_task_times_global else 0
            # stdev_in_task_time = statistics.stdev(
            #     in_task_times_global) if len(in_task_times_global) > 1 else 0
            # max_in_task_time = max(
            #     in_task_times_global) if in_task_times_global else 0
            # min_in_task_time = min(
            #     in_task_times_global) if in_task_times_global else 0

            # summary_file.write(
            #     f"\t\t- Średni czas zmiany wątku | przebywania w wątku: {mean_switch_time} | {mean_in_task_time}\n")
            # summary_file.write(
            #     f"\t\t- Odchylenie standardowe czasu zmiany wątku | przebywania w wątku: {stdev_switch_time} | {stdev_in_task_time}\n")
            # summary_file.write(
            #     f"\t\t- Maksymalny czas zmiany wątku | przebywania w wątku: {max_switch_time} | {max_in_task_time}\n")
            # summary_file.write(
            #     f"\t\t- Minimalny czas zmiany wątku | przebywania w wątku: {min_switch_time} | {min_in_task_time}\n")

            # switch_times_global = []
            # in_task_times_global = []

            # # 10_5 part
            # self.task_switch_input.delete(0, ctk.END)
            # self.task_switch_input.insert(0, "10; 10")
            # summary_file.write("\t- test 10 wątków po 5 pomiarów:\n")
            # for i in range(2):
            #     task_times = []
            #     switch_times = []
            #     in_task_times = []
            #     self.test_string = f"10_5_{i}"
            #     if (self.task_switch_command() != 0):
            #         return False
            #     for j in range(10):
            #         filename = f"./results/{self.system_string}/task_switch/{self.test_string}/raw/{j}.txt"
            #         # Read task times from file
            #         with open(filename, "r") as file:
            #             for line in file:
            #                 task_times.append(int(line.strip()))
            #     time.sleep(1)

            #     task_times.sort()

            #     with open(f"./results/{self.system_string}/task_switch/{self.test_string}/sorted_times.txt", "w") as file:
            #         for timex in task_times:
            #             file.write(f"{timex}\n")

            #     for j in range(1, len(task_times), 2):
            #         if j + 2 < len(task_times):
            #             switch_times.append(task_times[j+1] - task_times[j])
            #             switch_times_global.append(
            #                 task_times[j+1] - task_times[j])
            #             in_task_times.append(task_times[j+2] - task_times[j+1])
            #             in_task_times_global.append(
            #                 task_times[j+2] - task_times[j+1])

            #     with open(f"./results/{self.system_string}/task_switch/{self.test_string}/switch_times.txt", "w") as file:
            #         for timex in switch_times:
            #             file.write(f"{timex}\n")

            #     with open(f"./results/{self.system_string}/task_switch/{self.test_string}/in_task_times.txt", "w") as file:
            #         for timex in in_task_times:
            #             file.write(f"{timex}\n")

            # mean_switch_time = statistics.mean(
            #     switch_times_global) if switch_times_global else 0
            # stdev_switch_time = statistics.stdev(
            #     switch_times_global) if len(switch_times_global) > 1 else 0
            # max_switch_time = max(
            #     switch_times_global) if switch_times_global else 0
            # min_switch_time = min(
            #     switch_times_global) if switch_times_global else 0

            # # Calculating statistics for in_task_times_global
            # mean_in_task_time = statistics.mean(
            #     in_task_times_global) if in_task_times_global else 0
            # stdev_in_task_time = statistics.stdev(
            #     in_task_times_global) if len(in_task_times_global) > 1 else 0
            # max_in_task_time = max(
            #     in_task_times_global) if in_task_times_global else 0
            # min_in_task_time = min(
            #     in_task_times_global) if in_task_times_global else 0

            # summary_file.write(
            #     f"\t\t- Średni czas zmiany wątku | przebywania w wątku: {mean_switch_time} | {mean_in_task_time}\n")
            # summary_file.write(
            #     f"\t\t- Odchylenie standardowe czasu zmiany wątku | przebywania w wątku: {stdev_switch_time} | {stdev_in_task_time}\n")
            # summary_file.write(
            #     f"\t\t- Maksymalny czas zmiany wątku | przebywania w wątku: {max_switch_time} | {max_in_task_time}\n")
            # summary_file.write(
            #     f"\t\t- Minimalny czas zmiany wątku | przebywania w wątku: {min_switch_time} | {min_in_task_time}\n")

            # switch_times_global = []
            # in_task_times_global = []

            # # 20_10 part
            # self.task_switch_input.delete(0, ctk.END)
            # self.task_switch_input.insert(0, "20; 20")
            # summary_file.write("\t- test 20 wątków po 10 pomiarów:\n")
            # for i in range(10):
            #     task_times = []
            #     switch_times = []
            #     in_task_times = []
            #     self.test_string = f"20_10_{i}"
            #     if (self.task_switch_command() != 0):
            #         return False
            #     for j in range(20):
            #         filename = f"./results/{self.system_string}/task_switch/{self.test_string}/raw/{j}.txt"
            #         # Read task times from file
            #         with open(filename, "r") as file:
            #             for line in file:
            #                 task_times.append(int(line.strip()))
            #     time.sleep(1)

            #     task_times.sort()

            #     with open(f"./results/{self.system_string}/task_switch/{self.test_string}/sorted_times.txt", "w") as file:
            #         for timex in task_times:
            #             file.write(f"{timex}\n")

            #     for j in range(1, len(task_times), 2):
            #         if j + 2 < len(task_times):
            #             switch_times.append(task_times[j+1] - task_times[j])
            #             switch_times_global.append(
            #                 task_times[j+1] - task_times[j])
            #             in_task_times.append(task_times[j+2] - task_times[j+1])
            #             in_task_times_global.append(
            #                 task_times[j+2] - task_times[j+1])

            #     with open(f"./results/{self.system_string}/task_switch/{self.test_string}/switch_times.txt", "w") as file:
            #         for timex in switch_times:
            #             file.write(f"{timex}\n")

            #     with open(f"./results/{self.system_string}/task_switch/{self.test_string}/in_task_times.txt", "w") as file:
            #         for timex in in_task_times:
            #             file.write(f"{timex}\n")

            # mean_switch_time = statistics.mean(
            #     switch_times_global) if switch_times_global else 0
            # stdev_switch_time = statistics.stdev(
            #     switch_times_global) if len(switch_times_global) > 1 else 0
            # max_switch_time = max(
            #     switch_times_global) if switch_times_global else 0
            # min_switch_time = min(
            #     switch_times_global) if switch_times_global else 0

            # # Calculating statistics for in_task_times_global
            # mean_in_task_time = statistics.mean(
            #     in_task_times_global) if in_task_times_global else 0
            # stdev_in_task_time = statistics.stdev(
            #     in_task_times_global) if len(in_task_times_global) > 1 else 0
            # max_in_task_time = max(
            #     in_task_times_global) if in_task_times_global else 0
            # min_in_task_time = min(
            #     in_task_times_global) if in_task_times_global else 0

            # summary_file.write(
            #     f"\t\t- Średni czas zmiany wątku | przebywania w wątku: {mean_switch_time} | {mean_in_task_time}\n")
            # summary_file.write(
            #     f"\t\t- Odchylenie standardowe czasu zmiany wątku | przebywania w wątku: {stdev_switch_time} | {stdev_in_task_time}\n")
            # summary_file.write(
            #     f"\t\t- Maksymalny czas zmiany wątku | przebywania w wątku: {max_switch_time} | {max_in_task_time}\n")
            # summary_file.write(
            #     f"\t\t- Minimalny czas zmiany wątku | przebywania w wątku: {min_switch_time} | {min_in_task_time}\n")

            # switch_times_global = []
            # in_task_times_global = []

            # # TASK SWITCH PRIORITY
            # summary_file.write("Test wywłaszczenia wątków (piorytety):\n")

            # # 3_3_4 part
            # summary_file.write(
            #     "\t- test 3 wątków p. wysoki i 3 p. niski po 4 pomiary:\n")
            # self.task_switch_priority_input.delete(0, ctk.END)
            # self.task_switch_priority_input.insert(0, "3; 3; 4")
            # for i in range(2):
            #     task_times = []
            #     switch_times = []
            #     in_task_times = []
            #     self.test_string = f"3_3_4_{i}"
            #     if (self.task_switch_priority_command() != 0):
            #         return False
            #     # System analyzed
            #     for j in range(6):
            #         filename = f"./results/{self.system_string}/task_switch_priority/{self.test_string}/raw/{j}.txt"
            #         # Read task times from file
            #         with open(filename, "r") as file:
            #             for line in file:
            #                 task_times.append(int(line.strip()))
            #     time.sleep(1)

            #     task_times.sort()

            #     with open(f"./results/{self.system_string}/task_switch_priority/{self.test_string}/sorted_times.txt", "w") as file:
            #         for timex in task_times:
            #             file.write(f"{timex}\n")

            #     for j in range(1, len(task_times), 2):
            #         if j + 2 < len(task_times):
            #             switch_times.append(task_times[j+1] - task_times[j])
            #             switch_times_global.append(
            #                 task_times[j+1] - task_times[j])
            #             in_task_times.append(task_times[j+2] - task_times[j+1])
            #             in_task_times_global.append(
            #                 task_times[j+2] - task_times[j+1])

            #     with open(f"./results/{self.system_string}/task_switch_priority/{self.test_string}/switch_times.txt", "w") as file:
            #         for timex in switch_times:
            #             file.write(f"{timex}\n")

            #     with open(f"./results/{self.system_string}/task_switch_priority/{self.test_string}/in_task_times.txt", "w") as file:
            #         for timex in in_task_times:
            #             file.write(f"{timex}\n")

            # mean_switch_time = statistics.mean(
            #     switch_times_global) if switch_times_global else 0
            # stdev_switch_time = statistics.stdev(
            #     switch_times_global) if len(switch_times_global) > 1 else 0
            # max_switch_time = max(
            #     switch_times_global) if switch_times_global else 0
            # min_switch_time = min(
            #     switch_times_global) if switch_times_global else 0

            # # Calculating statistics for in_task_times_global
            # mean_in_task_time = statistics.mean(
            #     in_task_times_global) if in_task_times_global else 0
            # stdev_in_task_time = statistics.stdev(
            #     in_task_times_global) if len(in_task_times_global) > 1 else 0
            # max_in_task_time = max(
            #     in_task_times_global) if in_task_times_global else 0
            # min_in_task_time = min(
            #     in_task_times_global) if in_task_times_global else 0

            # summary_file.write(
            #     f"\t\t- Średni czas zmiany wątku | przebywania w wątku: {mean_switch_time} | {mean_in_task_time}\n")
            # summary_file.write(
            #     f"\t\t- Odchylenie standardowe czasu zmiany wątku | przebywania w wątku: {stdev_switch_time} | {stdev_in_task_time}\n")
            # summary_file.write(
            #     f"\t\t- Maksymalny czas zmiany wątku | przebywania w wątku: {max_switch_time} | {max_in_task_time}\n")
            # summary_file.write(
            #     f"\t\t- Minimalny czas zmiany wątku | przebywania w wątku: {min_switch_time} | {min_in_task_time}\n")

            # switch_times_global = []
            # in_task_times_global = []

            # # 5_5_6 part
            # summary_file.write(
            #     "\t- test 5 wątków p. wysoki i 5 p. niski po 6 pomiarów:\n")
            # self.task_switch_priority_input.delete(0, ctk.END)
            # self.task_switch_priority_input.insert(0, "5; 5; 6")
            # for i in range(2):
            #     task_times = []
            #     switch_times = []
            #     in_task_times = []
            #     self.test_string = f"5_5_6_{i}"
            #     if (self.task_switch_priority_command() != 0):
            #         return False
            #     # System analyzed
            #     for j in range(10):
            #         filename = f"./results/{self.system_string}/task_switch_priority/{self.test_string}/raw/{j}.txt"
            #         # Read task times from file
            #         with open(filename, "r") as file:
            #             for line in file:
            #                 task_times.append(int(line.strip()))
            #     time.sleep(1)

            #     task_times.sort()

            #     with open(f"./results/{self.system_string}/task_switch_priority/{self.test_string}/sorted_times.txt", "w") as file:
            #         for timex in task_times:
            #             file.write(f"{timex}\n")

            #     for j in range(1, len(task_times), 2):
            #         if j + 2 < len(task_times):
            #             switch_times.append(task_times[j+1] - task_times[j])
            #             switch_times_global.append(
            #                 task_times[j+1] - task_times[j])
            #             in_task_times.append(task_times[j+2] - task_times[j+1])
            #             in_task_times_global.append(
            #                 task_times[j+2] - task_times[j+1])

            #     with open(f"./results/{self.system_string}/task_switch_priority/{self.test_string}/switch_times.txt", "w") as file:
            #         for timex in switch_times:
            #             file.write(f"{timex}\n")

            #     with open(f"./results/{self.system_string}/task_switch_priority/{self.test_string}/in_task_times.txt", "w") as file:
            #         for timex in in_task_times:
            #             file.write(f"{timex}\n")

            # mean_switch_time = statistics.mean(
            #     switch_times_global) if switch_times_global else 0
            # stdev_switch_time = statistics.stdev(
            #     switch_times_global) if len(switch_times_global) > 1 else 0
            # max_switch_time = max(
            #     switch_times_global) if switch_times_global else 0
            # min_switch_time = min(
            #     switch_times_global) if switch_times_global else 0

            # # Calculating statistics for in_task_times_global
            # mean_in_task_time = statistics.mean(
            #     in_task_times_global) if in_task_times_global else 0
            # stdev_in_task_time = statistics.stdev(
            #     in_task_times_global) if len(in_task_times_global) > 1 else 0
            # max_in_task_time = max(
            #     in_task_times_global) if in_task_times_global else 0
            # min_in_task_time = min(
            #     in_task_times_global) if in_task_times_global else 0

            # summary_file.write(
            #     f"\t\t- Średni czas zmiany wątku | przebywania w wątku: {mean_switch_time} | {mean_in_task_time}\n")
            # summary_file.write(
            #     f"\t\t- Odchylenie standardowe czasu zmiany wątku | przebywania w wątku: {stdev_switch_time} | {stdev_in_task_time}\n")
            # summary_file.write(
            #     f"\t\t- Maksymalny czas zmiany wątku | przebywania w wątku: {max_switch_time} | {max_in_task_time}\n")
            # summary_file.write(
            #     f"\t\t- Minimalny czas zmiany wątku | przebywania w wątku: {min_switch_time} | {min_in_task_time}\n")

            # switch_times_global = []
            # in_task_times_global = []

            # # FORCE TASK SWITCH
            # summary_file.write("Test wymuszonej zmiany wątków:\n")

            # # 5_50 part
            # summary_file.write(
            #     "\t- test 5 wątków po 50 pomiarów:\n")
            # self.task_force_switch_input.delete(0, ctk.END)
            # self.task_force_switch_input.insert(0, "5; 50")
            # for i in range(2):
            #     task_times = []
            #     switch_times = []
            #     self.test_string = f"5_50_{i}"
            #     if (self.task_force_switch_command() != 0):
            #         return False
            #     # System analyzed
            #     for j in range(5):
            #         filename = f"./results/{self.system_string}/task_force_switch/{self.test_string}/raw/{j}.txt"
            #         # Read task times from file
            #         with open(filename, "r") as file:
            #             for line in file:
            #                 task_times.append(int(line.strip()))
            #     time.sleep(3)

            #     task_times.sort()

            #     with open(f"./results/{self.system_string}/task_force_switch/{self.test_string}/sorted_times.txt", "w") as file:
            #         for timex in task_times:
            #             file.write(f"{timex}\n")

            #     for j in range(len(task_times)-1):
            #         switch_times.append(
            #             task_times[j+1] - task_times[j] - TASK_SWITCH_TICKS)
            #         switch_times_global.append(
            #             task_times[j+1] - task_times[j] - TASK_SWITCH_TICKS)

            #     with open(f"./results/{self.system_string}/task_force_switch/{self.test_string}/switch_times.txt", "w") as file:
            #         for timex in switch_times:
            #             file.write(f"{timex}\n")

            # mean_switch_time = statistics.mean(
            #     switch_times_global) if switch_times_global else 0
            # stdev_switch_time = statistics.stdev(
            #     switch_times_global) if len(switch_times_global) > 1 else 0
            # max_switch_time = max(
            #     switch_times_global) if switch_times_global else 0
            # min_switch_time = min(
            #     switch_times_global) if switch_times_global else 0

            # summary_file.write(
            #     f"\t\t- Średni czas zmiany wątku: {mean_switch_time}\n")
            # summary_file.write(
            #     f"\t\t- Odchylenie standardowe czasu zmiany wątku: {stdev_switch_time}\n")
            # summary_file.write(
            #     f"\t\t- Maksymalny czas zmiany wątku: {max_switch_time}\n")
            # summary_file.write(
            #     f"\t\t- Minimalny czas zmiany wątku: {min_switch_time}\n")

            # switch_times_global = []

            # # 10_50 part
            # summary_file.write(
            #     "\t- test 10 wątków po 50 pomiarów:\n")
            # self.task_force_switch_input.delete(0, ctk.END)
            # self.task_force_switch_input.insert(0, "10; 50")
            # for i in range(2):
            #     task_times = []
            #     switch_times = []
            #     self.test_string = f"10_50_{i}"
            #     if (self.task_force_switch_command() != 0):
            #         return False
            #     # System analyzed
            #     for j in range(10):
            #         filename = f"./results/{self.system_string}/task_force_switch/{self.test_string}/raw/{j}.txt"
            #         # Read task times from file
            #         with open(filename, "r") as file:
            #             for line in file:
            #                 task_times.append(int(line.strip()))
            #     time.sleep(3)

            #     task_times.sort()

            #     with open(f"./results/{self.system_string}/task_force_switch/{self.test_string}/sorted_times.txt", "w") as file:
            #         for timex in task_times:
            #             file.write(f"{timex}\n")

            #     for j in range(len(task_times)-1):
            #         switch_times.append(
            #             task_times[j+1] - task_times[j] - TASK_SWITCH_TICKS)
            #         switch_times_global.append(
            #             task_times[j+1] - task_times[j] - TASK_SWITCH_TICKS)

            #     with open(f"./results/{self.system_string}/task_force_switch/{self.test_string}/switch_times.txt", "w") as file:
            #         for timex in switch_times:
            #             file.write(f"{timex}\n")

            # mean_switch_time = statistics.mean(
            #     switch_times_global) if switch_times_global else 0
            # stdev_switch_time = statistics.stdev(
            #     switch_times_global) if len(switch_times_global) > 1 else 0
            # max_switch_time = max(
            #     switch_times_global) if switch_times_global else 0
            # min_switch_time = min(
            #     switch_times_global) if switch_times_global else 0

            # summary_file.write(
            #     f"\t\t- Średni czas zmiany wątku: {mean_switch_time}\n")
            # summary_file.write(
            #     f"\t\t- Odchylenie standardowe czasu zmiany wątku: {stdev_switch_time}\n")
            # summary_file.write(
            #     f"\t\t- Maksymalny czas zmiany wątku: {max_switch_time}\n")
            # summary_file.write(
            #     f"\t\t- Minimalny czas zmiany wątku: {min_switch_time}\n")

            # switch_times_global = []

            # # 20_50 part
            # summary_file.write(
            #     "\t- test 20 wątków po 50 pomiarów:\n")
            # self.task_force_switch_input.delete(0, ctk.END)
            # self.task_force_switch_input.insert(0, "20; 50")
            # for i in range(10):
            #     task_times = []
            #     switch_times = []
            #     self.test_string = f"20_50_{i}"
            #     if (self.task_force_switch_command() != 0):
            #         return False
            #     # System analyzed
            #     for j in range(20):
            #         filename = f"./results/{self.system_string}/task_force_switch/{self.test_string}/raw/{j}.txt"
            #         # Read task times from file
            #         with open(filename, "r") as file:
            #             for line in file:
            #                 task_times.append(int(line.strip()))
            #     time.sleep(3)

            #     task_times.sort()

            #     with open(f"./results/{self.system_string}/task_force_switch/{self.test_string}/sorted_times.txt", "w") as file:
            #         for timex in task_times:
            #             file.write(f"{timex}\n")

            #     for j in range(len(task_times)-1):
            #         switch_times.append(
            #             task_times[j+1] - task_times[j] - TASK_SWITCH_TICKS)
            #         switch_times_global.append(
            #             task_times[j+1] - task_times[j] - TASK_SWITCH_TICKS)

            #     with open(f"./results/{self.system_string}/task_force_switch/{self.test_string}/switch_times.txt", "w") as file:
            #         for timex in switch_times:
            #             file.write(f"{timex}\n")

            # mean_switch_time = statistics.mean(
            #     switch_times_global) if switch_times_global else 0
            # stdev_switch_time = statistics.stdev(
            #     switch_times_global) if len(switch_times_global) > 1 else 0
            # max_switch_time = max(
            #     switch_times_global) if switch_times_global else 0
            # min_switch_time = min(
            #     switch_times_global) if switch_times_global else 0

            # summary_file.write(
            #     f"\t\t- Średni czas zmiany wątku: {mean_switch_time}\n")
            # summary_file.write(
            #     f"\t\t- Odchylenie standardowe czasu zmiany wątku: {stdev_switch_time}\n")
            # summary_file.write(
            #     f"\t\t- Maksymalny czas zmiany wątku: {max_switch_time}\n")
            # summary_file.write(
            #     f"\t\t- Minimalny czas zmiany wątku: {min_switch_time}\n")

            # switch_times_global = []

            # # FORCE TASK SWITCH
            # summary_file.write("Test wymuszonej zmiany wątków (priorytety):\n")
            # # 3_3_4 part
            # summary_file.write(
            #     "\t- test 3 wątków niski p. i 3 wysoki p. po 4 pomiary:\n")
            # self.task_force_switch_priority_input.delete(0, ctk.END)
            # self.task_force_switch_priority_input.insert(0, "3; 3; 4")
            # for i in range(2):
            #     task_times = []
            #     switch_times = []
            #     self.test_string = f"3_3_4_{i}"
            #     if (self.task_force_switch_priority_command() != 0):
            #         return False
            #     # System analyzed
            #     for j in range(6):
            #         filename = f"./results/{self.system_string}/task_force_switch_priority/{self.test_string}/raw/{j}.txt"
            #         # Read task times from file
            #         with open(filename, "r") as file:
            #             for line in file:
            #                 task_times.append(int(line.strip()))
            #     time.sleep(3)

            #     task_times.sort()

            #     with open(f"./results/{self.system_string}/task_force_switch_priority/{self.test_string}/sorted_times.txt", "w") as file:
            #         for timex in task_times:
            #             file.write(f"{timex}\n")

            #     for j in range(len(task_times)-1):
            #         switch_times.append(
            #             task_times[j+1] - task_times[j] - TASK_SWITCH_TICKS)
            #         switch_times_global.append(
            #             task_times[j+1] - task_times[j] - TASK_SWITCH_TICKS)

            #     with open(f"./results/{self.system_string}/task_force_switch_priority/{self.test_string}/switch_times.txt", "w") as file:
            #         for timex in switch_times:
            #             file.write(f"{timex}\n")

            # mean_switch_time = statistics.mean(
            #     switch_times_global) if switch_times_global else 0
            # stdev_switch_time = statistics.stdev(
            #     switch_times_global) if len(switch_times_global) > 1 else 0
            # max_switch_time = max(
            #     switch_times_global) if switch_times_global else 0
            # min_switch_time = min(
            #     switch_times_global) if switch_times_global else 0

            # summary_file.write(
            #     f"\t\t- Średni czas zmiany wątku: {mean_switch_time}\n")
            # summary_file.write(
            #     f"\t\t- Odchylenie standardowe czasu zmiany wątku: {stdev_switch_time}\n")
            # summary_file.write(
            #     f"\t\t- Maksymalny czas zmiany wątku: {max_switch_time}\n")
            # summary_file.write(
            #     f"\t\t- Minimalny czas zmiany wątku: {min_switch_time}\n")

            # switch_times_global = []

            # # 5_5_50 part
            # summary_file.write(
            #     "\t- test 5 wątków niski p. i 5 wysoki p. po 50 pomiarów:\n")
            # self.task_force_switch_priority_input.delete(0, ctk.END)
            # self.task_force_switch_priority_input.insert(0, "5; 5; 50")
            # for i in range(2):
            #     task_times = []
            #     switch_times = []
            #     self.test_string = f"5_5_50_{i}"
            #     if (self.task_force_switch_priority_command() != 0):
            #         return False
            #     # System analyzed
            #     for j in range(10):
            #         filename = f"./results/{self.system_string}/task_force_switch_priority/{self.test_string}/raw/{j}.txt"
            #         # Read task times from file
            #         with open(filename, "r") as file:
            #             for line in file:
            #                 task_times.append(int(line.strip()))
            #     time.sleep(3)

            #     task_times.sort()

            #     with open(f"./results/{self.system_string}/task_force_switch_priority/{self.test_string}/sorted_times.txt", "w") as file:
            #         for timex in task_times:
            #             file.write(f"{timex}\n")

            #     for j in range(len(task_times)-1):
            #         switch_times.append(
            #             task_times[j+1] - task_times[j] - TASK_SWITCH_TICKS)
            #         switch_times_global.append(
            #             task_times[j+1] - task_times[j] - TASK_SWITCH_TICKS)

            #     with open(f"./results/{self.system_string}/task_force_switch_priority/{self.test_string}/switch_times.txt", "w") as file:
            #         for timex in switch_times:
            #             file.write(f"{timex}\n")

            # mean_switch_time = statistics.mean(
            #     switch_times_global) if switch_times_global else 0
            # stdev_switch_time = statistics.stdev(
            #     switch_times_global) if len(switch_times_global) > 1 else 0
            # max_switch_time = max(
            #     switch_times_global) if switch_times_global else 0
            # min_switch_time = min(
            #     switch_times_global) if switch_times_global else 0

            # summary_file.write(
            #     f"\t\t- Średni czas zmiany wątku: {mean_switch_time}\n")
            # summary_file.write(
            #     f"\t\t- Odchylenie standardowe czasu zmiany wątku: {stdev_switch_time}\n")
            # summary_file.write(
            #     f"\t\t- Maksymalny czas zmiany wątku: {max_switch_time}\n")
            # summary_file.write(
            #     f"\t\t- Minimalny czas zmiany wątku: {min_switch_time}\n")

            # switch_times_global = []

            # FORCE TASK SWITCH
            summary_file.write("Test dostępu do semaforów:\n")
            # 5_10 part
            summary_file.write(
                "\t- test 5 wątków po 10 pomiarów\n")
            self.semaphore_input.delete(0, ctk.END)
            self.semaphore_input.insert(0, "5; 10")
            for i in range(2):
                task_times = []
                switch_times = []
                self.test_string = f"5_10_{i}"
                if (self.semaphore_command() != 0):
                    return False
                # System analyzed
                for j in range(5):
                    filename = f"./results/{self.system_string}/semaphore/{self.test_string}/raw/{j}.txt"
                    # Read task times from file
                    with open(filename, "r") as file:
                        for line in file:
                            task_times.append(int(line.strip()))
                time.sleep(1)

                task_times.sort()

                with open(f"./results/{self.system_string}/semaphore/{self.test_string}/sorted_times.txt", "w") as file:
                    for timex in task_times:
                        file.write(f"{timex}\n")

                for j in range(0, len(task_times), 2):
                    if j + 1 <= len(task_times):
                        switch_times.append(
                            task_times[j+1] - task_times[j])
                        switch_times_global.append(
                            task_times[j+1] - task_times[j])

                with open(f"./results/{self.system_string}/semaphore/{self.test_string}/semaphore_times.txt", "w") as file:
                    for timex in switch_times:
                        file.write(f"{timex}\n")

            mean_switch_time = statistics.mean(
                switch_times_global) if switch_times_global else 0
            stdev_switch_time = statistics.stdev(
                switch_times_global) if len(switch_times_global) > 1 else 0
            max_switch_time = max(
                switch_times_global) if switch_times_global else 0
            min_switch_time = min(
                switch_times_global) if switch_times_global else 0

            summary_file.write(
                f"\t\t- Średni czas oczekiwania na otworzenie semaforów: {mean_switch_time}\n")
            summary_file.write(
                f"\t\t- Odchylenie standardowe: {stdev_switch_time}\n")
            summary_file.write(
                f"\t\t- Maksymalny czas: {max_switch_time}\n")
            summary_file.write(
                f"\t\t- Minimalny czas: {min_switch_time}\n")

            switch_times_global = []

            # 10_10 part
            summary_file.write(
                "\t- test 10 wątków po 10 pomiarów\n")
            self.semaphore_input.delete(0, ctk.END)
            self.semaphore_input.insert(0, "10; 10")
            for i in range(2):
                task_times = []
                switch_times = []
                self.test_string = f"10_10_{i}"
                if (self.semaphore_command() != 0):
                    return False
                # System analyzed
                for j in range(10):
                    filename = f"./results/{self.system_string}/semaphore/{self.test_string}/raw/{j}.txt"
                    # Read task times from file
                    with open(filename, "r") as file:
                        for line in file:
                            task_times.append(int(line.strip()))
                time.sleep(1)

                task_times.sort()

                with open(f"./results/{self.system_string}/semaphore/{self.test_string}/sorted_times.txt", "w") as file:
                    for timex in task_times:
                        file.write(f"{timex}\n")

                for j in range(0, len(task_times), 2):
                    if j + 1 <= len(task_times):
                        switch_times.append(
                            task_times[j+1] - task_times[j])
                        switch_times_global.append(
                            task_times[j+1] - task_times[j])

                with open(f"./results/{self.system_string}/semaphore/{self.test_string}/semaphore_times.txt", "w") as file:
                    for timex in switch_times:
                        file.write(f"{timex}\n")

            mean_switch_time = statistics.mean(
                switch_times_global) if switch_times_global else 0
            stdev_switch_time = statistics.stdev(
                switch_times_global) if len(switch_times_global) > 1 else 0
            max_switch_time = max(
                switch_times_global) if switch_times_global else 0
            min_switch_time = min(
                switch_times_global) if switch_times_global else 0

            summary_file.write(
                f"\t\t- Średni czas oczekiwania na semafor: {mean_switch_time}\n")
            summary_file.write(
                f"\t\t- Odchylenie standardowe: {stdev_switch_time}\n")
            summary_file.write(
                f"\t\t- Maksymalny czas: {max_switch_time}\n")
            summary_file.write(
                f"\t\t- Minimalny czas: {min_switch_time}\n")

            switch_times_global = []

            # 20_50 part
            summary_file.write(
                "\t- test 20 wątków po 50 pomiarów\n")
            self.semaphore_input.delete(0, ctk.END)
            self.semaphore_input.insert(0, "20; 50")
            for i in range(10):
                task_times = []
                switch_times = []
                self.test_string = f"20_50_{i}"
                if (self.semaphore_command() != 0):
                    return False
                # System analyzed
                for j in range(20):
                    filename = f"./results/{self.system_string}/semaphore/{self.test_string}/raw/{j}.txt"
                    # Read task times from file
                    with open(filename, "r") as file:
                        for line in file:
                            task_times.append(int(line.strip()))
                time.sleep(1)

                task_times.sort()

                with open(f"./results/{self.system_string}/semaphore/{self.test_string}/sorted_times.txt", "w") as file:
                    for timex in task_times:
                        file.write(f"{timex}\n")

                for j in range(0, len(task_times), 2):
                    if j + 1 <= len(task_times):
                        switch_times.append(
                            task_times[j+1] - task_times[j])
                        switch_times_global.append(
                            task_times[j+1] - task_times[j])

                with open(f"./results/{self.system_string}/semaphore/{self.test_string}/semaphore_times.txt", "w") as file:
                    for timex in switch_times:
                        file.write(f"{timex}\n")

            mean_switch_time = statistics.mean(
                switch_times_global) if switch_times_global else 0
            stdev_switch_time = statistics.stdev(
                switch_times_global) if len(switch_times_global) > 1 else 0
            max_switch_time = max(
                switch_times_global) if switch_times_global else 0
            min_switch_time = min(
                switch_times_global) if switch_times_global else 0

            summary_file.write(
                f"\t\t- Średni czas oczekiwania na semafor: {mean_switch_time}\n")
            summary_file.write(
                f"\t\t- Odchylenie standardowe: {stdev_switch_time}\n")
            summary_file.write(
                f"\t\t- Maksymalny czas: {max_switch_time}\n")
            summary_file.write(
                f"\t\t- Minimalny czas: {min_switch_time}\n")

            switch_times_global = []

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

    def change_radio_button(self):
        self.system_string = self.radio_options.get(
            self.radio_var.get(), "Unknown")
        if self.radio_var.get() == 3:
            TASK_SWITCH_TICKS = 59
            TASK_SWITCH_TIME = float(
                "{:.9f}".format(TASK_SWITCH_TICKS / 72.000))
            MEASSURE_TICKS = 46
            MEASSURE_TIME = float("{:.9f}".format(MEASSURE_TICKS / 72.000))
        else:
            TASK_SWITCH_TICKS = 14
            TASK_SWITCH_TIME = float(
                "{:.9f}".format(TASK_SWITCH_TICKS / 72.000))
            MEASSURE_TICKS = 6
            MEASSURE_TIME = float("{:.9f}".format(MEASSURE_TICKS / 72.000))

    def read_args(self, input_text):
        if input_text:
            args = [int(arg) for arg in input_text.split(';') if arg.strip()]
            arg_count = len(args)
        else:
            # Set default values if input is empty
            args = [10]  # Default value
            arg_count = 1
        return args, arg_count

    def delete_old_measurements(self, dir):
        folders = [f"{dir}/raw", f"{dir}/us"]

        for folder in folders:
            os.makedirs(folder, exist_ok=True)
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print('Failed to delete %s. Reason: %s' % (file_path, e))

    def task_force_switch_command(self):
        self.blocked_state = True
        self.change_state(True, False)
        fpath = f"./results/{self.system_string}/task_force_switch/{self.test_string}"
        self.delete_old_measurements(fpath)

        error = 0
        buffor_tx = bytearray(9)
        command = 0x00
        arg_count = 0
        args, arg_count = self.read_args(self.task_force_switch_input.get())
        result = code_command_frame(buffor_tx, command, arg_count, args)
        print([hex(byte) for byte in buffor_tx])

        if result == 0:
            self.ser.flush()
            self.ser.write(buffor_tx)
            # time.sleep(10)
            response = self.ser.read(406 * args[0])
            print(len(response))
            if len(response) == 406 * args[0]:
                scores = [response[i * 406: (i + 1) * 406]
                          for i in range(args[0])]
                for i in range(args[0]):
                    print([hex(byte) for byte in scores[i]])
                    with open(f"{fpath}/us/{i}.txt", "w") as file:
                        with open(f"{fpath}/raw/{i}.txt", "w") as file_raw:
                            command_anw = 0
                            arg_count_anw = 0
                            args_anw = []
                            result, command_anw, arg_count_anw = decode_command_frame(
                                scores[i], args_anw)
                            if result == 0 and command_anw == command:
                                for j in range(0, arg_count_anw, 4):
                                    value_bytes = args_anw[j:j+4]
                                    uint_value = struct.unpack(
                                        "<I", bytes(value_bytes))[0]
                                    file_raw.write(f"{uint_value}\n")
                                    # Convert uint32_t to float by dividing by 72
                                    float_value = uint_value / 72.0
                                    file.write(f"{float_value:.9f}\n")
                                self.task_force_switch_label.configure(
                                    text="OK")
                            else:
                                self.change_state(False, True)
                                self.task_force_switch_label.configure(
                                    text="Err")
                                error = -1
            else:
                print("Board didn't send full responce to frame. Maybe resend?")
                self.change_state(False, True)
                self.task_force_switch_label.configure(text="Err")
                error = -1

        self.blocked_state = False
        self.change_state(True, True)
        return error

    def task_force_switch_analyze(self):
        args, arg_count = self.read_args(self.task_force_switch_input.get())
        num_tasks = args[0]

        task_times = []
        system_intervals = []
        # System analyzed
        for i in range(num_tasks):
            filename = f"./res/task_force_switch/{i}.txt"
            # Read task times from file
            with open(filename, "r") as file:
                for line in file:
                    task_times.append(float(line.strip()))

        # Find system intervals
        task_times.sort()
        prev_time = 0
        for time in task_times:
            if time - prev_time > TASK_SWITCH_TIME:
                system_intervals.append(
                    (prev_time + TASK_SWITCH_TIME, time - prev_time-TASK_SWITCH_TIME))
            prev_time = time

        # Adjust figure size to reduce stretching on y-axis
        # You can adjust the figure width as needed
        plt.figure(figsize=(num_tasks, num_tasks))

        # Loop through each file
        for i in range(num_tasks):
            filename = f"./res/task_force_switch/{i}.txt"
            task_times = []
            # color = random.choice(COLORS)

            # Read task times from file
            with open(filename, "r") as file:
                for line in file:
                    task_times.append(float(line.strip()))

            # Plot each task as a straight line segment
            for time_idx, task_time in enumerate(task_times):
                plt.plot([task_time, task_time + TASK_SWITCH_TIME],
                         [i, i], color='blue')

        for interval in system_intervals:
            plt.plot([interval[0], interval[0] + interval[1]],
                     [num_tasks, num_tasks], color='red', label='SYSTEM')

        # Set task labels on the y-axis
        plt.yticks(range(num_tasks), [f'Task {i}' for i in range(num_tasks)])

        # Set labels and show plot
        plt.xlabel('Time')
        plt.ylabel('Task')
        plt.title('Task Time Visualization')
        plt.grid(True)  # Add grid for better readability
        plt.tight_layout()  # Adjust layout to prevent overlapping labels
        plt.show()

        with open("times.txt", "w") as time_file:
            for interval in system_intervals[num_tasks+1:-(num_tasks+1)]:
                time_file.write(f"{interval[1]:.3f}\n")

    def task_force_switch_priority_command(self):
        error = 0
        self.blocked_state = True
        self.change_state(True, False)
        fpath = f"./results/{self.system_string}/task_force_switch_priority/{self.test_string}"
        self.delete_old_measurements(fpath)

        buffor_tx = bytearray(9)
        command = 0x01
        arg_count = 0
        args, arg_count = self.read_args(
            self.task_force_switch_priority_input.get())
        result = code_command_frame(buffor_tx, command, arg_count, args)
        print([hex(byte) for byte in buffor_tx])

        if result == 0:
            self.ser.flush()
            self.ser.write(buffor_tx)
            # time.sleep(10)
            thread_count = (args[0]+args[1])
            response = self.ser.read(406 * thread_count)
            print(len(response))
            if len(response) == 406 * thread_count:
                scores = [response[i * 406: (i + 1) * 406]
                          for i in range(thread_count)]
                for i in range(thread_count):
                    print([hex(byte) for byte in scores[i]])
                    with open(f"{fpath}/us/{i}.txt", "w") as file:
                        with open(f"{fpath}/raw/{i}.txt", "w") as file_raw:
                            command_anw = 0
                            arg_count_anw = 0
                            args_anw = []
                            result, command_anw, arg_count_anw = decode_command_frame(
                                scores[i], args_anw)
                            if result == 0 and command_anw == command:
                                for j in range(0, arg_count_anw, 4):
                                    value_bytes = args_anw[j:j+4]
                                    uint_value = struct.unpack(
                                        "<I", bytes(value_bytes))[0]
                                    file_raw.write(f"{uint_value}\n")
                                    # Convert uint32_t to float by dividing by 72
                                    float_value = uint_value / 72.0
                                    file.write(f"{float_value:.9f}\n")
                                self.task_force_switch_priority_label.configure(
                                    text="OK")
                            else:
                                self.change_state(False, True)
                                self.task_force_switch_priority_label.configure(
                                    text="Err")
                                error = -1
            else:
                print("Board didn't send full responce to frame. Maybe resend?")
                self.change_state(False, True)
                self.task_force_switch_priority_label.configure(text="Err")
                error = -1

        self.blocked_state = False
        self.change_state(True, True)
        return error

    def task_force_switch_priority_analyze(self):
        args, arg_count = self.read_args(
            self.task_force_switch_priority_input.get())
        num_tasks = args[0] + args[1]

        task_times = []
        system_intervals = []
        # System analyzed
        for i in range(num_tasks):
            filename = f"./res/task_force_switch_priority/{i}.txt"
            # Read task times from file
            with open(filename, "r") as file:
                for line in file:
                    task_times.append(float(line.strip()))

        # Find system intervals
        task_times.sort()
        prev_time = 0
        for time in task_times:
            if time - prev_time > TASK_SWITCH_TIME:
                system_intervals.append(
                    (prev_time + TASK_SWITCH_TIME, time - prev_time-TASK_SWITCH_TIME))
            prev_time = time

        # Adjust figure size to reduce stretching on y-axis
        # You can adjust the figure width as needed
        plt.figure(figsize=(num_tasks, num_tasks))

        # Loop through each file
        for i in range(num_tasks):
            filename = f"./res/task_force_switch_priority/{i}.txt"
            task_times = []
            if i < args[0]:
                color = 'blue'
            else:
                color = 'green'
            # color = random.choice(COLORS)

            # Read task times from file
            with open(filename, "r") as file:
                for line in file:
                    task_times.append(float(line.strip()))

            # Plot each task as a straight line segment
            for time_idx, task_time in enumerate(task_times):
                plt.plot([task_time, task_time + TASK_SWITCH_TIME],
                         [i, i], color=color)

        for interval in system_intervals:
            plt.plot([interval[0], interval[0] + interval[1]],
                     [num_tasks, num_tasks], color='red', label='SYSTEM')

        # Set task labels on the y-axis
        plt.yticks(range(num_tasks), [f'Task {i}' for i in range(num_tasks)])

        # Set labels and show plot
        plt.xlabel('Time')
        plt.ylabel('Task')
        plt.title('Task Time Visualization')
        plt.grid(True)  # Add grid for better readability
        plt.tight_layout()  # Adjust layout to prevent overlapping labels
        plt.show()

        with open("times.txt", "w") as time_file:
            for interval in system_intervals[num_tasks+1:-(num_tasks+1)]:
                time_file.write(f"{interval[1]:.3f}\n")

    def task_switch_command(self):
        error = 0
        self.blocked_state = True
        self.change_state(True, False)
        fpath = f"./results/{self.system_string}/task_switch/{self.test_string}"
        self.delete_old_measurements(fpath)

        buffor_tx = bytearray(9)
        command = 0x02
        arg_count = 0
        args, arg_count = self.read_args(self.task_switch_input.get())
        result = code_command_frame(buffor_tx, command, arg_count, args)
        print([hex(byte) for byte in buffor_tx])

        if result == 0:
            self.ser.flush()
            self.ser.write(buffor_tx)
            # time.sleep(10)
            response = self.ser.read(406 * args[0])
            print(len(response))
            if len(response) == 406 * args[0]:
                scores = [response[i * 406: (i + 1) * 406]
                          for i in range(args[0])]
                for i in range(args[0]):
                    print([hex(byte) for byte in scores[i]])
                    with open(f"{fpath}/us/{i}.txt", "w") as file:
                        with open(f"{fpath}/raw/{i}.txt", "w") as file_raw:
                            command_anw = 0
                            arg_count_anw = 0
                            args_anw = []
                            result, command_anw, arg_count_anw = decode_command_frame(
                                scores[i], args_anw)
                            if result == 0 and command_anw == command:
                                for j in range(0, arg_count_anw, 4):
                                    value_bytes = args_anw[j:j+4]
                                    uint_value = struct.unpack(
                                        "<I", bytes(value_bytes))[0]
                                    file_raw.write(f"{uint_value}\n")
                                    # Convert uint32_t to float by dividing by 72
                                    float_value = uint_value / 72.0
                                    file.write(f"{float_value:.9f}\n")
                                self.task_switch_label.configure(text="OK")
                            else:
                                self.change_state(False, True)
                                self.task_switch_label.configure(text="Err")
                                error = -1
            else:
                print("Board didn't send full responce to frame. Maybe resend?")
                self.change_state(False, True)
                self.task_switch_label.configure(text="Err")
                error = -1

        self.blocked_state = False
        self.change_state(True, True)
        return error

    def task_switch_analyze(self):
        args, arg_count = self.read_args(self.task_switch_input.get())
        num_tasks = args[0]

        # task_times = []
        # system_intervals = []
        # # System analyzed
        # for i in range(num_tasks):
        #     filename = f"./res/task_switch/{i}.txt"
        #     # Read task times from file
        #     with open(filename, "r") as file:
        #         for line in file:
        #             task_times.append(float(line.strip()))

        # # Find system intervals
        # task_times.sort()
        # prev_time = 0
        # for time in task_times:
        #     if time - prev_time > TASK_SWITCH_TIME:
        #         system_intervals.append((prev_time + TASK_SWITCH_TIME, time - prev_time-TASK_SWITCH_TIME))
        #     prev_time = time

        # Adjust figure size to reduce stretching on y-axis
        # You can adjust the figure width as needed
        plt.figure(figsize=(num_tasks, num_tasks))

        # Loop through each file
        for i in range(num_tasks):
            filename = f"./res/task_switch/{i}.txt"
            task_times = []
            # color = random.choice(COLORS)

            # Read task times from file
            with open(filename, "r") as file:
                lines = file.readlines()
                # Iterate over the lines two at a time
                for j in range(0, len(lines), 2):
                    # Ensure there are at least two lines to read
                    if j + 1 < len(lines):
                        # Append the tuple of two float values to the task_times list
                        task_times.append(
                            (float(lines[j].strip()), float(lines[j + 1].strip())))

            # Plot each task as a straight line segment
            for time_start, time_end in task_times:
                plt.plot([time_start, time_end], [i, i], color='blue')

        # for interval in system_intervals:
        #     plt.plot([interval[0], interval[0] + interval[1]], [num_tasks, num_tasks], color='red', label='SYSTEM')

        # Set task labels on the y-axis
        plt.yticks(range(num_tasks), [f'Task {i}' for i in range(num_tasks)])

        # Set labels and show plot
        plt.xlabel('Time')
        plt.ylabel('Task')
        plt.title('Task Time Visualization')
        plt.grid(True)  # Add grid for better readability
        plt.tight_layout()  # Adjust layout to prevent overlapping labels
        plt.show()

        # with open("times.txt", "w") as time_file:
        #     for interval in system_intervals[num_tasks+1:-(num_tasks+1)]:
        #         time_file.write(f"{interval[1]:.3f}\n")

    def task_switch_priority_command(self):
        error = 0
        self.blocked_state = True
        self.change_state(True, False)
        fpath = f"./results/{self.system_string}/task_switch_priority/{self.test_string}"
        self.delete_old_measurements(fpath)

        buffor_tx = bytearray(9)
        command = 0x03
        arg_count = 0
        args, arg_count = self.read_args(self.task_switch_priority_input.get())
        result = code_command_frame(buffor_tx, command, arg_count, args)
        print([hex(byte) for byte in buffor_tx])

        if result == 0:
            self.ser.flush()
            self.ser.write(buffor_tx)
            # time.sleep(10)
            thread_count = (args[0]+args[1])
            response = self.ser.read(406 * thread_count)
            print(len(response))
            if len(response) == 406 * thread_count:
                scores = [response[i * 406: (i + 1) * 406]
                          for i in range(thread_count)]
                for i in range(thread_count):
                    print([hex(byte) for byte in scores[i]])
                    with open(f"{fpath}/us/{i}.txt", "w") as file:
                        with open(f"{fpath}/raw/{i}.txt", "w") as file_raw:
                            command_anw = 0
                            arg_count_anw = 0
                            args_anw = []
                            result, command_anw, arg_count_anw = decode_command_frame(
                                scores[i], args_anw)
                            if result == 0 and command_anw == command:
                                for j in range(0, arg_count_anw, 4):
                                    value_bytes = args_anw[j:j+4]
                                    uint_value = struct.unpack(
                                        "<I", bytes(value_bytes))[0]
                                    file_raw.write(f"{uint_value}\n")
                                    # Convert uint32_t to float by dividing by 72
                                    float_value = uint_value / 72.0
                                    file.write(f"{float_value:.9f}\n")
                                self.task_switch_priority_label.configure(
                                    text="OK")
                            else:
                                self.change_state(False, True)
                                self.task_switch_priority_label.configure(
                                    text="Err")
                                error = -1
            else:
                print("Board didn't send full responce to frame. Maybe resend?")
                self.change_state(False, True)
                self.task_switch_priority_label.configure(text="Err")
                error = -1

        self.blocked_state = False
        self.change_state(True, True)
        return error

    def task_switch_priority_analyze(self):
        args, arg_count = self.read_args(self.task_switch_priority_input.get())
        num_tasks = args[0] + args[1]

        plt.figure(figsize=(num_tasks, num_tasks))

        fpath = f"./results/{self.system_string}/task_switch_priority/{self.test_string}"
        # Loop through each file
        for i in range(num_tasks):
            filename = f"{fpath}/raw/{i}.txt"
            task_times = []
            # color = random.choice(COLORS)

            # Read task times from file
            with open(filename, "r") as file:
                lines = file.readlines()
                # Iterate over the lines two at a time
                for j in range(len(lines)):
                    task_times.append(int(lines[j].strip()))

            # Plot each task as a straight line segment
            for time_slot in task_times:
                plt.plot([time_slot-1000, time_slot+1000],
                         [i, i], color='blue')

        # Set task labels on the y-axis
        plt.yticks(range(num_tasks), [f'Task {i}' for i in range(num_tasks)])

        # Set labels and show plot
        plt.xlabel('Time')
        plt.ylabel('Task')
        plt.title('Task Time Visualization')
        plt.grid(True)  # Add grid for better readability
        plt.tight_layout()  # Adjust layout to prevent overlapping labels
        plt.show()

    def semaphore_command(self):
        error = 0
        self.blocked_state = True
        self.change_state(True, False)
        fpath = f"./results/{self.system_string}/semaphore/{self.test_string}"
        self.delete_old_measurements(fpath)

        buffor_tx = bytearray(9)
        command = 0x04
        arg_count = 0
        args, arg_count = self.read_args(self.semaphore_input.get())
        result = code_command_frame(buffor_tx, command, arg_count, args)
        print([hex(byte) for byte in buffor_tx])

        if result == 0:
            self.ser.flush()
            self.ser.write(buffor_tx)
            # time.sleep(10)
            response = self.ser.read(406 * args[0])
            print(len(response))
            if len(response) == 406 * args[0]:
                scores = [response[i * 406: (i + 1) * 406]
                          for i in range(args[0])]
                for i in range(args[0]):
                    print([hex(byte) for byte in scores[i]])
                    with open(f"{fpath}/us/{i}.txt", "w") as file:
                        with open(f"{fpath}/raw/{i}.txt", "w") as file_raw:
                            command_anw = 0
                            arg_count_anw = 0
                            args_anw = []
                            result, command_anw, arg_count_anw = decode_command_frame(
                                scores[i], args_anw)
                            if result == 0 and command_anw == command:
                                for j in range(0, arg_count_anw, 4):
                                    value_bytes = args_anw[j:j+4]
                                    uint_value = struct.unpack(
                                        "<I", bytes(value_bytes))[0]
                                    file_raw.write(f"{uint_value}\n")
                                    # Convert uint32_t to float by dividing by 72
                                    float_value = uint_value / 72.0
                                    file.write(f"{float_value:.9f}\n")
                                self.semaphore_label.configure(text="OK")
                            else:
                                self.change_state(False, True)
                                self.semaphore_label.configure(text="Err")
                                error = -1
            else:
                print("Board didn't send full responce to frame. Maybe resend?")
                self.change_state(False, True)
                self.semaphore_label.configure(text="Err")
                error = -1

        self.blocked_state = False
        self.change_state(True, True)
        return error

    def semaphore_analyze(self):
        args, arg_count = self.read_args(self.semaphore_input.get())
        num_tasks = args[0]

        # system_intervals = []
        # # System analyzed
        # for i in range(num_tasks):
        #     filename = f"./res/task_switch/{i}.txt"
        #     # Read task times from file
        #     with open(filename, "r") as file:
        #         for line in file:
        #             task_times.append(float(line.strip()))

        # # Find system intervals
        # task_times.sort()
        # prev_time = 0
        # for time in task_times:
        #     if time - prev_time > TASK_SWITCH_TIME:
        #         system_intervals.append((prev_time + TASK_SWITCH_TIME, time - prev_time-TASK_SWITCH_TIME))
        #     prev_time = time

        # Adjust figure size to reduce stretching on y-axis
        # You can adjust the figure width as needed
        plt.figure(figsize=(num_tasks, num_tasks))

        # Loop through each file
        for i in range(num_tasks):
            filename = f"./res/semaphore/{i}.txt"
            # color = random.choice(COLORS)
            task_times = []
            # Read task times from file
            with open(filename, "r") as file:
                lines = file.readlines()
                # Iterate over the lines two at a time
                for j in range(len(lines)):
                    # Append the tuple of two float values to the task_times list
                    task_times.append(float(lines[j].strip()))

            # Plot each task as a straight line segment
            for point in task_times:
                plt.plot([point, point + MEASSURE_TIME], [i, i], color='blue')

        # for interval in system_intervals:
        #     plt.plot([interval[0], interval[0] + interval[1]], [num_tasks, num_tasks], color='red', label='SYSTEM')

        # Set task labels on the y-axis
        plt.yticks(range(num_tasks), [f'Task {i}' for i in range(num_tasks)])

        # Set labels and show plot
        plt.xlabel('Time')
        plt.ylabel('Task')
        plt.title('Task Time Visualization')
        plt.grid(True)  # Add grid for better readability
        plt.tight_layout()  # Adjust layout to prevent overlapping labels
        plt.show()

        # with open("times.txt", "w") as time_file:
        #     for interval in system_intervals[num_tasks+1:-(num_tasks+1)]:
        #         time_file.write(f"{interval[1]:.3f}\n")

    def queue_command(self):
        error = 0
        self.blocked_state = True
        self.change_state(True, False)
        fpath = f"./results/{self.system_string}/queue/{self.test_string}"
        self.delete_old_measurements(fpath)

        buffor_tx = bytearray(9)
        command = 0x05
        arg_count = 0
        args, arg_count = self.read_args(self.queue_input.get())
        result = code_command_frame(buffor_tx, command, arg_count, args)
        print([hex(byte) for byte in buffor_tx])

        if result == 0:
            self.ser.flush()
            self.ser.write(buffor_tx)
            # time.sleep(10)
            response = self.ser.read(406 * 2)
            print(len(response))
            if len(response) == 406 * 2:
                scores = [response[i * 406: (i + 1) * 406] for i in range(2)]
                for i in range(2):
                    print([hex(byte) for byte in scores[i]])
                    with open(f"{fpath}/us/{i}.txt", "w") as file:
                        with open(f"{fpath}raw/{i}.txt", "w") as file_raw:
                            command_anw = 0
                            arg_count_anw = 0
                            args_anw = []
                            result, command_anw, arg_count_anw = decode_command_frame(
                                scores[i], args_anw)
                            if result == 0 and command_anw == command:
                                for j in range(0, arg_count_anw, 4):
                                    value_bytes = args_anw[j:j+4]
                                    uint_value = struct.unpack(
                                        "<I", bytes(value_bytes))[0]
                                    file_raw.write(f"{uint_value}\n")
                                    # Convert uint32_t to float by dividing by 72
                                    float_value = uint_value / 72.0
                                    file.write(f"{float_value:.9f}\n")
                                self.queue_label.configure(text="OK")
                            else:
                                self.change_state(False, True)
                                self.queue_label.configure(text="Err")
                                error = -1
            else:
                print("Board didn't send full responce to frame. Maybe resend?")
                self.change_state(False, True)
                self.queue_label.configure(text="Err")
                error = -1

        self.blocked_state = False
        self.change_state(True, True)
        return error

    def queue_analyze(self):
        pass


if __name__ == "__main__":
    directories = [
        './results/Zephyr',
        './results/FreeRTOS',
        './results/EmbOS']

# Create each directory if it doesn't exist
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    app = App(serial_port)
    app.mainloop()
