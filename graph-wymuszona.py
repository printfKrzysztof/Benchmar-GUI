import numpy as np
import matplotlib.pyplot as plt

# Data for the test results in microseconds
systems_tests = [
    "FreeRTOS - 5x50", "FreeRTOS - 10x50", "FreeRTOS - 20x50",  
    "EmbOS - 5x50", "EmbOS - 10x50", "EmbOS - 20x50",
    "Zephyr - 5x50", "Zephyr - 10x50", "Zephyr - 20x50"
]

average_times = [
    2.82, 2.83, 2.83,  # FreeRTOS
    6.77, 7.55, 9.14,  # EmbOS
    44.29, 48.31, 52.47 # Zephyr
]

std_dev = [
    0.27, 0.35, 0.39,  # FreeRTOS
    0.25, 0.31, 0.38,  # EmbOS
    0.46, 2.67, 1.16   # Zephyr
]

min_values = [
    2.69, 2.71, 2.71,  # FreeRTOS
    6.74, 7.51, 9.09,  # EmbOS
    43.77, 45.63, 51.09 # Zephyr
]

max_values = [
    7.43, 8.80, 8.94,  # FreeRTOS
    9.57, 10.34, 11.91, # EmbOS
    44.74, 51.03, 54.29 # Zephyr
]

# X-axis locations
x = np.arange(len(systems_tests))

# Create the figure and axis, adjusting for A4 paper proportions
fig, ax = plt.subplots(figsize=(11.7, 8.3))  # A4 proportions (11.7x8.3)

# Plotting the min, max, average, and standard deviation
for i in range(len(systems_tests)):
    # Plot the range line for min to max with thicker line
    ax.plot([x[i], x[i]], [min_values[i], max_values[i]], color='grey', lw=2, label='Min-Max' if i == 0 else "_nolegend_")
    
    # Plot the average point with larger marker
    ax.scatter(x[i], average_times[i], color='blue', zorder=3, s=50, label='Średnia' if i == 0 else "_nolegend_")
    
    # Plot standard deviation as thicker error bars
    ax.errorbar(x[i], average_times[i], yerr=std_dev[i], fmt='o', color='orange', capsize=10, lw=2, label='Odch. stand.' if i == 0 else "_nolegend_")
    
    # Plot min and max as larger individual points
    ax.scatter(x[i], min_values[i], color='red', zorder=3, s=30, label='Min' if i == 0 else "_nolegend_")
    ax.scatter(x[i], max_values[i], color='green', zorder=3, s=30, label='Max' if i == 0 else "_nolegend_")

# Add labels and title with larger font sizes
ax.set_xticks(x)
ax.set_xticklabels(systems_tests, rotation=45, ha="right", fontsize=12)
ax.set_ylabel('Czas (mikro-sekunda)', fontsize=14)
ax.set_title('Wyniki testów wymuszonej zmiany wątków', fontsize=16)

# Adjust x-axis limits and y-axis limits for better visualization
ax.set_xlim(-0.5, len(systems_tests) - 0.5)  # Limit x-axis to keep data centered
ax.set_ylim(0, 60)  # Y-axis to accommodate all values

# Add more y-axis ticks and bold grid
ax.yaxis.set_major_locator(plt.MultipleLocator(5))  # Set y-axis to have ticks every 5 units
ax.grid(True, which='both', axis='y', linestyle='--', lw=1, color='gray')  # Bolder vertical grid lines

# Make y-axis tick labels larger for readability
ax.tick_params(axis='y', labelsize=12)  # Increase the size of the y-axis tick labels

# Show legend with larger font
ax.legend(loc='upper left', fontsize='large')

# Adjust layout to fit well on A4 size
plt.tight_layout()

# Show the plot
plt.show()
