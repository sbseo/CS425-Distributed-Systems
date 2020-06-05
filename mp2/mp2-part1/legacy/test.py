d = dict() # Stores

d.update({'a':1, 'b':2})

for v in d.values():
    print(v)


def update_node_handler(object):
    print(type(object))
    print(object)
    return 0
# print(d.pop('a'))
# print(d.keys())
print(update_node_handler("2"))