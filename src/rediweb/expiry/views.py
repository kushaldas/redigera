# Create your views here.
import os
import time
from datetime import datetime
from io import BytesIO
from multiprocessing import Process, Queue
from pathlib import Path
from pprint import pprint
from typing import Dict, Optional

import johnnycanencrypt.johnnycanencrypt as rjce
from django.http import FileResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils.dateparse import parse_datetime

from .forms import UpdateExpiryForm, UploadFileForm

# The main key data
KEY = BytesIO()
# After updated expiry date
UPDATEDKEY = BytesIO()
# Fingerprint of the primary key
FINGERPRINT = ""
# Bulk Data
DB = {}
# If we have a real key uploaded already
UP = False
# Queue for multiprocessing, this is what we use to get back the data
Q = Queue()
# The process object
PROCESS = None


# To make it easier in templates etc
class Subkey:
    def __init__(self, data) -> None:
        self.fingerprint = data[1]
        self.expiry = data[3]
        self.keytype = data[4]

def change_expiry_date(key: bytes, date: Optional[datetime], pin: str, db: Dict, q: Queue): 
    """This updates the key, runs on a different process via multiprocess.
    """
    pin = pin.strip()
    # First calculate when in future the key is expiring
    newtime = date - datetime.now()
    new_expiry_in_future = int(newtime.total_seconds())
        
    # Now first update the primary expiry date
    data = rjce.update_primary_expiry_on_card(key, new_expiry_in_future, pin.encode("utf-8"))
    subkeys = []
    for skey in db["subkeys"]:
        subkeys.append(skey.fingerprint)
    # Next update the expiry for subkeys
    data = rjce.update_subkeys_expiry_on_card(data, subkeys, new_expiry_in_future, pin.encode("utf-8"))
    # Now return the data before finish
    q.put(data)



def upload_file(request):
    """Allows uploading the public key file from user.
    """
    global KEY, UP
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            KEY = BytesIO()
            for chunk in request.FILES["file"].chunks():
                KEY.write(chunk)
            # We now have a public key file on memory.
            UP = True
            KEY.seek(0)
            return HttpResponseRedirect("/")
        else:
            print(form)
            print("Failed  form validation.")
    else:
        form = UploadFileForm()
    return render(request, "expiry/upload.html", {"form": form})

def index(request):
    global UP, FINGERPRINT, DB
    fingerprint = ""
    expiring_on = None
    subkeys = []
    if UP:
        # We have a key
        keydata = KEY.read()
        try:
            pgp_data = rjce.parse_cert_bytes(keydata)
            expiring_on = pgp_data[3]
            FINGERPRINT = pgp_data[1]
            KEY.seek(0)
            for skey in pgp_data[5]["subkeys"]:
                # now for each key create the data we need
                sub = Subkey(skey)
                subkeys.append(sub)
            DB["subkeys"] = subkeys
        except:
            UP = False
    return render(request, "expiry/index.html", {"up": UP, "fingerprint": FINGERPRINT, "expiry": expiring_on, "subkeys": subkeys})

def getyubikey(request):
    "This verifies that we can access a yubikey"
    if rjce.is_smartcard_connected():
        return render(request, "expiry/yubikeyfound.html")
    else:
        return render(request, "expiry/checkyubikey.html")

def expiry(request):
    "Shows the expiry form"
    return render(request, "expiry/expiryform.html")

def update_expiry(request):
    global UP, Q, KEY, DB
    msg = ""
    if request.method == "POST":
        form = UpdateExpiryForm(request.POST)
        if form.is_valid():
            # Now update the public key
            try:
                date = parse_datetime(form.data["date"])
                if not date:
                    raise Exception("Failed to parse")
                pin = form.data["pin"]
                # Now start the process to upload to Yubikey
                keydata = KEY.read()
                PROCESS = Process(target=change_expiry_date, args=(keydata, date, pin, DB, Q))
                msg = "Updation is happening."
                PROCESS.start()
            except:
                return render(request, "expiry/expiryform.html")
        else:
            # Show the form again for invalid form
            return render(request, "expiry/expiryform.html")
    # It is a GET request or POST started updating.
    return render(request, "expiry/update_expiry.html")

def key_ready(request):
    "Function to check if a key is ready"
    global Q,UPDATEDKEY, FINGERPRINT
    msg = "Update is happening."
    filename = None
    try:
        data = Q.get_nowait()
    except:
        data = None
    if data: # Means we have the new key
        dirname = Path.home() / "Downloads"
        if not os.path.exists(dirname):
            # TODO: Create the directory
            pass
        filename = dirname / f"{FINGERPRINT}.pub"
        with open(filename, "wb") as fobj:
            fobj.write(data)
        msg = "Updated key is ready."
        UPDATEDKEY.write(data)

    return render(request, "expiry/update_expiry.html", {"msg": msg, "data": data, "filename": str(filename)})
