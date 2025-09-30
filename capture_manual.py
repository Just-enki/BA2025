from picamera2 import Picamera2
from datetime import datetime
import schedule
import time

# Set resolution
resolution = (1280, 720)

# custom ISO and shutter speed
ISO_VALUE = 100              
#SHUTTER_SPEED_US = 20000    # microseconds (20,000 mus = 1/50 sec)

def job():
    print('running job')
    try:
        picam2a = Picamera2(0)
        picam2b = Picamera2(1)
        print('starting cameras')

        # create still configs
        config_a = picam2a.create_still_configuration(main={"size": resolution})
        config_b = picam2b.create_still_configuration(main={"size": resolution})

        picam2a.configure(config_a)
        picam2b.configure(config_b)

        # apply ISO  and shutter speed
        picam2a.set_controls({"AnalogueGain": ISO_VALUE/100})
        picam2b.set_controls({"AnalogueGain": ISO_VALUE/100})
        picam2a.awb_mode = 'off' 
        picam2a.awb_gains = (1.0, 1.0) 
        picam2b.awb_mode = 'off'
        picam2b.awb_gains = (1.0, 1.0)

        picam2a.start()
        picam2b.start()

        print('capturing images')

        # get current time
        now = datetime.now()
        time_str = now.strftime("%d_%m_%H_%M")

        # save images with timestamp
        picam2a.capture_file(f"./ba_1_LED/{time_str}.jpg")
        picam2b.capture_file(f"./ba_2_LED/{time_str}.jpg")

        print('stopping cameras')
        picam2a.stop()
        picam2b.stop()
        print('cameras stopped')

    except Exception as e:
        print("There was an error running the camera:", e)

    finally:
        # close cams
        try: picam2a.close()
        except: pass
        try: picam2b.close()
        except: pass


# Run job every 5 minutes
job()
schedule.every(5).minutes.do(job)

while True:
    schedule.run_pending()
    time.sleep(30)
