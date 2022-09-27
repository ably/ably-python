import random
import string


def get_random_id():
    # get random string of letters and digits
    source = string.ascii_letters + string.digits
    random_id = ''.join((random.choice(source) for i in range(8)))
    return random_id
