import sys
import shutil

import tensorflow as tf
import efficientnet.tfkeras as efn

import codebase as cb


def create_model(outputs, trainable_blocks=[]):
    model = efn.EfficientNetB4(include_top=False, weights='imagenet', pooling='max')
    
    for l in model.layers:
        l.trainable = any([(b in l.name) for b in trainable_blocks])

    model.add(tf.keras.layers.Dense(outputs))
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    
    return model


if __name__ == '__main__':
    data = sys.argv[1]
    if sys.argv[2] is not None:
        trainable_blocks = [ f'block{i}' for i in sys.argv[2].split(',')]
    else:
        trainable_blocks = []
    
    if data == 'paint':
        classes = 136
    elif data == 'arch':
        classes = 25
    cp_dir = f'checkpoint_{data}/'
    shutil.rmtree(cp_dir, ignore_errors=True)

    train_set, eval_set = cb.load_train(data)

    model = create_model(classes, trainable_blocks)

    train_stats = {
        'loss': [],
        'accuracy': []
    }

    eval_stats = {
        'loss': [],
        'accuracy': []
    }
    best_loss = 1000
    patience = 0
    for i in range(100):
        history = model.fit(
            train_set,
            epochs=1,
        )
        train_stats['loss'].append(history['loss'])
        train_stats['accuracy'].append(history['accuracy'])

        loss, accuracy = model.evaluate(eval_set)
        eval_stats['loss'].append(loss)
        eval_stats['accuracy'].append(accuracy)

        if loss < best_loss - 1e-5:
            model.save(cp_dir)
            best_loss = loss
            patience = 0
        else:
            if patience < 10:
                patience += 1
            else:
                break
