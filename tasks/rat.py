import os
import sys
import shutil
import uuid
import subprocess
import re
import glob

# helper functions
def system(cmd, wd=None):
    '''a wrapper for subprocess.call, which executes cmd in working directory
    wd in a bash shell, returning the exit code.'''
    if wd:
        cmd = ('cd %s && ' % wd) + cmd
    return subprocess.call([cmd], executable='/bin/bash', shell=True)

# main task function
def execute(macro=None, revnumber='HEAD'):
    '''generate monte carlo with rat given a macro and software environment
    
       Keyword arguments:

           macro: uuencoded string of contents of a RAT macro file

           revnumber: RAT revision number, assumed to be installed on the slave
                      with environment source-able with ./env/rat_<number>.sh
    '''
    if macro is None:
        return {'success': False, 'reason': 'no macro provided'}

    # find the appropriate environment script
    env_script = os.path.abspath(os.path.join('env', 'rat_' + revnumber + '.sh'))

    # temporary working directory
    wd = os.path.abspath(str(uuid.uuid4()))
    os.mkdir(wd)
    os.chdir(wd)

    # create macro file and discover output file name
    with open('job.mac', 'w') as f:
        macro_dec = macro.decode('uu')
        f.write(macro_dec)

    match = re.search(r'/rat/proc\soutroot\s/rat/procset\sfile\s"(.+)"', macro_dec)
    if match is None:
        return {'success': False, 'reason': 'unable to determine root output filename'}
    else:
        outroot_file = match.groups(1)

    # run the simulation
    results = {'success': True, 'attachments': []}
    ret = system('source %s && rat job.mac &> /dev/null' % env_script)
    if ret != 0:
        results['success'] = False
        results['reason'] = 'rat failed with error code ' + str(ret)

    # attach results
    logfile = glob.glob('*.log')
    if len(logfile) > 0:
        with open(logfile[0], 'r') as f:
            attachment = {'filename': logfile, 'contents': f.read()}
            attachment['link_name'] = 'RAT Log'
            results['attachments'].append(attachment)

    rootfile = glob.glob('*.root')
    if len(rootfile) > 0:
        with open(rootfile[0], 'r') as f:
            attachment = {'filename': rootfile, 'contents': f.read()}
            attachment['link_name'] = 'ROOT File'
            results['attachments'].append(attachment)

    # delete the working directory
    shutil.rmtree(wd)

    return results

if __name__ == '__channelexec__':
    kwargs = channel.receive()
    results = execute(**kwargs)
    channel.send(results)

if __name__ == '__main__':
    with open(sys.argv[1], 'r') as f:
        print execute(macro=f.read().encode('uu'))

