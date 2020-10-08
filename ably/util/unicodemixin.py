class UnicodeMixin(object):
    def __str__(self):
        return self.__unicode__()
