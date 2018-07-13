import re

def camel_to_snake(name, first_cap_re = re.compile('(.)([A-Z][a-z]+)')):
    return first_cap_re.sub(r'\1_\2', name).lower()

def snake_to_camel(name):
    name = name.split('_')
    for i in range(1, len(name)):
        name[i] = name[i].title()

    return ''.join(name)
