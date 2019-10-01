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


class DaysFields():

    def __init__(self,dom_string,dow_string):
        self.dom = CronField(dom_string,1,31)
        self.dow = CronField(dow_string,0,6)

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
        self.months  = CronField(cron_fields[3],1,12)

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








if __name__ == '__main__':
    base_point = datetime.datetime(2019,10,3,12,49) #Thursday
    tests = [
        # Any
        ('* * * * *',        ((2019,10, 3,12,50),(2019,10, 3,12,51),(2019,10, 3,12,52))),

        # Single field, either requiring an increment of the field above or not
        ('59 * * * *',       ((2019,10, 3,12,59),(2019,10, 3,13,59),(2019,10, 3,14,59))),
        ('35 * * * *',       ((2019,10, 3,13,35),(2019,10, 3,14,35),(2019,10, 3,15,35))),
        ('* 19 * * *',       ((2019,10, 3,19, 0),(2019,10, 3,19, 1),(2019,10, 3,19, 2))),
        ('* 0 * * *',        ((2019,10, 4, 0, 0),(2019,10, 4, 0, 1),(2019,10, 4, 0, 2))),
        ('* * 5 * *',        ((2019,10, 5, 0, 0),(2019,10, 5, 0, 1),(2019,10, 5, 0, 2))),
        ('* * 1 * *',        ((2019,11, 1, 0, 0),(2019,11, 1, 0, 1),(2019,11, 1, 0, 2))),
        ('* * * * 6',        ((2019,10, 5, 0, 0),(2019,10, 5, 0, 1),(2019,10, 5, 0, 2))),
        ('* * * * 1',        ((2019,10, 7, 0, 0),(2019,10, 7, 0, 1),(2019,10, 7, 0, 2))),
        ('* * * 12 *',       ((2019,12, 1, 0, 0),(2019,12, 1, 0, 1),(2019,12, 1, 0, 2))),
        ('* * * 1 *',        ((2020, 1, 1, 0, 0),(2020, 1, 1, 0, 1),(2020, 1, 1, 0, 2))),

        # Day of month, testing the number of days in each month and leap years
        ('0 0 31 * *',       ((2019,10,31, 0, 0),(2019,12,31, 0, 0),(2020, 1,31, 0, 0),(2020, 3,31, 0, 0))),
        ('0 0 29 * *',       ((2019,10,29, 0, 0),(2019,11,29, 0, 0),(2019,12,29, 0, 0),(2020, 1,29, 0, 0),
                              (2020, 2,29, 0, 0),(2020, 3,29, 0, 0),(2020, 4,29, 0, 0),(2020, 5,29, 0, 0),
                              (2020, 6,29, 0, 0),(2020, 7,29, 0, 0),(2020, 8,29, 0, 0),(2020, 9,29, 0, 0),
                              (2020,10,29, 0, 0),(2020,11,29, 0, 0),(2020,12,29, 0, 0),(2021, 1,29, 0, 0),
                              (2021, 3,29, 0, 0))),

        # Field combination, requiring an increment of the first 'any' field
        ('12 2 * * *',       ((2019,10, 4, 2,12),(2019,10, 5, 2,12),(2019,10, 6, 2,12))),
        ('7 5 1 * *',        ((2019,11, 1, 5, 7),(2019,12, 1, 5, 7),(2020, 1, 1, 5, 7))),
        ('7 5 * * 2',        ((2019,10, 8, 5, 7),(2019,10,15, 5, 7),(2019,10,22, 5, 7))),
        ('42 23 25 3 *',     ((2020, 3,25,23,42),(2021, 3,25,23,42),(2022, 3,25,23,42))),
        ('0 0 * 8 5',        ((2020, 8, 7, 0, 0),(2020, 8,14, 0, 0),(2020, 8,21, 0, 0))),

        # Single field, with multiplicator
        ('*/26 * * * *',     ((2019,10, 3,12,52),(2019,10, 3,13,00),(2019,10, 3,13,26))),
        ('* */7 * * *',      ((2019,10, 3,14, 0),(2019,10, 3,14, 1),(2019,10, 3,14, 2))),
        ('3 */7 * * *',      ((2019,10, 3,14, 3),(2019,10, 3,21, 3),(2019,10, 4, 0, 3))),
        ('* * */10 * *',     ((2019,10,11, 0, 0),(2019,10,11, 0, 1),(2019,10,11, 0, 2))),
        ('18 * */10 * *',    ((2019,10,11, 0,18),(2019,10,11, 1,18),(2019,10,11, 2,18))),
        ('* 3 */10 * *',     ((2019,10,11, 3, 0),(2019,10,11, 3, 1),(2019,10,11, 3, 2))),
        ('8 3 */10 * *',     ((2019,10,11, 3, 8),(2019,10,21, 3, 8),(2019,10,31, 3, 8),(2019,11, 1, 3, 8))),
        ('* * * * */3',      ((2019,10, 5, 0, 0),(2019,10, 5, 0, 1),(2019,10, 5, 0, 2))),
        ('19 * * * */1',     ((2019,10, 3,13,19),(2019,10, 3,14,19),(2019,10, 3,15,19))),
        ('59 23 * * */2',    ((2019,10, 3,23,59),(2019,10, 5,23,59),(2019,10, 6,23,59))),
        ('* * * */11 *',     ((2019,12, 1, 0, 0),(2019,12, 1, 0, 1),(2019,12, 1, 0, 2))),
        ('* 13 * */3 *',     ((2019,10, 3,13, 0),(2019,10, 3,13, 1),(2019,10, 3,13, 2))),
        ('12 * 8 */7 *',     ((2020, 1, 8, 0,12),(2020, 1, 8, 1,12),(2020, 1, 8, 2,12))),
        ('30 21 1 */5 *',    ((2019,11, 1,21,30),(2020, 1, 1,21,30),(2020, 6, 1,21,30))),

        # Out of range multiplicator
        ('*/132 * * * *',    ((2019,10, 3,13, 0),(2019,10, 3,14, 0),(2019,10, 3,15, 0))),
        ('0 */2154 * * *',   ((2019,10, 4, 0, 0),(2019,10, 5, 0, 0),(2019,10, 6, 0, 0))),
        ('0 0 */85 * *',     ((2019,11, 1, 0, 0),(2019,12, 1, 0, 0),(2020, 1, 1, 0, 0))),
        ('0 0 * * */87450',  ((2019,10, 6, 0, 0),(2019,10,13, 0, 0),(2019,10,20, 0, 0))),
        ('0 0 1 */13 *',     ((2020, 1, 1, 0, 0),(2021, 1, 1, 0, 0),(2022, 1, 1, 0, 0))),

        # Field combination, with multiplicators
        ('*/53 */2 * * *',          ((2019,10, 3,12,53),(2019,10, 3,14,00),(2019,10, 3,14,53))),
        ('*/35 */22 */8 * *',       ((2019,10, 9, 0, 0),(2019,10, 9, 0,35),(2019,10, 9,22, 0),
                                     (2019,10, 9,22,35),(2019,10,17, 0, 0),(2019,10,17, 0,35))),
        ('*/46 */18 * * */5',       ((2019,10, 4, 0, 0),(2019,10, 4, 0,46),(2019,10, 4,18, 0),
                                     (2019,10, 4,18,46),(2019,10, 6, 0, 0),(2019,10, 6, 0,46))),
        ('50 */16 */30 */4 *',      ((2020, 1, 1, 0,50),(2020, 1, 1,16,50),(2020, 1,31, 0,50),
                                     (2020, 1,31,16,50),(2020, 5, 1, 0,50),(2020, 5, 1,16,50),
                                     (2020, 5,31, 0,50),(2020, 5,31,16,50),(2020, 9, 1, 0,50),
                                     (2020, 9, 1,16,50),(2021, 1, 1, 0,50),(2021, 1, 1,16,50))),

        # Days in month vs days of week
        # - dom and dow has same first match
        ('0 0 5 * 6',       ((2019,10, 5, 0, 0),(2019,10,12, 0, 0),(2019,10,19, 0, 0),
                             (2019,10,26, 0, 0),(2019,11, 2, 0, 0),(2019,11, 5, 0, 0))),
        ('0 0 */2 * */6',   ((2019,10, 5, 0, 0),(2019,10, 6, 0, 0),(2019,10, 7, 0, 0),
                             (2019,10, 9, 0, 0),(2019,10,11, 0, 0),(2019,10,12, 0, 0))),
        # - dom has a first match before dow
        ('0 0 4 * 0',       ((2019,10, 4, 0, 0),(2019,10, 6, 0, 0),(2019,10,13, 0, 0))),
        # - dow has a first match before dom
        ('0 0 10 * 2',      ((2019,10, 8, 0, 0),(2019,10,10, 0, 0),(2019,10,15, 0, 0))),

        # Single field, ranges, with current time either before range, in range, or after range
        ('25-26 * * * *',   ((2019,10, 3,13,25),(2019,10, 3,13,26),(2019,10, 3,14,25))),
        ('48-51 * * * *',   ((2019,10, 3,12,50),(2019,10, 3,12,51),(2019,10, 3,13,48))),
        ('55-58 * * * *',   ((2019,10, 3,12,55),(2019,10, 3,12,56),(2019,10, 3,12,57),
                             (2019,10, 3,12,58),(2019,10, 3,13,55),(2019,10, 3,13,56))),
        ('50 1-3 * * *',    ((2019,10, 4, 1,50),(2019,10, 4, 2,50),(2019,10, 4, 3,50),
                             (2019,10, 5, 1,50),(2019,10, 5, 2,50),(2019,10, 5, 3,50))),
        ('55 3-13 * * *',   ((2019,10, 3,12,55),(2019,10, 3,13,55),(2019,10, 4, 3,55))),
        ('50 15-16 * * *',  ((2019,10, 3,15,50),(2019,10, 3,16,50),(2019,10, 4,15,50))),
        ('12 12 1-2 * *',   ((2019,11, 1,12,12),(2019,11, 2,12,12),(2019,12, 1,12,12))),
        ('50 2 2-4 * *',    ((2019,10, 4, 2,50),(2019,11, 2, 2,50),(2019,11, 3, 2,50),
                             (2019,11, 4, 2,50),(2019,12, 2, 2,50),(2019,12, 3, 2,50))),
        ('0 0 21-22 * *',   ((2019,10,21, 0, 0),(2019,10,22, 0, 0),(2019,11,21, 0, 0))),
        ('12 12 * * 0-1',   ((2019,10, 6,12,12),(2019,10, 7,12,12),(2019,10,13,12,12))),
        ('50 22 * * 1-5',   ((2019,10, 3,22,50),(2019,10, 4,22,50),(2019,10, 7,22,50))),
        ('0 0 * * 5-6',     ((2019,10, 4, 0, 0),(2019,10, 5, 0, 0),(2019,10,11, 0, 0))),
        ('12 12 12 3-4 *',  ((2020, 3,12,12,12),(2020, 4,12,12,12),(2021, 3,12,12,12))),
        ('50 22 31 6-10 *', ((2019,10,31,22,50),(2020, 7,31,22,50),(2020, 8,31,22,50))),
        ('0 0 1 11-12 *',   ((2019,11, 1, 0, 0),(2019,12, 1, 0, 0),(2020,11, 1, 0, 0))),

        # Ranges with same start and end
        ('59-59 * * * *',   ((2019,10, 3,12,59),(2019,10, 3,13,59),(2019,10, 3,14,59))),
        ('*/31 5-5 * * *',  ((2019,10, 4, 5, 0),(2019,10, 4, 5,31),(2019,10, 5, 5, 0))),
        ('36 21 30-30 * *', ((2019,10,30,21,36),(2019,11,30,21,36),(2019,12,30,21,36),
                             (2020, 1,30,21,36),(2020, 3,30,21,36),(2020, 4,30,21,36))),
        ('1 2 * * 0-0',     ((2019,10, 6, 2, 1),(2019,10,13, 2, 1),(2019,10,20, 2, 1))),
        ('0 23 1 12-12 *',  ((2019,12, 1,23, 0),(2020,12, 1,23, 0),(2021,12, 1,23, 0))),

        # Field combination, with ranges
        ('1-2 3-4 5-6 7-8 *',   ((2020, 7, 5, 3, 1),(2020, 7, 5, 3, 2),(2020, 7, 5, 4, 1),
                                 (2020, 7, 5, 4, 2),(2020, 7, 6, 3, 1),(2020, 7, 6, 3, 2),
                                 (2020, 7, 6, 4, 1),(2020, 7, 6, 4, 2),(2020, 8, 5, 3, 1),
                                 (2020, 8, 5, 3, 2),(2020, 8, 5, 4, 1),(2020, 8, 5, 4, 2),
                                 (2020, 8, 6, 3, 1),(2020, 8, 6, 3, 2),(2020, 8, 6, 4, 1),
                                 (2020, 8, 6, 4, 2),(2021, 7, 5, 3, 1))),
        ('0 10-11 * 11-11 2-3', ((2019,11, 5,10, 0),(2019,11, 5,11, 0),(2019,11, 6,10, 0),
                                 (2019,11, 6,11, 0),(2019,11,12,10, 0),(2019,11,12,11, 0),
                                 (2019,11,13,10, 0),(2019,11,13,11, 0),(2019,11,19,10, 0),
                                 (2019,11,19,11, 0),(2019,11,20,10, 0),(2019,11,20,11, 0),
                                 (2019,11,26,10, 0),(2019,11,26,11, 0),(2019,11,27,10, 0),
                                 (2019,11,27,11, 0),(2020,11, 3,10, 0),(2020,11, 3,11, 0),
                                 (2020,11, 4,10, 0),(2020,11, 4,11, 0))),

        # Ranges with multiplicators
        ('2-20/7 * * * *',      ((2019,10, 3,13, 2),(2019,10, 3,13, 9),(2019,10, 3,13,16),(2019,10, 3,14, 2))),
        ('0 1-2/20 * * *',      ((2019,10, 4, 1, 0),(2019,10, 5, 1, 0),(2019,10, 6, 1, 0))),
        ('12 12 25-31/6 * *',   ((2019,10,25,12,12),(2019,10,31,12,12),(2019,11,25,12,12),(2019,12,25,12,12))),
        ('14 14 14 * 0-5/4',    ((2019,10, 3,14,14),(2019,10, 6,14,14),(2019,10,10,14,14),(2019,10,13,14,14))),
        ('14 14 14 1-4/2 *',    ((2020, 1,14,14,14),(2020, 3,14,14,14),(2021, 1,14,14,14),(2021, 3,14,14,14))),

        # Single field, lists
        #TODO manage lists in wrong order (simple reordering at read time)
        #TODO manage lists with same element twice (reordering en imposant unicite)
        ('2,3,7 * * * *',       ((2019,10, 3,13, 2),(2019,10, 3,13, 3),(2019,10, 3,13, 7),(2019,10, 3,14, 2))),
        ('3,2,7 * * * *',       ((2019,10, 3,13, 2),(2019,10, 3,13, 3),(2019,10, 3,13, 7),(2019,10, 3,14, 2))),
        ('51 2,11,13 * * *',    ((2019,10, 3,13,51),(2019,10, 4, 2,51),(2019,10, 4,11,51))),
        ('51 2,13,13,11,2 * * *',    ((2019,10, 3,13,51),(2019,10, 4, 2,51),(2019,10, 4,11,51))),
        ('3 3 21,31 * *',       ((2019,10,21, 3, 3),(2019,10,31, 3, 3),(2019,11,21, 3, 3),(2019,12,21, 3, 3))),
        ('3 3 31,21 * *',       ((2019,10,21, 3, 3),(2019,10,31, 3, 3),(2019,11,21, 3, 3),(2019,12,21, 3, 3))),
        ('5 4 * * 0,3',         ((2019,10, 6, 4, 5),(2019,10, 9, 4, 5),(2019,10,13, 4, 5),(2019,10,16, 4, 5))),
        ('5 4 * * 3,0',         ((2019,10, 6, 4, 5),(2019,10, 9, 4, 5),(2019,10,13, 4, 5),(2019,10,16, 4, 5))),
        ('0 10 31 1,2,10 4',   ((2019,10,10,10, 0),(2019,10,17,10, 0),(2019,10,24,10, 0),(2019,10,31,10, 0),
                                 (2020, 1, 2,10, 0),(2020, 1, 9,10, 0),(2020, 1,16,10, 0),(2020, 1,23,10, 0),
                                 (2020, 1,30,10, 0),(2020, 1,31,10, 0),(2020, 2, 6,10, 0),(2020, 2,13,10, 0),
                                 (2020, 2,20,10, 0),(2020, 2,27,10, 0),(2020,10, 1,10, 0))),
        ('0 10 31 10,2,1 4',   ((2019,10,10,10, 0),(2019,10,17,10, 0),(2019,10,24,10, 0),(2019,10,31,10, 0),
                                 (2020, 1, 2,10, 0),(2020, 1, 9,10, 0),(2020, 1,16,10, 0),(2020, 1,23,10, 0),
                                 (2020, 1,30,10, 0),(2020, 1,31,10, 0),(2020, 2, 6,10, 0),(2020, 2,13,10, 0),
                                 (2020, 2,20,10, 0),(2020, 2,27,10, 0),(2020,10, 1,10, 0))),

        # Field combination, with lists
        ('1,2,3 0 11,12 1 *',   ((2020, 1,11, 0, 1),(2020, 1,11, 0, 2),(2020, 1,11, 0, 3),
                                 (2020, 1,12, 0, 1),(2020, 1,12, 0, 2),(2020, 1,12, 0, 3),
                                 (2021, 1,11, 0, 1),(2021, 1,11, 0, 2),(2021, 1,11, 0, 3))),
        ('0 0 25,26,28 2,3 1,5', ((2020, 2, 3, 0, 0),(2020, 2, 7, 0, 0),(2020, 2,10, 0, 0),
                                  (2020, 2,14, 0, 0),(2020, 2,17, 0, 0),(2020, 2,21, 0, 0),
                                  (2020, 2,24, 0, 0),(2020, 2,25, 0, 0),(2020, 2,26, 0, 0),
                                  (2020, 2,28, 0, 0),(2020, 3, 2, 0, 0),(2020, 3, 6, 0, 0),
                                  (2020, 3, 9, 0, 0),(2020, 3,13, 0, 0),(2020, 3,16, 0, 0),
                                  (2020, 3,20, 0, 0),(2020, 3,23, 0, 0),(2020, 3,25, 0, 0),
                                  (2020, 3,26, 0, 0),(2020, 3,27, 0, 0),(2020, 3,28, 0, 0),
                                  (2020, 3,30, 0, 0),(2021, 2, 1, 0, 0))),




        # Never-matching expressions #TODO
        #TODO code qui gere ces soucis
        #('0 0 31 2 *',      (None,)),

        # Ill-formed expressions
        #TODO



    ]

    count = 0
    for t in tests:
        count += 1
        expr_str,occurrences = t
        expr = CronExpression(expr_str)
        d = base_point
        print('--{ '+str(count).rjust(2,'0')+' }-----------------------------------------------------')
        print(expr_str)
        print(base_point.strftime('%a %d %b(%m) %Y, at %H:%M:%S'))
        for o in occurrences:
            d = expr.getNextOccurence(d)
            if o is None:
                if d is None:
                    print('None [OK]')
                else:
                    print('Should be none [KO]')
                continue
            print(' '+d.strftime('%a %d %b(%m) %Y, at %H:%M:%S').ljust(20,' '),end='')
            Y,M,D,h,m = o
            if d.year == Y and d.month == M and d.day == D and d.hour == h and d.minute == m:
                print('  [OK]')
            else:
                print('  [KO: expecting '+datetime.datetime(Y,M,D,h,m).strftime('%a %d %b(%m) %Y, at %H:%M:%S')+']')
                break

