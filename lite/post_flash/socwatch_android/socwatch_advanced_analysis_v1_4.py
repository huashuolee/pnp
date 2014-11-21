#!/usr/bin/python

#****************************************************************************
#                         INTEL CONFIDENTIAL
#
# Copyright 2009-2012 Intel Corporation All Rights Reserved.
#
# This file is provided for internal use only. You are free to modify it
# for your own internal purposes, but you cannot release it to the external
# open source community under any circumstances without SSG.DPD's approval.
#
# If you make significant improvements, fix bugs, or have suggestions for
# additional features or improvements, please provide your changes to
# Robert or Hrabri for inclusion in this tool.
#
# Please contact Robert Knight (robert.knight@intel.com) or Hrabri Rajic
# (hrabri.rajic@intel.com) if you have any questions.
#
#*****************************************************************************

import getopt
import sys, re
import os.path
import math
from   operator import itemgetter
from   time import strftime
from   collections import namedtuple

debug = 0
IRQ = 'IRQ'
TIMER = 'PID'
show_promotion=0
percore = 0
txt = 0 
csv = 0
current_core = 0
current_core_c0 = 0
core = 0
core_c0 = 0
integrity = 0
previous_sample_TSC = 0
wakelock = 0
test = 0

def usage():
        print '\nThis application gives a statistical summary of the data collected by socwatch.\n'
        print 'USAGE:'
        print '    COMMAND -f |--file [socwatch-output-file]  <Optional Arguments>'
        print 'Optional Arguments:\n'
        print '-h|--help: Print this help message.\n'
        print '-w|--wakelock: Print wakelock tables.\n'
        print '-c|--core: Additionally print all data per core.\n'
        print '--csv: Print data in csv format. By default advanced_analysis.csv will be created in the current directory. Alternate output file path may be specified using the -o option.\n'
        print '--txt: Print data in text format. By default advanced_analysis.txt will be created in the current directory. Alternate output file path may be specified using the -o option.\n'
        print '-o|--output-file [output file]: Create the specified summary o/p files. The directory path will be created if not found.\n'
        #print '-t|--time [time slice in miliseconds]: Use this time slice value for wakeups timeline(Default=1000 msec).'
        print '\nNote* If neither file format(csv/txt) is specified the script defaults to dumping the data to console.\n'
        print '\n\n'
        print 'Sample Command: advanced_SOCWatch_analysis.py -f socwatch_file.txt --txt -o socwatch_summary'
        print 'The above command dumps a text summary output file called socwatch_summary.txt in the current directory.'
        print '\n\n'

####################################################################################################################3
#
# This class is used for making composite key for Wakelocks, so different tags could be separated from the same process ID.


CompositeWakelockKeyBase = namedtuple("CompositeWakelockKeyBase", ["uid", "lockTag"])
class CompositeWakelockKey(CompositeWakelockKeyBase):
    def __new__(cls, uid, lockTag):
        obj = CompositeWakelockKeyBase.__new__(cls, uid, lockTag)
        return obj


####################################################################################################################3

# This class holds the general details of the system on which the power analysis was performed .
# The information is read from the wudump output file supplied as CL argument

class generalSystemDetailsClass:

    """
    This dictionary data structure holds the residency thresholds in units of 1000 corresponding to a particular state.
    These threshold values are used to calculate bad sleep state transition decisions .
    Map format [state -> (lower threshold,upper threshold)]
    """
    m_lower_upper_thresholds_map_C = dict()
    m_logical_cpu_count    = 0       #Number of CPU's on the system , as read from wudump
    m_core_count           = 0
    m_deepest_state        = 0       #The deepest sleep state found on the system, as read from wudump 
    m_collection_time      = 0.0    
    m_summary_data_version = 2.0
    
    m_system_frequency = 0            #system frequency in MHz 
    m_collection_start_tsc = 0        # Boundary TSC values for the collection
    m_collection_end_tsc   = 0

    #The entire collection run is divided into slices to generate a wucount timeline
    #Each such slice is made of 'time_slice' number of miliseconds.
    m_time_slice_msec       = 1000
    m_cycles_per_time_slice = 0

    #input and output files
    m_output_dir = os.curdir
    m_wudump_input_file = ""
    m_output_summary_text_file   = "advanced_analysis.txt"
    m_output_summary_tl_csv_file = "advanced_analysis.csv"
    m_output_integrity_csv_file  = "integrity.csv"

    m_sleep_states = list()
    
    def getPlatformDetailsFromWudump(self):

        global debug,utility_functions,IRQ ,TIMER

        #read the wudump o/p file to get the required information here
        try:
            fdtemp = open(self.m_wudump_input_file)
        except IOError: 
            print 'File not found: ', self.m_wudump_input_file
            sys.exit()

        if debug:
            print 'Inputfile = ' + self.m_wudump_input_file
            
        cstateheaderfound = 0
        foundTargetResidencies  = 0   
        line = ''
        for line in fdtemp:

            if line.strip().startswith("Number of Cores"):
                index = -1
                tuples = line.rpartition('=')
                try:
                    self.m_core_count = int(tuples[2].strip())
                except ValueError:
                    print 'Failed to read cpu count from file ',self.m_wudump_input_file,' Exiting !'
                    fdtemp.close()
                    sys.exit()
                    
                if debug:    
                    print 'Core Count = ',self.m_core_count

                
            if line.strip().startswith("Number of Logical CPU's"):
                index = -1
                tuples = line.rpartition('=')
                try:
                    self.m_logical_cpu_count = int(tuples[2].strip())
                except ValueError:
                    print 'Failed to read cpu count from file ',self.m_wudump_input_file,' Exiting !'
                    fdtemp.close()
                    sys.exit()
                    
                if debug:    
                    print 'CPU Count = ',self.m_logical_cpu_count
                
            if line.strip().startswith("Processor C-States"):
                index = -1
                index = line.rfind("C");
                if index == -1:
                    print "Error ! Deepest Processor State value not found. Exiting."
                    fdtemp.close()
                    sys.exit()
                self.m_deepest_state = (line[index + 1])
                if debug:
                    print 'Deepest State = ' , self.m_deepest_state

            if line.strip().startswith("TSC Frequency (MHz) ="):
                index = -1

                tuples = line.rpartition('=')
                try:
                    self.m_system_frequency = float(tuples[2].strip())
                    self.m_system_frequency *= 1000000
                except ValueError:
                    print 'Failed to read system frequency from file ',self.m_wudump_input_file,' Exiting !'
                    fdtemp.close()
                    sys.exit()
                
                if debug:    
                    print 'system frequency = ',self.m_system_frequency

            if line.strip().startswith("Collection start TSC value"):
                tuples = line.partition('=')
                try:
                    self.m_collection_start_tsc = long(tuples[2])
                except ValueError:
                   print 'Failed to read Collection start TSC value from file ',self.m_wudump_input_file,' Exiting !'
                   fdtemp.close()
                   sys.exit()
                
                
            if line.strip().startswith("Collection stop TSC value"):
                tuples = line.partition('=')
                try:
                    self.m_collection_end_tsc = long(tuples[2])
                except ValueError:
                    print 'Failed to read Collection end TSC value from file ',self.m_wudump_input_file,' Exiting !'
                    fdtemp.close()
                    sys.exit()
             
            if line.strip().startswith("TARGET RESIDENCIES"):
                index = -1

                line = fdtemp.next();
                prev = 0
                while(line.startswith('C')):

                    if foundTargetResidencies  == 0:
                        foundTargetResidencies =  1
                   
                    state = 0
                    residency = 0
                    tuples = line.rpartition('=')
                   
                    try:
                        state     = ((tuples[0].lstrip('C')).strip())    
                        residency = long((tuples[2].rstrip('\n')).strip())
                        
                        #skip if state is 5
                        if state == 5:
                                line = fdtemp.next()
                                continue
                        
                        self.m_lower_upper_thresholds_map_C[state] = [residency, 0]
                        #Create the breakeven buckets for the intermediate C states
                        self.m_lower_upper_thresholds_map_C[state + 'i'] = [residency, 0]
                        curr  =  state
                        if (prev != 0):
                            self.m_lower_upper_thresholds_map_C[prev][1] = residency
                            #Create the breakeven buckets for the intermediate C states (1.5, 2.5 etc.)
                            self.m_lower_upper_thresholds_map_C[prev + 'i'][1] = residency
                        prev = state
                    except ValueError:
                        print 'Failed to read system residencies from file ', self.m_wudump_input_file, ' Exiting !'
                        fdtemp.close()
                        sys.exit()
                    line = fdtemp.next()

                self.m_lower_upper_thresholds_map_C[prev][1] = 10000000000
                               
                if debug:    
                    print 'Thresholds: ',self.m_lower_upper_thresholds_map_C

            if line.strip().startswith("Total"):
                parsed = line.strip().split()
                if len(parsed) == 6 and parsed[0] == "Total" and parsed[1] == "Collection":
                    self.m_collection_time = float(parsed[4])
                    self.m_collection_time = (self.m_collection_time * 1.0 )
                    if debug:
                        print 'Collection Run Time = ' , self.m_collection_time

                else:
                    print "Error ! Collection time could not be found.Exiting."
                    fdtemp.close()
                    sys.exit()

            #Check for the validity of the input file , if header not found , wudump file is in incorrect format. Exit.

            if line.strip().startswith("TSC"):
                parsed = line.strip().split()
                if(len(parsed) == 16 and parsed[0] ==  "TSC" and parsed[1] == "ID" and parsed[4] == "C-STATE"
                                  and parsed[5] == "C-STATE" and parsed[6] == "(clock" and parsed[7] == "ticks)"
                                  and parsed[8] == "EVENT" and parsed[9] == "CPU" and parsed[10] == "TID"
                                  and parsed[11] == "PID" and parsed[12] == "IRQ" and parsed[13] == "(MHz)" and parsed[14] == "Additional"):
                    cstateheaderfound = 1
                    break      

        if cstateheaderfound == 1:
             #Error Checking
            if  foundTargetResidencies == 0 :
                print 'Failed to parse the target residencies: Incorrect File Format!' ,self.m_wudump_input_file
                fdtemp.close()
                sys.exit()       
            if self.m_logical_cpu_count <= 0:             
                    print 'Error in wudump metadata parser. CPU Count value error ', self.m_logical_cpu_count
                    fdtemp.close()
                    sys.exit()
            if self.m_core_count <= 0:
                    print 'Error in wudump metadata parser. Core Count value Error ', self.m_core_count
                    fdtemp.close()
                    sys.exit()
            if self.m_collection_time <= 0.0:
                    print 'Error in wudump metadata parser. Collection Time error', self.m_collection_time
                    fdtemp.close()
                    sys.exit()
            if self.m_system_frequency <= 0.0:
                    print 'Error in wudump metadata parser. System frequency value error', self.m_system_frequency
                    fdtemp.close()
                    sys.exit()
            if self.m_deepest_state <= 0:
                    print 'Error in wudump metadata parser. Deepest sleep state value error', self. m_deepest_state
                    fdtemp.close()
                    sys.exit()
            if self.m_collection_start_tsc <= 0 or self.m_collection_end_tsc <= 0:
                    print 'Error in wudump metadata parser. Collection start/stop TSC is invalid.', self.m_collection_start_tsc , ':', self.m_collection_end_tsc
                    fdtemp.close()
                    sys.exit() 
                
        #msec -> Hz/1000
        frequency_in_khz = self.m_system_frequency/1000
        self.m_cycles_per_time_slice = int((frequency_in_khz) * self.m_time_slice_msec) #every time slice is made of these many cycles
        # To support hyper threading sitautaion, we assume that the max number of cpu is 2*core_count
        # Currently there are only 2 threads per core <Assumption>
        self.m_logical_cpu_count = 2*self.m_core_count
        
####################################################################################################################################################
# class to hold wakelock infomation
#We use a map of PID->list of wl objects

def createWLBuckets():

    wl_bucket_map = dict()    
    wl_bucket_map[0]     = resBuckets(0,1)
    wl_bucket_map[1]     = resBuckets(1,5)
    wl_bucket_map[5]     = resBuckets(5,30)
    wl_bucket_map[30]    = resBuckets(30,50)
    wl_bucket_map[50]    = resBuckets(50,100)
    wl_bucket_map[100]   = resBuckets(100,500)
    wl_bucket_map[500]   = resBuckets(500,1000)
    wl_bucket_map[1000]  = resBuckets(1000,5000)
    wl_bucket_map[5000]  = resBuckets(5000,15000)
    wl_bucket_map[15000] = resBuckets(15000,-1)

    return wl_bucket_map


def incrementWLBuckets(wl_bucket_map, lock_duration):

    for key in sorted(wl_bucket_map.iterkeys()):      
        value = wl_bucket_map[key]
        
        #upper threshold for highest bucket is set as -1
        #if the rescount is greater than lowerbound and less than upper bound , bucket found !
        if value.m_range_upperbound != -1 and (lock_duration >= value.m_range_lowerbound and lock_duration < value.m_range_upperbound):
            value.updateBucket(lock_duration, 0)        
            return
        #This is the case when the res count lies in the highes bucket
        elif value.m_range_upperbound == -1 and lock_duration >= value.m_range_lowerbound:
            value.updateBucket(lock_duration, 0)       
            return
            
    print'Error! residency count does not lie in any bucket. ', rescount_msec
    sys.exit()

def addProcessToWakelockDict(wakelock_dict, uid_tag, wakelock_bucket_dict, name, pid, tid, lock_type, tsc, pname, wl_tag='', wl_flag='', timeout_tsc=0):

    wakelock_dict[uid_tag] = list()
    wakelock_dict[uid_tag].append(Wakelock(name, tid, lock_type, tsc, pname, wl_tag, wl_flag, timeout_tsc))
    if wakelock_bucket_dict != None:
        wakelock_bucket_dict[uid_tag] = createWLBuckets()

non_overlapping_lock_time_per_process = dict()
def calculate_non_overlapping_lock_time (wl_nonoverlapping_time_dict, sys_info):

    for uid_tag, lock_list in wl_nonoverlapping_time_dict.items():
        index = 0
        lock_list = sorted(lock_list,  key=lambda x:x[0])
        while index < (len(lock_list ) -1):            
            if lock_list [index+1][0] < lock_list [index][1]: #start of next element is lower than end of currenmt => overlapping
                if lock_list [index][1] < lock_list [index+1][1]:
                    lock_list [index][1] = lock_list [index+1][1]
                del lock_list [index + 1]
            else:
                index += 1
        wl_nonoverlapping_time_dict[uid_tag] = lock_list
            

    for uid_tag, lock_list in wl_nonoverlapping_time_dict.items():
        total_time = 0
        index = 0
        while index < len(lock_list):
            total_time += utility_functions.getCountinMiliseconds((long(lock_list[index][1]) - long(lock_list[index][0])), sys_info)
            index += 1
        non_overlapping_lock_time_per_process[uid_tag] = total_time
        

#wakelock_bucket_dict
class Wakelock:

    def __init__(self, name, TID, lock_type, tsc, pname="-", wl_tag='', wl_flag='', timeout_tsc=0):

        self.m_WL_name = name
        self.m_WL_TID = TID
        self.m_pname  = pname 
        self.m_lock_type = lock_type
        self.m_lock_tsc   = 0
        self.m_unlock_tsc = 0
        self.m_unlock_process = ''
        self.m_timeout_tsc = timeout_tsc
        self.m_wl_tag = wl_tag
        self.m_wl_flag = wl_flag
        
        if lock_type == "UNLOCK":
            self.m_unlock_tsc = tsc
        elif lock_type == "LOCK":
            self.m_lock_tsc = tsc

        self.m_lock_hold_time = 0 
                

    def calculateWLHoldTimeMsec(self, sys_info, lock_state):

        if(lock_state == "LOCK"):
            self.m_unlock_tsc = sys_info.m_collection_end_tsc          
        elif(lock_state == "UNLOCK"):
            self.m_lock_tsc = sys_info.m_collection_start_tsc          

        self.m_lock_hold_time += utility_functions.getCountinMiliseconds((long(self.m_unlock_tsc) - long(self.m_lock_tsc)), sys_info)
    
####################################################################################################################################################
# This class represents a residency bucket
# Each resideny bucket is a range of time , within which a sleep state residency may lie .

class resBuckets:
    
    def __init__(self,range_lb,range_ub,state=0):
            
        self.m_range_lowerbound = range_lb    #lower bound for the bucket , in msec
        self.m_range_upperbound = range_ub    #upper bound for the bucket , in msec 
        self.m_idle_rescount_msec   = 0       #cumulative residency count in msec , for all sleeps which lie in this bucket range
        self.m_hit_count    = 0               #represents the number of times a sleep state fell betweent this bucket range
        self.m_active_count = 0               #for future use
        self.m_active_hit_count = 0
        self.m_bucket_C_state = state
        
    #updates information for a bucket 
    def updateBucket(self, rescount_msec, activecount=0):
            
        self.m_idle_rescount_msec += rescount_msec
        self.m_hit_count += 1
        self.m_active_count += activecount

    def updateBucketActiveHitCount(self):

        self.m_active_hit_count += 1

###################################################################################################################################################
#This class represents each Sleep State and stores its corresponding residency information.
#
class residencyInformationClass:
    
    def __init__(self, sleep_state, res_count, intermediateState=False):
        self.m_sleep_state = sleep_state            #Sleep state number , C1-Cx
        self.m_sleep_state_hit_count = 0
        
        if intermediateState == False:
            self.m_sleep_state_hit_count = 1            #The number os times this state was entered

        #this dictionary stores the counts of wakeups caused by different events in this particular sleep state
        #e.g. C0 was woken up by timers 25 times and IRQ 50 times and so on
        self.m_wakeup_specific_hit_count = dict()          
        self.m_wakeup_specific_hit_count['Timer'] = 0
        self.m_wakeup_specific_hit_count['IRQ']   = 0
        self.m_wakeup_specific_hit_count['IPI']   = 0
        self.m_wakeup_specific_hit_count['Unknown'] = 0
        self.m_wakeup_specific_hit_count['WQExec']  = 0
        self.m_wakeup_specific_hit_count['Scheduler'] = 0
    
        self.m_res_count = res_count                #The cumulative residency count for the sleep state
        self.m_lower_threshold_count = 0            #The number of times  when , res_count was lower than lower threshold for the sleep state (to calculate power lost metric)
        self.m_upper_threshold_count = 0            #The number of times when  , res_count was higher than upper threshold for the sleep state (to calculate oppurtunity lost metric)
        self.m_lower_threshold_rescount = 0         #This is the power wasted residency counts
        self.m_upper_threshold_rescount = 0         #This is the oppurtunity lost residency counts
        

    def updateResidencyInfoMap(self, res_count, core, break_type, state, intermediateState= False):
        
        self.m_res_count += res_count

        if intermediateState == False:
            self.m_sleep_state_hit_count += 1                    #update occurrence count for this state by 1

        #ignore C0 as it is not a wakeup
        if state !='0' and intermediateState == False:
            self.m_wakeup_specific_hit_count[break_type] += 1

    # Calculate power wasted % , (number of times when res < l_threashold )/number of times sleep state was entered       
    def powerWastedPercentage(self):
        return utility_functions.getPercentage(self.m_lower_threshold_count, self.m_sleep_state_hit_count)
    
    # Calculate power wasted % , (number of times when res > u_threashold )/number of times sleep state was entered       
    def oppurtunityLostPercentage(self, key, WakeUpDetailsObject):

        sleep_state_hit_count = 0

        if (isIntermediateState(key) == True):
            try:
                sleep_state_hit_count = self.m_sleep_state_hit_count + WakeUpDetailsObject.m_intermediate_sample_count[(key)]
            except:
                sleep_state_hit_count = self.m_sleep_state_hit_count
        else:
            sleep_state_hit_count = self.m_sleep_state_hit_count
                
        return utility_functions.getPercentage(self.m_upper_threshold_count, sleep_state_hit_count)

    def updatePowerMetrics(self, res_count, system_info, power_wastage_type ):

        if power_wastage_type == 'Pwasted':
            self.m_lower_threshold_count += 1
            self.m_lower_threshold_rescount += res_count

        if power_wastage_type == 'Olost':
            self.m_upper_threshold_count += 1
            self.m_upper_threshold_rescount += res_count
         
    def updatePowerWastedResidencyCount(self, system_info):
        pass
    def updateoppurtunityLostResidencyCount(self, system_info):
        pass
    
#######################################################################################################################################

#This class represents each wakeup event such as  process/irq  and stores detailed information aout that wakeup event
class wakeupTypesInformationClass:
    
    def __init__(self, wakeup_type, name, res_count, state, core, system_info, my_wu_handler_cpu):
        
        self.m_name  = name                           #Process name / IRQ name
        self.m_type = wakeup_type                     #Type of wakeup : IRQ/Timer/unknown/IPI
        self.m_wakeup_count = 1                       #Total count of wakeups caused by this event
       
        self.m_idle_count = res_count                 #cumulative residency count for this event
        self.m_active_count = 0                       #cumulative active state residency count for this event , the residency count of the C0 following this wakeup is considered active count for this event.
        self.m_my_cpu_list = list()                   #List of CPU's on which this event has occurred

        self.m_state_specific_wakeup_count = dict()   #Wakeups caused by this event per c states such as C1 ,C2 etc  MAPP[ STATE -> COUNT ]
        self.m_state_specific_wakeup_count[state] = 1 #Update the wakeup for the current sample
        
        self.m_res_bucket_map = dict()                #Create residency bucket map for every wakeup event.
        self.createBuckets(system_info)
        
        self.m_fist_sighting_tsc = 0                  #TSC value when the wakeup event first occcurred.
        self.m_last_sighting_tsc = 0                  #TSC value when the wakeup event last occcurred. These TSC values are used to calculate the Trace Coverage for the event.
        

        #Add an entry for each cpu , initially each values is set to 0
        #For every sighting the count for that cpu is incermented by 1
        i = 0
        
        while i < system_info.m_logical_cpu_count:
            self.m_my_cpu_list.insert(i,0)
            i += 1
        
        self.m_my_cpu_list[ my_wu_handler_cpu] += 1
              
    def updateMyInfo(self, core, res_count, cpu ):
        
        self.m_wakeup_count += 1
        self.m_my_cpu_list[cpu] += 1
        self.m_idle_count +=  res_count
       
    def updateActiveCount(self, active_count):

        self.m_active_count += active_count
        active_bucket_id = self.findMybucket(active_count)
        self.m_res_bucket_map[active_bucket_id].updateBucketActiveHitCount()

    #return the wakeups per state information
    def get_wakeup_count_by_state(self, state):
        
        if state in self.m_state_specific_wakeup_count:
            return self.m_state_specific_wakeup_count[state]
        else:
            return 0

    #Claculate the trace coverage for this wakeup event 
    def getTraceCoverage(self, sys_info):

        #Find differene in in TSC between the last and first occurrence of this wakeup
        diff_tsc = int(self.m_last_sighting_tsc) - int(self.m_first_sighting_tsc) 
        #Convert the tsc difference into a time value (seconds)
        diff_tsc = utility_functions.getCountinMiliseconds(diff_tsc, sys_info)
        diff_tsc = ((diff_tsc * 1.0)/1000)

        #Trace coverage is calculated as diff/total collection time 
        return utility_functions.getPercentage(diff_tsc, sys_info.m_collection_time)
     
    #return the cpu list for this wakeup event as a string 
    def get_cpu_list(self):
        i = 0
        #if entry for a cpu is > 0 update the string with that cpu number
        my_cpu_string = ''
        while i < len(self.m_my_cpu_list):
            if self.m_my_cpu_list[i] != 0:
                my_cpu_string += str(i) + '+'
            i += 1
        return my_cpu_string.rstrip('+') 

    #wakeup events have their own specific buckets
    def createBuckets(self, sys_info):
    
        #add all the bucket ranges you need to this dictionary
        #insert lowerbound as the key
        #self.m_lower_upper_thresholds_map_C[state]    
        #time unit used : miliseconds
        #We need to create buckets based on the target residencies for the different sleep states available
        index = 0
        for state in sorted(sys_info.m_lower_upper_thresholds_map_C.iterkeys()):

                if (state.rfind('i') == -1):
                    lower_bound_usec = round((utility_functions.getCountinMiliseconds(sys_info.m_lower_upper_thresholds_map_C[state][0] , sys_info)), 5)            
                    upper_bound_usec = round((utility_functions.getCountinMiliseconds(sys_info.m_lower_upper_thresholds_map_C[state][1] , sys_info)), 5)
                    if index == 0:
                            self.m_res_bucket_map[0] = resBuckets(0, upper_bound_usec, state )
                            index += 1
                            continue
                    
                    if state == sys_info.m_deepest_state:
                            self.m_res_bucket_map[lower_bound_usec] = resBuckets(lower_bound_usec, 1, int(state))
                    else:
                            self.m_res_bucket_map[lower_bound_usec] = resBuckets(lower_bound_usec, upper_bound_usec, int(state))
                    index += 1
        
        self.m_res_bucket_map[1]    = resBuckets(1,5)
        self.m_res_bucket_map[5]    = resBuckets(5,10)
        self.m_res_bucket_map[10]   = resBuckets(10,30)
        self.m_res_bucket_map[30]   = resBuckets(30,50)
        self.m_res_bucket_map[50]   = resBuckets(50,100)
        self.m_res_bucket_map[100]  = resBuckets(100,200)
        self.m_res_bucket_map[200]  = resBuckets(200,500)
        self.m_res_bucket_map[500]  = resBuckets(500,1000)
        self.m_res_bucket_map[1000] = resBuckets(1000,5000)
        self.m_res_bucket_map[5000] = resBuckets(5000,-1)
        
    #Find the bucket within which a residency count value for a wakeup resides
    def findMybucket(self, rescount_msec):
       
        for key in sorted(self.m_res_bucket_map.iterkeys()):      
            value = self.m_res_bucket_map[key]
            #upper threshold for highest bucket is set as -1
            #if the rescount is greater than lowerbound and less than upper bound , bucket found !
            if value.m_range_upperbound != -1 and (rescount_msec >= value.m_range_lowerbound and rescount_msec < value.m_range_upperbound) :
                return key
            #This is the case when the res count lies in the highes bucket
            elif value.m_range_upperbound == -1 and rescount_msec >= value.m_range_lowerbound:
                return key         
        print'Error! residency count does not lie in any bucket. ', rescount_msec
        sys.exit()
    
