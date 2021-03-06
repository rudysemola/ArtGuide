import io
import numpy as np
from PIL import Image
import time
import re
import os
import json
import requests
import base64
import pprint

from helpers import Point, ImageBoundingBox
from flask_cors import CORS
from flask import Flask, escape, request
from google.cloud import vision
from google.cloud.vision import types
from google.protobuf.json_format import MessageToDict
from google.oauth2 import service_account
from PIL import Image
import tensorflow as tf
from google.oauth2 import service_account

PORT = 2345
VALID_PICT_LABELS = set(["Painting", "Picture frame"])
VALID_ARCH_LABELS = set(["Building", "Architecture", "Monument"])
CROP_SIZE = [300, 300, 3]

# ----- ----- CONFIGURING ROUTES ----- ----- #
if not "ROUTES_JSON" in os.environ:
    print("routes.json path not specified, please set the envir. variable ROUTES_JSON")
    exit(0)
routes_path = os.environ["ROUTES_JSON"]

if not os.path.exists(routes_path):
    print("routes file not found: {}".format(routes_path))
    exit(0)

with open(routes_path) as json_path:
    routes_json = json.load(json_path)
    OPUS_URL = routes_json["opus"]
    print("> Post to opus service on port {}".format(OPUS_URL))

# ----- ----- CONFIGURING MODELS ----- ----- #
if not "MODELS_DIR_PATH" in os.environ:
    print("Models directory path not specified, please set the envir. variable MODELS_DIR_PATH")
    exit(0)
models_path = os.environ["MODELS_DIR_PATH"]

# ----- CONFIGURING API KEY ----- #
if not "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
    print("Google cloud vision API key not provided, please set the envir. variable GOOGLE_APPLICATION_CREDENTIALS")
    exit(0)
api_key_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

if not os.path.exists(api_key_path):
    print("Google cloud API key file not found: {}".format(api_key_path))


# ----- CONFIGURING TENSOR MAP ----- #
with open("image_analysis/app/tensormaps/dpictstyle2wd.json", "r") as f:
    # picture style name to wikidata identifier
    PICTSTYLE_2_WD = json.load(f)

with open("image_analysis/app/tensormaps/idx2pictstyle.json", "r") as f:
    # picture style name to index in the model output
    IDX_2_PICTSTYLE = json.load(f)

with open("image_analysis/app/tensormaps/darchstyle2wd.json", "r") as f:
    # picture style name to wikidata identifier
    ARCHSTYLE_2_WD = json.load(f)

with open("image_analysis/app/tensormaps/idx2archstyle.json", "r") as f:
    # picture style name to index in the model output
    IDX_2_ARCHSTYLE = json.load(f)




# ----- FUNCTION DEFINITION ----- #
def tf2wd(model_prediction_tf, art_type='picture'):
    """Convert a model prediction to a dictionary {"WDId": v} with {v} the value predicted by the model for each style
    INPUT 
        model_prediction_tf - tensor returned by the model
        art_type            - 'architecture' or 'picture' 
    """ 
    res = []
    prediction = list(map(float, list(model_prediction_tf)))
    if art_type == "picture":
        idx_style_map = IDX_2_PICTSTYLE 
        style_2_wd = PICTSTYLE_2_WD 
    else:
        idx_style_map = IDX_2_ARCHSTYLE
        style_2_wd = ARCHSTYLE_2_WD

    for idx, stylename in idx_style_map.items():
        wd_id = style_2_wd[stylename]
        res.append({"wikidataId": wd_id, "score": prediction[int(idx)]})
    return res


def get_vision(content):
    # The name of the image file to annotate
    image = types.Image(content=content)

    # Performs label detection on the image file
    label = MessageToDict(client.label_detection(image=image))
    web_entities = MessageToDict(client.web_detection(image=image))

    return {"label": label, "we": web_entities}


def get_bounding(content):
    # The name of the image file to annotate
    image = types.Image(content=content)

    # Performs object detection on the image file
    objects = MessageToDict(client.object_localization(image=image))

    return {"objects": objects}


def freebaseID2wd(freebase_id):
    url = 'https://query.wikidata.org/sparql'
    query = """
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX wikibase: <http://wikiba.se/ontology#>

    SELECT ?s WHERE {{
      ?s ?p ?o .
      ?s wdt:P646 "{}" .
    }}
    LIMIT 1
    """.format(freebase_id)
    for tries in range(0, 3):
        try:
            data = None
            r = requests.get(url, params = {'format': 'json', 'query': query})
            data = r.json()
            break
        except ValueError:
            time.sleep(.5)
            pass
    if data is None:
        print("Requests to wikidata failed for {}".format(freebase_id))
        return None

    iri = data["results"]["bindings"][0]["s"]["value"]    
    return iri.split("/")[-1]


