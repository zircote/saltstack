'''
The client module is used to create a client connection to the publisher
The data structurte needs to be:
    {'enc': 'clear',
     'load': {'fun': '<mod.callable>',
              'arg':, ('arg1', 'arg2', ...),
              'tgt': '<glob or hostname>',
              'key': '<read in the key file>'}
'''
# The components here are simple, and they need to be and stay simple, we
# want a client to have 3 external concerns, and maybe a forth configurable
# option.
# The concers are
# 1. Who executes the command?
# 2. what is the function being run?
# 3. What arguments need to be passed to the function?
# 4. How long do we wait for all of the replies?
#
# Next there are a number of tasks, first we need some kind of authentication
# This Client initially will be the master root client, which will run as the 
# root user on the master server.
# BUT we also want a client to be able to work over the network, so that
# controllers can exist within disperate applicaitons.
# The problem is that this is a security nightmare, so I am going to start
# small, and only start with the ability to execute salt commands locally.
# This means that the primary client to build is, the LocalClient

import os
import re
import glob

# Import zmq modules
import zmq

# Import salt modules
import salt.config
import salt.payload


class SaltClientError(Exception): pass

class LocalClient(object):
    '''
    Connect to the salt master via the local server and via root
    '''
    def __init__(self, c_path='/etc/salt/master'):
        self.opts = salt.config.master_config(c_path)
        self.key = self.__read_master_key()

    def __read_master_key(self):
        '''
        Read in the rotating master authentication key
        '''
        try:
            keyfile = os.path.join(self.opts['cachedir'], '.root_key')
            key = open(keyfile, 'r').read()
            return key
        except:
            raise SaltClientError('Failed to read in the salt root key')

    def check_minions(self, expr, expr_type='glob'):
        '''
        Check the passed glob or regex against the available minions' public
        keys stored for authentication. This should return a set of hostnames
        which match the glob or regex, this will then be used to parse the
        returns to make sure everyone has checked back in.
        '''
        ret = set()
        cwd = os.getcwd()
        os.chdir(os.path.join(self.opts['pki_dir'], 'minions'))
        if expr_type == 'glob':
            ret = set(glob.glob(expr))
        else:
            reg = re.compile(expr)
            for fn_ in os.listdir('.'):
                if reg.match(fn_):
                    ret.add(fn_)
        os.chdir(cwd)
        return ret
            
    def pub(self, tgt, fun, arg=()):
        '''
        Take the required arguemnts and publish the given command.
        Arguments:
            tgt:
                The tgt is a regex or a glob used to match up the hostname on
                the minions. Salt works by always publishing every command to
                all of the minions and then the minions determine if the
                command is for them based on the tgt value.
            fun:
                The function nane to be called on the remote host(s), this must
                be a string in the format "<modulename>.<function name>"
            arg:
                The arg option needs to be a tuple of arguments to pass to the
                calling function, if left blank 
        Returns:
            jid:
                A string, as returned by the publisher, which is the job id,
                this will inform the client where to get the job results
            minions:
                A set, the targets that the tgt passed should match.
        '''
        # Run a check_minions, if no minons match return False
        # format the payload - make a function that does this in the payload
        #   module
        # make the zmq client
        # connect to the req server
        # send!
        # return what we get back
        minions = self.check_minions(tgt)
        if not minions:
            return {'jid': '',
                    'minions': minions}
        package = salt.payload.format_payload('clear',
                cmd='publish',
                tgt=tgt,
                fun=fun,
                arg=arg,
                key=self.key)
        # Prep zmq
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect('tcp://127.0.0.1:' + self.opts['ret_port'])
        socket.send(package)
        payload = salt.payload.unpackage(socket.recv())
        return {'jid': payload['load']['jid'],
                'minions': minions}



