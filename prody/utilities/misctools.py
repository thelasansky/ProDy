"""This module defines miscellaneous utility functions."""
import re

from numpy import unique, linalg, diag, sqrt, dot, chararray, divide, zeros_like
from numpy import diff, where, insert, nan, isnan, loadtxt, array, round, average
from numpy import sign, arange, asarray, ndarray, subtract, power, sum
from collections import Counter
import numbers

from prody import PY3K

from xml.etree.ElementTree import Element

__all__ = ['Everything', 'Cursor', 'ImageCursor', 'rangeString', 'alnum', 'importLA', 'dictElement',
           'intorfloat', 'startswith', 'showFigure', 'countBytes', 'sqrtm',
           'saxsWater', 'count', 'addEnds', 'copy', 'dictElementLoop', 
           'getDataPath', 'openData', 'chr2', 'toChararray', 'interpY', 'cmp',
           'getValue', 'indentElement', 'isPDB', 'isURL', 'isListLike',
           'getDistance', 'fastin', 'createStringIO', 'div0', 'wmean', 'bin2dec']

CURSORS = []

# Note that the chain id can be blank (space). Examples:
# 3TT1, 3tt1A, 3tt1:A, 3tt1_A, 3tt1-A, 3tt1 A
isPDB = re.compile('^[A-Za-z0-9]{4}[ -_:]{,1}[A-Za-z0-9 ]{,1}$').match

# django url validation regex
isURL = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE).match

class Everything(object):
    """A place for everything."""

    def __contains__(self, what):

        return True

class Cursor(object):
    def __init__(self, ax):
        self.ax = ax
        self.lx = ax.axhline(color='k', linestyle='--', linewidth=0.)  # the horiz line
        self.ly = ax.axvline(color='k', linestyle='--', linewidth=0.)  # the vert line

        # text location in axes coords
        self.txt = ax.text(0., 1., '', transform=ax.transAxes, verticalalignment='bottom')
        
        # preserve the cursor reference
        global CURSORS
        CURSORS.append(self)

    def onClick(self, event):
        from matplotlib.pyplot import draw

        if event.inaxes != self.ax:
            return

        if event.button == 1:
            self.show(event)
        elif event.button == 3:
            self.clear(event)

        draw()

    def show(self, event):
        x, y = event.xdata, event.ydata
        # update the line positions
        self.lx.set_ydata(y)
        self.ly.set_xdata(x)

        self.lx.set_linewidth(.75)
        self.ly.set_linewidth(.75)

        self.txt.set_text('x=%1.2f, y=%1.2f' % (x, y))
        #self.txt.set_position((x, y))

    def clear(self, event):
        self.lx.set_linewidth(0.)
        self.ly.set_linewidth(0.)

        self.txt.set_text('')

class ImageCursor(Cursor):
    def __init__(self, ax, image, atoms=None):
        super(ImageCursor, self).__init__(ax)
        self.image = image
        self.atoms = atoms
    
    def show(self, event):
        x, y = event.xdata, event.ydata
        # update the line positions
        self.lx.set_ydata(y)
        self.ly.set_xdata(x)

        self.lx.set_linewidth(1.)
        self.ly.set_linewidth(1.)

        i, j, v = self.get_cursor_data(event)

        if v > 1e-4 and v < 1e4:
            template = 'x=%d, y=%d [%f]'
        else:
            template = 'x=%d, y=%d [%e]'
        if self.atoms is None:
            self.txt.set_text(template % (j, i, v))
        else:
            seq = self.atoms.getSequence()
            resnums = self.atoms.getResnums()

            a = seq[j] + str(resnums[j])
            b = seq[i] + str(resnums[i])
            self.txt.set_text(template % (a, b, v))
        #self.txt.set_position((x, y))

    def get_cursor_data(self, event):
        """Get the cursor data for a given event"""
        from matplotlib.transforms import Bbox, BboxTransform

        aximg = self.image
        xmin, xmax, ymin, ymax = aximg.get_extent()
        if aximg.origin == 'upper':
            ymin, ymax = ymax, ymin

        arr = aximg.get_array()
        data_extent = Bbox([[ymin, xmin], [ymax, xmax]])
        array_extent = Bbox([[0, 0], arr.shape[:2]])
        trans = BboxTransform(boxin=data_extent, boxout=array_extent)
        y, x = event.ydata, event.xdata
        point = trans.transform_point([y, x])
        if any(isnan(point)):
            return None
        i, j = point.astype(int)
        # Clip the coordinates at array bounds
        if not (0 <= i < arr.shape[0]) or not (0 <= j < arr.shape[1]):
            return None
        else:
            return i, j, arr[i, j]

