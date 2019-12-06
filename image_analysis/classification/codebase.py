import os

import pandas as pd
import tensorflow as tf
import shutil

import project_types as pt

CROP_SIZE = [299, 299, 3]

arch_styles = [
    'Achaemenid architecture',
    'American Foursquare architecture',
    'American craftsman style',
    'Ancient Egyptian architecture',
    'Art Deco architecture',
    'Art Nouveau architecture',
    'Baroque architecture',
    'Bauhaus architecture',
    'Beaux-Arts architecture',
    'Byzantine architecture',
    'Chicago school architecture',
    'Colonial architecture',
    'Deconstructivism',
    'Edwardian architecture',
    'Georgian architecture',
    'Gothic architecture',
    'Greek Revival architecture',
    'International style',
    'Novelty architecture',
    'Palladian architecture',
    'Postmodern architecture',
    'Queen Anne architecture',
    'Romanesque architecture',
    'Russian Revival architecture',
    'Tudor Revival architecture',
]

# ----- ----- TENSORFLOW ARCHITECTURE ----- ----- #
one_hot_arch = tf.one_hot(range(len(arch_styles)), len(arch_styles))
tflabels_arch = {style: one_hot_arch[idx] for idx, style in enumerate(arch_styles)}


def archstyle2str(tf_vect):
    return arch_styles[tf.math.argmax(tf_vect)]


def parse_image_arch(filename, linux=True):
    if not linux:
        filename = tf.strings.regex_replace(filename, '\\\\', '/')
    fname = tf.strings.split(filename, '/')[-1]
    label = tf.strings.split(fname, '_')[0]

    image = tf.io.read_file(filename)
    image = tf.image.decode_jpeg(image)
    image = tf.image.convert_image_dtype(image, tf.float32)
    image = tf.image.random_crop(image, CROP_SIZE)
    return image, label


# ----- ----- TENSORFLOW PICTURE ----- ----- #
# Manipulating dataframe
pictdf = pd.read_csv(pt.pict_info, index_col='new_filename').drop('date', axis=1)
pictdf = pictdf.dropna(subset=['style'])
# Getting one hot
pict_styles = pictdf['style'].unique()
one_hot_pict = tf.one_hot(range(len(pict_styles)), len(pict_styles))
tflabels_pict = {style: one_hot_pict[idx] for idx, style in enumerate(pict_styles)}


def convert_paths(n_path):
    for (fpath, row) in pictdf.iterrows():
        try:
            new_fname = row['style'].replace(' ', '_') + '__' + str(fpath)
            new_path = pt.datasets / n_path / new_fname
            old_path = pt.pict_dset / fpath
            shutil.copyfile(old_path, new_path)
        except:
            pass
        
        
if not os.path.exists(pt.pict_style):
    os.mkdir(pt.pict_style)
    convert_paths(pt.pict_style)
        
        
def pictstyle2str(tf_vect):
    return pict_styles[tf.math.argmax(tf_vect)]


def parse_image_pict(filename, linux=True):
    if not linux:
        filename = tf.strings.regex_replace(filename, '\\\\', '/')
    fname = tf.strings.split(filename, '/')[-1]
    label = tf.strings.split(fname, '__')[0]

    image = tf.io.read_file(filename)
    image = tf.image.decode_jpeg(image)
    image = tf.image.convert_image_dtype(image, tf.float32)
    image = tf.image.random_crop(image, CROP_SIZE)
    return image, label
