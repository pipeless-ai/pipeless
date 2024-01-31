def hook(frame_data, _):
    # Add data to the frame that you can later recover from hooks of subsequent stages. You can also recover it from subsequent hooks of the same stage.
    # You can use any kind of data.
    # Integers: frame_data['user_data'] = 100
    # Floats:   frame_data['user_data'] = 100.5
    # Strings:  frame_data['user_data'] = "Hello!"
    # Heterogeneus arrays: frame_data['user_data'] = ["string", 13, 34.6]
    # Heterogeneus Dictionaries (IMPORTANT: all keys must be strings):
    frame_data['user_data'] = {
        "key1": 0,
        "key2": [1, "3"],
        "key3": { "inner1": "hola" }
    }

    # In a later hook you can obtain the data like:
    # my_data = frame_data['user_data']

    # To connect stages simply give the list to Pipeless when adding a stream:
    # pipeless add stream --input-uri "file:///home/user/my/path.mp4" --output-uri "screen" --frame-path "stage1,stage2"
