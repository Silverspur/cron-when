import datetime
import calendar


DELTA_1_MINUTE         = datetime.timedelta(seconds=60)
DELTA_1_HOUR           = datetime.timedelta(seconds=3600)
DELTA_1_DAY            = datetime.timedelta(days=1)
DELTA_AT_LEAST_1_MONTH = datetime.timedelta(days=31)

DAYS_IN_MONTH = [31,28,31,30,31,30,31,31,30,31,30,31]

debug = False
__dummy__ = None

def printdbg(msg):
    if debug:
        print(msg)

class CronError(Exception):
    pass


class ExtendedDateTime():

    def now():
        now = datetime.datetime.now()
        return ExtendedDateTime(now)

    def __init__(self,date):
        self.date = date

    def add(self,timedelta):
        self.date += timedelta

    def resetMinutes(self):
        self.date -= self.date.minute * DELTA_1_MINUTE
    def resetHours(self):
        self.date -= self.date.hour * DELTA_1_HOUR
    def resetDays(self):
        self.date -= (self.date.day-1) * DELTA_1_DAY
    def resetMonths(self):
        self.date = ExtendedDateTime(self.date.year,1,self.date.day,self.date.hour,self.date.minute)

class CronField:

    def __init__(self,string,first,last):
        self.first = first
        #for 'days of month' field, last is changing depending on the month we are in
        self.last = last
        self.start = None
        self.end = None
        self.any = False
        self.allowed = None
        self.mult = 1
        self.final = False

        try:
            main,mult = string.split('/')
            self.mult = int(mult)
        except:
            main = string

        if main =='*':
            if self.mult == 1:
                self.any = True
            self.start = self.first
            self.end   = self.last
        elif '-' in main:
            self.start,self.end = main.split('-')
            self.start = int(self.start)
            self.end = int(self.end)
            if self.start < self.first or self.start > self.last:
                raise CronError("Expression '%s' has an out of bounds number: %d is not in [%d,%d]." % (string,self.start,self.first,self.last))
            if self.end < self.first or self.end > self.last:
                raise CronError("Expression '%s' has an out of bounds number: %d is not in [%d,%d]." % (string,self.end,self.first,self.last))
            if self.end < self.start:
                raise CronError("Expression '%s' is an ill-written range: %d > %d." % (string,self.start,self.end))
        else:
            if ',' in main:
                self.allowed = [int(a) for a in main.split(',')]
                self.allowed.sort()
            else:
                self.allowed = [int(main)]

            for a in self.allowed:
                if a < self.first or a > self.last:
                    raise CronError("Expression '%s' is out of bounds: %d is not in [%d,%d]." % (string,a,self.first,self.last))

        if self.allowed:#P#
            printdbg(str(self.allowed))
        else:#P#
            printdbg('['+str(self.start)+'->'+str(self.end)+']')
        printdbg(' /'+str(self.mult))


    def next(self,current):
        # '*'
        if self.any:
            return (current, 0, False)

        next_value = None
        # 'x[,y,z,...]'
        #TODO multiplicator
        if self.allowed:
            if self.allowed[-1] < current:
                printdbg('(allowed with loop)')
                printdbg(self.allowed[0])
                next_value = self.allowed[0]
            else:
                for a in self.allowed:
                    if a >= current:
                        printdbg('(allowed)')
                        printdbg(a)
                        next_value = a
                        break
        else:
            # 'x-y'
            if current > self.end or current <= self.start:
                if current > self.end:
                    printdbg("(above end: set to start="+str(self.start)+')')
                else:
                    printdbg("(below start: set to start="+str(self.start)+')')
                next_value = self.start
            else:
                x = current - self.start
                printdbg('x='+str(x))
                if x % self.mult:
                    printdbg('x is not a multiple of multiplicator')
                    next_value = x + (self.mult - x % self.mult) + self.start
                    if next_value > self.end:
                        printdbg("(set to start="+str(self.start)+')')
                        next_value = self.start
                else:
                    printdbg('x is a multiple of multiplicator')
                    next_value = current
            printdbg('(range)')
            printdbg('next_value='+str(next_value))

        increment = next_value - current
        printdbg('increment = next_value - current:')
        printdbg(str(increment)+'  =  '+str(next_value)+'  -  '+str(current))
        if next_value >= current:
            ret_val = (next_value,increment,False)
        else:
            #TODO a decommenter une fois que le reste fonctionne: self.final = True
            # regarder si le temps d'exécution diminue
            ret_val = (next_value,increment+(self.last-self.first+1),True)
        return ret_val

class DaysOfWeekField(CronField):
    def __init__(self,string):
        string = (string
                .upper()
                .replace('SUN','0')
                .replace('MON','1')
                .replace('TUE','2')
                .replace('WED','3')
                .replace('THU','4')
                .replace('FRI','5')
                .replace('SAT','6'))
        super().__init__(string,0,6)

class MonthsField(CronField):
    def __init__(self,string):
        string = (string
                .upper()
                .replace('JAN','1')
                .replace('FEB','2')
                .replace('MAR','3')
                .replace('APR','4')
                .replace('MAY','5')
                .replace('JUN','6')
                .replace('JUL','7')
                .replace('AUG','8')
                .replace('SEP','9')
                .replace('OCT','10')
                .replace('NOV','11')
                .replace('DEC','12'))
        super().__init__(string,1,12)


