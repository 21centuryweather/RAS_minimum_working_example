#!/usr/bin/env python
# (c) Crown copyright Met Office. All rights reserved.
"""
Use "cumf" and Mule from the UM utilities to compare two fields
files, or PP files.

"""
import os
import re
import sys
import argparse

UNKNOWN_SECTION = -1
TIMESTEP_SECTION = 1
NORM_SECTION = 2
SEARCH_PATTERN = '\*\s+\d+\s+\d+\s+\d+\s+(\S+)\s+\*'
TIMESTEP_HEADER_STRING = (
    'Model time:[ ]+([0-9]{2,4}[-]{0,1}){3}[ ]+([0-9]{2,4}[:]{0,1}){3}')
NORM_HEADER_STRING = 'Linear solve for Helmholtz problem'
NORM_VALUE_STRING = '\\*[ ]*[0-9]+[ ]+[0-9]+[ ]+[0-9]+[ ]+.*\\*'
TIMESTEP_NUMBER_PATTERN = 'Atm_Step: Timestep[ ]+[0-9]+'


class Timestep(object):
    """
    Represent a timestep in a model pe_output file. Stores the timestamp and
    output norms for the timestep
    """
    def __init__(self, year, month, day, hour, minute, second, number):
        self.Year = year
        self.Month = month
        self.Day = day
        self.Hour = hour
        self.Minute = minute
        self.Second = second
        self.Number = number
        self.NormList = []

    def __str__(self):
        retVal = (
            '{year:04}/{month:02}/{day:02} {hour:02}:{minute:02}:{second:02}')
        retVal = retVal.format(year=self.Year,
                               month=self.Month,
                               day=self.Day,
                               hour=self.Hour,
                               minute=self.Minute,
                               second=self.Second)
        return retVal

    def addNorm(self, norm1):
        self.NormList += [norm1]

    def compareTimes(self, other):
        if self.Year != other.Year:
            return False
        if self.Month != other.Month:
            return False
        if self.Day != other.Day:
            return False
        if self.Hour != other.Hour:
            return False
        if self.Minute != other.Minute:
            return False
        if self.Second != other.Second:
            return False
        return True

    def compareNorms(self, other):
        if len(self.NormList) != len(other.NormList):
            return False
        for n1, n2 in zip(self.NormList, other.NormList):
            if n1.Norm != n2.Norm:
                return False
        return True
	
class Norm(object):
    """
    Represents a norm value output by an UM EndGame run.
    """
    TOLERANCE = 1.0e-8

    def __init__(self, outer, inner, iterations, norm):
        self.Outer = outer
        self.Inner = inner
        self.Iterations = iterations
        self.Norm = norm

    def __eq__(self, other):
        if self.Outer != other.Outer:
            return False
        if self.Inner != other.Inner:
            return False
        if self.Iterations != other.Iterations:
            return False
        if abs(self.Norm - other.Norm) < self.TOLERANCE:
            return False
        return True

def processTimestepString(line, timeStepHeaderPattern,
                          timeStepNumberPattern):
    """
    Process a line of a pe_output file containg a timestep header

    timeStep = processTimestepString(line, timeStepHeaderPattern)
    line: string containing the line to be processed
    timeStepHeaderPattern: string with the pattern of the timestamp
    to be matched
    timeStep: A Timestep object extract from line input argument
    """
    regExOutput = re.finditer(timeStepHeaderPattern, line)
    timeStepStr = ''.join([x1.group() for x1 in regExOutput])
    tsList1 = timeStepStr[11:].lstrip().rstrip().split(' ')
    dateList1 = [int(x1) for x1 in tsList1[0].split('-')]
    timeList1 = [int(x1) for x1 in tsList1[1].split(':')]
    regExOutput2 = re.finditer(timeStepNumberPattern, line)
    tsNum = -1
    try:
        tsNumMatch = [x for x in re.finditer(timeStepNumberPattern,
                                             line)][0]
        tsNum = int(tsNumMatch.group()[18:].strip(' '))
    except:
        tsNum = -1

    currentTimestep = Timestep(year=dateList1[0],
                               month=dateList1[1],
                               day=dateList1[2],
                               hour=timeList1[0],
                               minute=timeList1[1],
                               second=timeList1[2],
                               number=tsNum)
    return currentTimestep

	
def processNormString(line, normValuePattern):
    """
    Process a line of a pe_output file containing output model norms

    newNorm = processNormString(line, normValuePattern)
    line: string containing the line to processed
    normValuePattern: string containing the pattern to be matched
    newNorm: a Norm object containing the extracted norm value
    """
    regExOutput = re.finditer(normValuePattern, line)
    normStrRaw = ''.join([x1.group() for x1 in regExOutput])
    normStrRaw = normStrRaw[1:-1].lstrip().rstrip()
    normSet1 = [s1 for s1 in normStrRaw.split(' ') if len(s1) > 0]
    outerVal = int(normSet1[0])
    innerVal = int(normSet1[1])
    iterationsVal = int(normSet1[2])
    normVal = float(normSet1[3])
    newNorm = Norm(outer=outerVal,
                   inner=innerVal,
                   iterations=iterationsVal,
                   norm=normVal)
    return newNorm


