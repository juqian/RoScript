% if note != None:
"""
${note}
"""
% endif
from rcs import Rcs

ro = Rcs()
% for name,parameter,sleep_time in instructions:
% if sleep_time != None:
ro.sleep(${sleep_time})
% endif
ro.${name}(${parameter})
% endfor

ro.reset_arms()