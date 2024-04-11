import customtkinter as ctk
import serial
import threading

class SerialThread(threading.Thread):
    def __init__(self, serial_port, baud_rate):
        super().__init__()
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.stop_event = threading.Event()

    def run(self):
        try:
            with serial.Serial(self.serial_port, self.baud_rate, timeout=1) as ser:
                while not self.stop_event.is_set():
                    ser.write(b'Frame')  # Send frame to device
                    response = ser.readline().strip()  # Read response
                    if response:
                        app.change_diode_color('green')  # Change diode color to green if response is received
        except serial.SerialException:
            print("Serial port error")
        finally:
            self.stop_event.set()

    def stop(self):
        self.stop_event.set()


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Communication App")

        self.serial_thread = None
        self.blocked_state = False
        self.create_widgets()

    def create_widgets(self):
        self.frame = ctk.CTkFrame(self.root)
        self.frame.pack(padx=20, pady=20)

        self.diode_label = ctk.CTkLabel(self.frame, width=10, height=5)
        self.diode_label.grid(row=0, column=0, columnspan=4, pady=10)

        self.start_button = ctk.CTkButton(self.frame, text="Start", command=self.start_serial)
        self.start_button.grid(row=1, column=0, padx=5)

        self.stop_button = ctk.CTkButton(self.frame, text="Stop", command=self.stop_serial)
        self.stop_button.grid(row=1, column=1, padx=5)

        self.block_checkbox = ctk.CTkCheckBox(self.frame, text="Block", command=self.toggle_block)
        self.block_checkbox.grid(row=1, column=2, padx=5)

        self.quit_button = ctk.CTkButton(self.frame, text="Quit", command=self.root.quit)
        self.quit_button.grid(row=1, column=3, padx=5)

        self.change_diode_color('red')

    def start_serial(self):
        if self.serial_thread is None or not self.serial_thread.is_alive():
            self.serial_thread = SerialThread('/dev/ttyACM0', 38400)
            self.serial_thread.start()

    def stop_serial(self):
        if self.serial_thread:
            self.serial_thread.stop()

    def toggle_block(self):
        if self.blocked_state:
            self.blocked_state = False
            self.start_button._state = 'normal'
            self.stop_button._state = 'normal'
            self.quit_button._state = 'normal'
        else:
            self.blocked_state = True
            self.start_button._state = 'disabled'
            self.stop_button._state = 'disabled'
            self.quit_button._state = 'disabled'

    def change_diode_color(self, color):
        self.diode_label['background'] = color


if __name__ == "__main__":
    root = ctk.CTk()
    app = App(root)
    root.mainloop()
