#!/usr/bin/env python
# Copyright 2016 Autodesk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
This is a script that drives the remote computation of a function or instance method.
It's designed to use the pickled objects produced by the PythonJob class

Note:
    This script must be able to run in both Python 2.7 and 3.5+ *without any dependencies*
"""
from __future__ import print_function, unicode_literals, absolute_import, division

import os
import types
import sys
import pickle as cp
import traceback as tb


RENAMETABLE = {'pyccc.python': 'source',
               '__main__': 'source'}


def unpickle_with_remap(fileobj):
    """ This function remaps pickled classnames. It's specifically here to remap the
    "PackagedFunction" class from pyccc to the __main__ module.

    References:
        This was taken without modification from
        https://wiki.python.org/moin/UsingPickle/RenamingModules
    """
    import pickle
    import source

    def mapname(name):
        if name in RENAMETABLE:
            return RENAMETABLE[name]
        return name

    def mapped_load_global(self):
        modname = mapname(self.readline()[:-1])
        name = mapname(self.readline()[:-1])
        try:
            klass = self.find_class(modname, name)
        except ImportError:  # if necessary, create a module and put the class there
            if hasattr(source, name):
                newmod = types.ModuleType(modname)
                sys.modules[modname] = newmod
                setattr(newmod, name, getattr(source, name))
            klass = self.find_class(modname, name)
            klass.__module__ = modname

        self.append(klass)

    unpickler = pickle.Unpickler(fileobj)
    unpickler.dispatch[pickle.GLOBAL] = mapped_load_global
    return unpickler.load()


if __name__ == '__main__':
    import source  # this is the dynamically created source module
    os.environ['IS_PYCCC_JOB'] = '1'
    try:
        # Deserialize and set up the packaged function (see pyccc.python.PackagedFunction)
        with open('function.pkl', 'r') as pf:
            job = unpickle_with_remap(pf)

        if not hasattr(job, 'obj'):  # it's a standalone function
            func = getattr(source, job.__name__)
        else:  # it's an instance method
            func = None

        # Run the function!
        result = job.run(func)

        # Serialize the results
        with open('_function_return.pkl', 'w') as rp:
            cp.dump(result, rp, cp.HIGHEST_PROTOCOL)
        if job.is_imethod:
            with open('_object_state.pkl', 'w') as ofp:
                cp.dump(job.obj, ofp, cp.HIGHEST_PROTOCOL)

    # Catch all exceptions and return them to the client
    except Exception as exc:
        with open('exception.pkl', 'w') as excfile:
            cp.dump(exc, excfile)
        with open('traceback.txt', 'w') as tbfile:
            tb.print_exc(file=tbfile)


