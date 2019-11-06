import requests 
import json
import os
  
URL = "http://cipizio.it:4321/keywords"
  
 
with open("./adaptation/data/input_phase1.json","r") as file:
    PARAMS = json.load(file)
    r = requests.post(url = URL, json = PARAMS) 
  
data = r.json() 
  
print(data)