class DaysFields():

    def __init__(self,dom_string,dow_string):
        self.dom = CronField(dom_string,1,31)
        self.dow = DaysOfWeekField(dow_string)

    def next(self,date):
        # If no constraint on either type of day
        if self.dom.any and self.dow.any:
            return (date.day, 0, False)

        # How many days in current month
        days_in_month = DAYS_IN_MONTH[date.month-1]
        if days_in_month == 28 and calendar.isleap(date.year):
            days_in_month = 29

        # Get next dom
        printdbg("DAYS OF MONTH")
        if not self.dom.any:
            # set last and end according to days in month
            self.dom.last = days_in_month
            was_none = False
            if self.dom.end is None:
                was_none = True
                self.dom.end = days_in_month
            dom_next_value,dom_increment,dom_isJumping = self.dom.next(date.day)
            # reset end to none (meaning value depends on month) if needed
            if was_none:
                self.dom.end = None
            printdbg("Days of month: "+str((dom_next_value,dom_increment,dom_isJumping)))


        # Get next dow
        printdbg("DAYS OF WEEK")
        if not self.dow.any:
            current_dow = calendar.weekday(date.year,date.month,date.day)+1 #python's 0 is Monday, vs Sunday in cron
            current_dow %= 7
            dow_next_value,dow_increment,dow_isJumping = self.dow.next(current_dow)
            dow_next_value_as_dom = (date.day + dow_increment) % days_in_month
            printdbg("Days of week: "+str((dow_next_value,dow_increment,dow_isJumping)))
            printdbg("   as dom: "+str(dow_next_value_as_dom))

        # Take the smallest increment that is not small due to 'any'
        if self.dow.any: # if (only) dow is any, focus on dom
            return (dom_next_value,dom_increment,__dummy__)
        if self.dom.any: # if (only) dom is any, focus on dow
            return (dow_next_value_as_dom,dow_increment,__dummy__)
        if dow_increment < dom_increment : # if noone is any, get the smallest increment
            return (dow_next_value_as_dom,dow_increment,__dummy__)
        else:
            return (dom_next_value,dom_increment,__dummy__)



class CronExpression:


    def __init__(self,cron_string):
        cron_fields = cron_string.split()
        self.minutes = CronField(cron_fields[0],0,59)
        self.hours   = CronField(cron_fields[1],0,23)
        self.days    = DaysFields(cron_fields[2],cron_fields[4])
        self.months  = MonthsField(cron_fields[3])

    def getNextOccurence(self,starting_point=None):
        if starting_point:
            now = ExtendedDateTime(starting_point)
        else:
            now = ExtendedDateTime.now()
        now.date += DELTA_1_MINUTE # go to next minute so that now is not an answer #TODO

        printdbg("===================================================================")
        printdbg("===================================================================")
        printdbg("===================================================================")
        printdbg("===================================================================")
        printdbg("Starting now = "+str(now))

        done = False
        while not done:
#        for i in range(1,5):
            printdbg("===================================================================")
            # Minutes
            printdbg("-------------------------------------------------------------------")
            printdbg("MINUTES")
            # if no result greater than current minute number
            increment = self.minutes.next(now.date.minute)[1]
            printdbg('Minutes:' + str(increment))
            if increment:
                now.date += increment*DELTA_1_MINUTE
            printdbg('New date = '+str(now.date))

            # Hours
            printdbg("-------------------------------------------------------------------")
            printdbg("HOURS")
            increment = self.hours.next(now.date.hour)[1]
            printdbg('Hours:' + str(increment))
            if increment:
                if not self.minutes.final: now.resetMinutes()
                now.date += increment*DELTA_1_HOUR
                printdbg('New date = '+str(now.date))
                continue

            # Days (day of month, day of week)
            printdbg("-------------------------------------------------------------------")
            printdbg("DAYS")
            increment = self.days.next(now.date)[1]
            printdbg('Days:' + str(increment))
            if increment:
                if not self.minutes.final: now.resetMinutes()
                if not self.hours.final: now.resetHours()
                now.date += increment*DELTA_1_DAY
                printdbg('New date = '+str(now.date))
                continue

            # Months
            printdbg("-------------------------------------------------------------------")
            printdbg("MONTHS")
            next_value,increment,isJumping = self.months.next(now.date.month)
            printdbg('Months:' + str(increment))
            if increment:
                if not self.minutes.final: now.resetMinutes()
                if not self.hours.final: now.resetHours()
                printdbg(next_value)
                printdbg(now.date.day)
                now.resetDays() #days are never final since they depend on month; and prevents creating a date like 31/02
                printdbg(next_value)
                printdbg(now.date.day)
                year = now.date.year+1 if isJumping else now.date.year
                now.date = datetime.datetime(year,next_value,now.date.day,now.date.hour,now.date.minute)
                printdbg('New date = '+str(now.date))
                continue

            done = True
        return now.date

    def getPreviousOccurence(self):
        pass








