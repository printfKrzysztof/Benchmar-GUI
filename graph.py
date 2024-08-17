import argparse
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='Program do benchmarkowania RTOS')
parser.add_argument(
    '--test', help='Test to analyze (task-switch[-priority] / task-force-switch / semaphore / queue)')
parser.add_argument(
    '--system', help='System to get data from (Zephyr / FreeRTOS/ EmbOS)')
args = parser.parse_args()

match args.test:
    case "task-switch":
        num_tasks = 5
        plt.figure(figsize=(num_tasks, num_tasks))

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

            # Plot each task as a straight line segment
            for time_start, time_end in task_times:
                plt.plot([time_start, time_end], [i, i], color='blue')

        # Set task labels on the y-axis
        plt.yticks(range(num_tasks), [f'Task {i}' for i in range(num_tasks)])

        # Set labels and show plot
        plt.xlabel('Time')
        plt.ylabel('Task')
        plt.title('Task Time Visualization')
        plt.grid(True)  # Add grid for better readability
        plt.tight_layout()  # Adjust layout to prevent overlapping labels
        plt.show()

    case "task-switch-priority":

        num_tasks = 10
        plt.figure(figsize=(num_tasks, num_tasks))
        # Loop through each file
        for i in range(num_tasks):
            filename = f"./results/{args.system}/task_switch_priority/5_5_6_0/us/{i}.txt"
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

            # Plot each task as a straight line segment
            for time_start, time_end in task_times:
                plt.plot([time_start, time_end], [i, i], color='blue')

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
        plt.figure(figsize=(num_tasks, num_tasks))

        # Loop through each file
        for i in range(num_tasks):
            filename = f"./results/{args.system}/task_force_switch/5_50_0/us/{i}.txt"
            task_times = []
            # Read task times from file
            with open(filename, "r") as file:
                lines = file.readlines()
                # Iterate over the lines two at a time
                for j in range(0, len(lines)):
                    task_times.append((float(lines[j].strip())))

            # Plot each task as a straight line segment
            if args.system == "Zephyr":
                time_to_add = 5
            else:
                time_to_add = 1
            for timex in task_times:
                plt.plot([timex, timex+time_to_add], [i, i], color='blue')

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
        pass
    case "queue":
        pass
