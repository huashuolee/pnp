#!/usr/bin/python
# -*- encoding = utf8 -*-

import time

# msg_type : E (Error) | A (Attention and Warning) | M (Message) | F (Function Call) | C (Class Initialize) | D (Debug)
def print_msg(msg_type, msg_content) :
    type_dict = {'E':'Error', 'A':'Attention', 'M':'Message', 'F':'Function','C':'Class', 'D':'Debug'}
    timestamp = time.strftime('%H:%M:%S',time.localtime(time.time()))
    if msg_type == 'E' :
        print "\033[1;31;40mXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
        print "[ %-10s] %s"%(type_dict[msg_type], timestamp)
        print "\t%s"%msg_content
        print "XXXXXXXXXXXXXXXXXXXXXXXXXXXX\033[0m"
    elif msg_type == 'A':
        print "\033[1;33;40m----------------------------"
        print "[ %-10s] %s"%(type_dict[msg_type], timestamp)
        print "\t%s"%msg_content
        print "----------------------------\033[0m"
    elif msg_type == 'M':
        print "\033[1;32;40m[ %-10s] %s %s"%(type_dict[msg_type], timestamp, msg_content),"\033[0m"
    elif msg_type == 'F':
        #print "\033[1;36;40m[ %-10s] %s %s"%(type_dict[msg_type], timestamp, msg_content),"\033[0m"
        print "[ %-10s] %s %s"%(type_dict[msg_type], timestamp, msg_content)
    elif msg_type == 'C':
        print "\033[1;35;40m[ %-10s] %s %s"%(type_dict[msg_type], timestamp, msg_content),"\033[0m"
    elif msg_type == 'D':
        print "\033[1;31;40m[ %-10s] %s %s"%(type_dict[msg_type], timestamp, msg_content),"\033[0m"
    else :
        print "[ %-10s] %s %s"%(type_dict[msg_type], timestamp, msg_content)


if __name__ == '__main__'  :
    print_msg('E','Errors')
    print_msg('A','Pay attention to Warning')
    print_msg('M','Hello world')
    print_msg('F','Function Call')
    print_msg('C','Class Initialize')
    print_msg('A','''
            Hello world
            Baidu
            Narutom.com
            ''')
