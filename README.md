Crawler for UCSC dining hall menus. The menus are powered by FoodPro / Aurora Information Systems, so this code would likely (mostly?) work on similar systems with minimal modification.

```
$ pip install -r requirements.txt
$ python3 sustenance.py dest.json
```

The JSON looks something like this:

```
[{
    'location_id': 05,
    'location': "Cowell Stevenson Dining Hall",
    'date': "11/13/2017",
    'asof': time.now(),
    'menu': [
        {
            'name': "Belgian Waffles",
            'has': ['glutenfree', 'soy', 'dairy'],
            'course': "Breakfast",
            'group': None,
        },
        {
            'name': "Cheesy Garlic Bread Sticks",
            ...
            'group': "Bar Pasta",`
        }
    ]
}, ...]
```