#This class contains top level information for all wakeup types
#It represents each top level type such as 'Timers/Interrupts/Others(ipi,?)
class wakeUpDetailsClass:

    break_type = {'?'  :'Unknown',
                  'T'  :'PID',
                  'IPI':'IPI',
                  'I'  :'IRQ',
                  'W'  :'WQExec',
                  'S'  :'Scheduler',
                  '-'  :'Snooze'}
    
    def __init__(self, system_info):

        self.m_net_collection_time = system_info.m_collection_time
        self.m_wake_up_counts_map = dict() #Map containing all the wake-up reasons and respective counts
        #Wake-up reasons
        self.m_wake_up_counts_map['ALL'] = 0
        self.m_wake_up_counts_map['PID'] = 0
        self.m_wake_up_counts_map['IRQ'] = 0
        self.m_wake_up_counts_map['IPI'] = 0
        self.m_wake_up_counts_map['Unknown'] = 0
        self.m_wake_up_counts_map['WQExec'] = 0
        self.m_wake_up_counts_map['Scheduler'] = 0
        
        #This list has two members , (a) promotion counts (b) demotion counts
        #Promotion : (Sleep state requested by OS ) < (Sleep state granted by h/w)
        #Demotion  : (Sleep state requested by OS ) > (Sleep state granted by h/w)
        self.m_promotion_demotion_count_list = [0,0]

        #Create level two maps for each wakeup type , these maps contain further details about each wakeup type    
        self.m_residency_info_map            = dict()            #Map contating objects of residencyInformationClass as values and the states as keys [state: residency_object]
        self.m_timer_wakeups_details_map     = dict()            #Map containing [PID -> (detailed information about wu's caused by this PID)] information
        self.m_irq_wakeups_details_map       = dict()            #Map containing [IRQ -> (detailed information about wu's caused by this IRQ)] information
        self.m_other_wakeups_details_map     = dict()            #Map containing [?/IPI -> (detailed information about wu's caused by this wakeup)] information

        self.m_wakeups_per_sec = 0
        self.m_res_bucket_map = dict()
        self.createBuckets(system_info)

        self.m_p_residency = dict()
        
        ####Timeline Stuff
        
        self.m_wu_per_slice = []  #A list of the number of breaks for every time slice    
        self.m_time_slice_count = 0  #total number of slices
        self.m_num_cycles = 0        #every slice is made up of n cycles , cycles are calculated just to know when a slice was completed
        collection_time_in_msec = system_info.m_collection_time *1000
        self.m_wu_per_slice = [0] * (int(math.ceil(collection_time_in_msec/ system_info.m_time_slice_msec))) #the collection time is divided into slices of time_slice second each
        self.m_locks_per_timeslice =[0] * (int(math.ceil(collection_time_in_msec/ system_info.m_time_slice_msec)))
        ####
        #
        #List of existing wakelocks
        self.m_existing_wakelocks_list = []
        # A count of the total number of intermediate samples
        self.m_intermediate_sample_count = dict()

        # A dictionary of packag numbers -> residencies
        #self.m_package_residency = dict()     
        self.abort_sample_count = 0
        self.package_no = -1
        self.module_no  = -1
        self.m_c_state_residency = list()
        #residnecies for all levels below the package
        self.m_package_residency = dict()
        
        

    #Define buckets for the entire system , these are different from the buckets defined previously for each wakeup event 
    def createBuckets(self, sys_info):
        #add all the bucket ranges you need to this dictionary
        #insert lowerbound as the key
        #self.m_lower_upper_thresholds_map_C[state]
        
        #time unit used : miliseconds
        #We need to create buckets based on the target residencies for the different sleep states available
        index = 0
        for state in sorted(sys_info.m_lower_upper_thresholds_map_C.iterkeys()):

            if (isIntermediateState(state) == False):
                lower_bound_usec = round((utility_functions.getCountinMiliseconds(sys_info.m_lower_upper_thresholds_map_C[state][0] , sys_info)), 5)            
                upper_bound_usec = round((utility_functions.getCountinMiliseconds(sys_info.m_lower_upper_thresholds_map_C[state][1] , sys_info)), 5)
                if index == 0:
                    self.m_res_bucket_map[0] = resBuckets(0, upper_bound_usec, state)
                    index += 1
                    continue
                    
                if state == sys_info.m_deepest_state:
                    self.m_res_bucket_map[lower_bound_usec] = resBuckets(lower_bound_usec, 1, state)
                else:
                    self.m_res_bucket_map[lower_bound_usec] = resBuckets(lower_bound_usec, upper_bound_usec, state)
                index += 1
        
        self.m_res_bucket_map[1]    = resBuckets(1,5)
        self.m_res_bucket_map[5]    = resBuckets(5,10)
        self.m_res_bucket_map[10]   = resBuckets(10,30)
        self.m_res_bucket_map[30]   = resBuckets(30,50)
        self.m_res_bucket_map[50]   = resBuckets(50,100)
        self.m_res_bucket_map[100]  = resBuckets(100,200)
        self.m_res_bucket_map[200]  = resBuckets(200,500)
        self.m_res_bucket_map[500]  = resBuckets(500,1000)
        self.m_res_bucket_map[1000] = resBuckets(1000,5000)
        self.m_res_bucket_map[5000] = resBuckets(5000,-1)
               
    # Find system wide buckets    
    def findMybucket(self, rescount_msec):
       
        for key in sorted(self.m_res_bucket_map.iterkeys()):
            value = self.m_res_bucket_map[key]
            if value.m_range_upperbound != -1 and (rescount_msec >= value.m_range_lowerbound and rescount_msec < value.m_range_upperbound) :
                return key
            elif value.m_range_upperbound == -1 and rescount_msec >= value.m_range_lowerbound:
                return key        
        print'Error! residency count does not lie in any bucket .'
        sys.exit()

    #Update all the second tier maps for this wakeup event         
    def updateWakeUpMaps(self, wakeup_type, wakeup_name, identifier, core, res_count, state, breaktype, tsc, system_info, per_core_info_list, my_wu_handler_cpu):

        rescount_msec = utility_functions.getCountinMiliseconds((res_count), system_info)
        #Depending on the wakeup type , assign the map name
        if breaktype == 'T':
            map_name     = self.m_timer_wakeups_details_map
            cpu_map_name = per_core_info_list[core].m_timer_wakeups_details_map           
        elif breaktype == 'I':
            map_name     = self.m_irq_wakeups_details_map
            cpu_map_name = per_core_info_list[core].m_irq_wakeups_details_map
        elif breaktype == '?' or breaktype == 'IPI' or breaktype == 'W' or breaktype == 'S':
            map_name     = self.m_other_wakeups_details_map
            cpu_map_name = per_core_info_list[core].m_other_wakeups_details_map

        # elif breaktype == 'IPI':
        #     map_name     = self.m_other_wakeups_details_map
        #     cpu_map_name = per_core_info_list[cpu].m_other_wakeups_details_map

        else:
            print 'Wakeup type not recognized .Exiting.'
            sys.exit()

        #Identifier is the map key , it is PID for timer wakeups , IRQ for Interrupts , ?/IPI for Unknown and IPI wakeups         
        #Add this wu information to the corresponding map for over_all
        #If id already exists in the map , update its information 
        if identifier in  map_name :
            map_name[identifier].updateMyInfo(core, res_count, my_wu_handler_cpu )
            self.updatewakeupsPerStateInfo(self, breaktype, state, identifier)
            
            #update first and last sighting
            #if current tsc is less than first sighting then , then this is the first sighting
            #this needs to be done as data in wudump output is arranged per cpu and thus the first/last sighting could be on any cpu
            if tsc < map_name[identifier].m_first_sighting_tsc:
                map_name[identifier].m_first_sighting_tsc = tsc
            #if current tsc is greater than last sighting then , then this is the latest last sighting
            elif tsc > map_name[identifier].m_last_sighting_tsc:
                map_name[identifier].m_last_sighting_tsc = tsc

        #If pid does not exist in the map , create a new timer object and add its information
        else:
            tempObject = wakeupTypesInformationClass(wakeup_type, wakeup_name, res_count, state, core, system_info, my_wu_handler_cpu)
            map_name[identifier] = tempObject
            map_name[identifier].m_first_sighting_tsc = tsc
            map_name[identifier].m_last_sighting_tsc  = tsc
                 
        #Add this wu information to the per cpu objects' map
        #follow same procedure as above for the cpu on which wu occurred
        if identifier in cpu_map_name :
            cpu_map_name[identifier].updateMyInfo(core, res_count, my_wu_handler_cpu)
            self.updatewakeupsPerStateInfo(per_core_info_list[core], breaktype, state, identifier)
            cpu_map_name[identifier].m_last_sighting_tsc = tsc           
        else:
            tempObject = wakeupTypesInformationClass(wakeup_type, wakeup_name, res_count, state, core, system_info, my_wu_handler_cpu)    
            cpu_map_name[identifier] = tempObject
            cpu_map_name[identifier].m_first_sighting_tsc = tsc
            cpu_map_name[identifier].m_last_sighting_tsc  = tsc

        #UPDATE BUCKET INFORMATION
        #find the bucket to which the wu belongs
        bucket_id = map_name[identifier].findMybucket(rescount_msec)
        map_name[identifier].m_res_bucket_map[bucket_id].updateBucket(rescount_msec)
        cpu_map_name[identifier].m_res_bucket_map[bucket_id].updateBucket(rescount_msec)
        return map_name[identifier]

    def updateResCountMap(self, state, core, per_core_info_list, res_count, break_type, intermediateState= False):

        if state in  self.m_residency_info_map:
            self.m_residency_info_map[state].updateResidencyInfoMap(res_count, core, break_type, state, intermediateState)          
            #If state does not exist in the map , create a new state object and add its information
        else:       
            tempResObject = residencyInformationClass(state, res_count, intermediateState)
            self.m_residency_info_map[state] = tempResObject
            self.m_residency_info_map[state].m_wakeup_specific_hit_count[break_type] = 1
             
        #Add this residency information to the per cpu objects' res map
        #follow same procedure as above for the cpu on which wake-up occurred
        if state in per_core_info_list[core].m_residency_info_map :
            per_core_info_list[core].m_residency_info_map[state].updateResidencyInfoMap(res_count, core, break_type, state, intermediateState)
        else:
            tempResObject = residencyInformationClass(state, res_count, intermediateState)
            per_core_info_list[core].m_residency_info_map[state] = tempResObject
            per_core_info_list[core].m_residency_info_map[state].m_wakeup_specific_hit_count[break_type] = 1
            
    #Update information for the corresponding sleep state        
    def updatewakeupsPerStateInfo(self, obj, wakeup_type, state, identifier):
  
        if wakeup_type == 'T':
            if state in obj.m_timer_wakeups_details_map[identifier].m_state_specific_wakeup_count:
                obj.m_timer_wakeups_details_map[identifier].m_state_specific_wakeup_count[state] += 1
            else:
                obj.m_timer_wakeups_details_map[identifier].m_state_specific_wakeup_count[state] = 1

        elif wakeup_type == 'I':
            if state in obj.m_irq_wakeups_details_map[identifier].m_state_specific_wakeup_count:
                obj.m_irq_wakeups_details_map[identifier].m_state_specific_wakeup_count[state] += 1
            else:
                obj.m_irq_wakeups_details_map[identifier].m_state_specific_wakeup_count[state] = 1
        else :
            if state in obj.m_other_wakeups_details_map[identifier].m_state_specific_wakeup_count:
                obj.m_other_wakeups_details_map[identifier].m_state_specific_wakeup_count[state] += 1
            else:
                obj.m_other_wakeups_details_map[identifier].m_state_specific_wakeup_count[state] = 1

    def updateFrequencyDB(self, per_core_info_list, freq, count, core):

        if freq not in per_core_info_list[core].m_p_residency.keys():
            per_core_info_list[core].m_p_residency[freq] = 0
        per_core_info_list[core].m_p_residency[freq] += count
       
    def stateType(self, package, module, core):

        if core != '-':
            return "core"
        else:
            if module != '-':
                return "module" 
            else:
                return "package"

    def addToMap(self, map, item, count):
        
        if item in map:
            map[item] += count
        else:
            map[item] = count

    def updateHWNodesResidency(self, sample, system_info):

        sample_type = self.stateType(sample.package, sample.module, sample.core)
        try:
            if sample_type == "package":
                if sample.package in self.m_package_residency:
                    self.addToMap(self.m_package_residency[sample.package].m_c_res, sample.state, sample.count)
                    #self.m_package_residency[sample.package].m_c_res[sample.state] += sample.count
                
                else:
                    packageObj = Package()
                    packageObj.package_id = sample.package
                    packageObj.m_c_res[sample.state] = sample.count
                    self.m_package_residency[sample.package] =  packageObj

            if sample_type == "module":
                if sample.package in self.m_package_residency:
                    #self.addToMap(self.m_package_residency[sample.package].m_c_res, sample.state, sample.count)
                    #self.m_package_residency[sample.package].m_c_res[sample.state] += sample.count
                    if sample.module in self.m_package_residency[sample.package].m_modules:
                        self.addToMap(self.m_package_residency[sample.package].m_modules[sample.module].m_c_res, sample.state, sample.count)
                        #self.m_package_residency[sample.package].m_modules[sample.module].m_c_res[sample.state] += sample.count
                    else:
                        moduleObj = Module()
                        moduleObj.m_c_res[sample.state] = sample.count
                        self.m_package_residency[sample.package].m_modules[sample.module] = moduleObj
                else:
                    packageObj = Package()
                    packageObj.package_id = sample.package
                    packageObj.m_c_res[sample.state] = 0
                    packageObj.m_modules[sample.module] = Module()
                    packageObj.m_modules[sample.module].m_c_res[sample.state] = sample.count;
                    self.m_package_residency[sample.package] =  packageObj

            if sample_type == "core":
                if sample.package in self.m_package_residency:
                    if sample.core in self.m_package_residency[sample.package].m_cores:
                        self.addToMap(self.m_package_residency[sample.package].m_cores[sample.core].m_c_res, sample.state, sample.count)                       
                    else:
                        coreObj = Core()
                        coreObj.m_c_res[sample.state] = sample.count
                        self.m_package_residency[sample.package].m_cores[sample.core] = coreObj
                        if sample.module not in self.m_package_residency[sample.package].m_modules:
                            self.m_package_residency[sample.package].m_modules[sample.module] = Module()
                        self.m_package_residency[sample.package].m_modules[sample.module].m_core_count+= 1

                else:
                    packageObj = Package()
                    packageObj.package_id = sample.package
                    packageObj.m_c_res[sample.state] = 0
                    packageObj.m_modules[sample.module] = Module()
                    packageObj.m_modules[sample.module].m_c_res[sample.state] = 0
                    packageObj.m_modules[sample.module].m_core_count+= 1
                    packageObj.m_cores[sample.core] = Core()
                    packageObj.m_cores[sample.core].m_c_res[sample.state] = sample.count
                    self.m_package_residency[sample.package] =  packageObj

        except Exception, e:
            print 'Caught Exception: ', sample.TSC, str(e)
            sys.exit(1)


    def updatePackageResidency(self, state, package, count, system_info):

        pkg = int(package)
        if pkg not in self.m_package_residency:
            stateList = [0] * (system_info. m_deepest_state + 1)
            self.m_package_residency[pkg] = stateList
            
        self.m_package_residency[pkg][int(state)] += count

    #This function receives a sample from wudump,
    #dismemebers it and updates the information to the corresponding data structures
    def storeWakeUpInformation(self, sample, per_core_info_list, system_info, intermediateState = False):
   
        global debug, utility_functions, IRQ, TIMER, current_core, core, previous_sample_TSC
        is_a = {'promotion':0,'demotion':1}
        wakeup_obj = None

        if sample.TSC == '-':
            sample.TSC = previous_sample_TSC
        else:
            previous_sample_TSC = sample.TSC

        if type(sample.core) == type(int()):
            if sample.core != current_core:
                current_core = sample.core
                core += 1

        sample_type = self.stateType(sample.package, sample.module, sample.core)
        self.updateHWNodesResidency(sample, system_info)
         
        if sample.state not in system_info.m_sleep_states:
            system_info.m_sleep_states.append(sample.state)
        if sample_type == 'core':
            
            if intermediateState == True:
                try:
                    if int(sample.state) not in self.m_intermediate_sample_count:
                   
                        self.m_intermediate_sample_count[int(sample.state)] =  1
                        per_core_info_list[core].m_intermediate_sample_count[int(sample.state)] =  1
                    else:
                        self.m_intermediate_sample_count[int(sample.state)] += 1
                        per_core_info_list[core].m_intermediate_sample_count[int(sample.state)] += 1
                except:
                    pass
          
            #################################################################################################
            #Build the frequency DB
            #################################################################################################
        
            if (type(sample.frequency) == type (int())):
                self.updateFrequencyDB(per_core_info_list, sample.frequency, sample.count, core)
        
            #################################################################################################
            #UPDATE WAKEUP COUNT INFORMATION : FOR BREAKTYPE(I/T/IPI/U) WAKEUPS AND ALL WAKEUPS
            ################################################################################################
            #If it is a sleep sample which is followed by another sleep, it is not a wakeup as it
            # leads to another sleep state. do not update wakeup counts.
            if intermediateState == False:
            
                self.m_wake_up_counts_map['ALL'] += 1
                self.m_wake_up_counts_map[self.break_type[sample.breaktype]] += 1
                per_core_info_list[core].m_wake_up_counts_map['ALL'] += 1
                per_core_info_list[core].m_wake_up_counts_map[self.break_type[sample.breaktype]] += 1

                #################################################################################################
                # Requested state for initial sample is - , ignore that case for promotion/demotion calculations
                # 1) Intermediate samples cannot be demotion sample
                # 2) If a sample has an actual state of C6, and the req state is higher, its is not a demotion.
                #    It probbaly went into an S State.
                #################################################################################################
                if (type(sample.reqstate) == type (float())):
                    if utility_functions.calculatePromotionOrDemotion(sample.reqstate, sample.state) == is_a['promotion'] :
                        self.m_promotion_demotion_count_list[is_a['promotion']] += 1
                        per_core_info_list[core].m_promotion_demotion_count_list[is_a['promotion']] += 1
                    elif utility_functions.calculatePromotionOrDemotion(sample.reqstate, sample.state) == is_a['demotion'] :
                        self.m_promotion_demotion_count_list[is_a['demotion']] += 1
                        per_core_info_list[core].m_promotion_demotion_count_list[is_a['demotion']] += 1

            #################################################################################################
            #converts the wu shorthand to full name '?' -> UNKNOWN , 'T'-> timer etc
            break_type = utility_functions.break_type_names[sample.breaktype]
           
            if intermediateState == False:
                if sample.breaktype == 'T':
                    wakeup_obj = self.updateWakeUpMaps(TIMER, sample.WU_name, sample.pid, core, sample.count, sample.state, sample.breaktype, sample.TSC, system_info, per_core_info_list, sample.my_wakeup_handler_cpu)
                elif sample.breaktype == 'I':
                    wakeup_obj = self.updateWakeUpMaps(IRQ, sample.WU_name, sample.irq, core, sample.count, sample.state, sample.breaktype, sample.TSC, system_info, per_core_info_list, sample.my_wakeup_handler_cpu)        
                #IPI/UNKNOWN breaks
                else:
                    wakeup_obj = self.updateWakeUpMaps(break_type, break_type, break_type, core, sample.count, sample.state, sample.breaktype, sample.TSC, system_info, per_core_info_list, sample.my_wakeup_handler_cpu)

        
            ####################################
            # UPDATE RESIDENCY COUNT INFORMATION
            ####################################
            #Add this state information to the residency map for over_all
            #If state# already exists in the map , update its information
            #self.m_residency_info_map[state].updateResidencyInfoMap(state,count,per_core_info_list)
            self.updateResCountMap(sample.state, core, per_core_info_list, sample.count, break_type, intermediateState)
       
        
            ###############################################
            #UPDATE THE INCORRECT C STATES USED INFORMATION
            ###############################################
            #Update counts for thresholds.
            #Check whether residency of the current sample is lower/higher than the lower/upper threshold for that state and accordingly update numbers 
            try:
                if sample.state in system_info.m_lower_upper_thresholds_map_C:
                    if sample.state != 5 and sample.count < system_info.m_lower_upper_thresholds_map_C[sample.state][0] :
                        self.m_residency_info_map[sample.state].updatePowerMetrics(sample.count, system_info, 'Pwasted')
                        per_core_info_list[core].m_residency_info_map[sample.state].updatePowerMetrics(sample.count, system_info, 'Pwasted')
                    # Oppurtunity wasted counts do not apply to the deepest state
                    if sample.state != system_info.m_deepest_state and sample.state != 5: 
                        if sample.count > system_info.m_lower_upper_thresholds_map_C[sample.state][1]:
                            self.m_residency_info_map[sample.state].updatePowerMetrics(sample.count, system_info, 'Olost')
                            per_core_info_list[core].m_residency_info_map[sample.state].updatePowerMetrics(sample.count, system_info, 'Olost')
              
            except Exception, e:
                print 'Found a invalid state', str(e)
                sys.exit(1)
            ################################################
            #UPDATE THE RESIDENCY BUCKET INFORMATION 
            ################################################
            rescount_msec = float(utility_functions.getCountinMiliseconds((sample.count), system_info))
            bucket_id = self.findMybucket(rescount_msec)
            self.m_res_bucket_map[bucket_id].updateBucket(rescount_msec)
            per_core_info_list[core].m_res_bucket_map[bucket_id].updateBucket(rescount_msec)
        
        return wakeup_obj
                
    def storeActiveStateInformation(self, sample, per_core_info_list, prev_wakeup_obj, system_info):

        
        #This is a C0 sample , update data structures with information
        global utility_functions, current_core_c0, core_c0
        #This is CoreID

        if type(sample.core) == type(int()):
            if sample.core != current_core_c0:
                current_core_c0 = sample.core
                core_c0 += 1

        self.updateHWNodesResidency(sample, system_info)  
        if sample.state not in system_info.m_sleep_states:
            system_info.m_sleep_states.append(sample.state)

        if self.stateType(sample.package, sample.module, sample.core) == 'core':
            #################################################################################################
            #Build the frequency DB
            #################################################################################################
            if type(sample.frequency) ==  type(int()):
                self.updateFrequencyDB(per_core_info_list, sample.frequency, sample.count, core_c0) 
            #################################################################################################

            break_type = ''
            self.updateResCountMap(sample.state, core_c0, per_core_info_list, sample.count, break_type) 
          
            #The residency count for this C0 sample serves as the active count for the previous CX sample, update that infomation        
            if prev_wakeup_obj != None:
                rescount_msec = float(utility_functions.getCountinMiliseconds((sample.count), system_info))
                prev_wakeup_obj.updateActiveCount(rescount_msec)
            #if there is no previous Cx sample, this means that there is an error
            #else:
            #    if sample.TSC != -1:
            #        utility_functions.errorSamples = utility_functions.errorSamples + 'Discarding corresponding C0 sample: '+  str(sample)  + '\n'

    """      
    def buildTimeline(self, current_sample, per_core_info_list, system_info, disregardWakeup):

        global current_core
  
        ########################################################################################################################################################################################
        #COUNT THE NUMBER OF WAKEUPS IN A TIMESLICE
        #A time slice is made of N cycles
        #
        #Divide the entire collection run time into slices
        #For every C state , cumalatively add the residency counts to check if the timeslice is full , count the number of wakeups in a timeslice
        #Once the residency count sums to N , we know that the time slice is full and we increment the time-slice number by 1 to gather statistics for the next time slice
        #########################################################################################################################################################################################       

        if type(current_sample.core) ==  type(int()):
            current_core = int(current_sample.core)
        core = current_core
           
        if per_core_info_list[core].m_time_slice_count < len(per_core_info_list[core].m_wu_per_slice):        
            #if time slice cycle count was exceeded, increment to next time slice count, and reset cycles
            if per_core_info_list[core].m_num_cycles >= system_info.m_cycles_per_time_slice:
                per_core_info_list[core].m_time_slice_count += 1
                per_core_info_list[core].m_num_cycles = per_core_info_list[core].m_num_cycles - system_info.m_cycles_per_time_slice
 
            if current_sample.state == 0:          
                #If this was an errneous wakeup sample, do not increment the wu count for this slice                
                if disregardWakeup ==  False:
                    #In the collection time, we round off the time to two decimal places.
                    # Example collection time was 673miliseconds, we round it off as .67 seconds
                    #If each slice was 10miliseconds, a wu in the last3 miliseconds would try to goto slice 68 which
                    # would generate an index error. To prevent a situation like this, we check if the slice count is higher than max
                    #expected and if it is higher, we reduce it by 1.
                    if per_core_info_list[core].m_time_slice_count >= len(per_core_info_list[core].m_wu_per_slice):
                            per_core_info_list[core].m_time_slice_count = len(per_core_info_list[core].m_wu_per_slice) - 1
                    
                    per_core_info_list[core].m_wu_per_slice[per_core_info_list[core].m_time_slice_count] += 1
                    self.m_wu_per_slice[per_core_info_list[core].m_time_slice_count] += 1 
            #Special case for smaller slices, say the time_slice is 1ms and freq 1597MHz, each slice cycle =(1597mHz * 1msec) in this case if a rescount for a sample is say 4000k
            #then nothing happens in the next 2-3 slice cycles as its the same c state sample.
            #so here we keep incrementing the slice number till we exhaust this sample.
            while per_core_info_list[core].m_num_cycles >= system_info.m_cycles_per_time_slice:
                per_core_info_list[core].m_time_slice_count += 1
                per_core_info_list[core].m_num_cycles = per_core_info_list[core].m_num_cycles - system_info.m_cycles_per_time_slice                                      
                
            if current_sample.count != 0:
                per_core_info_list[core].m_num_cycles += (current_sample.count) 
            #else:
            #    per_core_info_list[cpu].m_num_cycles += 500 #if count is 0 (there were < 1000 cycles) ad 500 cycles assuming an even distribution
        """

#########################################################################################################################################                
def isIntermediateState(key):

    if key.rfind('i') != -1:
        return True
    else:
        return False

def isPackageCState(package, core, module):

    if(core == '-' and module == '-'):
        return True
    else:
        return False

class utilityFunctions:

    errorSamples = ''
    break_type_names = {  '?'  : 'Unknown' ,
                          'T'  : 'Timer' ,
                          'I'  : 'IRQ',
                          'IPI': 'IPI',
                          'W'  : 'WQExec',
                          'S'  : 'Scheduler',
                          '-'  : 'Snooze'}

    def mergeTwoDictionaries(self, dict1, dict2):
        # merge the timer and interrupt maps , sort the merged map and print top 10
        merged = dict1.copy()
        #check for cases where list1 and list 2 might have confliction key's
        #in such a situation , negate the key, multiply by 100 and add it .
        for item in dict1.keys(): 
            if dict2.has_key(item):
                x = int(item) * -100
                merged[str(x)] = merged[item]
                del merged[item]
        #add the dict2 itmes to the merged dictionary now
        merged.update(dict2)
        return merged

    def  getRate(self, dividend, divisor):
        
        if divisor <= 0:
            return 0
        else:
            return float(dividend * 1.0 / divisor)
        
    def  getPercentage(self, dividend, divisor):
        
        if divisor <= 0:
            return 0
        else:
            return float(dividend * 1.0 / divisor) * 100.0

    def  getTopTen(self):
        pass

    def getCountinMiliseconds(self, count, system_info):

        #residency count in the count variable is in units of 1 and NOT K
        if system_info.m_system_frequency > 0:
            result = float(self.getRate(count, system_info.m_system_frequency))
            #convert resulting seconds to miliseconds
            result = result * 1000    
            return float(result)
        else:
            return 0
        
    def calculatePromotionOrDemotion(self, requestedState, actualState):
  
        try:
            if len(actualState) == 1:
                if actualState != '-':
                    actualState = long(actualState)
            elif len(actualState) > 1:
                try: 
                    int(actualState[1])
                    state = long(actualState[0:1])
                except ValueError:
                    state = long(actualState[0])
                actualState = state

            #return 0 for promotion, 1 for demotion
            if actualState < requestedState:
                #C6 samples cannot be a demotion sample. It probably went into an S state.
                if actualState == 6:
                    return 2
                return 1    #demotion
            elif actualState > requestedState:
                return 0    #promotion
            else:
                return 2
        except Exception:
            print "Error in promotion demotion calculation"

    def collectErroneousSamples(self, current_sample, system_info, over_all_cpu_info):
 
        error_in = ''
        found_error = 0

        if type(current_sample.core) == type(int()):
            if current_sample.core < 0 or current_sample.core > (system_info.m_core_count-1):
                found_error = 1
                error_in = 'core'

        if type(current_sample.state) == type(float()):
            if current_sample.state < 0:
                found_error = 1
                error_in = 'state'
      
        if type(current_sample.count) == type(int()):
            if current_sample.count < 0:
                found_error = 1
                error_in = 'count'
                    
        if type(current_sample.my_wakeup_handler_cpu) == type(int()):
            if current_sample.my_wakeup_handler_cpu > (system_info.m_logical_cpu_count-1) or current_sample.my_wakeup_handler_cpu < 0:
                found_error = 1
                error_in = 'cpu'
        
        if  current_sample.state != 0 :
            if current_sample.breaktype not in over_all_cpu_info.break_type:
                found_error = 1
                error_in += ' /break_type'
            else:  
                if current_sample.breaktype == 'T':
                    try:
                        if int(current_sample.tid) < -1 or int(current_sample.pid) < -1:
                            found_error = 1
                            error_in += ' /pid/tid'
                    except ValueError:
                        if current_sample.tid == '-' or current_sample.pid == '-':
                            pass
                        else:
                            found_error = 1
                            error_in += ' /pid/tid'
                elif current_sample.breaktype == 'I':
                    try:
                        if int(current_sample.irq) < -1:
                            found_error = 1
                            error_in += ' /irq'
                    except ValueError:
                        if current_sample.irq == '-':
                            pass
                        else:
                            found_error = 1
                            error_in += ' /irq'
                        
            try:
                if type(current_sample.reqstate) == type(float()): 
                    if current_sample.reqstate < 0:
                        found_error = 1
                        error_in += ' /requestedState' 
            except ValueError:
                found_error = 1
                error_in += ' ,requestedState'
            
        if found_error == 1 and current_sample.breaktype != 'B' and current_sample.breaktype != 'A' :       
            self.errorSamples = self.errorSamples + 'Error Found In Value : [' + error_in + ']  SAMPLE TSC ' +  str(current_sample.TSC)  + '\n'         
        return found_error

##############################################################################################################################################33    
#Creating global utility functions object    
utility_functions = utilityFunctions() 

class cStateSample:

    def __init__(self, sample):

        self.TSC       = sample[0].strip()
        self.package   = sample[1].strip()
        self.module    = sample[2].strip()
        self.core      = sample[3].strip()
        self.state     = sample[4].strip()
        #self.state_char = ""
        self.reqstate  = sample[5].strip()
        self.count     = long(sample[6].strip())
        self.tid       = sample[9].strip()
        self.pid       = sample[10].strip()
        self.irq       = sample[11].strip()
        self.frequency = sample[12].strip()
        self.WU_name   = sample[13].strip()
        self.breaktype = (sample[7]).strip()
        self.my_wakeup_handler_cpu = sample[8].strip()

        """
        if len(self.state) == 1:
            if self.state != '-':
                self.state = long(self.state)

        if len(self.state) > 1:
            try: 
                int(self.state[1])
                state = long(self.state[0:1])
                self.state_char = self.state[2:]
            except ValueError:
                state = long(self.state[0])
                self.state_char = self.state[1:]
            self.state = state
        """

        if self.TSC != '-':
            self.TSC = long(self.TSC)

        if self.package != '-':
            self.package = int(self.package)

        if self.module != '-':
            self.module = int(self.module)

        if self.core != '-':
            self.core = int(self.core)

        if self.reqstate != '-':
            self.reqstate = float(self.reqstate)

        if self.count != '-':
            self.count = int(self.count)

        if self.frequency != '-':
            self.frequency = int(self.frequency)

        if self.my_wakeup_handler_cpu != '-':
            self.my_wakeup_handler_cpu = int(self.my_wakeup_handler_cpu)