def rangeString(lint, sep=' ', rng=' to ', exc=False, pos=True):
    """Returns a structured string for a given list of integers.

    :arg lint: integer list or array
    :arg sep: range or number separator
    :arg rng: range symbol
    :arg exc: set **True** if range symbol is exclusive
    :arg pos: only consider zero and positive integers

    .. ipython:: python

       from prody.utilities import rangeString
       lint = [1, 2, 3, 4, 10, 15, 16, 17]
       rangeString(lint)
       rangeString(lint, sep=',', rng='-')
       rangeString(lint, ',', ':', exc=True)"""

    ints = unique(lint)
    if len(ints) == 0:
        return ''
    if pos and ints[0] < 0:
        ints = ints[ints > -1]

    prev = ints[0]
    lint = [[prev]]
    for i in ints[1:]:
        if i - prev > 1:
            lint.append([i])
        else:
            lint[-1].append(i)
        prev = i
    exc = int(exc)
    return sep.join([str(l[0]) if len(l) == 1 else
                     str(l[0]) + rng + str(l[-1] + exc) for l in lint])


def alnum(string, alt='_', trim=False, single=False):
    """Replace non alpha numeric characters with *alt*.  If *trim* is **True**
    remove preceding and trailing *arg* characters.  If *single* is **True**,
    contain only a single joining *alt* character. """

    result = ''
    multi = not bool(single)
    prev = None
    for char in string:
        if char.isalnum():
            result += char
            prev = char
        else:
            if multi or prev != alt:
                result += alt
            prev = alt
    trim = int(bool(trim))
    result = result[trim * (result[0] == alt):
                    len(result) - trim * (result[-1] == alt)]
    return result


def importLA():
    """Returns one of :mod:`scipy.linalg` or :mod:`numpy.linalg`."""

    try:
        import scipy.linalg as linalg
    except ImportError:
        try:
            import numpy.linalg as linalg
        except:
            raise ImportError('scipy.linalg or numpy.linalg is required for '
                              'NMA and structure alignment calculations')
    return linalg

def createStringIO():
    if PY3K:
        from io import StringIO
    else:
        from StringIO import StringIO
    return StringIO()

def dictElement(element, prefix=None, number_multiples=False):
    """Returns a dictionary built from the children of *element*, which must be
    a :class:`xml.etree.ElementTree.Element` instance. Keys of the dictionary
    are *tag* of children without the *prefix*, or namespace. Values depend on
    the content of the child. If a child does not have any children, its text
    attribute is the value. If a child has children, then the child is the
    value.
    """
    
    dict_ = {}
    length = False
    if isinstance(prefix, str):
        length = len(prefix)

    prev_tag = ''
    for child in element:
        tag = child.tag

        if length and tag.startswith(prefix):
            tag = tag[length:]

        if tag != prev_tag:
            prev_tag = tag
            i = 0
        else:
            i += 1

        if number_multiples:
            tag = tag + '{:>4}'.format(str(i))
            
        if len(child) == 0:
            if child.text is None:
                dict_[tag] = child.items()
            else:
                dict_[tag] = child.text
        else:
            dict_[tag] = child

    return dict_

def dictElementLoop(dict_, keys=None, prefix=None, number_multiples=False):

    if isinstance(keys, str):
        keys = [keys]

    if not keys:
        keys = dict_.keys()

    for orig_key in keys:
        item = dict_[orig_key]
        if isinstance(item, Element):
            dict2 = dictElement(dict_[orig_key], prefix, number_multiples)
            finished = False
            while not finished:
                dict3 = dict2.copy()
                try:
                    key = dict2.keys()[0]
                    dict2[key] = dictElement(dict2[key], prefix, number_multiples)
                except:
                    finished = True
                else:
                    dict2 = dict3
                    for key in dict2.keys():
                        dict2[key] = dictElement(dict2[key], prefix, number_multiples)

            dict_[orig_key] = dict2

    return dict_

def intorfloat(x):
    """Returns ``int(x)``, or ``float(x)`` upon :exc:`ValueError`."""

    try:
        return int(x)
    except ValueError:
        return float(x)


def startswith(this, that):
    """Returns **True** if *this* or *that* starts with the other."""

    if len(this) < len(that):
        return that.startswith(this)
    else:
        return this.startswith(that)


def showFigure():
    """Call :func:`~matplotlib.pyplot.show` function with ``block=False``
    argument to avoid blocking behavior in non-interactive sessions.  If
    *block* keyword argument is not recognized, try again without it."""

    from matplotlib.pyplot import show
    try:
        show(block=False)
    except TypeError:
        show()


def countBytes(arrays, base=False):
    """Returns total number of bytes consumed by elements of arrays.  If
    *base* is **True**, use number of bytes from the base array."""

    if base:
        getbase = lambda arr: arr if arr.base is None else getbase(arr.base)
        nbytes = lambda arr: getbase(arr).nbytes
    else:
        nbytes = lambda arr: arr.nbytes

    return sum(nbytes(arr) for arr in arrays)

def sqrtm(matrix):
    """Returns the square root of a matrix."""
    (U,S,VT)=linalg.svd(matrix)
    D = diag(sqrt(S))
    return dot(dot(U,D),VT)