# ----- CROP FUNCTION ON BOUNDING BOX ----- #
def crop_on_bb(image, api_res):
    most_centered_obj = None
    if "localizedObjectAnnotations" not in api_res["objects"]:
        print(" -- No crop found -- ")
        return image
     
    for obj in api_res["objects"]["localizedObjectAnnotations"]:
        if not "name" in obj:
            continue
        if obj["name"] in VALID_PICT_LABELS:
            # Sum distances from the center (return the most "centered" bounding box)
            nv = obj["boundingPoly"]["normalizedVertices"]
            bb = ImageBoundingBox(nv)
            if (most_centered_obj is None) or (bb.distance < most_centered_obj.distance):
                most_centered_obj = bb

    if most_centered_obj is None:
        print(" -- No crop found -- ")
        return image


    imageb = Image.open(io.BytesIO(image))
    imageb.show()
    width, height = imageb.size

    points = most_centered_obj.points

    left = points[0].x * width 
    top = points[0].y * height
    right = points[1].x * width
    bottom = points[2].y * height

    # Crop image with above dimension  
    im1 = imageb.crop((left, top, right, bottom)) 
    newsize = (CROP_SIZE[0], CROP_SIZE[1])
    im1 = im1.resize(newsize) 
    
    imgByteArr = io.BytesIO()
    im1.save(imgByteArr, format='PNG')
    imgByteArr = imgByteArr.getvalue()

    return imgByteArr


def detect_image_type(obj_res, api_res):
    """Returns:
    0: Picture
    1: Architecture
    2: None
    """
    pprint.pprint(obj_res)
    if "localizedObjectAnnotations" in obj_res["objects"]:
        for obj in obj_res["objects"]["localizedObjectAnnotations"]:
            if obj["name"] in VALID_PICT_LABELS:
                return 0
            if obj["name"] in VALID_ARCH_LABELS:
                return 1

    to_check = [api_res["we"]["webDetection"]["webEntities"], api_res["label"]["labelAnnotations"]]
    for entity_list in to_check:
        for lem in entity_list:
            if "description" not in lem:
                continue
            if lem["description"] in VALID_PICT_LABELS:
                return 0
            if lem["description"] in VALID_ARCH_LABELS:
                return 1
        
    return 2


# ----- ENVIRONMENT ----- #
app = Flask(__name__)
CORS(app, resources=r"/*")
credentials = service_account.Credentials.from_service_account_file(api_key_path)
client = vision.ImageAnnotatorClient(credentials=credentials)
architecture_nn = tf.saved_model.load("{}/models/architecture/1".format(models_path))

# ----- ROUTES ----- #
@app.route("/", methods=["GET"])
def home():
    return "<h1>Image analysis service</h1>"


@app.route("/mock", methods=["POST"])
def mock():
    content = request.get_json()
    labels = image_analysis(content)
    pprint.pprint(labels)
    return str(labels)


@app.route("/upload", methods=["POST"])
def upload():
    # Define the headers (they are needed to make get_json() work)
    head = {"Content-type": "application/json"}

    content = request.get_json()
    labels = image_analysis(content)

    r = requests.post(OPUS_URL, json=labels, headers=head)
    return r.content


def replaceGFreebaseID(elist, field): 
    res = []
    for el in elist: 
        try:
            el[field] = freebaseID2wd(el[field])
            if el[field] is not None:
                res.append(el)
        except IndexError as e:
            print("> error: unable to find wikidataID for {}".format(el))
    return res


def visionMock(img):
    return {
        "label": { "labelAnnotations": "fake" },
        "we": {"webDetection": { "webEntities": "fake" }}
    }


def image_analysis(content):
    """
    For Test.py:
        load the Base64 encoded image with get_json(),
        decode it back to an image and send it to the API
        to retrieve the JSON answer.
    """
    # Manipulating image
    image = content["image"]
    image_b64_str = re.sub("^data:image/.+;base64,", "", image)
    img_b64 = base64.b64decode(image_b64_str)
    
    # Vision API request and bounding box crop
    obj_res = get_bounding(img_b64)
    cropped_img = crop_on_bb(img_b64, obj_res)
    api_res = get_vision(cropped_img)
    # api_res = visionMock(cropped_img)
    
    # Architecture model request
    numpy_image = np.asarray(Image.open(io.BytesIO(cropped_img)))
    tf_image = tf.convert_to_tensor([numpy_image])
    
    tf_image = tf.image.decode_jpeg(img_b64, channels=3)[tf.newaxis, ...]
    tf_image = tf.image.resize_with_crop_or_pad(tf_image, CROP_SIZE[0], CROP_SIZE[1])
    tf_image = tf.image.convert_image_dtype(tf_image, tf.float32, name="input_1") / 255
    
    wd_prediction = []
    typ = detect_image_type(obj_res, api_res)
    if typ == 0:
        pass
        #pict_pred = picture_nn(tf_image)
        #wd_prediction = tf2wd(pict_pred[0], art_type="picture")
    if typ == 1:
        arch_pred = architecture_nn(tf_image)
        wd_prediction = tf2wd(arch_pred[0], art_type="architecture")

    # Cleaning data for ir module ----- #
    content["classification"] = {
        "labels": api_res["label"]["labelAnnotations"],
        "entities": api_res["we"]["webDetection"]["webEntities"],
        "locations": [],
        "safeSearch": [],
        "type": [],
        "monumentType": [],
        "period": [],
        "style": wd_prediction,
        "materials": []
    }
    del content["image"]
    
    # Cleaning data for ir module ----- #
    for el in content["classification"]["labels"]:
        el["entityId"] = el["mid"]
        del el["mid"]
    # Replace freebaseID with wikidataID
    # content["classification"]["entities"] = replaceGFreebaseID(content["classification"]["entities"], "entityId")
    # content["classification"]["labels"] = replaceGFreebaseID(content["classification"]["labels"], "mid")

    return content


if __name__ == "__main__":
    app.config["DEBUG"] = True
    print("> Opening service on port {}".format(PORT))
    app.run(host="0.0.0.0", port=PORT)