def parseCStateSamples(fd, system_info, per_core_info_list, over_all_cpu_info):

    for line in fd:
        if line.startswith("*************"):
            break;
    cstateheaderfound = 0
    
    for line in fd:            
        if line.strip().startswith("TSC"):
            parsed = line.strip().split()
            if(len(parsed) == 16 and parsed[0] ==  "TSC" and parsed[1] == "ID" and parsed[4] == "C-STATE"
                                  and parsed[5] == "C-STATE" and parsed[6] == "(clock" and parsed[7] == "ticks)"
                                  and parsed[8] == "EVENT" and parsed[9] == "CPU" and parsed[10] == "TID"
                                  and parsed[11] == "PID" and parsed[12] == "IRQ" and parsed[13] == "(MHz)" and parsed[14] == "Additional"):
                cstateheaderfound = 1
            elif(len(parsed) == 15 and parsed[6] == "(usecs)"):
                print("C-State residency data must be in clock ticks. Please use socwatch to dump the data in clock ticks.")        
            break
        
    # Skip the separator **********************
    for line in fd:            
        if line.strip().startswith("**********"):
            break;

    #if the c state header is found to be valid proceed with reading the c state samples
    if cstateheaderfound == 1:
        prev_wakeup_obj = None
        line = ''
        index = 0
        previous_sample_TSC = 0
        for line in fd:
           
            #Exit at reaching the end of samples
            if line.strip().startswith("**********"):
                break;
            else:
                parsed = ''
                parsed = line.strip().split(None, 13)
                #If the sample has all the information , it must contain atleast 13 tokens
                if len(parsed) >= 13:          
                    #######################################################################################
                    # ERRONEOUS SAMPLE CHECK
                    #check for any erroneous samples , if sample found to be erroneous , do not proces it
                    #######################################################################################
                    current_sample = None
                    current_sample = cStateSample(parsed)
                    if utility_functions.collectErroneousSamples(current_sample, system_info, over_all_cpu_info):
                        #if the erroneous sample is a sleep(C1-6) discard the corresponding C0 sample, which follows it
                        if current_sample.state != '0':
                            # We add the residency counts of collected samples to create a time slice, where all the time slices add upto the total collection time.
                            # Some samples collected might be deemed erroneous, but for timeline creation we need to take into account the residency counts of these tobe discarded samples as well.
                            # So that a time slice spans over the right samples. But, at the same time we should not account these erroneous wakeup samples in the waleup count per time slice metric.
                            disregardWakeup = False    # This is an erroneous sample, but NOT A WAKEUP i.e. C0 so do not decrement the wu count
                            
                            #over_all_cpu_info.buildTimeline(current_sample, per_core_info_list, system_info, disregardWakeup)                         
                            try:
                                # before discarding this C0 sample we need to take into account its residency count for correct timeline building, as the timeslice needs to increment by this
                                # residency count                            
                                currPos = fd.tell()
                                C0Sample = cStateSample(fd.next().strip().split(None, 13))
                                if C0Sample.state == '0':    #if its is the corresponding C0 discard it.                         
                                    disregardWakeup =  True   #C0 is a wakeup sample, we need to disregard this wakeup in the timeline as it is erroneous
                                    
                                    #over_all_cpu_info.buildTimeline( C0Sample, per_core_info_list, system_info, disregardWakeup)
                                    if current_sample.breaktype != 'B' and current_sample.breaktype != 'A' :
                                        utility_functions.errorSamples = (utility_functions.errorSamples + 'Discard C0 corresponding to erroneous Cx' + 
                                                                          ' SAMPLE (res count: ' +  str(C0Sample.count)  + ') \n')
                                    else:
                                        if current_sample.breaktype == 'B':
                                            # If the sample is a dummy B sample, add it as an unknown wakeup
                                            current_sample.breaktype = '?'
                                            prev_wakeup_obj  = over_all_cpu_info.storeWakeUpInformation(current_sample, per_core_info_list, system_info)
                                        elif current_sample.breaktype == 'A':                                        
                                            over_all_cpu_info.abort_sample_count += 1
                                        #This sample does not need to be printed in the erroneous samples
                                        #We make the tsc for this sample -1 to make it distinguishable.
                                        #C0Sample.TSC = -1
                                        over_all_cpu_info.storeActiveStateInformation(C0Sample, per_core_info_list, prev_wakeup_obj, system_info)
                                        
                                #Incase the next sample is not a C0 i.e. a Sleep sample was followed by another sleep sample(this would be the case if a C0 sample is missing)
                                #We should parse this sample as it could be a valid sample
                                
                                else:
                                    #We reposition the file to the erroneous sample so that the next sample can be read in the next iteration of the for loop
                                    fd.seek(currPos, 0)
                                    
                            except StopIteration:
                                pass                                 
                        elif current_sample.state == '0':   #incase for some reason, the first erroneous sample was a C0 sample
                            disregardWakeup = True                      
                            #over_all_cpu_info.buildTimeline(current_sample, per_core_info_list, system_info, disregardWakeup)  
                        continue
                        #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


                    #######################################################################################
                    # No erros found. Now, parse the sample.
                    #######################################################################################
                    
                    intermediateState = False
                    
                    
                    #Here we will consider samples where a sleep was followed by another sleep state
                    #For such cases wudump adds dummy C0 samples with 0 residency
                    #These are not real wakeups, so we need to ignore them
                    if current_sample.state != '0':
                        if current_sample.breaktype == '-':
                            index += 1
                            intermediateState = True
                            #The next sample is a C0 with 0 residency. We ignore that sample
                            fd.next()

                        #Some wakeup samples will not have a TSC, only the first sample of that bunch will have a TSC
                        #if current_sample.TSC == '-':
                        #    current_sample.TSC = previous_sample_TSC
                        #else:
                        #    previous_sample_TSC = current_sample.TSC
                        prev_wakeup_obj  = over_all_cpu_info.storeWakeUpInformation(current_sample, per_core_info_list, system_info, intermediateState)
                  

                    #This is a C0 state, update active state information
                    elif current_sample.state == '0':
                        over_all_cpu_info.storeActiveStateInformation(current_sample, per_core_info_list, prev_wakeup_obj, system_info)
                        #reset the previous sample to none
                        
                    #over_all_cpu_info.buildTimeline(current_sample, per_core_info_list, system_info, intermediateState)    
                    
    return fd

def parseOldPStateSamples(fd, system_info, per_core_info_list, over_all_cpu_info, p_residency, p_timeline):
  
    global utility_functions
    pstateheaderfound = 0

    
    for line in fd:            
        #End of P-State Samples
        if line.strip().startswith("**********"):
            break;

    pstateheaderfound = 1
    prev_core = -1
    prev_tsc = 0
    if pstateheaderfound == 1:
        for line in fd:            
            if line.strip().startswith("**********"):
                break;
            else:
                parsed = ''
                parsed = line.strip().split()

                #if the sample has all the information , it must contain 4 tokens
                if len(parsed) == 4:
                    try:
                        tsc = long(parsed[0]) 
                        core = int(parsed[1]) 
                        ActFreq = int(parsed[3])
                        ReqFreq = (parsed[2])
                    except  Exception, e:
                        print 'Exception in reading P-State sample: ', str(e), '\nSample:', parsed
                        continue

                    p_timeline[core][tsc] = [0,0]
                    p_timeline[core][tsc][0] = ActFreq
                    p_timeline[core][tsc][1] = ReqFreq

                    if prev_core != core:
                        p_residency[core][ActFreq] = 0.0
                    else:
                        if not ActFreq in p_residency[core]:
                            p_residency[core][ActFreq] = utility_functions.getCountinMiliseconds(tsc-prev_tsc, system_info)
                        else:
                            p_residency[core][ActFreq] = p_residency[core][ActFreq] + utility_functions.getCountinMiliseconds(tsc-prev_tsc, system_info)
                    prev_core = core
                    prev_tsc = tsc
                                       
    return fd

                    
def parsePStateSamples(fd, system_info, per_core_info_list, over_all_cpu_info, p_residency, p_timeline):
  
    global utility_functions
    pstateheaderfound = 0
    oldpstateheaderfound = 0

    #Skip P-State Samples
    for line in fd:            
        #Before header line of P-State Samples
        if line.strip().startswith("**********"):
            break;
        
    for line in fd:
        if line.strip().startswith("TSC"):
            parsed = line.strip().split()
            if parsed == ["TSC", "ID", "Frequency(Mhz)", "Frequency(Mhz)", "(TSC", "ticks)"]:
                pstateheaderfound = 1
            elif parsed == ["TSC", "ID", "Frequency(Mhz)", "Frequency(Mhz)"]:
                oldpstateheaderfound = 1
                return parseOldPStateSamples(fd, system_info, per_core_info_list, over_all_cpu_info, p_residency, p_timeline)
            break

    for line in fd:            
        #End of P-State Samples
        if line.strip().startswith("**********"):
            break;

    prev_core = -1
    prev_tsc = 0
    if pstateheaderfound == 1:
        for line in fd:            
            if line.strip().startswith("**********"):
                break;
            else:
                parsed = ''
                parsed = line.strip().split()

                #if the sample has all the information , it must contain 4 tokens
                if len(parsed) == 5:
                    try:
                        tsc = long(parsed[0]) 
                        core = int(parsed[1]) 
                        ActFreq = int(parsed[3])
                        ReqFreq = (parsed[2])
                        C0Ticks = long(parsed[4])
                    except  Exception, e:
                        print 'Exception in reading P-State sample: ', str(e), '\nSample:', parsed
                        continue

                    p_timeline[core][tsc] = [0,0]
                    p_timeline[core][tsc][0] = ActFreq
                    p_timeline[core][tsc][1] = ReqFreq

                    if prev_core != core:
                        p_residency[core][ActFreq] = 0.0
                    else:
                        if not ActFreq in p_residency[core]:
                            p_residency[core][ActFreq] = utility_functions.getCountinMiliseconds( C0Ticks, system_info)
                        else:
                            p_residency[core][ActFreq] = p_residency[core][ActFreq] + utility_functions.getCountinMiliseconds( C0Ticks, system_info)
                    prev_core = core
                    prev_tsc = tsc
                                       
    return fd


def parseSStateSamples(fd, system_info, per_core_info_list, over_all_cpu_info, s_residency):

    sresidencyheaderfound = 0
    
    for line in fd:            
        if line.strip().startswith("TSC"):
            parsed = line.strip().split()
            if len(parsed) == 5 and parsed[1].startswith("S0i0"):
                sresidencyheaderfound = 1
            break
            
    # Skip the separator **********************
    for line in fd:            
        if line.strip().startswith("**********"):
            break;
  
    s0i0 = 0
    s0i1 = 0
    s0i2 = 0
    s0i3_s3 = 0
    #s3   = 0
    
    if sresidencyheaderfound == 1:
        for line in fd:            
            if line.strip().startswith("**********"):
                break;
            else:     
                parsed = ''
                parsed = line.strip().split()

                #if the sample has all the information , it must contain 6 tokens
                if len(parsed) == 5:
                    try:
                        s0i0 = int(parsed[1]) # s0i0
                        s0i1 = int(parsed[2]) # s0i1
                        s0i2 = int(parsed[3]) # s0i2
                        s0i3_s3 = int(parsed[4]) # s0i3
                        #s3   = int(parsed[5]) # s3

                    except  Exception, e:
                        print 'Exception in reading S-State sample: ', str(e), '\nSample:', parsed
                        continue
                    
                    s_residency.append([s0i0, s0i1, s0i2, s0i3_s3])

    return fd


def parseDStateSCResidencySamples(fd, system_info, per_core_info_list, over_all_cpu_info, d_sc_residency, sc_device_mapping):
    
    dresidencyheaderfound = 0

    for line in fd:     
        if line.strip().startswith("**********"):
            break;

    if len(sc_device_mapping.keys()) == 0:
        for line in fd:            
            if line.strip().startswith("**********"):
                break;
            else:
                if len(line[:-1].strip()) > 0:
                    tuple = line.partition(':')
                    identifier = tuple[0].strip()
                    name = tuple[2].strip()
                    #identifier = line[:-1].split(':')[0].strip()
                    #name = line[:-1].split(':')[1].strip()
                    if not sc_device_mapping.has_key(identifier):
                        sc_device_mapping[identifier] = name

    for line in fd:            
        if line.strip().startswith("TSC"):
            parsed = line.strip().split()
            if len(parsed) == 6 and parsed[2].startswith("D0i0"):
                dresidencyheaderfound = 1
            break
    # Skip the separator **********************
    for line in fd:            
        if line.strip().startswith("**********"):
            break;

    d0i0 = 0
    d0i1 = 0
    d0i2 = 0
    d0i3 = 0
    if dresidencyheaderfound == 1:
        for line in fd:            
            if line.strip().startswith("**********"):
                break;
            else:     
                parsed = ''
                parsed = line.strip().split()

                #if the sample has all the information , it must contain 6 tokens
                if len(parsed) == 6:
                    lss = parsed[1] # LSS name
                    if not d_sc_residency.has_key(lss):
                        d_sc_residency[lss] = []
                    try:
                        d0i0 = int(parsed[2]) # d0i0
                        d0i1 = int(parsed[3]) # d0i1
                        d0i2 = int(parsed[4]) # d0i2
                        d0i3 = int(parsed[5]) # d0i3
                    except  Exception, e:
                        print 'Exception in reading SC D-Residency sample: ', str(e), '\nSample:', parsed
                        continue
                    
                    d_sc_residency[lss].append([d0i0, d0i1, d0i2, d0i3])


    return fd

def parseDStateNCStateSamples(fd, system_info, per_core_info_list, over_all_cpu_info, d_nc_state, nc_device_mapping):
    
    dncstateheaderfound = 0

    for line in fd:     
        if line.strip().startswith("**********"):
            break;
            
    for line in fd:            
        if line.strip().startswith("**********"):
            break;
        else:
            if len(line[:-1].strip()) > 0:
                identifier = line[:-1].split(':')[0].strip()
                name = line[:-1].split(':')[1].strip()
                if not nc_device_mapping.has_key(identifier):
                    nc_device_mapping[identifier] = name

    for line in fd:            
        if line.strip().startswith("TSC"):
            parsed = line.strip().split()
            if len(parsed) == 3 and parsed[2].startswith("State"):
                dncstateheaderfound = 1
            break
    # Skip the separator **********************
    for line in fd:            
        if line.strip().startswith("**********"):
            break;

    if dncstateheaderfound == 1:
        for line in fd:            
            if line.strip().startswith("**********"):
                break;
            else:     
                parsed = ''
                parsed = line.strip().split()

                #if the sample has all the information , it must contain 3 tokens
                if len(parsed) == 3:
                    try:
                        tsc = parsed[0] # tsc
                        lss = parsed[1] # LSS name
                        state = int(parsed[2]) # state
                    except  Exception, e:
                        print 'Exception in reading NC D-State sample: ', str(e), '\nSample:', parsed
                        continue
                    
                    if not d_nc_state.has_key(lss):
                        d_nc_state[lss] = [0L, 0L, 0L, 0L]
                        
                    d_nc_state[lss][state] +=  1
                    

    return fd

def parseDStateSCStateSamples(fd, system_info, per_core_info_list, over_all_cpu_info, d_sc_state, sc_device_mapping):

    dscstateheaderfound = 0
    for line in fd:     
        if line.strip().startswith("**********"):
            break;

    if len(sc_device_mapping.keys()) == 0:
        for line in fd:            
            if line.strip().startswith("**********"):
                break;
            else:
                if len(line[:-1].strip()) > 0:
                    identifier = line[:-1].split(':')[0].strip()
                    name = line[:-1].split(':')[1].strip()
                    if not sc_device_mapping.has_key(identifier):
                        sc_device_mapping[identifier] = name

    for line in fd:            
        if line.strip().startswith("TSC"):
            parsed = line.strip().split()
            if len(parsed) == 3 and parsed[2].startswith("State"):
                dscstateheaderfound = 1
            break
    # Skip the separator **********************
    for line in fd:            
        #End of Samples
        if line.strip().startswith("**********"):
            break;

    if dscstateheaderfound == 1:
        for line in fd:            
            if line.strip().startswith("**********"):
                break;
            else:     
                parsed = ''
                parsed = line.strip().split()

                #if the sample has all the information , it must contain 3 tokens
                if len(parsed) == 3:

                    try:
                        tsc = parsed[0] # tsc
                        lss = parsed[1] # LSS name
                        state = int(parsed[2]) # state
                    except  Exception, e:
                        print 'Exception in reading SC D-State sample: ', str(e), '\nSample:', parsed
                        continue
                    
                    if not d_sc_state.has_key(lss):
                        d_sc_state[lss] = []
                    lst = [0, 0, 0, 0]
                    lst[state] = int(tsc, 16)
                    d_sc_state[lss].append(lst)

    return fd

def parseKernelWakelockSamples(fd, system_info, per_core_info_list, over_all_cpu_info, wakelock_dict, wakelock_bucket_dict):
  

    #Skip wakelock Samples
    for line in fd:            
        #Before header line of Wakelocks Samples
        if line.strip().startswith("**********"):
            break;

    wakelockheaderfound = False      
    for line in fd:
    
        if line.strip().startswith("TSC"):
            parsed = line.strip().split()
            if len(parsed) == 9 and parsed[3].startswith("TID") and parsed[8].startswith("Name"):
                wakelockheaderfound = 1
                fd.next()
            break;
    if wakelockheaderfound == 1:
                       
        fd.next()
        for line in fd:
            if line.strip().startswith("**********"):
                break; #end of wl samples
            else:
                parsed = ''
                parsed = line.strip().split(None,6)
                if len(parsed) >= 6:
                    try:
                        tsc = long(parsed[0])  #long
                        lock_type = parsed[1]  #string
                        pid     = parsed[2]    #int/string
                        tid     = parsed[3]    #int/string
                        name    = parsed[4].lstrip()  #string
                        pname   = parsed[6]    #string
                        lock_flag =''  #Not applicable to kl wakelocks
                        wl_tag = ''    #Not applicable to kl wakelocks
                    except  Exception, e :
                        print 'Exception in reading kernel wakelock data: ', str(e), '\nSample: ', parsed
                        continue
                            
                    #older locks that were present before we started collecting data
                    if lock_type == "EXISTING_LOCK":
                        over_all_cpu_info.m_existing_wakelocks_list.append(name)
                        if csv:
                            over_all_cpu_info.m_locks_per_timeslice[0] += 1
                    else:
                        timeout_tsc = 0
                        if lock_type == "LOCK_TIMEOUT":                           
                            lock_type = "LOCK"
                            timeout_tsc = long(parsed[5].strip())
                            #find if the lock is  being overwritten or its a new lock
                            for process in wakelock_dict:
                                for wl in wakelock_dict[process]:
                                    if  wl.m_WL_name == name and wl.m_lock_type == "LOCK" and wl.m_timeout_tsc > 0:
                                        #if current tsc > timeout tsc then its a new lock, else we are overwriting
                                        if tsc <= wl.m_timeout_tsc:
                                            if wl.m_pname ==  pname:
                                                 wl.m_unlock_process = 'Overwritten by: ' + " Self"
                                            else:
                                                wl.m_unlock_process = 'Overwritten by: ' + pname + " (" + pid + ":" + tid + ")"
                                            
                                            wl.m_lock_type = "DONE"                             
                                            wl.m_unlock_tsc = tsc
                                            wl.calculateWLHoldTimeMsec(system_info, wl.m_lock_type)
                                        
                        #name, TID, lock_type, tsc                 
                        pid_name = CompositeWakelockKey( pid, name )
                        if lock_type == "LOCK":
                            if  pid_name in wakelock_dict :
                                if csv:
                                    #add to the right bucket bucket
                                    diff_msec = 0
                                    diff_msec = utility_functions.getCountinMiliseconds((tsc - system_info.m_collection_start_tsc), system_info)
                                    over_all_cpu_info.m_locks_per_timeslice[int(math.floor(diff_msec/system_info.m_time_slice_msec))] += 1
                                wakelock_dict[pid_name].append(Wakelock(name, tid, lock_type, tsc, pname,'',lock_flag, timeout_tsc))

                            else:
                                addProcessToWakelockDict(wakelock_dict, pid_name, wakelock_bucket_dict, name, pid, tid, lock_type, tsc, pname, wl_tag, lock_flag, timeout_tsc)
                                
                        elif lock_type == "UNLOCK":
                            found_match = 0                         
                            for process in wakelock_dict:
                                for wl in wakelock_dict[process]:
                                    if  wl.m_WL_name == name and wl.m_lock_type == "LOCK":
                                        wl.m_unlock_tsc = tsc
                                        if wl.m_pname ==  pname:
                                             wl.m_unlock_process = 'Self'
                                        else:
                                            wl.m_unlock_process = pname + " (" + pid + ":" + tid + ")"                                              
                                        wl.m_lock_type = "DONE"
                                        found_match  = 1
                                        wl.calculateWLHoldTimeMsec(system_info, wl.m_lock_type)
                                        if csv:
                                            diff_msec = utility_functions.getCountinMiliseconds((tsc - system_info.m_collection_start_tsc), system_info)
                                            over_all_cpu_info.m_locks_per_timeslice[int(math.floor(diff_msec/system_info.m_time_slice_msec))] -= 1
                                        break                                                              
                            if found_match == 0:
                                if  pid_name not in wakelock_dict :
                                    addProcessToWakelockDict(wakelock_dict, pid_name, wakelock_bucket_dict, name, pid, tid, lock_type, tsc, pname, wl_tag, lock_flag, timeout_tsc)
                                else:
                                    wakelock_dict[pid_name].append(Wakelock(name, tid, lock_type, tsc, pname, wl_tag, lock_flag))
                
    #Once all the wakelocks have been parsed and Lock/Unlock pairs have been combined.
    #We calculate the time values for locks which were just acquired or just released during the collection.
    #If a lock was just acquired during the collection and never released. The lock time is = (Collection end time - Lock acquired time)
    #If a lock was already acquired when the application began and during the collection it was just released.
    #Lock time = Lock released time - Collection start time
    
    wakelock_nonoverlapping_time_dict = dict()   # A ductionary of lock-unlock times for each lock per process.
 
    for pid_name, wl_obj_list in wakelock_dict.items():
     
        temp_list = list()
        for wl_obj in wl_obj_list:
            if wl_obj.m_lock_type != "DONE":
                if wl_obj.m_timeout_tsc != 0 and wl_obj.m_timeout_tsc < system_info.m_collection_end_tsc:
                    wl_obj.m_lock_type = "DONE"
                    wl_obj.m_unlock_tsc = wl_obj.m_timeout_tsc
                    wl_obj.m_unlock_process = 'Timeout'
                wl_obj.calculateWLHoldTimeMsec(system_info, wl_obj.m_lock_type)
                incrementWLBuckets(wakelock_bucket_dict[pid_name], wl_obj.m_lock_hold_time)
            elif wl_obj.m_lock_type == "DONE":
                 incrementWLBuckets(wakelock_bucket_dict[pid_name], wl_obj.m_lock_hold_time)
            temp_list.append([wl_obj.m_lock_tsc, wl_obj.m_unlock_tsc])
        wakelock_nonoverlapping_time_dict[pid_name] = temp_list

            
    calculate_non_overlapping_lock_time( wakelock_nonoverlapping_time_dict, system_info)
    return fd

def parseUserWakelockSamples(fd, system_info, per_core_info_list, over_all_cpu_info, user_wakelock_dict):

    #Skip wakelock Samples
    for line in fd:            
        #Before header line of Wakelocks Samples
        if line.strip().startswith("**********"):
            break;
    # TSC-TYPE-FLAG-COUNT-PID-UID-TAG-PACKAGE_NAME
    wakelockheaderfound = False      
    for line in fd:
    
        if line.strip().startswith("TSC"):
            parsed = line.strip().split()
            if (len(parsed) == 8 and parsed[1].startswith("TYPE") and parsed[2].startswith("FLAG")
            and parsed[3].startswith("COUNT") and parsed[4].startswith("PID") and parsed[5].startswith("UID")
            and parsed[6].startswith("TAG") and parsed[7].startswith("PACKAGE_NAME")):
                    
                wakelockheaderfound = 1
                fd.next()
            break;

    if wakelockheaderfound == 1:                    
        fd.next()
        for line in fd:
            if line.strip().startswith("**********"):
                break; #end of wl samples
            else:
                parsed = ''
                parsed = line.strip().split('\t',7)
                if len(parsed) >= 7:
                    try:
                        tsc = long(parsed[0].strip())  #long
                        lock_type = parsed[1].strip()  #string
                        lock_flag = parsed[2].strip()
                        count     = parsed[3].strip()
                        pid       = int(parsed[4].strip())      #int/string
                        uid       = int(parsed[5].strip())      #int/string
                        tag       = parsed[6].strip()  #string same as lock name in kernel wl
                        pname     = parsed[7].strip()
                    except  Exception, e:
                        print 'Exception in reading user wakelock data sample: ', str(e), '\nSample:', parsed
                        continue
                    
                    uid_tag = CompositeWakelockKey( uid, tag )
                    if lock_type == "ACQUIRE":
                        lock_type = "LOCK"
                        if  uid_tag in user_wakelock_dict :
                            user_wakelock_dict[uid_tag].append(Wakelock(tag, pid, lock_type, tsc, pname, tag, lock_flag))
                        else:
                            addProcessToWakelockDict(user_wakelock_dict, uid_tag, None, tag, uid, pid, lock_type, tsc, pname, tag, lock_flag)
                            
                    elif lock_type == "RELEASE":
                        lock_type = "UNLOCK"
                        found_match = 0                         
                        if uid_tag in user_wakelock_dict:
                            for wl in user_wakelock_dict[uid_tag]:
                                if  wl.m_WL_TID == pid and wl.m_wl_tag == tag and wl.m_lock_type == "LOCK":
                                    wl.m_unlock_tsc = tsc
                                    wl.m_unlock_process = pid
                                    wl.m_lock_type = "DONE"
                                    found_match  = 1
                                    wl.calculateWLHoldTimeMsec(system_info, wl.m_lock_type)
                                    break
                            if found_match == 0:
                                addProcessToWakelockDict(user_wakelock_dict, uid_tag, None, tag, uid, pid, lock_type, tsc, pname, tag, lock_flag)
                        else:
                            addProcessToWakelockDict(user_wakelock_dict, uid_tag, None, tag, uid, pid, lock_type, tsc, pname, tag, lock_flag)

    wakelock_nonoverlapping_time_dict = dict()   # A ductionary of lock-unlock times for each lock per process.
    for uid_tag, wl_obj_list in user_wakelock_dict.items():  
        temp_list = list()  
        for wl_obj in wl_obj_list:
            if wl_obj.m_lock_type != "DONE":
                wl_obj.calculateWLHoldTimeMsec(system_info, wl_obj.m_lock_type)
            temp_list.append([wl_obj.m_lock_tsc, wl_obj.m_unlock_tsc])
        wakelock_nonoverlapping_time_dict[uid_tag] = temp_list
      
    calculate_non_overlapping_lock_time( wakelock_nonoverlapping_time_dict, system_info)                      
    return fd


def parseThermalSamples(fd, system_info, thermal_list):

    for line in fd:            
        if line.strip().startswith("**********"):
            break;
    thermalheaderfound = False      
    for line in fd:
    
        if line.strip().startswith("TSC"):
            thermalheaderfound = True
            parsed = line.strip().split('\t')
            idx = 1
            while(idx < len(parsed)):
                #mn, max, avg
                if(len(parsed[idx].strip()) == 0):
                    idx += 1
                    continue
                thermal_list.append(componentThermalClass(parsed[idx]))
                idx += 1
            fd.next()
            break;
    sample_count = 0
    if thermalheaderfound:                    
        #fd.next()
        for line in fd:
            if line.strip().startswith("**********"):
                break; #end of thermal samples
            else:
                parsed = ''
                parsed = line.strip().split()
                if len(parsed) > 0:
                    sample_count += 1
                    try:
                        tsc = long(parsed[0]) 
                        idx = 1
                        x = len(parsed)
                        while(idx < len(parsed)):

                            if(int(parsed[idx]) < thermal_list[idx-1].m_min_max_avg[0]):
                                thermal_list[idx-1].m_min_max_avg[0] = int(parsed[idx] )
                            if(int(parsed[idx]) > thermal_list[idx-1].m_min_max_avg[1]):
                                thermal_list[idx-1].m_min_max_avg[1] = int(parsed[idx] )
                            #collecting the sum in the average
                            thermal_list[idx-1].m_min_max_avg[2] += float(parsed[idx])
                            idx += 1

                    except  Exception, e:
                        print 'Exception in reading user thermal data sample: ', str(e), '\nSample:', parsed              
                        continue
        #calculate the averages
        idx = 0
        while(idx < len(thermal_list)):
            thermal_list[idx].m_min_max_avg[2] /= sample_count
            idx += 1
     
    return fd
                                

def parseBandwidthSamples(fd, system_info, bandwidth_list, component_name_line):

    tuples = component_name_line.rpartition(':')

    for line in fd:            
        if line.strip().startswith("**********"):
            break;
    bandwidthheaderfound = False      
    for line in fd:
    
        if line.strip().startswith("TSC"):
            bandwidthheaderfound = True
            bandwidth_obj = componentBandwidthClass(tuples[2].strip())
            fd.next()
            break;
  
    if bandwidthheaderfound == 1:                    
        #fd.next()
        prev_tsc = system_info.m_collection_start_tsc
        parsed = []
        for line in fd:
            if line.strip().startswith("**********"):
                break; #end of thermal samples
            else:
                parsed = []
                parsed = line.strip().split()
                if len(parsed) == 5:
                    try:
                        tsc = long(parsed[0]) 
                        time_dur = utility_functions.getCountinMiliseconds((tsc - prev_tsc), system_info)
                        bandwidth_obj.m_rd32_wr32_rd64_wr64[0] += float(parsed[1])*float(time_dur)
                        bandwidth_obj.m_rd32_wr32_rd64_wr64[1] += float(parsed[2])*float(time_dur)
                        bandwidth_obj.m_rd32_wr32_rd64_wr64[2] += float(parsed[3])*float(time_dur)
                        bandwidth_obj.m_rd32_wr32_rd64_wr64[3] += float(parsed[4])*float(time_dur)
                     
                        prev_tsc = tsc
                       
                    except  Exception, e:
                        print 'Exception in reading user bandwidth data sample: ', str(e), '\nSample:', parsed              
                        continue

        tsc = system_info.m_collection_end_tsc
        time_dur = utility_functions.getCountinMiliseconds((tsc - prev_tsc), system_info)
        bandwidth_obj.m_rd32_wr32_rd64_wr64[0] += float(parsed[1])*float(time_dur)
        bandwidth_obj.m_rd32_wr32_rd64_wr64[1] += float(parsed[2])*float(time_dur)
        bandwidth_obj.m_rd32_wr32_rd64_wr64[2] += float(parsed[3])*float(time_dur)
        bandwidth_obj.m_rd32_wr32_rd64_wr64[3] += float(parsed[4])*float(time_dur)
        tot_time = utility_functions.getCountinMiliseconds((tsc - system_info.m_collection_start_tsc), system_info)
        bandwidth_obj.m_rd32_wr32_rd64_wr64[0] = bandwidth_obj.m_rd32_wr32_rd64_wr64[0]/tot_time
        bandwidth_obj.m_rd32_wr32_rd64_wr64[1] = bandwidth_obj.m_rd32_wr32_rd64_wr64[1]/tot_time
        bandwidth_obj.m_rd32_wr32_rd64_wr64[2] = bandwidth_obj.m_rd32_wr32_rd64_wr64[2]/tot_time
        bandwidth_obj.m_rd32_wr32_rd64_wr64[3] = bandwidth_obj.m_rd32_wr32_rd64_wr64[3]/tot_time
        bandwidth_list.append(bandwidth_obj)
      
    return fd
                                