def getMasses(elements):
    """Gets the mass atom. """
    
    import numpy as np
    mass_dict = {'C':12,'N':14,'S':32,'O':16,'H':1}

    if isinstance(elements, str):
        return mass_dict[elements]
    else:
        masses = np.zeros(len(elements))
        for i,element in enumerate(elements):
            if element in mass_dict:
                masses[i] = mass_dict[element]
            else:
                masses[i] = 0.
        return masses

def count(L, a=None):
    return len([b for b in L if b is a])

def addEnds(x, y, axis=0):
    """Finds breaks in *x*, extends them by one position and adds **nan** at the 
    corresponding position in *y*. *x* needs to be an 1-D array, *y* can be a 
    matrix of column (or row) vectors"""

    d = diff(x)
    counter = Counter(d)
    step = counter.most_common(1)[0][0]

    breaks = where(d != step)[0]
    for b in reversed(breaks):
        x = insert(x, b+1, x[b]+step)
        y = insert(y, b+1, nan, axis=axis)

    return x, y

def copy(x):
    if x is None:
        return None
    return x.copy()

def getDataPath(filename):
    import pkg_resources
    return pkg_resources.resource_filename('prody.utilities', 'datafiles/%s'%filename)

def openData(filename, mode='r'):
    return open(getDataPath(filename), mode)

def saxsWater():
    filename = getDataPath('saxs_water.dat')
    return loadtxt(filename, delimiter=',')

def chr2(a):
    try:
        c = chr(a)
    except TypeError:
        c = str(a)
    return c

def toChararray(arr, aligned=False):
    arr = array(arr, dtype='|S')
    try:
        ndim, dtype_, shape = arr.ndim, arr.dtype, arr.shape
    except AttributeError:
        raise TypeError('arr is not a Numpy array')

    if ndim < 1:
        raise ValueError('arr.ndim should be at least 1')
    if dtype_.char != 'S':
        raise ValueError('arr must be a character array')

    if ndim != 2:
        n_seq = shape[0]
        l_seq = dtype_.itemsize
        new_arr = chararray((n_seq, l_seq))
        for i, s in enumerate(arr):
            for j in range(l_seq):
                if j < len(s):
                    new_arr[i, j] = chr2(s[j])
                else:
                    if aligned:
                        raise ValueError('arr does not the same lengths')
                    new_arr[i, j] = '.'
    else:
        new_arr = array(arr, dtype='|S1')
    return new_arr

def interpY(Y):
    Y = asarray(Y, dtype=float)
    n = len(Y)
    X = arange(n)

    dy = (Y.max() - Y.min()) / n

    Xp = [X[0]]; Yp = [Y[0]]
    for i in range(n-1):
        y1, y2 = Y[i], Y[i+1]
        x1, x2 = X[i], X[i+1]
        if abs(y2 - y1) > dy:
            sdy = sign(y2 - y1)*dy
            yp = arange(Y[i]+sdy, Y[i+1], sdy)
            xp = (yp - y1)/(y2 - y1)*(x2 - x1) + x1
            Xp.extend(xp)
            Yp.extend(yp)

        Xp.append(x2)
        Yp.append(y2)
    return array(Xp), array(Yp)

def cmp(a, b):
    return (a > b) - (a < b)

def getValue(dict_, attr, default=None):
    value = default
    if attr in dict_:
        value = dict_[attr]
        if default is not None:
            try:
                if value.ndim == 0:
                    value = type(default)(value)
            except:
                pass
    return value

def indentElement(elem, level=0):
    i = "\n" + level*"  "
    j = "\n" + (level-1)*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for subelem in elem:
            indentElement(subelem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = j
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = j
    return elem 

def isListLike(a):
    return isinstance(a, (list, tuple, ndarray))

def getDistance(coords1, coords2, unitcell=None):

    diff = coords1 - coords2
    if unitcell is not None:
        diff = subtract(diff, round(diff/unitcell)*unitcell, diff)
    return sqrt(power(diff, 2, diff).sum(axis=-1))

def fastin(a, B):
    for b in reversed(B):
        if a is b:
            return True
    return False

def div0(a, b):
    """ Performs ``true_divide`` but ignores the error when division by zero 
    (result is set to zero instead). """

    from numpy import errstate, true_divide, isfinite, isscalar
    
    with errstate(divide='ignore', invalid='ignore'):
        c = true_divide(a, b)
        if isscalar(c):
            if not isfinite(c):
                c = 0
        else:
            c[~isfinite(c)] = 0.  # -inf inf NaN
    return c

def wmean(array, weights, axis=None):
    """Calculates the weighted average of *array* given *axis*."""

    try:
        avg = average(array, axis=axis, weights=weights)
    except ZeroDivisionError:
        numer = sum(array*weights, axis=axis)
        denom = sum(weights, axis=axis)
        avg = div0(numer, denom)
    return avg

def bin2dec(x):
    """Converts the binary array to decimal."""

    y = 0
    for i,j in enumerate(x):
        if j: y += 1<<i
    return y
