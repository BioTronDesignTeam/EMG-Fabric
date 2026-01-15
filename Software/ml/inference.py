import time
import scipy.signal as signal
from pathlib import Path
import numpy as np
import serial
import struct
from collections import deque

class EMGBuffer:
    def __init__(self, window_size=100):
        self.window_size = window_size
        self.buffer = deque(maxlen=window_size)
    
    def add(self, value):
        self.buffer.append(value)
    
    def get_data(self):
        return np.array(list(self.buffer))
    
    def is_full(self):
        return len(self.buffer) == self.window_size

def connect_serial(port='/dev/ttyUSB0', baudrate=115200):
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"Connected to {port} at {baudrate} baud")
        return ser
    except serial.SerialException as e:
        print(f"Error connecting to serial port: {e}")
        return None

def read_emg_packet(ser):
    try:
        if ser.in_waiting > 0:
            # Read raw bytes
            data = ser.read(ser.in_waiting)
            values = list(data)
        
            if len(values) > 0:
                return np.mean(values)
            
        return None
    except Exception as e:
        print(f"Error reading serial: {e}")
        return None

def preprocess_data(data):
    data = data - np.mean(data)
    data = np.abs(data)
    return data

def filter_data(data, s_rate=100):
    """
    Apply bandpass filter to EMG data
    High-pass: 20 Hz (remove motion artifacts)
    Low-pass: 450 Hz (remove high-freq noise)
    Then envelope detection with low-pass at 5 Hz
    optional if using myoware2.0
    """
    if len(data) < 10:
        return data
    
    nyquist_f = s_rate / 2
    
    # Bandpass filter: 20-450 Hz
    high = 20.0 / nyquist_f
    low = min(450.0 / nyquist_f, 0.99)  
    
    try:
        b, a = signal.butter(4, [high, low], btype='bandpass')
        emg_filtered = signal.filtfilt(b, a, data)
        
        # Rectify
        emg_rectified = np.abs(emg_filtered)
        
        # Envelope detection with low-pass filter at 5 Hz
        low_pass = 5.0 / nyquist_f
        b2, a2 = signal.butter(4, low_pass, btype='lowpass')
        emg_envelope = signal.filtfilt(b2, a2, emg_rectified)
        
        return emg_envelope
    except Exception as e:
        return data

def threshold_prediction(data, threshold=100):
    max_value = np.max(data)
    
    if max_value > threshold:
        return 1  # Active/Grab
    else:
        return 0  # Relaxed/Release

def control_output(motion, previous_motion):
    if motion != previous_motion:
        if motion == 1:
            # DO things
            # - Send serial command
            # - Control GPIO pin
            # - Trigger servo/motor
            # - Send network packet
            # Example: ser.write(b'GRAB\n')
            print("state")
        else:
            print("another state")
            # Add release control code
    
    return motion

def calibrate_threshold(ser, duration=5):
    print(f"Keep muscle RELAXED for {duration} seconds...")
    time.sleep(2)
    
    baseline_buffer = []
    start = time.time()
    while time.time() - start < duration:
        value = read_emg_packet(ser)
        if value is not None:
            baseline_buffer.append(value)
        time.sleep(0.01)
    
    baseline_mean = np.mean(baseline_buffer)
    baseline_std = np.std(baseline_buffer)
    
    # print(f"Baseline: {baseline_mean:.2f} ± {baseline_std:.2f}")
    print(f"\nNow CONTRACT muscle for {duration} seconds...")
    time.sleep(2)
    
    active_buffer = []
    start = time.time()
    while time.time() - start < duration:
        value = read_emg_packet(ser)
        if value is not None:
            active_buffer.append(value)
        time.sleep(0.01)
    
    active_mean = np.mean(active_buffer)
    active_max = np.max(active_buffer)
    
    # print(f"Active: {active_mean:.2f}, Max: {active_max:.2f}")
    
    threshold = baseline_mean + (active_mean - baseline_mean) * 0.5
    return threshold


if __name__ == "__main__":
    # Config
    SERIAL_PORT = '/dev/ttyUSB0'  
    BAUDRATE = 115200
    SAMPLE_RATE = 100  # Hz
    WINDOW_SIZE = 100  # Number of samples in sliding window
    THRESHOLD = 100  
    
    ser = connect_serial(SERIAL_PORT, BAUDRATE)
    if ser is None:
        print("Failed to connect to serial port. Exiting.")
        exit(1)
    
    try:
        response = input("Run calibration? (y/n): ").lower()
        if response == 'y':
            THRESHOLD = calibrate_threshold(ser, duration=3)
        else:
            print(f"Using default threshold: {THRESHOLD}")
    except KeyboardInterrupt:
        print("\nCalibration skipped")
    
    emg_buffer = EMGBuffer(window_size=WINDOW_SIZE)

    previous_motion = 0
    frame_count = 0
    start_time = time.time()
    
    # Main Loop
    try:
        while True:
            raw_value = read_emg_packet(ser)
            
            if raw_value is not None:
                emg_buffer.add(raw_value)
                if emg_buffer.is_full():
                    data = emg_buffer.get_data()
                    data = preprocess_data(data)
                    data = filter_data(data, SAMPLE_RATE)
                    motion = threshold_prediction(data, THRESHOLD)
                    previous_motion = control_output(motion, previous_motion)
                    
                    frame_count += 1
                    
                    # Print stats every second
                    if frame_count % 10 == 0:
                        elapsed = time.time() - start_time
                        fps = frame_count / elapsed
                        print(f"FPS: {fps:.1f}")
            
            # Control loop rate
            time.sleep(1.0 / SAMPLE_RATE)
    
    except KeyboardInterrupt:
        print("\n\nStopping inference...")
    
    finally:
        if ser and ser.is_open:
            ser.close()
        print("Serial connection closed")