def parseGPUSamples(fd, system_info, gpu_dict):


    for line in fd:            
        if line.strip().startswith("**********"):
            break;
    gpuheaderfound = False      

    for line in fd:   
        if line.strip().startswith("TSC"):
            gpuheaderfound = True
            fd.next()
            break;
  
    if gpuheaderfound == 1:                    
        #fd.next()
        freq = 0 # needed to handle the last boundary interval
        prev_tsc = system_info.m_collection_start_tsc
        for line in fd:
            if line.strip().startswith("**********"):
                break; #end of thermal samples
            else:
                parsed = ''
                parsed = line.strip().split()
                if len(parsed) == 2:
                    try:
                       #utility_functions.getCountinMiliseconds((tsc - system_info.m_collection_start_tsc), system_info)
                        tsc = long(parsed[0]) 
                        if prev_tsc != 0:
                            freq = float(parsed[1])
                            if freq not in gpu_dict:
                                gpu_dict[freq] = utility_functions.getCountinMiliseconds((tsc - prev_tsc), system_info)
                            else:
                                gpu_dict[freq] += utility_functions.getCountinMiliseconds((tsc - prev_tsc), system_info)
                     
                        prev_tsc = tsc
                    except  Exception, e:
                        print 'Exception in reading user gpu data sample: ', str(e), '\nSample:', parsed              
                        continue
        
      
        # use the last sample frequency as the frequency till the end of collection 
        tsc = system_info.m_collection_end_tsc
        if freq not in gpu_dict:
            gpu_dict[freq] = utility_functions.getCountinMiliseconds((tsc - prev_tsc), system_info)
        else:
            gpu_dict[freq] += utility_functions.getCountinMiliseconds((tsc - prev_tsc), system_info)

    return fd
                                

                
def parseWudump(system_info, dS):

    global debug, utility_functions   
    try:
        fd = open(system_info.m_wudump_input_file,'rb', 1)  
    except IOError: 
        print 'File does not exist :', system_info.m_wudump_input_file
        sys.exit()
        fd.close()

    for line in fd:
       
        if line.startswith("C-State Samples"): 
            fd = parseCStateSamples(fd, system_info, dS.per_core_info_list, dS.over_all_cpu_info)         
        elif line.startswith("P-State Samples"):
            fd = parsePStateSamples(fd, system_info, dS.per_core_info_list, dS.over_all_cpu_info, dS.p_residency, dS.p_timeline)
        elif line.startswith("S-State Samples"):
            fd = parseSStateSamples(fd, system_info, dS.per_core_info_list, dS.over_all_cpu_info, dS.s_residency)
        elif line.startswith("South Complex D-State Residency Samples"):
            fd = parseDStateSCResidencySamples(fd, system_info, dS.per_core_info_list, dS.over_all_cpu_info, dS.d_sc_residency, dS.sc_device_mapping)
        elif line.startswith("North Complex D-State Samples"):
            fd = parseDStateNCStateSamples(fd, system_info, dS.per_core_info_list, dS.over_all_cpu_info, dS.d_nc_state, dS.nc_device_mapping)
        elif line.startswith("South Complex D-State Samples"):
            fd = parseDStateSCStateSamples(fd, system_info, dS.per_core_info_list, dS.over_all_cpu_info, dS.d_sc_state, dS.sc_device_mapping)
        elif line.startswith("Kernel Wakelock Samples"):
            fd = parseKernelWakelockSamples(fd, system_info, dS.per_core_info_list, dS.over_all_cpu_info, dS.wakelock_dict, dS.wakelock_bucket_dict)
        elif line.startswith("User Wakelock Samples"):
            fd = parseUserWakelockSamples(fd, system_info, dS.per_core_info_list, dS.over_all_cpu_info, dS.user_wakelock_dict)
        elif line.startswith("Thermal Samples"):
            fd = parseThermalSamples(fd, system_info, dS.thermal_list)
        elif line.startswith("Bandwidth Samples"):
            fd = parseBandwidthSamples(fd, system_info, dS.bandwidth_list, line)
        elif line.startswith("GPU P-State Samples"):
            fd = parseGPUSamples(fd, system_info, dS.gpu_p_states_dict)


    fd.close()
##############################################################################################################################
#This class contains all the print functions for printing different sets of information
                    
