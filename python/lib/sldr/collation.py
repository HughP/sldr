#!/usr/bin/python

import re, copy
from math import log10
from itertools import groupby
from difflib import SequenceMatcher
import ducet


def escape(s):
    '''Turn normal Unicode into escaped tailoring syntax'''
    res = ""
    escs = ['\\&[]/<']
    for k in s:
        if k in escs:
            res += u"\\" + k
            continue
        i = ord(k)
        if 32 < i < 127:
            res += k
        elif i > 0xFFFF:
            res += u'\\U' + ("00000000" + (hex(i)[2:]))[:-8]
        else:
            res += u'\\' + ("0000" + (hex(i)[2:]))[:-4]
    return res

def unescape(s):
    '''Parse tailoring escaped characters into normal Unicode'''
    s = re.sub(ur'(?:\\U([0-9A-F]{8})|\\u([0-9A-F]{4}))', lambda m:unichr(int(m.group(m.lastindex), 16)), s, re.I)
    s = re.sub(ur'\\(.)', ur'\1', s)
    return s

def ducetSortKey(d, k, extra=None):
    '''Turn a sequence of sort keys for the given string into a single
        sort key.'''
    res = [[], [], []]
    i = len(k)
    while i > 0:
        try:
            if extra and k[:i] in extra:
                key = extra[k[:i]].key
            else:
                b = d[k[:i]]
                key = ducet._generateSortKey(b, separate=True)
        except KeyError:
            i -= 1
            continue
        res = [res[j] + key[j] for j in range(3)]
        k = k[i:]
        i = len(k)
    return res

def filtersame(dat, level):
    '''A kind of groupby, return first of every sequence with the sortkey
        up to the given level'''
    # anyopne want to refactor this to use groupby()?
    res = []
    acc = (0,)
    level -= 1
    for d in dat:
        if d[1][level] != acc:
            acc = d[1][level]
            res.append(d)
    return res

def makegroupdict(dat, keyfunc):
    '''Create a dictionary for each sublist of dat keyed by first
        in sublist. Used to collect subgroups with the same primary
        key keyed by the first in the sublist.'''
    res = {}
    for k, t in groupby(dat, keyfunc):
        d = list(t)
        res[d[0][0]] = d
    return res


class Collation(dict):

    def __init__(self, ducetDict):
        self.ducet = ducetDict

    def parse(self, string):
        """Parse LDML/ICU sort tailoring"""
        for run in string.split('&'):
            bits = [x.strip() for x in re.split(ur'([<=]+)', run)]
            base = unescape(bits[0])
            for i in range(1, len(bits), 2):
                if bits[i] == '=': l = 4
                else:
                    l = bits[i].count('<')
                key = unescape(bits[i+1])
                self[key] = CollElement(base, l)
                base = key

    def _setSortKeys(self):
        '''Calculates tailored sort keys for everything in this collation'''
        if len(self) > 0 :
            inc = 1. / pow(10, int(log10(len(self)))+1)
            for v in self.values():
                v.sortkey(self, self.ducet, inc)

    def asICU(self):
        """Returns ICU tailoring syntax of this Collation"""
        self._setSortKeys()
        lastk = None
        res = ""
        for k, v in sorted(self.items(), key=lambda x:x[1].key):
            if v.base != lastk:
                res += "\n&" + escape(v.base)
            if v.level == 4:
                res += "="
            else:
                res += " " + ("<<<"[:v.level]) + " "
            res += escape(k)
            lastk = k
        return res[1:] if len(res) else ""

    def _stripoverlaps(self, a, b):
        '''Given two sorted lists of (k, sortkey(k)) delete from this
            collation any k that is not inserted into the first list.
            I.e. only keep things inserted into the ducet sequence'''
        s = SequenceMatcher(a=a, b=b)
        for g in s.get_opcodes():
            if g[0] == 'insert': continue
            for i in range(g[3], g[4]):
                if b[i] in self:
                    del self[b[i]]

    def minimise(self, alphabet):
        '''Minimise a sort tailoring such that the minimised tailoring
            functions the same as the unminimised tailoring for the
            strings in alphabet (e.g. main+aux exemplars)'''
        self._setSortKeys()
        # create (k, sortkey(k)) for the alphabet from the ducet and from the tailored
        base = sorted([(x, ducetSortKey(self.ducet, x)) for x in alphabet if x in self.ducet], key=lambda x: x[1])
        this = sorted([(x, ducetSortKey(self.ducet, x, extra=self)) for x in alphabet], key=lambda x: x[1])
        # strip down to only primary orders
        basep = filtersame(base, 1)
        thisp = filtersame(this, 1)
        # Remove any non-inserted elements
        self._stripoverlaps(zip(*basep)[0], zip(*thisp)[0])

        # dict[primary] = list of (k, sortkey(k)) with same primary as primary
        bases = makegroupdict(base, lambda x:x[1][0])
        thiss = makegroupdict(this, lambda x:x[1][0])
        for k, v in thiss.items():
            # no subsorting then ignore, if primary is tailored then all subsorts are tailored too
            if len(v) == 1 or k in self:
                continue
            # remove any non-inserted subsorts in the subsequences
            self._stripoverlaps(zip(*bases[k])[0][1:], zip(*v)[0][1:])


class CollElement(object):

    def __init__(self, base, level):
        self.base = base
        self.level = level

    def __repr__(self):
        return ">>>>"[:self.level] + self.base

    def sortkey(self, collations, ducetDict, inc):
        if hasattr(self, 'key'):
            return self.key
        if self.base in collations:
            basekey = copy.deepcopy(collations[self.base].sortkey(collations, ducetDict, inc))
        else:
            basekey = copy.deepcopy(ducetSortKey(ducetDict, self.base))
        basekey[self.level-1][0] += inc
        self.key = basekey
        return basekey

if __name__ == '__main__':
    import sys
    import ducet
    ducetDict = ducet.readDucet()
    coll = Collation(ducetDict)
    if len(sys.argv) > 1:
        coll.parse(sys.argv[1])
        alphabet = "a b c d e f g h i j k l m n o p q r s t u v w x y z".split()
        alphabet += coll.keys()
        coll.minimise(alphabet)
        print coll.asICU()