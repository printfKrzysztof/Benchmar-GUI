import argparse
import matplotlib.pyplot as plt

# Increase font sizes and figure size for better readability
plt.rcParams.update({
    'font.size': 14,          # General font size
    'axes.titlesize': 18,     # Title font size
    'axes.labelsize': 16,     # X and Y axis label font size
    'xtick.labelsize': 14,    # X tick label font size
    'ytick.labelsize': 14,    # Y tick label font size
    'legend.fontsize': 14,    # Legend font size
    'figure.figsize': (10, 8)  # Default figure size for better visibility
})

parser = argparse.ArgumentParser(description='Program do benchmarkowania RTOS')
parser.add_argument(
    '--test', help='Test to analyze (task-switch[-priority] / task-force-switch / semaphore / queue)')
parser.add_argument(
    '--system', help='System to get data from (Zephyr / FreeRTOS/ EmbOS)')
args = parser.parse_args()

# Set a common line width for all plots
line_width = 3.0

match args.test:
    case "task-switch":
        num_tasks = 5
        plt.figure(figsize=(12, 8))

        # Loop through each file
        for i in range(num_tasks):
            filename = f"./results/{args.system}/task_switch/5_5_0/us/{i}.txt"
            task_times = []
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

            # Plot each task as a straight line segment with thicker lines
            for time_start, time_end in task_times:
                plt.plot([time_start, time_end], [i, i],
                         color='blue', linewidth=line_width)

        # Set task labels on the y-axis
        plt.yticks(range(num_tasks), [f'Task {i}' for i in range(num_tasks)])

        # Set labels and show plot
        plt.xlabel('Time')
        plt.ylabel('Task')
        plt.title('Task Time Visualization')
        plt.grid(True)  # Add grid for better readability
        plt.tight_layout()  # Adjust layout to prevent overlapping labels
        plt.show()

    case "task-force-switch":
        num_tasks = 5
        plt.figure(figsize=(12, 8))

        # Loop through each file
        for i in range(num_tasks):
            filename = f"./results/{args.system}/task_force_switch/5_50_1/us/{i}.txt"
            task_times = []
            # Read task times from file
            with open(filename, "r") as file:
                lines = file.readlines()
                # Iterate over the lines
                for j in range(0, len(lines)):
                    task_times.append((float(lines[j].strip())))

            # Plot each task as a straight line segment with thicker lines
            if args.system == "Zephyr":
                time_to_add = 5
            else:
                time_to_add = 1
            for timex in task_times:
                plt.plot([timex, timex + time_to_add], [i, i],
                         color='blue', linewidth=line_width)

        # Set task labels on the y-axis
        plt.yticks(range(num_tasks), [f'Task {i}' for i in range(num_tasks)])

        # Set labels and show plot
        plt.xlabel('Time')
        plt.ylabel('Task')
        plt.title('Task Time Visualization')
        plt.grid(True)  # Add grid for better readability
        plt.tight_layout()  # Adjust layout to prevent overlapping labels
        plt.show()

    case "semaphore":
        num_tasks = 5
        plt.figure(figsize=(12, 8))

        # Loop through each file
        for i in range(num_tasks):
            filename = f"./results/{args.system}/semaphore/5_10_1/us/{i}.txt"
            task_times = []
            # Read task times from file
            with open(filename, "r") as file:
                lines = file.readlines()
                # Iterate over the lines
                for j in range(0, len(lines)):
                    task_times.append((float(lines[j].strip())))

            # Plot each task as a straight line segment with thicker lines
            if args.system == "Zephyr":
                time_to_add = 8
            else:
                time_to_add = 3
            for timex in task_times:
                plt.plot([timex, timex + time_to_add], [i, i],
                         color='blue', linewidth=line_width)

        # Set task labels on the y-axis
        plt.yticks(range(num_tasks), [f'Task {i}' for i in range(num_tasks)])

        # Set labels and show plot
        plt.xlabel('Time')
        plt.ylabel('Task')
        plt.title('Task Time Visualization')
        plt.grid(True)  # Add grid for better readability
        plt.tight_layout()  # Adjust layout to prevent overlapping labels
        plt.show()

    case "queue":
        num_tasks = 2
        plt.figure(figsize=(10, 6))

        # Loop through each file
        for i in range(num_tasks):
            filename = f"./results/{args.system}/queue/50_0/us/{i}.txt"
            task_times = []
            # Read task times from file
            with open(filename, "r") as file:
                lines = file.readlines()
                # Iterate over the lines
                for j in range(0, len(lines)):
                    task_times.append((float(lines[j].strip())))

            # Plot each task as a straight line segment with thicker lines
            if args.system == "Zephyr":
                time_to_add = 8
            else:
                time_to_add = 3
            for timex in task_times:
                plt.plot([timex, timex + time_to_add], [i, i],
                         color='blue', linewidth=line_width)

        # Set task labels on the y-axis
        plt.yticks(range(num_tasks), ["Receiver", "Transmitter"])

        # Set labels and show plot
        plt.xlabel('Time')
        plt.ylabel('Task')
        plt.title('Task Time Visualization')
        plt.grid(True)  # Add grid for better readability
        plt.tight_layout()  # Adjust layout to prevent overlapping labels
        plt.show()