class printOutput:

    global txt, csv, integrity
    
    def __init__(self, system_info):

        global txt, csv

        if(txt):
            try:
                self.FILE_summary = open(system_info.m_output_summary_text_file,'w')
            except IOError as (errorno, strerror):
                print 'Could write to file: ', system_info.m_output_summary_text_file, ' ', strerror
                sys.exit(1)
        if(csv):                
            try:
                self.FILE_csv = open(system_info.m_output_summary_tl_csv_file,'w')
            except IOError as (errorno, strerror):
                print 'Could write to file: ', system_info.m_output_summary_tl_csv_file, ' ', strerror
                sys.exit(1)

        if(integrity):                
            try:
                self.FILE_integrity = open( system_info.m_output_integrity_csv_file ,'w')
            except IOError as (errorno, strerror):
                print 'Could write to file: ',  system_info.m_output_integrity_csv_file , ' ', strerror
                sys.exit(1)


    def cleanup(self):

        global txt, csv  
        if txt :
                self.FILE_summary.close()
        if csv:
                self.FILE_csv.close()
    
    def printAllResults(self, system_info, dS):

        global percore, txt, csv, test

        #in case any erroneous samples were discarded, we ned to remove the time spent in erroneous samples from the total collections time.
        self.checkForDiscardedSamplesTime(system_info,dS.over_all_cpu_info,'sys')    
        if (txt == 1 or (txt == 0 and csv == 0)):
                
                self.OverallInfo(dS.over_all_cpu_info, system_info)                             #Prints information corresponding to the overall system
                self.printResidencyCountSummary(system_info, dS.over_all_cpu_info, 'sys', dS.per_core_info_list)
                self.printHWPResidencyInfo(dS.over_all_cpu_info, dS.per_core_info_list, system_info)          #Prints P-State Residency information
                self.printOSPResidencyInfo(dS.p_residency, system_info)  
                self.printwakeupTables(system_info, dS.over_all_cpu_info, 'sys', dS.per_core_info_list)
                self.printWakeUpMetrics(system_info, dS.over_all_cpu_info, 'sys')

        
                if dS.over_all_cpu_info.m_wake_up_counts_map['ALL'] > 0:          
                    self.printWakeUPEventsBuckets(system_info, dS.over_all_cpu_info)              #Prints wakeup buckets for the overall system
                    self.printWakeUPEventsActiveBuckets(system_info, dS.over_all_cpu_info)
                if percore:
                        self.printCPUSpecificInfo(dS.per_core_info_list, dS.p_residency, system_info)               #Prints information for each CPU
                
                if test == 1: self.printSResidencyInfo(dS.per_core_info_list, dS.s_residency, system_info)                             #Prints S-State Residency information
                if test == 1: self.printDNCStateInfo(dS.per_core_info_list, dS.d_nc_state,system_info, dS.nc_device_mapping)           #Prints North complex D-State information
                if test == 1: self.printDSCResidencyInfo(dS.per_core_info_list, dS.d_sc_residency, system_info, dS.sc_device_mapping)  #Prints South complex D-State Residency information
                self.printWLBuckets(system_info, dS.wakelock_bucket_dict, dS.wakelock_dict)
                self.printKernelWLInfo(dS.wakelock_dict, dS.over_all_cpu_info)
                self.printUserWLInfo(dS.user_wakelock_dict, dS.over_all_cpu_info)
                if test == 1: self.printThermalInfo(dS.thermal_list)
                if test == 1: self.printBandwidthInfo(dS.bandwidth_list)
                if test == 1: self.printGpuInfo(dS.gpu_p_states_dict, system_info)
                self.textSummaryWriter('################################################################################################################\n')        
                if test == 1: self.textSummaryWriter('Original Total Collection Time = ' + str(system_info.m_collection_time ) + '\n\n')
                self.textSummaryWriter(utility_functions.errorSamples)

        #close all open resources
        if(csv or integrity):
            self.printCSVFile(system_info, dS)
        
        self.cleanup()
      
    def textSummaryWriter(self, string):
            if txt == 0 and csv == 0:                   
                    sys.stdout.write(string)
            else:
                if txt:
                    self.FILE_summary.write(string)
                elif csv:
                    self.FILE_csv.write(string)
                 
    def checkForDiscardedSamplesTime(self, system_info, WakeUpDetailsObject, info_type):

        totalResidencyCount = 0

        for key, value in  WakeUpDetailsObject.m_residency_info_map.items():
            totalResidencyCount = totalResidencyCount + value.m_res_count

        #convert the total residency count into time in msec       
        total_time_msec = utility_functions.getCountinMiliseconds((totalResidencyCount), system_info)
        total_time_sec =  total_time_msec / 1000
        
        if info_type == 'sys':
            total_time_sec /= system_info.m_core_count
        
        if total_time_sec != system_info.m_collection_time:
            WakeUpDetailsObject.m_net_collection_time = total_time_sec
            #system_info.m_discarded_samples_time = system_info.m_collection_time - total_time_sec
            #system_info.m_collection_time =  total_time_sec
     
    def OverallInfo(self, over_all_cpu_info, system_info):
     
        #calculate wake-ups per second for all cpu
        #wakeup rate must be calculated from the original time.
        over_all_cpu_info.m_wakeups_per_sec = utility_functions.getRate(over_all_cpu_info.m_wake_up_counts_map['ALL'],system_info.m_collection_time)
        wakeups_p_sec_p_cpu = utility_functions.getRate(over_all_cpu_info.m_wakeups_per_sec , system_info.m_core_count)
        
        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('SoCWatch: Advanced CPU C-state Analysis\nCollected: ')+ strftime("%Y-%m-%d %H:%M:%S %Z") + '\n')
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        
        if over_all_cpu_info.m_wake_up_counts_map['ALL'] == 0:
            self.textSummaryWriter( str('# Total Collection Time = {0:.2f} secs'.format(system_info.m_collection_time) + '\n'))
            return
        else:
            #in case any erroneous samples were discarded, we ned to remove the time spent in erroneous samples from the total collections time.
            if(system_info.m_collection_time != over_all_cpu_info.m_net_collection_time):
                 self.textSummaryWriter(str('# Total Collection Time = {0:.2f} secs'.format(over_all_cpu_info.m_net_collection_time) + '\n'))
            else:
                self.textSummaryWriter(str( '# Total Collection Time = {0:.2f} secs'.format(system_info.m_collection_time) +'\n'))
   
        self.textSummaryWriter(str('# Total number of C-State Wake Ups =:').ljust(37) + str(over_all_cpu_info.m_wake_up_counts_map['ALL']).ljust(16) +
               str('## Wake-Ups/second/core =: ') + str(round(wakeups_p_sec_p_cpu,2)) +' WU/sec/core \n\n')
        
        if(test == 1):
            self.textSummaryWriter(str('# Number of Timer Wake-Ups =: ').ljust(37) + str(over_all_cpu_info.m_wake_up_counts_map['PID']).ljust(16) +
                   str('## Percentage of Timer Wake-Ups =: ').ljust(39) + str(round(utility_functions.getPercentage(over_all_cpu_info.m_wake_up_counts_map['PID'],
                                                                                                                over_all_cpu_info.m_wake_up_counts_map['ALL']), 2)).ljust(5) + ' %\n')
        
            self.textSummaryWriter(str('# Number of Interrupt Wake-Ups =:').ljust(37) + str(over_all_cpu_info.m_wake_up_counts_map['IRQ']).ljust(16) +
                   str('## Percentage of Interrupt Wake-Ups =:').ljust(39) + str(round(utility_functions.getPercentage(over_all_cpu_info.m_wake_up_counts_map['IRQ'],
                                                                                                                over_all_cpu_info.m_wake_up_counts_map['ALL']), 2)).ljust(5) + ' %\n')
        
            self.textSummaryWriter(str('# Number of IPI Wake-Ups =:').ljust(37) + str(over_all_cpu_info.m_wake_up_counts_map['IPI']).ljust(16) +
                   str('## Percentage of IPI Wake-Ups =:').ljust(39) + str(round(utility_functions.getPercentage(over_all_cpu_info.m_wake_up_counts_map['IPI'],
                                                                                                                over_all_cpu_info.m_wake_up_counts_map['ALL']), 2)).ljust(5) + ' %\n')
        
            self.textSummaryWriter(str('# Number of WQExec Wake-Ups =:').ljust(37)+str(over_all_cpu_info.m_wake_up_counts_map['WQExec']).ljust(16) +
                   str('## Percentage of WQExec Wake-Ups =:').ljust(39) + str(round(utility_functions.getPercentage(over_all_cpu_info.m_wake_up_counts_map['WQExec'],
                                                                                                                  over_all_cpu_info.m_wake_up_counts_map['ALL']), 2)).ljust(5)+ ' %\n')
        
            self.textSummaryWriter(str('# Number of Scheduler Wake-Ups =:').ljust(37) + str(over_all_cpu_info.m_wake_up_counts_map['Scheduler']).ljust(16) +
                   str('## Percentage of Scheduler Wake-Ups =:').ljust(39) + str(round(utility_functions.getPercentage(over_all_cpu_info.m_wake_up_counts_map['Scheduler'],
                                                                                                                     over_all_cpu_info.m_wake_up_counts_map['ALL']), 2)).ljust(5) + ' %\n')
        
            self.textSummaryWriter(str('# Number of Unknown Wake-Ups =:').ljust(37)+str(over_all_cpu_info.m_wake_up_counts_map['Unknown']).ljust(16) +
                   str('## Percentage of Unknown Wake-Ups =:').ljust(39) + str(round(utility_functions.getPercentage(over_all_cpu_info.m_wake_up_counts_map['Unknown'],
                                                                                                                   over_all_cpu_info.m_wake_up_counts_map['ALL']), 2)).ljust(5) + ' %\n\n')      
            if show_promotion:  
                     self.textSummaryWriter(str('# No. of C-State Promotions =:').ljust(37)+str(over_all_cpu_info.m_promotion_demotion_count_list[0]).ljust(16) +
                           str('## Percentage of C-State Promotions =:').ljust(39) + str(round(utility_functions.getPercentage(over_all_cpu_info.m_promotion_demotion_count_list[0],
                                                                                                                             (over_all_cpu_info.m_wake_up_counts_map['ALL'] +
                                                                                                                              sum(over_all_cpu_info.m_intermediate_sample_count.values()))), 2)).ljust(5) + ' %\n')
                                        
            self.textSummaryWriter(str('# No. of C-State Demotions =:').ljust(37) + str(over_all_cpu_info.m_promotion_demotion_count_list[1]).ljust(16)
                   + str('## Percentage of C-State Demotions =:').ljust(39) + str(round(utility_functions.getPercentage(over_all_cpu_info.m_promotion_demotion_count_list[1],
                                                                                                                       (over_all_cpu_info.m_wake_up_counts_map['ALL'] +
                                                                                                                         sum(over_all_cpu_info.m_intermediate_sample_count.values()))), 2)).ljust(5) + ' %\n')
        
         
            self.textSummaryWriter(str('# No. of Abort Samples =:').ljust(37) + str(over_all_cpu_info.abort_sample_count).ljust(16))
            self.textSummaryWriter("\n\n")
            
    def printCPUSpecificInfo(self, per_core_info_list, p_residency, system_info):

        self.textSummaryWriter("\n")
        self.textSummaryWriter('--------------------------------------\n')
        self.textSummaryWriter(str('CORE SPECIFIC INFORMATION').ljust(120) + '\n')
        self.textSummaryWriter('--------------------------------------\n')
        ind = 0
        while ind < system_info.m_core_count:
            core_number  = ind
            #core_number = system_info.m_core_count - 1
            
            self.textSummaryWriter(str('******').ljust(50) + '\n')
            self.textSummaryWriter(str('CORE ') + str(core_number)+'\n')
            self.textSummaryWriter(str('******').ljust(50)+'\n')
            
            self.textSummaryWriter('* Total number of wake ups = ' +  str(per_core_info_list[core_number].m_wake_up_counts_map['ALL']) +'\n')
            #wakeup rate must be calculated from original total time.
            self.textSummaryWriter('* Wake up Rate = {0:.2f} WU/sec\n'.format(utility_functions.getRate(per_core_info_list[core_number].m_wake_up_counts_map['ALL'],system_info.m_collection_time))+'\n') 

            #in case any erroneous samples were discarded, we ned to remove the time spent in erroneous samples from the total collections time.
            self.checkForDiscardedSamplesTime(system_info,per_core_info_list[core_number],'cpu')
       
            if debug and (system_info.m_collection_time != per_core_info_list[core_number].m_net_collection_time):
                print '# Net Collection Time* = {0:.2f} secs'.format(per_core_info_list[ind].m_net_collection_time)
                print' Net Collection Time =  Total collection time - Time consumed by erroneous samples\n'

            self.textSummaryWriter(' ------------------------CORE ' + str(core_number) +  ' RESIDENCY INFORMATION -------------------------------------- \n\n')
            if test == 1:
                self.printResidencyCountSummary(system_info, per_core_info_list[core_number], 'core', per_core_info_list)
            self.printwakeupTables(system_info, per_core_info_list[core_number], 'core')
            self.printWakeUpMetrics(system_info, per_core_info_list[core_number], 'core')
            ind += 1
                    
    def printwakeupTables(self, system_info, WakeUpDetailsObject, info_type, per_core_info_list=None):

        if WakeUpDetailsObject.m_wake_up_counts_map['ALL'] == 0:
                return
        
        #Prints all tables depending on the object sent as argument i.e. system-wide/percpu
        if test == 1:
            self.printCStatesVsWakeupReason(system_info, WakeUpDetailsObject, info_type)
        self.printIncorrectCStatesUsed(system_info, WakeUpDetailsObject, info_type)
        if test == 1:
            self.printTop10WakeUPs(system_info, WakeUpDetailsObject, info_type)
            self.printTop10Interrupts(system_info, WakeUpDetailsObject, info_type)
            self.printTop10Timers(system_info, WakeUpDetailsObject, info_type)
        self.printbuckets(system_info, WakeUpDetailsObject, info_type)
        
    def printCStatesVsWakeupReason(self, system_info, WakeUpDetailsObject, info_type):
        global debug, test
        global utility_functions

        if WakeUpDetailsObject.m_wake_up_counts_map['ALL'] == 0:
                return

        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('C States Vs. Wakeup Reasons (Instances)'.ljust(120)+'\n'))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')

        self.textSummaryWriter(str(' ').ljust(5) + str('Total').rjust(10) + str('Timer').rjust(10) + str('Interrupt').rjust(15) +
                                str('IPI').rjust(15) + str('WQExec').rjust(15) + str('Scheduler').rjust(15) + str('Unknown').rjust(15)+'\n')     
        for key, value in  sorted(WakeUpDetailsObject.m_residency_info_map.items()):
            if key != '0' and value.m_sleep_state_hit_count > 0:
                self.textSummaryWriter(("C" + str(key).ljust(5) + str(value.m_sleep_state_hit_count).rjust(5) +
                       str(value.m_wakeup_specific_hit_count['Timer']).rjust(10)     + str(value.m_wakeup_specific_hit_count['IRQ']).rjust(15) +
                       str(value.m_wakeup_specific_hit_count['IPI']).rjust(15)       + str(value.m_wakeup_specific_hit_count['WQExec']).rjust(15) +
                       str(value.m_wakeup_specific_hit_count['Scheduler']).rjust(15) + str(value.m_wakeup_specific_hit_count['Unknown']).rjust(15)) + '\n')
            
        self.textSummaryWriter('\n\n')


    def printResidencyCountSummary(self, system_info, WakeUpDetailsObject, info_type, per_core_info_list = None):

        global debug, utility_functions, csv, test

        #check if any residency data was collected
        if  not WakeUpDetailsObject.m_residency_info_map:
            return
        totalResCountOverAllCpu = 0

        try:
            for key, value in  sorted(WakeUpDetailsObject.m_residency_info_map.items()):
                totalResCountOverAllCpu = totalResCountOverAllCpu + value.m_res_count

            if debug:
                print 'Total res count is ' , totalResCountOverAllCpu

            if csv:
                file_writer =  self.FILE_csv.write
                file_writer('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
                file_writer(str('C-STATE RESIDENCY SUMMARY'))
                file_writer('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
                file_writer(str(', , , ,RESIDENCY(%),') + '\n')
                file_writer(str('C STATE,'))
               
            else:
                file_writer = self.textSummaryWriter
                file_writer('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
                file_writer(str('C-STATE RESIDENCY SUMMARY'.ljust(120) + '\n'))
                file_writer('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
                file_writer(('RESIDENCY(%)').center(55) + '\n')
                file_writer(str('C STATE').center(5) + " ".rjust(8))
              
                
            if info_type == "sys":
                for pkg in WakeUpDetailsObject.m_package_residency:
                    if csv:
                        file_writer(str('Package' + str(pkg)) + ',')
                    else:
                        file_writer(str('Package' + str(pkg)).rjust(10))
                    for module in WakeUpDetailsObject.m_package_residency[pkg].m_modules:
                        if csv:
                            file_writer(str('Module' + str(module)) + ',')
                        else:
                            file_writer(str('Module' + str(module)).rjust(10))
                    for core in WakeUpDetailsObject.m_package_residency[pkg].m_cores:
                        if csv:
                            file_writer(str('Core' + str(core)) + ',')
                        else:
                            file_writer(str('Core' + str(core)).rjust(10))
            """
            if info_type == "core":
                totalResCountPerCore = 0
                totalResCountPerCore = WakeUpDetailsObject.m_residency_info_map.m_res_count
            """          
            #sorted(mydict, key=lambda key: mydict[key])
            file_writer(str('\n\n'))                    

            for state in  sorted(system_info.m_sleep_states):
                if debug:
                    print 'State ', state, '  Rescount ', value.m_res_count
                res_percentage = 0           
                if totalResCountOverAllCpu > 0:
                    res_percentage = utility_functions.getPercentage(value.m_res_count, totalResCountOverAllCpu)
          
                if csv:
                    file_writer("C" + str(state) + ',') 
                else:
                    file_writer("C" + str(state).ljust(10)) 

                if info_type == "sys":     
                    
                    for pkg in sorted(WakeUpDetailsObject.m_package_residency, key=lambda key:WakeUpDetailsObject.m_package_residency[key]):
                        if state not in WakeUpDetailsObject.m_package_residency[pkg].m_c_res:
                            if csv:
                                file_writer('-,')
                            else:
                                file_writer('-'.rjust(10))
                        else:
                            perc = utility_functions.getPercentage(WakeUpDetailsObject.m_package_residency[pkg].m_c_res[state], ((totalResCountOverAllCpu/system_info.m_core_count)))
                            perc = perc/(len(WakeUpDetailsObject.m_package_residency[pkg].m_cores))
                            if csv:
                                file_writer(str(round(perc, 2)) + ',')
                            else:
                                file_writer(str(round(perc, 2)).rjust(10))

                        for module in sorted(WakeUpDetailsObject.m_package_residency[pkg].m_modules,key=lambda key:WakeUpDetailsObject.m_package_residency[pkg].m_modules[key] ):
                            if state not in WakeUpDetailsObject.m_package_residency[pkg].m_modules[module].m_c_res:
                                if csv:
                                    file_writer('-,')
                                else:
                                    file_writer('-'.rjust(10))
                            else:
                                perc = utility_functions.getPercentage(WakeUpDetailsObject.m_package_residency[pkg].m_modules[module].m_c_res[state], (totalResCountOverAllCpu/system_info.m_core_count))
                                perc = perc/(WakeUpDetailsObject.m_package_residency[pkg].m_modules[module].m_core_count)
                                if csv:
                                    file_writer(str(round(perc, 2)) + ',')
                                else:
                                    file_writer(str(round(perc, 2)).rjust(10))
                               

                        for core in range(system_info.m_core_count):
                            if core not in WakeUpDetailsObject.m_package_residency[pkg].m_cores:
                                continue
                            if state not in WakeUpDetailsObject.m_package_residency[pkg].m_cores[core].m_c_res:
                                if csv:
                                    file_writer('-,')
                                else:
                                    file_writer('-'.rjust(10))
                                    
                            else:
                                perc = utility_functions.getPercentage(WakeUpDetailsObject.m_package_residency[pkg].m_cores[core].m_c_res[state], (totalResCountOverAllCpu/system_info.m_core_count))
                                if csv:
                                    file_writer(str(round(perc, 2)) + ',')
                                else:
                                    file_writer(str(round(perc, 2)).rjust(10))
                               
                                if debug:
                                    print 'Core ', core, ', State ', state, '  Rescount ', WakeUpDetailsObject.m_package_residency[pkg].m_cores[core].m_c_res[state]
                        
                if info_type == "core":
                    
                    if state not in WakeUpDetailsObject.m_residency_info_map:
                        if csv:
                            file_writer('-,')
                        else:
                            file_writer('-'.rjust(10))
                    else: 
                        if debug:
                            print 'Core ------',', State ', state, '  Rescount ', WakeUpDetailsObject.m_residency_info_map[state].m_res_count,' Total ', totalResCountOverAllCpu     
                        perc = utility_functions.getPercentage(WakeUpDetailsObject.m_residency_info_map[state].m_res_count, totalResCountOverAllCpu) 
                                              
                        if csv:
                            file_writer(str(round(perc, 2)) + ',')
                        else:
                            file_writer(str(round(perc, 2)).rjust(10))
                  
                file_writer(str('\n'))
                
        except Exception, e:
            print 'Exception occured in printResidencyCountSummary ', str(e)
            sys.exit(1)

        file_writer(str('\n'))
                
    
    """
    def printResidencyCountSummaryold(self, system_info, WakeUpDetailsObject, info_type, per_core_info_list = None):

        global debug, utility_functions
        #check if any residency data was collected
        if  not WakeUpDetailsObject.m_residency_info_map:
            return

        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('C-STATE RESIDENCY SUMMARY'.ljust(120) + '\n'))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        totalResCountOverAllCpu = 0
        try:
            for key, value in  sorted(WakeUpDetailsObject.m_residency_info_map.items()):
                totalResCountOverAllCpu = totalResCountOverAllCpu + value.m_res_count

            if debug:
                print 'Total res count is ' , totalResCountOverAllCpu

            self.textSummaryWriter(repr('RESIDENCY(%)').center(35) + '\n')
            self.textSummaryWriter(repr('C STATE').center(5) + repr('Overall').rjust(13))

            if info_type == "sys":
                for pkg in WakeUpDetailsObject.m_package_residency:
                    self.textSummaryWriter(str('Package' + str(pkg)).rjust(10))

                totalResCountPerCore = [0.0] * system_info.m_core_count
                for core in range(system_info.m_core_count):
                    self.textSummaryWriter(str('Core' + str(core)).rjust(10))
                    try:
                        for key, value in  per_core_info_list[core].m_residency_info_map.items():
                            totalResCountPerCore[core] = totalResCountPerCore[core] + value.m_res_count
                    except KeyError:
                        totalResCountPerCore[core] = totalResCountPerCore[core] + 0
            
                
            self.textSummaryWriter(str('\n\n'))                    
            for state, value in  sorted(WakeUpDetailsObject.m_residency_info_map.items()):
                if debug:
                    print 'State ', state, '  Rescount ', value.m_res_count
                res_percentage = 0           
                if totalResCountOverAllCpu > 0:
                    res_percentage = utility_functions.getPercentage(value.m_res_count, totalResCountOverAllCpu)
                #Check for intermediate state (e.g. 1.5, 2.5 etc.)
                if (isIntermediateState(state)):
                    self.textSummaryWriter("*  C" + str(int(state)) + "i".ljust(10) + str(round(res_percentage, 2)).rjust(6)[:6])
                else:
                    self.textSummaryWriter("*  C" + str(int(state)).ljust(10) + str(round(res_percentage, 2)).rjust(6)[:6])
                
                if info_type == "sys":     
                    
                    for pkg in sorted(WakeUpDetailsObject.m_package_residency.items()):
                        if state < 2:
                            self.textSummaryWriter('-'.rjust(10))
                        else:
                            if debug:
                                print 'pkg ', pkg, 'state ', state, 'rescount ', WakeUpDetailsObject.m_package_residency[pkg][int(state)], 'total ',  sum(WakeUpDetailsObject.m_package_residency[pkg])
                            perc = utility_functions.getPercentage(WakeUpDetailsObject.m_package_residency[pkg][int(state)], sum(WakeUpDetailsObject.m_package_residency[pkg]))
                            self.textSummaryWriter(str(round(perc, 2)).rjust(10)[:10])
                    for core in range(system_info.m_core_count):
                        try:
                            if debug:
                                print 'core ', core, 'state ', state, 'rescount ', per_core_info_list[core].m_residency_info_map[state].m_res_count, 'total ',  totalResCountPerCore[core]
                            perc = utility_functions.getPercentage(per_core_info_list[core].m_residency_info_map[state].m_res_count, totalResCountPerCore[core])
                        except KeyError:
                            perc = 0       
                        self.textSummaryWriter(str(round(perc, 2)).rjust(10)[:10])
                 
                self.textSummaryWriter(str('\n'))
                
        except Exception, e:
            print 'Exception occured in printResidencyCountSummary ', str(e)
            sys.exit(1)

        self.textSummaryWriter("\n")
    """

    def printIncorrectCStatesUsed(self, system_info, WakeUpDetailsObject, info_type):

        if WakeUpDetailsObject.m_wake_up_counts_map['ALL'] == 0:
                return
        global debug, csv, test
        global utility_functions     
        
        if csv:
            file_writer = self.FILE_csv.write
        else:
            file_writer = self.textSummaryWriter

        file_writer('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        file_writer(str('INCORRECT C-STATES USED' + '\n'))
        file_writer('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        if csv:
            file_writer(str('C STATE,') + str('Wasted Power Metrics, ,') +
                                    str('Opportunity Lost Metrics, ,') + str('% Poor Decisions') + '\n')
            file_writer((' ,Instances(%),') + str('Res Count(%),') + str('Instances(%),') + str('Res Count(%),,') + '\n')
            file_writer('\n')
        else:
            file_writer(str('C STATE').ljust(10) + str('Wasted Power Metrics').rjust(30) +
                                    str('Opportunity Lost Metrics').rjust(50) + str('% Poor Decisions').rjust(31) + '\n')
            file_writer("\n\n")
            file_writer(('Instances(%)').rjust(25) + str('Res Count(%)').rjust(20) + str('Instances(%)').rjust(30) + str('Res Count(%)').rjust(19) + '\n')
            file_writer('\n')
            
        totalWastedPower        = 0
        totalOppurtunityLost    = 0
        totalWastedPowerRes     = 0
        totalOppurtunityLostRes = 0
        totalResCountOverAllCpu = 0       
         
        for key, value in sorted(WakeUpDetailsObject.m_residency_info_map.items()):
            if key != '0':
                # 0:rescout total ,1:number of Cx breaks, < x rescount,> x rescount
                powerWastedP = 0
                oppurtunityLostP = 0
                if  value.m_sleep_state_hit_count > 0 and (value.m_lower_threshold_count > 0 or value.m_upper_threshold_count > 0) :
                
                    oppurtunityLostP = value.oppurtunityLostPercentage(key, WakeUpDetailsObject)
                    powerWastedP     = value.powerWastedPercentage()

                    #Sum the information for all states , this data will be used to calculated wasted power over all C States combined

                    if (isIntermediateState(key) == False):  #intermediate states cannot provide the power wasted statistic
                        totalWastedPower        += value.m_lower_threshold_count
                        totalWastedPowerRes     += value.m_lower_threshold_rescount
                
                    totalOppurtunityLost    += value.m_upper_threshold_count 
                    totalOppurtunityLostRes += value.m_upper_threshold_rescount

                    wastedPowerResP = utility_functions.getPercentage(value.m_lower_threshold_rescount, value.m_res_count)
                    oppLostResP     = utility_functions.getPercentage(value.m_upper_threshold_rescount, value.m_res_count)
             
                    totalResCountOverAllCpu = totalResCountOverAllCpu + value.m_res_count 

                    ##########################################################################################################################################
                    if csv:
                        if key == system_info.m_deepest_state:
                            file_writer(("C" + str(key) + ',' + str(round(powerWastedP,2)) + ',' + str(round(wastedPowerResP, 2)) + ','
                                   + str("-") + ',' + str("-") + ',' + str(round((powerWastedP), 2)).rjust(22)) + '\n')
                        elif (isIntermediateState(key)):
                            file_writer(("C" + str(key) + str("-,") + str("-,") +
                                   str(round(oppurtunityLostP, 2)) + ',' + str(round(oppLostResP, 2)) + ',' + str(round((oppurtunityLostP), 2))) + '\n')
                        else:
                            file_writer(("C" + str(key) + ',' + str(round( powerWastedP, 2)) + ',' + str(round(wastedPowerResP, 2)) + ',' +
                                   str(round(oppurtunityLostP, 2)) + ',' + str(round(oppLostResP, 2)) + ',' + str(round((powerWastedP + oppurtunityLostP), 2))) + '\n')

                    else:
                        if key == system_info.m_deepest_state:
                            file_writer(("C" + str(key).ljust(10) + str(round(powerWastedP,2)).rjust(10)+str(round(wastedPowerResP, 2)).rjust(15)+
                                   str("-").rjust(30) + str("-").rjust(23) + str(round((powerWastedP), 2)).rjust(22)) + '\n')
                        elif (isIntermediateState(key)):
                            file_writer(("C" + str(key).ljust(10) + str("-").rjust(7)+str("-").rjust(15)+
                                   str(round(oppurtunityLostP, 2)).rjust(32)+str(round(oppLostResP, 2)).rjust(25) + str(round((oppurtunityLostP), 2)).rjust(20)) + '\n')
                        else:
                            file_writer(("C" + str(key).ljust(10) + str(round( powerWastedP, 2)).rjust(10) + str(round(wastedPowerResP, 2)).rjust(15)+
                                   str(round(oppurtunityLostP, 2)).rjust(30)+str(round(oppLostResP, 2)).rjust(25) + str(round((powerWastedP + oppurtunityLostP), 2)).rjust(20)) + '\n')

                    ##########################################################################################################################################
                    
        #These metrics represent the wasted power and oppurtunity lost over all wake-ups . 
        wastedPowerOverAllBreaks      = 0
        oppurtunityLostOverAllBreaks  = 0

        wastedPowerOverAllBreaks     = utility_functions.getPercentage(totalWastedPower, WakeUpDetailsObject.m_wake_up_counts_map['ALL'])
        # For the oppurtunity lost table we also take into account the intermediate states 
        oppurtunityLostOverAllBreaks = utility_functions.getPercentage(totalOppurtunityLost, (WakeUpDetailsObject.m_wake_up_counts_map['ALL'] +
                                                                                              sum(WakeUpDetailsObject.m_intermediate_sample_count.values())))
        totalWastedPowerResP         =   utility_functions.getPercentage(totalWastedPowerRes, totalResCountOverAllCpu)
        totalOppLostResP             =   utility_functions.getPercentage(totalOppurtunityLostRes, totalResCountOverAllCpu)

        ##########################################################################################################################################
        if csv:
            file_writer(str("   Totals,") + str(round(wastedPowerOverAllBreaks, 2)) + ',' +
                                    str(round(totalWastedPowerResP, 2)) + ',' + str(round(oppurtunityLostOverAllBreaks, 2)) + ',' +
                                    str(round(totalOppLostResP, 2)) + ',' + str(round((wastedPowerOverAllBreaks+oppurtunityLostOverAllBreaks), 2)) + '\n')
            file_writer('(over all sleep states)\n')
        else:
            file_writer('\n-----------------------------------------------------------------------------------------------------------------\n')
            file_writer(str("   Totals").ljust(14) + str(round(wastedPowerOverAllBreaks, 2)).rjust(10) +
                                    str(round(totalWastedPowerResP, 2)).rjust(15)+ str(round(oppurtunityLostOverAllBreaks, 2)).rjust(30) +
                                    str(round(totalOppLostResP, 2)).rjust(25) + str(round((wastedPowerOverAllBreaks+oppurtunityLostOverAllBreaks), 2)).rjust(20) + '\n')
            file_writer('(over all sleep states)\n')
            file_writer('\n------------------------------------------------------------------------------------------------------------------')
        file_writer('\n\n')
        ##########################################################################################################################################
  
    def printTop10WakeUPs(self, system_info, WakeUpDetailsObject, info_type):

        if WakeUpDetailsObject.m_wake_up_counts_map['ALL'] == 0:
                return
        global debug, test
        global utility_functions    
        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('TOP 10 CAUSES OF C STATE WAKE-UPS' + '\n'))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')

        CStatestr = ''
        for key, value in sorted(WakeUpDetailsObject.m_residency_info_map.items()):
            if key != '0':
                CStatestr += str(' ').rjust(20) + 'C' + str(key).ljust(5)

        merged = utility_functions.mergeTwoDictionaries(WakeUpDetailsObject.m_irq_wakeups_details_map, WakeUpDetailsObject.m_timer_wakeups_details_map) 
        #Create a dictionary to store all wake-up reasons (processes/irqs etc) with wakeup counts for each 
        wakeup_counts_allcauses = dict()
                          
        for key, value in merged.items():
            wakeup_counts_allcauses[key] = value.m_wakeup_count
          
        if WakeUpDetailsObject.m_wake_up_counts_map['Unknown'] > 0:
            wakeup_counts_allcauses['Unknown'] = WakeUpDetailsObject.m_wake_up_counts_map['Unknown']
           
        if WakeUpDetailsObject.m_wake_up_counts_map['IPI'] > 0:
            wakeup_counts_allcauses['IPI'] = WakeUpDetailsObject.m_wake_up_counts_map['IPI']

        if WakeUpDetailsObject.m_wake_up_counts_map['WQExec'] > 0:
            wakeup_counts_allcauses['WQExec'] = WakeUpDetailsObject.m_wake_up_counts_map['WQExec']

        if WakeUpDetailsObject.m_wake_up_counts_map['Scheduler'] > 0:
            wakeup_counts_allcauses['Scheduler'] = WakeUpDetailsObject.m_wake_up_counts_map['Scheduler']
           
        totalCauses = len(wakeup_counts_allcauses)
        toptenp = 10
        if totalCauses < 10:
            toptenp = totalCauses
    
        self.textSummaryWriter(str(' Wakeup Reason').rjust(22), )
          
        self.textSummaryWriter(str('Total').rjust(25),)
        for key, value in sorted(WakeUpDetailsObject.m_residency_info_map.items()):
            if key != '0':
                self.textSummaryWriter(str('C').rjust(6) + str(key).ljust(3), )

        #print the cpu list only for overall information and not for per cpu information
        #if info_type == 'sys':
        self.textSummaryWriter(str(' CPU''s').rjust(15), )
        #else:
        #self.textSummaryWriter(str(' ').rjust(3), )
            
        self.textSummaryWriter('\n\n')
        i = 1
        prev = 0
        curr = 0
        #sort by value i.e sort by the wu counts in descending order
        for key, value in sorted(wakeup_counts_allcauses.items(), key=itemgetter(1), reverse=True):
         
            if i <= toptenp:
                if key in WakeUpDetailsObject.m_timer_wakeups_details_map:
                    wakeup = WakeUpDetailsObject.m_timer_wakeups_details_map[key]
                    self.textSummaryWriter(str(merged[key].m_type) + '-' + str(key).ljust(10) + str(merged[key].m_name).ljust(25), )
                    
                #During the merge of the two dictionaries if we find a key repeptiition , one of the keys is negated and multiplied by 100 and added to the map
                #This works for our case as al the keys are expected to be +ive , and if they are not , such a sample with a -ive id will be removed as an erroneous sample
                #When a negative key is found , it is first made positive, divided by 100 and the corresponding sample is printed
                elif str(key).startswith('-'):                  
                    key   = int(key) * (-1)
                    key   = str(key/100) 
                    wakeup = WakeUpDetailsObject.m_irq_wakeups_details_map[key]
                    self.textSummaryWriter(str('IRQ-') + str(key).ljust(10)  + str(WakeUpDetailsObject.m_irq_wakeups_details_map[key].m_name).ljust(25),)                 
                
                elif WakeUpDetailsObject.m_irq_wakeups_details_map.has_key(key):
                    wakeup = WakeUpDetailsObject.m_irq_wakeups_details_map[key]
                    self.textSummaryWriter(str(merged[key].m_type) + '-' + str(key).ljust(10) + str(merged[key].m_name).ljust(25),)
                    
                else:
                    wakeup = WakeUpDetailsObject.m_other_wakeups_details_map[key]
                    self.textSummaryWriter(str(key).ljust(37) + '  ', )

                self.textSummaryWriter(str(wakeup.m_wakeup_count).rjust(5), )
                curr = wakeup.m_wakeup_count
                
                for key_res,value_res in sorted(WakeUpDetailsObject.m_residency_info_map.items()):
                    if  key_res != '0':
                        self.textSummaryWriter(str(wakeup.get_wakeup_count_by_state(key_res) ).rjust(8), )

                #Print cpu list only for system-wide information
                #if info_type == 'sys':
                self.textSummaryWriter(' '.center(15))
                self.textSummaryWriter(wakeup.get_cpu_list().ljust(30), )
                                                    
                self.textSummaryWriter('\n')
                if prev != curr:
                    i += 1
                prev = curr
            elif i > toptenp:
                break            
        self.textSummaryWriter('\n')
                
    def printTop10Interrupts(self, system_info, WakeUpDetailsObject, info_type):

        if WakeUpDetailsObject.m_wake_up_counts_map['ALL'] == 0:
                return

        global debug, utility_functions, test
        
        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('TOP 10 INTERRUPTS CAUSING C STATE WAKE-UPS'.ljust(120) + '\n'))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        toptenp = 10
        if len(WakeUpDetailsObject.m_irq_wakeups_details_map) < 10:
            toptenp = len(WakeUpDetailsObject.m_irq_wakeups_details_map)
        
        self.textSummaryWriter(str(' Interrupt Info.').rjust(25), )
            
        self.textSummaryWriter(str('Total').rjust(24), )
        for key, value in sorted(WakeUpDetailsObject.m_residency_info_map.items()):
            if key != '0':
                self.textSummaryWriter(str('C').rjust(6) + str(key).ljust(4), )

        #print the cpu list only for overall information and not for per cpu information
        #if info_type == 'sys':
        self.textSummaryWriter(str(' CPU''s').rjust(15), )
        #else:
        #self.textSummaryWriter(str(' ').rjust(3), )
            
        self.textSummaryWriter('\n\n')
        i = 1
        prev = 0
        curr = 0       
        for key,value in sorted(WakeUpDetailsObject.m_irq_wakeups_details_map.items(), key=lambda x:x[1].m_wakeup_count, reverse=True):
            if i <= toptenp:   
                self.textSummaryWriter(str('IRQ-') + str(key).ljust(5)+'    ' + str(value.m_name).ljust(25) + str(' '), )
                #self.textSummaryWriter(str(' ').rjust(5), )
                self.textSummaryWriter(str(value.m_wakeup_count).rjust(6), )
                curr = value.m_wakeup_count
                    
                for key_res, value_res in sorted(WakeUpDetailsObject.m_residency_info_map.items()):
                    if key_res != '0':
                        self.textSummaryWriter(str(WakeUpDetailsObject.m_irq_wakeups_details_map[key].get_wakeup_count_by_state(key_res) ).rjust(10), )

                #print the cpu list only for overall information and not for per cpu information
                #if info_type == 'sys':
                self.textSummaryWriter(' '.center(15))
                self.textSummaryWriter(WakeUpDetailsObject.m_irq_wakeups_details_map[key].get_cpu_list().ljust(30), )

                self.textSummaryWriter('\n')
                if prev != curr:
                    i += 1
                prev = curr

            elif i > toptenp:
                break           
        self.textSummaryWriter('\n')
        
    def printTop10Timers(self, system_info, WakeUpDetailsObject, info_type):

        if WakeUpDetailsObject.m_wake_up_counts_map['ALL'] == 0:
                return

        global debug, utility_functions, test    
        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('TOP 10 TIMERS CAUSING C STATE WAKE-UPS'.ljust(120) + '\n'))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        toptenp = 10

        if len(WakeUpDetailsObject.m_timer_wakeups_details_map) < 10:
            toptenp = len(WakeUpDetailsObject.m_timer_wakeups_details_map)

        self.textSummaryWriter(str(' Process Info.').rjust(18),)
        self.textSummaryWriter(str('Total').rjust(32),)
        for key, value in sorted(WakeUpDetailsObject.m_residency_info_map.items()):
            if key != '0':
                self.textSummaryWriter(str('C').rjust(7) + str(key).ljust(3),)

        #print the cpu list only for overall information and not for per cpu information
        #if info_type == 'sys':
        self.textSummaryWriter(str(' CPU''s').rjust(20),)
        #else:
        #self.textSummaryWriter(str(' ').rjust(6),)
        self.textSummaryWriter('\n\n')
        
        i = 1
        prev = 0
        curr = 0        
        for key, value in sorted(WakeUpDetailsObject.m_timer_wakeups_details_map.items(), key=lambda x:x[1].m_wakeup_count, reverse=True):
            if i <= toptenp:   
                self.textSummaryWriter(str('PID-') + str(key).ljust(10)+'    ' + str(value.m_name).ljust(25),)
                
                self.textSummaryWriter(str(value.m_wakeup_count).rjust(6),)
                curr = value.m_wakeup_count 
                for key_res,value_res in sorted(WakeUpDetailsObject.m_residency_info_map.items()):
                    if key_res != '0':
                        self.textSummaryWriter(str(WakeUpDetailsObject.m_timer_wakeups_details_map[key].get_wakeup_count_by_state(key_res) ).rjust(10),)

                #print the cpu list only for overall information and not for per cpu information
                #if info_type == 'sys':
                self.textSummaryWriter(' '.center(15))
                self.textSummaryWriter(WakeUpDetailsObject.m_timer_wakeups_details_map[key].get_cpu_list().ljust(30),)

                if prev != curr:
                    i += 1
                prev = curr                    
                self.textSummaryWriter('\n')
            elif i > toptenp:
                break
            
    def printWakeUPEventsBuckets(self, system_info, WakeUpDetailsObject):

        if WakeUpDetailsObject.m_wake_up_counts_map['ALL'] == 0:
                return

        #traverese through the IRQ/Timer/IPI maps and print the bucket information for all of the wakeups
        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('SHORT SLEEPS, FREQUENT WAKEUPS'.ljust(120) + '\n'))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        self.textSummaryWriter('Wakeup Reason'.ljust(23) + 'Counts per Sleep Time Range(msec)\n\n'.rjust(70))

        tempObj = wakeupTypesInformationClass('', '', 0, 0, 0, system_info, 0)
       
        mystring = ''.rjust(40)
        myStateString = ' '.rjust(40)
        for key in sorted(tempObj.m_res_bucket_map.iterkeys()):

                if tempObj.m_res_bucket_map[key].m_bucket_C_state != 0:
                        myStateString +=  'C' + str(int(tempObj.m_res_bucket_map[key].m_bucket_C_state)) + ''.rjust(9)
                
                if tempObj.m_res_bucket_map[key].m_range_lowerbound < 1:
                        mystring += str(round(tempObj.m_res_bucket_map[key].m_range_lowerbound, 2)) + '-'
                else:
                        mystring += (str(tempObj.m_res_bucket_map[key].m_range_lowerbound)) + '-'

                if tempObj.m_res_bucket_map[key].m_range_upperbound < 1:
                        mystring += str(round(tempObj.m_res_bucket_map[key].m_range_upperbound, 2)) + str('  ').ljust(3)
                else:
                        mystring += (str(tempObj.m_res_bucket_map[key].m_range_upperbound)) + str('  ').ljust(3)
                
        old = str(tempObj.m_res_bucket_map[key].m_range_lowerbound) + '--1'
        new = '>=' + str(tempObj.m_res_bucket_map[key].m_range_lowerbound) +'ms'
        str1 = mystring.replace(old,new)
                                                                                                                        
        self.textSummaryWriter(str1 + 'CPU''s'.rjust(10) + '\n')
        self.textSummaryWriter('\n')
        ID = '  '
        #merge irq-timer wakeups information into a single list
        #In this merge , conflicting id's is not an issue as we do not print pid's
        merged = utility_functions.mergeTwoDictionaries(WakeUpDetailsObject.m_irq_wakeups_details_map, WakeUpDetailsObject.m_timer_wakeups_details_map)
        merged = utility_functions.mergeTwoDictionaries(merged, WakeUpDetailsObject.m_other_wakeups_details_map)
        
        for iden,wakeup_obj in sorted(merged.items(), key=lambda x:x[1].m_wakeup_count, reverse=True):
            ID = iden   
            #if an IRQ and PID are same , we negate the IRQ number to be able to add them to the hashtable, at this point this needs to be reversed 
            if iden.startswith('-') and wakeup_obj.m_type == 'IRQ':
                ID = int(iden) * (-1/100)
                ID = str(ID)            
            spacing = 7
            if wakeup_obj.m_type == 'Unknown' or wakeup_obj.m_type == 'WQExec' or wakeup_obj.m_type == 'Scheduler':      
                ID = ''
                spacing = 2
            # convert msec to usec
            self.textSummaryWriter('[' + wakeup_obj.m_type  + str(ID).rjust(spacing) + '] ' + wakeup_obj.m_name.ljust(21) + ''.rjust(3),)
          
            for range_lowerbound in sorted(wakeup_obj.m_res_bucket_map.iterkeys()):
                # convert msec to usec
                self.textSummaryWriter(str(int(wakeup_obj.m_res_bucket_map[range_lowerbound].m_hit_count)).rjust(6) + str(' ').rjust(4),)
            
            self.textSummaryWriter(wakeup_obj.get_cpu_list().rjust(5))
            self.textSummaryWriter('\n')  
        self.textSummaryWriter('\n\n\n')

    def printWakeUPEventsActiveBuckets(self, system_info, WakeUpDetailsObject):
        
        #traverese through the IRQ/Timer/IPI maps and print the bucket information for all of the wakeups
        if WakeUpDetailsObject.m_wake_up_counts_map['ALL'] == 0:
                return

        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('SHORT C0 TIME, FREQUENT WAKEUPS\n'))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        self.textSummaryWriter('Wakeup Reason'.ljust(23) + 'Counts per C0 Time Range(msec)'.rjust(75) + '\n\n')
        
        
        tempObj = wakeupTypesInformationClass('', '', 0, 0, 0, system_info, 0)
      
        mystring = ''.rjust(38)    
        for key in sorted(tempObj.m_res_bucket_map.iterkeys()): 
                if tempObj.m_res_bucket_map[key].m_range_lowerbound < 1:
                        mystring += str(round(tempObj.m_res_bucket_map[key].m_range_lowerbound, 2)) + '-'
                else:
                        mystring += (str(tempObj.m_res_bucket_map[key].m_range_lowerbound)) + '-'

                if tempObj.m_res_bucket_map[key].m_range_upperbound < 1:
                        mystring += str(round(tempObj.m_res_bucket_map[key].m_range_upperbound, 2)) + str('  ').ljust(3)
                else:
                        mystring += (str(tempObj.m_res_bucket_map[key].m_range_upperbound)) + str('  ').ljust(3)
        
        old = str(tempObj.m_res_bucket_map[key].m_range_lowerbound) + '--1'
        new = '>=' + str(tempObj.m_res_bucket_map[key].m_range_lowerbound) +'ms'
        str1 = mystring.replace(old,new)
                                                                                                                             
        self.textSummaryWriter(str1 + 'CPU''s'.rjust(13) + '\n')
        self.textSummaryWriter('\n')
        ID= '  '
        #merge irq-timer wakeups information into a single list
        #In this merge , conflicting id's is not an issue as we do not print pid's
        merged = utility_functions.mergeTwoDictionaries(WakeUpDetailsObject.m_irq_wakeups_details_map,WakeUpDetailsObject.m_timer_wakeups_details_map)
        merged = utility_functions.mergeTwoDictionaries(merged,WakeUpDetailsObject.m_other_wakeups_details_map)

        for iden,wakeup_obj in sorted(merged.items(), key=lambda x:x[1].m_wakeup_count, reverse=True):
            ID = iden   
            #if an IRQ and PID are same , we negate the IRQ number to be able to add them to the hashtable, at this point this needs to be reversed 
            if iden.startswith('-') and wakeup_obj.m_type == 'IRQ':
                ID = int(iden) * (-1/100)
                ID = str(ID)
                
            spacing = 7
            if wakeup_obj.m_type == 'Unknown'  or wakeup_obj.m_type == 'WQExec' or wakeup_obj.m_type == 'Scheduler':      
                ID = ''
                spacing = 2
            # convert msec to usec
            self.textSummaryWriter('[' + wakeup_obj.m_type + str(ID).rjust(spacing) + '] ' + wakeup_obj.m_name.ljust(21),)       
            for range_lowerbound in sorted(wakeup_obj.m_res_bucket_map.iterkeys()):  
                # convert msec to usec
                self.textSummaryWriter(str(int(wakeup_obj.m_res_bucket_map[range_lowerbound].m_active_hit_count )).rjust(7) + str(' ').rjust(3),)

            self.textSummaryWriter(wakeup_obj.get_cpu_list().rjust(10))
            self.textSummaryWriter('\n') 
        self.textSummaryWriter('\n\n\n')
        
    def printbuckets(self, system_info, WakeUpDetailsObject, info_type):

        if WakeUpDetailsObject.m_wake_up_counts_map['ALL'] == 0:
                return

        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('HISTOGRAM OF IDLE TIME' + '\n'))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
       
        mystring = ''
        myStateString = ''.rjust(26)
        self.textSummaryWriter('\nHeader (ms)'.ljust(24),)

        for key in sorted(WakeUpDetailsObject.m_res_bucket_map.iterkeys()):

            if WakeUpDetailsObject.m_res_bucket_map[key].m_bucket_C_state != 0:
                myStateString +=  'C' + str(int(WakeUpDetailsObject.m_res_bucket_map[key].m_bucket_C_state)) + ''.rjust(12) 
                
            if  WakeUpDetailsObject.m_res_bucket_map[key].m_range_lowerbound < 1:
                mystring += str(round(WakeUpDetailsObject.m_res_bucket_map[key].m_range_lowerbound, 2))
        
            else:
                mystring += str(WakeUpDetailsObject.m_res_bucket_map[key].m_range_lowerbound)

            if  WakeUpDetailsObject.m_res_bucket_map[key].m_range_upperbound < 1:
                mystring +=  '-' + str(round(WakeUpDetailsObject.m_res_bucket_map[key].m_range_upperbound, 2)) + str('  ').ljust(6)  
            else:
                mystring += '-' + str(WakeUpDetailsObject.m_res_bucket_map[key].m_range_upperbound) + str('  ').ljust(6)  
                
        old = str(WakeUpDetailsObject.m_res_bucket_map[key].m_range_lowerbound) + '--1.0'
        new = '>=' + str(WakeUpDetailsObject.m_res_bucket_map[key].m_range_lowerbound) + 'ms'
        str1 = mystring.replace(old, new)
        
        self.textSummaryWriter(str1 + '\n' + '\n' )
   
        totalIdleTime_us = 0
        self.textSummaryWriter('Idle Bucket Time(us)'.ljust(25),)
        for key in sorted(WakeUpDetailsObject.m_res_bucket_map.iterkeys()):
                
            self.textSummaryWriter(str(int(WakeUpDetailsObject.m_res_bucket_map[key].m_idle_rescount_msec*1000)).rjust(7) + str(' ').rjust(6),)
            totalIdleTime_us += int(WakeUpDetailsObject.m_res_bucket_map[key].m_idle_rescount_msec * 1000)
        self.textSummaryWriter('\n')

        self.textSummaryWriter('% Of Total Idle Time'.ljust(25),)
        for key in sorted(WakeUpDetailsObject.m_res_bucket_map.iterkeys()):
            self.textSummaryWriter(str( round(utility_functions.getPercentage(int(WakeUpDetailsObject.m_res_bucket_map[key].m_idle_rescount_msec*1000),
                                                                               totalIdleTime_us), 2)).rjust(7) + str(' ').rjust(6),)
        self.textSummaryWriter('\n')
        totalIdleHitCount = 0
        self.textSummaryWriter('Idle Bucket Hit Count'.ljust(25),)
        
        for key in sorted(WakeUpDetailsObject.m_res_bucket_map.iterkeys()):
        
            self.textSummaryWriter(str(WakeUpDetailsObject.m_res_bucket_map[key].m_hit_count).rjust(7) + str(' ').rjust(6),)
            totalIdleHitCount += WakeUpDetailsObject.m_res_bucket_map[key].m_hit_count

        self.textSummaryWriter('\n')
        self.textSummaryWriter('% of Total Idle Count'.ljust(25),)
        for key in sorted(WakeUpDetailsObject.m_res_bucket_map.iterkeys()):
        
            self.textSummaryWriter(str(round(utility_functions.getPercentage(WakeUpDetailsObject.m_res_bucket_map[key].m_hit_count, totalIdleHitCount),2)).rjust(7) + str(' ').rjust(6),)

        self.textSummaryWriter('\n\n')
        if debug:
                print 'totalIdleTime_us', str(round(((totalIdleTime_us * 1.0) / 1000), 2)), WakeUpDetailsObject.m_net_collection_time
        self.textSummaryWriter('Total Idle Time(ms)'.ljust(25) + str(round(((totalIdleTime_us * 1.0) / 1000), 2)).rjust(5) + '\n')  
        #if the metric is for overall system , collection time is, run time * number of cpu's 
        if info_type == 'sys':
                #collection run time over all cpu's        
                collection_time_over_all_cpu =  WakeUpDetailsObject.m_net_collection_time * system_info.m_core_count 
                self.textSummaryWriter('Total Idle %'.ljust(25) + str(round(utility_functions.getPercentage(((totalIdleTime_us *1.0) / 1000),
                                                                                                             (collection_time_over_all_cpu * 1000)),2)).rjust(5))
        else:
                self.textSummaryWriter('Total Idle %'.ljust(25) + str(round(utility_functions.getPercentage(((totalIdleTime_us*1.0) / 1000),
                                                                                                            (WakeUpDetailsObject.m_net_collection_time * 1000 )), 2)).rjust(5))
        self.textSummaryWriter('\nAvg. Idle Interval(us) '.ljust(25) + str(round(utility_functions.getRate(totalIdleTime_us,  totalIdleHitCount ),2)).rjust(5))

    def printWakeUpMetrics(self, system_info, WakeUpDetailsObject, info_type):

        if WakeUpDetailsObject.m_wake_up_counts_map['ALL'] == 0:
                return

        self.textSummaryWriter('\n\n\n')
        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('WAKEUP METRICS '.ljust(120) + '\n'))
        self.textSummaryWriter('-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')

        self.textSummaryWriter('Total # of wakeups :' + str(WakeUpDetailsObject.m_wake_up_counts_map['ALL']) + '\n\n')
        #if info_type == 'sys':
        self.textSummaryWriter('Wakeup Reason'.center(35) + 'WU %'.rjust(12) + 'WU count'.rjust(22) + 'WU Rate(WU/sec/core)'.rjust(25) + 'TraceCoverage(%)'.rjust(20) + 'CPU''s'.rjust(15) + '\n\n')
       
        #merge irq-timer wakeups information into a single list
        merged = utility_functions.mergeTwoDictionaries(WakeUpDetailsObject.m_irq_wakeups_details_map, WakeUpDetailsObject.m_timer_wakeups_details_map)
        merged = utility_functions.mergeTwoDictionaries(merged, WakeUpDetailsObject.m_other_wakeups_details_map)
                                        
        for iden, wakeup_obj in sorted(merged.items(), key=lambda x:x[1].m_wakeup_count, reverse=True):
            wakeup_p = 0
            wakeup_per_sec = 0
            wakeup_per_sec_per_core = 0
            wakeup_p = utility_functions.getPercentage(wakeup_obj.m_wakeup_count, WakeUpDetailsObject.m_wake_up_counts_map['ALL'])
            wakeup_per_sec = utility_functions.getRate(wakeup_obj.m_wakeup_count, system_info.m_collection_time)
           
            if system_info.m_core_count > 0 and info_type == 'sys':
                wakeup_per_sec_per_core =  wakeup_per_sec / system_info.m_core_count
            else:
                wakeup_per_sec_per_core = wakeup_per_sec
            ID = iden
            if wakeup_obj.m_type == 'IRQ' : 
                #if an IRQ and PID are same , we negate the IRQ number to be able to add them to the hashtable, at this point this needs to be reversed 
                if iden.startswith('-'):
                        ID = int(iden) * (-1)
                        ID = str(ID / 100)      
            spacing = 10
            if wakeup_obj.m_type == 'Unknown' or wakeup_obj.m_type == 'WQExec' or wakeup_obj.m_type == 'Scheduler':      
                ID = ''
                spacing = 5                 
            self.textSummaryWriter('[' + str(wakeup_obj.m_type) + '] ' + str(ID).rjust(spacing) + '  ' + str(wakeup_obj.m_name).ljust(25) +
                   str(round(wakeup_p, 2)).rjust(5) + str(wakeup_obj.m_wakeup_count).rjust(20) + str(round(wakeup_per_sec_per_core, 2)).rjust(20) +
                   str(round(wakeup_obj.getTraceCoverage(system_info), 2)).rjust(20),)
                                    
            #if info_type == 'sys':
            self.textSummaryWriter(str(' ').rjust(15) + wakeup_obj.get_cpu_list().ljust(15),)
            self.textSummaryWriter('\n')
        self.textSummaryWriter('\n\n')

    def printHWPResidencyInfo(self, WakeUpDetailsObject, per_core_info_list, system_info):

        global debug, utility_functions, percore, csv, test

        if csv:
            file_writer =  self.FILE_csv.write
        else:
            file_writer = self.textSummaryWriter

        if WakeUpDetailsObject.m_wake_up_counts_map['ALL'] == 0:
            return
      
        keyList = []
        have_data = 0
        for core in range(system_info.m_core_count):
            if (len(per_core_info_list[core].m_p_residency.keys()) > 0):
                    have_data = 1
            for key in per_core_info_list[core].m_p_residency.keys():
                if not key in keyList:
                    keyList.append(key)

        if have_data == 0:
            return
        
        for core in range(system_info.m_core_count):
            for key in keyList:
                if not key in per_core_info_list[core].m_p_residency.keys():
                    per_core_info_list[core].m_p_residency[key] = 0;
       
        totalResCount = 0
        pstate_stat = dict()
        totalResCountPerCore = [0.0] * system_info.m_core_count
        for core in range(system_info.m_core_count):
            for key in per_core_info_list[core].m_p_residency.keys():
                totalResCount = totalResCount + per_core_info_list[core].m_p_residency[key]
                totalResCountPerCore[core] = totalResCountPerCore[core] + per_core_info_list[core].m_p_residency[key]
                if not key in pstate_stat:
                    pstate_stat[key] = 0.0
                pstate_stat[key] = pstate_stat[key] + per_core_info_list[core].m_p_residency[key]

        file_writer('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        file_writer(str('HARDWARE P-STATE RESIDENCY SUMMARY'.ljust(120) + '\n'))
        file_writer('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')

        if csv:
            file_writer(',,RESIDENCY(%)\n')
            file_writer(str('P-STATE(Mhz),') + str('Overall,'))
            for core in range(system_info.m_core_count):
                file_writer(('Core' + str(core)) + ',')
        else:
            file_writer('RESIDENCY(%)'.center(50) + '\n')
            file_writer(str('P-STATE(Mhz)').ljust(15) + str('Overall').center(20),)
            for core in range(system_info.m_core_count):
                file_writer(('Core' + str(core)).center(7) ,)

        file_writer('\n\n')

        for k in sorted(keyList):
            if totalResCount != 0:
                if csv:
                    file_writer(str(k) + ',' + '%-15.2f' % (1.0 * pstate_stat[k] / totalResCount * 100.00) + ',')
                else:
                    file_writer(str(k).ljust(20) + '%-15.2f' % (1.0 * pstate_stat[k] / totalResCount * 100.00),)
            for core in range(system_info.m_core_count):
                if totalResCountPerCore[core] != 0:
                    if csv:
                        file_writer(('%7.2f' % (1.0 * per_core_info_list[core].m_p_residency[k] / totalResCountPerCore[core] * 100.00)) + ',')
                    else:
                        file_writer(('%7.2f' % (1.0 * per_core_info_list[core].m_p_residency[k] / totalResCountPerCore[core] * 100.00)))
            file_writer('\n')
        file_writer('\n')

    def printHWPResidencyInfoIntegrity(self, WakeUpDetailsObject, per_core_info_list, system_info):

        global debug, utility_functions, percore, csv, test

        file_writer =  self.FILE_integrity.write

        if not integrity and WakeUpDetailsObject.m_wake_up_counts_map['ALL'] == 0:
            return

        keyList = []
        have_data = 0
        for core in range(system_info.m_core_count):
            if (len(per_core_info_list[core].m_p_residency.keys()) > 0):
                    have_data = 1
            for key in per_core_info_list[core].m_p_residency.keys():
                if not key in keyList:
                    keyList.append(key)

        if have_data == 0:
            return

        for core in range(system_info.m_core_count):
            for key in keyList:
                if not key in per_core_info_list[core].m_p_residency.keys():
                    per_core_info_list[core].m_p_residency[key] = 0;

        totalResCount = 0
        pstate_stat = dict()
        totalResCountPerCore = [0.0] * system_info.m_core_count
        for core in range(system_info.m_core_count):
            for key in per_core_info_list[core].m_p_residency.keys():
                totalResCount = totalResCount + per_core_info_list[core].m_p_residency[key]
                totalResCountPerCore[core] = totalResCountPerCore[core] + per_core_info_list[core].m_p_residency[key]
                if not key in pstate_stat:
                    pstate_stat[key] = 0.0
                pstate_stat[key] = pstate_stat[key] + per_core_info_list[core].m_p_residency[key]

        file_writer('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        file_writer(str('HARDWARE P-STATE RESIDENCY SUMMARY'.ljust(120) + '\n'))
        file_writer('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')

        file_writer('*******\n')
        file_writer('OVERALL\n')
        file_writer('*******\n')
        file_writer(str('P STATE(Mhz),') + str('RESIDENCY(msec),\n'))
        for k in sorted(keyList):
            file_writer(str(k) + ',' + '%-15.2f' % (1.0 * pstate_stat[k] ) + '\n')

        file_writer('\n\n')

        for core in range(system_info.m_core_count):
            file_writer('******\n')
            file_writer(('Core ' + str(core)) + "\n")
            file_writer('******\n\n')
            file_writer(str('P STATE(Mhz),') + str('RESIDENCY(msec),\n'))
            for k in sorted(keyList):
                file_writer((str(k) + ',' + '%-15.2f' % (1.0 * per_core_info_list[core].m_p_residency[k] )) + '\n')
            file_writer('\n')

        file_writer('\n')

    def printOSPResidencyInfo(self, p_residency, system_info):

        global debug, utility_functions, percore, test

        if len(p_residency[0].keys()) == 0:
            return
        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('OS REQUESTED P-STATE RESIDENCY SUMMARY'.ljust(120) + '\n'))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')

        keyList = []
        for core in range(system_info.m_core_count):
            for key in p_residency[core].keys():
                if not key in keyList:
                    keyList.append(key)

        for core in range(system_info.m_core_count):
            for key in keyList:
                if not key in p_residency[core].keys():
                    p_residency[core][key] = 0;
       
        totalResCount = 0
        pstate_stat = dict()
        totalResCountPerCore = [0.0] * system_info.m_core_count
        
        for core in range(system_info.m_core_count):
            for key in p_residency[core].keys():
                totalResCount = totalResCount + p_residency[core][key]
                totalResCountPerCore[core] = totalResCountPerCore[core] + p_residency[core][key]
                if not key in pstate_stat:
                    pstate_stat[key] = 0.0
                pstate_stat[key] = pstate_stat[key] + p_residency[core][key]
        
        self.textSummaryWriter('RESIDENCY(%)'.center(50) + '\n')
        self.textSummaryWriter(str('P-STATE(Mhz)').ljust(15) + str('Overall').center(20),)
        
        for core in range(system_info.m_core_count):
            self.textSummaryWriter(('Core' + str(core)).center(7) ,)
        self.textSummaryWriter('\n\n')

        for k in sorted(keyList):
            if totalResCount != 0:
                if debug:
                    print 'Overall: ' + str(k) + ' Residency: ' + str(pstate_stat[k]) + ' C0 ', str(totalResCount)
                self.textSummaryWriter(str(k).ljust(20) + '%-15.2f' % (1.0 * pstate_stat[k] / totalResCount * 100.00))
            
            for core in range(system_info.m_core_count):
                if totalResCountPerCore[core] != 0:
                    if debug:
                        print 'Core: ' + str(core) + ' Residency: ' + str(p_residency[core][k]) + ' total ', str(system_info.m_collection_time*100)
                    self.textSummaryWriter(str(round((p_residency[core][k] / totalResCountPerCore[core]) * 100.00, 2)).center(10))
            self.textSummaryWriter('\n')
        self.textSummaryWriter('\n')


    def printSResidencyInfo(self, per_core_info_list, s_residency, system_info):

        global debug, utility_functions, test
        if len(s_residency) == 0:
            return
        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('S-STATE RESIDENCY COUNT SUMMARY (all state data shown in usecs)'.ljust(120) + '\n'))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        totalResCount = 0
        S0i0ResCount = 0
        S0i1ResCount = 0
        S0i2ResCount = 0
        S0i3_S3ResCount = 0
        #S3ResCount   = 0

        for val in s_residency:
            totalResCount = totalResCount + sum(val)
            S0i0ResCount = S0i0ResCount + val[0]
            S0i1ResCount = S0i1ResCount + val[1]
            S0i2ResCount = S0i2ResCount + val[2]
            S0i3_S3ResCount = S0i3_S3ResCount + val[3]
            #S3ResCount   = S3ResCount   + val[4]

        
        S0i0Perc = 1.0*S0i0ResCount/totalResCount*100.00
        S0i1Perc = 1.0*S0i1ResCount/totalResCount*100.00
        S0i2Perc = 1.0*S0i2ResCount/totalResCount*100.00
        S0i3_S3Perc = 1.0*S0i3_S3ResCount/totalResCount*100.00
        #S3Perc = 1.0*S3ResCount/totalResCount*100.00

        self.textSummaryWriter(str('S STATE').center(5) + str(' (%)').center(35) + '\n')
        self.textSummaryWriter("S0i0".ljust(8) + str(S0i0ResCount).rjust(15) + " (" + str(round(S0i0Perc, 3)).rjust(7) + ')\n')
        self.textSummaryWriter("S0i1".ljust(8) + str(S0i1ResCount).rjust(15) + " (" + str(round(S0i1Perc, 3)).rjust(7) + ')\n')
        self.textSummaryWriter("S0i2".ljust(8) + str(S0i2ResCount).rjust(15) + " (" + str(round(S0i2Perc, 3)).rjust(7) + ")\n")
        self.textSummaryWriter("S0i3+S3".ljust(8) + str(S0i3_S3ResCount).rjust(15) + " (" + str(round(S0i3_S3Perc, 3)).rjust(7) + ")\n")
        #self.textSummaryWriter("S3".ljust(8)   + str(S3ResCount).rjust(15) + " (" + str(round(S3Perc, 3)).rjust(7) + ")\n")
        self.textSummaryWriter("\n\n")
 

    def printDSCResidencyInfo(self, per_core_info_list, d_sc_residency, system_info, sc_device_mapping):

        global debug, utility_functions, test

        if len(d_sc_residency.keys()) == 0:
            return

        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('SOUTH COMPLEX D-STATE RESIDENCY SUMMARY (all state data shown in usecs)').ljust(120) + '\n')
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')

        self.textSummaryWriter(str('LSSID').center(8) + str('D0i0 (%)').center(28) + str('D0i1 (%)').center(28) + str('D0i2 (%)').center(28) + str('D0i3 (%)').center(28) + str('Subsystem').center(48) + '\n')
        self.textSummaryWriter('\n')
        for key in sorted(d_sc_residency.keys(), key=lambda a:int(re.sub('LSS',"",a))):
            totalResCount = 0
            D0i0ResCount = 0
            D0i0CGResCount = 0
            D0i1ResCount = 0
            D0i3ResCount = 0
            for val in d_sc_residency[key]:
                totalResCount = totalResCount + sum(val)
                D0i0ResCount = D0i0ResCount + val[0]
                D0i0CGResCount = D0i0CGResCount + val[1]
                D0i1ResCount = D0i1ResCount + val[2]
                D0i3ResCount = D0i3ResCount + val[3]

            if totalResCount == 0:
                sys.stderr.write("All SC residencies are 0\n")
                totalResCount = 1

            self.textSummaryWriter(key.ljust(8) + str(D0i0ResCount).rjust(15) + " (" + "%7.2f" % (1.0*D0i0ResCount/totalResCount*100.00) + ")" + str(D0i0CGResCount).rjust(15)+
                   " (" + "%7.2f" % (1.0*D0i0CGResCount/totalResCount*100.00) + ")"+str(D0i1ResCount).rjust(15) + " (" + "%7.2f" %
                   (1.0*D0i1ResCount/totalResCount*100.00) + ")" + str(D0i3ResCount).rjust(15) + " (" + "%7.2f" % (1.0*D0i3ResCount/totalResCount*100.00) + ")"+
                   sc_device_mapping[key].rjust(52) + '\n')
            self.textSummaryWriter('\n')


    def printDNCStateInfo(self, per_core_info_list, d_nc_state, system_info, nc_device_mapping):

        global debug, utility_functions, test

        if len(d_nc_state.keys()) == 0:
            return
        
        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('NORTH COMPLEX D-STATE SAMPLING SUMMARY'.ljust(120) + '\n'))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        self.textSummaryWriter(str('Device ID').center(10) + str('Sample Count Percentage per State'). center(80))
        self.textSummaryWriter('\n\n')
        self.textSummaryWriter(str('LSSID').ljust(15) + str('D0i0 (%)').center(16) + str('D0i1 (%)').center(16) + str('D0i2 (%)').center(16) +
                                str('D0i3 (%)').center(16) + str('Subsystem').center(32) + '\n')
   
        self.textSummaryWriter('\n')
        for key in sorted(d_nc_state.keys()):
        
            
            totalSampleCount = sum(d_nc_state[key])
            if totalSampleCount == 0:
                totalSampleCount = 1

            self.textSummaryWriter(key.ljust(8) + ("%7.2f" % (1.0*d_nc_state[key][0]/totalSampleCount*100.00)).rjust(16) +
                                     ("%7.2f" % (1.0*d_nc_state[key][1]/totalSampleCount*100.00)).rjust(16) +
                                           ("%7.2f" % (1.0*d_nc_state[key][2]/totalSampleCount*100.00)).rjust(16) +
                                             ("%7.2f" % (1.0*d_nc_state[key][3]/totalSampleCount*100.00)).rjust(16) +
                                                  nc_device_mapping[key].rjust(32) + '\n')
                                                  
            self.textSummaryWriter('\n')
        """ 
        for key in sorted(d_nc_state.keys()):
            totalResCount = 0
            D0i0ResCount = 0
            D0i0CGResCount = 0
            D0i1ResCount = 0
            D0i3ResCount = 0
            prevtsc = 0
            prevstate = -1
            transitions = 0
            
            for val in d_nc_state[key]:
                if prevtsc != 0:
                    diff_tsc = utility_functions.getCountinMiliseconds((sum(val) - prevtsc), system_info)
                    totalResCount = totalResCount + diff_tsc
                    if val[0] != 0:
                        D0i0ResCount = D0i0ResCount + diff_tsc
                    if val[1] != 0:
                        D0i0CGResCount = D0i0CGResCount + diff_tsc
                    if val[2] != 0:
                        D0i1ResCount = D0i1ResCount + diff_tsc
                    if val[3] != 0:
                        D0i3ResCount = D0i3ResCount + diff_tsc
                prevtsc = sum(val)
                if val[0] != 0:
                    if prevstate != 0:
                        transitions = transitions + 1
                    prevstate = 0
                if val[1] != 0:
                    if prevstate != 1:
                        transitions = transitions + 1
                    prevstate = 1
                if val[2] != 0:
                    if prevstate != 2:
                        transitions = transitions + 1
                    prevstate = 2
                if val[3] != 0:
                    if prevstate != 3:
                        transitions = transitions + 1
                    prevstate = 3

            self.textSummaryWriter(key.ljust(8) + ("%7.2f" % (1.0*D0i0ResCount/totalResCount*100.00)).rjust(16) +
                                     ("%7.2f" % (1.0*D0i0CGResCount/totalResCount*100.00)).rjust(16) +
                                           ("%7.2f" % (1.0*D0i1ResCount/totalResCount*100.00)).rjust(16) +
                                             ("%7.2f" % (1.0*D0i3ResCount/totalResCount*100.00)).rjust(16) +
                                                  nc_device_mapping[key].rjust(32) + '\n')
        
            """
            


    def printKernelWLInfo(self, wakelock_dict, over_all_cpu_info):

        global wakelock, test

        if wakelock == 0:
            return

        if len(wakelock_dict) == 0 and len(over_all_cpu_info.m_existing_wakelocks_list) == 0:
            return  
                
        self.textSummaryWriter('\n\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('KERNEL WAKELOCKS SUMMARY'.ljust(120) + '\n\n' ))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')      
        #existing locks
        self.textSummaryWriter('Locks acquired before collection start\n\n')
        for lock in over_all_cpu_info.m_existing_wakelocks_list:
            self.textSummaryWriter(str(lock) + '\n' )	     
        
        self.textSummaryWriter('\nPID'.ljust(6) + 'No. of WLocks'.rjust(10) + 'Total Locked Duration(msec)'.rjust(30) +
                                'TID'.rjust(5) + 'Process Name'.rjust(20) + 'Lock Name'.rjust(28) + 'Time(msec)'.rjust(18) + 'Op. performed during collection'.rjust(35) + 'Unlock Process (PID:TID)'.rjust(30) + '\n\n')
   
        total_WL_time = 0
        for pid_name, wl_obj_list in wakelock_dict.items():
            total_WL_time = 0
            for wl_obj in wl_obj_list:
                total_WL_time += wl_obj.m_lock_hold_time

            self.textSummaryWriter(str(pid_name.uid).ljust(6) + str(len(wl_obj_list)).rjust(10)+ str(round(non_overlapping_lock_time_per_process[pid_name], 2)).rjust(20))          
            for index, wl_obj in enumerate(wl_obj_list):
                if index > 0:
                    if wl_obj.m_lock_type == "DONE":
                        self.textSummaryWriter( str(wl_obj.m_WL_TID).rjust(55)  + str(wl_obj.m_pname).rjust(20) + str(wl_obj.m_WL_name).rjust(30) + str(round(wl_obj.m_lock_hold_time,2)).rjust(15) + 'L+U'.rjust(22) + str(wl_obj.m_unlock_process).rjust(35))
                    else:
                        self.textSummaryWriter( str(wl_obj.m_WL_TID).rjust(55) + str(wl_obj.m_pname).rjust(20) + str(wl_obj.m_WL_name).rjust(30) + str(round(wl_obj.m_lock_hold_time,2)).rjust(15) + wl_obj.m_lock_type[0].rjust(22))
                else:
                    if wl_obj.m_lock_type == "DONE":
                        self.textSummaryWriter(str(wl_obj.m_WL_TID).rjust(19) + str(wl_obj.m_pname).rjust(20) + str(wl_obj.m_WL_name).rjust(30) + str(round(wl_obj.m_lock_hold_time,2)).rjust(15) + 'L+U'.rjust(22) + str(wl_obj.m_unlock_process).rjust(35))
                    else:
                        self.textSummaryWriter(str(wl_obj.m_WL_TID).rjust(19) + str(wl_obj.m_pname).rjust(20) + str(wl_obj.m_WL_name).rjust(30) +  str(round(wl_obj.m_lock_hold_time,2)).rjust(15) + wl_obj.m_lock_type[0].rjust(22))
                        
                self.textSummaryWriter('\n')               
            self.textSummaryWriter('\n')
        self.textSummaryWriter('\n\n')
        
    #wl_bucket_map:  Map of count of wakelocks per bucket for every pID.
    #wl_map: Map of PID->List of wakelocks for that process
    def printWLBuckets(self, system_info, wl_bucket_map, wl_map):

        global wakelock, test

        if wakelock == 0:
            return

        if (wl_map):
            pass
        else:
            return

        #traverese through the IRQ/Timer/IPI maps and print the bucket information for all of the wakeups
        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('KERNEL WAKELOCK COUNT PER PROCESS'.ljust(120) + '\n'))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        self.textSummaryWriter('Locking Process'.ljust(23) + 'Lock Counts per Time Range(msec)\n\n'.rjust(70))                                                                                                                      
        self.textSummaryWriter('\n')
        index = 0
        #Returns the number of wakelocks for that process
        def sortkey(pid_name): return len(wl_map[pid_name])
        
        for pid_name, buckets in sorted(wl_bucket_map.items(), key= lambda x:sortkey(x[0]), reverse=True):
            if index == 0:
                mystring = ''.rjust(28)    
                for key in sorted(buckets.iterkeys()):         
                    mystring += (str(buckets[key].m_range_lowerbound)) + '-'        
                    if buckets[key].m_range_upperbound < 1:
                        mystring += str(round(buckets[key].m_range_upperbound, 2)) + str('  ').ljust(3)
                    else:
                        mystring += (str(buckets[key].m_range_upperbound)) + str('  ').ljust(3)
                
                old = str(buckets[key].m_range_lowerbound) + '--1'
                new = '>=' + str(buckets[key].m_range_lowerbound) +'ms'
                str1 = mystring.replace(old, new)
                str1 = 'PID'.ljust(8) + 'PNAME' + str1
                self.textSummaryWriter(str1 + '\n\n')
                
            index +=1
            self.textSummaryWriter(str(pid_name.uid.ljust(8)) + wl_map[pid_name][0].m_pname.ljust(30))
            for key, value in sorted(buckets.items()):
                self.textSummaryWriter(str(value.m_hit_count).rjust(5) + ''.rjust(2)),
            self.textSummaryWriter('\n')  
        self.textSummaryWriter('\n\n\n')


    def printUserWLInfo(self, wakelock_dict, over_all_cpu_info):

        global wakelock, test

        if wakelock == 0:
            return
        if len(wakelock_dict) == 0:
            return
                
        self.textSummaryWriter('\n\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('USER WAKELOCKS SUMMARY'.ljust(120) + '\n' ))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        	
        self.textSummaryWriter('\nUID  Package Name'.ljust(18) + 'No. of WLocks'.rjust(17) + 'Total Locked Duration(msec)'.rjust(30) +
                                'PID'.rjust(5) + 'Wakelock Type'.rjust(20) + 'Lock Tag'.rjust(28) + 'Time(msec)'.rjust(18) +
                               'Op. performed during collection'.rjust(35) + 'Unlock Process(PID)'.rjust(25) + '\n\n')

        uid_name_mapping = dict()
        total_WL_time = 0
        for uid_tag, wl_obj_list in wakelock_dict.items():
            uid_name_mapping[uid_tag] = wl_obj_list[0].m_pname
            total_WL_time = 0
            for wl_obj in wl_obj_list:
                total_WL_time += wl_obj.m_lock_hold_time

            self.textSummaryWriter(str(uid_tag.uid).ljust(6) + str(uid_name_mapping[uid_tag]).rjust(10) + str(len(wl_obj_list)).rjust(10)+ str(round(non_overlapping_lock_time_per_process[uid_tag], 2)).rjust(20))          
            for index, wl_obj in enumerate(wl_obj_list):
                if index > 0:
                    if wl_obj.m_lock_type == "DONE":
                        self.textSummaryWriter( str(wl_obj.m_WL_TID).rjust(70)   + str(wl_obj.m_wl_flag).rjust(20) +
                                                str(wl_obj.m_WL_name).rjust(30) + str(round(wl_obj.m_lock_hold_time,2)).rjust(15) +
                                                'L+U'.rjust(22) + str(wl_obj.m_unlock_process).rjust(25))
                    else:
                        self.textSummaryWriter( str(wl_obj.m_WL_TID).rjust(70) + str(wl_obj.m_wl_flag).rjust(20) + str(wl_obj.m_WL_name).rjust(30) +
                                                str(round(wl_obj.m_lock_hold_time,2)).rjust(15) + wl_obj.m_lock_type[0].rjust(22))
                else:
                    if wl_obj.m_lock_type == "DONE":
                        self.textSummaryWriter(str(wl_obj.m_WL_TID).rjust(21) + str(wl_obj.m_wl_flag).rjust(20) + str(wl_obj.m_WL_name).rjust(30) +
                                               str(round(wl_obj.m_lock_hold_time,2)).rjust(15) + 'L+U'.rjust(22) + str(wl_obj.m_unlock_process).rjust(25))
                    else:
                        self.textSummaryWriter(str(wl_obj.m_WL_TID).rjust(21) + str(wl_obj.m_wl_flag).rjust(20) + str(wl_obj.m_WL_name).rjust(30) +
                                               str(round(wl_obj.m_lock_hold_time,2)).rjust(15) + wl_obj.m_lock_type[0].rjust(22))
                        
                self.textSummaryWriter('\n')               
            self.textSummaryWriter('\n')
        self.textSummaryWriter('\n\n')
        

    def printThermalInfo(self, thermal_list):

        if len(thermal_list) == 0:
            return
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        self.textSummaryWriter(str('THERMAL SUMMARY'.ljust(120) + '\n' ))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
                	
        self.textSummaryWriter('\nComponent Name'.ljust(20) + 'Avg Temp (Celsius)'.rjust(20) + 'Min Temp (Celsius)'.rjust(20) +
                                'Max Temp (Celsius)'.rjust(20) + '\n\n')

        idx = 0
        while(idx < len(thermal_list)):
            self.textSummaryWriter(thermal_list[idx].m_name.ljust(20) + str(round(thermal_list[idx].m_min_max_avg[2],1)).rjust(15) + str(thermal_list[idx].m_min_max_avg[0]).rjust(15)
                                  + str(thermal_list[idx].m_min_max_avg[1]).rjust(20) + '\n')
            idx += 1
       
        self.textSummaryWriter('\n')     

    def printBandwidthInfo(self, bandwidth_list):

        if len(bandwidth_list) == 0:
            return
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        self.textSummaryWriter(str('BANDWIDTH SUMMARY'.ljust(120) + '\n' ))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        	
        self.textSummaryWriter('\nComponent Name'.ljust(20) + 'Read32 (MB/s)'.rjust(25) + 'Write32 (MB/s)'.rjust(25) +
                                'Read64 (MB/s)'.rjust(25)  +'Write64 (MB/s)'.rjust(25) + '\n\n')


        idx = 0
        while(idx < len(bandwidth_list)):
            self.textSummaryWriter(bandwidth_list[idx].m_name.ljust(20) + str(round((bandwidth_list[idx].m_rd32_wr32_rd64_wr64[0]),2)).rjust(22) +
                                   str(round((bandwidth_list[idx].m_rd32_wr32_rd64_wr64[1]), 2)).rjust(22) +
                                   str(round((bandwidth_list[idx].m_rd32_wr32_rd64_wr64[2]), 2)).rjust(22) +
                                   str(round((bandwidth_list[idx].m_rd32_wr32_rd64_wr64[3]), 2)).rjust(22) + '\n')
            idx += 1
       
        self.textSummaryWriter('\n')     

    def printGpuInfo(self, gpu_dict, system_info):

        if len(gpu_dict) == 0:
            return
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        self.textSummaryWriter(str('GPU P-STATE SUMMARY'.ljust(120) + '\n' ))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        	
        self.textSummaryWriter('\nFrequency(Mhz)'.ljust(20) + 'Time(msec)'.rjust(15) + 'Time(%)'.rjust(20) +'\n\n')

        totalGPUTime = sum(gpu_dict.values())
        for freq, time in sorted(gpu_dict.items()):
          
            self.textSummaryWriter(str(round(freq, 2)).ljust(20) + str(round(time, 2)).rjust(15) + str(round(utility_functions.getPercentage(time, totalGPUTime), 2)).rjust(20))
            self.textSummaryWriter('\n')     
                
        self.textSummaryWriter('\n')     

    ######CSV print functions
    #prints out comma delimted numbers representing wakeups graphed over a specified amount of time
    #this specified amount of time is self.time_slice

    def printCSVFile(self, system_info, dS):

        global percore, integrity, csv, test

        if (integrity):
            self.printPResidencyInfoIntegrity(dS.p_residency, dS.p_timeline, system_info) 
            #self.printHWPResidencyInfoIntegrity(dS.over_all_cpu_info, dS.per_core_info_list, system_info)        #Prints P-State HW Residency information
            self.printResidencyCountSummaryIntegrity(system_info, dS.over_all_cpu_info, 'sys')
            self.printCStatesVsWakeupReasonIntegrity(system_info, dS.over_all_cpu_info, 'sys')

        if (csv):
        
            self.OverallInfoCSV(dS.over_all_cpu_info, system_info)
            if percore and dS.over_all_cpu_info.m_wake_up_counts_map['ALL'] > 0:
                self.printCPUSpecificInfoCSV(dS.per_core_info_list, system_info)      
            if test == 1:
                self.printHWPResidencyInfo(dS.over_all_cpu_info, dS.per_core_info_list, system_info)        #Prints P-State HW Residency information
            self.printPResidencyInfoCSV(dS.p_residency, dS.p_timeline, system_info)                         #Prints P-State Residency information
            
            if test == 1:
                self.printSResidencyInfoCSV(dS.per_core_info_list, dS.s_residency, system_info)                  #Prints S-State Residency information
                self.printDNCStateInfoCSV(dS.per_core_info_list, dS.d_nc_state, system_info, dS.nc_device_mapping)          #Prints North complex D-State information
                self.printDSCResidencyInfoCSV(dS.per_core_info_list, dS.d_sc_residency, system_info, dS.sc_device_mapping)  #Prints South complex D-State Residency information
                self.printWLInfoCSV(dS.over_all_cpu_info, system_info)
                self.printThermalInfoCSV(dS.thermal_list)
                self.printBandwidthInfoCSV(dS.bandwidth_list)
                self.printGpuInfoCSV(dS.gpu_p_states_dict, system_info)
                
        
    def OverallInfoCSV(self, over_all_cpu_info, system_info):
        
        self.FILE_csv.write('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.FILE_csv.write(str('SoCWatch: Advanced CPU C-state Analysis\nCollected: ')+ strftime("%Y-%m-%d %H:%M:%S %Z") + '\n')
        self.FILE_csv.write('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        
        self.FILE_csv.write('# Total Collection Time = {0:.2f} secs'.format(system_info.m_collection_time) + '\n')

        # If no C State samples were found, return!
        if over_all_cpu_info.m_wake_up_counts_map['ALL'] == 0:
                return

        #calculate wake-ups per second for all cpu
        over_all_cpu_info.m_wakeups_per_sec = utility_functions.getRate(over_all_cpu_info.m_wake_up_counts_map['ALL'], system_info.m_collection_time)
        wakeups_p_sec_p_cpu = utility_functions.getRate(over_all_cpu_info.m_wakeups_per_sec , system_info.m_core_count)
        self.FILE_csv.write('# Wake-Ups/second/core =: ' + str(round(wakeups_p_sec_p_cpu, 2)) + ' WU/sec/core \n\n')
        self.printwakeupTablesCSV(system_info,over_all_cpu_info, 'sys')
        self.printTotalWakeupsPerTimeSliceCSV(system_info, over_all_cpu_info,'sys')

    def printCPUSpecificInfoCSV(self, per_core_info_list, system_info):

        #self.createTimeLineGraphCSV(per_core_info_list,system_info)
        self.FILE_csv.write('\n')
        self.FILE_csv.write('----------------------------\n')
        self.FILE_csv.write(str('CORE SPECIFIC INFORMATION' + '\n'))
        #self.FILE_csv.write( '----------------------------\n\n')

        ind = 0
        while ind < system_info.m_core_count:
            core_number = ind
            
            self.FILE_csv.write(('******') + '\n')
            self.FILE_csv.write('CORE ' + str(core_number) + '\n')
            self.FILE_csv.write('******' + '\n')
            self.FILE_csv.write('* Total number of wake ups = ' + str(per_core_info_list[core_number].m_wake_up_counts_map['ALL']) + '\n')

            per_core_info_list[core_number].m_wakeups_per_sec = utility_functions.getRate(per_core_info_list[core_number].m_wake_up_counts_map['ALL'], system_info.m_collection_time)
            #in case any erroneous samples were discarded, we need to remove the time spent in erroneous samples from the total collections time.
            self.checkForDiscardedSamplesTime(system_info, per_core_info_list[core_number], 'cpu')
            self.printwakeupTablesCSV(system_info, per_core_info_list[core_number], 'cpu')
            self.printTotalWakeupsPerTimeSliceCSV(system_info, per_core_info_list[core_number], 'cpu')
            ind += 1

    def printTotalWakeupsPerTimeSliceCSV(self, system_info, WakeUpDetailsObject, info_type):
      
        self.FILE_csv.write('Number of wakeups each ' + str(system_info.m_time_slice_msec) + ' milisecond over total collection time\n')
        self.FILE_csv.write('------------------------------------------------------------------------------------------\n')

        #self.FILE_csv.write(str(WakeUpDetailsObject.m_wu_per_slice) + info_type + '\n')
        self.FILE_csv.write('Average WU count: ' + str((sum( WakeUpDetailsObject.m_wu_per_slice) / len( WakeUpDetailsObject.m_wu_per_slice))) + '\n')
        self.FILE_csv.write('------------------------------------------------------------------------------------------\n\n')
        self.FILE_csv.write(str('Slice No. , WU/') + str(system_info.m_time_slice_msec) + str('ms\n'))
        
        for time_slice, wakeups in enumerate(WakeUpDetailsObject.m_wu_per_slice):
            self.FILE_csv.write(str(time_slice) + ',' + str(wakeups) + '\n' )
        self.FILE_csv.write('\n\n\n')
            
    def createTimeLineGraphCSV(self, cpu_list, system_info):

        overall_breaks_timeline = [0] * len(cpu_list[0].m_wu_per_slice)
        i =0
        while i < system_info.m_logical_cpu_count :
            for time_slice, breaks in enumerate(cpu_list[i].m_wu_per_slice):
                overall_breaks_timeline[time_slice] += breaks
            i += 1
                
        self.FILE_csv.write('Number of wakeups each' + system_info.m_time_slice_msec + 'milisecond over total collection time\n')
        self.FILE_csv.write('------------------------------------------------------------------------------------------\n')

        self.FILE_csv.write('Average WU count' + (sum(overall_breaks_timeline) / len(overall_breaks_timeline)) + '\n' )
        self.FILE_csv.write('------------------------------------------------------------------------------------------\n\n')
        self.FILE_csv.write(str('Slice No. , WU/') + str(system_info.m_time_slice_msec) + str('ms\n'))
        
        for time_slice, breaks in enumerate(overall_breaks_timeline):
            self.FILE_csv.write(time_slice + ',' + breaks + '\n')

    def printwakeupTablesCSV(self, system_info, WakeUpDetailsObject, info_type):

        #Prints all tables depending on the object sent as argument i.e. system-wide/percpu

        if test == 1:
            self.printResidencyCountSummary(system_info, WakeUpDetailsObject, info_type)
            self.printCStatesVsWakeupReasonCSV(system_info, WakeUpDetailsObject, info_type)
            self.printTop10WakeUPsCSV(system_info, WakeUpDetailsObject, info_type)
            self.printTop10TimersIRQCSV(system_info, WakeUpDetailsObject, info_type, "Timer")
            self.printTop10TimersIRQCSV(system_info, WakeUpDetailsObject, info_type, "IRQ")
        self.printIncorrectCStatesUsed(system_info, WakeUpDetailsObject, info_type)
        self.printbucketsCSV(system_info, WakeUpDetailsObject, info_type)

        if info_type == 'sys':
                self.printWakeUPEventsBucketsCSV(system_info, WakeUpDetailsObject, "Sleep Buckets")
                self.printWakeUPEventsBucketsCSV(system_info, WakeUpDetailsObject, "Active Buckets")
                
        self.printWakeUpMetricsCSV(system_info, WakeUpDetailsObject, info_type)
    
    def printResidencyCountSummaryIntegrity(self, system_info, WakeUpDetailsObject, info_type):
        
        global debug, utility_functions, integrity, test

        self.FILE_integrity.write('----------------------------------------')
        self.FILE_integrity.write(str('\nC-STATE RESIDENCY SUMMARY\n') )
        self.FILE_integrity.write('----------------------------------------\n\n')
        self.FILE_integrity.write(str('C STATE, RESIDENCY(msec)\n'))
  
        for key, value in  sorted(WakeUpDetailsObject.m_residency_info_map.items()):
            self.FILE_integrity.write('C' +  str(int(key)) + ',' + str(utility_functions.getCountinMiliseconds(value.m_res_count, system_info)) + '\n')
            
        self.FILE_integrity.write('\n\n')

    def printResidencyCountSummaryCSV(self, system_info, WakeUpDetailsObject, info_type):

        global debug, utility_functions, test
        self.FILE_csv.write('----------------------------------------')
        self.FILE_csv.write(str('\nC-STATE RESIDENCY SUMMARY\n') )
        self.FILE_csv.write('----------------------------------------\n\n')
        self.FILE_csv.write(str('C STATE,% RESIDENCY\n'))

        totalResCountOverAllCpu = 0   
        for key, value in  sorted(WakeUpDetailsObject.m_residency_info_map.items()):
           totalResCountOverAllCpu = totalResCountOverAllCpu + value.m_res_count 
        
        for key, value in  sorted(WakeUpDetailsObject.m_residency_info_map.items()):
            res_percentage = 0
            if totalResCountOverAllCpu > 0:
                res_percentage = utility_functions.getPercentage(value.m_res_count, totalResCountOverAllCpu)  
            self.FILE_csv.write('C' +  str(int(key)) + ',' + str(round(res_percentage, 2)) + '\n')
        
        self.FILE_csv.write('\n\n')

    def printCStatesVsWakeupReasonIntegrity(self, system_info, WakeUpDetailsObject, info_type):
        
        global debug, utility_functions, test
    
        self.FILE_integrity.write('\n')
        self.FILE_integrity.write(str(',WU-Count,WU-%,'),)
        for key,value in sorted(WakeUpDetailsObject.m_residency_info_map.items()):
            if key != '0':
               self.FILE_integrity.write('C' + str(key) + ',',)

        if info_type == 'sys':
                self.FILE_integrity.write(str('WU/sec/core'))
        else:
                self.FILE_integrity.write(str('WU/sec,TraceCoverage,CPU''s'))
        self.FILE_integrity.write('\n\n') 
      
        self.FILE_integrity.write(str('Total,' ) + str(WakeUpDetailsObject.m_wake_up_counts_map['ALL']) + ',' + ' ,',)
        
        for key, value in  sorted(WakeUpDetailsObject.m_residency_info_map.items()):
            if key != '0':
                 self.FILE_integrity.write(str(round(utility_functions.getPercentage(value.m_sleep_state_hit_count, WakeUpDetailsObject.m_wake_up_counts_map['ALL']), 2)) + ',', )

        #calculate wake-ups per second for all cpu
        wakeups_p_sec_p_core = 0
        if info_type == 'sys':
            wakeups_p_sec_p_core = utility_functions.getRate(WakeUpDetailsObject.m_wakeups_per_sec, system_info.m_core_count)  #Divide by core count for now, to accomodate for wuatch changes
        else:
            #self.textSummaryWriter('* Wake up Rate = {0:.2f} WU/sec\n'.format(utility_functions.getRate(per_core_info_list[core_number].m_wake_up_counts_map['ALL'],system_info.m_collection_time))+'\n') 
            wakeups_p_sec_p_core = WakeUpDetailsObject.m_wakeups_per_sec
            
        self.FILE_integrity.write(str(round(wakeups_p_sec_p_core,2)) + ',',)
        self.FILE_integrity.write('\n\n')

        self.CStatesVsWakeupReasonGenerateTableCSV(system_info, WakeUpDetailsObject, info_type, 'PID', 'Timer', 'integrity')
        self.CStatesVsWakeupReasonGenerateTableCSV(system_info, WakeUpDetailsObject, info_type, 'IRQ', 'IRQ', 'integrity')
        self.CStatesVsWakeupReasonGenerateTableCSV(system_info, WakeUpDetailsObject, info_type, 'IPI', 'IPI', 'integrity')
        self.CStatesVsWakeupReasonGenerateTableCSV(system_info, WakeUpDetailsObject, info_type, 'WQExec', 'WQExec', 'integrity')
        self.CStatesVsWakeupReasonGenerateTableCSV(system_info, WakeUpDetailsObject, info_type, 'Scheduler', 'Scheduler', 'integrity')
        self.CStatesVsWakeupReasonGenerateTableCSV(system_info, WakeUpDetailsObject, info_type, 'Unknown', 'Unknown', 'integrity')
        self.FILE_integrity.write('\n')

    def printCStatesVsWakeupReasonCSV(self, system_info, WakeUpDetailsObject, info_type):

        global debug, utility_functions, test
    
        self.FILE_csv.write('---------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.FILE_csv.write(str(',WU-Count,WU-%,'),)
        for key,value in sorted(WakeUpDetailsObject.m_residency_info_map.items()):
            if key != '0':
               self.FILE_csv.write('C' + str(key) + ',',)

        if info_type == 'sys':
                self.FILE_csv.write(str('WU/sec/core,TraceCoverage,CPU''s'))
        else:
                self.FILE_csv.write(str('WU/sec,TraceCoverage,CPU''s'))
        self.FILE_csv.write('\n-----------------------------------------------------------------------------------------------------------------------------------------------\n\n') 
      
        self.FILE_csv.write(str('Total,' ) + str(WakeUpDetailsObject.m_wake_up_counts_map['ALL']) + ',' + ' ,',)
        
        for key, value in  sorted(WakeUpDetailsObject.m_residency_info_map.items()):
            if key != '0':
                 self.FILE_csv.write(str(round(utility_functions.getPercentage(value.m_sleep_state_hit_count, WakeUpDetailsObject.m_wake_up_counts_map['ALL']), 2)) + ',', )

        #calculate wake-ups per second for all cpu
        wakeups_p_sec_p_core = 0
        if info_type == 'sys':
            wakeups_p_sec_p_core = utility_functions.getRate(WakeUpDetailsObject.m_wakeups_per_sec, system_info.m_core_count)  #Divide by core count for now, to accomodate for wuatch changes
        else:
            #self.textSummaryWriter('* Wake up Rate = {0:.2f} WU/sec\n'.format(utility_functions.getRate(per_core_info_list[core_number].m_wake_up_counts_map['ALL'],system_info.m_collection_time))+'\n') 
            wakeups_p_sec_p_core = WakeUpDetailsObject.m_wakeups_per_sec
            
        self.FILE_csv.write(str(round(wakeups_p_sec_p_core,2)) + ',',)
        self.FILE_csv.write('\n\n')

        self.CStatesVsWakeupReasonGenerateTableCSV(system_info, WakeUpDetailsObject, info_type, 'PID', 'Timer')
        self.CStatesVsWakeupReasonGenerateTableCSV(system_info, WakeUpDetailsObject, info_type, 'IRQ', 'IRQ')
        self.CStatesVsWakeupReasonGenerateTableCSV(system_info, WakeUpDetailsObject, info_type, 'IPI', 'IPI')
        self.CStatesVsWakeupReasonGenerateTableCSV(system_info, WakeUpDetailsObject, info_type, 'WQExec', 'WQExec')
        self.CStatesVsWakeupReasonGenerateTableCSV(system_info, WakeUpDetailsObject, info_type, 'Scheduler', 'Scheduler')
        self.CStatesVsWakeupReasonGenerateTableCSV(system_info, WakeUpDetailsObject, info_type, 'Unknown', 'Unknown')
        self.FILE_csv.write('\n')

    def CStatesVsWakeupReasonGenerateTableCSV(self, system_info,WakeUpDetailsObject, info_type, wakeup_ID, wakeup_type, file_type='csv'):

        global csv, integrity, test

        if file_type == 'csv':
            self.FILE_csv.write(wakeup_type + ',' + str(WakeUpDetailsObject.m_wake_up_counts_map[wakeup_ID]) + ',' + 
                            str(round(utility_functions.getPercentage(WakeUpDetailsObject.m_wake_up_counts_map[wakeup_ID], 
                                                                      WakeUpDetailsObject.m_wake_up_counts_map['ALL']),2)) + ',' ,)
        if file_type == 'integrity':
            self.FILE_integrity.write(wakeup_type + ',' + str(WakeUpDetailsObject.m_wake_up_counts_map[wakeup_ID]) + ',' + 
                            str(round(utility_functions.getPercentage(WakeUpDetailsObject.m_wake_up_counts_map[wakeup_ID], 
                                                                      WakeUpDetailsObject.m_wake_up_counts_map['ALL']),2)) + ',' ,)
      
        for key, value in  sorted(WakeUpDetailsObject.m_residency_info_map.items()):
            if key != '0':
                if file_type == 'csv':
                    self.FILE_csv.write(str(round(utility_functions.getPercentage(value.m_wakeup_specific_hit_count[wakeup_type], WakeUpDetailsObject.m_wake_up_counts_map['ALL']), 2)) + ',',)
                if file_type == 'integrity':
                    self.FILE_integrity.write(str(round(utility_functions.getPercentage(value.m_wakeup_specific_hit_count[wakeup_type], WakeUpDetailsObject.m_wake_up_counts_map['ALL']), 2)) + ',',)

        #calculate wu/sec/cpu
        wu_sec_cpu = 0
        if system_info.m_collection_time > 0 and system_info.m_core_count > 0:
            wu_sec_cpu = WakeUpDetailsObject.m_wake_up_counts_map[wakeup_ID] / system_info.m_collection_time
            if info_type == 'sys':
                wu_sec_cpu = wu_sec_cpu / system_info.m_core_count

        if file_type == 'csv':
            self.FILE_csv.write(str(round(wu_sec_cpu, 2)) + ',' ,)
            self.FILE_csv.write('\n')
        if file_type == 'integrity':
            self.FILE_integrity.write(str(round(wu_sec_cpu, 2)) + ',' ,)
            self.FILE_integrity.write('\n')

        
    def printTop10WakeUPsCSV(self, system_info, WakeUpDetailsObject, info_type):
        
        global debug,utility_functions, test
        self.FILE_csv.write('-----------------------\n')
        self.FILE_csv.write('TOP 10 WakeUps\n')
        self.FILE_csv.write('-----------------------\n')

        self.FILE_csv.write(str('Name,WU-Count,WU-%,'),)
        for key,value in sorted(WakeUpDetailsObject.m_residency_info_map.items()):
            if key != '0':
               if key == '1i' :
                   self.FILE_csv.write('C' + key + ',',)
               else:
                   self.FILE_csv.write('C' + str(int(key)) + ',',)
        #if info_type == 'sys':
        self.FILE_csv.write(str('WU/sec/core,TraceCoverage,CPU''s'),)
        #else:
        #self.FILE_csv.write(str('WU/sec,TraceCoverage,CPU''s'),)
                
        self.FILE_csv.write('\n\n')
        CStatestr = ''
        for key, value in sorted(WakeUpDetailsObject.m_residency_info_map.items()):
           CStatestr += str(' ') + 'C' + str(key)

        merged = utility_functions.mergeTwoDictionaries(WakeUpDetailsObject.m_irq_wakeups_details_map,WakeUpDetailsObject.m_timer_wakeups_details_map) 
        #Create a dictionary to store all wake-up reasons (processes/irqs etc) with wakeup counts for each 
        wakeup_counts_allcauses = dict()
                        
        for key, value in merged.items():
            wakeup_counts_allcauses[key] = value.m_wakeup_count
          
        if WakeUpDetailsObject.m_wake_up_counts_map['Unknown'] > 0:
            wakeup_counts_allcauses['Unknown'] = WakeUpDetailsObject.m_wake_up_counts_map['Unknown']
           
        if WakeUpDetailsObject.m_wake_up_counts_map['IPI'] > 0:
            wakeup_counts_allcauses['IPI'] = WakeUpDetailsObject.m_wake_up_counts_map['IPI']

        if WakeUpDetailsObject.m_wake_up_counts_map['WQExec'] > 0:
            wakeup_counts_allcauses['WQExec'] = WakeUpDetailsObject.m_wake_up_counts_map['WQExec']

        if WakeUpDetailsObject.m_wake_up_counts_map['Scheduler'] > 0:
            wakeup_counts_allcauses['Scheduler'] = WakeUpDetailsObject.m_wake_up_counts_map['Scheduler']
                     
        totalCauses = len(wakeup_counts_allcauses)
        toptenp = 10 ;
        if totalCauses < 10 :
            toptenp = totalCauses

        i = 1
        prev = 0
        curr = 0
        #sort by value i.e sort by the wu counts in descending order
        for key,value in sorted(wakeup_counts_allcauses.items(), key=itemgetter(1), reverse=True):
            if i <= toptenp:
                if WakeUpDetailsObject.m_timer_wakeups_details_map.has_key(key):
                    wakeup = WakeUpDetailsObject.m_timer_wakeups_details_map[key]
                    self.FILE_csv.write(str(merged[key].m_type) + '-' + str(key) + '  ' + str(merged[key].m_name) + ',',)
                    
                #During the merge of the two dictionaries if we find a key repeptiition , one of the keys is negated and added to the map
                #This works for our case as al the keys are expected to be +ive , and if they are not , such a sample with a -ive id will be removed as an erroneous sample

                #When a negative key is found , it is first made positive and the corresponding sample is printed
                elif str(key).startswith('-'):
                    key   = int(key) * (-1)
                    key   = str(key/100)
                    wakeup = WakeUpDetailsObject.m_irq_wakeups_details_map[key]
                    self.FILE_csv.write(str('IRQ-') + str(key)  + '  ' + str(WakeUpDetailsObject.m_irq_wakeups_details_map[key].m_name) + ',',)
                                                   
                elif WakeUpDetailsObject.m_irq_wakeups_details_map.has_key(key):
                    wakeup = WakeUpDetailsObject.m_irq_wakeups_details_map[key]
                    self.FILE_csv.write(str(merged[key].m_type) + '-' + str(key)+ '  ' + str(merged[key].m_name) + ',',)
                    
                elif WakeUpDetailsObject.m_other_wakeups_details_map.has_key(key):
                    wakeup = WakeUpDetailsObject.m_other_wakeups_details_map[key]
                    self.FILE_csv.write(str(key) + ',',           )
                
                self.FILE_csv.write(str(wakeup.m_wakeup_count) + ',',)
                curr = wakeup.m_wakeup_count

                wakeup_perc = utility_functions.getPercentage(wakeup.m_wakeup_count ,  WakeUpDetailsObject.m_wake_up_counts_map['ALL'])                
                self.FILE_csv.write(str(round(wakeup_perc,2)) + ',',)

                for key_res,value_res in sorted(WakeUpDetailsObject.m_residency_info_map.items()):
                    wu_count_per_state = 0
                    if  key_res != '0':
                        wu_count_per_state = (wakeup.get_wakeup_count_by_state(key_res) )
                        wu_perc_per_state = utility_functions.getPercentage(wu_count_per_state,WakeUpDetailsObject.m_wake_up_counts_map['ALL'])
                        self.FILE_csv.write(str(round(wu_perc_per_state,2)) + ',',)
                        
                wakeup_sec = 0
                #wakeup per second
                wakeup_sec = utility_functions.getRate(wakeup.m_wakeup_count,system_info.m_collection_time)
                wakeup_sec_cpu = 0
                if system_info.m_core_count and info_type == 'sys':
                    wakeup_sec_cpu = wakeup_sec/system_info.m_core_count  #
                else:
                    wakeup_sec_cpu = wakeup_sec
                    
                self.FILE_csv.write(str(round(wakeup_sec_cpu,2)) + ',' + str(round(wakeup.getTraceCoverage(system_info),2))+',',)
            
                #Print cpu list only for system-wide information
                #if info_type == 'sys':
                self.FILE_csv.write(wakeup.get_cpu_list(),)
                self.FILE_csv.write('\n\n')
                if prev != curr:
                    i += 1
                prev = curr

            elif i > toptenp:
                break
        self.FILE_csv.write('\n')

    def printTop10TimersIRQCSV(self, system_info, WakeUpDetailsObject, info_type, wakeup_type):
        
        global debug,utility_functions, test
        if wakeup_type == "Timer":
            self.FILE_csv.write('--------------------\n')
            self.FILE_csv.write('TOP 10 Timers\n')
            self.FILE_csv.write('--------------------\n')
            wakeups_map = WakeUpDetailsObject.m_timer_wakeups_details_map    
        else:
            self.FILE_csv.write('-----------------------\n')
            self.FILE_csv.write('TOP 10 Interrupts\n')
            self.FILE_csv.write('-----------------------\n')
            wakeups_map = WakeUpDetailsObject.m_irq_wakeups_details_map

        self.FILE_csv.write(str('Name,WU-Count,WU-%,'),)
        for key,value in sorted(WakeUpDetailsObject.m_residency_info_map.items()):
            if key != '0':
               if key == '1i' :
                   self.FILE_csv.write('C' + key + ',',)
               else:
                   self.FILE_csv.write('C' + str(int(key)) + ',',)

        #if info_type == 'sys':
        self.FILE_csv.write(str('WU/sec/core,TraceCoverage,CPU''s'),)
        #else:
        #       self.FILE_csv.write(str('WU/sec,TraceCoverage,CPU''s'),)
                
        self.FILE_csv.write('\n\n')
        totalCauses = len(wakeups_map)    
        toptenp = 10 ;
        if totalCauses < 10 :
            toptenp = totalCauses

        i = 1
        prev = 0
        curr = 0
        #sort by value i.e sort by the wu counts in descending order
        for key, value in sorted(wakeups_map.items(), key=lambda x:x[1].m_wakeup_count, reverse=True):
            if i <= toptenp:
                if wakeups_map.has_key(key):
                    wakeup = wakeups_map[key]
                    self.FILE_csv.write(str(wakeups_map[key].m_type) + '-' + str(key) + '  ' + str(wakeups_map[key].m_name) + ',',)
                    
                self.FILE_csv.write(str(wakeup.m_wakeup_count) + ',',)
                curr = wakeup.m_wakeup_count

                wakeup_perc = utility_functions.getPercentage(wakeup.m_wakeup_count ,  WakeUpDetailsObject.m_wake_up_counts_map['ALL'])                
                self.FILE_csv.write(str(round(wakeup_perc,2)) + ',',)

                for key_res,value_res in sorted(WakeUpDetailsObject.m_residency_info_map.items()):
                    wu_count_per_state = 0
                    if  key_res != '0':
                        wu_count_per_state = (wakeup.get_wakeup_count_by_state(key_res) )
                        wu_perc_per_state = utility_functions.getPercentage(wu_count_per_state,WakeUpDetailsObject.m_wake_up_counts_map['ALL'])
                        self.FILE_csv.write(str(round(wu_perc_per_state,2)) + ',',)
                        
                wakeup_sec = 0
                #wakeup per second
                wakeup_sec = utility_functions.getRate(wakeup.m_wakeup_count,system_info.m_collection_time)
                wakeup_sec_cpu = 0
                if system_info.m_core_count and info_type == 'sys':
                    wakeup_sec_cpu = wakeup_sec/system_info.m_core_count
                else:
                    wakeup_sec_cpu = wakeup_sec
                    
                self.FILE_csv.write(str(round(wakeup_sec_cpu,2)) + ',' + str(round(wakeup.getTraceCoverage(system_info),2))+',',)
            
                #Print cpu list only for system-wide information
                #if info_type == 'sys':
                self.FILE_csv.write(wakeup.get_cpu_list(),)
                self.FILE_csv.write('\n\n')
                if prev != curr:
                    i += 1
                prev = curr

            elif i > toptenp:
                break
        self.FILE_csv.write('\n')

    def printbucketsCSV(self, system_info, WakeUpDetailsObject, info_type):

        self.FILE_csv.write('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.FILE_csv.write(str('HISTOGRAM OF IDLE TIME' + '\n'))
        self.FILE_csv.write('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
       
        mystring = ''
        self.FILE_csv.write('\nHeader(ms),',)

        for key in sorted(WakeUpDetailsObject.m_res_bucket_map.iterkeys()):
                
                mystring += str(round(WakeUpDetailsObject.m_res_bucket_map[key].m_range_lowerbound, 2))
                mystring +=  '-' + str(round(WakeUpDetailsObject.m_res_bucket_map[key].m_range_upperbound, 2)) + ','  
                
        #Last bucket is ">500", heere we create the string for the last bucket
        old = str(WakeUpDetailsObject.m_res_bucket_map[key].m_range_lowerbound) + '--1,'
        new = '>=' + str(WakeUpDetailsObject.m_res_bucket_map[key].m_range_lowerbound) + 'ms'
        str1 = mystring.replace(old, new)
        
        self.FILE_csv.write(str1 + '\n\n')
        
        totalIdleTime_us = 0
        self.FILE_csv.write('Idle Bucket Time(us),',)
        for key in sorted(WakeUpDetailsObject.m_res_bucket_map.iterkeys()):
            self.FILE_csv.write(str(int(WakeUpDetailsObject.m_res_bucket_map[key].m_idle_rescount_msec*1000)) + ',',)
            totalIdleTime_us += int(WakeUpDetailsObject.m_res_bucket_map[key].m_idle_rescount_msec * 1000)
        self.FILE_csv.write('\n\n')

        self.FILE_csv.write('% Of Total Idle Time,',)
        for key in sorted(WakeUpDetailsObject.m_res_bucket_map.iterkeys()):
            self.FILE_csv.write(str( round(utility_functions.getPercentage(int(WakeUpDetailsObject.m_res_bucket_map[key].m_idle_rescount_msec*1000),
                                                                               totalIdleTime_us), 2)) + ',' ,)
        self.FILE_csv.write('\n')
        totalIdleHitCount = 0
        self.FILE_csv.write('Idle Bucket Hit Count,',)
        
        for key in sorted(WakeUpDetailsObject.m_res_bucket_map.iterkeys()):
            self.FILE_csv.write(str(WakeUpDetailsObject.m_res_bucket_map[key].m_hit_count) + ',' ,)
            totalIdleHitCount += WakeUpDetailsObject.m_res_bucket_map[key].m_hit_count

        self.FILE_csv.write('\n')
        self.FILE_csv.write('% of Total Idle Count,',)
        for key in sorted(WakeUpDetailsObject.m_res_bucket_map.iterkeys()):
            self.FILE_csv.write(str(round(utility_functions.getPercentage(WakeUpDetailsObject.m_res_bucket_map[key].m_hit_count, totalIdleHitCount),2)) + ',',)

        self.FILE_csv.write('\n')
        self.FILE_csv.write('Total Idle Time(ms),' + str(round(((totalIdleTime_us*1.0) / 1000), 2)) + '\n')    
        #if the metric is for overall system , collection time is, run time * number of cpu's 
        if info_type == 'sys':
                #collection run time over all cpu's        
                collection_time_over_all_cpu =  WakeUpDetailsObject.m_net_collection_time * system_info.m_core_count
                if debug:
                        print 'totalIdleTime_us', str(round(((totalIdleTime_us * 1.0) / 1000), 2)), WakeUpDetailsObject.m_net_collection_time
                self.FILE_csv.write('Total Idle %,'+ str(round(utility_functions.getPercentage(((totalIdleTime_us*1.0) / 1000),
                                                                                                             (collection_time_over_all_cpu * 1000)),2)) )
        else:
                self.FILE_csv.write('Total Idle %,' + str(round(utility_functions.getPercentage(((totalIdleTime_us*1.0) / 1000),
                                                                                                            (WakeUpDetailsObject.m_net_collection_time * 1000 )), 2)))

        self.FILE_csv.write('\nAvg. Idle Interval(us),' + str(round(utility_functions.getRate(totalIdleTime_us,  totalIdleHitCount ),2)))
        self.FILE_csv.write('\n\n')

    def printWakeUPEventsBucketsCSV(self, system_info, WakeUpDetailsObject, data_type):
        
        #traverese through the IRQ/Timer/IPI maps and print the bucket information for all of the wakeups

        self.FILE_csv.write('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        if data_type == "Sleep Buckets":
            self.FILE_csv.write(str('SHORT SLEEPS, FREQUENT WAKEUPS' + '\n'))
        elif data_type == "Active Buckets":
            self.FILE_csv.write(str('SHORT C0 TIME, FREQUENT WAKEUPS' + '\n'))
        self.FILE_csv.write('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        mystring = ''
        
        if data_type == "Sleep Buckets":
            self.FILE_csv.write(',,,,,Counts,per,Sleep,Time,Range,(msec)\n')
        elif data_type == "Active Buckets":
            self.FILE_csv.write(',,,,,Counts,per,C0,Time,Range,(msec)\n')
        self.FILE_csv.write(' ,Wakeup Reason,' + 'WU Count,' ,)
            
        tempObj = wakeupTypesInformationClass('', '', 0, 0, 0, system_info, 0)
            
        for key in sorted(tempObj.m_res_bucket_map.iterkeys()):
                mystring += str(round(tempObj.m_res_bucket_map[key].m_range_lowerbound, 2)) + '-'
                mystring += str(round(tempObj.m_res_bucket_map[key].m_range_upperbound, 2)) + ','
             
        old = str(tempObj.m_res_bucket_map[key].m_range_lowerbound) + '--1,'
        new = '>=' + str(tempObj.m_res_bucket_map[key].m_range_lowerbound) +'ms'
        str1 = mystring.replace(old,new)
                                                                                                                                   
        self.FILE_csv.write(str1 + '\n')
        self.FILE_csv.write('\n')
        ID= '  '
        #merge irq-timer wakeups information into a single list
        #In this merge , conflicting id's is not an issue as we do not print pid's
        merged = utility_functions.mergeTwoDictionaries(WakeUpDetailsObject.m_irq_wakeups_details_map, WakeUpDetailsObject.m_timer_wakeups_details_map)
        merged = utility_functions.mergeTwoDictionaries(merged, WakeUpDetailsObject.m_other_wakeups_details_map)
        
        for iden,wakeup_obj in sorted(merged.items(), key=lambda x:x[1].m_wakeup_count, reverse=True):
            ID = iden   
            #if an IRQ and PID are same , we negate the IRQ number to be able to add them to the hashtable, at this point this needs to be reversed 
            if iden.startswith('-') and wakeup_obj.m_type == 'IRQ':
                ID = int(iden) * (-1/100)
                ID = str(ID)            
            
            if wakeup_obj.m_type == 'Unknown' or wakeup_obj.m_type == 'WQExec' or wakeup_obj.m_type == 'Scheduler':      
                ID = ''
        
            self.FILE_csv.write(wakeup_obj.m_type + '-' + str(ID)+ ',' + wakeup_obj.m_name + ',' +
                                    str(wakeup_obj.m_wakeup_count) + ',',)
                    
            for range_lowerbound in sorted(wakeup_obj.m_res_bucket_map.iterkeys()):
                # convert msec to usec
                if data_type == "Sleep Buckets":
                    self.FILE_csv.write(str(int(wakeup_obj.m_res_bucket_map[range_lowerbound].m_hit_count)) + ',',)
                elif data_type == "Active Buckets":
                     self.FILE_csv.write(str(int(wakeup_obj.m_res_bucket_map[range_lowerbound].m_active_hit_count )) + ',',)
                    
            self.FILE_csv.write('\n')  
        self.FILE_csv.write('\n\n')

    
    def printWakeUpMetricsCSV(self, system_info, WakeUpDetailsObject, info_type):

        self.FILE_csv.write('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.FILE_csv.write(str('WAKEUP METRICS' + '\n'))
        self.FILE_csv.write('-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.FILE_csv.write('Total # of wakeups :' + str(WakeUpDetailsObject.m_wake_up_counts_map['ALL']) + '\n\n')

        if info_type == 'sys':
                self.FILE_csv.write(' ,Wakeup Reason,' + 'WU %,' + 'WU count,' + 'WU Rate(WU/sec/core),' + 'TraceCoverage(%),\n\n' )       
        else:
                self.FILE_csv.write(' ,Wakeup Reason,' + 'WU %,' + 'WU count,' + 'WU Rate(WU/sec),' + 'TraceCoverage(%),\n\n' )       

        #merge irq-timer wakeups information into a single list
        merged = utility_functions.mergeTwoDictionaries(WakeUpDetailsObject.m_irq_wakeups_details_map, WakeUpDetailsObject.m_timer_wakeups_details_map)
        merged = utility_functions.mergeTwoDictionaries(merged, WakeUpDetailsObject.m_other_wakeups_details_map)
                                        
        for iden, wakeup_obj in sorted(merged.items(), key=lambda x:x[1].m_wakeup_count, reverse=True):
            wakeup_p = 0
            wakeup_per_sec = 0
            wakeup_per_sec_per_core = 0
            wakeup_p = utility_functions.getPercentage(wakeup_obj.m_wakeup_count, WakeUpDetailsObject.m_wake_up_counts_map['ALL'])
            wakeup_per_sec = utility_functions.getRate(wakeup_obj.m_wakeup_count, system_info.m_collection_time)
            if system_info.m_core_count > 0 and info_type == 'sys':
                wakeup_per_sec_per_core =  wakeup_per_sec / system_info.m_core_count
            else:
                wakeup_per_sec_per_core = wakeup_per_sec
            ID = iden
            if wakeup_obj.m_type == 'IRQ' : 
                #if an IRQ and PID are same , we negate the IRQ number to be able to add them to the hashtable, at this point this needs to be reversed 
                if iden.startswith('-'):
                        ID = int(iden) * (-1)
                        ID = str(ID / 100)      
            spacing = 10
            if wakeup_obj.m_type == 'Unknown' or wakeup_obj.m_type == 'WQExec' or wakeup_obj.m_type == 'Scheduler':      
                ID = ''
                spacing = 5                 
            self.FILE_csv.write(str(wakeup_obj.m_type) + '-' + str(ID) + ',' + str(wakeup_obj.m_name) + ',' +
                   str(round(wakeup_p, 2)) + ',' + str(wakeup_obj.m_wakeup_count) + ',' + str(round(wakeup_per_sec_per_core, 2)) + ',' +
                   str(round(wakeup_obj.getTraceCoverage(system_info), 2)),)         
            self.FILE_csv.write('\n')
        self.FILE_csv.write('\n\n')
  
    def printSResidencyInfoCSV(self, per_core_info_list, s_residency, system_info):

        global debug, utility_functions, test
        if len(s_residency) == 0:
            
            return
        self.FILE_csv.write('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.FILE_csv.write(str('S-STATE RESIDENCY COUNT SUMMARY (all state data shown in usecs)' + '\n'))
        self.FILE_csv.write('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        totalResCount = 0
        S0i0ResCount = 0
        S0i1ResCount = 0
        S0i2ResCount = 0
        S0i3_S3ResCount = 0
        #S3ResCount   = 0

        for val in s_residency:
            totalResCount = totalResCount + sum(val)
            S0i0ResCount = S0i0ResCount + val[0]
            S0i1ResCount = S0i1ResCount + val[1]
            S0i2ResCount = S0i2ResCount + val[2]
            S0i3_S3ResCount = S0i3_S3ResCount + val[3]
            #S3ResCount   = S3ResCount + val[3]

        self.FILE_csv.write(str('S STATE,Count,') + str('%') + '\n')
        self.FILE_csv.write("S0i0," + str(S0i0ResCount) + "," + str(1.0 * S0i0ResCount / totalResCount * 100.00) + '\n')
        self.FILE_csv.write("S0i1," + str(S0i1ResCount) + "," + str(1.0*S0i1ResCount/totalResCount*100.00) + '\n')
        self.FILE_csv.write("S0i2," + str(S0i2ResCount) + "," + str(1.0*S0i2ResCount/totalResCount*100.00) + "\n")
        self.FILE_csv.write("S0i3 + S3," + str(S0i3_S3ResCount) + "," + str(1.0*S0i3_S3ResCount/totalResCount*100.00) + "\n")
        #self.FILE_csv.write("S3," + str(S3ResCount)     + "," + str(1.0*S3ResCount/totalResCount*100.00) + "\n")
        self.FILE_csv.write("\n\n")

    def printDSCResidencyInfoCSV(self, per_core_info_list, d_sc_residency, system_info, sc_device_mapping):

        global debug, utility_functions, test

        if len(d_sc_residency.keys()) == 0:
            return

        self.FILE_csv.write('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.FILE_csv.write(str('SOUTH COMPLEX D-STATE RESIDENCY SUMMARY (all state data shown in usecs)') + '\n')
        self.FILE_csv.write('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')

        self.FILE_csv.write(str('LSSID,') + str('D0i0(%),') + str('D0i1(%),') + str('D0i2(%),') + str('D0i3(%),') + str('Subsystem') + '\n')

        for key in sorted(d_sc_residency.keys()):
            totalResCount = 0
            D0i0ResCount = 0
            D0i0CGResCount = 0
            D0i1ResCount = 0
            D0i3ResCount = 0
            for val in d_sc_residency[key]:
                totalResCount = totalResCount + sum(val)
                D0i0ResCount = D0i0ResCount + val[0]
                D0i0CGResCount = D0i0CGResCount + val[1]
                D0i1ResCount = D0i1ResCount + val[2]
                D0i3ResCount = D0i3ResCount + val[3]

            if totalResCount == 0:
                sys.stderr.write("All SC residencies are 0\n")
                totalResCount = 1

            self.FILE_csv.write(key + ',' + "%7.2f" % (1.0*D0i0ResCount/totalResCount*100.00) + "," +
                   "%7.2f" % (1.0*D0i0CGResCount/totalResCount*100.00) + "," + "%7.2f" %
                   (1.0*D0i1ResCount/totalResCount*100.00) + "," +  "%7.2f" % (1.0*D0i3ResCount/totalResCount*100.00) +
                    ',' + sc_device_mapping[key] + '\n')
            self.FILE_csv.write('\n')


    def printDNCStateInfoCSV(self, per_core_info_list, d_nc_state, system_info, nc_device_mapping):

        global debug, utility_functions, test

        if len(d_nc_state.keys()) == 0:
            return
        
        self.textSummaryWriter('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.textSummaryWriter(str('NORTH COMPLEX D-STATE SAMPLING SUMMARY' + '\n'))
        self.textSummaryWriter('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        self.textSummaryWriter(str('Device ID,,,') + str('Sample Count Percentage per State,'))
        self.textSummaryWriter('\n\n')
        self.textSummaryWriter(str('LSSID,') + str('D0i0 (%),') + str('D0i1 (%),') + str('D0i2 (%),') +
                                str('D0i3 (%),') + str('Subsystem,') + '\n')
   
        self.textSummaryWriter('\n')
        for key in sorted(d_nc_state.keys()):
        
            
            totalSampleCount = sum(d_nc_state[key])
        
            self.textSummaryWriter(key + ',' + ("%7.2f" % (1.0*d_nc_state[key][0]/totalSampleCount*100.00)) + ',' +
                                     ("%7.2f" % (1.0*d_nc_state[key][1]/totalSampleCount*100.00)) + ',' +
                                           ("%7.2f" % (1.0*d_nc_state[key][2]/totalSampleCount*100.00)) + ',' +
                                             ("%7.2f" % (1.0*d_nc_state[key][3]/totalSampleCount*100.00)) + ',' +
                                                  nc_device_mapping[key] + '\n')
                                                  
            self.textSummaryWriter('\n')

    def printPResidencyInfoIntegrity(self, p_residency, p_timeline, system_info):
        
        global debug, utility_functions, test

        if len(p_residency[0].keys()) == 0:
            return
        self.FILE_integrity.write('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.FILE_integrity.write(str('OS REQUESTED P-STATE RESIDENCY SUMMARY' + '\n'))
        self.FILE_integrity.write('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        self.FILE_integrity.write(str('*******\n'))
        self.FILE_integrity.write('OVERALL\n')
        self.FILE_integrity.write(('*******\n'))

        totalResCount = 0
        pstate_stat = dict()
        totalResCountPerCore = [0.0] * system_info.m_core_count
        for core in range(system_info.m_core_count):
            for key in p_residency[core].keys():
                totalResCount = totalResCount + p_residency[core][key]
                totalResCountPerCore[core] = totalResCountPerCore[core] + p_residency[core][key]
                if not key in pstate_stat:
                    pstate_stat[key] = 0.0
                pstate_stat[key] = pstate_stat[key] + p_residency[core][key]
                  
        self.FILE_integrity.write(str('P STATE(Mhz),') + str('RESIDENCY(msec),') + '\n')
       
        for k in sorted(pstate_stat.keys()):
        
            if debug:
                print ' csv  ' +  str(k) + '' + str(pstate_stat[k]) + ' Time: ' + str(utility_functions.getCountinMiliseconds(pstate_stat[k], system_info))
            self.FILE_integrity.write(str(k) + ',' + str(pstate_stat[k]) + '\n')
        self.FILE_integrity.write('\n\n')

        for core in range(system_info.m_core_count):
            self.FILE_integrity.write(('******\n'))
            self.FILE_integrity.write(('Core ') + str(core) + '\n')
            self.FILE_integrity.write(('******\n')+ '\n')
            self.FILE_integrity.write(('P STATE(Mhz),') + ('RESIDENCY(msec),') + '\n')
                                    
            for k in sorted(p_residency[core].keys()):
                self.FILE_integrity.write( str(k) + ',' + str(p_residency[core][k]) + '\n')
               
            self.FILE_integrity.write('\n\n')

    def printPResidencyInfoCSV(self, p_residency, p_timeline, system_info, file_type='csv'):

        global debug, utility_functions, test
        if len(p_residency[0].keys()) == 0:
            return
        self.FILE_csv.write
        ('\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n')
        self.FILE_csv.write(str('OS REQUESTED P-STATE RESIDENCY SUMMARY' + '\n'))
        self.FILE_csv.write('---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n')
        self.FILE_csv.write(str('*******\n'))
        self.FILE_csv.write('OVERALL\n')
        self.FILE_csv.write(('*******\n'))

        totalResCount = 0
        pstate_stat = dict()
        totalResCountPerCore = [0.0] * system_info.m_core_count
        for core in range(system_info.m_core_count):
            for key in p_residency[core].keys():
                totalResCount = totalResCount + p_residency[core][key]
                totalResCountPerCore[core] = totalResCountPerCore[core] + p_residency[core][key]
                if not key in pstate_stat:
                    pstate_stat[key] = 0.0
                pstate_stat[key] = pstate_stat[key] + p_residency[core][key]
          
        self.FILE_csv.write(str('P STATE(Mhz),') + str('RESIDENCY(%),') + '\n')
        for k in sorted(pstate_stat.keys()): 
            self.FILE_csv.write(str(k) + ',' + '%6.3f' % (1.0 * pstate_stat[k] / totalResCount * 100.00) + '\n')
        self.FILE_csv.write('\n\n')

        for core in range(system_info.m_core_count):
            self.FILE_csv.write(('******\n'))
            self.FILE_csv.write(('Core ') + str(core) + '\n')
            self.FILE_csv.write(('******\n')+ '\n')
            self.FILE_csv.write(('P STATE(Mhz),') + ('RESIDENCY(%),') + '\n')
                                        
            for k in sorted(p_residency[core].keys()):
                self.FILE_csv.write(str(k) + ',' + '%6.3f' % (1.0 * p_residency[core][k] / totalResCountPerCore[core] * 100.00) + '\n')

            """
            self.FILE_csv.write('\n\n')
            self.FILE_csv.write('P State Timeline\n')
            self.FILE_csv.write(('Time(msec),') + ('ActualFreq(MHz),ReqFreq(MHz)') + '\n')
            for tsc in sorted(p_timeline[core].keys()):             
                time_since_collection_start = utility_functions.getCountinMiliseconds((tsc - system_info.m_collection_start_tsc), system_info)
                self.FILE_csv.write(str(time_since_collection_start) + ',' + str(p_timeline[core][tsc][0]) + ',' + str(p_timeline[core][tsc][1]) + '\n')
            self.FILE_csv.write('\n\n')
            """
        self.FILE_csv.write('\n')
    
    def printWLInfoCSV(self, over_all_cpu_info, system_info):
        
        #over_all_cpu_info.self.m_locks_per_timeslice
        self.FILE_csv.write('Open Locks in each' + str(system_info.m_time_slice_msec) + ' milisecond over total collection time\n')
        self.FILE_csv.write('------------------------------------------------------------------------------------------\n')

        self.FILE_csv.write(str('Slice No. , Lock  Count\n'))
        
        index = 0
        while index < len(over_all_cpu_info.m_locks_per_timeslice):
            self.FILE_csv.write(str(index) + ',' + str(over_all_cpu_info.m_locks_per_timeslice[index])+ '\n')
            index += 1
            
        self.FILE_csv.write('\n\n\n')
        
    def printThermalInfoCSV(self, thermal_list):

        if len(thermal_list) == 0:
            return
        
        self.FILE_csv.write(str('\nTHERMAL SUMMARY'.ljust(120) + '\n\n' ))
                	
        self.FILE_csv.write('\nComponent Name,' + 'Avg Temp (Celsius),' + 'Min Temp (Celsius),' +
                                'Max Temp (Celsius)' + '\n\n')

        idx = 0
        while(idx < len(thermal_list)):
            self.FILE_csv.write(thermal_list[idx].m_name + ',' + str(thermal_list[idx].m_min_max_avg[2]) + ',' + str(thermal_list[idx].m_min_max_avg[0]) + ','
                                  + str(thermal_list[idx].m_min_max_avg[1]) + '\n')
            idx += 1
       
        self.FILE_csv.write('\n')     
 
    def printBandwidthInfoCSV(self, bandwidth_list):

        if len(bandwidth_list) == 0:
            return
        self.FILE_csv.write(str('\nBANDWIDTH SUMMARY \n' ))

        self.FILE_csv.write('\nComponent Name,' + 'Read32 (MB/s),' + 'Write32 (MB/s),' +
                                'Read64 (MB/s),'  +'Write64 (MB/s)' + '\n\n')


        idx = 0
        while(idx < len(bandwidth_list)):
            self.FILE_csv.write(bandwidth_list[idx].m_name + ',' + str(round((bandwidth_list[idx].m_rd32_wr32_rd64_wr64[0]/1048576),2))+ ',' +
                                   str(round((bandwidth_list[idx].m_rd32_wr32_rd64_wr64[1]/1048576), 2)) + ',' +
                                   str(round((bandwidth_list[idx].m_rd32_wr32_rd64_wr64[2]/1048576), 2)) + ',' +
                                   str(round((bandwidth_list[idx].m_rd32_wr32_rd64_wr64[3]/1048576), 2)) + '\n')
            idx += 1
       
        self.FILE_csv.write('\n')     

    def printGpuInfoCSV(self, gpu_dict, system_info):

        if len(gpu_dict) == 0:
            return
        self.FILE_csv.write(str('GPU P-STATE SUMMARY\n' ))
        	
        self.FILE_csv.write('\nFrequency(Mhz)' + ',' + 'Time(msec)' + ',' + 'Time(%)' + ',' +'\n\n')

        for freq, time in sorted(gpu_dict.items()):
                self.FILE_csv.write(str(round(freq, 2)) + ',' + str(round(time, 2)) + ',' + str(round(utility_functions.getPercentage((time/1000), system_info.m_collection_time), 2)))
       
        self.textSummaryWriter('\n')     

    
###########################################################################################################################################################        

def parseCommandLineInput(system_info):

    global debug, show_promotion, percore, csv, txt, integrity, wakelock, test
    
    datafile = ''
    t_slice = 0   
    shortarg = "hdciwtf:o:"
    longarg = ["help", "debug", "core", "integrity", "wakelock", "test", "file=", "csv", "txt", "output-file="]

    try:
        opts, args = getopt.getopt(sys.argv[1:], shortarg, longarg)
    except getopt.GetoptError, err:
        usage()
        sys.exit(1)      

    
    output_file = ''

    #if no options were given    
    if not opts:
        usage()
        sys.exit(1)
        
    for o, a in opts:
         
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o == "-d":
            debug = 1
        #elif o == "-p":
        #    show_promotion = 1
        elif o in ("-c", "--core"):          # Print information for each cpu?
            percore = 1
        elif o in ("-t", "--test"):         # Get the time range of each slice
            test = 1
            """
            try:
                t_slice = float(a)
            except ValueError:
                print "***Time slice value must be an integer or float.*** "
                sys.exit()
            """
        elif o in ("--txt"):                # Print output in CSV format?
            txt = 1
        elif o in ("--csv"):                # Print output in CSV format?
            csv = 1
        elif o in ("-o", "--output-file"):   # dump output files to specific dir?
            output_file = a
        elif o in ("-f", "--file"):         # Get the input data file name
            datafile = a
        elif o in ("-i", "--integrity"):         # Get the input data file name
            integrity = 1
        elif o in ("-w", "--wakelock"):         # Get the input data file name
            wakelock = 1

        else:
            print '***Unrecognizable parameters***'
            usage()
            sys.exit()

            
    #if niether csv nor txt is specified use csv by default
    if txt == 1 and csv == 1:
            print '***Usage Error: Only one output file type can be specified.***'
            sys.exit()

    if t_slice > 0:
            system_info.m_time_slice_msec = t_slice
            
            if csv == 0:
                    print '***Time switch only applies to csv output, time input ignored.***'
    elif t_slice < 0:
            if csv == 0:
                    print '***Time switch only applies to csv output, time input ignored.***'
            else:
                    print '***Time value must be greater than 0. Assuming default(time=1000msec)***'
                                          
    if datafile == '' or not os.path.exists(datafile):
        print '\nSocwatch data file not found. ', datafile
        usage()
    if datafile.endswith('.sw1'):
        print '\n***Incorrect input file: ', datafile,'. Socwatch text file required.***'
        usage()
        sys.exit(1)

    system_info.m_wudump_input_file = datafile

    if output_file != '':
        (path, filename) = os.path.split(output_file)
        
        if path:
            if not os.path.isdir(path):
                os.makedirs(path)
            system_info.m_output_dir = path
                
        if filename:
                
            if(txt):
                system_info.m_output_summary_text_file = filename + ".txt"
            if(csv):
                 system_info.m_output_summary_tl_csv_file = filename + ".csv"
            if(integrity):
                 system_info.m_output_integrity_csv_file = filename + "_integrity.csv"
                
    system_info.m_output_summary_text_file    = os.path.join(system_info.m_output_dir, system_info.m_output_summary_text_file)
    system_info.m_output_summary_tl_csv_file  = os.path.join(system_info.m_output_dir, system_info.m_output_summary_tl_csv_file)
    system_info.m_output_integrity_csv_file   = os.path.join(system_info.m_output_dir, system_info.m_output_integrity_csv_file)

    if debug:
            print 'o/p files: ', system_info.m_output_summary_text_file, ' ', system_info.m_output_summary_tl_csv_file
   

class Package:
        def __init__(self):
            self.package_id = -1
            self.m_c_res   = dict()
            self.m_modules = dict()
            self.m_cores    = dict()

class Module:
        def __init__(self):
            self.m_c_res  = dict()
            self.m_core_count = 0
           

class Core:
        def __init__(self):
            self.m_c_res  = dict()


class componentThermalClass:
        def __init__(self, comp_name=" "):
            self.m_name  = comp_name
            self.m_min_max_avg = [1000000000,-1,0.0]

class componentBandwidthClass:
        def __init__(self, comp_name=" "):
            self.m_name  = comp_name
            self.m_rd32_wr32_rd64_wr64 = [0, 0, 0, 0]

class defineDataStructuresClass:
            
    def __init__(self,system_info):
       
        
        self.per_core_info_list = list()                      #List containing the wake-up information for every cpu , this list is an array of wakeUpDetailsClass objects
        self.p_residency        = list()                      #List containing P-State residency
        self.p_timeline         = list()
        self.s_residency        = list()                      #List containing S-State residency counters 
        self.d_sc_residency     = dict()                      #Dictionary containing D-State residency counters 
        self.d_nc_state         = dict()                      #Dictionary containing North complex D-State  
        self.d_sc_state         = dict()                      #Dictionary containing South complex S-State
        self.nc_device_mapping  = dict()                      #Dictionary containing NC D-State id and name mapping
        self.sc_device_mapping  = dict()                      #Dictionary containing SC D-State id and name mapping
        self.wakelock_dict      = dict()                    #Dict containing Wakelock state data. PID -> List of wakelocks
        self.user_wakelock_dict = dict()                    #Dict containing Wakelock state data. PID -> List of wakelocks
        self.wakelock_bucket_dict = dict()                  #PID -> Map of wakeup bucket counts
        self.thermal_list         = list()                  #comp_name -> min, max, avg
        self.bandwidth_list       = list()                  #comp_name -> min, max, avg
        self.gpu_p_states_dict    = dict()
        
        
        #Create a wakeUpDetailsClass object for every cpu found on the system
        i = 0     
        while i < system_info.m_core_count:
            self.per_core_info_list.insert(i, wakeUpDetailsClass(system_info))
            i += 1

        i = 0
        while i < system_info.m_core_count:
            self.p_residency.insert(i, dict())
            self.p_timeline.insert(i, dict())
            i += 1
            
        self.over_all_cpu_info = wakeUpDetailsClass(system_info)        #This object holds the over all system wakeups information , i.e over all cpu's
       

###########################################################################################################################################################        
def main():

    global debug      
    #Get the system information like cpucount , colection run time etc 
    system_info = generalSystemDetailsClass()
    
    #Parse the command line 
    parseCommandLineInput(system_info)
    
    #read the wudump file specified on command line to get the host platform information
    system_info.getPlatformDetailsFromWudump()    
    dS = defineDataStructuresClass(system_info)
     
    #Parses wudump to store data into the corresponding data structures
    parseWudump(system_info, dS)   

    #Print result tables
    printOutputObj = printOutput(system_info)                                 
    printOutputObj.printAllResults(system_info, dS)
    printOutputObj.cleanup()
                        
if __name__ ==  "__main__":
            main()     
#==========================================================
# end of file
# vim: set et ts=4 sw=4 ai ft=python :
