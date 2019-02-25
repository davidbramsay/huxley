# Written by Bo Yang
# https://github.com/bo-yang/misc/blob/master/run_command_timeout.py

import subprocess
import threading

""" Run system commands with timeout
"""
class Command(object):
    def __init__(self, cmd):
        self.cmd = cmd
        self.process = None
        self.out = "TIMEOUT"

    def run_command(self, capture = False):
        if not capture:
            self.process = subprocess.Popen(self.cmd,shell=True)
            self.process.communicate()
            return
        # capturing the outputs of shell commands
        self.process = subprocess.Popen(self.cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=subprocess.PIPE)
        out,err = self.process.communicate()
        if len(out) > 0:
            self.out = out.splitlines()
        else:
            self.out = None

    # set default timeout to 2 minutes
    def run(self, capture = False, timeout = 120):
        thread = threading.Thread(target=self.run_command, args=(capture,))
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            print 'Command timeout, kill it: ' + self.cmd
            self.process.terminate()
            thread.join()
            return False
        return True


if __name__=='__main__':

    for i in range(3): #three tries
        s = 3-i
        r = Command('echo "sleep ' + str(s) + ' seconds"; sleep ' + str(s) + '; echo "done"').run(timeout=2)
        print r
        if r:
            print 'success attempt ' + str(i+1)
            break
        else:
            print 'failed. trying again...'
