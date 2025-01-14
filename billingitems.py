#!/usr/bin/env python

import cv2
import os
import sys, getopt
import signal
import time
from edge_impulse_linux.image import ImageImpulseRunner
import RPi.GPIO as GPIO 
from hx711 import HX711
import requests
import json
from requests.structures import CaseInsensitiveDict

runner = None
show_camera = True

c_value = 0
flag = 0
ratio = -1363.992

global id_product
id_product = 1
list_label = []
list_weight = []
count = 0
final_weight = 0
taken = 0

a = 'Apple'
b = 'Banana'
l = 'Lays'
c = 'Coke'

total_cost = 0  # Track the total cost for the customer

def now():
    return round(time.time() * 1000)

def get_webcams():
    port_ids = []
    for port in range(5):
        print("Looking for a camera in port %s:" % port)
        camera = cv2.VideoCapture(port)
        if camera.isOpened():
            ret = camera.read()[0]
            if ret:
                backendName = camera.getBackendName()
                w = camera.get(3)
                h = camera.get(4)
                print("Camera %s (%s x %s) found in port %s " % (backendName, h, w, port))
                port_ids.append(port)
            camera.release()
    return port_ids

def sigint_handler(sig, frame):
    print('Interrupted')
    if runner:
        runner.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, sigint_handler)

def help():
    print('python classify.py <path_to_model.eim> <Camera port ID, only required when more than 1 camera is present>')

def find_weight():
    global c_value
    global hx
    if c_value == 0:
        print('Calibration starts')
        try:
            GPIO.setmode(GPIO.BCM)
            hx = HX711(dout_pin=20, pd_sck_pin=21)
            err = hx.zero()
            if err:
                raise ValueError('Tare is unsuccessful.')
            hx.set_scale_ratio(ratio)
            c_value = 1
        except (KeyboardInterrupt, SystemExit):
            print('Bye :)')
        print('Calibrate ends')
    else:
        GPIO.setmode(GPIO.BCM)
        time.sleep(1)
        try:
            weight = int(hx.get_weight_mean(20))
            print(weight, 'g')
            return weight
        except (KeyboardInterrupt, SystemExit):
            print('Bye :)')

def post(label, price, final_rate, taken):
    global id_product
    url = "https://automaticbilling.herokuapp.com/product"
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"
    data_dict = {"id": id_product, "name": label, "price": price, "units": "units", "taken": taken, "payable": final_rate}
    data = json.dumps(data_dict)
    resp = requests.post(url, headers=headers, data=data)
    print(resp.status_code)
    id_product += 1  

def calculate_rate(final_weight, label, taken):
    global total_cost
    print("Calculating rate...")
    if label == a:
        print("Calculating rate of", label)
        price_per_g = 0.01  # Price per gram for Apple
        price = 10
    elif label == b:
        print("Calculating rate of", label)
        price_per_g = 0.02  # Price per gram for Banana
        price = 20
    elif label == l:
        print("Calculating rate of", label)
        price_per_g = 1  # Fixed price for Lays
        price = 1
    else:
        print("Calculating rate of", label)
        price_per_g = 2  # Fixed price for Coke
        price = 2

    final_rate = final_weight * price_per_g
    total_cost += final_rate  # Update total cost
    print(f"Total Cost So Far: ₹{total_cost:.2f}")  # Display total cost
    post(label, price, final_rate, taken)

def list_com(label, final_weight):
    global count
    global taken
    if final_weight > 2:
        list_weight.append(final_weight)
        if count > 1 and list_weight[-1] > list_weight[-2]:
            taken += 1
    list_label.append(label)
    count += 1
    print('Count is', count)
    time.sleep(1)
    if count > 1 and list_label[-1] != list_label[-2]:
        print("New Item Detected")
        print("Final weight is", list_weight[-1])
        calculate_rate(list_weight[-2], list_label[-2], taken)

def main(argv):
    global flag
    global final_weight
    if flag == 0:
        find_weight()
        flag = 1
    try:
        opts, args = getopt.getopt(argv, "h", ["--help"])
    except getopt.GetoptError:
        help()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            help()
            sys.exit()

    if len(args) == 0:
        help()
        sys.exit(2)

    model = args[0]

    dir_path = os.path.dirname(os.path.realpath(__file__))
    modelfile = os.path.join(dir_path, model)

    print('MODEL: ' + modelfile)

    with ImageImpulseRunner(modelfile) as runner:
        try:
            model_info = runner.init()
            print('Loaded runner for "' + model_info['project']['owner'] + ' / ' + model_info['project']['name'] + '"')
            labels = model_info['model_parameters']['labels']
            videoCaptureDeviceId = int(args[1]) if len(args) >= 2 else 0

            camera = cv2.VideoCapture(videoCaptureDeviceId)
            if not camera.isOpened():
                raise Exception("Couldn't initialize selected camera.")

            for res, img in runner.classifier(videoCaptureDeviceId):
                if "classification" in res["result"].keys():
                    for label in labels:
                        score = res['result']['classification'][label]
                        if score > 0.9:
                            final_weight = find_weight()
                            list_com(label, final_weight)
        finally:
            if runner:
                runner.stop()

if __name__ == "__main__":
    main(sys.argv[1:])
