
--------------------------------------------------------------------------------
                       PYTHON 3 PORTING INSTRUCTIONS
--------------------------------------------------------------------------------

1. Install pip for python 3: apt-get install python3-pip

2. Install katcp(+future+tornado) for python 3: sudo pip3 install katcp

3. Install 2to3 : sudo apt-get install 2to3

4. Use 2to3 to upgrade obsolete python2 code: 2to3 nonsense.py

5. Rename instances of thread module from 'thread' to '_thread' for python3 compatibility
