# cron-when

Python package to compute next execution date of a cron expression.

```
# Simple example:

import datetime
from cronwhen import cronwhen

base_point = datetime.datetime(2019,10,3,12,49)

expression = cronwhen.CronExpression('59 10-20/3 1,2,6 * *')
expression.get_next_occurrence(base_point)
# --> datetime.datetime(2019,10,6,10,59)
```