def extractNorms(filename):
    """
    Process a file at the specified location

    timeStepList = extractNorms(filename)
    filename: string containing path to the pe_output file
    timeStepList: A list fo Timestep objects extracted from the file
    """
    timeStepHeaderPattern = re.compile(TIMESTEP_HEADER_STRING)
    normHeaderPattern = re.compile(NORM_HEADER_STRING)
    normValuePattern = re.compile(NORM_VALUE_STRING)
    timeStepNumberPattern = re.compile(TIMESTEP_NUMBER_PATTERN)

    timeStepList = []
    with open(filename) as resultFile:
        status = UNKNOWN_SECTION
        currentTimestep = None
        for i, line in enumerate(resultFile):
            if re.findall(timeStepHeaderPattern, line):
                # check that there is a current timestep, and that it has
                # at least one norm associated with it. First timestep
                # in a CRUN output file has a non-zero timestep number,
                # but no norms because it is an initialisation timestep,
                # not a calculation step so should be ignored.
                if (currentTimestep is not None and
                        currentTimestep.NormList):
                    timeStepList += [currentTimestep]

                currentTimestep = (
                    processTimestepString(line,
                                               timeStepHeaderPattern,
                                               timeStepNumberPattern))
                status = TIMESTEP_SECTION
            elif (re.findall(normHeaderPattern, line)
                  and status == TIMESTEP_SECTION):
                status = NORM_SECTION
            elif (re.findall(normValuePattern, line)
                  and status == NORM_SECTION):
                newNorm = processNormString(line, normValuePattern)
                currentTimestep.addNorm(newNorm)

    return timeStepList

def compareTimestepNorms(tsList1, tsList2):
    """
    Compare 2 lists of Timestep objects
    The function considers all possible pairs from the 2 lists. If a pair
    of Timestep objects have the same timestamp, the norms for that pair
    are compared and if they differ, the indices of the each Timestep
    object is stored. The function returns a list of Tuples containing 2
    integers, which refer to a Timestep in the first and second input
    arguments that have equal timestamps and unequal norms

    misMatches = compareTimestepNorms(tsList1, tsList2)
    tsList1: A list of Timestep objects
    tsList2: A list of Timestep objects
    misMatches: a list of Tuples containing 2 integers, which refer to a
                Timestep in the first and second input arguments that have
                equal timestamps and unequal norms
    """
    misMatches = []
    num_comps = 0
    iter1 = ((ix1, ts1, ix2, ts2)
             for ix1, ts1 in enumerate(tsList1)
             for ix2, ts2 in enumerate(tsList2))
    for ix1, ts1, ix2, ts2 in iter1:
        # We are not comparing norms for timestep 0, because none are
        # output as no calculation has been done!
        if ts1.Number > 0 and ts2.Number > 0 and ts1.compareTimes(ts2):
            num_comps += 1
            if not ts1.compareNorms(ts2):
                misMatches += [(ix1, ix2)]
    return misMatches, num_comps

def main(args):

    tsList1 = extractNorms(args.file1)
    tsList2 = extractNorms(args.file2)

    print('[INFO] %i time steps found in input 1'%(len(tsList1)))
    print('[INFO] %i time steps found in input 2'%(len(tsList2)))


    if (len(tsList1) != len(tsList2) and args.allow_unmatched == False):
        print("[FAIL] Number of timesteps different in each file "
                      "and \"allow_unmatched\" is false")
        raise Exception("Comparing number of timesteps failed. Check stdout for details")
    else:
        misMatches, num_comps = compareTimestepNorms(tsList1, tsList2)

        print('[INFO] Compared %i timesteps'%(num_comps))
        if len(misMatches) > 0:
            print('[FAIL] The following timesteps have different norms:')
            for ix1, ix2 in misMatches:
                print('[FAIL] Model time: %s'%(str(tsList1[ix1])))
            raise Exception("Comparing norms failed. Check stdout for details")
        else:
            print('[INFO] All matching timesteps have equal norms.')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "Compare the norms of two UM output files", epilog=__doc__)
    parser.add_argument("file1", type=str, help="First output file.")
    parser.add_argument("file2", type=str, help="Second output file.")
    parser.add_argument('--allow_unmatched', default=False, action='store_true',
                        help="Do you allow a different number of timesteps")
    args = parser.parse_args()
    main(args)

