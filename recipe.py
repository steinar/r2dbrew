# Volume is liters, temp is degrees celsius, duration is minutes.
sample_recipe = {
    'mash': {
        'water_volume': 27,
        'temp': 70,
        'rests': [
            {'temp': 66, 'duration': 60 },
            {'temp': 76, 'duration': 10 }
        ]
    },
    'boil_duration': 60,
    'hops': [
        {
            'when': 60,  # Minutes of boiling remaining
            'what': '28gr Cascade',
        },
        {
            'when': 30,
            'what': '14gr Cascade',
        },
        {
            'when': 15,
            'what': '7gr Cascade',
        },
        {
            'when': 5,
            'what': '7gr Cascade',
        },

    ],
    'final_temp': 20
}
