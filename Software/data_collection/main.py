import serial   # pip install pyserial, not serial
import threading
import tkinter as tk
import datetime
import numpy as np
import os
import random
import time
from time import sleep
import matplotlib
matplotlib.use('TkAgg') 
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
import matplotlib.colors as mccolor

# Constants
# TODO: probably make this in a class so we can do OOP
print("Hello World")
recordingStarted = False
recordingInitial = False
recordedData = []


def read_serial():
    print("Test")
    global recordingStarted
    global recordedData
    global recordingInitial
    try:
        with serial.Serial('/dev/cu.SLAB_USBtoUART', 9600, timeout=2) as ser:
            while ser.is_open:
                line = ser.readline() # will need to be decoded
                decoded = line.decode('utf-8')
                update_label(decoded)
                # sleep(0.0050)
                if recordingStarted:
                    if recordingInitial:
                        update_cd("Begin Recording in 3")
                        time.sleep(1)
                        update_cd("Begin Recording in 2")
                        time.sleep(1)
                        update_cd("Begin Recording in 1")
                        time.sleep(1)
                        recordingInitial = not recordingInitial
                    x = 5
                    time_begin = time.time()
                    while time.time() - time_begin < 5:
                        if not recordingStarted:
                            break
                        start_time = time.time()
                        update_cd("Relax Arm. Contract in " + str(x))
                        x-=1
                        while time.time()-start_time <1:
                            decoded = decoded[:-2]
                            time.sleep(0.01)
                            update_label(decoded)
                            if recordingStarted:
                                recordedData.append([decoded,0])
                    x = 5
                    time_begin = time.time()
                    while time.time()-time_begin < 5:
                        if not recordingStarted:
                            break
                        start_time = time.time()
                        update_cd("Contract Arm. Relax in " + str(x))
                        x-=1
                        while time.time()-start_time < 1:
                            decoded = decoded[:-2]
                            time.sleep(0.01)
                            update_label(decoded)
                            if recordingStarted:
                                recordedData.append([decoded,1])
                if not recordingStarted:
                    update_cd("Recording Stopped")

    # When you don't have esp32 connected but just work on the GUI itself
    except Exception as e:
        print("Currently at offline mode, generating random data")
        # Send fake data with random pockets of EMG
        while True:
            if recordingStarted:
                if recordingInitial:
                    update_cd("Begin Recording in 3")
                    time.sleep(1)
                    update_cd("Begin Recording in 2")
                    time.sleep(1)
                    update_cd("Begin Recording in 1")
                    time.sleep(1)
                    recordingInitial = not recordingInitial
                x = 5
                time_begin = time.time()
                while time.time()-time_begin < 5:
                    if not recordingStarted:
                        break
                    start_time = time.time()
                    update_cd("Relax Arm. Contract in " + str(x))
                    x-=1
                    while time.time()-start_time < 1:
                        decoded = random.randint(0, 100)
                        time.sleep(0.01)
                        update_label(decoded)
                        if recordingStarted:
                            recordedData.append([decoded,0])
                x = 5
                time_begin = time.time()
                while time.time()-time_begin < 5:
                    if not recordingStarted:
                        break
                    start_time = time.time()
                    update_cd("Contract Arm. Relax in " + str(x))
                    x-=1
                    while time.time()-start_time < 1:
                        decoded = random.randint(1000, 2000)
                        time.sleep(0.01)
                        update_label(decoded)
                        if recordingStarted:
                            recordedData.append([decoded,1])
            if not recordingStarted:
                update_cd("Recording Stopped")


def update_label(data):
    root.after(0, lambda: lbl.config(text=str(data)))

def update_cd(data):
    root.after(0, lambda: cd.config(text=str(data)))

def toggleRecord():
    global recordingStarted
    global recordedData
    global recordingInitial
    if (not recordingStarted): 
        rec_btn.config(text="Stop")
        recordingInitial = True
        print("RECORDING [STARTED]\n")
    else: 
        rec_btn.config(text="Start")
        print("RECORDING [STOPPED]\n")
        saveData = np.array(recordedData, dtype=np.int16)
        print(saveData)
        print(saveData.shape)
        if not os.path.exists("saves/"):
            os.makedirs("saves")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        np.savetxt(f"saves/{timestamp}_Trail_0.csv", saveData, fmt="%d", delimiter ='; ')
        recordedData = []
    recordingStarted = not recordingStarted

root = tk.Tk()
root.geometry("600x1000")
root.title("Live Serial Data")

fig, ax = plt.subplots()
#graph row =4
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().grid(row=4, column=0, columnspan=3, pady=20)

def update_plot(data):
    ax.clear()
    ax.plot(data, color='blue', label = 'Data Values')
    recent_data = data[-100:]
    avg = np.mean(recent_data)
    ax.scatter(len(data)-1, avg, color='red', label='Point Average')
    ax.annotate(f'{avg:.2f}', xy=(len(data)-1, avg), xytext=(len(data)-1, avg+0.5),
                arrowprops=dict(facecolor='red', shrink=0.005),
                bbox=dict(boxstyle="round,pad=0.3", edgecolor='red', facecolor='white'))
    ax.legend(loc='upper right')
    canvas.draw()

def animate(i):
    if recordedData and recordingStarted:
        update_plot([row[0] for row in recordedData])

def close():
    print("closing")
    root.quit()
    root.destroy()


ani = animation.FuncAnimation(fig, animate, interval=1000)

lbl = tk.Label(root, text="Waiting for data...", font=("Helvetica", 16))
lbl.grid(row=0, column=0, columnspan=3, pady=20)

cd = tk.Label(root, text="Recording stopped", font=("Helvetica", 16))
cd.grid(row=1, column=0, columnspan=3, pady=20)

delayTime = tk.IntVar()
delayTimeEntry = tk.Entry(root, textvariable = delayTime, font=("Helvetica", 16))
delayTimeEntry.grid(row=2, column=1, padx=20, pady=10)

rec_btn = tk.Button(root, text = 'Start' , command = toggleRecord)
rec_btn.grid(row=3, column=1, padx=20, pady=10)

delayTimeEntry.grid(row=2,column=1)
rec_btn.grid(row=3,column=1)

close_btn = tk.Button(root, text = 'Close Program', command = close)
close_btn.grid(row=11, column=1, padx=50, pady=10)

# Make sure everything is centered in the window
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)

# =============================================================================
sleep(1)
thread = threading.Thread(target=read_serial).start()
root.mainloop()
