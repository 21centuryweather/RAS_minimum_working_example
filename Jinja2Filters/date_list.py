#!/usr/bin/env python

import datetime

ISO8601_FORMAT = "%Y%m%dT%H%MZ"

def cycle_time_to_datetime(cycle_time):
    return datetime.datetime.strptime(cycle_time, ISO8601_FORMAT)

def datetime_to_cycle_time(date_time):
    return date_time.strftime(ISO8601_FORMAT)

def date_list(start_date, end_date, delta_date, include_endpoint=True):
    """Computes the North pole coordinates for a model domain.

       Arguments:
         centre -- coordinates (latitude, longitude) of the centre of 
                   the domain   
       Keyword arguments:
         do_rotate -- if this is true a coordinate system with a rotated
                      pole will be adopted
       Returns:
         The (latitude, longitude) coordinates of the North pole of the  
         domain with the specified centre.         
    """
    start_date = cycle_time_to_datetime(start_date)
    end_date = cycle_time_to_datetime(end_date)
    delta_date = datetime.timedelta(hours=delta_date)

    if include_endpoint:
        while start_date <= end_date:
            yield datetime_to_cycle_time(start_date)
            start_date += delta_date
    else:
        while start_date < end_date:
            yield datetime_to_cycle_time(start_date)
            start_date += delta_date
