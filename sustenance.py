#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Authors: Natan Lao, Eli Pandolfo
# crawl UCSC dining hall menus, search current menu items,
# collect and analyze data over time

from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import requests
import sys
import time
import urllib.parse
import numpy as np

BASE_URL = "http://nutrition.sa.ucsc.edu/menuSamp.asp?locationNum={location_id}&locationName={location}&sName=&naFlag="

LOCATIONS = {
    5: "Cowell Stevenson Dining Hall",
    20: "Crown Merill Dining Hall",
    25: "Porter Kresge Dining Hall",
    30: "Rachel Carson Oakes Dining Hall",
    40: "Colleges Nine & Ten Dining Hall",
    # There are some other non-dining hall locations but those are all
    # formatted in another, weird way and I don't like that.
}


def parse_url(url, location_id):
    r = requests.get(url)
    s = BeautifulSoup(r.content, 'lxml')

    rv = {
        'location_id': str(location_id).zfill(2),
        'location': LOCATIONS[location_id],
        'date': time.strftime("%m/%d/%Y"),
        'asof': datetime.utcnow().isoformat(),
        'menu': [],
    }

    for item in s.find_all(class_="menusamprecipes"):
        data = {}

        data['has'] = []
        for attrib in item.parent.parent.findChildren("img"):
            name = os.path.splitext(os.path.basename(attrib['src']))[0]
            if name == "gluten":
                name = "nogluten"
            data['has'].append(name)

        data.update({
            'name': item.text,
            'course': item.findPrevious(class_="menusampmeals").text,
            'group': None,
        })

        # If the item is actually a header for a Bar
        if item.span['style'] == 'color: #008000':
            data['group'] = True
        # I don't know an easier way to do this (efficiently) so we're going
        # to build the menu first, then after the menu has been totally compiled,
        # loop through the menu again and look for any items with group=True. If
        # that's the case, we'll then assume that all items occurring after that
        # item for the remainder of the current course are part of that group.
        # There's probably a better way to do this.

        rv['menu'].append(data)

    return rv


# i don't like this
def process_group(menu):
    bar = ""
    course = ""
    for item in menu:
        if bar and item['course'] == course:
            item['group'] = bar
        if item['group'] is True:
            course = item['course']
            bar = item['name']

    return [i for i in menu if i['group'] is not True]

# searches for one or more food items in all dining halls
def simple_search(menu, food_item):
    result_string = ''
    for location in menu:
        result_string += location['location'] + ':\n'
        for item in location['menu']:
            for search_term in food_item:
                if search_term.lower() in item['name'].lower():
                    group = item['group'] if item['group'] is not None else ''    
                    result_string += item['name'] + ' -- ' + item['course'] + \
                    ', ' + group + ', contains: '
                    for food_label in item['has']:
                        result_string += food_label + ' '
                    result_string += '\n'
        result_string += '\n'
    return result_string

def equals(s, t):
    if s == t:
        return 0
    else:
        return 1

# sequence alignment algorithm for autocorrecting search queries
# mismatch incurs cost of 1, gap incurs cost of 1
def match(search, target):
    m = 2
    g = 1.5
    min_diff = 999999

    if search == '9':
        search = 'nine'
    if search == '10':
        search == 'ten'

    search = search.lower()
    target = target.lower()
        
    A = np.empty([len(search) + 1, len(target) + 1])
    
    for i in range(len(search) + 1):
        A[i, 0] = i * g
    for j in range(len(target) + 1):
        A[0, j] = j * g
    
    # matrix uses i, strings use i-1
    for i in range(1, len(search) + 1):
        for j in range(1, len(target) + 1):
            s = search[i - 1]
            t = target[j - 1]

            A[i, j] = min(
                m * equals(s, t) + A[i - 1, j - 1],
                g + A[i - 1, j],
                g + A[i, j - 1])
    
    # if A[len(search), len(target)] <= 10:
    #     print('search: ' + search + '\ttarget ' +  target + '\tdiff: ' + str(A[len(search), len(target)]))
    
    if A[len(search), len(target)] < min_diff:
        min_diff = A[len(search), len(target)]

    if min_diff < 4:
        return True
    else:
        return False
            

def advanced_search(menu, foods='all', locations='all', courses='all', groups='all', restrictions=None):

    # use the parameters to reduce the menu
    # this is done additively instead of with list comprehension because the fcn's args can be lists
    # could use sets and is disjoint
    parsed_menu = []

    if locations is not 'all':
        for menu_loc in menu:
            for arg_loc in locations:
                for word in menu_loc['location'].split(' '):
                    if match(arg_loc, word) == True:
                        parsed_menu.append(menu_loc)
    else:
        parsed_menu = menu
    
    if courses is not 'all':
        for menu_loc in parsed_menu:
            new_loc_menu = []
            for item in menu_loc['menu']:
                for course in courses:
                    # try and match with the phrase and each word in the phrase.
                    # eg, 'night' will return 'Late Night'
                    if match(course, item['course']) == True:
                        new_loc_menu.append(item)
                        break
                    for word in item['course'].split(' '):
                        if match(course, word) == True:
                            new_loc_menu.append(item)
                            break

            menu_loc['menu'] = new_loc_menu
    
    if groups is not 'all':
        for menu_loc in parsed_menu:
            new_loc_menu = []
            for item in menu_loc['menu']:
                for group in groups:
                    if item['group'] is not None:
                        if match(group, item['group']) == True:
                            new_loc_menu.append(item)
                            break
                        for word in item['group'].split(' '):
                            if match(group, word) == True:
                                new_loc_menu.append(item)
                                break

            menu_loc['menu'] = new_loc_menu

    if foods is not 'all':
        for menu_loc in parsed_menu:
            new_loc_menu = []
            for item in menu_loc['menu']:
                for food in foods:
                    if match(food, item['name']):
                        new_loc_menu.append(item)
                        break
                    for word in item['name'].split(' '):
                        if match(food, word) == True:
                            new_loc_menu.append(item)
                            break

            menu_loc['menu'] = new_loc_menu

    # restrictions: glutenfree, soy, dairy, nuts
    if restrictions is not None:
        for menu_loc in parsed_menu:
            new_loc_menu = []
            for item in menu_loc['menu']:
                for restriction in restrictions:
                    for attribute in item['has']:
                        if match(restriction, attribute) == False:
                            new_loc_menu.append(item)
                            break

            menu_loc['menu'] = new_loc_menu
    
    results = ''
    for location in parsed_menu:
        results += location['location'] + ':\n'
        for item in location['menu']:

            group = item['group'] if item['group'] is not None else ''    
            results += '\t' + item['name'] + ' -- ' + item['course'] + ', ' + group + ', contains: '
            for food_label in item['has']:
                results += food_label + ' '
            results += '\n'
        results += '\n'
    
    return results

def search(fname):
    with open(fname, 'r') as f:
        menu = json.load(f)
    search_result = advanced_search(menu, foods=['potato'])
    print('\n')
    print(search_result)

search('test')


def main(fname):
    urls = []
    for location_id, location in LOCATIONS.items():
        urls.append((BASE_URL.format(**{
            'location_id': str(location_id).zfill(2),
            'location': urllib.parse.quote_plus(location),
        }), location_id))

    results = []
    for url, location_id in urls:
        results.append(parse_url(url, location_id))

    for result in results:
        result['menu'] = process_group(result['menu'])

    with open(fname, "w") as f:
        json.dump(results, f)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])
    











    